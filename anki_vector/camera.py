# Copyright (c) 2018 Anki, Inc.
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

"""Support for Vector's camera.

Vector has a built-in camera which he uses to observe the world around him.

The :class:`CameraComponent` class defined in this module is made available as
:attr:`anki_vector.robot.Robot.camera` and can be used to enable/disable image
sending and observe images being sent by the robot.

The camera resolution is 1280 x 720 with a field of view of 90 deg (H) x 50 deg (V).
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['CameraComponent']

import asyncio
from concurrent.futures import CancelledError
import sys

try:
    import cv2
except ImportError:
    sys.exit("Cannot import opencv-python: Do `pip3 install opencv-python` to install")

from . import util
from .messaging import protocol

try:
    import numpy as np
except ImportError:
    sys.exit("Cannot import numpy: Do `pip3 install numpy` to install")

try:
    from PIL import Image
except ImportError:
    sys.exit("Cannot import from PIL: Do `pip3 install --user Pillow` to install")


class CameraComponent(util.Component):
    """Represents Vector's camera.

    The CameraComponent object receives images from Vector's camera, unpacks the data,
    composes it and makes it available as latest_image.

    The :class:`anki_vector.robot.Robot` or :class:`anki_vector.robot.AsyncRobot` instance observes the camera.

    .. testcode::

        import anki_vector

        with anki_vector.Robot(enable_camera_feed=True) as robot:
            image = robot.camera.latest_image
            image.show()

    :param robot: A reference to the owner Robot object.
    """

    def __init__(self, robot):
        super().__init__(robot)

        self._latest_image: Image.Image = None
        self._latest_image_id: int = None
        self._camera_feed_task: asyncio.Task = None
        self._enabled = False

    @property
    @util.block_while_none()
    def latest_image(self) -> Image.Image:
        """:class:`Image.Image`: The most recently processed image received from the robot.

        :getter: Returns the Pillow Image representing the latest image

        .. testcode::

            import anki_vector

            with anki_vector.Robot(enable_camera_feed=True) as robot:
                image = robot.camera.latest_image
                image.show()
        """
        if not self._camera_feed_task:
            raise Exception("Camera feed not open!")  # TODO: Use a VectorException
        return self._latest_image

    @property
    @util.block_while_none()
    def latest_image_id(self) -> int:
        """The most recently processed image's id received from the robot.

        Used only to track chunks of the same image.

        :getter: Returns the id for the latest image

        .. testcode::

            import anki_vector

            with anki_vector.Robot(enable_camera_feed=True) as robot:
                image = robot.camera.latest_image
                image.show()
                print(f"latest_image_id: {robot.camera.latest_image_id}")
        """
        if not self._camera_feed_task:
            raise Exception("Camera feed not open!")  # TODO: Use a VectorException
        return self._latest_image_id

    def init_camera_feed(self) -> None:
        """Begin camera feed task."""
        if not self._camera_feed_task or self._camera_feed_task.done():
            self._enabled = True
            self._camera_feed_task = self.conn.loop.create_task(self._request_and_handle_images())

    def close_camera_feed(self) -> None:
        """Cancel camera feed task."""
        if self._camera_feed_task:
            self._enabled = False
            self._camera_feed_task.cancel()
            future = self.conn.run_coroutine(self._camera_feed_task)
            future.result()
            self._camera_feed_task = None

    def _unpack_image(self, msg: protocol.CameraFeedResponse) -> None:
        """Processes raw data from the robot into a more more useful image structure."""
        size = len(msg.data)

        # Constuct numpy array out of source data
        array = np.empty(size, dtype=np.uint8)
        array[0:size] = list(msg.data)

        # Decode compressed source data into uncompressed image data
        imageArray = cv2.imdecode(array, -1)
        imageArray = cv2.cvtColor(imageArray, cv2.COLOR_BGR2RGB)

        # Convert to Pillow Image
        self._latest_image = Image.fromarray(imageArray)
        self._latest_image_id = msg.image_id
        self.robot.viewer.enqueue_frame(self._latest_image)

    async def _request_and_handle_images(self) -> None:
        """Queries and listens for camera feed events from the robot.
        Received events are parsed by a helper function."""
        try:
            req = protocol.CameraFeedRequest()
            async for evt in self.grpc_interface.CameraFeed(req):
                # If the camera feed is disabled after stream is setup, exit the stream
                # (the camera feed on the robot is disabled internally on stream exit)
                if not self._enabled:
                    self.logger.warning('Camera feed has been disabled. Enable the feed to start/continue receiving camera feed data')
                    return
                self._unpack_image(evt)
        except CancelledError:
            self.logger.debug('Camera feed task was cancelled. This is expected during disconnection.')
