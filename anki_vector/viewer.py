# Copyright (c) 2018 Anki, Inc.
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

"""Displays camera feed from Vector's camera.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['ViewerComponent']

import asyncio
from concurrent.futures import CancelledError
import sys
import time

try:
    import cv2
except ImportError as exc:
    sys.exit("Cannot import opencv-python: Do `pip3 install opencv-python` to install")

try:
    import numpy as np
except ImportError as exc:
    sys.exit("Cannot import numpy: Do `pip3 install numpy` to install")

try:
    from PIL import Image
except ImportError:
    sys.exit("Cannot import from PIL: Do `pip3 install --user Pillow` to install")

from .exceptions import VectorCameraFeedDisabledException
from . import util


class ViewerComponent(util.Component):
    """This component is used to render a video using the images
    obtained from Vector's camera.

    .. testcode::

        import anki_vector

        import asyncio

        with anki_vector.Robot("my_robot_serial_number", show_viewer=True) as robot:
            robot.loop.run_until_complete(asyncio.sleep(5))

    :param robot: A reference to the owner Robot object. (May be :class:`None`)
    """

    def __init__(self, robot):
        super().__init__(robot)
        self.render_task: asyncio.Task = None
        self.overlays: list = []

    @staticmethod
    def _close_window(window_name: str) -> None:
        # Close the openCV window
        cv2.destroyWindow(window_name)
        cv2.waitKey(1)

    def _apply_overlays(self, image: Image.Image) -> None:
        """Apply all overlays attached to viewer instance on to image from camera feed."""
        for overlay in self.overlays:
            overlay.apply_overlay(image)
        return image

    async def _render_frames(self, timeout: float) -> None:
        latest_image_id = None
        opencv_window_name = "Vector Camera Feed"
        cv2.namedWindow(opencv_window_name, cv2.WINDOW_NORMAL)
        start_time = time.time()
        try:
            while True:
                # Stop rendering if feed is disabled
                if not self.robot.enable_camera_feed:
                    raise VectorCameraFeedDisabledException()

                if timeout and ((time.time() - start_time) >= timeout):
                    # Close the openCV window
                    self._close_window(opencv_window_name)
                    break

                # Render image only if new image is available
                if self.robot.camera.latest_image_id != latest_image_id:
                    image = self.robot.camera.latest_image.copy()
                    if self.overlays:
                        image = self._apply_overlays(image)

                    cv2.imshow(opencv_window_name, np.array(image))
                    cv2.waitKey(1)
                    latest_image_id = self.robot.camera.latest_image_id
                await asyncio.sleep(0.1)
        except CancelledError:
            self.logger.debug('Event handler task was cancelled. This is expected during disconnection.')
            # Close the openCV window
            self._close_window(opencv_window_name)

    def show_video(self, timeout: float = None) -> None:
        """Render a video stream using the images obtained from
        Vector's camera feed.

        Be sure to create your Robot object with the camera feed enabled
        by using "show_viewer=True".

        .. testcode::

            import anki_vector
            import asyncio

            with anki_vector.Robot("my_robot_serial_number", show_viewer=True) as robot:
                robot.viewer.show_video()
                robot.loop.run_until_complete(asyncio.sleep(5))

        :param timeout: Render video for the given time. (Renders forever, if timeout not given)
        """
        if not self.render_task or self.render_task.done():
            self.render_task = self.robot.loop.create_task(self._render_frames(timeout))

    def stop_video(self) -> None:
        """Stop rendering video of Vector's camera feed

        .. testcode::

            import anki_vector
            import asyncio

            with anki_vector.Robot("my_robot_serial_number", show_viewer=True) as robot:
                robot.loop.run_until_complete(asyncio.sleep(5))
                robot.viewer.stop_video()
                robot.loop.run_until_complete(asyncio.sleep(5))
        """
        if self.render_task:
            self.render_task.cancel()
            self.robot.loop.run_until_complete(self.render_task)
