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
.. _status:

Robot Status class and exposed properties for Vector's various states.

The :class:`RobotStatus` class in this module exposes properties
about the robot status like :py:attr:`is_charging <RobotStatus.is_charging>`,
:py:attr:`is_being_held <RobotStatus.is_being_held>`, etc.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['ROBOT_STATUS_NONE', 'ROBOT_STATUS_ARE_MOTORS_MOVING', 'ROBOT_STATUS_IS_CARRYING_BLOCK',
           'ROBOT_STATUS_IS_DOCKING_TO_MARKER', 'ROBOT_STATUS_IS_PICKED_UP', 'ROBOT_STATUS_IS_BUTTON_PRESSED',
           'ROBOT_STATUS_IS_FALLING', 'ROBOT_STATUS_IS_ANIMATING', 'ROBOT_STATUS_IS_PATHING',
           'ROBOT_STATUS_LIFT_IN_POS', 'ROBOT_STATUS_HEAD_IN_POS', 'ROBOT_STATUS_CALM_POWER_MODE',
           'ROBOT_STATUS_IS_ON_CHARGER', 'ROBOT_STATUS_IS_CHARGING', 'ROBOT_STATUS_CLIFF_DETECTED',
           'ROBOT_STATUS_ARE_WHEELS_MOVING', 'ROBOT_STATUS_IS_BEING_HELD', 'ROBOT_STATUS_IS_ROBOT_MOVING',
           'RobotStatus']

from . import util
from .messaging import protocol

ROBOT_STATUS_NONE = protocol.RobotStatus.Value("ROBOT_STATUS_NONE")
ROBOT_STATUS_ARE_MOTORS_MOVING = protocol.RobotStatus.Value("ROBOT_STATUS_IS_MOVING")
ROBOT_STATUS_IS_CARRYING_BLOCK = protocol.RobotStatus.Value("ROBOT_STATUS_IS_CARRYING_BLOCK")
ROBOT_STATUS_IS_DOCKING_TO_MARKER = protocol.RobotStatus.Value("ROBOT_STATUS_IS_PICKING_OR_PLACING")
ROBOT_STATUS_IS_PICKED_UP = protocol.RobotStatus.Value("ROBOT_STATUS_IS_PICKED_UP")
ROBOT_STATUS_IS_BUTTON_PRESSED = protocol.RobotStatus.Value("ROBOT_STATUS_IS_BUTTON_PRESSED")
ROBOT_STATUS_IS_FALLING = protocol.RobotStatus.Value("ROBOT_STATUS_IS_FALLING")
ROBOT_STATUS_IS_ANIMATING = protocol.RobotStatus.Value("ROBOT_STATUS_IS_ANIMATING")
ROBOT_STATUS_IS_PATHING = protocol.RobotStatus.Value("ROBOT_STATUS_IS_PATHING")
ROBOT_STATUS_LIFT_IN_POS = protocol.RobotStatus.Value("ROBOT_STATUS_LIFT_IN_POS")
ROBOT_STATUS_HEAD_IN_POS = protocol.RobotStatus.Value("ROBOT_STATUS_HEAD_IN_POS")
ROBOT_STATUS_CALM_POWER_MODE = protocol.RobotStatus.Value("ROBOT_STATUS_CALM_POWER_MODE")
ROBOT_STATUS_IS_ON_CHARGER = protocol.RobotStatus.Value("ROBOT_STATUS_IS_ON_CHARGER")
ROBOT_STATUS_IS_CHARGING = protocol.RobotStatus.Value("ROBOT_STATUS_IS_CHARGING")
ROBOT_STATUS_CLIFF_DETECTED = protocol.RobotStatus.Value("ROBOT_STATUS_CLIFF_DETECTED")
ROBOT_STATUS_ARE_WHEELS_MOVING = protocol.RobotStatus.Value("ROBOT_STATUS_ARE_WHEELS_MOVING")
ROBOT_STATUS_IS_BEING_HELD = protocol.RobotStatus.Value("ROBOT_STATUS_IS_BEING_HELD")
ROBOT_STATUS_IS_ROBOT_MOVING = protocol.RobotStatus.Value("ROBOT_STATUS_IS_MOTION_DETECTED")


