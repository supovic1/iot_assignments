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

URL_USERS = 'http://admin:smartmeter@' + HOST + '/api/admin/users'
URL_DASHBOARD = 'http://' + HOST + '/api/dashboards/db'
URL_DASHBOARD_PERMISSIONS = 'http://' + HOST + '/api/dashboards/id/%s/permissions'
URL_CUSTOMERS_TEAM_MEMBERS = 'http://' + HOST + '/api/teams/10/members'

CREDENTIALS = ""

headers = {
    'Authorization': 'Bearer eyJrIjoidEY0VlhTSjAyRk1hNW9nM0VvRWV6cGpLa3ltS29LRVAiLCJuIjoiYWRtaW5fa2V5IiwiaWQiOjF9',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
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

    CREDENTIALS = {'login:', email, 'password:', password}
    # Send credentials to customer

    return '{ "email": "' + email + '", "login": "' + email + '","password": "' + password + '" }'


def create_user(meter_id, email):
    response = requests.post(URL_USERS, headers=headers, data=generate_user_data(meter_id, email))
    # print("Response:", response.text)
    return _extract_id(response.text)


def add_user_to_customers_team(user_id):
    data = '{ "userId": ' + str(user_id) + ' }'
    response = requests.post(URL_CUSTOMERS_TEAM_MEMBERS, headers=headers, data=data)
    # print(response.text)


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
    # teamId 9 = team named "suppliers" has "admin" permission
    # teamId 8 = team names "housing cooperative team 1" has "viewer" permission
    # userId _ has "viewer" permission
    permissions = '{ "items": [{"teamId": 9,"permission": 4},{"teamId": 8,"permission": 1},{"userId":' + str(
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
    add_user_to_customers_team(user_id)
    dashboard_id = create_dashboard(meter_id)
    set_permissions(dashboard_id, user_id)

    return CREDENTIALS
