# Copyright (c) 2019 Anki, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the file LICENSE.txt or at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Data generation script to build a training and test dataset.

A sample dataset is included in the project ("dataset.zip"). Unzip the folder and use the
--dataset_root_folder option to specify the file path and expand this dataset.

Use this script to build/expand the data needed to train the sign language recognition system.
"""

from concurrent.futures import CancelledError
import curses
import json
import os
import platform
from pathlib import Path
import random
import sys
import tempfile
import time

try:
    import numpy as np
except ImportError as exc:
    sys.exit("Cannot import numpy: Do `pip3 install numpy` to install")

try:
    from PIL import Image
except ImportError:
    sys.exit("Cannot import from PIL: Do `pip3 install --user Pillow` to install")

try:
    from scipy import ndimage
except ImportError as exc:
    sys.exit("Cannot import scipy: Do `pip3 install scipy` to install")

import anki_vector
import util


def data_capture(camera: anki_vector.camera.CameraComponent, stats: dict, root_folder: str) -> None:
    """Build an image dataset using the camera feed from Vector.

    This method uses an image from the camera and generates a multiplier number of images by
    rotating the original image. The keystroke used to initiate the image capture and processing
    is used to label the image.
    """

    try:
        # TODO: curses works well with Mac OS and Linux, explore msvcrt for Windows
        terminal = curses.initscr()
        curses.cbreak()
        curses.noecho()
        terminal.nodelay(True)

        # The number of images to generate using the image captured as a seed
        image_multiplier = 10
        # The maximum amount of rotation by which to rotate the original image to generate more images
        min_rotation = -10
        max_rotation = 10

        print("------ capturing hand signs dataset, press ctrl+c to exit ------")
        while True:
            key = terminal.getch()
            if (ord("a") <= key <= ord("z")) or (key == ord(" ")):

                # Represents background images, filenames are switched to be prefixed with "background" instead of " "
                if key == ord(" "):
                    key = "background"
                else:
                    key = chr(key)

                # Pull image from camera
                original_image = camera.latest_image.raw_image
                if original_image:
                    # Convert image to black and white
                    black_white_image = original_image.convert("L")
                    rotation_axes = [1, 1, 0]

                    # Generate more images with random rotation
                    for rotation in random.sample(range(min_rotation, max_rotation), image_multiplier):
                        # Randomly define which axis to rotate the image by
                        random.shuffle(rotation_axes)
                        x_axis_rotation_enabled, y_axis_rotation_enabled = rotation_axes[:2]
                        rotated_image_array = ndimage.rotate(black_white_image,
                                                             rotation,
                                                             axes=(x_axis_rotation_enabled, y_axis_rotation_enabled),
                                                             reshape=False)

                        # Convert to a 200*200 image
                        rotated_image = Image.fromarray(rotated_image_array)
                        cropped_image = util.crop_image(rotated_image, util.NetworkConstants.IMAGE_WIDTH, util.NetworkConstants.IMAGE_HEIGHT)

                        # Save the image
                        image_filename = key + "_" + str(stats.get(key, 0)) + ".png"
                        stats[key] = stats.get(key, 0) + 1
                        cropped_image.save(os.path.join(root_folder, image_filename))

                    # Character
                    print(f"Recorded images for {key}\n\r")
    except (CancelledError, KeyboardInterrupt):
        pass
    finally:
        curses.nocbreak()
        curses.echo()
        curses.endwin()


def main():
    stats = {}

    args = util.parse_command_args()
    if not args.dataset_root_folder:
        args.dataset_root_folder = str(Path(tempfile.gettempdir(), "dataset"))
        print(f"No data folder defined, saving to {args.dataset_root_folder}")
        os.makedirs(args.dataset_root_folder, exist_ok=True)
        time.sleep(2)

    # Read existing stats or set new stats up
    if os.path.isfile(os.path.join(args.dataset_root_folder, "stats.json")):
        with open(os.path.join(args.dataset_root_folder, "stats.json"), "r") as stats_file:
            stats = json.load(stats_file)
    else:
        stats = {}

    with anki_vector.Robot(args.serial) as robot:
        try:
            # Add a rectangular overlay describing the portion of image that is used after cropping.
            # TODO: The rectangle overlay should feed in a full rect, not just a size
            frame_of_interest = anki_vector.util.RectangleOverlay(util.NetworkConstants.IMAGE_WIDTH, util.NetworkConstants.IMAGE_HEIGHT)
            robot.viewer.overlays.append(frame_of_interest)
            robot.camera.init_camera_feed()
            robot.viewer.show()
            data_capture(robot.camera, stats, args.dataset_root_folder)
        finally:
            with open(os.path.join(args.dataset_root_folder, "stats.json"), "w") as stats_file:
                # Save the stats of expanded dataset
                json.dump(stats, stats_file)

            # Reset the terminal
            print(f"Data collection done!\nData stored in {args.dataset_root_folder}")


if __name__ == '__main__':
    main()
