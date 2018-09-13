#!/usr/bin/env python3

#TODO Update this comment and anything else in file to be good for the public.

"""
This script is needed to use the python sdk as of now (when this file was created) because
we have turned on client authorization on the robot. This means that all connections will
require a client token guid to be valid.

Running this script requires that the Robot be on and connected to the same network as your
laptop. If you have any trouble, please mention it immediately in the #vic-coz-sdk channel.


**IMPORTANT NOTE**

Use _build/mac/Release/bin/tokprovision to provision your robot (not needed if you have connected with a recent build of Chewie)

******************
"""

# TODO: Update doc with actual copy

import configparser
from getpass import getpass
import json
import os
from pathlib import Path
import requests
import sys

from google.protobuf.json_format import MessageToJson
import grpc
try:
    # Non-critical import to add color output
    from termcolor import colored
except:
    def colored(text, color=None, on_color=None, attrs=None):
        return text

import anki_vector.messaging as api

class ApiHandler:
    def __init__(self, headers: dict, url: str):
        self._headers = headers
        self._url = url

    @property
    def headers(self):
        return self._headers

    @property
    def url(self):
        return self._url

class Api:
    def __init__(self, environment):
        if environment == "prod":
            self._handler = ApiHandler(
                headers={'Anki-App-Key': 'aung2ieCho3aiph7Een3Ei'},
                url='https://accounts.api.anki.com/1/sessions'
            )
        # TODO: remove beta and dev from released version
        elif environment == "beta":
            self._handler = ApiHandler(
                headers={'Anki-App-Key': 'va3guoqueiN7aedashailo'},
                url='https://accounts-beta.api.anki.com/1/sessions'
            )
        else:
            self._handler = ApiHandler(
                headers={'Anki-App-Key': 'eiqu8ae6aesae4vi7ooYi7'},
                url='https://accounts-dev2.api.anki.com/1/sessions'
            )

    @property
    def handler(self):
        return self._handler

def get_esn():
    esn = os.environ.get('ANKI_ROBOT_SERIAL')
    if esn is None or len(esn) == 0:
        print("Please find your Robot Serial Number (ex. 00e20100) located on the underside of Vector, or accessible from Vector's debug screen.\n")
        esn = input('Enter Robot Serial Number: ')
    else:
        print("Found Robot Serial Number in environment variable '{}'".format(colored("ANKI_ROBOT_SERIAL", "green")))
    esn = esn.lower()
    print("Using Robot Serial Number: {}".format(colored(esn, "cyan")))
    print("\nDownloading certificate from the cloud...", end="")
    sys.stdout.flush()
    r = requests.get('https://session-certs.token.global.anki-services.com/vic/{}'.format(esn))
    if r.status_code != 200:
        print(colored(" ERROR", "red"))
        sys.exit(r.content)
    print(colored(" DONE\n", "green"))
    cert = r.content
    return cert, esn

def user_authentication(session_id: bytes, cert: bytes, ip: str, name: str) -> str:
    # Pin the robot certificate for opening the channel
    creds = grpc.ssl_channel_credentials(root_certificates=cert)

    print("Attempting to download guid from {} at {}:443...".format(colored(name, "cyan"), colored(ip, "cyan")), end="")
    sys.stdout.flush()
    channel = grpc.secure_channel("{}:443".format(ip), creds,
                                        options=(("grpc.ssl_target_name_override", name,),))
    interface = api.client.ExternalInterfaceStub(channel)
    request = api.protocol.UserAuthenticationRequest(user_session_id=session_id.encode('utf-8'))
    response = interface.UserAuthentication(request)
    if response.code != api.protocol.UserAuthenticationResponse.AUTHORIZED:
        print(colored(" ERROR", "red"))
        sys.exit("Failed to authorize request: {}\n\n"
                 "Make sure to either connect via Chewie (preferred) or follow the steps for logging a Vector into an account first: "
                 "https://ankiinc.atlassian.net/wiki/spaces/VD/pages/449380359/Logging+a+Victor+into+an+Anki+account".format(MessageToJson(response, including_default_value_fields=True)))
    print(colored(" DONE\n", "green"))
    return response.client_token_guid

def get_session_token():
    valid = ["prod", "beta", "dev"]
    environ = input("Select an environment [(dev)/beta/prod]? ")
    if environ == "":
        environ = "dev"
    if environ not in valid:
        sys.exit("{}: That is not a valid environment".format(colored("ERROR", "red")))

    print("Enter your email and password. Make sure to use the same account that was used to set up Vector.")
    username = input("Enter Email: ")
    password = getpass("Enter Password: ")
    payload = {'username': username, 'password': password}

    print("\nAuthenticating user with the cloud...", end="")
    sys.stdout.flush()
    api = Api(environ)
    r = requests.post(api.handler.url, data=payload, headers=api.handler.headers)
    if r.status_code != 200:
        print(colored(" ERROR", "red"))
        sys.exit(r.content)
    print(colored(" DONE\n", "green"))
    return json.loads(r.content)

def get_name_and_ip():
    robot_name = os.environ.get('VECTOR_ROBOT_NAME')
    if robot_name is None or len(robot_name) == 0:
        print("Find your Robot Name (ex. Vector-A1B2) by placing Vector on the charger, and double clicking Vector's backpack button.")
        robot_name = input("Enter Robot Name: ")
    else:
        print("Found Robot Name in environment variable '{}'".format(colored("VECTOR_ROBOT_NAME", "green")))
    print("Using Robot Name: {}".format(colored(robot_name, "cyan")))
    ip = os.environ.get('ANKI_ROBOT_HOST')
    if ip is None or len(ip) == 0:
        print("Find your Robot IP (ex. 192.168.42.42) by placing Vector on the charger, and double clicking Vector's backpack button.\n"
              "If you see {} on his face, reconnect Vector to your WiFi using the Vector Companion App.".format(colored("XX.XX.XX.XX", "red")))
        ip = input("Enter Robot IP: ")
    else:
        print("Found Robot IP in environment variable '{}'".format(colored("ANKI_ROBOT_HOST", "green")))
    print("Using IP: {}".format(colored(ip, "cyan")))
    return robot_name, ip

def main():
    print(__doc__)

    name, ip = get_name_and_ip()
    cert, esn = get_esn()
    token = get_session_token()
    if token.get("session") is None:
        sys.exit("Session error: {}".format(token))
    guid = user_authentication(token["session"]["session_token"], cert, ip, name)

    # Write cert to a file
    home = Path.home()
    anki_dir = home / ".anki-vector"
    os.makedirs(str(anki_dir), exist_ok=True)
    cert_file = str(anki_dir / "{name}-{esn}.cert".format(name=name, esn=esn))
    print("Writing certificate file to '{}'...".format(colored(cert_file, "cyan")))
    with os.fdopen(os.open(cert_file, os.O_WRONLY | os.O_CREAT, 0o600), 'wb') as f:
        f.write(cert)

    # Store details in a config file
    config_file = str(anki_dir / "sdk_config.ini")
    print("Writing config file to '{}'...".format(colored(config_file, "cyan")))
    config = configparser.ConfigParser()

    config.read(config_file)
    config[esn] = {}
    config[esn]["cert"] = cert_file
    config[esn]["ip"] = ip
    config[esn]["name"] = name
    config[esn]["guid"] = guid.decode("utf-8")
    with os.fdopen(os.open(config_file, os.O_WRONLY | os.O_CREAT, 0o600), 'w') as f:
        config.write(f)
    print(colored("SUCCESS!", "green"))

if __name__ == "__main__":
    main()
