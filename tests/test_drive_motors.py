#!/usr/bin/env python3

"""
Test wheel motor control functions
"""

import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import anki_vector  # pylint: disable=wrong-import-position


def main():
    """main execution"""
    args = anki_vector.util.parse_command_args()

    with anki_vector.Robot(args.serial) as robot:
        # manually drive about 0.1 m forward (100.0 mm/s for 1 sec) with a
        # 100.0 mm/s2 acceleration
        robot.motors.set_wheel_motors(100.0, 100.0, 100.0, 100.0)
        time.sleep(1.0)
        # stop moving
        robot.motors.set_wheel_motors(0, 0)


if __name__ == "__main__":
    main()
