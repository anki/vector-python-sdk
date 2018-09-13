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

"""Tell Vector to drive up to a seen cube.

This example demonstrates Vector driving to and docking with a cube, without
picking it up.  Vector will line his lift hooks up with the cube so that they are
inserted into the cube's corners.

You must place a cube in front of Vector so that he can see it.
"""

import anki_vector
from anki_vector.util import degrees


def main():
    args = anki_vector.util.parse_test_args()

    docking_result = None
    with anki_vector.Robot(args.serial, port=args.port) as robot:
        robot.behavior.drive_off_charger()

        # If necessary, Move Vector's Head and Lift down
        robot.behavior.set_head_angle(degrees(-5.0))
        robot.behavior.set_lift_height(0.0)

        robot.world.connect_cube()

        if robot.world.connected_light_cube:
            print("Begin cube docking...")
            # TODO Add num_retries of 3. Observe it actually trying multiple times.
            dock_response = robot.behavior.dock_with_cube(robot.world.connected_light_cube)
            docking_result = dock_response.result

    if docking_result:
        if docking_result.code != anki_vector.messaging.protocol.ActionResult.ACTION_RESULT_SUCCESS:
            print("Cube docking failed with code {0} ({1})".format(str(docking_result).rstrip('\n\r'), docking_result.code))


if __name__ == "__main__":
    main()
