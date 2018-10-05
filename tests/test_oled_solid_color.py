#!/usr/bin/env python3
"""
This test cycles Vector's Screen 4 times between solid colors:
yellow-orange, green, azure, and purple

NOTE: Currently, Vector's default eye animations will override the solid colors, so
      when testing the colors will flicker back and forth between the eyes and color.
"""

# @TODO: Once behaviors are worked out, we should be sending some kind of "stop default eye stuff"
#        message at the start of this program, and a complimentary "turn back on default eye stuff"
#        message when it stops.

import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import anki_vector  # pylint: disable=wrong-import-position


def main():
    """main execution"""
    args = anki_vector.util.parse_command_args()

    with anki_vector.Robot(args.serial) as robot:
        print("------ begin testing screen ------")

        for _ in range(4):
            robot.screen.set_screen_to_color(anki_vector.color.Color(rgb=[255, 128, 0]), duration_sec=1.0)
            time.sleep(1.0)
            robot.screen.set_screen_to_color(anki_vector.color.Color(rgb=[48, 192, 48]), duration_sec=1.0)
            time.sleep(1.0)
            robot.screen.set_screen_to_color(anki_vector.color.Color(rgb=[0, 128, 255]), duration_sec=1.0)
            time.sleep(1.0)
            robot.screen.set_screen_to_color(anki_vector.color.Color(rgb=[96, 0, 192]), duration_sec=1.0)
            time.sleep(1.0)

        print("------ finish testing screen ------")


if __name__ == "__main__":
    main()
