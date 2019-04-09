# Copyright (c) 2018 Anki, Inc.
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

"""
SDK-specific exception classes for Vector.
"""

from grpc import RpcError, StatusCode

from .messaging import protocol

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['VectorAsyncException',
           'VectorBehaviorControlException',
           'VectorCameraFeedException',
           'VectorCameraImageCaptureException',
           'VectorConfigurationException',
           'VectorConnectionException',
           'VectorControlException',
           'VectorControlTimeoutException',
           'VectorException',
           'VectorInvalidVersionException',
           'VectorNotFoundException',
           'VectorNotReadyException',
           'VectorPropertyValueNotReadyException',
           'VectorTimeoutException',
           'VectorUnauthenticatedException',
           'VectorUnavailableException',
           'VectorUnimplementedException',
           'VectorExternalAudioPlaybackException',
           'connection_error']


class VectorException(Exception):
    """Base class of all Vector SDK exceptions."""


class VectorInvalidVersionException(VectorException):
    """Your SDK version is not compatible with Vector's version."""

    def __init__(self, version_response):
        host = version_response.host_version
        min_host = protocol.PROTOCOL_VERSION_MINIMUM
        client = protocol.PROTOCOL_VERSION_CURRENT
        if min_host > host:
            error_message = (f"{self.__class__.__doc__}\n\n"
                             f"Your Vector is an older version that is not supported by the SDK: Vector={host}, SDK minimum={min_host}\n"
                             f"Use your app to make sure that Vector is on the internet, and able to download the latest update.")
        else:
            error_message = (f"{self.__class__.__doc__}\n\n"
                             f"Your SDK is an older version that is not supported by Vector: Vector={host}, SDK={client}\n"
                             f"Please install the latest SDK to continue.")
        super().__init__(error_message)


class VectorControlException(VectorException):
    """Unable to run a function which requires behavior control."""

    def __init__(self, function):
        msg = (f"Unable to run '{function}' because it requires behavior control.\n\n"
               "Make sure to request control from Vector either by providing the 'behavior_control_level' parameter to Robot, "
               "or directly call 'request_control()' on your connection.")
        super().__init__(msg)


class VectorConnectionException(VectorException):
    def __init__(self, cause):
        doc_str = self.__class__.__doc__
        if cause is not None:
            self._status = cause.code()
            self._details = cause.details()
            msg = (f"{self._status}: {self._details}"
                   f"\n\n{doc_str if doc_str else 'Unknown error'}")
            super().__init__(msg)
        else:
            super().__init__(doc_str)

    @property
    def status(self):
        return self._status

    @property
    def details(self):
        return self._details


class VectorUnauthenticatedException(VectorConnectionException):
    """Failed to authenticate request."""


class VectorUnavailableException(VectorConnectionException):
    """Unable to reach Vector."""


class VectorUnimplementedException(VectorConnectionException):
    """Vector does not handle this message."""


class VectorTimeoutException(VectorConnectionException):
    """Message took too long to complete."""


def connection_error(rpc_error: RpcError) -> VectorConnectionException:
    """Translates grpc-specific errors to user-friendly :class:`VectorConnectionException`."""
    code = rpc_error.code()
    if code is StatusCode.UNAUTHENTICATED:
        return VectorUnauthenticatedException(rpc_error)
    if code is StatusCode.UNAVAILABLE:
        return VectorUnavailableException(rpc_error)
    if code is StatusCode.UNIMPLEMENTED:
        return VectorUnimplementedException(rpc_error)
    if code is StatusCode.DEADLINE_EXCEEDED:
        return VectorTimeoutException(rpc_error)
    return VectorConnectionException(rpc_error)


class _VectorGenericException(VectorException):
    def __init__(self, _cause=None, *args, **kwargs):  # pylint: disable=keyword-arg-before-vararg
        msg = (f"{self.__class__.__doc__}\n\n{_cause if _cause is not None else ''}")
        super().__init__(msg.format(*args, **kwargs))


class VectorAsyncException(_VectorGenericException):
    """Invalid asynchronous action attempted."""


class VectorBehaviorControlException(_VectorGenericException):
    """Invalid behavior control action attempted."""


class VectorCameraFeedException(_VectorGenericException):
    """The camera feed is not open.

Make sure to enable the camera feed either using Robot(show_viewer=True), or robot.camera.init_camera_feed()"""


class VectorCameraImageCaptureException(_VectorGenericException):
    """Image capture exception."""


class VectorConfigurationException(_VectorGenericException):
    """Invalid or missing configuration data."""


class VectorControlTimeoutException(_VectorGenericException):
    """Failed to get control of Vector.

Please verify that Vector is connected to the internet, is on a flat surface, and is fully charged.
"""


class VectorNotFoundException(_VectorGenericException):
    """Unable to establish a connection to Vector.

Make sure you're on the same network, and Vector is connected to the internet.
"""


class VectorNotReadyException(_VectorGenericException):
    """Vector tried to do something before it was ready."""


class VectorPropertyValueNotReadyException(_VectorGenericException):
    """Failed to retrieve the value for this property."""


class VectorUnreliableEventStreamException(VectorException):
    """The robot event stream is currently unreliable.

Please ensure the app is not connected. If this persists, reboot Vector and try again."""


class VectorExternalAudioPlaybackException(VectorException):
    """Failed to play external audio on Vector."""
