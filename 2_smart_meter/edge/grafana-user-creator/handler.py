import datetime as dt
from math import sqrt
from time import sleep
import os
import json
import random
import string

import requests
import re

HOST = os.getenv("host")

URL_USERS = 'http://admin:smartmeter@'+HOST+'/api/admin/users'
URL_DASHBOARD = 'http://'+HOST+'/api/dashboards/db'
URL_DASHBOARD_PERMISSIONS = 'http://'+HOST+'/api/dashboards/id/%s/permissions'

CREDENTIALS = ""

headers = {
    'Authorization': 'Bearer eyJrIjoiU3FvV2RvbnRSVlYwN3lvaFdxdzRTRDNzT1hiTmlZZGEiLCJuIjoiYWRtaW5fa2V5IiwiaWQiOjJ9',
    'Content-Type': 'application/json',
}


def get_random_alphaNumeric_string(stringLength=12):
    #https://pynative.com/python-generate-random-string/
    lettersAndDigits = string.ascii_letters + string.digits
    return ''.join((random.choice(lettersAndDigits) for i in range(stringLength)))


def _extract_id(str):
    return re.findall(r'"id":\d+\b', str)[0][5:]


def generate_user_data(meter_id, email):
    # email = "meter_id_" + str(meter_id) + "@" + HOST
    # password = "meter_id_" + str(meter_id)
    password = get_random_alphaNumeric_string(12)
    # print ('login:', email, 'password:', password)

    CREDENTIALS = { 'login:', email, 'password:', password }
    # Send credentials to customer

    return '{ "email": "' + email + '", "login": "' + email + '","password": "' + password + '" }'


def create_user(meter_id, email):
    response = requests.post(URL_USERS, headers=headers, data=generate_user_data(meter_id, email))
    # print("Response:", response.text)
    return _extract_id(response.text)


def generate_user_dashboard(meter_id):
    file = open('./templates/grafana_customer_dashboard.json', mode='r')
    data = '{ "dashboard":' + file.read().replace('%s', str(meter_id)) + '}'
    file.close()
    # print(data)
    return data


def create_dashboard(meter_id):
    response = requests.post(URL_DASHBOARD, headers=headers, data=generate_user_dashboard(meter_id), verify=False)
    # print(response.text)
    return _extract_id(response.text)


def set_permissions(dashboard_id, user_id):
    permissions = '{ "items": [{"userId": 3,"permission": 4},{"userId": 4,"permission": 4},{"userId":' + str(
        user_id) + ',"permission": 1}]}'
    response = requests.post(URL_DASHBOARD_PERMISSIONS.replace('%s', str(dashboard_id)), headers=headers,
                             data=permissions)
    # print(response.text)


def handle(req):
    """handle a request to the function
    Args:
        req (str): request body
    """

    r = json.loads(req)
    
    meter_id = int(r['meter-id'])
    user_id = create_user(meter_id, r['email'])
    dashboard_id = create_dashboard(meter_id)
    set_permissions(dashboard_id, user_id)

    return CREDENTIALS
