import time
import ttn
import string

app_id = "coffeegrinderiot"
access_key = "ttn-account-v2.GPKtvM0_H3ntqqXrp3b-ijs53XoxdOr8i7aCDOO4d_c"


def uplink_callback(msg, client):
  print("Received uplink from ", msg.dev_id)
  print(msg)

handler = ttn.HandlerClient(app_id, access_key)

mqtt_client = handler.data()
mqtt_client.set_uplink_callback(uplink_callback)
mqtt_client.connect()
time.sleep(1)
mqtt_client.close()

# using application manager client
app_client =  handler.application()
my_app = app_client.get()
print(my_app)
my_devices = app_client.devices()
print(my_devices)