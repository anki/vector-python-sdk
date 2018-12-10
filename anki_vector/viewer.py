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

"""Displays camera feed from Vector's camera.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['ViewerComponent', 'Viewer3DComponent']

import multiprocessing as mp
import os
import sys
import threading

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
from .events import Events


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
        self._close_event: mp.Event = None
        self._frame_queue: mp.Queue = None
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
        self._close_event = ctx.Event()
        self._frame_queue = ctx.Queue(maxsize=4)
        self._process = ctx.Process(target=ViewerComponent._render_frames,
                                    args=(self._frame_queue,
                                          self._close_event,
                                          self.overlays,
                                          timeout),
                                    daemon=True,
                                    name="Camera Viewer Process")
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
        if self._close_event:
            self._close_event.set()
            self._close_event = None
        if self._frame_queue:
            try:
                self._frame_queue.put(None, False)
            except mp.queues.Full:
                pass
            self._frame_queue = None
        if self._process:
            self._process.join(timeout=5)
            if self._process.is_alive():
                self._process.terminate()
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
        close_event = self._close_event
        if self._frame_queue is not None and close_event is not None and not close_event.is_set():
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
    def _render_frames(queue: mp.Queue, event: mp.Event, overlays: list = None, timeout: float = 10.0) -> None:
        """Rendering the frames in another process. This allows the UI to have the
        main thread of its process while the user code continues to execute.

        :param queue: A queue to send frames between main thread and other process.
        :param overlays: overlays to be drawn on the images of the renderer.
        :param timeout: The time without a new frame before the process will exit.
        """
        is_windows = os.name == 'nt'
        window_name = "Vector Camera Feed"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        try:
            image = queue.get(True, timeout=timeout)
            while image:
                if event.is_set():
                    break
                if overlays:
                    for overlay in overlays:
                        overlay.apply_overlay(image)
                image = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2RGB)
                cv2.imshow(window_name, image)
                cv2.waitKey(1)
                if not is_windows and cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                    break
                image = queue.get(True, timeout=timeout)
        except TimeoutError:
            pass
        except KeyboardInterrupt:
            pass
        finally:
            event.set()
            cv2.destroyWindow(window_name)
            cv2.waitKey(1)


class _ExternalRenderCallFunctor():  # pylint: disable=too-few-public-methods
    """Externally specified OpenGL render function.

    Allows extra geometry to be rendered into OpenGLViewer.

    :param f: function to call inside the rendering loop
    :param f_args: a list of arguments to supply to the callable function
    """

    def __init__(self, f: callable, f_args: list):
        self._f = f
        self._f_args = f_args

    def invoke(self, user_data_queue):
        """Calls the internal function"""
        self._f(*self._f_args, user_data_queue=user_data_queue)


class Viewer3DComponent(util.Component):
    """This component opens a window and renders the a 3D view obtained from Vector's navigation map.
    This viewer window is run in a separate process spawned by :func:`~Viewer3DComponent.show`.
    Being on a separate process means the rendering of the 3D view does not block the main thread
    of the calling code, and allows the viewer to have its own ui thread with which it can render OpenGL.
    :func:`~Viewer3DComponent.close` will stop the viewer process.

    .. testcode::

        import anki_vector

        import time

        with anki_vector.Robot(enable_nav_map_feed=True, show_3d_viewer=True) as robot:
            time.sleep(5)

    :param robot: A reference to the owner Robot object. (May be :class:`None`)
    """

    def __init__(self, robot):
        super().__init__(robot)
        self.overlays: list = []
        self._close_event: mp.Event = None
        self._input_intent_queue: mp.Queue = None
        self._nav_map_queue: mp.Queue = None
        self._world_frame_queue: mp.Queue = None
        self._extra_render_function_queue: mp.Queue = None
        self._user_data_queue: mp.Queue = None
        self._process: mp.process.BaseProcess = None
        self._update_thread: threading.Thread = None
        self._last_robot_control_intents = None

    def show(self):
        """Spawns a background process that shows the navigation map in a 3D view.

        .. testcode::

            import anki_vector

            import time

            with anki_vector.Robot(enable_nav_map_feed=True) as robot:
                robot.viewer_3d.show()
                time.sleep(5)
                robot.viewer_3d.close()
        """
        from . import opengl
        ctx = mp.get_context('spawn')
        self._close_event = ctx.Event()
        self._input_intent_queue = ctx.Queue(maxsize=10)
        self._nav_map_queue = ctx.Queue(maxsize=10)
        self._world_frame_queue = ctx.Queue(maxsize=10)
        self._extra_render_function_queue = ctx.Queue(maxsize=1)
        self._user_data_queue = ctx.Queue()
        self._update_thread = threading.Thread(target=self._update,
                                               args=(),
                                               daemon=True,
                                               name="3D Viewer Update Thread")
        self._update_thread.start()
        self._process = ctx.Process(target=opengl.main,
                                    args=(self._close_event,
                                          self._input_intent_queue,
                                          self._nav_map_queue,
                                          self._world_frame_queue,
                                          self._extra_render_function_queue,
                                          self._user_data_queue),
                                    daemon=True,
                                    name="3D Viewer Process")
        self._process.start()
        self.robot.events.subscribe(self._on_robot_state_update, Events.robot_state)
        self.robot.events.subscribe(self._on_nav_map_update, Events.nav_map_update)

    @property
    def user_data_queue(self):
        """A queue to send custom data to the 3D viewer process.

        Best used in conjunction with :func:`~Viewer3DComponent.add_render_call` to place
        a process on the 3D viewer process then obtain data from this queue.
        """
        return self._user_data_queue

    def add_render_call(self, render_function: callable, *args):
        """Allows external functions to be injected into the viewer process which
        will be called at the appropriate time in the rendering pipeline.

        Example usage to draw a dot at the world origin:

        .. code-block:: python

            import time

            import anki_vector

            def my_render_function(user_data_queue):
                glBegin(GL_POINTS)
                glVertex3f(0, 0, 0)
                glEnd()

            with anki_vector.Robot(enable_nav_map_feed=True, show_3d_viewer=True) as robot:
                robot.viewer_3d.add_render_call(my_render_function)
                time.sleep(10)

        :param render_function: The delegated function to be invoked in the pipeline.
        :param args: An optional list of arguments to send to the render_function
            the arguments list must match the parameters accepted by the
            supplied function.
        """
        self._extra_render_function_queue.put(_ExternalRenderCallFunctor(render_function, args))

    def close(self):
        """Closes the background process showing the 3D view.

        .. testcode::

            import anki_vector

            import time

            with anki_vector.Robot(enable_nav_map_feed=True) as robot:
                robot.viewer_3d.show()
                time.sleep(5)
                robot.viewer_3d.close()
        """
        if self._close_event:
            self._close_event.set()
            self._close_event = None
        if self._update_thread:
            self._update_thread.join(timeout=2)
            self._update_thread = None
        self._input_intent_queue = None
        self._nav_map_queue = None
        self._world_frame_queue = None
        if self._process:
            self._process.join(timeout=5)
            if self._process.is_alive():
                self._process.terminate()
            self._process = None

    def _update(self):
        """Reads most recently stored user-triggered intents, and sends
        motor messages to the robot if the intents should effect the robot's
        current motion.

        Called on SDK thread, for controlling robot from input intents
        pushed from the OpenGL thread.

        :param robot: the robot being updated by this View Controller
        """
        close_event = self._close_event
        while close_event and not close_event.is_set():
            try:
                input_intents = self._input_intent_queue.get(True, timeout=2)  # type: RobotControlIntents

                # Track last-used intents so that we only issue motor controls
                # if different from the last frame (to minimize it fighting with an SDK
                # program controlling the robot):
                old_intents = self._last_robot_control_intents
                self._last_robot_control_intents = input_intents

                if not old_intents or (old_intents.left_wheel_speed != input_intents.left_wheel_speed
                                       or old_intents.right_wheel_speed != input_intents.right_wheel_speed):
                    self.robot.motors.set_wheel_motors(input_intents.left_wheel_speed,
                                                       input_intents.right_wheel_speed,
                                                       input_intents.left_wheel_speed * 4,
                                                       input_intents.right_wheel_speed * 4,
                                                       _return_future=True)

                if not old_intents or old_intents.lift_speed != input_intents.lift_speed:
                    self.robot.motors.set_lift_motor(input_intents.lift_speed, _return_future=True)

                if not old_intents or old_intents.head_speed != input_intents.head_speed:
                    self.robot.motors.set_head_motor(input_intents.head_speed, _return_future=True)
            except mp.queues.Empty:
                pass
            close_event = self._close_event

    def _on_robot_state_update(self, *_):
        """Called from SDK process whenever the robot state is updated (so i.e. every engine tick).

        Note:

            This is called from the SDK process, and will pass the nav map data to the
            3D viewer process.

            We can safely capture any robot and world state here, and push to OpenGL
            (main) process via a multiprocessing queue.
        """
        from .opengl import opengl_vector
        world_frame = opengl_vector.WorldRenderFrame(self.robot)
        queue = self._world_frame_queue
        if queue:
            try:
                queue.put(world_frame, False)
            except mp.queues.Full:
                pass
        # self._view_controller.update(self.robot) # TODO: <- sounds like this has something to do with keyboard input...

    def _on_nav_map_update(self, _, msg):
        """Called from SDK process whenever the nav map is updated.

        Note:

            This is called from the SDK process, and will pass the nav map data to the
            3D viewer process.

            We can safely capture any robot and world state here, and push to OpenGL
            (main) process via a multiprocessing queue.
        """
        queue = self._nav_map_queue
        if queue:
            try:
                queue.put(msg, False)
            except mp.queues.Full:
                pass
