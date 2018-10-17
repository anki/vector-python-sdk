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

"""This module provides a 3D support classes for openGL, used by opengl_viewer.py

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
__all__ = ['CubeRenderFrame', 'FaceRenderFrame', 'LightCubeView', 'RobotRenderFrame', 'RobotView',
           'UnitCubeView', 'VectorViewManifest', 'WorldRenderFrame']

import math
import time
from typing import List

from anki_vector.faces import Face
from anki_vector.objects import LightCube
from anki_vector.robot import Robot
from anki_vector import util

import opengl

try:
    from OpenGL.GL import (GL_AMBIENT, GL_BLEND, GL_DIFFUSE, GL_FILL, GL_FRONT, GL_FRONT_AND_BACK, GL_LIGHTING, GL_LINE, GL_ONE_MINUS_SRC_ALPHA, GL_POLYGON, GL_SHININESS, GL_SPECULAR, GL_SRC_ALPHA,
                           glBegin, glBlendFunc, glColor, glDisable, glEnable, glEnd, glMaterialfv, glMultMatrixf, glNormal3fv,
                           glPolygonMode, glPopMatrix, glPushMatrix, glRotatef, glScalef, glTranslatef, glVertex3fv)

except ImportError as import_exc:
    opengl.raise_opengl_or_pillow_import_error(import_exc)


#: The object file used to render the robot.
VECTOR_MODEL_FILE = "vector.obj"

#: The object file used to render the cube.
CUBE_MODEL_FILE = "cube.obj"

# The following offsets are used in displaying the Vector 3d model.
# These values are tuned to reflect the vector.obj file, and do not
# necessarily reflect the actual measurements of the physical robot.

#: The length of Vector's lift arm
LIFT_ARM_LENGTH_MM = 66.0

#: The height above ground of Vector's lift arm's pivot
LIFT_PIVOT_HEIGHT_MM = 45.0

#: Angle of the lift in the object's initial default pose.
LIFT_ANGLE_IN_DEFAULT_POSE = -11.36

#: Pivot offset for where the fork rotates around itself
FORK_PIVOT_X = 3.0
FORK_PIVOT_Z = 3.4

#: Offset for the axel that the upper arm rotates around.
UPPER_ARM_PIVOT_X = -3.73
UPPER_ARM_PIVOT_Z = 4.47

#: Offset for the axel that the lower arm rotates around.
LOWER_ARM_PIVOT_X = -3.74
LOWER_ARM_PIVOT_Z = 3.27

#: Offset for the pivot that the head rotates around.
HEAD_PIVOT_X = -1.1
HEAD_PIVOT_Z = 4.75


_resource_package = __name__  # All resources are in subdirectories from this file's location


class UnitCubeView(opengl.PrecomputedView):
    """A view containing a cube of unit size at the origin."""

    def __init__(self):

        self._display_list_name = 'cube'

        super(UnitCubeView, self).__init__()
        self.build_from_render_function(self._display_list_name, self._render_cube)

    @staticmethod
    def _render_cube():
        """Pre renders a unit-size cube, with normals, centered at the origin.
        """
        # build each of the 6 faces
        for face_index in range(6):
            # calculate normal and vertices for this face
            vertex_normal = [0.0, 0.0, 0.0]
            vertex_pos_options1 = [-1.0, 1.0, 1.0, -1.0]
            vertex_pos_options2 = [1.0, 1.0, -1.0, -1.0]
            face_index_even = ((face_index % 2) == 0)
            # odd and even faces point in opposite directions
            normal_dir = 1.0 if face_index_even else -1.0
            if face_index < 2:
                # -X and +X faces (vert positions differ in Y,Z)
                vertex_normal[0] = normal_dir
                v1i = 1
                v2i = 2
            elif face_index < 4:
                # -Y and +Y faces (vert positions differ in X,Z)
                vertex_normal[1] = normal_dir
                v1i = 0
                v2i = 2
            else:
                # -Z and +Z faces (vert positions differ in X,Y)
                vertex_normal[2] = normal_dir
                v1i = 0
                v2i = 1

            vertex_pos = list(vertex_normal)

            # Polygon (N verts) with optional normals and tex coords
            glBegin(GL_POLYGON)
            for vert_index in range(4):
                vertex_pos[v1i] = vertex_pos_options1[vert_index]
                vertex_pos[v2i] = vertex_pos_options2[vert_index]
                glNormal3fv(vertex_normal)
                glVertex3fv(vertex_pos)
            glEnd()

    def display(self, color: List[float], draw_solid: bool):
        """Displays the cube with a specific color.

        :param color: Color to display the cube.
        :param draw_solid: Whether to draw solid polygons (False to draw wireframe).
        """
        glColor(color)

        if draw_solid:
            ambient_color = [color[0] * 0.1, color[1] * 0.1, color[2] * 0.1, 1.0]
        else:
            ambient_color = color
        glMaterialfv(GL_FRONT, GL_AMBIENT, ambient_color)
        glMaterialfv(GL_FRONT, GL_DIFFUSE, color)
        glMaterialfv(GL_FRONT, GL_SPECULAR, color)

        glMaterialfv(GL_FRONT, GL_SHININESS, 10.0)

        if draw_solid:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        else:
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

        self.display_by_key(self._display_list_name)


class LightCubeView(opengl.PrecomputedView):
    """A view containing the Vector Light Cube 3D Model.

    :param mesh_data: Source Mesh Data for the light cube.
    """

    def __init__(self, mesh_data: opengl.MeshData):

        super(LightCubeView, self).__init__()
        self.build_from_mesh_data(mesh_data)

    def display(self, pose: util.Pose):
        """Displays the precomputed view at a specific pose in 3d space.

        :param pose: Where to display the cube.
        """
        glPushMatrix()

        # TODO if cube_pose.is_accurate is False, render half-translucent?
        #  (This would require using a shader, or having duplicate objects)

        cube_matrix = pose.to_matrix()
        glMultMatrixf(cube_matrix.in_row_order)

        # Cube is drawn slightly larger than the 10mm to 1 cm scale, as the model looks small otherwise
        cube_scale_amt = 10.7
        glScalef(cube_scale_amt, cube_scale_amt, cube_scale_amt)

        self.display_all()
        glPopMatrix()


class RobotView(opengl.PrecomputedView):
    """A view containing the Vector robot 3D Model.

    :param mesh_data: Source Mesh Data for the robot.
    """

    def __init__(self, mesh_data: opengl.MeshData):

        super(RobotView, self).__init__()
        self.build_from_mesh_data(mesh_data)

    def _display_vector_body(self):
        """Displays the robot's body to the current OpenGL context
        """

        # Render the static body meshes - first the main body:
        self.display_by_key("body_geo")
        # Render the left treads and wheels
        self.display_by_key("trackBase_L_geo")
        self.display_by_key("wheel_BL_geo")
        self.display_by_key("wheel_FL_geo")
        self.display_by_key("tracks_L_geo")
        # Render the right treads and wheels
        self.display_by_key("trackBase_R_geo")
        self.display_by_key("wheel_BR_geo")
        self.display_by_key("wheel_FR_geo")
        self.display_by_key("tracks_R_geo")

    def _display_vector_lift(self, lift_angle: float):
        """Displays the robot's lift to the current OpenGL context

        :param lift_angle: the angle of the lift in radians
        """

        # Render the fork at the front (but not the arms)
        glPushMatrix()
        # The fork rotates first around upper arm (to get it to the correct position).
        glTranslatef(UPPER_ARM_PIVOT_X, 0.0, UPPER_ARM_PIVOT_Z)
        glRotatef(lift_angle, 0, 1, 0)
        glTranslatef(-UPPER_ARM_PIVOT_X, 0.0, -UPPER_ARM_PIVOT_Z)
        # The fork then rotates back around itself as it always hangs vertically.
        glTranslatef(FORK_PIVOT_X, 0.0, FORK_PIVOT_Z)
        glRotatef(-lift_angle, 0, 1, 0)
        glTranslatef(-FORK_PIVOT_X, 0.0, -FORK_PIVOT_Z)
        # Render
        self.display_by_key("fork_geo")
        glPopMatrix()

        # Render the upper arms:
        glPushMatrix()
        # Rotate the upper arms around the upper arm joint
        glTranslatef(UPPER_ARM_PIVOT_X, 0.0, UPPER_ARM_PIVOT_Z)
        glRotatef(lift_angle, 0, 1, 0)
        glTranslatef(-UPPER_ARM_PIVOT_X, 0.0, -UPPER_ARM_PIVOT_Z)
        # Render
        self.display_by_key("uprArm_L_geo")
        self.display_by_key("uprArm_geo")
        glPopMatrix()

        # Render the lower arms:
        glPushMatrix()
        # Rotate the lower arms around the lower arm joint
        glTranslatef(LOWER_ARM_PIVOT_X, 0.0, LOWER_ARM_PIVOT_Z)
        glRotatef(lift_angle, 0, 1, 0)
        glTranslatef(-LOWER_ARM_PIVOT_X, 0.0, -LOWER_ARM_PIVOT_Z)
        # Render
        self.display_by_key("lwrArm_L_geo")
        self.display_by_key("lwrArm_R_geo")
        glPopMatrix()

    def _display_vector_head(self, head_angle: float):
        """Displays the robot's head to the current OpenGL context

        :param head_angle: the angle of the lift in radians
        """

        glPushMatrix()
        # Rotate the head around the pivot
        glTranslatef(HEAD_PIVOT_X, 0.0, HEAD_PIVOT_Z)
        glRotatef(-head_angle, 0, 1, 0)
        glTranslatef(-HEAD_PIVOT_X, 0.0, -HEAD_PIVOT_Z)
        # Render all of the head meshes
        self.display_by_key("head_geo")
        # Screen
        self.display_by_key("backScreen_mat")
        self.display_by_key("screenEdge_geo")
        self.display_by_key("overscan_1_geo")
        # Eyes
        self.display_by_key("eye_L_geo")
        self.display_by_key("eye_R_geo")
        # Eyelids
        self.display_by_key("eyeLid_R_top_geo")
        self.display_by_key("eyeLid_L_top_geo")
        self.display_by_key("eyeLid_L_btm_geo")
        self.display_by_key("eyeLid_R_btm_geo")
        # Face cover (drawn last as it's translucent):
        self.display_by_key("front_Screen_geo")
        glPopMatrix()

    def display(self, pose: util.Pose, head_angle: util.Angle, lift_position: util.Distance):
        """Displays the precomputed view at a specific pose in 3d space.

        :param pose: Where to display the robot.
        """
        if not self._display_lists:
            return

        robot_matrix = pose.to_matrix()
        head_angle_degrees = head_angle.degrees

        # Get the angle of Vector's lift for rendering - we subtract the angle
        # of the lift in the default pose in the object, and apply the inverse
        # rotation
        sin_angle = (lift_position.distance_mm - LIFT_PIVOT_HEIGHT_MM) / LIFT_ARM_LENGTH_MM
        angle_radians = math.asin(sin_angle)

        lift_angle = -(angle_radians - LIFT_ANGLE_IN_DEFAULT_POSE)

        glPushMatrix()
        glEnable(GL_LIGHTING)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_BLEND)

        glMultMatrixf(robot_matrix.in_row_order)

        robot_scale_amt = 10.0  # cm to mm
        glScalef(robot_scale_amt, robot_scale_amt, robot_scale_amt)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        self._display_vector_body()
        self._display_vector_lift(lift_angle)
        self._display_vector_head(head_angle_degrees)

        glDisable(GL_LIGHTING)
        glPopMatrix()


class VectorViewManifest():
    """A collection of Vector-specific source data containing views to display.
    """

    def __init__(self):
        self._light_cube_view: LightCubeView = None
        self._unit_cube_view: UnitCubeView = None
        self._robot_view: RobotView = None

    @property
    def light_cube_view(self) -> LightCubeView:
        """A precomputed view of Vector's light cube."""
        return self._light_cube_view

    @property
    def unit_cube_view(self) -> UnitCubeView:
        """A precomputed view of a unit cube.

        This is used for representing detected faces.
        """
        return self._unit_cube_view

    @property
    def robot_view(self) -> RobotView:
        """A precomputed view of the robot."""
        return self._robot_view

    def load_assets(self):
        """Loads all assets needed for the view manifest, and precomputes them
        into cached views.
        """
        resource_context = opengl.ResourceManager(_resource_package)

        # Load 3D objects
        robot_mesh_data = opengl.MeshData(resource_context, VECTOR_MODEL_FILE)
        self._robot_view = RobotView(robot_mesh_data)

        # Load the cube
        cube_mesh_data = opengl.MeshData(resource_context, CUBE_MODEL_FILE)
        self._light_cube_view = LightCubeView(cube_mesh_data)

        self._unit_cube_view = UnitCubeView()


