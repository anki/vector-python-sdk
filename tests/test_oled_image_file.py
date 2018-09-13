#!/usr/bin/env python3

"""
Test showing solid image of Cozmo on Vector's face for 4 seconds
"""

import os
import sys
import time

try:
    from PIL import Image
except ImportError:
    sys.exit("Cannot import from PIL: Do `pip3 install --user Pillow` to install")

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import anki_vector  # pylint: disable=wrong-import-position


def main():
    """main execution"""
    args = anki_vector.util.parse_test_args()

    with anki_vector.Robot(args.serial, port=args.port) as robot:
        print("------ begin testing screen ------")

        current_directory = os.path.dirname(os.path.realpath(__file__))
        image_path = os.path.join(current_directory, "test_assets", "cozmo_image.jpg")

        image_file = Image.open(image_path)
        screen_data = anki_vector.screen.convert_image_to_screen_data(image_file)
        robot.screen.set_screen_with_image_data(screen_data, 4.0)
        time.sleep(5)  # TODO: make set_screen_with_image_data a blocking call until the time passes

        print("------ finish testing screen ------")


if __name__ == "__main__":
    main()
