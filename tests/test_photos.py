#!/usr/bin/env python3

"""
Grabs the pictures off of Vector and open them via PIL

This assumes the user has taken some pictures on their robot
using the "Hey Vector, Take a Selfie"-style voice command.
"""

import io
import os
import sys

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
        print("------ begin testing ------")

        for photo in robot.photos.photo_info:
            print(f"Opening photo {photo.photo_id}")
            val = robot.photos.get_photo(photo.photo_id)
            image = Image.open(io.BytesIO(val.image))
            image.show()

        print("------ finish testing ------")


if __name__ == "__main__":
    main()
