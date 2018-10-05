# Copyright (c) 2018 Anki, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the file LICENSE.txt or at
#
#     http://www.apache.org/licenses/LICENSE-2.0
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

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['VectorCameraFeedDisabledException',
           'VectorConnectionException',
           'VectorControlException',
           'VectorException',
           'VectorNotReadyException',
           'VectorTimeoutException',
           'VectorUnauthenticatedException',
           'VectorUnavailableException',
           'VectorUnimplementedException',
           'connection_error']


class VectorException(Exception):
    """Base class of all Vector SDK exceptions."""

# Don't add a docstring here or it prints out at runtime undesirably.


class VectorConnectionException(VectorException):
    def __init__(self, cause):
        self._status = cause.code()
        self._details = cause.details()
        doc_str = self.__class__.__doc__
        msg = (f"{self._status}: {self._details}"
               f"\n\n{doc_str if doc_str else 'Unknown error'}")
        super().__init__(msg)

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
    def __init__(self, cause=None):
        msg = (f"{self.__class__.__doc__}\n{cause if cause is not None else ''}")
        super().__init__(msg)


class VectorNotReadyException(_VectorGenericException):
    """Vector tried to do something before it was ready."""


class VectorControlException(_VectorGenericException):
    """Failed to get control of Vector.

Please verify that Vector is connected to the internet, and consider trying to request a higher control level.
"""


class VectorCameraFeedDisabledException(VectorException):
    """Failed to render video because camera feed was disabled."""
