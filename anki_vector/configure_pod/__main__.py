#!/usr/bin/env python3

"""
***Vector EscapePod Python SDK Setup***

Vector requires all requests be authorized by an authenticated Anki user.

This script will enable this device to authenticate with your Vector
robot for use with a Vector Python SDK program.

Vector must be powered on and connected on the same network as your
computer. By running this script, you will be asked to provide your
Anki account credentials, and the script will download an authentication
token and cert that will grant you access to the robot and his
capabilities (such as camera and audio) as well as data stored on the
robot (such as faces and photos).

See the README for more information.

Use of Vector and the Vector SDK is subject to Anki's Privacy Policy and Terms and Conditions.

https://www.anki.com/en-us/company/privacy
https://www.anki.com/en-us/company/terms-and-conditions

"""

import argparse
import configparser
from getpass import getpass
import json
import os
from pathlib import Path
import platform
import re
import socket
import sys
import ssl

from cryptography import x509
from cryptography.hazmat.backends import default_backend
import grpc
import requests
try:
    from termcolor import colored  # pylint: disable=import-error
except:  # pylint: disable=bare-except
    def colored(text, color=None, on_color=None, attrs=None):  # pylint: disable=unused-argument
        return text

import anki_vector
from anki_vector import messaging


def get_serial(serial=None):
    if not serial:
        serial = os.environ.get('ANKI_ROBOT_SERIAL')
        if not serial:
            print("\n\nPlease find your robot serial number (ex. 00e20100) located on the underside of Vector, or accessible from Vector's debug screen.")
            serial = input('Enter robot serial number: ')
        else:
            print("Found robot serial number in environment variable '{}'".format(colored("ANKI_ROBOT_SERIAL", "green")))
    serial = serial.lower()
    print("Using robot serial number: {}".format(colored(serial, "cyan")))
    return serial


def get_cert(hostname=None):
    print("\nDownloading Vector certificate...", end="")
    sys.stdout.flush()

    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    sock = context.wrap_socket(conn, server_hostname=hostname)
    sock.connect((hostname, 443))
    cert = ssl.DER_cert_to_PEM_cert(sock.getpeercert(True))
    return str.encode(cert)


def user_authentication(session_id: bytes, cert: bytes, ip: str, name: str) -> str:
    # Pin the robot certificate for opening the channel
    creds = grpc.ssl_channel_credentials(root_certificates=cert)

    print("Attempting to download guid from {} at {}:443...".format(colored(name, "cyan"), colored(ip, "cyan")), end="")
    sys.stdout.flush()
    channel = grpc.secure_channel("{}:443".format(ip), creds,
                                  options=(("grpc.ssl_target_name_override", name,),))

    # Verify the connection to Vector is able to be established (client-side)
    try:
        # Explicitly grab _channel._channel to test the underlying grpc channel directly
        grpc.channel_ready_future(channel).result(timeout=15)
    except grpc.FutureTimeoutError:
        print(colored(" ERROR", "red"))
        sys.exit("\nUnable to connect to Vector\n"
                 "Please be sure to connect via the Vector companion app first, and connect your computer to the same network as your Vector.")

    try:
        interface = messaging.client.ExternalInterfaceStub(channel)
        request = messaging.protocol.UserAuthenticationRequest(
            user_session_id=session_id.encode('utf-8'),
            client_name=socket.gethostname().encode('utf-8'))
        response = interface.UserAuthentication(request)
        if response.code != messaging.protocol.UserAuthenticationResponse.AUTHORIZED:  # pylint: disable=no-member
            print(colored(" ERROR", "red"))
            sys.exit("\nFailed to authorize request:\n"
                     "Please be sure to first set up Vector using the companion app.")
    except grpc.RpcError as e:
        print(colored(" ERROR", "red"))
        sys.exit("\nFailed to authorize request:\n"
                 "An unknown error occurred '{}'".format(e))

    print(colored(" DONE\n", "green"))
    return response.client_token_guid



def standardize_name(robot_name):
    # Extend the name if not enough is provided
    if len(robot_name) == 4:
        robot_name = "Vector-{}".format(robot_name.upper())
    # Fix possible capitalization and space/dash/etc.
    if re.match("[Vv]ector.[A-Za-z0-9]{4}", robot_name):
        robot_name = "V{}-{}".format(robot_name[1:-5], robot_name[-4:].upper())
    # Check that the end is valid
    if re.match("Vector-[A-Z0-9]{4}", robot_name):
        return robot_name
    print(colored(" ERROR", "red"))
    sys.exit("Invalid robot name. Please match the format exactly. Example: Vector-A1B2")


def get_name_and_ip(robot_name=None, ip=None):
    if not robot_name:
        robot_name = os.environ.get('VECTOR_ROBOT_NAME')
        if not robot_name:
            print("\n\nFind your robot name (ex. Vector-A1B2) by placing Vector on the charger and double-clicking Vector's backpack button.")
            robot_name = input("Enter robot name: ")
        else:
            print("Found robot name in environment variable '{}'".format(colored("VECTOR_ROBOT_NAME", "green")))
    robot_name = standardize_name(robot_name)
    print("Using robot name: {}".format(colored(robot_name, "cyan")))
    if not ip:
        ip = os.environ.get('ANKI_ROBOT_HOST')
        if not ip:
            print("\n\nFind your robot ip address (ex. 192.168.42.42) by placing Vector on the charger, double-clicking Vector's backpack button,\n"
                  "then raising and lowering his arms. If you see {} on his face, reconnect Vector to your WiFi using the Vector Companion App.".format(colored("XX.XX.XX.XX", "red")))
            ip = input("Enter robot ip: ")
        else:
            print("Found robot ip address in environment variable '{}'".format(colored("ANKI_ROBOT_HOST", "green")))
    print("Using IP: {}".format(colored(ip, "cyan")))
    return robot_name, ip


