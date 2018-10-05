#!/usr/bin/env python3

"""
Test the motors for the head and lift
"""

import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import anki_vector  # pylint: disable=wrong-import-position


def main():
    """main execution"""
    args = anki_vector.util.parse_command_args()

    print("------ begin testing head and lift motors ------")
    with anki_vector.Robot(args.serial) as robot:
        # move head upward for a second at an arbitrarily selected speed
        robot.motors.set_head_motor(5.0)
        time.sleep(1.0)
        # move head downward for a second at an arbitrarily selected speed
        robot.motors.set_head_motor(-5.0)
        time.sleep(1.0)
        # stop head movement
        robot.motors.set_head_motor(0)
        # move lift upward for a second at an arbitrarily selected speed
        robot.motors.set_lift_motor(5.0)
        time.sleep(1.0)
        # move lift downward for a second at an arbitrarily selected speed
        robot.motors.set_lift_motor(-5.0)
        time.sleep(1.0)
        # stop lift movement
        robot.motors.set_lift_motor(0.0)
    print("------ finished testing head and lift motors ------")


if __name__ == "__main__":
    main()
