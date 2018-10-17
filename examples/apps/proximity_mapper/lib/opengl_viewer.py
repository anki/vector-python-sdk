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

"""This module provides a 3D visualizer for Vector's world state.

It uses PyOpenGL, a Python OpenGL 3D graphics library which is available on most
platforms. It also depends on the Pillow library for image processing.

The easiest way to make use of this viewer is to create an OpenGLViewer object
for a valid robot and call run with a control function injected into it.

Example:
    .. code-block:: python

        def my_function(robot):
            robot.play_animation("anim_blackjack_victorwin_01")

        with anki_vector.Robot("my_robot_serial_number") as robot:
            viewer = opengl.OpenGLViewer(robot=robot)
            viewer.run(my_function)

Warning:
    This package requires Python to have the PyOpenGL package installed, along
    with an implementation of GLUT (OpenGL Utility Toolkit).

    To install the Python packages do ``pip install .[3dviewer]``

    On Windows and Linux you must also install freeglut (macOS / OSX has one
    preinstalled).

    On Linux: ``sudo apt-get install freeglut3``

    On Windows: Go to http://freeglut.sourceforge.net/ to get a ``freeglut.dll``
    file. It's included in any of the `Windows binaries` downloads. Place the DLL
    next to your Python script, or install it somewhere in your PATH to allow any
    script to use it."
"""

# TODO Update install line above to: ``pip3 install --user "anki_vector[3dviewer]"``

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['OpenGLViewer']

import asyncio
import collections
import concurrent
import inspect
import math
import threading
from typing import List

import opengl
import opengl_vector

from anki_vector.events import Events
from anki_vector.robot import Robot
from anki_vector import util

try:
    from OpenGL.GL import (GL_FILL,
                           GL_FRONT_AND_BACK,
                           GL_LIGHTING, GL_NORMALIZE,
                           GL_TEXTURE_2D,
                           glBindTexture, glDisable, glEnable,
                           glMultMatrixf, glPolygonMode, glPopMatrix, glPushMatrix,
                           glScalef)
    from OpenGL.GLUT import (GLUT_ACTIVE_ALT, GLUT_ACTIVE_CTRL, GLUT_ACTIVE_SHIFT, GLUT_DOWN, GLUT_LEFT_BUTTON, GLUT_RIGHT_BUTTON,
                             glutCheckLoop, glutLeaveMainLoop, glutGetModifiers,
                             glutKeyboardFunc, glutKeyboardUpFunc, glutMainLoop, glutMouseFunc, glutMotionFunc, glutPassiveMotionFunc,
                             glutSpecialFunc, glutSpecialUpFunc)
    from OpenGL.error import NullFunctionError

except ImportError as import_exc:
    opengl.raise_opengl_or_pillow_import_error(import_exc)

# Constants


class VectorException(BaseException):
    """Raised by a failure in the owned Vector thread while the openGL viewer is running."""


class _LoopThread:
    """Takes care of managing an event loop running in a dedicated thread.

    :param loop: The loop to run
    :param f: Optional code to execute on the loop's thread
    :param argument: external argument to inject into the function.
    """

    def __init__(self, loop: asyncio.BaseEventLoop, f: callable = None, argument: object = None):
        self._loop = loop
        self._f = f
        self._argument = argument
        self._thread = None
        self._running = False

    def start(self):
        """Start a thread."""
        def run_loop():
            asyncio.set_event_loop(self._loop)

            if self._f:
                asyncio.ensure_future(self._f(self._argument))
            self._loop.run_forever()

        self._thread = threading.Thread(target=run_loop)
        self._thread.start()

        self._running = True

    def stop(self):
        """Cleaning shutdown the running loop and thread."""
        if self._running:
            async def _stop():
                self._loop.call_soon(lambda: self._loop.stop())  # pylint: disable=unnecessary-lambda
            asyncio.run_coroutine_threadsafe(_stop(), self._loop).result()
            self._thread.join()
            self._running = False

    def abort(self, exc: BaseException):  # pylint: disable=unused-argument
        """Abort the running loop and thread.

        :param exc: exception being raised
        """
        if self._running:
            self.stop()


