from influxdb import InfluxDBClient
from time import sleep
from math import sqrt
from numpy import array
from sklearn.metrics import mean_squared_error
from matplotlib import pyplot
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import MinMaxScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LinearRegression
from sklearn.linear_model import Lasso
from sklearn.linear_model import Ridge
from sklearn.linear_model import ElasticNet
from sklearn.linear_model import HuberRegressor
from sklearn.linear_model import Lars
from sklearn.linear_model import LassoLars
from sklearn.linear_model import PassiveAggressiveRegressor
from sklearn.linear_model import RANSACRegressor
from sklearn.linear_model import SGDRegressor
from sklearn.svm import SVR
from sklearn.neighbors import KNeighborsRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.isotonic import IsotonicRegression
from sklearn.neural_network import MLPRegressor
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.ensemble import VotingRegressor
import pandas as pd
import datetime as dt
import random

INFLUXDB_ADDRESS = 'localhost'
INFLUXDB_PORT = 8086
INFLUXDB_USER = 'mqtt'
INFLUXDB_PASSWORD = 'mqtt'
INFLUXDB_DATABASE = 'smart_meter'

influxdb_client = InfluxDBClient(INFLUXDB_ADDRESS, INFLUXDB_PORT, INFLUXDB_USER, INFLUXDB_PASSWORD, INFLUXDB_DATABASE)


def read_data(meter_id):
    query = "SELECT timestamp,value FROM smart_meter WHERE is_data_real = 'True' AND meter_id = " + str(
        meter_id) + " ORDER BY time"
    consumption = influxdb_client.query(query)
    consumption_df = pd.DataFrame.from_records(consumption.raw["series"][0]["values"],
                                               columns=consumption.raw["series"][0]["columns"])
    workdays = []
    hours = []
    date_time = dt.datetime.now()
    for index, row in consumption_df.iterrows():
        date_time = dt.datetime.utcfromtimestamp(row["timestamp"]) - dt.timedelta(days=363, hours=22)
        workdays.append(1 if (date_time).weekday() < 5 else 0)
        hours.append(date_time.hour)
    consumption_df.insert(1, "workday", workdays)
    consumption_df.insert(2, "hour", hours)
    return consumption_df, date_time


def split_data(data):
    train, test = data[0:-24], data[-24:]
    train = array(train)
    test = array(test)
    return train, test


# evaluate one or more weekly forecasts against expected values
def evaluate_forecasts(actual, predicted):
    mse = mean_squared_error(actual, predicted)
    # calculate rmse
    return sqrt(mse)


# prepare a list of ml models
def get_models(models=dict()):
    # linear models
    # models['lr'] = LinearRegression()
    # models['lasso'] = Lasso()
    # models['ridge'] = Ridge()
    # models['en'] = ElasticNet()
    # models['huber'] = HuberRegressor()
    # models['lars'] = Lars()
    # models['llars'] = LassoLars()
    # models['pa'] = PassiveAggressiveRegressor(max_iter=1000, tol=1e-3)
    # models['ranscac'] = RANSACRegressor()
    # models['sgd'] = SGDRegressor(max_iter=1000, tol=1e-3)
    models['svr'] = SVR(kernel='rbf', C=100, gamma=0.1, epsilon=.1)
    models['knn'] = KNeighborsRegressor(3)
    models['gpr'] = GaussianProcessRegressor()
    models['dt'] = DecisionTreeRegressor()
    # models['isotonic'] = IsotonicRegression()
    models['mlp'] = MLPRegressor()
    models['gbr'] = GradientBoostingRegressor(random_state=1, n_estimators=100)
    models['rfr'] = RandomForestRegressor(random_state=1, n_estimators=100)
    models['vr'] = VotingRegressor(estimators=[('gb', models['gbr']), ('rf', models['rfr'])])
    print('Defined %d models' % len(models))
    return models


# create a feature preparation pipeline for a model
def make_pipeline(model):
    steps = list()
    # standardization
    steps.append(('standardize', StandardScaler()))
    # normalization
    steps.append(('normalize', MinMaxScaler()))
    # the model
    steps.append(('model', model))
    # create pipeline
    pipeline = Pipeline(steps=steps)
    return pipeline


# convert history into inputs and outputs
def to_supervised(history):
    X, y = list(), list()
    # step over the entire history one time step at a time
    for i in range(len(history)):
        X.append(history[i][:-1])
        y.append(history[i][-1])
    return array(X), array(y)


# evaluate a single model
def evaluate_model(model, train, test):
    train_x, train_y = to_supervised(train)
    test_x, test_y = to_supervised(test)
    # make pipeline
    pipeline = make_pipeline(model)
    # fit the model
    pipeline.fit(train_x, train_y)
    # forecast
    predictions = pipeline.predict(test_x)
    score = evaluate_forecasts(test_y, predictions)
    return score, predictions


def _send_sensor_data_to_influxdb(time, meter_id, value):
    time = time + dt.timedelta(days=363, hours=22, seconds=meter_id)
    final = list(str(time) + "Z")
    final[10] = 'T'
    json_body = [
        {
            'measurement': 'predicted_test',
            'time': "".join(final),
            'fields': {
                'meter_id': meter_id,
                'value': int(value)
            }
        }
    ]
    print(json_body)
    # influxdb_client.write_points(json_body, time_precision='s')


def main():
    while True:
        for meter_id in range(4):
            consumption_df, date_time = read_data(meter_id)
            models = get_models()
            # compute next 48 hours
            for _ in range(48):
                date_time += dt.timedelta(hours=1)
                test = [1 if (date_time).weekday() < 5 else 0, date_time.hour, 0]
                next_hour_df = pd.DataFrame.from_records([test], columns=["workday", "hour", "timestamp"])
                score, scores = evaluate_model(models['rfr'],
                                               array(consumption_df[["workday", "hour", "value"]].values),
                                               next_hour_df.values)
                next_hour_df.insert(2, "value", scores)
                _send_sensor_data_to_influxdb(date_time, meter_id, scores[0])
                consumption_df = pd.concat([consumption_df, next_hour_df])

            train, test = split_data(consumption_df[["workday", "hour", "value"]].values)
            # for name, model in models.items():
            #     score, scores = evaluate_model(model, train, test)
            #     pyplot.plot(list(range(24)), scores, marker='o', label=name)
            #     print(name, score)
            # pyplot.plot(list(range(24)), [x[-1] for x in test], marker='o', label='real')
            # pyplot.legend()
            # pyplot.show()
        break
        sleep(3600)


if __name__ == '__main__':
    print('ML model')
    main()
