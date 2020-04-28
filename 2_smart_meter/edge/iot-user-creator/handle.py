import datetime as dt
from math import sqrt
from time import sleep
import os


import requests
import re

URL_USERS = 'http://admin:smartmeter@localhost:3000/api/admin/users'
URL_DASHBOARD = 'http://localhost:3000/api/dashboards/db'
URL_DASHBOARD_PERMISSIONS = 'http://localhost:3000/api/dashboards/id/%s/permissions'

headers = {
    'Authorization': 'Bearer eyJrIjoiU3FvV2RvbnRSVlYwN3lvaFdxdzRTRDNzT1hiTmlZZGEiLCJuIjoiYWRtaW5fa2V5IiwiaWQiOjJ9',
    'Content-Type': 'application/json',
}


def _extract_id(str):
    return re.findall(r'"id":\d+\b', str)[0][5:]


def generate_user_data(meter_id):
    email = "meter_id_" + str(meter_id) + "@localhost"
    password = "meter_id_" + str(meter_id)
    print ('login:', email, 'password:', password)
    return '{ "email": "' + email + '", "login": "' + email + '","password": "' + password + '" }'


def create_user(meter_id):
    response = requests.post(URL_USERS, headers=headers, data=generate_user_data(meter_id))
    print(response.text)
    return _extract_id(response.text)


def generate_user_dashboard(meter_id):
    file = open('./templates/grafana_customer_dashboard.json', mode='r')
    data = '{ "dashboard":' + file.read().replace('%s', str(meter_id)) + '}'
    file.close()
    print(data)
    return data


def create_dashboard(meter_id):
    response = requests.post(URL_DASHBOARD, headers=headers, data=generate_user_dashboard(meter_id), verify=False)
    print(response.text)
    return _extract_id(response.text)


def set_permissions(dashboard_id, user_id):
    permissions = '{ "items": [{"userId": 3,"permission": 4},{"userId": 4,"permission": 4},{"userId":' + str(
        user_id) + ',"permission": 1}]}'
    response = requests.post(URL_DASHBOARD_PERMISSIONS.replace('%s', str(dashboard_id)), headers=headers,
                             data=permissions)
    print(response.text)


HOST = os.getenv("host")


def handle(req):
    """handle a request to the function
    Args:
        req (str): request body
    """
    
    meter_id = int(req)

    user_id = create_user(meter_id)
    dashboard_id = create_dashboard(meter_id)
    set_permissions(dashboard_id, user_id)

    return "User Created"