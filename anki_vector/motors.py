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
Control the motors of Vector.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['MotorComponent']

from . import sync, util
from .messaging import protocol


class MotorComponent(util.Component):
    """Controls the low-level motor functions."""
    @sync.Synchronizer.wrap
    async def set_wheel_motors(self,
                               left_wheel_speed: float,
                               right_wheel_speed: float,
                               left_wheel_accel: float = 0.0,
                               right_wheel_accel: float = 0.0):
        '''Tell Vector to move his wheels / treads at a given speed.

        The wheels will continue to move at that speed until commanded to drive
        at a new speed.

        To unlock the wheel track, call `set_wheel_motors(0, 0)`.

        .. testcode::

            import anki_vector

            with anki_vector.Robot("my_robot_serial_number") as robot:
                robot.motors.set_wheel_motors(25, 50)

        :param left_wheel_speed: Speed of the left tread (in millimeters per second).
        :param right_wheel_speed: Speed of the right tread (in millimeters per second).
        :param left_wheel_accel: Acceleration of left tread (in millimeters per second squared)
                            ``None`` value defaults this to the same as l_wheel_speed.
        :param right_wheel_accel: Acceleration of right tread (in millimeters per second squared)
                            ``None`` value defaults this to the same as r_wheel_speed.
        '''
        motors = protocol.DriveWheelsRequest(left_wheel_mmps=left_wheel_speed,
                                             right_wheel_mmps=right_wheel_speed,
                                             left_wheel_mmps2=left_wheel_accel,
                                             right_wheel_mmps2=right_wheel_accel)
        return await self.grpc_interface.DriveWheels(motors)

    @sync.Synchronizer.wrap
    async def set_head_motor(self,
                             speed: float):
        '''Tell Vector's head motor to move with a certain speed.

        Positive speed for up, negative speed for down. Measured in radians per second.

        To unlock the head track, call `set_head_motor(0)`.

        .. testcode::

            import anki_vector

            with anki_vector.Robot("my_robot_serial_number") as robot:
                robot.motors.set_head_motor(-5.0)

        :param speed: Motor speed for Vector's head, measured in radians per second.
        '''
        set_head_request = protocol.MoveHeadRequest(speed_rad_per_sec=speed)
        return await self.grpc_interface.MoveHead(set_head_request)

    @sync.Synchronizer.wrap
    async def set_lift_motor(self,
                             speed: float):
        '''Tell Vector's lift motor to move with a certain speed.

        Positive speed for up, negative speed for down. Measured in radians per second.

        To unlock the lift track, call `set_lift_motor(0)`.

        .. testcode::

            import anki_vector

            with anki_vector.Robot("my_robot_serial_number") as robot:
                robot.motors.set_lift_motor(-5.0)

        :param speed: Motor speed for Vector's lift, measured in radians per second.
        '''
        set_lift_request = protocol.MoveLiftRequest(speed_rad_per_sec=speed)
        return await self.grpc_interface.MoveLift(set_lift_request)
