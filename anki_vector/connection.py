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
Management of the connection to and from Vector.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['CONTROL_PRIORITY_LEVEL', 'Connection']

import asyncio
from enum import Enum
from concurrent import futures

import grpc
import aiogrpc

from . import exceptions, util
from .messaging import client, protocol


class CONTROL_PRIORITY_LEVEL(Enum):
    """Enum used to specify the priority level for the program."""

    #: Runs below Mandatory Physical Reactions such as tucking Vector's head and arms during a fall,
    #: yet above Trigger-Word Detection.
    TOP_PRIORITY_AI = protocol.ControlRequest.TOP_PRIORITY_AI  # pylint: disable=no-member


class _ControlEventManager:
    """This manages every :class:`asyncio.Event` that handles the behavior control
    system.

    These include three events: granted, lost, and request.

    :class:`granted_event` represents the behavior system handing control to the SDK.

    :class:`lost_event` represents a higher priority behavior taking control away from the SDK.

    :class:`request_event` Is a way of alerting :class:`Connection` to request control.
    """

    def __init__(self, loop: asyncio.BaseEventLoop):
        self._granted_event = asyncio.Event(loop=loop)
        self._lost_event = asyncio.Event(loop=loop)
        self._request_event = asyncio.Event(loop=loop)
        self._has_control = False
        self._priority = CONTROL_PRIORITY_LEVEL.TOP_PRIORITY_AI
        self._is_shutdown = False

    @property
    def granted_event(self) -> asyncio.Event:
        """This event is used to notify listeners that control has been granted to the SDK."""
        return self._granted_event

    @property
    def lost_event(self) -> asyncio.Event:
        """Represents a higher priority behavior taking control away from the SDK."""
        return self._lost_event

    @property
    def request_event(self) -> asyncio.Event:
        """Used to alert :class:`Connection` to request control."""
        return self._request_event

    @property
    def has_control(self) -> bool:
        """Check to see that the behavior system has control (without blocking by checking :class:`granted_event`)"""
        return self._has_control

    @property
    def priority(self) -> CONTROL_PRIORITY_LEVEL:
        """The currently desired priority for the SDK."""
        return self._priority

    @property
    def is_shutdown(self) -> bool:
        """Detect if the behavior control stream is supposed to shut down."""
        return self._is_shutdown

    def request(self, priority: CONTROL_PRIORITY_LEVEL = CONTROL_PRIORITY_LEVEL.TOP_PRIORITY_AI) -> None:
        """Tell the behavior stream to request control via setting the :class:`request_event`."""
        self._priority = priority
        self._request_event.set()

    def update(self, enabled: bool) -> None:
        """Update the current state of control (either enabled or disabled)

        :param enabled: Used to enable/disable behavior control
        """
        self._has_control = enabled
        if enabled:
            self._granted_event.set()
            self._lost_event.clear()
        else:
            self._lost_event.set()
            self._granted_event.clear()

    def shutdown(self) -> None:
        """Tells the control stream to shut down.

        This will return control to the rest of the behavior system.
        """
        self._has_control = False
        self._granted_event.set()
        self._lost_event.set()
        self._is_shutdown = True
        self._request_event.set()


