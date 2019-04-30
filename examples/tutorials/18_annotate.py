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

'''Display a GUI window showing an annotated camera view.

Note:
    This example requires Python to have Tkinter installed to display the GUI.

This example uses tkinter to display the annotated camera feed on the screen
and adds a couple of custom annotations of its own using two different methods.
'''

import asyncio
import sys
import time

from PIL import ImageDraw

import anki_vector
from anki_vector import annotate


# Define an annotator using the annotator decorator
@annotate.annotator
def clock(image, scale, annotator=None, world=None, **kw):
    d = ImageDraw.Draw(image)
    bounds = (0, 0, image.width, image.height)
    text = annotate.ImageText(time.strftime("%H:%m:%S"),
                              position=annotate.AnnotationPosition.TOP_LEFT,
                              outline_color="black")
    text.render(d, bounds)

# Define a new annotator by inheriting the base annotator class
class Battery(annotate.Annotator):
    def __init__(self, img_annotator, box_color=None):
        super().__init__(img_annotator)
        self.battery_state = None
        self.battery_state_task = None
        if box_color is not None:
            self.box_color = box_color

    def apply(self, image, scale):
        d = ImageDraw.Draw(image)
        bounds = (0, 0, image.width, image.height)

        if not self.battery_state_task:
            self.battery_state_task = self.world.robot.get_battery_state()

        if asyncio.isfuture(self.battery_state_task) and self.battery_state_task.done():
            self.battery_state = self.battery_state_task.result()
            self.battery_state_task = self.world.robot.get_battery_state()

        if self.battery_state:
            batt = self.battery_state.battery_volts
            text = annotate.ImageText(f"BATT {batt:.1f}v", color="green", outline_color="black")
            text.render(d, bounds)


def main():
    args = anki_vector.util.parse_command_args()
    with anki_vector.Robot(args.serial, show_viewer=True, enable_face_detection=True) as robot:
        robot.camera.image_annotator.add_static_text("text", "Vec-Cam", position=annotate.AnnotationPosition.TOP_RIGHT)
        robot.camera.image_annotator.add_annotator("clock", clock)
        robot.camera.image_annotator.add_annotator("battery", Battery)

        time.sleep(10)

        print("Turning off all annotations for 5 seconds")
        robot.camera.image_annotator.annotation_enabled = False
        time.sleep(5)

        print("Re-enabling all annotations")
        robot.camera.image_annotator.annotation_enabled = True

        print("------ Press ctrl+c to exit early ------")

        try:
            # Shutdown the program after 30 seconds
            time.sleep(30)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
