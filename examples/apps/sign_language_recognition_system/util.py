# Copyright (c) 2018 Anki, Inc.

"""
Utility functions and classes for the sign language recognition system
"""

import argparse

from anki_vector import util


class NetworkConstants():  # pylint: disable=too-few-public-methods
    """Constant values used as image and network parameters."""

    # Width of images passed to the network
    IMAGE_WIDTH: int = 200

    # Height of images passed to the network
    IMAGE_HEIGHT: int = 200

    # TODO: Change to 27 (26 alphabets + 1 background image).
    # Currently set to 2 alphabet images and 1 background image class
    # Number of classes that the network can categorize
    NUM_CLASSES: int = 3

    # The fraction of images passed to the network during training that should
    # be used as a validation set. Range: 0 to 1
    VALIDATION_SPLIT: float = 0.1

    # The fraction of images passed to the network during training that should
    # be used as a test set. Range: 0 to 1
    TEST_SPLIT: float = 0.2


def parse_command_args():
    """Parses command line args"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--predict", action="store_true")
    parser.add_argument("--dataset_root_folder", nargs='?', default=None)
    parser.add_argument("--model_config", nargs='?', default=None)
    parser.add_argument("--model_weights", nargs='?', default=None)

    return util.parse_test_args(parser)


def crop_image(image, target_width, target_height):
    """Crops an image to the target width and height"""
    image_width, image_height = image.shape

    remaining_width = image_width - target_width
    remaining_height = image_height - target_height

    image = image[(remaining_width // 2):(image_width - (remaining_width // 2)), (remaining_height // 2):(image_height - (remaining_height // 2))]
    return image
