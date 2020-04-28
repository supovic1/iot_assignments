import datetime as dt
from math import sqrt
from time import sleep
import os

import pandas as pd
from influxdb import InfluxDBClient
from numpy import array
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler
from sklearn.preprocessing import StandardScaler


def get_file(path):
    v = ""
    with open(path) as f:
        v = f.read()
        f.close()
    return v.strip()

INFLUXDB_ADDRESS = os.getenv("influx_host")
INFLUXDB_PORT = os.getenv("influx_port")
INFLUXDB_DATABASE = os.getenv("influx_db")
INFLUXDB_USER = get_file("/var/openfaas/secrets/influx-user")
INFLUXDB_PASSWORD = get_file("/var/openfaas/secrets/influx-pass")

influxdb_client = InfluxDBClient(INFLUXDB_ADDRESS, INFLUXDB_PORT, INFLUXDB_USER, INFLUXDB_PASSWORD, INFLUXDB_DATABASE)


# read data for particular meter id (household)
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


# calculate root mean square error
def evaluate_forecasts(actual, predicted):
    return sqrt(mean_squared_error(actual, predicted))


# prepare a list of ml models
def get_models(models=dict()):
    models['rfr'] = RandomForestRegressor(random_state=1, n_estimators=100)
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


# convert data into inputs and outputs
def to_supervised(data):
    X, y = list(), list()
    for i in range(len(data)):
        X.append(data[i][:-1])
        y.append(data[i][-1])
    return array(X), array(y)


# evaluate a single model
def evaluate_model(model, train, test):
    # convert train/test data to inputs and outputs
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
    influxdb_client.write_points(json_body, time_precision='s')



def handle(req):
    """handle a request to the function
    Args:
        req (str): request body
    """
    
    for meter_id in range(4):
        consumption_df, date_time = read_data(meter_id)
        models = get_models()
        # compute next 48 hours
        for _ in range(48):
            date_time += dt.timedelta(hours=1)
            next_hour_X = [1 if (date_time).weekday() < 5 else 0, date_time.hour, 0]
            next_hour_df = pd.DataFrame.from_records([next_hour_X], columns=["workday", "hour", "timestamp"])
            score, scores = evaluate_model(models['rfr'],
                                            array(consumption_df[["workday", "hour", "value"]].values),
                                            next_hour_df.values)
            # insert column (predicted) value
            next_hour_df.insert(2, "value", scores)
            _send_sensor_data_to_influxdb(date_time, meter_id, scores[0])
            # concatenate dataframes
            consumption_df = pd.concat([consumption_df, next_hour_df])

    return "Model trained"