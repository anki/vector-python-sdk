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

"""Make Vector drive to a cliff and back up.

Place the robot about a foot from a "cliff" (such as a tabletop edge),
then run this script.

This tutorial is an advanced example that shows the SDK's integration
with the Vector behavior system.

The Vector behavior system uses an order of prioritizations to determine
what the robot will do next. The highest priorities in the behavior
system including the following:
* When Vector reaches a cliff, he will back up to avoid falling.
* When Vector is low on battery, he will start searching for his charger
and self-dock.

When the SDK is running at a lower priority level than high priorities
like cliff and low battery, an SDK program can lose its ability to
control the robot when a cliff if reached or when battery is low.

This example shows how, after reaching a cliff, the SDK program can
re-request control so it can continue controlling the robot after
reaching the cliff.
"""

import anki_vector
from anki_vector.util import distance_mm, speed_mmps


def main():
    args = anki_vector.util.parse_test_args()

    with anki_vector.Robot(args.serial, port=args.port) as robot:
        print("Vector SDK has behavior control...")
        robot.behavior.drive_off_charger()

        print("Drive Vector straight until he reaches cliff...")
        robot.behavior.drive_straight(distance_mm(500), speed_mmps(100))

        robot.conn.control_lost_event.wait()

        print("Lost SDK behavior control. Request SDK behavior control again...")
        robot.conn.request_control()

        print("Drive Vector backward away from the cliff...")
        robot.behavior.drive_straight(distance_mm(-200), speed_mmps(100))


if __name__ == "__main__":
    main()
