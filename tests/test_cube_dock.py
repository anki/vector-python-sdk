#!/usr/bin/env python3

"""
Test cube docking behavior.

Vector should drive to a seen cube, lining up so that his lift hooks are inserted into
the cube's corners.
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import anki_vector  # pylint: disable=wrong-import-position


def main():
    """main execution"""
    args = anki_vector.util.parse_command_args()

    print("------ begin cube docking ------")

    docking_result = None
    with anki_vector.Robot(args.serial) as robot:
        robot.world.connect_cube()

        if robot.world.connected_light_cube:
            dock_response = robot.behavior.dock_with_cube(robot.world.connected_light_cube)
            docking_result = dock_response.result

    if docking_result:
        if docking_result.code == anki_vector.messaging.protocol.ActionResult.ACTION_RESULT_SUCCESS:  # pylint: disable=no-member
            print("------ finish cube docking ------")
        else:
            print("------ cube docking failed with code {0} ({1}) ------".format(str(docking_result).rstrip('\n\r'), docking_result.code))
    else:
        print("------ skipping cube docking, could not connect to robot ------")


if __name__ == "__main__":
    main()
