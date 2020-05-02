import base64
from typing import NamedTuple
from influxdb import InfluxDBClient
import json
import os

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

influxdb_client = InfluxDBClient(INFLUXDB_ADDRESS, INFLUXDB_PORT, INFLUXDB_USER, INFLUXDB_PASSWORD, None)

class SensorData(NamedTuple):
    is_data_real : bool
    meter_id : int
    timestamp : int
    value : int


def _parse_mqtt_message(payload):
    bts = base64.b64decode(payload)
    timestamp = bts[1]
    for i in range(2,5):
        timestamp = timestamp << 8
        timestamp = timestamp + bts[i]
    value = bts[5] << 8
    value = value + bts[6]
    return SensorData((bts[0] >> 7) == 0, bts[0] & 127, timestamp, value)


def _send_sensor_data_to_influxdb(sensor_data):
    json_body = [
        {
            "measurement": "smart_meter",
            "tags": {
                "is_data_real": sensor_data.is_data_real
            },
            "fields": {
                "meter_id": sensor_data.meter_id,
                "timestamp": sensor_data.timestamp,
                "value": sensor_data.value
            }
        }
    ]
    influxdb_client.write_points(json_body)
    # print(sensor_data, 'was saved to InfluxDB successfully.')

    return json.dumps(json_body[0])

def _init_influxdb_database():
    databases = influxdb_client.get_list_database()
    if len(list(filter(lambda x: x['name'] == INFLUXDB_DATABASE, databases))) == 0:
        influxdb_client.create_database(INFLUXDB_DATABASE)
    influxdb_client.switch_database(INFLUXDB_DATABASE)
    # print('Influx DB was initialized successfully.')


def handle(req):
    """handle a request to the function
    Args:
        req (str): request body
    """
    
    _init_influxdb_database()

    # print("req:", req)

    r = json.loads(req)
    bts = bytes(r['data'][2:-1],'utf-8')

    # print("bts:", bts)

    sensor_data = _parse_mqtt_message(bts)
    if sensor_data is not None:
        return _send_sensor_data_to_influxdb(sensor_data)

    return req
