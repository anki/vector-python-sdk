#!/usr/bin/env python3

"""
Test driving on and off charger
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import anki_vector  # pylint: disable=wrong-import-position


def main():
    """main execution"""
    args = anki_vector.util.parse_command_args()

    with anki_vector.Robot(args.serial) as robot:
        print("------ begin testing drive on charger ------")
        result = robot.behavior.drive_on_charger()
        print("------ finish testing drive on charger. result: " + str(result))

        print("------ begin testing drive off charger ------")
        result = robot.behavior.drive_off_charger()
        print("------ finish testing drive off charger. result: " + str(result))


if __name__ == '__main__':
    main()