def save_cert(cert, name, serial, anki_dir):
    """Write Vector's certificate to a file located in the user's home directory"""
    os.makedirs(str(anki_dir), exist_ok=True)
    cert_file = str(anki_dir / "{name}-{serial}.cert".format(name=name, serial=serial))
    print("Writing certificate file to '{}'...\n".format(colored(cert_file, "cyan")))
    with os.fdopen(os.open(cert_file, os.O_WRONLY | os.O_CREAT, 0o600), 'wb') as f:
        f.write(cert)
    return cert_file


def validate_cert_name(cert_file, robot_name):
    """Validate the name on Vector's certificate against the user-provided name"""
    with open(cert_file, "rb") as f:
        cert_file = f.read()
        cert = x509.load_pem_x509_certificate(cert_file, default_backend())
        for fields in cert.subject:
            current = str(fields.oid)
            if "commonName" in current:
                common_name = fields.value
                if common_name != robot_name:
                    print(colored(" ERROR", "red"))
                    sys.exit("The name of the certificate ({}) does not match the name provided ({}).\n"
                             "Please verify the name, and try again.".format(common_name, robot_name))
                else:
                    return


def write_config(serial, cert_file=None, ip=None, name=None, guid=None, clear=True):
    home = Path.home()
    config_file = str(home / ".anki_vector" / "sdk_config.ini")
    print("Writing config file to '{}'...".format(colored(config_file, "cyan")))

    config = configparser.ConfigParser(strict=False)

    try:
        config.read(config_file)
    except configparser.ParsingError:
        if os.path.exists(config_file):
            os.rename(config_file, config_file + "-error")
    if clear:
        config[serial] = {}
    if cert_file:
        config[serial]["cert"] = cert_file
    if ip:
        config[serial]["ip"] = ip
    if name:
        config[serial]["name"] = name
    if guid:
        config[serial]["guid"] = guid.decode("utf-8")
    temp_file = config_file + "-temp"
    if os.path.exists(config_file):
        os.rename(config_file, temp_file)
    try:
        with os.fdopen(os.open(config_file, os.O_WRONLY | os.O_CREAT, 0o600), 'w') as f:
            config.write(f)
    except Exception as e:
        if os.path.exists(temp_file):
            os.rename(temp_file, config_file)
        raise e
    else:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def main():
    parser = argparse.ArgumentParser(description=("Vector requires all requests be authorized by an authenticated Anki user. "
                                                  "This script will enable this device to authenticate with your Vector "
                                                  "robot for use with a Vector Python SDK program."),
                                     epilog=("See the README for more information. "
                                             "Use of Vector and the Vector SDK is subject to Anki's Privacy Policy and Terms and Conditions. "
                                             "https://www.anki.com/en-us/company/privacy and "
                                             "https://www.anki.com/en-us/company/terms-and-conditions"))
    parser.add_argument("-i", "--ip", help=("Your robot ip address (ex. 192.168.42.42). "
                                            "It may be found by placing Vector on the charger, "
                                            "double-clicking Vector's backpack button, "
                                            "then raising and lowering his arms. "
                                            "If you see {} on his face, "
                                            "reconnect Vector to your WiFi using the Vector Companion App.".format(colored("XX.XX.XX.XX", "red"))))
    parser.add_argument("-n", "--name", help=("Your robot name (ex. Vector-A1B2). "
                                              "It may be found by placing Vector on the charger and double-clicking Vector's backpack button."))
    parser.add_argument("-s", "--serial", help=("Your robot serial number (ex. 00e20100). "
                                                "It is located on the underside of Vector, or accessible from Vector's debug screen."))
    parser.add_argument("-u", "--update", dest="new_ip", help=("Update the stored ip for Vector. This makes it easier to transfer between networks."))
    args = parser.parse_args()

    if args.new_ip:
        serial = get_serial(args.serial)
        write_config(serial, ip=args.new_ip, clear=False)
        print(colored("\nIP Updated!", "green"))
        sys.exit()

    print(__doc__)

    valid = ["y", "Y", "yes", "YES"]
    environ = input("Do you wish to proceed? (y/n) ")
    if environ not in valid:
        sys.exit("Stopping...")

    name, ip = get_name_and_ip(args.name, args.ip)
    serial = get_serial(args.serial)
    cert = get_cert(ip)

    home = Path.home()
    anki_dir = home / ".anki_vector"

    cert_file = save_cert(cert, name, serial, anki_dir)
    validate_cert_name(cert_file, name)

    guid = user_authentication("Anything1", cert, ip, name)

    # Store credentials in the .anki_vector directory's sdk_config.ini file
    write_config(serial, cert_file, ip, name, guid)
    print(colored("\nSUCCESS!", "green"))

if __name__ == "__main__":
    main()