class CubeRenderFrame():  # pylint: disable=too-few-public-methods
    """Minimal copy of a Cube's state for 1 frame of rendering.

    :param cube: the cube object to be rendered.
    """

    def __init__(self, cube: LightCube):  # pylint: disable=useless-super-delegation
        self.pose = cube.pose
        self.last_observed_time = cube.last_observed_time

    @property
    def time_since_last_seen(self) -> float:
        """:return: time since this element was last seen (math.inf if never)"""
        if self.last_observed_time is None:
            return math.inf
        return time.time() - self.last_observed_time


class FaceRenderFrame():  # pylint: disable=too-few-public-methods
    """Minimal copy of a Face's state for 1 frame of rendering.

    :param face: the face object to be rendered.
    """

    def __init__(self, face: Face):  # pylint: disable=useless-super-delegation
        self.pose = face.pose
        self.last_observed_time = face.last_observed_time

    @property
    def time_since_last_seen(self) -> float:
        """:return: time since this element was last seen (math.inf if never)"""
        if self.last_observed_time is None:
            return math.inf
        return time.time() - self.last_observed_time


class RobotRenderFrame():  # pylint: disable=too-few-public-methods
    """Minimal copy of a Robot's state for 1 frame of rendering.

    :param robot: the robot object to be rendered.
    """

    def __init__(self, robot: Robot):
        self.pose = robot.pose
        if robot.head_angle_rad is None:
            self.head_angle = util.radians(0.0)
        else:
            self.head_angle = util.radians(robot.head_angle_rad)
        if robot.lift_height_mm is None:
            self.lift_position = util.distance_mm(0.0)
        else:
            self.lift_position = util.distance_mm(robot.lift_height_mm)


class WorldRenderFrame():  # pylint: disable=too-few-public-methods
    """Minimal copy of the World's state for 1 frame of rendering.

    :param robot: the robot object to be rendered, which also has handles to the other objects
        defined in it's world class.
    """

    def __init__(self, robot: Robot):

        self.robot_frame = RobotRenderFrame(robot)

        self.cube_frames: List[CubeRenderFrame] = []
        if robot.world.connected_light_cube is None:
            self.cube_frames.append(None)
        else:
            self.cube_frames.append(CubeRenderFrame(robot.world.connected_light_cube))

        self.face_frames: List[FaceRenderFrame] = []
        for face in robot.world.visible_faces:
            # Ignore faces that have a newer version (with updated id)
            # or if they haven't been seen in a while).
            if not face.has_updated_face_id and (face.time_since_last_seen < 60):
                self.face_frames.append(FaceRenderFrame(face))
