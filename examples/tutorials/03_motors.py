#!/usr/bin/env python3

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

"""Drive Vector's wheels, lift and head motors directly

This is an example of how you can also have low-level control of Vector's motors
(wheels, lift and head) for fine-grained control and ease of controlling
multiple things at once.
"""

import time
import anki_vector


def main():
    args = anki_vector.util.parse_command_args()
    with anki_vector.Robot(args.serial) as robot:
        robot.behavior.drive_off_charger()

        # Tell the head motor to start lowering the head (at 5 radians per second)
        print("Lower Vector's head...")
        robot.motors.set_head_motor(-5.0)

        # Tell the lift motor to start lowering the lift (at 5 radians per second)
        print("Lower Vector's lift...")
        robot.motors.set_lift_motor(-5.0)

        # Tell Vector to drive the left wheel at 25 mmps (millimeters per second),
        # and the right wheel at 50 mmps (so Vector will drive Forwards while also
        # turning to the left
        print("Set Vector's wheel motors...")
        robot.motors.set_wheel_motors(25, 50)

        # wait for 3 seconds (the head, lift and wheels will move while we wait)
        time.sleep(3)

        # Tell the head motor to start raising the head (at 5 radians per second)
        print("Raise Vector's head...")
        robot.motors.set_head_motor(5)

        # Tell the lift motor to start raising the lift (at 5 radians per second)
        print("Raise Vector's lift...")
        robot.motors.set_lift_motor(5)

        # Tell Vector to drive the left wheel at 50 mmps (millimeters per second),
        # and the right wheel at -50 mmps (so Vector will turn in-place to the right)
        print("Set Vector's wheel motors...")
        robot.motors.set_wheel_motors(50, -50)

        # Wait for 3 seconds (the head, lift and wheels will move while we wait)
        time.sleep(3)

        # Stop the motors, which unlocks the tracks
        robot.motors.set_wheel_motors(0, 0)
        robot.motors.set_lift_motor(0)
        robot.motors.set_head_motor(0)


if __name__ == "__main__":
    main()
