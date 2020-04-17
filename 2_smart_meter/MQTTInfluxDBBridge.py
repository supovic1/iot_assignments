import base64
from typing import NamedTuple

import paho.mqtt.client as mqtt
from influxdb import InfluxDBClient

INFLUXDB_ADDRESS = 'localhost'
INFLUXDB_PORT = 8086
INFLUXDB_USER = 'mqtt'
INFLUXDB_PASSWORD = 'mqtt'
INFLUXDB_DATABASE = 'smart_meter'


MQTT_ADDRESS = 'influx.itu.dk'
MQTT_PORT = 8883
MQTT_USER = 'smartreader'
MQTT_PASSWORD = '4mp3r3h0ur'
MQTT_TOPIC = 'IoT2020sec/meters'
#MQTT_CAPATH = '/etc/ssl/certs/ca-certificates.crt'
MQTT_CAPATH = './certs/ca-certificates.crt'
MQTT_CLIENT_ID = 'MQTTInfluxDBBridge'

influxdb_client = InfluxDBClient(INFLUXDB_ADDRESS, INFLUXDB_PORT, INFLUXDB_USER, INFLUXDB_PASSWORD, None)

class SensorData(NamedTuple):
    isRealData: bool
    meter_id : int
    timestamp: int
    value: int


def on_connect(client, userdata, flags, rc):
    """ The callback for when the client receives a CONNACK response from the server."""
    print('Connected with result code ' + str(rc))
    client.subscribe(MQTT_TOPIC)


def on_message(client, userdata, msg):
    """The callback for when a PUBLISH message is received from the server."""
    print(msg.topic + ' ' + str(msg.payload))
    sensor_data = _parse_mqtt_message(msg.payload)
    if sensor_data is not None:
        _send_sensor_data_to_influxdb(sensor_data)


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
            'measurement': 'smart_meter',
            'tags': {
                'isRealData': sensor_data.isRealData
            },
            'fields': {
                'meter_id': sensor_data.meter_id,
                'timestamp': sensor_data.timestamp,
                'value': sensor_data.value
            }
        }
    ]
    influxdb_client.write_points(json_body)
    print(sensor_data, 'was saved to InfluxDB successfully.')



def _init_influxdb_database():
    databases = influxdb_client.get_list_database()
    if len(list(filter(lambda x: x['name'] == INFLUXDB_DATABASE, databases))) == 0:
        influxdb_client.create_database(INFLUXDB_DATABASE)
    influxdb_client.switch_database(INFLUXDB_DATABASE)
    print('Influx DB was initialized successfully.')


def main():
    _init_influxdb_database()

    mqtt_client = mqtt.Client(MQTT_CLIENT_ID)
    mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    mqtt_client.tls_set(MQTT_CAPATH)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    mqtt_client.connect(MQTT_ADDRESS, MQTT_PORT)
    mqtt_client.loop_forever()


if __name__ == '__main__':
    print('MQTT to InfluxDB bridge')
    main()
