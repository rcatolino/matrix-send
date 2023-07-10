#!/usr/bin/python3

import argparse
import configparser
import requests
import uuid

def login(config):
    login_data = {
            'device_id' : config['device']['device_id'],
            'initial_device_display_name' : config['device']['device_name'],
            'type' : "m.login.password",
            'identifier' : {
                'type' : "m.id.user",
                'user' : config['server']['user'],
                },
            'password' : config['server']['password'],
            }

    r = requests.post(f"{config['server']['url']}/_matrix/client/v3/login", json=login_data)
    print(f"Login status : {r.status_code}")
    if r.status_code != 200:
        print("Login failed, check user/password")
        return None

    access_token = r.json()['access_token']
    config['server']['access_token'] = access_token
    return access_token

def sendmsg(access_token, api_url, room, msg):
    data = {
            'body' : msg,
            'msgtype' : "m.text",
            }

    r = requests.put(f"{api_url}/rooms/{room}/send/m.room.message/{uuid.uuid1()}",
                     headers = {'Authorization' : f"Bearer {access_token}"},
                     json = data)

    print(f"Sendmsg status : {r.status_code}, body : {r.text}")
    return r.status_code

def join(access_token, api_url, room):
    r = requests.post(f"{api_url}/join/{room}",
                      headers = {'Authorization' : f"Bearer {access_token}"},
                      json={})
    print(f"Join status : {r.status_code}, body : {r.text}")
    return r.status_code

def main(message, config, config_path):
    api_url = f"{config['server']['url']}/_matrix/client/v3"
    access_token = config['server'].get('access_token', None)
    if access_token is None:
        # We are unauthenticated, let's pretend we got a 401 and save a request
        ret = 401
    else:
        ret = sendmsg(access_token, api_url, config['server']['room'], message)

    if ret == 401:
        # Current access_token is invalid (or inexistant)
        access_token = login(config)
        assert(access_token is not None)
        # Save new access token in config
        with open(config_path, 'w') as conf_file:
            config.write(conf_file)
    elif ret == 403:
        # We are not in the room
        assert(join(access_token, api_url, config['server']['room']) == 200)
    else:
        return

    # Retry
    main(message, config, config_path)

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", required=True, help="Config file")
parser.add_argument("message", help="Message to send")

args = parser.parse_args()
config = configparser.ConfigParser()
config.read(args.config)

main(args.message, config, args.config)