class _OpenGLViewController():
    """Controller that registeres for keyboard and mouse input through GLUT, and uses them to update
    the camera and listen for a shutdown cue.

    :param shutdown_delegate: Function to call when we want to exit the host OpenGLViewer.
    :param camera: The camera object for the controller to mutate.
    """

    def __init__(self, shutdown_delegate: callable, camera: opengl.Camera):
        # Keyboard
        self._is_key_pressed = {}
        self._is_alt_down = False
        self._is_ctrl_down = False
        self._is_shift_down = False

        # Mouse
        self._is_mouse_down = {}
        self._mouse_pos = None  # type: util.Vector2

        self._shutdown_delegate = shutdown_delegate

        self._last_robot_position = None

        self._camera = camera

    @property
    def last_robot_position(self):
        return self._last_robot_position

    @last_robot_position.setter
    def last_robot_position(self, last_robot_position):
        self._last_robot_position = last_robot_position

    def initialize(self):
        """Sets up the openGL window and binds input callbacks to it
        """

        glutKeyboardFunc(self._on_key_down)
        glutSpecialFunc(self._on_special_key_down)

        # [Keyboard/Special]Up methods aren't supported on some old GLUT implementations
        try:
            if bool(glutKeyboardUpFunc):
                glutKeyboardUpFunc(self._on_key_up)
            if bool(glutSpecialUpFunc):
                glutSpecialUpFunc(self._on_special_key_up)
        except NullFunctionError:
            # Methods aren't available on this GLUT version
            pass

        glutMouseFunc(self._on_mouse_button)
        glutMotionFunc(self._on_mouse_move)
        glutPassiveMotionFunc(self._on_mouse_move)

    def _update_modifier_keys(self):
        """Updates alt, ctrl, and shift states.
        """
        modifiers = glutGetModifiers()
        self._is_alt_down = (modifiers & GLUT_ACTIVE_ALT != 0)
        self._is_ctrl_down = (modifiers & GLUT_ACTIVE_CTRL != 0)
        self._is_shift_down = (modifiers & GLUT_ACTIVE_SHIFT != 0)

    def _key_byte_to_lower(self, key):  # pylint: disable=no-self-use
        """Convert bytes-object (representing keyboard character) to lowercase equivalent.
        """
        if b'A' <= key <= b'Z':
            lowercase_key = ord(key) - ord(b'A') + ord(b'a')
            lowercase_key = bytes([lowercase_key])
            return lowercase_key
        return key

    def _on_key_up(self, key, x, y):  # pylint: disable=unused-argument
        """Called by GLUT when a standard keyboard key is released.

        :param key: which key was released.
        :param x: the x coordinate of the mouse cursor.
        :param y: the y coordinate of the mouse cursor.
        """
        key = self._key_byte_to_lower(key)
        self._update_modifier_keys()
        self._is_key_pressed[key] = False

    def _on_key_down(self, key, x, y):  # pylint: disable=unused-argument
        """Called by GLUT when a standard keyboard key is pressed.

        :param key: which key was released.
        :param x: the x coordinate of the mouse cursor.
        :param y: the y coordinate of the mouse cursor.
        """
        key = self._key_byte_to_lower(key)
        self._update_modifier_keys()
        self._is_key_pressed[key] = True

        if ord(key) == 9:  # Tab
            # Set Look-At point to current robot position
            if self._last_robot_position is not None:
                self._camera.look_at = self._last_robot_position
        elif ord(key) == 27:  # Escape key
            self._shutdown_delegate()

    def _on_special_key_up(self, key, x, y):  # pylint: disable=unused-argument
        """Called by GLUT when a special key is released.

        :param key: which key was released.
        :param x: the x coordinate of the mouse cursor.
        :param y: the y coordinate of the mouse cursor.
        """
        self._update_modifier_keys()

    def _on_special_key_down(self, key, x, y):  # pylint: disable=unused-argument
        """Called by GLUT when a special key is pressed.

        :param key: which key was pressed.
        :param x: the x coordinate of the mouse cursor.
        :param y: the y coordinate of the mouse cursor.
        """
        self._update_modifier_keys()

    def _on_mouse_button(self, button, state, x, y):
        """Called by GLUT when a mouse button is pressed.

        :param button: which button was pressed.
        :param state: the current state of the button.
        :param x: the x coordinate of the mouse cursor.
        :param y: the y coordinate of the mouse cursor.
        """
        # Don't update modifier keys- reading modifier keys is unreliable
        # from _on_mouse_button (for LMB down/up), only SHIFT key seems to read there
        # self._update_modifier_keys()
        is_down = (state == GLUT_DOWN)
        self._is_mouse_down[button] = is_down
        self._mouse_pos = util.Vector2(x, y)

    def _on_mouse_move(self, x, y):
        """Handles mouse movement.

        :param x: the x coordinate of the mouse cursor.
        :param y: the y coordinate of the mouse cursor.
        """

        # is_active is True if this is not passive (i.e. a mouse button was down)
        last_mouse_pos = self._mouse_pos
        self._mouse_pos = util.Vector2(x, y)
        if last_mouse_pos is None:
            # First mouse update - ignore (we need a delta of mouse positions)
            return

        left_button = self._is_mouse_down.get(GLUT_LEFT_BUTTON, False)
        # For laptop and other 1-button mouse users, treat 'x' key as a right mouse button too
        right_button = (self._is_mouse_down.get(GLUT_RIGHT_BUTTON, False) or
                        self._is_key_pressed.get(b'x', False))

        MOUSE_SPEED_SCALAR = 1.0  # general scalar for all mouse movement sensitivity
        MOUSE_ROTATE_SCALAR = 0.025  # additional scalar for rotation sensitivity
        mouse_delta = (self._mouse_pos - last_mouse_pos) * MOUSE_SPEED_SCALAR

        if left_button and right_button:
            # Move up/down
            self._camera.move(up_amount=-mouse_delta.y)
        elif right_button:
            # Move forward/back and left/right
            self._camera.move(forward_amount=mouse_delta.y, right_amount=mouse_delta.x)
        elif left_button:
            if self._is_key_pressed.get(b'z', False):
                # Zoom in/out
                self._camera.zoom(mouse_delta.y)
            else:
                self._camera.turn(mouse_delta.x * MOUSE_ROTATE_SCALAR, mouse_delta.y * MOUSE_ROTATE_SCALAR)


