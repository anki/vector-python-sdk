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
__all__ = ['CONTROL_PRIORITY_LEVEL', 'Connection', 'on_connection_thread']

import asyncio
from concurrent import futures
from enum import Enum
import functools
import logging
import sys
import threading
from typing import Any, Awaitable, Callable, Coroutine, Dict, List

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
    """Creates and maintains a aiogrpc connection including managing the connection thread.
    The connection thread decouples the actual messaging layer from the user's main thread,
    and requires any network requests to be ran using :func:`asyncio.run_coroutine_threadsafe`
    to make them run on the other thread. Connection provides two helper functions for running
    a function on the connection thread: :func:`~Connection.run_coroutine` and
    :func:`~Connection.run_soon`.

    This class may be used to bypass the structures of the python sdk handled by
    :class:`~anki_vector.robot.Robot`, and instead talk to aiogrpc more directly.

    .. code-block:: python

        import anki_vector

        # Connect to your Vector
        conn = anki_vector.connection.Connection("Vector-XXXX", "XX.XX.XX.XX:443", "/path/to/file.cert", "<secret_key>")
        conn.connect()
        # Run your commands
        async def play_animation():
            # Run your commands
            anim = anki_vector.messaging.protocol.PlayAnimationRequest(name="anim_turn_left_01")
            await conn.grpc_interface.PlayAnimation(anim) # This needs to be run in an asyncio loop
        conn.run_coroutine(play_animation())
        # Close the connection
        conn.close()

    :param name: Vector's name in the format of "Vector-XXXX"
    :param host: The IP address and port of Vector in the format "XX.XX.XX.XX:443"
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
        self._thread: threading.Thread = None
        self._ready_signal: threading.Event = threading.Event()
        self._done_signal: asyncio.Event = None
        self._conn_exception = False

    @property
    def loop(self) -> asyncio.BaseEventLoop:
        """A direct reference to the loop on the connection thread.
        Can be used to run functions in on thread.

        .. code-block:: python

            import anki_vector
            import asyncio

            async def connection_function():
                print("I'm running in the connection thread event loop.")

            with anki_vector.Robot() as robot:
                asyncio.run_coroutine_threadsafe(connection_function(), robot.conn.loop)

        :returns: The loop running inside the connection thread
        """
        if self._loop is None:
            raise Exception("Attempted to access the connection loop before it was ready")
        return self._loop

    @property
    def thread(self) -> threading.Thread:
        """A direct reference to the connection thread. Available to callers to determine if the
        current thread is the connection thread.

        .. testcode::

            import anki_vector
            import threading

            with anki_vector.Robot() as robot:
                if threading.current_thread() is robot.conn.thread:
                    print("This code is running on the connection thread")
                else:
                    print("This code is not running on the connection thread")

        :returns: The connection thread where all of the grpc messages are being processed.
        """
        if self._thread is None:
            raise Exception("Attempted to access the connection loop before it was ready")
        return self._thread

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
        self.run_soon(self._request_control(timeout=timeout))

    async def _request_control(self, timeout: float = 10.0):
        self._control_events.request()
        try:
            self._has_control = await asyncio.wait_for(self._control_events.granted_event.wait(), timeout)
        except futures.TimeoutError as e:
            raise exceptions.VectorControlException(f"Surpassed timeout of {timeout}s") from e

    def connect(self, timeout: float = 10.0) -> None:
        """Connect to Vector. This will start the connection thread which handles all messages
        between Vector and Python.

        .. code-block:: python

            import anki_vector

            # Connect to your Vector
            conn = anki_vector.connection.Connection("Vector-XXXX", "XX.XX.XX.XX:443", "/path/to/file.cert", "<secret_key>")
            # Add a 5 second timeout to reduce the amount of time allowed for a connection
            conn.connect(timeout=5.0)
            async def play_animation():
                # Run your commands
                anim = anki_vector.messaging.protocol.PlayAnimationRequest(name="anim_turn_left_01")
                await conn.grpc_interface.PlayAnimation(anim) # This needs to be run in an asyncio loop
            conn.run_coroutine(play_animation())
            # Close the connection
            conn.close()

        :param timeout: The time allotted to attempt a connection, in seconds.
        """
        if self._thread:
            raise Exception("\n\nRepeated connections made to open Connection.")
        self._ready_signal.clear()
        self._thread = threading.Thread(target=self._connect, args=(timeout,), daemon=True, name="gRPC Connection Handler Thread")
        self._thread.start()
        ready = self._ready_signal.wait(timeout=2 * timeout)
        if not ready:
            raise exceptions.VectorNotFoundException()
        if hasattr(self._ready_signal, "exception"):
            e = getattr(self._ready_signal, "exception")
            delattr(self._ready_signal, "exception")
            raise e

    def _connect(self, timeout: float) -> None:
        """The function that runs on the connection thread. This will connect to Vector,
        and establish the BehaviorControl stream.
        """
        try:
            if threading.main_thread() is threading.current_thread():
                raise Exception("\n\nConnection._connect must be run outside of the main thread.")
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._done_signal = asyncio.Event()
            self._control_events = _ControlEventManager(self._loop)
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
            self._loop.run_until_complete(self._request_control(timeout=timeout))
        except Exception as e:  # pylint: disable=broad-except
            # Propagate the errors to the calling thread
            setattr(self._ready_signal, "exception", e)
            return
        finally:
            self._ready_signal.set()

        async def wait_until_done():
            return await self._done_signal.wait()
        self._loop.run_until_complete(wait_until_done())

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
            self.run_coroutine(self._control_stream_task).result()
        if self._channel:
            self.run_coroutine(self._channel.close()).result()
        self.run_coroutine(self._done_signal.set)
        self._thread.join(timeout=5)
        self._thread = None

    def run_soon(self, coro: Awaitable) -> None:
        """Schedules the given awaitable to run on the event loop for the connection thread.

        .. code-block:: python

            import anki_vector

            async def my_coroutine():
                print("Running on the connection thread")

            with anki_vector.Robot() as robot:
                robot.conn.run_soon(my_coroutine())
                time.sleep(1)


        :param coro: The coroutine, task or any awaitable to schedule for execution on the connection thread.
        """
        def soon():
            asyncio.ensure_future(coro)
        if threading.current_thread() is self._thread:
            self._loop.call_soon(soon)
        else:
            self._loop.call_soon_threadsafe(soon)

    def run_coroutine(self, coro: Awaitable) -> Any:
        """Runs a given awaitable on the connection thread's event loop.
        Cannot be called from within the connection thread.

        .. code-block:: python

            import anki_vector

            async def my_coroutine():
                print("Running on the connection thread")
                return "Finished"

            with anki_vector.Robot() as robot:
                result = robot.conn.run_coroutine(my_coroutine())
                print(result)

        :param coro: The coroutine, task or any other awaitable which should be executed.
        :returns: The result of the awaitable's execution.
        """
        if threading.current_thread() is self._thread:
            raise Exception("Attempting to invoke async from same thread."
                            "Instead you may want to use 'run_soon'")
        if asyncio.iscoroutinefunction(coro) or asyncio.iscoroutine(coro):
            return self._run_coroutine(coro)
        if asyncio.isfuture(coro):
            async def future_coro():
                return await coro
            return self._run_coroutine(future_coro())
        if callable(coro):
            async def wrapped_coro():
                return coro()
            return self._run_coroutine(wrapped_coro())
        raise Exception("\n\nInvalid parameter to run_coroutine: {}\n"
                        "This function expects a coroutine, task, or awaitable.".format(type(coro)))

    def _run_coroutine(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self._loop)


def on_connection_thread(log_messaging: bool = True) -> Callable[[Coroutine[util.Component, Any, None]], Any]:
    """A decorator generator used internally to denote which functions will run on
    the connection thread. This unblocks the caller of the wrapped function
    and allows them to continue running while the messages are being processed.

    .. code-block:: python


        import anki_vector

        class MyComponent(anki_vector.util.Component):
            @connection._on_connection_thread()
            async def on_connection_thread(self):
                // Do work on the connection thread

    :param log_messaging: Whether the log output should include the entire message or just the size. Recommended for
        large binary return values.
    :returns: A decorator which has 3 possible returns based on context: the result of the decorated function,
        the :class:`concurrent.futures.Future` which points to the decorated function, or the
        :class:`asyncio.Future` which points to the decorated function.
        These contexts are: when the robot is a :class:`~anki_vector.robot.Robot`,
        when the robot is an :class:`~anki_vector.robot.AsyncRobot`, and when
        called from the connection thread respectively.
    """
    def _on_connection_thread_decorator(func: Coroutine) -> Any:
        """A decorator which specifies a function to be executed on the connection thread

        :params func: The function to be decorated
        :returns: There are 3 possible returns based on context: the result of the decorated function,
            the :class:`concurrent.futures.Future` which points to the decorated function, or the
            :class:`asyncio.Future` which points to the decorated function.
            These contexts are: when the robot is a :class:`anki_vector.robot.Robot`,
            when the robot is an :class:`anki_vector.robot.AsyncRobot`, and when
            called from the connection thread respectively.
        """
        if not asyncio.iscoroutinefunction(func):
            raise Exception("\n\nCannot define non-coroutine function '{}' to run on connection thread.\n"
                            "Make sure the function is defined using 'async def'.".format(func.__name__ if hasattr(func, "__name__") else func))

        @functools.wraps(func)
        async def log_handler(func: Coroutine, logger: logging.Logger, *args: List[Any], **kwargs: Dict[str, Any]) -> Coroutine:
            """Wrap the provided coroutine to better express exceptions as specific :class:`anki_vector.exceptions.VectorException`s, and
            adds logging to incoming (from the robot) and outgoing (to the robot) messages.
            """
            result = None
            logger.debug(f'Outgoing {func.__name__}: {args[1:] if log_messaging else "size = {} bytes".format(sys.getsizeof(args[1:]))}')
            try:
                result = await func(*args, **kwargs)
            except grpc.RpcError as rpc_error:
                raise exceptions.connection_error(rpc_error) from rpc_error
            logger.debug(f'Incoming {type(result).__name__}: {str(result).strip() if log_messaging else "size = {} bytes".format(sys.getsizeof(result))}')
            return result

        @functools.wraps(func)
        def result(*args: List[Any], **kwargs: Dict[str, Any]) -> Any:
            """The function that is the result of the decorator. Provides a wrapped function.

            :returns: Based on context this can return the result of the decorated function,
                the :class:`concurrent.futures.Future` which points to the decorated function, or the
                :class:`asyncio.Future` which points to the decorated function.
                These contexts are: when the robot is a :class:`anki_vector.robot.Robot`,
                when the robot is an :class:`anki_vector.robot.AsyncRobot`, and when
                called from the connection thread respectively."""
            self = args[0]  # Get the self reference from the function call
            wrapped_coroutine = log_handler(func, self.logger, *args, **kwargs)
            if threading.current_thread() == self.conn.thread:
                if self.conn.loop.is_running():
                    return wrapped_coroutine
                raise Exception("\n\nThe connection thread loop is not running, but a "
                                "function '{}' is being invoked on that thread.\n".format(func.__name__ if hasattr(func, "__name__") else func))
            future = asyncio.run_coroutine_threadsafe(wrapped_coroutine, self.conn.loop)
            if self.force_async:
                return future
            return future.result()
        return result
    return _on_connection_thread_decorator
