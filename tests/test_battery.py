#!/usr/bin/env python3

"""
Prints out the battery voltage on the robot & cube.
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import anki_vector  # pylint: disable=wrong-import-position


def main():
    args = anki_vector.util.parse_command_args()

    print("------ begin testing battery state ------")

    battery_state = None
    with anki_vector.Robot(args.serial) as robot:
        battery_state = robot.get_battery_state()

    if battery_state:
        print("Robot Battery Voltage: {0}".format(battery_state.battery_volts))

        if battery_state.cube_battery:
            cube_state = battery_state.cube_battery
            print("Cube [{0}] Battery Voltage: {1} as of {2} seconds ago".format(
                cube_state.factory_id,
                cube_state.battery_volts,
                int(cube_state.time_since_last_reading_sec)))

    print("------ end testing battery state ------")


if __name__ == "__main__":
    main()