class _ExternalRenderCallFunctor():  # pylint: disable=too-few-public-methods
    """Externally specified OpenGL render function.

    Allows extra geometry to be renderd into an openGL viewer

    :param f: function to call inside the rendering loop
    :param f_args: a list of arguments to supply to the callable function
    """

    def __init__(self, f: callable, f_args: list):
        self._f = f
        self._f_args = f_args

    def invoke(self):
        """Calls the internal function"""
        self._f(*self._f_args)


#: A default window resolution provided for opengl Vector programs
#: 800x600 is large enough to see detail, while fitting on the smaller
#: end of modern monitors.
default_resolution = [800, 600]

#: A default projector configurate provided for opengl Vector programs
#: A Field of View of 45 degrees is common for 3d applications,
#: and a viewable distance range of 1.0 to 1000.0 will provide a
#: visible space comparable with most physical Vector environments.
default_projector = opengl.Projector(
    fov=45.0,
    near_clip_plane=1.0,
    far_clip_plane=1000.0)

#: A default camera object provided for opengl Vector programs.
#: Starts close to and looking at the charger.
default_camera = opengl.Camera(
    look_at=util.Vector3(100.0, -25.0, 0.0),
    up=util.Vector3(0.0, 0.0, 1.0),
    distance=500.0,
    pitch=math.radians(40),
    yaw=math.radians(270))

#: A default light group provided for opengl Vector programs.
#: Contains one light near the origin.
default_lights = [opengl.Light(
    ambient_color=[1.0, 1.0, 1.0, 1.0],
    diffuse_color=[1.0, 1.0, 1.0, 1.0],
    specular_color=[1.0, 1.0, 1.0, 1.0],
    position=util.Vector3(0, 32, 20))]

