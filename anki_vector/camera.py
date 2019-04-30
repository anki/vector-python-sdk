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
sending and observe images being sent by the robot. It emits :class:`EvtNewRawCameraImage`
and :class:`EvtNewCameraImage` objects whenever a new camera image is available.

The camera resolution is 1280 x 720 with a field of view of 90 deg (H) x 50 deg (V).
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ["EvtNewRawCameraImage", "EvtNewCameraImage",
           "CameraComponent", "CameraImage"]

import asyncio
from concurrent.futures import CancelledError
import io
import time
import sys

from . import annotate, connection, util
from .events import Events
from .exceptions import VectorCameraFeedException
from .messaging import protocol

try:
    import numpy as np
except ImportError:
    sys.exit("Cannot import numpy: Do `pip3 install numpy` to install")

try:
    from PIL import Image
except ImportError:
    sys.exit("Cannot import from PIL: Do `pip3 install --user Pillow` to install")


def _convert_to_pillow_image(image_data: bytes) -> Image.Image:
    """Convert raw image bytes to a Pillow Image."""
    size = len(image_data)

    # Constuct numpy array out of source data
    array = np.empty(size, dtype=np.uint8)
    array[0:size] = list(image_data)

    # Decode compressed source data into uncompressed image data
    image = Image.open(io.BytesIO(array))
    return image


class CameraImage:
    """A single image from the robot's camera.
    This wraps a raw image and provides an :meth:`annotate_image` method
    that can resize and add dynamic annotations to the image, such as
    marking up the location of objects and faces.

    .. testcode::

        import anki_vector

        with anki_vector.Robot() as robot:
            image = robot.camera.capture_single_image()
            print(f"Displaying image with id {image.image_id}, received at {image.image_recv_time}")
            image.raw_image.show()

    :param raw_image: The raw unprocessed image from the camera.
    :param image_annotator: The image annotation object.
    :param image_id: An image number that increments on every new image received.
    """

    def __init__(self, raw_image: Image.Image, image_annotator: annotate.ImageAnnotator, image_id: int):

        self._raw_image = raw_image
        self._image_annotator = image_annotator
        self._image_id = image_id
        self._image_recv_time = time.time()

    @property
    def raw_image(self) -> Image.Image:
        """The raw unprocessed image from the camera."""
        return self._raw_image

    @property
    def image_id(self) -> int:
        """An image number that increments on every new image received."""
        return self._image_id

    @property
    def image_recv_time(self) -> float:
        """The time the image was received and processed by the SDK."""
        return self._image_recv_time

    def annotate_image(self, scale: float = None, fit_size: tuple = None, resample_mode: int = annotate.RESAMPLE_MODE_NEAREST) -> Image.Image:
        """Adds any enabled annotations to the image.
        Optionally resizes the image prior to annotations being applied.  The
        aspect ratio of the resulting image always matches that of the raw image.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                image = robot.camera.capture_single_image()
                annotated_image = image.annotate_image()
                annotated_image.show()

        :param scale: If set then the base image will be scaled by the
            supplied multiplier.  Cannot be combined with fit_size
        :param fit_size:  If set, then scale the image to fit inside
            the supplied (width, height) dimensions. The original aspect
            ratio will be preserved.  Cannot be combined with scale.
        :param resample_mode: The resampling mode to use when scaling the
            image. Should be either :attr:`~anki_vector.annotate.RESAMPLE_MODE_NEAREST`
            (fast) or :attr:`~anki_vector.annotate.RESAMPLE_MODE_BILINEAR` (slower,
            but smoother).
        """
        return self._image_annotator.annotate_image(self._raw_image,
                                                    scale=scale,
                                                    fit_size=fit_size,
                                                    resample_mode=resample_mode)


