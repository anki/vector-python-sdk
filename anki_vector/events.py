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
Event handler used to make functions subscribe to robot events.
"""

__all__ = ['EventHandler']

import asyncio
from concurrent.futures import CancelledError

from .connection import Connection
from . import util
from .messaging import protocol


class EventHandler:
    """Listen for Vector events."""

    def __init__(self):
        self.logger = util.get_class_logger(__name__, self)
        self._loop = None
        self._conn = None
        self.listening_for_events = False
        self.event_task = None
        self.subscribers = {}

    def start(self, connection: Connection, loop: asyncio.BaseEventLoop):
        """Start listening for events. Automatically called by the :class:`anki_vector.robot.Robot` class.

        .. code-block:: python

            robot.events.start(robot.conn, robot.loop)

        :param connection: A reference to the connection from the SDK to the robot.
        :param loop: The loop to run the event task on.
        """
        self._loop = loop
        self._conn = connection
        self.listening_for_events = True
        self.event_task = self._loop.create_task(self._handle_events())

    def close(self):
        """Stop listening for events. Automatically called by the :class:`anki_vector.robot.Robot` class.

        .. code-block:: python

            robot.events.close()
        """
        self.listening_for_events = False
        self.event_task.cancel()
        self._loop.run_until_complete(self.event_task)

    async def _handle_events(self):
        try:
            req = protocol.EventRequest()
            async for evt in self._conn.grpc_interface.EventStream(req):
                if not self.listening_for_events:
                    break
                event_type = evt.event.WhichOneof("event_type")
                if event_type in self.subscribers.keys():
                    for func in self.subscribers[event_type]:
                        func(event_type, getattr(evt.event, event_type))
        except CancelledError:
            self.logger.debug('Event handler task was cancelled. This is expected during disconnection.')

    def subscribe(self, event_type: str, func):
        """Receive a method call when the specified event occurs.

        .. code-block:: python

            robot.events.subscribe("robot_observed_face",
                                   on_robot_observed_face)

        :param event_type: The name of the event that will result in func being called.
        :param func: A method implemented in your code that will be called when the event is fired.
        """
        if event_type not in self.subscribers.keys():
            self.subscribers[event_type] = set()
        self.subscribers[event_type].add(func)

    def unsubscribe(self, event_type: str, func):
        """Unregister a previously subscribed method from an event.

        .. code-block:: python

            robot.events.unsubscribe("robot_observed_face",
                                   on_robot_observed_face)

        :param event_type: The name of the event for which you no longer want to receive a method call.
        :param func: The method you no longer wish to be called when an event fires.
        """
        if event_type in self.subscribers.keys():
            event_subscribers = self.subscribers[event_type]
            if func in event_subscribers:
                event_subscribers.remove(func)
                if not event_subscribers:
                    del self.subscribers[event_type]
            else:
                self.logger.error(f"The function '{func.__name__}' is not subscribed to '{event_type}'")
        else:
            self.logger.error(f"Cannot unsubscribe from event_type '{event_type}'. "
                              "It has no subscribers.")
