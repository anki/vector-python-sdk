# Copyright (c) 2021 cyb3rdog
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the file LICENSE.txt or at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import grpc
import json
import ssl
import socket
import requests
import base64
import urllib3
urllib3.disable_warnings()

from cryptography import x509
from cryptography.hazmat.backends import default_backend

from os import name

from . import messaging
from .exceptions import (connection_error,
                         VectorUnauthenticatedException,
                         VectorNotFoundException)

class EscapePodMetadataPlugin:
    """A specification for custom escape pod authentication."""

    def __init__(self, token_guid):
        self.token_hash = token_guid

    def __call__(self, context, callback):
        """Implements authentication by passing metadata to a callback.
        Args:
          access_token: A string to place directly in the http request
            authorization header, for example
            "authorization: Bearer <access_token>".
          callback: An EscapePodMetadataPlugin to be invoked either
            synchronously or asynchronously.
        """

        callback((('authorization', 'Bearer ' +  self.token_hash ),), None)


class EscapePod:

    def url_for(host, method):
        return "https://{}/v1/{}".format(host, method)

    # Make a request and return a pair (status_code,result_json)
    # result_json is null if the call fails
    def request(host, guid, method, request_json):
        url = EscapePod.url_for( host, method )
        auth = 'Bearer ' + guid
        headers = {"Authorization": auth, "Content-Type" : "application/json" }
        try:
            response = requests.post( url, json=request_json, headers=headers, stream=False,
                # cert = self._cfg['cert'] )
                verify=False )
        except requests.exceptions.ConnectionError as e:
            raise VectorNotFoundException() from e
        except requests.exceptions.Timeout as e:
            raise VectorNotFoundException() from e
        except requests.exceptions.RequestException as e:
            raise VectorNotFoundException() from e

        if response.status_code == 200:
            return (response.status_code, response.json())

        return (response.status_code, None)

    #
    # The new DDL's Go-SDK uses grpc insecure channel together with call credentials.
    # That kind of credentials composition is not supported on low-level of many grpc
    # implementations including the python's grpc core. The reason for that is to
    # discourage developers from sending the credentials over the unecrypted channels.
    # This method is a replication of the Go-SDK current authentication method and is
    # not being used by this SDK. For the reference and educational purposes only.
    #
    def authenticate_insecure(host: str, name:str, cert: bytes = None) -> str:

        guid = base64.b64encode( bytes("Anything1", 'utf-8')).decode('utf-8')
        request_json = {"user_session_id": guid }
        response = EscapePod.request( host, guid, 'user_authentication', request_json )
        if response[1]:
            guid = base64.b64decode(response[1]['client_token_guid']).decode( 'utf-8' )
            return guid
        else:
            print( response[0] )

        return None


    def authenticate_escape_pod(host: str, name: str, cert: bytes = None) -> str:
        """Authenticates the escape pod Vector and returns the token hash guid"""

        call_credentials = grpc.metadata_call_credentials(EscapePodMetadataPlugin('Anything1'),
                                                                name='authorization')
        # Channel credential will be valid for the entire channel
        channel_credential = grpc.ssl_channel_credentials(root_certificates=cert)

        # Combining channel credentials and call credentials together
        credentials = grpc.composite_channel_credentials(
            channel_credential,
            call_credentials,
        )

        channel = grpc.secure_channel(host, credentials, options=(("grpc.ssl_target_name_override", name,),))

        # Verify the connection to Vector is able to be established (client-side)
        try:
            # Explicitly grab _channel._channel to test the underlying grpc channel directly
            grpc.channel_ready_future(channel).result(timeout=15)
        except grpc.FutureTimeoutError as e:
            raise VectorNotFoundException() from e

        try:
            interface = messaging.client.ExternalInterfaceStub(channel)
            request = messaging.protocol.UserAuthenticationRequest(
                user_session_id='anything1'.encode('utf-8'),
                client_name='anything2'.encode('utf-8'))

            response = interface.UserAuthentication(request)
            if response.code != messaging.protocol.UserAuthenticationResponse.AUTHORIZED:  # pylint: disable=no-member
                raise VectorUnauthenticatedException('Failed to authenticate')
        except grpc.RpcError as e:
            raise VectorUnauthenticatedException() from e

        return response.client_token_guid.decode("utf-8")


    def get_authentication_certificate(hostname:str) -> str:
        """Get the Vector gateway certificate"""
        host = hostname.split(":")[0]
        port = int(hostname.split(":")[1] or 443)
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        sock = context.wrap_socket(conn, server_hostname=host)
        sock.connect((host, port))
        cert = ssl.DER_cert_to_PEM_cert(sock.getpeercert(True))
        return str.encode(cert)


    def get_certificate_name(cert_data) -> str:
        """Validate the name on Vector's certificate against the user-provided name"""
        if cert_data is None:
            return None

        cert = x509.load_pem_x509_certificate(cert_data, default_backend())
        for fields in cert.subject:
            current = str(fields.oid)
            if "commonName" in current:
                return fields.value


    def validate_certificate_name(cert_file, robot_name) -> bool:
        """Validate the name on Vector's certificate against the user-provided name"""
        if cert_file is None or robot_name is None:
            return False

        with open(cert_file, "rb") as f:
            cert_data = f.read()
            return EscapePod.get_certificate_name(cert_data) == robot_name