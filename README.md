# Activity

A web service providing an easy way to train and generate JavaScript-based machine learning classifiers.

To add a classifier for standing, walking, and cycling to a mobile HTML5 page, insert the script:
```html
<script src="http://localhost:5000/measurements/devicemotion/classifiers/DecisionTreeClassifier.js?_sensors=Accelerometer-X,Accelerometer-Y,Accelerometer-Z&_labels=STILL,WALKING,CYCLING"></script>
```

## Set up

Start Docker containers with
```bash
docker-compose -p activity up -d
```

Download training data
```bash
git clone git@github.com:teco-kit/CSS-RTutorial.git data
```

Install requirements.txt
```bash
pip install -r requirements.txt
```

Convert training data from ARFF to InfluxDB line protocol
```bash
python activity/arff-to-influxdb.py -i data -o data.txt -m devicemotion
```

Create database and store training data to InfluxDB
```bash
curl -i -XPOST 'http://localhost:8086/query' --data-urlencode 'q=CREATE DATABASE activity'
curl -i -XPOST 'http://localhost:8086/write?db=activity' --data-binary @data.txt
```

## Usage

**http://localhost:5000/classifiers**
```json
{
    "DecisionTreeClassifier": [
        "criterion",
        "splitter",
        "max_depth",
        "..."
    ],
    "RandomForestClassifier": [
        "n_estimators",
        "criterion",
        "max_depth",
        "..."
    ]
}
```

**http://localhost:5000/measurements**
```json
[
  "devicemotion"
]
```

**http://localhost:5000/measurements/devicemotion/sensors**
```json
[
    "Acceleration",
    "Accelerometer-X",
    "Accelerometer-Y",
    "Accelerometer-Z",
    "..."
]
```

**http://localhost:5000/measurements/devicemotion/labels**
```json
[
    "WALKING",
    "CYCLING",
    "STILL",
    "..."
]
```


**http://localhost:5000/measurements/devicemotion/classifiers/DecisionTreeClassifier.js?_sensors=Accelerometer-X,Accelerometer-Y,Accelerometer-Z&_labels=STILL,WALKING&max_depth=2**
```js
var Activity = function() {

    this.predict = function(atts) {
        if (atts.length != 3) { return -1; };
        var classes = new Array(2);
            
        if (atts[2] <= -5.335479736328125) {
            if (atts[1] <= -3.6414794921875) {
                classes[0] = 27; 
                classes[1] = 1640; 
            // ...
```