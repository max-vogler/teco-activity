import functools
from os import environ

from flask import Flask, make_response, request, jsonify
from flask_restful.reqparse import RequestParser
from influxdb import InfluxDBClient
from influxdb.resultset import ResultSet
from pylru import lrucache

from activity import classifiers

INFLUXDB_HOSTNAME = environ.get('INFLUXDB_HOSTNAME', 'localhost')
INFLUXDB_USERNAME = environ.get('INFLUXDB_USERNAME', 'root')
INFLUXDB_PASSWORD = environ.get('INFLUXDB_PASSWORD', 'root')
INFLUXDB_PORT = int(environ.get('INFLUXDB_PORT', '8086'))
INFLUXDB_DATABASE = environ.get('INFLUXDB_DATABASE', 'activity')
CACHE_SIZE = environ.get('CACHE_SIZE', 100)  # the number of classifiers to cache in memory
LABEL_KEY = environ.get('LABEL_KEY', 'Traininglabel')  # the key of the InfluxDB Tag that contains the label/class

app = Flask(__name__)
classifier_cache = lrucache(size=CACHE_SIZE)
client = InfluxDBClient(host=INFLUXDB_HOSTNAME,
                        port=INFLUXDB_PORT,
                        username=INFLUXDB_USERNAME,
                        password=INFLUXDB_PASSWORD,
                        database=INFLUXDB_DATABASE)


def query_data(labels, fields='*', measurement='devicemotion', label_key=LABEL_KEY) -> ResultSet:
    """
    Query InfluxDB by selecting a list of fields for a list of labels in a measurement. This function roughly executes
    SELECT <fields> FROM <measurement> WHERE <label_key> IN <labels>
    
    :param list[str] labels: list of label values to filter the InfluxDB Tag referenced by label_key
    :param str|list[str] fields: one or multiple InfluxDB field keys to return 
    :param str measurement: the InfluxDB measurement to query 
    :param label_key: the InfluxDB tag key to use as filter
    :return: ResultSet
    """
    if not isinstance(labels, list):
        raise Exception('Parameter "classes" must contain a list of field names')

    if isinstance(fields, list):
        fields = [f'"{field}"' for field in fields]
        select = ', '.join(fields)
    else:
        select = fields

    labels = [f'{label_key} = \'{label}\'' for label in labels]
    where = ' OR '.join(labels)
    query = f'SELECT {select} FROM {measurement} WHERE {where}'

    return client.query(query)


def return_json(f):
    """
    Decorator that wraps a function's return value in a JSON response.
    :param f: 
    :return: 
    """

    @functools.wraps(f)
    def wrapper(*args, **kw):
        return jsonify(f(*args, **kw))

    return wrapper


@app.route('/measurements')
@return_json
def get_measurements():
    """
    Return a list of all InfluxDB measurements
    :return: 
    """
    return [m['name'] for m in client.query('SHOW MEASUREMENTS').get_points()]


@app.route('/measurements/<measurement>/labels')
@return_json
def get_labels(measurement):
    """
    Return a list of all training labels for a given InfluxDB measurement
    :param str measurement: 
    :return: 
    """
    labels = client.query(f'SHOW TAG VALUES FROM {measurement} WITH KEY = Traininglabel').get_points()
    return [label['value'] for label in labels]


@app.route('/measurements/<measurement>/sensors')
@return_json
def get_sensors(measurement):
    """
    Return a list of all InfluxDB fields for a given measurement
    :param str measurement: 
    :return: 
    """
    fields = client.query(f'SHOW FIELD KEYS FROM {measurement}').get_points()
    return [f['fieldKey'] for f in fields]


@app.route('/classifiers')
@return_json
def get_classifiers():
    """
    Return a dict of classifiers and their arguments,
    :return: 
    """
    _classifiers = classifiers.get_all().items()
    return {name: list(cls.arguments.keys()) for name, cls in _classifiers}


@app.route('/measurements/<measurement>/classifiers/<classifier_name>.js')
def train_classifier(measurement, classifier_name):
    """
    Train a classifier and transpile it to JavaScript. This route expects a request in the following format:
    
    /measurements/<measurement>/classifiers/<classifier_name>.js?
        _sensors=<comma-separated list of fields>&
        _labels=<comma-separated list of labels>&
        <constructor arguments to configure <classifier_name>>
        
    For example:
    /measurements/devicemotion/classifiers/DecisionTreeClassifier.js?
        _sensors=Accelerometer-X,Accelerometer-Y,Accelerometer-Z&
        _labels=STILL,WALKING&
        max_depth=2
        
    :param str measurement: the InfluxBD measurement
    :param str classifier_name: the classifier class name (see: classifiers.get_all().keys())
    :return: JavaScript code of the trained classifier
    """
    if request.full_path not in classifier_cache:
        classifier = classifiers.get(classifier_name)

        parser = RequestParser()
        parser.add_argument('_sensors', type=str, required=True)
        parser.add_argument('_labels', type=str, required=True)
        parser.add_argument('_preprocessor', type=str, required=False)
        parser.add_argument('_window', type=int, required=False)
        for key, type in classifier.arguments.items():
            parser.add_argument(key, type=type)

        arguments = parser.parse_args()

        # `v is not None`: If the user does not provide an argument in the query, RequestParser sets None as value.
        # Stick to the default value of the Classifier constructor in this case by omitting the argument.
        # This might become an issue if a user wants to explicitly provide None as value, but is not able to.
        # ----
        # `k[:1] != '_'`: Do not pass arguments starting with an underscore to the Classifier. We use those
        # to separate "_sensors" and "_labels" from the Classifier constructor arguments.
        classifier_args = {k: v for k, v in arguments.items() if v is not None and k[:1] != '_'}
        query_labels = arguments['_labels'].split(',')
        query_fields = arguments['_sensors'].split(',') + [LABEL_KEY]

        data = query_data(labels=query_labels, fields=query_fields, measurement=measurement).get_points()
        x, y = classifiers.split_x_y(data, label_key=LABEL_KEY)

        if arguments['_window'] and arguments['_preprocessor']:
            x = classifiers.preprocess(x, arguments['_preprocessor'], arguments['_window'])
            y = y[x.index]
        elif arguments['_window'] or arguments['_preprocessor']:
            raise Exception("Both _window and _preprocessor need to be specified (or left out)")

        # sklearn fails if given the raw DataFrame, so use the Numpy representation
        x = x.values
        y = y.values

        cls = classifier.train(x=x, y=y, arguments=classifier_args)
        classifier_cache[request.full_path] = classifiers.transpile(cls)

    response = make_response(classifier_cache[request.full_path])
    response.headers['Content-Type'] = 'application/javascript'
    return response


@app.route('/activity.js')
def serve_javascript():
    return app.send_static_file('client/dist/activity.js')


if __name__ == '__main__':
    app.run(debug=False)
