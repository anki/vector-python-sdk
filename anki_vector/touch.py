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
Support for Vector's touch sensor.

The robot will forward a raw sensor reading representing the capacitance detected
on its back sensor.  Accompanied with this value is a true/false flag that takes into
account other aspects of the robot's state to evaluate whether the robot thinks it is
being touched or not.  This flag is the same value used internally for petting detection.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ["TouchComponent", "TouchSensorData"]

from . import util
from .events import Events
from .messaging import protocol


class TouchSensorData:
    """A touch sample from the capacitive touch sensor, accompanied with the robot's
    conclusion on whether this is considered a valid touch.
    """

    def __init__(self, proto_data: protocol.TouchData):
        self._raw_touch_value = proto_data.raw_touch_value
        self._is_being_touched = proto_data.is_being_touched

    @property
    def raw_touch_value(self) -> int:
        """The detected sensitivity from the touch sensor.

        This will not map to a constant raw value, as it may be impacted by various
        environmental factors such as whether the robot is on its charger, being held, humidity, etc.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                touch_data = robot.touch.last_sensor_reading
                if touch_data is not None:
                    raw_touch_value = touch_data.raw_touch_value
        """
        return self._raw_touch_value

    @property
    def is_being_touched(self) -> bool:
        """The robot's conclusion on whether the current value is considered
        a valid touch.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                touch_data = robot.touch.last_sensor_reading
                if touch_data is not None:
                    is_being_touched = touch_data.is_being_touched
        """
        return self._is_being_touched


class TouchComponent(util.Component):
    """Maintains the most recent touch sensor data

    This will be updated with every broadcast RobotState, and can be queried at any time.

    .. testcode::

        import anki_vector

        with anki_vector.Robot() as robot:
            touch_data = robot.touch.last_sensor_reading
            if touch_data is not None:
                print('Touch sensor value: {0}, is being touched: {1}'.format(touch_data.raw_touch_value, touch_data.is_being_touched))
    """

    def __init__(self, robot):
        super().__init__(robot)
        self._last_sensor_reading = None

        # Subscribe to a callback that updates the robot's local properties - which includes touch data.
        self._robot.events.subscribe(self._on_robot_state,
                                     Events.robot_state,
                                     _on_connection_thread=True)

    def close(self):
        """Closing the touch component will unsubscribe from robot state updates."""
        self._robot.events.unsubscribe(self._on_robot_state,
                                       Events.robot_state)

    @property
    def last_sensor_reading(self) -> TouchSensorData:
        """:class:`anki_vector.touch.TouchSensorData`: The last reported sensor data.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                touch_data = robot.touch.last_sensor_reading
        """
        return self._last_sensor_reading

    def _on_robot_state(self, _robot, _event_type, msg):
        self._last_sensor_reading = TouchSensorData(msg.touch_data)
