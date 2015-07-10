__author__ = 'ahma'

import requests

def pushover(token, api_user, message):

    API_URL	= 'https://api.pushover.net/1/messages.json'

    requests.post(API_URL, {'token': token, 'user': api_user, 'message': message}, verify=False,)
