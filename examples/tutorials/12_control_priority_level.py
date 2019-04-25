#!/usr/bin/env python3

# Copyright (c) 2019 Anki, Inc.
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

"""Vector maintains SDK behavior control after being picked up

During normal operation, SDK programs cannot maintain control over Vector
when he is at a cliff, stuck on an edge or obstacle, tilted or inclined,
picked up, in darkness, etc.

This script demonstrates how to use the highest level SDK behavior control
ControlPriorityLevel.OVERRIDE_BEHAVIORS_PRIORITY to make Vector perform
actions that normally take priority over the SDK. These commands will not
succeed at ControlPriorityLevel.DEFAULT.
"""

import sys
import time
import anki_vector
from anki_vector.connection import ControlPriorityLevel


def main():
    args = anki_vector.util.parse_command_args()
    with anki_vector.Robot(args.serial, behavior_control_level=ControlPriorityLevel.OVERRIDE_BEHAVIORS_PRIORITY) as robot:
        robot.behavior.say_text("Pick me up!")
        pickup_countdown = 20

        print("------ waiting for Vector to be picked up, press ctrl+c to exit early ------")

        try:
            while not robot.status.is_picked_up and pickup_countdown:
                time.sleep(0.5)
                pickup_countdown -= 1

            if not pickup_countdown:
                print("Did not get picked up")
                sys.exit()

            print("Vector is picked up...")
            robot.behavior.say_text("Hold on tight")
            print("Setting wheel motors...")
            robot.motors.set_wheel_motors(75, -75)
            time.sleep(0.5)
            robot.motors.set_wheel_motors(-75, 75)
            time.sleep(0.5)
            robot.motors.set_wheel_motors(0, 0)

        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
