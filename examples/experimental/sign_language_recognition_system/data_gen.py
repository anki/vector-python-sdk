#!/usr/bin/env python3

# Copyright (c) 2018 Anki, Inc.

"""
Data generation script to build a training and test dataset.
Use this script to build the data needed to train sign language recognition system.
"""

import asyncio
from concurrent.futures import CancelledError
import curses
import json
import os
import sys
import random

try:
    import cv2
except ImportError as exc:
    sys.exit("Cannot import opencv-python: Do `pip3 install opencv-python` to install")

try:
    from scipy import ndimage
except ImportError as exc:
    sys.exit("Cannot import scipy: Do `pip3 install scipy` to install")

import anki_vector
import util


async def data_capture(camera: anki_vector.camera.CameraComponent, stats: dict, root_folder: str) -> None:
    """Build an image dataset using the camera feed from Vector.

    This method uses an image from the camera and generates a multiplier number of images by
    rotating the original image. The keystroke used to initiate the image capture and processing
    is used to label the image.
    """

    # TODO: curses works well with Mac OS and Linux, explore msvcrt for Windows
    terminal = curses.initscr()
    curses.cbreak()
    curses.noecho()
    terminal.nodelay(True)

    # The number fo images to generate using the image captured as a seed
    image_multiplier = 10
    # The maximum amount of rotation by which to rotate the original image to generate more images
    min_rotation = -10
    max_rotation = 10

    print("------ capturing hand signs dataset, press ctrl+c to exit ------")
    while True:
        key = terminal.getch()
        if (ord("a") <= key <= ord("z")) or (key == ord(" ")):

            # Represents background images, filenames are switched to be prefixed with '_' instead of " "
            if key == ord(" "):
                key = ord("_")

            # Pull image from camera
            original_image = camera.latest_image
            # Convert image to black and white
            original_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)
            images = []
            rotation_axes = [1, 1, 0]

            # Generate more images with random rotation
            for rotation in random.sample(range(min_rotation, max_rotation), image_multiplier):
                # Randomly define which axis to rotate the image by
                random.shuffle(rotation_axes)
                x_axis_rotation_enabled, y_axis_rotation_enabled = rotation_axes[:2]
                image = ndimage.rotate(original_image,
                                       rotation,
                                       axes=(x_axis_rotation_enabled, y_axis_rotation_enabled))
                images.append(image)

            for image in images:
                # Convert to a 200*200 image
                image = util.crop_image(image, util.NetworkConstants.IMAGE_WIDTH, util.NetworkConstants.IMAGE_HEIGHT)

                # Show image for feedback
                cv2.imshow("Latest Image Captured", image)
                cv2.waitKey(1)

                # Save the image
                image_filename = chr(key) + "_" + str(stats.get(chr(key), 0)) + ".png"
                stats[chr(key)] = stats.get(chr(key), 0) + 1
                cv2.imwrite(os.path.join(root_folder, image_filename), image)

                await asyncio.sleep(0.1)

            # Character
            print(f"Recorded images for {chr(key)}")
        await asyncio.sleep(0.1)


def main():
    stats = {}

    args = util.parse_command_args()
    if not args.dataset_root_folder:
        sys.exit("Specify the folder at which to generate data")

    # Read existing stats or set new stats up
    if os.path.isfile(os.path.join(args.dataset_root_folder, "stats.json")):
        with open(os.path.join(args.dataset_root_folder, "stats.json"), "r") as stats_file:
            stats = json.load(stats_file)
    else:
        stats = {}

    with anki_vector.Robot(args.serial, enable_camera_feed=True, show_viewer=True) as robot:
        try:
            # Add a rectangular overlay describing the portion of image that is used after cropping.

            # @TODO: The rectangle overlay should feed in a full rect, not just a size
            frame_of_interest = anki_vector.util.RectangleOverlay(util.NetworkConstants.IMAGE_WIDTH, util.NetworkConstants.IMAGE_HEIGHT)
            robot.viewer.overlays.append(frame_of_interest)
            robot.loop.run_until_complete(data_capture(robot.camera, stats, args.dataset_root_folder))
        except (KeyboardInterrupt, CancelledError):
            with open(os.path.join(args.dataset_root_folder, "stats.json"), "w") as stats_file:
                # Save the stats of expanded dataset
                json.dump(stats, stats_file)

            # Reset the terminal
            curses.nocbreak()
            curses.echo()
            curses.endwin()
            print("Data collection done!")


if __name__ == '__main__':
    main()
