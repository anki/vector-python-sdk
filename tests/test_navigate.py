#!/usr/bin/env python3

"""
Test navigating to a pose
"""

import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import anki_vector  # pylint: disable=wrong-import-position


def main():
    """main execution"""
    args = anki_vector.util.parse_command_args()

    print("------ begin testing go to pose ------")

    # The robot should go to given pose
    with anki_vector.Robot(args.serial) as robot:

        pose = anki_vector.util.Pose(x=50, y=0, z=0, angle_z=anki_vector.util.Angle(degrees=0))
        robot.behavior.go_to_pose(pose)
        # Permit enough time to pass to reach required pose
        time.sleep(5)

        pose = anki_vector.util.Pose(x=0, y=50, z=0, angle_z=anki_vector.util.Angle(degrees=90))
        # Use a custom profile to change specs
        robot.behavior.motion_profile_map = {"speed_mmps": 500.0}
        robot.behavior.go_to_pose(pose)
        # Permit enough to pass before the SDK behavior is deactivated
        time.sleep(5)

    print("------ finished testing go to pose ------")


if __name__ == '__main__':
    main()
