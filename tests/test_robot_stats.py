#!/usr/bin/env python3

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import anki_vector  # pylint: disable=wrong-import-position


def main():
    """main execution"""
    args = anki_vector.util.parse_command_args()

    print("------ begin testing fetching robot stats ------")

    # Fetch robot stats
    with anki_vector.Robot(args.serial) as robot:
        robot.get_battery_state()  # Fetch the battery level
        robot.get_version_state()  # Fetch the os version and engine build version
        robot.get_network_state()  # Fetch the network stats

    print("------ finished testing fetching robot stats ------")


if __name__ == "__main__":
    main()
