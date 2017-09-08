import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn_porter import Porter
import re


class Classifier:
    def __init__(self, realClass, arguments):
        self.realClass = realClass
        self.arguments = arguments

    def train(self, x, y, arguments):
        for k in arguments.keys():
            if k not in self.arguments:
                raise Exception(f'Illegal argument {k} for {self.realClass.__name__}')

        cls = self.realClass(**arguments)
        cls.fit(x, y)
        return cls


__CLASSIFIERS = {
    'DecisionTreeClassifier': Classifier(DecisionTreeClassifier, {
        'criterion': str,
        'splitter': str,
        'max_depth': int,
        'min_samples_split': int,
        'min_samples_leaf': int,
        'min_weight_fraction_leaf': float,
        'max_features': int,
        'random_state': int,
        'max_leaf_nodes': int,
        'min_impurity_split': float,
        'presort': bool
    }),
    'RandomForestClassifier': Classifier(RandomForestClassifier, {
        'n_estimators': int,
        'criterion': str,
        'max_depth': int,
        'min_samples_split': int,
        'min_samples_leaf': int,
        'min_weight_fraction_leaf': float,
        'max_features': str,
        'max_leaf_nodes': int,
        'min_impurity_split': float,
        'bootstrap': bool,
        'oob_score': bool,
        'random_state': int,
        'warm_start': bool,
    })
}


def get_all():
    """
    Return all usable classifiers.
    :return: dict of Classifier instances
    """
    return __CLASSIFIERS


def get(classifier):
    if classifier not in __CLASSIFIERS:
        raise Exception(f'Unknown classifier: {classifier}')

    return __CLASSIFIERS[classifier]


def split_x_y(data, label_key, time_key='time', remove_keys=None) -> (pd.DataFrame, pd.Series):
    df = pd.DataFrame(data).set_index(time_key)
    y = df[label_key]

    if remove_keys is None:
        remove_keys = []

    remove_keys.append(label_key)

    for key in remove_keys:
        del df[key]

    return df, y


def transpile(cls):
    return Porter(cls, language='js').port(class_name='Activity')


def preprocess(data: pd.DataFrame, preprocessor: str, window: int) -> pd.DataFrame:
    """
    Apply a preprocessing step to data.

    The preprocessor 'fft' operates on the columns (axis 0) of the given ndarray.
    :param data: the data to be modified
    :param preprocessor: the name of the preprocessor (available:  min, max, median, stddev)
    :return: preprocessed data
    """
    data = data.rolling(window // 50)  # TODO replace 50ms with real interval, or resample data

    if preprocessor == 'min':
        data = data.min()
    elif preprocessor == 'max':
        data = data.max()
    elif preprocessor == 'median':
        data = data.median()
    elif preprocessor == 'stddev':
        data = data.std()
    else:
        raise Exception(f'Unknown preprocessor {preprocessor}. Available: min, max, median, stddev.')

    return data.dropna()
