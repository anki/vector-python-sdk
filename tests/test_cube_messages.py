#!/usr/bin/env python3

"""
Test cube connection interactions
"""

import os
import sys

import utilities
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import anki_vector  # pylint: disable=wrong-import-position


def main():
    """main execution"""
    args = anki_vector.util.parse_command_args()

    print("------ begin cube interactions ------")

    # The robot shall drive straight, stop and then turn around
    with anki_vector.Robot(args.serial) as robot:
        print("disconnecting from any connected cube...")
        robot.world.disconnect_cube()

        loop = robot.loop
        loop.run_until_complete(utilities.wait_async(2.0))

        print("connect to a cube...")
        connectionResult = robot.world.connect_cube()
        print(connectionResult)

        connected_cube = robot.world.connected_light_cube
        if connected_cube:
            print("connected to cube {0}, clearing preferred cube for 1 second...".format(connected_cube.factory_id))
            robot.world.forget_preferred_cube()
            loop.run_until_complete(utilities.wait_async(1.0))

            print("resetting preferred cube to the one we connected to...")
            robot.world.set_preferred_cube(connected_cube.factory_id)
            loop.run_until_complete(utilities.wait_async(1.0))

            robot.world.flash_cube_lights()

        print("for the next 8 second, please tap, move, or allow Vector to observe the cube, events will be logged to console.")
        for _ in range(16):
            if connected_cube:
                print(connected_cube)
                print("last observed timestamp: " + str(connected_cube.last_observed_time) + ", robot timestamp: " + str(connected_cube.last_observed_robot_timestamp))
            loop.run_until_complete(utilities.wait_async(0.5))

        print("disconnecting...")
        robot.world.disconnect_cube()
        loop.run_until_complete(utilities.wait_async(1.0))

    print("------ finish cube interactions ------")


if __name__ == "__main__":
    main()
