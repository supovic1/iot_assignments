import time
import ttn
from random import randint

app_id = "coffeegrinderiot"
access_key = "ttn-account-v2.GPKtvM0_H3ntqqXrp3b-ijs53XoxdOr8i7aCDOO4d_c"
mqtt_client = ttn.HandlerClient(app_id, access_key).data()
bytes = ['AQEBAQ==', # 01 01 01 01
         'AgEBAQ==', # 02 01 01 01
         'AQIBAQ==', # 01 02 01 01
         'AQECAQ==', # 01 01 02 01
         'AQEBAg==', # 01 01 01 02
         'AwEBAQ==', # 03 01 01 01
         ]

# using mqtt client
while True:
  mqtt_client.connect()
  mqtt_client.send("coffeegrinderdevice", bytes[randint(0, len(bytes) - 1)], port=1, sched="replace")
  mqtt_client.close()
  time.sleep(600)  # every 10 minutes

