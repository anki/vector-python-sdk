#!/usr/bin/env python3

"""
Test proximity sensor data
"""

import os
import sys
import utilities

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import anki_vector  # pylint: disable=wrong-import-position


def main():
    args = anki_vector.util.parse_command_args()

    print("------ begin testing prox sensor data ------")

    with anki_vector.Robot(args.serial) as robot:
        loop = robot.loop
        for _ in range(30):
            proximity_data = robot.proximity.last_valid_sensor_reading
            if proximity_data is not None:
                print(proximity_data.distance)
            loop.run_until_complete(utilities.wait_async(0.5))

    print("------ finish testing prox sensor data ------")


if __name__ == "__main__":
    main()
