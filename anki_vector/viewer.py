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
import multiprocessing as mp
import sys

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

from . import util


class ViewerComponent(util.Component):
    """This component opens a window and renders the images obtained from Vector's camera.
    This viewer window is run in a separate process spawned by :func:`~ViewerComponent.show_video`.
    Being on a separate process means the rendering of the camera does not block the main thread
    of the calling code, and allows the viewer to have its own ui thread which it can operate on.
    :func:`~ViewerComponent.stop_video` will stop the viewer process.

    .. testcode::

        import anki_vector

        import time

        with anki_vector.Robot(enable_camera_feed=True, show_viewer=True) as robot:
            time.sleep(5)

    :param robot: A reference to the owner Robot object. (May be :class:`None`)
    """

    def __init__(self, robot):
        super().__init__(robot)
        self.overlays: list = []
        self._frame_queue: mp.Queue = None
        self._loop: asyncio.BaseEventLoop = None
        self._process = None

    def show_video(self, timeout: float = 10.0) -> None:
        """Render a video stream using the images obtained from
        Vector's camera feed.

        Be sure to create your Robot object with the camera feed enabled
        by using "show_viewer=True" and "enable_camera_feed=True".

        .. testcode::

            import anki_vector
            import time

            with anki_vector.Robot(enable_camera_feed=True) as robot:
                robot.viewer.show_video()
                time.sleep(10)

        :param timeout: Render video for the given time. (Renders forever, if timeout not given)
        """
        ctx = mp.get_context('spawn')
        self._frame_queue = ctx.Queue(maxsize=4)
        self._process = ctx.Process(target=ViewerComponent._render_frames, args=(self._frame_queue, self.overlays, timeout), daemon=True)
        self._process.start()

    def stop_video(self) -> None:
        """Stop rendering video of Vector's camera feed and close the viewer process.

        .. testcode::

            import anki_vector
            import time

            with anki_vector.Robot(show_viewer=True) as robot:
                time.sleep(10)
                robot.viewer.stop_video()
        """
        if self._frame_queue:
            self._frame_queue.put(None, False)
            self._frame_queue = None
        if self._process:
            self._process.join(timeout=5)
            self._process = None

    def enqueue_frame(self, image: Image.Image):
        """Sends a frame to the viewer's rendering process. Sending `None` to the viewer
        will cause it to gracefully shutdown.

        .. note::

            This function will be called automatically from the camera feed when the
            :class:`~anki_vector.robot.Robot` object is created with ``enable_camera_feed=True``.

        .. code-block:: python

            import anki_vector
            from PIL.Image import Image

            image = Image()
            with anki_vector.Robot(show_viewer=True) as robot:
                robot.viewer.enqueue_frame(image)

        :param image: A frame from Vector's camera.
        """
        if self._frame_queue is not None:
            try:
                self._frame_queue.put(image, False)
            except mp.queues.Full:
                pass

    def _apply_overlays(self, image: Image.Image) -> None:
        """Apply all overlays attached to viewer instance on to image from camera feed."""
        for overlay in self.overlays:
            overlay.apply_overlay(image)
        return image

    @staticmethod
    def _render_frames(queue: mp.Queue, overlays: list = None, timeout: float = 10.0) -> None:
        """Rendering the frames in another process. This allows the UI to have the
        main thread of its process while the user code continues to execute.

        :param queue: A queue to send frames between main thread and other process.
        :param overlays: overlays to be drawn on the images of the renderer.
        :param timeout: The time without a new frame before the process will exit.
        """
        window_name = "Vector Camera Feed"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        try:
            image = queue.get(True, timeout=timeout)
            while image:
                if overlays:
                    for overlay in overlays:
                        overlay.apply_overlay(image)
                image = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2RGB)
                cv2.imshow(window_name, image)
                cv2.waitKey(1)
                if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                    break
                image = queue.get(True, timeout=timeout)
        except TimeoutError:
            pass
        except KeyboardInterrupt:
            pass

        cv2.destroyWindow(window_name)
        cv2.waitKey(1)