class CameraComponent(util.Component):
    """Represents Vector's camera.

    The CameraComponent object receives images from Vector's camera, unpacks the data,
    composes it and makes it available as latest_image.

    The :class:`anki_vector.robot.Robot` or :class:`anki_vector.robot.AsyncRobot` instance observes the camera.

    .. testcode::

        import anki_vector

        with anki_vector.Robot() as robot:
            robot.camera.init_camera_feed()
            image = robot.camera.latest_image
            image.raw_image.show()

    :param robot: A reference to the owner Robot object.
    """

    #: callable: The factory function that returns an
    #: :class:`annotate.ImageAnnotator` class or subclass instance.
    annotator_factory = annotate.ImageAnnotator

    def __init__(self, robot):
        super().__init__(robot)

        self._image_annotator: annotate.ImageAnnotator = self.annotator_factory(self.robot.world)
        self._latest_image: CameraImage = None
        self._latest_image_id: int = None
        self._camera_feed_task: asyncio.Task = None
        self._enabled = False

    @property
    @util.block_while_none()
    def latest_image(self) -> CameraImage:
        """:class:`Image.Image`: The most recently processed image received from the robot.

        The resolution of latest_image is 640x360.

        :getter: Returns the Pillow Image representing the latest image

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                robot.camera.init_camera_feed()
                image = robot.camera.latest_image
                image.raw_image.show()
        """
        if not self._camera_feed_task:
            raise VectorCameraFeedException()
        return self._latest_image

    @property
    @util.block_while_none()
    def latest_image_id(self) -> int:
        """The most recently processed image's id received from the robot.

        Used only to track chunks of the same image.

        :getter: Returns the id for the latest image

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                robot.camera.init_camera_feed()
                image = robot.camera.latest_image
                image.raw_image.show()
                print(f"latest_image_id: {robot.camera.latest_image_id}")
        """
        if not self._camera_feed_task:
            raise VectorCameraFeedException()
        return self._latest_image_id

    @property
    def image_annotator(self) -> annotate.ImageAnnotator:
        """The image annotator used to add annotations to the raw camera images.

        .. testcode::

            import time
            import anki_vector

            with anki_vector.Robot(show_viewer=True) as robot:
                # Annotations (enabled by default) are displayed on the camera feed
                time.sleep(5)
                # Disable all annotations
                robot.camera.image_annotator.annotation_enabled = False
                time.sleep(5)
        """
        return self._image_annotator

    def init_camera_feed(self) -> None:
        """Begin camera feed task.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                robot.camera.init_camera_feed()
                image = robot.camera.latest_image
                image.raw_image.show()
        """
        if not self._camera_feed_task or self._camera_feed_task.done():
            self._enabled = True
            self._camera_feed_task = self.conn.loop.create_task(self._request_and_handle_images())

    def close_camera_feed(self) -> None:
        """Cancel camera feed task."""
        if self._camera_feed_task:
            self._enabled = False
            self._camera_feed_task.cancel()
            future = self.conn.run_coroutine(self._camera_feed_task)
            try:
                future.result()
            except CancelledError:
                self.logger.debug('Camera feed task was cancelled. This is expected during disconnection.')
            # wait for streaming to end, up to 10 seconds
            iterations = 0
            max_iterations = 100
            while self.image_streaming_enabled():
                time.sleep(0.1)
                iterations += 1
                if iterations > max_iterations:
                    # leave loop, even if streaming is still enabled
                    # because other SDK functions will still work and
                    # the RPC should have had enough time to finish
                    # which means we _should_ be in a good state.
                    self.logger.info('Camera Feed closed, but streaming on'
                                     ' robot remained enabled.  This is unexpected.')
                    break
            self._camera_feed_task = None

    async def _image_streaming_enabled(self) -> bool:
        """request streaming enabled status from the robot"""
        request = protocol.IsImageStreamingEnabledRequest()
        response = await self.conn.grpc_interface.IsImageStreamingEnabled(request)
        enabled = False
        if response:
            enabled = response.is_image_streaming_enabled
        return enabled

    def image_streaming_enabled(self) -> bool:
        """True if image streaming is enabled on the robot

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                image_streaming_enabled = robot.camera.image_streaming_enabled()
                if image_streaming_enabled:
                    print("Robot is streaming video")
                else:
                    print("Robot is not streaming video")
        """
        future = self.conn.run_coroutine(self._image_streaming_enabled())
        return future.result()

    def _unpack_image(self, msg: protocol.CameraFeedResponse) -> None:
        """Processes raw data from the robot into a more useful image structure."""
        image = _convert_to_pillow_image(msg.data)

        self._latest_image = CameraImage(image, self._image_annotator, msg.image_id)
        self._latest_image_id = msg.image_id

        self.conn.run_soon(self.robot.events.dispatch_event(EvtNewRawCameraImage(image),
                                                            Events.new_raw_camera_image))
        self.conn.run_soon(self.robot.events.dispatch_event(EvtNewCameraImage(self._latest_image),
                                                            Events.new_camera_image))

        if self._image_annotator.annotation_enabled:
            image = self._image_annotator.annotate_image(image)
        self.robot.viewer.enqueue_frame(image)

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

    @connection.on_connection_thread()
    async def capture_single_image(self) -> CameraImage:
        """Request to capture a single image from the robot's camera.

        This call requests the robot to capture an image and returns the
        received image, formatted as a Pillow image. This differs from `latest_image`,
        which maintains the last image received from the camera feed (if enabled).

        Note that when the camera feed is enabled this call returns the `latest_image`.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                image = robot.camera.capture_single_image()
                image.raw_image.show()
        """
        if self._enabled:
            return self._latest_image
        req = protocol.CaptureSingleImageRequest()
        res = await self.grpc_interface.CaptureSingleImage(req)
        if res and res.data:
            image = _convert_to_pillow_image(res.data)
            return CameraImage(image, self._image_annotator, res.image_id)

        self.logger.error('Failed to capture a single image')


