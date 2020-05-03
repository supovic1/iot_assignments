import base64
import datetime
import json
import os
import requests
import paho.mqtt.client as mqtt
from typing import NamedTuple


MQTT_ADDRESS = 'influx.itu.dk'
MQTT_PORT = 8883
MQTT_USER = 'smartreader'
MQTT_PASSWORD = os.getenv('mqtt-pass')
MQTT_TOPIC = 'IoT2020sec/meters'
MQTT_CAPATH = './certs/ca-certificates.crt'
gateway_url = os.getenv("gateway_url", "https://gateway.christoffernissen.me")


print("Using gateway {} and topic {}".format(gateway_url, MQTT_TOPIC))

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe(MQTT_TOPIC)

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    data = {
        'data': str(msg.payload),
        'created_at': str(datetime.datetime.now())
    }
    r = json.dumps(data)
    
    print("Request data(json):", r)
    
    with open("./samples.txt", "a") as f:
        f.write(r + "\n")
        f.close()

    print(msg.topic+" "+json.dumps(r))

    res = requests.post(gateway_url + "/function/iot-influxdb-savedata-func", data=r)
    print("Function response code", res.status_code)


mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
mqtt_client.tls_set(MQTT_CAPATH)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

mqtt_client.connect(MQTT_ADDRESS, MQTT_PORT)
mqtt_client.loop_forever()
