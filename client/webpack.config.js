const path = require('path');
const webpack = require('webpack');

module.exports = {
  entry: ['./activity.js'],
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: 'activity.js'
  },
  module: {
    loaders: [
      {
        test: /\.js$/,
        exclude: /node_modules/,
        loader: 'babel-loader',
        query: {
          presets: ['es2015']
        }
      }
    ]
  },
  stats: {
    colors: true
  },
  devtool: 'source-map'
};