class Connection:
    """Creates and maintains a aiogrpc connection.

    This may be used to bypass the structures of the python sdk, and talk to aiogrpc more directly.

    .. code-block:: python

        import anki_vector

        # Connect to your Vector
        conn = connection.Connection("Vector-XXXX", "XX.XX.XX.XX:443", "/path/to/file.cert", "<secret_key>")
        conn.connect()
        # Run your commands
        anim = anki_vector.messaging.protocol.PlayAnimationRequest(name="anim_turn_left_01")
        await conn.grpc_interface.PlayAnimation(anim) # This needs to be run in an asyncio loop
        # Close the connection
        conn.close()

    :param name: Vector's name in the format of "Vector-XXXX"
    :param host: The ip and port of Vector in the format "XX.XX.XX.XX:443"
    :param cert_file: The location of the certificate file on disk
    :param loop: The asyncio loop for the control events to run inside
    """
    # TODO When sample code is ready, convert `.. code-block:: python` to `.. testcode::`

    def __init__(self, name: str, host: str, cert_file: str, guid: str):
        if cert_file is None:
            raise Exception("Must provide a cert file")
        self._loop: asyncio.BaseEventLoop = None
        self.name = name
        self.host = host
        self.cert_file = cert_file
        self._interface = None
        self._channel = None
        self._has_control = False
        self._logger = util.get_class_logger(__name__, self)
        self._control_stream_task = None
        self._control_events: _ControlEventManager = None
        self._guid = guid

    @property
    def grpc_interface(self) -> client.ExternalInterfaceStub:
        """A direct reference to the connected aiogrpc interface.

        This may be used to directly call grpc messages bypassing :class:`anki_vector.Robot`

        .. code-block:: python

            import anki_vector

            anim = anki_vector.messaging.protocol.PlayAnimationRequest(name="anim_turn_left_01")
            await conn.grpc_interface.PlayAnimation(anim) # This needs to be run in an asyncio loop
        """
        # TODO When sample code is ready, convert `.. code-block:: python` to `.. testcode::`
        return self._interface

    @property
    def control_lost_event(self) -> asyncio.Event:
        """This provides an :class:`asyncio.Event` that a user may :func:`wait()` upon to
        detect when Vector has taken control of the behaviors at a higher priority.

        .. testcode::

            import anki_vector

            async def auto_reconnect(conn: anki_vector.connection.Connection):
                await conn.control_lost_event.wait()
                conn.request_control()
        """
        return self._control_events.lost_event

    def request_control(self, timeout: float = 10.0):
        """Explicitly request control. Typically used after detecting :func:`control_lost_event`.

        .. testcode::

            import anki_vector

            async def auto_reconnect(conn: anki_vector.connection.Connection):
                await conn.control_lost_event.wait()
                conn.request_control(timeout=5.0)

        :param timeout: The time allotted to attempt a connection, in seconds.
        """
        self._control_events.request()
        try:
            self._has_control = self._loop.run_until_complete(asyncio.wait_for(self._control_events.granted_event.wait(), timeout))
        except futures.TimeoutError as e:
            raise exceptions.VectorControlException(f"Surpassed timeout of {timeout}s") from e

    def connect(self, loop: asyncio.BaseEventLoop, timeout: float = 10.0):
        """Connect to Vector

        .. code-block:: python

            import anki_vector

            # Connect to your Vector
            conn = connection.Connection("Vector-XXXX", "XX.XX.XX.XX:443", "/path/to/file.cert", "<secret_key>")
            # Add a 5 second timeout to reduce the amount of time allowed for a connection
            conn.connect(timeout=5.0)
            # Run your commands
            anim = anki_vector.messaging.protocol.PlayAnimationRequest(name="anim_turn_left_01")
            await conn.grpc_interface.PlayAnimation(anim) # This needs to be run in an asyncio loop
            # Close the connection
            conn.close()

        :param timeout: The time allotted to attempt a connection, in seconds.
        """
        # TODO When sample code is ready, convert `.. code-block:: python` to `.. testcode::`
        self._loop = loop
        self._control_events = _ControlEventManager(loop)
        trusted_certs = None
        with open(self.cert_file, 'rb') as cert:
            trusted_certs = cert.read()

        # Pin the robot certificate for opening the channel
        channel_credentials = aiogrpc.ssl_channel_credentials(root_certificates=trusted_certs)
        # Add authorization header for all the calls
        call_credentials = aiogrpc.access_token_call_credentials(self._guid)

        credentials = aiogrpc.composite_channel_credentials(channel_credentials, call_credentials)

        self._logger.info(f"Connecting to {self.host} for {self.name} using {self.cert_file}")
        self._channel = aiogrpc.secure_channel(self.host, credentials,
                                               options=(("grpc.ssl_target_name_override", self.name,),))

        # Verify the connection to Vector is able to be established (client-side)
        try:
            # Explicitly grab _channel._channel to test the underlying grpc channel directly
            grpc.channel_ready_future(self._channel._channel).result(timeout=timeout)  # pylint: disable=protected-access
        except grpc.FutureTimeoutError as e:
            raise exceptions.VectorNotFoundException() from e

        self._interface = client.ExternalInterfaceStub(self._channel)

        # Verify Vector and the SDK have compatible protocol versions
        version = protocol.ProtocolVersionRequest(client_version=0, min_host_version=0)
        protocol_version = self._loop.run_until_complete(self._interface.ProtocolVersion(version))
        if protocol_version.result != protocol.ProtocolVersionResponse.SUCCESS:  # pylint: disable=no-member
            raise exceptions.VectorInvalidVersionException(version, protocol_version)

        self._control_stream_task = self._loop.create_task(self._open_connections())
        self.request_control(timeout=timeout)

    async def _request_handler(self):
        """Handles generating messages for the BehaviorControl stream."""
        while await self._control_events.request_event.wait():
            self._control_events.request_event.clear()
            if self._control_events.is_shutdown:
                return
            msg = protocol.ControlRequest(priority=self._control_events.priority.value)
            msg = protocol.BehaviorControlRequest(control_request=msg)
            self._logger.debug(f"Sending: {msg}")
            yield msg
            await asyncio.sleep(0.1)

    async def _open_connections(self):
        """Starts the BehaviorControl stream, and handles the messages coming back from the robot."""
        try:
            async for response in self._interface.BehaviorControl(self._request_handler()):
                response_type = response.WhichOneof("response_type")
                if response_type == 'control_granted_response':
                    self._logger.debug(response)
                    self._control_events.update(True)
                elif response_type == 'control_lost_response':
                    self._logger.debug(response)
                    self._control_events.update(False)
        except futures.CancelledError:
            self._logger.debug('Behavior handler task was cancelled. This is expected during disconnection.')

    def close(self):
        """Cleanup the connection, and shutdown all the even handlers.

        Usually this should be invoked by the Robot class when it closes.

        .. code-block:: python

            import anki_vector

            # Connect to your Vector
            conn = connection.Connection("Vector-XXXX", "XX.XX.XX.XX:443", "/path/to/file.cert", "<secret_key>")
            conn.connect()
            # Run your commands
            anim = anki_vector.messaging.protocol.PlayAnimationRequest(name="anim_turn_left_01")
            await conn.grpc_interface.PlayAnimation(anim) # This needs to be run in an asyncio loop
            # Close the connection
            conn.close()
        """
        # TODO When sample code is ready, convert `.. code-block:: python` to `.. testcode::`
        if self._control_events:
            self._control_events.shutdown()
        if self._control_stream_task:
            self._control_stream_task.cancel()
            self._loop.run_until_complete(self._control_stream_task)
        if self._channel:
            self._loop.run_until_complete(self._channel.close())
