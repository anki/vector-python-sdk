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
Synchronizer related classes and functions.

A synchronizer is used to make functions waitable outside
of the scope of the event loop. This allows for more
advanced use cases where multiple commands may be sent in
parallel (see :class:`AsyncRobot` in robot.py), but also
simpler use cases where everything executes synchronously.
"""

__all__ = ['Synchronizer']

import functools

import grpc

from . import exceptions


class Synchronizer:
    """
    Class for managing asynchronous functions in a synchronous world
    """

    # TODO Add types, sample code
    def __init__(self, loop, remove_pending, func, *args, **kwargs):
        """
        Create an Synchronizer
        """
        self.remove_pending = remove_pending
        self.loop = loop
        self.task = self.loop.create_task(func(*args, **kwargs))

    # TODO add sample code
    def wait_for_completed(self):
        """
        Wait until the task completes before continuing
        """
        try:
            return self.loop.run_until_complete(self.task)
        finally:
            self.remove_pending(self)
        return None

    # TODO Need param type and sample code
    # TODO: Might be better to instead have this as a parameter you can pass to wrap
    @staticmethod
    def disable_log(func):
        """
        Use this decorator to disable the automatic debug logging of wrap
        """
        func.disable_log = True
        return func

    # TODO Need param type and sample code
    @classmethod
    def wrap(cls, func):
        """
        Decorator to wrap a function for synchronous usage
        """

        # TODO Need docstring
        @functools.wraps(func)
        def log_result(func, logger):
            if not hasattr(func, "disable_log"):
                async def log(*args, **kwargs):
                    result = None
                    try:
                        result = await func(*args, **kwargs)
                    except grpc.RpcError as rpc_error:
                        raise exceptions.connection_error(rpc_error) from rpc_error
                    logger.debug(f'{type(result)}: {str(result).strip()}')
                    return result
                return log
            return func

        # TODO Need sample code
        @functools.wraps(func)
        def waitable(*args, **kwargs):
            """
            Either returns an Synchronizer or finishes processing the function depending on if the
            object "is_async"
            """
            wrapped_self = args[0]
            log_wrapped_func = log_result(func, wrapped_self.logger)

            # When invoking inside of a running event loop, things could explode.
            # Instead, we should return the async function and let users await it
            # manually.
            if wrapped_self.robot.loop.is_running():
                return log_wrapped_func(*args, **kwargs)
            if wrapped_self.robot.is_async:
                # Return a Synchronizer to manage Task completion
                synchronizer = cls(wrapped_self.robot.loop,
                                   wrapped_self.robot.remove_pending,
                                   log_wrapped_func,
                                   *args,
                                   **kwargs)
                wrapped_self.robot.add_pending(synchronizer)
                return synchronizer
            return wrapped_self.robot.loop.run_until_complete(log_wrapped_func(*args, **kwargs))
        return waitable
