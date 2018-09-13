#!/usr/bin/env python3

import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import anki_vector  # pylint: disable=wrong-import-position


def main():
    """main execution"""
    args = anki_vector.util.parse_test_args()

    print("------ begin testing backpack light profiles ------")

    with anki_vector.Robot(args.serial, port=args.port) as robot:

        # Set backpack to White Lights using the max brightness profile for 4 seconds
        robot.backpack.set_all_backpack_lights(anki_vector.lights.white_light, anki_vector.lights.MAX_COLOR_PROFILE)
        time.sleep(4)

        # Set backpack to White Lights using the white balanced profile for 4 seconds
        robot.backpack.set_all_backpack_lights(anki_vector.lights.white_light, anki_vector.lights.WHITE_BALANCED_BACKPACK_PROFILE)
        time.sleep(4)

        # Set backpack to Magenta Lights using the max brightness profile for 4 seconds
        robot.backpack.set_all_backpack_lights(anki_vector.lights.magenta_light, anki_vector.lights.MAX_COLOR_PROFILE)
        time.sleep(4)

        # Set backpack to Magenta Lights using the white balanced profile for 4 seconds
        robot.backpack.set_all_backpack_lights(anki_vector.lights.magenta_light, anki_vector.lights.WHITE_BALANCED_BACKPACK_PROFILE)
        time.sleep(4)

        robot.backpack.set_all_backpack_lights(anki_vector.lights.off_light)

    print("------ end testing backpack light profiles ------")


if __name__ == "__main__":
    main()
