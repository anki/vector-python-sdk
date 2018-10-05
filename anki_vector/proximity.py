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
Support for Vector's distance sensor.

Vector's time-of-flight distance sensor has a usable range of about 30 mm to 1200 mm
(max useful range closer to 300mm for Victor) with a field of view of 25 degrees.

The distance sensor can be used to detect objects in front of the robot.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ["ProximityComponent", "ProximitySensorData"]

from . import util


class ProximitySensorData:
    """A distance sample from the time-of-flight sensor with metadata describing reliability of the measurement

    The proximity sensor is located near the bottom of Vector between the two front wheels, facing forward. The
    reported distance describes how far in front of this sensor the robot feels an obstacle is. The sensor estimates
    based on time-of-flight information within a field of view which the engine resolves to a certain quality value.

    Four additional flags are supplied by the engine to indicate whether this proximity data is considered valid
    for the robot's internal pathfinding. Respecting these is optional, but will help python code respect the
    behavior of the robot's innate object avoidance.
    """

    @property
    def distance(self) -> float:
        """The distance between the sensor and a detected object

        .. code-block:: python

           distance = robot.proximity.last_sensor_reading.distance
        """
        return self._distance

    @property
    def signal_quality(self) -> float:
        """The quality of the detected object.

        The proximity sensor detects obstacles within a given field of view,
        this value represents the likelihood of the reported distance being
        a solid surface.

        .. code-block:: python

           signal_quality = robot.proximity.last_sensor_reading.signal_quality
        """
        return self._signal_quality

    @property
    def is_in_valid_range(self) -> bool:
        """Whether or not the engine considers the detected signal is close enough
        to be considered useful. Past a certain threshold, distance readings
        become unreliable.

        .. code-block:: python

           is_in_valid_range = robot.proximity.last_sensor_reading.is_in_valid_range
        """
        return self._is_in_valid_range

    @property
    def is_valid_signal_quality(self) -> bool:
        """Whether the engine considers the detected signal to be reliable enough
        to be considered an object in proximity.

        .. code-block:: python

           is_valid_signal_quality = robot.proximity.last_sensor_reading.is_valid_signal_quality
        """
        return self._is_valid_signal_quality

    @property
    def is_lift_in_fov(self) -> bool:
        """Whether Vector's lift is blocking the time-of-flight sensor. While
        the lift will send clear proximity signals, it's not useful for object
        detection.

        .. code-block:: python

           is_lift_in_fov = robot.proximity.last_sensor_reading.is_lift_in_fov
        """
        return self._is_lift_in_fov

    @property
    def is_too_pitched(self) -> bool:
        """Whether the engine considers the robot to be tilted too much up or down
        for the time-of-flight data to usefully describe obstacles in the driving
        plane.

        .. code-block:: python

           is_too_pitched = robot.proximity.last_sensor_reading.is_too_pitched
        """
        return self._is_too_pitched

    def __init__(self, proto_data):
        self._distance = util.Distance(distance_mm=proto_data.distance_mm)
        self._signal_quality = proto_data.signal_quality
        self._is_in_valid_range = proto_data.is_in_valid_range
        self._is_valid_signal_quality = proto_data.is_valid_signal_quality
        self._is_lift_in_fov = proto_data.is_lift_in_fov
        self._is_too_pitched = proto_data.is_too_pitched

    @property
    def is_valid(self) -> bool:
        """Comprehensive judgment of whether the reported distance is useful for
        object proximity detection.

        .. code-block:: python

           is_valid = robot.proximity.last_sensor_reading.is_valid
        """
        return self._is_in_valid_range and self._is_valid_signal_quality and not self._is_lift_in_fov and not self._is_too_pitched


class ProximityComponent(util.Component):
    """Maintains the most recent proximity sensor data

    This will be updated with every broadcast RobotState, and can be queried at any time. Two sensor readings are made available:
        - the most recent data from the robot
        - the most recent data which was considered valid by the engine for usage

    An example of how to extract sensor data:

      .. code-block:: python

         with anki_vector.Robot("my_robot_serial_number") as robot:
             proximity_data = robot.proximity.last_sensor_reading
             if proximity_data is not None:
                 print('Proximity distance: {0}, engine considers useful: {1}'.format(proximity_data.distance, proximity_data.is_valid))
    """

    def __init__(self, robot):
        super().__init__(robot)
        self._last_valid_sensor_reading = None
        self._last_sensor_reading = None

    @property
    def last_sensor_reading(self) -> ProximitySensorData:
        """:class:`anki_vector.proximity.ProximitySensorData`: The last reported sensor data.

        .. code-block:: python

           last_sensor_reading = robot.proximity.last_sensor_reading
        """
        return self._last_sensor_reading

    @property
    def last_valid_sensor_reading(self) -> ProximitySensorData:
        """:class:`anki_vector.proximity.ProximitySensorData`: The last reported sensor data
        which is considered useful for object detection.

        .. code-block:: python

           last_valid_sensor_reading = robot.proximity.last_valid_sensor_reading
        """
        return self._last_valid_sensor_reading

    # TODO Should this be private? Otherwise needs docstring, sample code
    def on_proximity_update(self, prox_data: ProximitySensorData):
        self._last_sensor_reading = ProximitySensorData(prox_data)
        if self._last_sensor_reading.is_valid:
            self._last_valid_sensor_reading = self._last_sensor_reading
