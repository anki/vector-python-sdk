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
Support for Vector's distance sensor.

Vector's time-of-flight distance sensor has a usable range of about 30 mm to 1200 mm
(max useful range closer to 300mm for Vector) with a field of view of 25 degrees.

The distance sensor can be used to detect objects in front of the robot.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ["ProximityComponent", "ProximitySensorData"]

from . import util
from .events import Events
from .messaging import protocol


class ProximitySensorData:
    """A distance sample from the time-of-flight sensor with metadata describing reliability of the measurement

    The proximity sensor is located near the bottom of Vector between the two front wheels, facing forward. The
    reported distance describes how far in front of this sensor the robot feels an obstacle is. The sensor estimates
    based on time-of-flight information within a field of view which the engine resolves to a certain quality value.

    Four additional flags are supplied by the engine to indicate whether this proximity data is considered valid
    for the robot's internal pathfinding. Respecting these is optional, but will help python code respect the
    behavior of the robot's innate object avoidance.
    """

    def __init__(self, proto_data: protocol.ProxData):
        self._distance = util.Distance(distance_mm=proto_data.distance_mm)
        self._signal_quality = proto_data.signal_quality
        self._unobstructed = proto_data.unobstructed
        self._found_object = proto_data.found_object
        self._is_lift_in_fov = proto_data.is_lift_in_fov

    @property
    @util.block_while_none()
    def distance(self) -> util.Distance:
        """The distance between the sensor and a detected object

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                distance = robot.proximity.last_sensor_reading.distance
        """
        return self._distance

    @property
    @util.block_while_none()
    def signal_quality(self) -> float:
        """The quality of the detected object.

        The proximity sensor detects obstacles within a given field of view,
        this value represents the likelihood of the reported distance being
        a solid surface.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                signal_quality = robot.proximity.last_sensor_reading.signal_quality
        """
        return self._signal_quality

    @property
    @util.block_while_none()
    def unobstructed(self) -> bool:
        """The sensor has confirmed it has not detected anything up to its max range.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                unobstructed = robot.proximity.last_sensor_reading.unobstructed
        """
        return self._unobstructed

    @property
    @util.block_while_none()
    def found_object(self) -> bool:
        """The sensor detected an object in the valid operating range.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                found_object = robot.proximity.last_sensor_reading.found_object
        """
        return self._found_object

    @property
    @util.block_while_none()
    def is_lift_in_fov(self) -> bool:
        """Whether Vector's lift is blocking the time-of-flight sensor. While
        the lift will send clear proximity signals, it's not useful for object
        detection.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                is_lift_in_fov = robot.proximity.last_sensor_reading.is_lift_in_fov
        """
        return self._is_lift_in_fov


class ProximityComponent(util.Component):
    """Maintains the most recent proximity sensor data

    This will be updated with every broadcast RobotState, and can be queried at any time. Two sensor readings are made available:
        - the most recent data from the robot
        - the most recent data which was considered valid by the engine for usage

    An example of how to extract sensor data:

    .. testcode::

        import anki_vector

        with anki_vector.Robot() as robot:
            proximity_data = robot.proximity.last_sensor_reading
            if proximity_data is not None:
                print('Proximity distance: {0}'.format(proximity_data.distance))
    """

    def __init__(self, robot):
        super().__init__(robot)
        self._last_sensor_reading = None

        # Subscribe to a callback that updates the robot's local properties - which includes proximity data.
        self._robot.events.subscribe(self._on_robot_state,
                                     Events.robot_state,
                                     _on_connection_thread=True)

    def close(self):
        """Closing the touch component will unsubscribe from robot state updates."""
        self._robot.events.unsubscribe(self._on_robot_state,
                                       Events.robot_state)

    @property
    @util.block_while_none()
    def last_sensor_reading(self) -> ProximitySensorData:
        """:class:`anki_vector.proximity.ProximitySensorData`: The last reported sensor data.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                last_sensor_reading = robot.proximity.last_sensor_reading
        """
        return self._last_sensor_reading

    def _on_robot_state(self, _robot, _event_type, msg):
        self._last_sensor_reading = ProximitySensorData(msg.prox_data)
