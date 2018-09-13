#!/usr/bin/env python3

import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import anki_vector  # pylint: disable=wrong-import-position


def main():
    """main execution"""
    args = anki_vector.util.parse_test_args()

    print("------ begin testing backpack lights ------")

    with anki_vector.Robot(args.serial, port=args.port) as robot:
        # Set backpack to RGB Lights for 4 seconds
        robot.backpack.set_backpack_lights(anki_vector.lights.blue_light, anki_vector.lights.green_light, anki_vector.lights.red_light)
        time.sleep(4.0)

        # Set backpack to blinking yellow lights for 4 seconds (Warning lights)
        robot.backpack.set_all_backpack_lights(
            anki_vector.lights.Light(on_color=anki_vector.color.yellow,
                                     off_color=anki_vector.color.off,
                                     on_period_ms=100,
                                     off_period_ms=100))
        time.sleep(4.0)

        # Set backpack to different shades of red using int codes for 4 seconds
        robot.backpack.set_backpack_lights(
            anki_vector.lights.Light(anki_vector.color.Color(int_color=0xff0000ff)),
            anki_vector.lights.Light(anki_vector.color.Color(int_color=0x1f0000ff)),
            anki_vector.lights.Light(anki_vector.color.Color(int_color=0x4f0000ff)))
        time.sleep(4.0)

        # Set backpack to some more complex colors using rgb for 4 seconds
        robot.backpack.set_backpack_lights(
            anki_vector.lights.Light(anki_vector.color.Color(rgb=(0, 128, 255))),  # generic enterprise blue
            anki_vector.lights.Light(anki_vector.color.Color(rgb=(192, 96, 48))),  # a beige
            anki_vector.lights.Light(anki_vector.color.Color(rgb=(96, 0, 192))))  # a purple
        time.sleep(4.0)

        # Set backpack lights to fading between red and blue for 4 seconds (Police lights)
        robot.backpack.set_all_backpack_lights(
            anki_vector.lights.Light(on_color=anki_vector.color.red,
                                     off_color=anki_vector.color.blue,
                                     on_period_ms=25,
                                     off_period_ms=25,
                                     transition_on_period_ms=250,
                                     transition_off_period_ms=250))
        time.sleep(4.0)

        # Turn off backpack lights
        robot.backpack.set_all_backpack_lights(anki_vector.lights.off_light)

    print("------ end testing backpack lights ------")


if __name__ == "__main__":
    main()
