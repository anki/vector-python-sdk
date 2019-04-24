#!/usr/bin/env python3

# Copyright (c) 2019 Anki, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the file LICENSE.txt or at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''Demonstrate the manual and auto exposure settings of Vector's camera.

This example demonstrates the use of auto exposure and manual exposure for
Vector's camera. The current camera settings are overlaid onto the camera
viewer window.
'''


import sys
import time

try:
    from PIL import ImageDraw
    import numpy as np
except ImportError:
    sys.exit('run `pip3 install --user Pillow numpy` to run this example')

import anki_vector
from anki_vector import annotate


# Global values to display in the camera viewer window
example_mode = ""


def demo_camera_exposure(robot: anki_vector.Robot):
    """
    Run through camera exposure settings
    """
    global example_mode

    # Ensure camera is in auto exposure mode and demonstrate auto exposure for 5 seconds
    camera = robot.camera
    camera.enable_auto_exposure()
    example_mode = "Auto Exposure"
    time.sleep(5)

    # Demonstrate manual exposure, linearly increasing the exposure time, while
    # keeping the gain fixed at a medium value.
    example_mode = "Manual Exposure - Increasing Exposure, Fixed Gain"
    fixed_gain = (camera.config.min_gain + camera.config.max_gain) * 0.5
    for exposure in range(camera.config.min_exposure_time_ms, camera.config.max_exposure_time_ms+1, 1):
        camera.set_manual_exposure(exposure, fixed_gain)
        time.sleep(0.1)

    # Demonstrate manual exposure, linearly increasing the gain, while keeping
    # the exposure fixed at a relatively low value.
    example_mode = "Manual Exposure - Increasing Gain, Fixed Exposure"
    fixed_exposure_ms = 10
    for gain in np.arange(camera.config.min_gain, camera.config.max_gain, 0.05):
        camera.set_manual_exposure(fixed_exposure_ms, gain)
        time.sleep(0.1)

    # Switch back to auto exposure, demo for a final 5 seconds and then return
    camera.enable_auto_exposure()
    example_mode = "Mode: Auto Exposure"
    time.sleep(5)


class CameraSettings(annotate.Annotator):
    """
    An annotator for live-display of camera settings on top of the camera
    viewer window.
    """
    def apply(self, image, scale):
        d = ImageDraw.Draw(image)
        bounds = (0, 0, image.width, image.height)
        camera = self.world.robot.camera

        text_to_display = "Example Mode: " + example_mode + "\n\n"
        text_to_display += "Fixed Camera Settings (Calibrated for this Robot):\n"
        text_to_display += '  focal_length: %s\n' % camera.config.focal_length
        text_to_display += '  center: %s\n' % camera.config.center
        text_to_display += '  fov: <%.3f, %.3f> degrees\n' % (camera.config.fov_x.degrees,
                                                              camera.config.fov_y.degrees)
        text_to_display += "\nValid exposure and gain ranges:\n"
        text_to_display += '  Exposure: %s..%s\n' % (camera.config.min_exposure_time_ms,
                                                     camera.config.max_exposure_time_ms)
        text_to_display += '  Gain: %.2f..%.2f\n' % (camera.config.min_gain,
                                                     camera.config.max_gain)
        text_to_display += "\nCurrent settings:\n"
        text_to_display += '  Auto Exposure Enabled: %s\n' % camera.is_auto_exposure_enabled
        text_to_display += '  Exposure: %s ms\n' % camera.exposure_ms
        text_to_display += '  Gain: %.2f\n' % camera.gain

        text = annotate.ImageText(text_to_display,
                                  position=annotate.AnnotationPosition.TOP_LEFT,
                                  color="yellow",
                                  outline_color="black")
        text.render(d, bounds)


def main():
    args = anki_vector.util.parse_command_args()
    with anki_vector.Robot(args.serial, show_viewer=True) as robot:
        robot.camera.image_annotator.add_annotator("camera_settings", CameraSettings)
        demo_camera_exposure(robot)


if __name__ == "__main__":
    main()
