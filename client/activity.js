import math from 'mathjs';


/**
 * Load a trained classifier from the API server and return it. The API
 * server returns a JavaScript file containing `var Activity = <Classifier>`.
 */
function trainAndLoadClassifier(url) {
  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.setAttribute('src', url);
    script.onload = () => resolve(Activity); // Loaded script exposes `var Activity`.
    script.onerror = reject;
    document.head.appendChild(script);
  })
}

/**
 * Create an URL query string from an object of query parts.
 * @returns {string}
 */
function createQuery(params) {
  return Object.keys(params)
  .map(k => encodeURIComponent(k) + '=' + encodeURIComponent(params[k]))
  .join('&');
}

/**
 * Preprocess an input matrix, which is in the format [[x1, y1, z1], [x2, y2, z2], ...],
 * by applying a preprocessor column-wise (x, y, z) and returning a list of reduced values,
 * e.g. [min(x1, x2, ...), min(y1, y2, ...), min(z1, z2, ...)]
 *
 * @param data a matrix of sensor values
 * @param preprocessor the preprocessor function name. Valid: min, max, median, stddev
 */
function preprocess(data, preprocessor) {
  // transpose input data, which is in the format [[x1, y1, z1], [x2, y2, z2], ...], to
  // [[x1, x2, ...], [y1, y2, ...], [z1, z2, ...]] to allow reducing all sensor values of
  // one type (x, y, z) to a single value.
  const columns = math.chain(data).matrix().transpose().valueOf()._data;
  let reduce;

  // TODO Implement Fast Fourier Transform (FFT)
  if (preprocessor === 'min' || preprocessor === 'max' || preprocessor === 'median')
    reduce = math[preprocessor];
  else if (preprocessor === 'stddev')
    reduce = math.std;
  else
    throw "Illegal preprocessor: " + preprocessor;

  // return a single, flat array with aggregated values, e.g.: [min(x1, x2, ...), min(y1, y2, ...), min(z1, z2, ...)]
  return columns.map(sensorValues => reduce(sensorValues));
}

export class Classifier {
  /**
   * Create a new Classifier.
   *
   * @param options an object of configuration options, see example.html.
   * @param callback the function which is called with the label after each prediction
   */
  constructor(options, callback) {
    this.options = options;
    this.measurements = [];
    this.callback = callback;
  }

  /**
   * Train an sklearn classifier on the API server and load it.
   *
   * @returns {Promise.<Classifier>}
   */
  train() {
    const query = {};
    query._sensors = this.options.sensors.join(",");
    query._labels = this.options.labels.join(",");

    if (this.options.preprocessor) {
      query._preprocessor = this.options.preprocessor.type;
      query._window = this.options.preprocessor.window;
    }

    for (const [key, value] of Object.entries(this.options.classifier)) {
      if (key === 'type')
        continue;

      query[key] = value;
    }

    const url = `${this.options.server}/measurements/${this.options.measurement}/classifiers/${this.options.classifier.type}.js?${createQuery(query)}`;

    return trainAndLoadClassifier(url).then(GeneratedClassifier => {
      this.predict = new GeneratedClassifier().predict;
      return this;
    });
  }

  /**
   * Predict a label, based on sensor values that have been saved in Classifier.measurements.
   * This method is typically called in a given interval. Use startPrediction() instead of
   * manually calling it.
   */
  runPrediction() {
    if (this.measurements.length === 0)
      return;

    // convert list of events, which looks like [DevicemotionEvent, DevicemotionEvent, ...] to
    // a list of lists containing the values in the order we need them: [[x1, y1, z1], [x2, y2, z2], ...]
    let data = this.measurements.map(measurement => this.options.sensors.map(sensor => measurement[sensor]));

    // clear all measurements, because the given window is done
    // TODO: Implement a rolling window, instead of the currently used non-overlapping window
    this.measurements = [];

    // If a preprocessor function (e.g. median) is given, reduce data with it, otherwise simply return the last data point
    if (this.options.preprocessor) {
      data = preprocess(data, this.options.preprocessor.type);
    } else {
      data = data.pop();
    }

    const labelId = this.predict(data);
    if (labelId === -1)
      throw Error("Invalid input used for prediction: " + JSON.stringify(data));

    const label = this.options.labels[labelId];
    this.callback(label);
  }

  /**
   * Start collecting sensor values and predicting classes. The callback given to the constructor
   * will be called with every class prediction. If the Classifier has not yet been trained,
   * it is first trained and loaded from the API server using Classifier.train().
   */
  startPrediction() {
    if (!this.predict)
      return this.train().then(() => this.startPrediction());

    window.addEventListener('devicemotion', (event) => {
      if (event.acceleration.x === null)
        throw Error("Device does not support devicemotion / acceleration.");

      const data = {
        'Accelerometer-X': event.acceleration.x,
        'Accelerometer-Y': event.acceleration.y,
        'Accelerometer-Z': event.acceleration.z,
      };

      this.measurements.push(data);
    });

    // If a preprocessor is given, use window size as interval, otherwise call runPrediction() in a loop
    if (this.options.preprocessor) {
      setInterval(() => this.runPrediction(), this.options.preprocessor.window);
    } else {
      const runPredictionLoop = () => {
        this.runPrediction();
        requestAnimationFrame(runPredictionLoop)
      };
      requestAnimationFrame(runPredictionLoop);
    }
  }
}

window.Classifier = Classifier;