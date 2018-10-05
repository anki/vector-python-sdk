#!/usr/bin/env python3

"""
test_drive
"""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import anki_vector  # pylint: disable=wrong-import-position
from anki_vector.util import degrees, distance_mm, speed_mmps  # pylint: disable=wrong-import-position


def main():
    """main execution"""
    args = anki_vector.util.parse_command_args()

    print("------ begin testing driving along a straight path and turning in place ------")

    # The robot shall drive straight, stop and then turn around
    with anki_vector.Robot(args.serial) as robot:
        robot.behavior.drive_straight(distance_mm(200), speed_mmps(50))

        robot.behavior.turn_in_place(degrees(180))

    print("------ finished testing driving along a straight path and turning in place ------")


if __name__ == "__main__":
    main()