class RobotStatus():
    """A class to expose various status properties of the robot."""

    def __init__(self):
        # Default robot status
        self._status: int = None

    def set(self, status: int):
        self._status = status

    @util.block_while_none()
    def __get(self) -> int:
        return self._status

    @property
    def are_motors_moving(self) -> bool:
        """True if Vector is currently moving any of his motors (head, arm or
        wheels/treads).

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                if robot.status.are_motors_moving:
                    print("Vector is moving.")
        """
        return (self.__get() & ROBOT_STATUS_ARE_MOTORS_MOVING) != 0

    @property
    def is_carrying_block(self) -> bool:
        """True if Vector is currently carrying a block.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                if robot.status.is_carrying_block:
                    print("Vector is carrying his block.")
        """
        return (self.__get() & ROBOT_STATUS_IS_CARRYING_BLOCK) != 0

    @property
    def is_docking_to_marker(self) -> bool:
        """True if Vector has seen a marker and is actively heading toward it
        (for example his charger or cube).

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                if robot.status.is_docking_to_marker:
                    print("Vector has found a marker and is docking to it.")
        """
        return (self.__get() & ROBOT_STATUS_IS_DOCKING_TO_MARKER) != 0

    @property
    def is_picked_up(self) -> bool:
        """True if Vector is currently picked up (in the air).

        If :py:attr:`is_being_held` is true, then :py:attr:`is_picked_up` is always True.

        :py:attr:`is_picked_up` uses the IMU data to determine if the robot is not on a stable surface with his treads down.
        If the robot is on its side, :py:attr:`is_picked_up` is True.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                if robot.status.is_picked_up:
                    print("Vector is picked up.")
        """
        return (self.__get() & ROBOT_STATUS_IS_PICKED_UP) != 0

    @property
    def is_button_pressed(self) -> bool:
        """True if Vector's button is pressed.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                if robot.status.is_button_pressed:
                    print("Vector's button was button pressed.")
        """
        return (self.__get() & ROBOT_STATUS_IS_BUTTON_PRESSED) != 0

    @property
    def is_falling(self) -> bool:
        """True if Vector is currently falling.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                if robot.status.is_falling:
                    print("Vector is falling.")
        """
        return (self.__get() & ROBOT_STATUS_IS_FALLING) != 0

    @property
    def is_animating(self) -> bool:
        """True if Vector is currently playing an animation.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                if robot.status.is_animating:
                    print("Vector is animating.")
        """
        return (self.__get() & ROBOT_STATUS_IS_ANIMATING) != 0

    @property
    def is_pathing(self) -> bool:
        """True if Vector is currently traversing a path.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                if robot.status.is_pathing:
                    print("Vector is traversing a path.")
        """
        return (self.__get() & ROBOT_STATUS_IS_PATHING) != 0

    @property
    def is_lift_in_pos(self) -> bool:
        """True if Vector's arm is in the desired position (False if still
        trying to move it there).

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                if robot.status.is_lift_in_pos:
                    print("Vector's arm is in position.")
        """
        return (self.__get() & ROBOT_STATUS_LIFT_IN_POS) != 0

    @property
    def is_head_in_pos(self) -> bool:
        """True if Vector's head is in the desired position (False if still
        trying to move there).

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                if robot.status.is_head_in_pos:
                    print("Vector's head is in position.")
        """
        return (self.__get() & ROBOT_STATUS_HEAD_IN_POS) != 0

    @property
    def is_in_calm_power_mode(self) -> bool:
        """True if Vector is in calm power mode.  Calm power mode is generally
        when Vector is sleeping or charging.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                if robot.status.is_in_calm_power_mode:
                    print("Vector is in calm power mode.")
        """
        return (self.__get() & ROBOT_STATUS_CALM_POWER_MODE) != 0

    @property
    def is_on_charger(self) -> bool:
        """True if Vector is currently on the charger.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                if robot.status.is_on_charger:
                    print("Vector is on the charger.")
        """
        return (self.__get() & ROBOT_STATUS_IS_ON_CHARGER) != 0

    @property
    def is_charging(self) -> bool:
        """True if Vector is currently charging.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                if robot.status.is_charging:
                    print("Vector is currently charging.")
        """
        return (self.__get() & ROBOT_STATUS_IS_CHARGING) != 0

    @property
    def is_cliff_detected(self) -> bool:
        """True if Vector detected a cliff using any of his four cliff sensors.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                if robot.status.is_cliff_detected:
                    print("Vector has detected a cliff.")
        """
        return (self.__get() & ROBOT_STATUS_CLIFF_DETECTED) != 0

    @property
    def are_wheels_moving(self) -> bool:
        """True if Vector's wheels/treads are currently moving.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                if robot.status.are_wheels_moving:
                    print("Vector's wheels are moving.")
        """
        return (self.__get() & ROBOT_STATUS_ARE_WHEELS_MOVING) != 0

    @property
    def is_being_held(self) -> bool:
        """True if Vector is being held.

        :py:attr:`is_being_held` uses the IMU to look for tiny motions
        that suggest the robot is actively being held in someone's hand.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                if robot.status.is_being_held:
                    print("Vector is being held.")
        """
        return (self.__get() & ROBOT_STATUS_IS_BEING_HELD) != 0

    @property
    def is_robot_moving(self) -> bool:
        """True if Vector is in motion.  This includes any of his motors
        (head, arm, wheels/tracks) and if he is being lifted, carried,
        or falling.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                if robot.status.is_robot_moving:
                    print("Vector has is in motion.")
        """
        return (self.__get() & ROBOT_STATUS_IS_ROBOT_MOVING) != 0