# Global viewer instance.  Stored to make sure multiple viewers are not
# instantiated simultaneously.
opengl_viewer = None  # type: OpenGLViewer


class OpenGLViewer():
    """OpenGL based 3D Viewer.

    Handles rendering of both a 3D world view and a 2D camera window.

    :param robot: the robot object being used by the OpenGL viewer
    """

    def __init__(self,
                 robot: Robot,
                 resolution: List[int] = None,
                 projector: opengl.Projector = None,
                 camera: opengl.Camera = None,
                 lights: List[opengl.Light] = None):

        if resolution is None:
            resolution = default_resolution
        if projector is None:
            projector = default_projector
        if camera is None:
            camera = default_camera
        if lights is None:
            lights = default_lights

        # Queues from SDK thread to OpenGL thread
        self._world_frame_queue = collections.deque(maxlen=1)

        self._logger = util.get_class_logger(__name__, self)
        self._robot = robot
        self._extra_render_calls = []

        self._internal_function_finished = False
        self._exit_requested = False

        global opengl_viewer  # pylint: disable=global-statement
        if opengl_viewer is not None:
            self._logger.error("Multiple OpenGLViewer instances not expected: "
                               "OpenGL / GLUT only supports running 1 blocking instance on the main thread.")
        opengl_viewer = self

        self._vector_view_manifest = opengl_vector.VectorViewManifest()
        self._main_window = opengl.OpenGLWindow(0, 0, resolution[0], resolution[1], b"Vector 3D Visualizer")

        # Create a 3d projector configuration class.
        self._projector = projector
        self._camera = camera
        self._lights = lights

        self._view_controller = _OpenGLViewController(self.close, self._camera)

        self._latest_world_frame = None  # type: WorldRenderFrame

    def add_render_call(self, render_function: callable, *args):
        """Allows external functions to be injected into the viewer which
        will be called at the appropriate time in the rendering pipeline.

        Exmaple usage to draw a dot at the world origin:

        .. code-block:: python

            def my_render_function():
                glBegin(GL_POINTS)
                glVertex3f(0, 0, 0)
                glEnd()

            my_opengl_viewer.add_render_call(my_render_function)

        :param render_function: The delegated function to be invoked in the pipeline
        :param args: An optional list of arguments to send to the render_function
            the arguments list must match the parameters accepted by the
            supplied function.
        """
        self._extra_render_calls.append(_ExternalRenderCallFunctor(render_function, args))

    def _request_exit(self):
        """Begins the viewer shutdown process"""
        self._exit_requested = True
        if bool(glutLeaveMainLoop):
            glutLeaveMainLoop()

    def _render_world_frame(self, world_frame: opengl_vector.WorldRenderFrame):
        """Render the world to the current OpenGL context

        :param world_frame: frame to render
        """
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glEnable(GL_LIGHTING)
        glEnable(GL_NORMALIZE)  # to re-scale scaled normals

        light_cube_view = self._vector_view_manifest.light_cube_view
        unit_cube_view = self._vector_view_manifest.unit_cube_view
        robot_view = self._vector_view_manifest.robot_view

        robot_frame = world_frame.robot_frame
        robot_pose = robot_frame.pose

        # Render the cube
        for i in range(1):
            cube_frame = world_frame.cube_frames[i]
            if cube_frame is None:
                continue

            cube_pose = cube_frame.pose
            if cube_pose is not None and cube_pose.is_comparable(robot_pose):
                light_cube_view.display(cube_pose)

        glBindTexture(GL_TEXTURE_2D, 0)

        for face in world_frame.face_frames:
            face_pose = face.pose
            if face_pose is not None and face_pose.is_comparable(robot_pose):
                glPushMatrix()
                face_matrix = face_pose.to_matrix()
                glMultMatrixf(face_matrix.in_row_order)

                # Approximate size of a head
                glScalef(100, 25, 100)

                FACE_OBJECT_COLOR = [0.5, 0.5, 0.5, 1.0]
                draw_solid = face.time_since_last_seen < 30
                unit_cube_view.display(FACE_OBJECT_COLOR, draw_solid)

                glPopMatrix()

        glDisable(GL_LIGHTING)

        robot_view.display(robot_frame.pose, robot_frame.head_angle, robot_frame.lift_position)

    def _render_3d_view(self, window: opengl.OpenGLWindow):
        """Renders 3d objects to an openGL window

        :param window: opengl window to render to
        """
        window.prepare_for_rendering(self._projector, self._camera, self._lights)

        # Update the latest world frame if there is a new one available
        try:
            world_frame = self._world_frame_queue.popleft()  # type: WorldRenderFrame
            if world_frame is not None:
                self._view_controller.last_robot_position = world_frame.robot_frame.pose.position
            self._latest_world_frame = world_frame
        except IndexError:
            world_frame = self._latest_world_frame

        if world_frame is not None:
            self._render_world_frame(world_frame)

        for render_call in self._extra_render_calls:
            # Protecting the external calls with pushMatrix so internal transform
            # state changes will not alter other calls
            glPushMatrix()
            try:
                render_call.invoke()
            finally:
                glPopMatrix()

        window.display_rendered_content()

    def _on_window_update(self):
        """Top level display call which intercepts keyboard interrupts or delegates
        to the lower level display call.
        """
        try:
            self._render_3d_view(self._main_window)

        except KeyboardInterrupt:
            self._logger.info("_display caught KeyboardInterrupt - exitting")
            self._request_exit()

    def run(self, delegate_function: callable):
        """Turns control of the main thread over to the openGL viewer

        :param delegate_function: external function to spin up on a seperate thread
            to allow for sdk code to run while the main thread is owned by the viewer.
        """
        abort_future = concurrent.futures.Future()

        # Register for robot state events
        robot = self._robot
        robot.events.subscribe(self._on_robot_state_update, Events.robot_state)

        # Determine how many arguments the function accepts
        function_args = []
        for param in inspect.signature(delegate_function).parameters:
            if param == 'robot':
                function_args.append(robot)
            elif param == 'viewer':
                function_args.append(self)
            else:
                raise ValueError("the delegate_function injected into OpenGLViewer.run requires an unrecognized parameter, only 'robot' and 'viewer' are supported")

        async def run_function(robot):
            try:
                if inspect.iscoroutinefunction(delegate_function):
                    await delegate_function(*function_args)
                else:
                    # await robot.loop.run_in_executor(None, f, base._SyncProxy(robot))
                    await robot.loop.run_in_executor(None, delegate_function, *function_args)
            finally:
                self._internal_function_finished = True
                self.close()

        #thread = None
        try:
            # if not inspect.iscoroutinefunction(f):
            #     conn_factory = functools.partial(conn_factory, _sync_abort_future=abort_future)
            #thread = threading.Thread(target=run_function)
            # thread.start()
            lt = _LoopThread(robot.loop, f=run_function, argument=robot)
            lt.start()

            self._main_window.initialize(self._on_window_update)
            self._view_controller.initialize()

            self._vector_view_manifest.load_assets()

            # use a non-blocking update loop if possible to make exit conditions
            # easier (not supported on all GLUT versions).
            if bool(glutCheckLoop):
                while not self._exit_requested:
                    glutCheckLoop()
            else:
                # This blocks until quit
                glutMainLoop()

            if self._exit_requested and not self._internal_function_finished:
                # Pass the keyboard interrupt on to SDK so that it can close cleanly
                raise KeyboardInterrupt

        except BaseException as e:
            abort_future.set_exception(VectorException(repr(e)))
            raise
        finally:
            lt.stop()

        global opengl_viewer  # pylint: disable=global-statement
        opengl_viewer = None

    def close(self):
        """Called from the SDK when the program is complete and it's time to exit."""
        if not self._exit_requested:
            self._request_exit()

    def _on_robot_state_update(self, _, msg):  # pylint: disable=unused-argument
        """Called from SDK whenever the robot state is updated (so i.e. every engine tick).
        Note: This is called from the SDK thread, so only access safe things
        We can safely capture any robot and world state here, and push to OpenGL
        (main) thread via a thread-safe queue.
        """
        world_frame = opengl_vector.WorldRenderFrame(self._robot)
        self._world_frame_queue.append(world_frame)
