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

"""Utility functions and classes for the sign language recognition system."""

import argparse

from anki_vector import util

try:
    from PIL import Image
except ImportError:
    sys.exit("Cannot import from PIL: Do `pip3 install --user Pillow` to install")


class NetworkConstants():  # pylint: disable=too-few-public-methods
    """Constant values used as image and network parameters."""

    # Width of images passed to the network
    IMAGE_WIDTH: int = 200

    # Height of images passed to the network
    IMAGE_HEIGHT: int = 200

    # Currently set to 2 alphabet images and 1 background image class
    # Number of classes that the network can categorize
    NUM_CLASSES: int = 27

    # The fraction of images passed to the network during training that should
    # be used as a validation set. Range: 0 to 1
    VALIDATION_SPLIT: float = 0.1

    # The fraction of images passed to the network during training that should
    # be used as a test set. Range: 0 to 1
    TEST_SPLIT: float = 0.2

    # Number of epochs on which to train the network
    EPOCHS: int = 5


def parse_command_args():
    """Parses command line args"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--predict", action="store_true")
    parser.add_argument("--dataset_root_folder", nargs='?', default=None)
    parser.add_argument("--model_config", nargs='?', default=None)
    parser.add_argument("--model_weights", nargs='?', default=None)

    return util.parse_command_args(parser)


def crop_image(image: Image.Image, target_width: int, target_height: int) -> Image.Image:
    """Crops an image to the target width and height"""
    image_width, image_height = image.size

    remaining_width = image_width - target_width
    remaining_height = image_height - target_height

    return image.crop(((remaining_width // 2),
                       (remaining_height // 2),
                       (image_width - (remaining_width // 2)),
                       (image_height - (remaining_height // 2))))