class EvtNewRawCameraImage:  # pylint: disable=too-few-public-methods
    """Dispatched when a new raw image is received from the robot's camera.

    See also :class:`~anki_vector.camera.EvtNewCameraImage` which provides access
    to both the raw image and a scaled and annotated version.

    .. testcode::

        import threading

        import anki_vector
        from anki_vector import events

        def on_new_raw_camera_image(robot, event_type, event, done):
            print("Display new camera image")
            event.image.show()
            done.set()

        with anki_vector.Robot() as robot:
            robot.camera.init_camera_feed()
            done = threading.Event()
            robot.events.subscribe(on_new_raw_camera_image, events.Events.new_raw_camera_image, done)

            print("------ waiting for camera events, press ctrl+c to exit early ------")

            try:
                if not done.wait(timeout=5):
                    print("------ Did not receive a new camera image! ------")
            except KeyboardInterrupt:
                pass

    :param image: A raw camera image.
    """

    def __init__(self, image: Image.Image):
        self.image = image


class EvtNewCameraImage:  # pylint: disable=too-few-public-methods
    """Dispatched when a new camera image is received and processed from the robot's camera.

    .. testcode::

        import threading

        import anki_vector
        from anki_vector import events

        def on_new_camera_image(robot, event_type, event, done):
            print(f"Display new annotated camera image with id {event.image.image_id}")
            annotated_image = event.image.annotate_image()
            annotated_image.show()
            done.set()

        with anki_vector.Robot(enable_face_detection=True, enable_custom_object_detection=True) as robot:
            robot.camera.init_camera_feed()
            done = threading.Event()
            robot.events.subscribe(on_new_camera_image, events.Events.new_camera_image, done)

            print("------ waiting for camera events, press ctrl+c to exit early ------")

            try:
                if not done.wait(timeout=5):
                    print("------ Did not receive a new camera image! ------")
            except KeyboardInterrupt:
                pass

    :param: A wrapped camera image object that contains the raw image.
    """

    def __init__(self, image: CameraImage):
        self.image = image
