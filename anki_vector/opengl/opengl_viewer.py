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

"""This module provides a 3D visualizer for Vector's world state and a 2D camera window.

It uses PyOpenGL, a Python OpenGL 3D graphics library which is available on most
platforms. It also depends on the Pillow library for image processing.

Example:
    .. testcode::

        import time

        import anki_vector

        with anki_vector.Robot(show_viewer=True,
                               show_3d_viewer=True,
                               enable_face_detection=True,
                               enable_custom_object_detection=True,
                               enable_nav_map_feed=True) as robot:
            time.sleep(10)

Warning:
    This package requires Python to have the PyOpenGL package installed, along
    with an implementation of GLUT (OpenGL Utility Toolkit).

    To install the Python packages on Mac and Linux do ``python3 -m pip install --user "cyb3r_vector_sdk[3dviewer]"``

    To install the Python packages on Windows do ``py -3 -m pip install --user "cyb3r_vector_sdk[3dviewer]"``

    On Windows and Linux you must also install freeglut (macOS / OSX has one
    preinstalled).

    On Linux: ``sudo apt-get install freeglut3``

    On Windows: Go to http://freeglut.sourceforge.net/ to get a ``freeglut.dll``
    file. It's included in any of the `Windows binaries` downloads. Place the DLL
    next to your Python script, or install it somewhere in your PATH to allow any
    script to use it."
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['OpenGLViewer']

import math
import multiprocessing as mp
import sys
from typing import List

from anki_vector import nav_map, util
from . import opengl, opengl_vector


try:
    from OpenGL.GL import (GL_FILL,
                           GL_FRONT_AND_BACK,
                           GL_LIGHTING, GL_NORMALIZE,
                           GL_TEXTURE_2D,
                           glBindTexture, glColor3f, glDisable, glEnable,
                           glMultMatrixf, glPolygonMode, glPopMatrix, glPushMatrix,
                           glScalef, glWindowPos2f)
    from OpenGL.GLUT import (ctypes,
                             GLUT_ACTIVE_ALT, GLUT_ACTIVE_CTRL, GLUT_ACTIVE_SHIFT, GLUT_BITMAP_9_BY_15,
                             GLUT_DOWN, GLUT_LEFT_BUTTON, GLUT_RIGHT_BUTTON, GLUT_VISIBLE,
                             glutBitmapCharacter, glutCheckLoop, glutGetModifiers, glutIdleFunc,
                             glutKeyboardFunc, glutKeyboardUpFunc, glutMainLoop, glutMouseFunc, glutMotionFunc, glutPassiveMotionFunc,
                             glutPostRedisplay, glutSpecialFunc, glutSpecialUpFunc, glutVisibilityFunc)
    from OpenGL.error import NullFunctionError

except ImportError as import_exc:
    opengl.raise_opengl_or_pillow_import_error(import_exc)


# Constants


class _RobotControlIntents():  # pylint: disable=too-few-public-methods
    """Input intents for controlling the robot.

    These are sent from the OpenGL process, and consumed by the main process for
    issuing movement commands on Vector (to provide a remote-control interface).
    """

    def __init__(self, left_wheel_speed=0.0, right_wheel_speed=0.0,
                 lift_speed=0.0, head_speed=0.0, connect_to_light_block=False):
        self.left_wheel_speed = left_wheel_speed
        self.right_wheel_speed = right_wheel_speed
        self.lift_speed = lift_speed
        self.head_speed = head_speed
        self.connect_to_light_block = connect_to_light_block


def _draw_text(font, input_str, x, y, line_height=16, r=1.0, g=1.0, b=1.0):
    """Render text based on window position. The origin is in the bottom-left."""
    glColor3f(r, g, b)
    glWindowPos2f(x, y)
    input_list = input_str.split('\n')
    y = y + (line_height * (len(input_list) - 1))
    for line in input_list:
        glWindowPos2f(x, y)
        y -= line_height
        for ch in line:
            glutBitmapCharacter(font, ctypes.c_int(ord(ch)))


def _glut_install_instructions():
    if sys.platform.startswith('linux'):
        return "Install freeglut: `sudo apt-get install freeglut3`"
    if sys.platform.startswith('darwin'):
        return "GLUT should already be installed by default on macOS!"
    if sys.platform in ('win32', 'cygwin'):
        return "Install freeglut: You can download it from http://freeglut.sourceforge.net/ \n"\
            "You just need the `freeglut.dll` file, from any of the 'Windows binaries' downloads. "\
            "Place the DLL next to your Python script, or install it somewhere in your PATH "\
            "to allow any script to use it."
    return "(Instructions unknown for platform %s)" % sys.platform


class _OpenGLViewController():
    """Controller that registers for keyboard and mouse input through GLUT, and uses them to update
    the camera and listen for a shutdown cue.

    :param shutdown_delegate: Function to call when we want to exit the host OpenGLViewer.
    :param camera: The camera object for the controller to mutate.
    :param input_intent_queue: Sends key commands from the 3D viewer process to the main process.
    :type input_intent_queue: multiprocessing.Queue
    :param viewer: A reference to the owning OpenGLViewer.
    :type viewer: OpenGLViewer
    """

    def __init__(self, shutdown_delegate: callable, camera: opengl.Camera, input_intent_queue: mp.Queue, viewer):

        self._logger = util.get_class_logger(__name__, self)
        self._input_intent_queue = input_intent_queue
        self._last_robot_control_intents = _RobotControlIntents()
        self._is_keyboard_control_enabled = False

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

        self._opengl_viewer = viewer

    #### Public Properties ####

    @property
    def last_robot_position(self):
        return self._last_robot_position

    @last_robot_position.setter
    def last_robot_position(self, last_robot_position):
        self._last_robot_position = last_robot_position

    #### Public Methods ####

    def initialize(self):
        """Sets up the OpenGL window and binds input callbacks to it
        """

        glutKeyboardFunc(self._on_key_down)
        glutSpecialFunc(self._on_special_key_down)

        # [Keyboard/Special]Up methods aren't supported on some old GLUT implementations
        has_keyboard_up = False
        has_special_up = False
        try:
            if bool(glutKeyboardUpFunc):
                glutKeyboardUpFunc(self._on_key_up)
                has_keyboard_up = True
            if bool(glutSpecialUpFunc):
                glutSpecialUpFunc(self._on_special_key_up)
                has_special_up = True
        except NullFunctionError:
            # Methods aren't available on this GLUT version
            pass

        if not has_keyboard_up or not has_special_up:
            # Warn on old GLUT implementations that don't implement much of the interface.
            self._logger.warning("Warning: Old GLUT implementation detected - keyboard remote control of Vector disabled."
                                 "We recommend installing freeglut. %s", _glut_install_instructions())
            self._is_keyboard_control_enabled = False
        else:
            self._is_keyboard_control_enabled = True

        try:
            GLUT_BITMAP_9_BY_15
        except NameError:
            self._logger.warning("Warning: GLUT font not detected. Help message will be unavailable.")

        glutMouseFunc(self._on_mouse_button)
        glutMotionFunc(self._on_mouse_move)
        glutPassiveMotionFunc(self._on_mouse_move)

        glutIdleFunc(self._idle)
        glutVisibilityFunc(self._visible)

    #### Private Methods ####

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
        elif ord(key) == 72 or ord(key) == 104:  # H key
            self._opengl_viewer.show_controls = not self._opengl_viewer.show_controls

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
        right_button = (self._is_mouse_down.get(GLUT_RIGHT_BUTTON, False)
                        or self._is_key_pressed.get(b'x', False))

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

    def _update_intents_for_robot(self):
        # Update driving intents based on current input, and pass to SDK thread
        # so that it can pass the input onto the robot.
        def get_intent_direction(key1, key2):
            # Helper for keyboard inputs that have 1 positive and 1 negative input
            pos_key = self._is_key_pressed.get(key1, False)
            neg_key = self._is_key_pressed.get(key2, False)
            return pos_key - neg_key

        drive_dir = get_intent_direction(b'w', b's')
        turn_dir = get_intent_direction(b'd', b'a')
        lift_dir = get_intent_direction(b'r', b'f')
        head_dir = get_intent_direction(b't', b'g')
        if drive_dir < 0:
            # It feels more natural to turn the opposite way when reversing
            turn_dir = -turn_dir

        # Scale drive speeds with SHIFT (faster) and ALT (slower)
        if self._is_shift_down:
            speed_scalar = 2.0
        elif self._is_alt_down:
            speed_scalar = 0.5
        else:
            speed_scalar = 1.0

        drive_speed = 75.0 * speed_scalar
        turn_speed = 100.0 * speed_scalar

        left_wheel_speed = (drive_dir * drive_speed) + (turn_speed * turn_dir)
        right_wheel_speed = (drive_dir * drive_speed) - (turn_speed * turn_dir)
        lift_speed = 4.0 * lift_dir * speed_scalar
        head_speed = head_dir * speed_scalar

        connect_block = self._is_key_pressed.get(b'c', False)

        control_intents = _RobotControlIntents(left_wheel_speed, right_wheel_speed,
                                               lift_speed, head_speed, connect_block)
        self._input_intent_queue.put(control_intents, True)

    def _idle(self):
        if self._is_keyboard_control_enabled:
            self._update_intents_for_robot()
        glutPostRedisplay()

    def _visible(self, vis):
        # Called from OpenGL when visibility changes (windows are either visible
        # or completely invisible/hidden)
        if vis == GLUT_VISIBLE:
            glutIdleFunc(self._idle)
        else:
            glutIdleFunc(None)


#: A default window resolution provided for OpenGL Vector programs
#: 800x600 is large enough to see detail, while fitting on the smaller
#: end of modern monitors.
default_resolution = [800, 600]

#: A default projector configurate provided for OpenGL Vector programs
#: A Field of View of 45 degrees is common for 3d applications,
#: and a viewable distance range of 1.0 to 1000.0 will provide a
#: visible space comparable with most physical Vector environments.
default_projector = opengl.Projector(
    fov=45.0,
    near_clip_plane=1.0,
    far_clip_plane=1000.0)

#: A default camera object provided for OpenGL Vector programs.
#: Starts close to and looking at the charger.
default_camera = opengl.Camera(
    look_at=util.Vector3(100.0, -25.0, 0.0),
    up=util.Vector3(0.0, 0.0, 1.0),
    distance=500.0,
    pitch=math.radians(40),
    yaw=math.radians(270))

#: A default light group provided for OpenGL Vector programs.
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
    """OpenGL-based 3D Viewer.

    Handles rendering of a 3D world view including navigation map.

    :param close_event: Used to notify each process when done rendering.
    :type close_event: multiprocessing.Event
    :param input_intent_queue: Sends key commands from the 3D viewer process to the main process.
    :type input_intent_queue: multiprocessing.Queue
    :param nav_map_queue: Updates the 3D viewer process with the latest navigation map.
    :type nav_map_queue: multiprocessing.Queue
    :param world_frame_queue: Provides the 3D viewer with details about the world.
    :type world_frame_queue: multiprocessing.Queue
    :param extra_render_function_queue: Functions to be executed in the 3D viewer process.
    :type extra_render_function_queue: multiprocessing.Queue
    :param user_data_queue: A queue that may be used outside the SDK to pass information to the viewer process.
        May be used by ``extra_render_function_queue`` functions.
    :type user_data_queue: multiprocessing.Queue
    :param resolution: Specifies whether to draw controls on the view.
    :param projector: Specifies whether to draw controls on the view.
    :param camera: Specifies whether to draw controls on the view.
    :param lights: Specifies whether to draw controls on the view.
    :param show_viewer_controls: Specifies whether to draw controls on the view.
    """

    def __init__(self,
                 close_event: mp.Event,
                 input_intent_queue: mp.Queue,
                 nav_map_queue: mp.Queue,
                 world_frame_queue: mp.Queue,
                 extra_render_function_queue: mp.Queue,
                 user_data_queue: mp.Queue,
                 resolution: List[int] = None,
                 projector: opengl.Projector = None,
                 camera: opengl.Camera = None,
                 lights: List[opengl.Light] = None,
                 show_viewer_controls: bool = True):
        if resolution is None:
            resolution = default_resolution
        if projector is None:
            projector = default_projector
        if camera is None:
            camera = default_camera
        if lights is None:
            lights = default_lights

        self._close_event = close_event
        self._input_intent_queue = input_intent_queue
        self._nav_map_queue = nav_map_queue
        self._world_frame_queue = world_frame_queue
        self._extra_render_function_queue = extra_render_function_queue
        self._user_data_queue = user_data_queue

        self._logger = util.get_class_logger(__name__, self)
        self._extra_render_calls = []

        self._internal_function_finished = False

        # Controls
        self.show_controls = show_viewer_controls
        self._instructions = '\n'.join(['W, S: Move forward, backward',
                                        'A, D: Turn left, right',
                                        'R, F: Lift up, down',
                                        'T, G: Head up, down',
                                        '',
                                        'C: Connect to LightCube',
                                        '',
                                        'LMB: Rotate camera',
                                        'RMB: Move camera',
                                        'LMB + RMB: Move camera up/down',
                                        'LMB + Z: Zoom camera',
                                        'X: same as RMB',
                                        'TAB: center view on robot',
                                        '',
                                        'H: Toggle help'])

        self._vector_view_manifest = opengl_vector.VectorViewManifest()
        self._main_window = opengl.OpenGLWindow(0, 0, resolution[0], resolution[1], b"Vector 3D Visualizer")

        # Create a 3d projector configuration class.
        self._projector = projector
        self._camera = camera
        self._lights = lights

        self._view_controller = _OpenGLViewController(self.close, self._camera, self._input_intent_queue, self)

        self._latest_world_frame: opengl_vector.WorldRenderFrame = None

    def _render_world_frame(self, world_frame: opengl_vector.WorldRenderFrame):
        """Render the world to the current OpenGL context

        :param world_frame: frame to render
        """
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glEnable(GL_NORMALIZE)  # to re-scale scaled normals

        light_cube_view = self._vector_view_manifest.light_cube_view
        unit_cube_view = self._vector_view_manifest.unit_cube_view
        robot_view = self._vector_view_manifest.robot_view
        nav_map_view = self._vector_view_manifest.nav_map_view

        robot_frame = world_frame.robot_frame
        robot_pose = robot_frame.pose

        try:
            glDisable(GL_LIGHTING)
            nav_map_view.display()

            glEnable(GL_LIGHTING)
            # Render the cube
            for obj in world_frame.cube_frames:
                cube_pose = obj.pose
                if cube_pose is not None and cube_pose.is_comparable(robot_pose):
                    light_cube_view.display(cube_pose)

            # Render the custom objects
            for obj in world_frame.custom_object_frames:
                obj_pose = obj.pose
                if obj_pose is not None and obj_pose.is_comparable(robot_pose):
                    glPushMatrix()
                    obj_matrix = obj_pose.to_matrix()
                    glMultMatrixf(obj_matrix.in_row_order)

                    glScalef(obj.x_size_mm * 0.5,
                             obj.y_size_mm * 0.5,
                             obj.z_size_mm * 0.5)

                    # Only draw solid object for observable custom objects

                    if obj.is_fixed:
                        # fixed objects are drawn as transparent outlined boxes to make
                        # it clearer that they have no effect on vision.
                        FIXED_OBJECT_COLOR = [1.0, 0.7, 0.0, 1.0]
                        unit_cube_view.display(FIXED_OBJECT_COLOR, False)
                    else:
                        CUSTOM_OBJECT_COLOR = [1.0, 0.3, 0.3, 1.0]
                        unit_cube_view.display(CUSTOM_OBJECT_COLOR, True)

                    glPopMatrix()

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
        except BaseException as e:
            self._logger.error('rendering error: {0}'.format(e))

        glDisable(GL_LIGHTING)

        # Draw the Vector robot to the screen
        robot_view.display(robot_frame.pose, robot_frame.head_angle, robot_frame.lift_position)

        if self.show_controls:
            self._draw_controls(world_frame.cube_connected(), world_frame.cube_connecting())

    def _draw_controls(self, cube_connected, cube_connecting):
        try:
            GLUT_BITMAP_9_BY_15
        except NameError:
            pass
        else:
            _draw_text(GLUT_BITMAP_9_BY_15, self._instructions, x=10, y=10)
            if cube_connecting:
                _draw_text(GLUT_BITMAP_9_BY_15, "<connecting...>", x=600, y=10, r=0.75, g=0.5, b=0.0)
            elif cube_connected:
                _draw_text(GLUT_BITMAP_9_BY_15, "<cube connected>", x=600, y=10, r=0.0, g=0.85, b=0.0)
            else:
                _draw_text(GLUT_BITMAP_9_BY_15, "<no cube connected>", x=600, y=10, r=0.75, g=0.75, b=0.75)

    def _render_3d_view(self, window: opengl.OpenGLWindow):
        """Renders 3d objects to an openGL window

        :param window: OpenGL window to render to
        """
        window.prepare_for_rendering(self._projector, self._camera, self._lights)

        try:
            extra_render_call = self._extra_render_function_queue.get(False)
            self._extra_render_calls.append(extra_render_call)
        except mp.queues.Empty:
            pass

        # Update the latest world frame if there is a new one available
        try:
            world_frame = self._world_frame_queue.get(False)  # type: WorldRenderFrame
            if world_frame is not None:
                self._view_controller.last_robot_position = world_frame.robot_frame.pose.position
            self._latest_world_frame = world_frame
        except mp.queues.Empty:
            world_frame = self._latest_world_frame

        try:
            new_nav_map = self._nav_map_queue.get(False)
            if new_nav_map is not None:
                new_nav_map = nav_map.NavMapGrid(new_nav_map, self._logger)
                self._vector_view_manifest.nav_map_view.build_from_nav_map(new_nav_map)
        except mp.queues.Empty:
            # no new nav map - queue is empty
            pass

        if world_frame is not None:
            self._render_world_frame(world_frame)

        for render_call in self._extra_render_calls:
            # Protecting the external calls with pushMatrix so internal transform
            # state changes will not alter other calls
            glPushMatrix()
            try:
                render_call.invoke(self._user_data_queue)
            finally:
                glPopMatrix()

        window.display_rendered_content()

    def _on_window_update(self):
        """Top level display call.
        """
        try:
            self._render_3d_view(self._main_window)

        except KeyboardInterrupt:
            self._logger.info("_display caught KeyboardInterrupt - exitting")
            self._close_event.set()

    def run(self):
        """Turns control of the current thread over to the OpenGL viewer
        """
        self._main_window.initialize(self._on_window_update)
        self._view_controller.initialize()

        self._vector_view_manifest.load_assets()

        # use a non-blocking update loop if possible to make exit conditions
        # easier (not supported on all GLUT versions).
        if bool(glutCheckLoop):
            while not self._close_event.is_set():
                glutCheckLoop()
        else:
            # This blocks until quit
            glutMainLoop()

        if not self._close_event.is_set():
            # Pass the keyboard interrupt on to SDK so that it can close cleanly
            raise KeyboardInterrupt

    def close(self):
        """Called from the SDK when the program is complete and it's time to exit."""
        if not self._close_event.is_set():
            self._close_event.set()
