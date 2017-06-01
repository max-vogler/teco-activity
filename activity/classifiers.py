from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn_porter import Porter
import pandas as pd


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


def split_x_y(data, label_key, remove_keys=None):
    df = pd.DataFrame(data)
    y = df[label_key]

    if remove_keys is None:
        remove_keys = []

    remove_keys.append(label_key)

    for key in remove_keys:
        del df[key]

    return df.values, y


def transpile(cls):
    return Porter(cls, language='js').port(class_name='Activity')
