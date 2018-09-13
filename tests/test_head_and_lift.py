#!/usr/bin/env python3

"""
Test the setting angle and height for the head and lift respectively
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import anki_vector  # pylint: disable=wrong-import-position
from anki_vector.util import degrees  # pylint: disable=wrong-import-position


def main():
    """main execution"""
    args = anki_vector.util.parse_test_args()

    print("------ begin testing head and lift actions ------")

    # The robot shall lower and raise his head and lift
    with anki_vector.Robot(args.serial, port=args.port) as robot:
        robot.behavior.set_head_angle(degrees(-50.0))

        robot.behavior.set_head_angle(degrees(50.0))

        robot.behavior.set_head_angle(degrees(0.0))

        robot.behavior.set_lift_height(100.0)

        robot.behavior.set_lift_height(0.0)

    print("------ finished testing head and lift actions ------")


if __name__ == "__main__":
    main()
