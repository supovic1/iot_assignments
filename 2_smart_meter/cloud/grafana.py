import requests
import re

URL_USERS = 'http://admin:smartmeter@localhost:3000/api/admin/users'
URL_DASHBOARD = 'http://localhost:3000/api/dashboards/db'
URL_DASHBOARD_PERMISSIONS = 'http://localhost:3000/api/dashboards/id/%s/permissions'
URL_CUSTOMERS_TEAM_MEMBERS = 'http://localhost:3000/api/teams/10/members'

headers = {
    'Authorization': 'Bearer eyJrIjoidEY0VlhTSjAyRk1hNW9nM0VvRWV6cGpLa3ltS29LRVAiLCJuIjoiYWRtaW5fa2V5IiwiaWQiOjF9',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
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


def add_user_to_customers_team(user_id):
    data = '{ "userId": ' + str(user_id) + ' }'
    response = requests.post(URL_CUSTOMERS_TEAM_MEMBERS, headers=headers, data=data)
    print(response.text)


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
    # teamId 9 = team named "suppliers" has "admin" permission
    # teamId 8 = team names "housing cooperative team 1" has "viewer" permission
    # userId _ has "viewer" permission
    permissions = '{ "items": [{"teamId": 9,"permission": 4},{"teamId": 8,"permission": 1},{"userId":' + str(
        user_id) + ',"permission": 1}]}'
    response = requests.post(URL_DASHBOARD_PERMISSIONS.replace('%s', str(dashboard_id)), headers=headers,
                             data=permissions)
    print(response.text)


for meter_id in range(4):
    user_id = create_user(meter_id)
    add_user_to_customers_team(user_id)
    dashboard_id = create_dashboard(meter_id)
    set_permissions(dashboard_id, user_id)
