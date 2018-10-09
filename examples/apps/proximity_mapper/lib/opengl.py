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

It uses PyOpenGL, a Python OpenGL 3D graphics library which is available on most
platforms. It also depends on the Pillow library for image processing.

Warning:
    This package requires Python to have the PyOpenGL package installed, along
    with an implementation of GLUT (OpenGL Utility Toolkit).

    To install the Python packages do ``pip3 install --user "anki_vector[3dviewer]"``

    On Windows and Linux you must also install freeglut (macOS / OSX has one
    preinstalled).

    On Linux: ``sudo apt-get install freeglut3``

    On Windows: Go to http://freeglut.sourceforge.net/ to get a ``freeglut.dll``
    file. It's included in any of the `Windows binaries` downloads. Place the DLL
    next to your Python script, or install it somewhere in your PATH to allow any
    script to use it."
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['Camera', 'DynamicTexture', 'MaterialLibrary', 'MeshData', 'MeshFace', 'MeshGroup', 'OpenGLWindow',
           'PrecomputedView', 'ResourceManager',
           'raise_opengl_or_pillow_import_error']

import math
import sys
from typing import List, Dict

from pkg_resources import resource_stream

from anki_vector import util


class InvalidOpenGLGlutImplementation(ImportError):
    """Raised by opengl viewer if no valid GLUT implementation available."""


#: Adds context to exceptions raised from attempts to import OpenGL libraries
def raise_opengl_or_pillow_import_error(opengl_import_exc):
    if isinstance(opengl_import_exc, InvalidOpenGLGlutImplementation):
        raise NotImplementedError('GLUT (OpenGL Utility Toolkit) is not available:\n%s'
                                  % opengl_import_exc)
    else:
        # TODO Update to: 'Do `pip3 install --user anki_vector[3dviewer]` from `pip3 install PyOpenGL`
        raise NotImplementedError('opengl is not available; '
                                  'make sure the PyOpenGL and Pillow packages are installed:\n'
                                  'Do `pip3 install PyOpenGL Pillow` to install. Error: %s' % opengl_import_exc)


try:
    from OpenGL.GL import (GL_AMBIENT, GL_AMBIENT_AND_DIFFUSE, GL_CCW, GL_COLOR_BUFFER_BIT, GL_COMPILE, GL_DEPTH_BUFFER_BIT, GL_DEPTH_TEST, GL_DIFFUSE,
                           GL_FRONT, GL_LIGHT0, GL_LINEAR, GL_MODELVIEW, GL_POLYGON, GL_PROJECTION, GL_POSITION, GL_RGBA, GL_SHININESS, GL_SMOOTH, GL_SPECULAR,
                           GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_TEXTURE_MAG_FILTER, GL_UNSIGNED_BYTE,
                           glBegin, glBindTexture, glCallList, glClear, glClearColor, glColor, glDisable, glEnable,
                           glEnd, glEndList, glFrontFace, glGenLists, glGenTextures, glLoadIdentity, glLightfv, glMaterialfv, glMatrixMode, glNewList,
                           glNormal3fv, glScalef, glShadeModel, glTexCoord2fv, glTexImage2D, glTexParameteri,
                           glTexSubImage2D, glVertex3fv, glViewport)
    from OpenGL.GLU import gluLookAt, gluPerspective
    from OpenGL.GLUT import (glutCreateWindow, glutDisplayFunc, glutIdleFunc, glutInit, glutInitDisplayMode,
                             glutInitWindowPosition, glutInitWindowSize, glutPostRedisplay, glutReshapeFunc,
                             glutSetWindow, glutSwapBuffers, glutVisibilityFunc,
                             GLUT_DEPTH, GLUT_DOUBLE, GLUT_RGB, GLUT_VISIBLE)
    from OpenGL.error import NullFunctionError

    from PIL import Image

except ImportError as import_exc:
    raise_opengl_or_pillow_import_error(import_exc)


# Check if OpenGL imported correctly and bound to a valid GLUT implementation


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


def _verify_glut_init():
    # According to the documentation, just checking bool(glutInit) is supposed to be enough
    # However on Windows with no GLUT DLL that can still pass, even if calling the method throws a null function error.
    if bool(glutInit):
        try:
            glutInit()
            return True
        except NullFunctionError as _:
            pass

    return False


if not _verify_glut_init():
    raise InvalidOpenGLGlutImplementation(_glut_install_instructions())


class ResourceManager():
    """Handles returning file resources by keys.  The current implementation delegates to resource_stream
    directly.

    :param context_id: Key used for identifying this context
    """

    def __init__(self, context_id: str):
        self._context_id = context_id

    @property
    def context_id(self) -> str:
        """Key used for identifying this context."""
        return self._context_id

    def load(self, *args: str):
        """Loads a resource given a groups of key arguments.

        Since the resource_stream path is non_stantard with os.path.join, this resolve is encapsulated inside
        the resource manager.  The context that these resources are files on disk is similarly encapsulated.
        All client classes only need match keys with returned data.

        :param *args: string keys for identifying the asset.
        """
        resource_path = '/'.join(map(str, args))  # Note: Deliberately not os.path.join, for use with pkg_resources
        return resource_stream(self._context_id, resource_path)


class DynamicTexture:
    """Wrapper around An OpenGL Texture that can be dynamically updated."""

    def __init__(self):
        self._texId = glGenTextures(1)
        self._width = None
        self._height = None
        # Bind an ID for this texture
        glBindTexture(GL_TEXTURE_2D, self._texId)
        # Use bilinear filtering if the texture has to be scaled
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    def bind(self):
        """Bind the texture for rendering."""
        glBindTexture(GL_TEXTURE_2D, self._texId)

    def update(self, pil_image: Image.Image):
        """Update the texture to contain the provided image.

        :param pil_image: The image to write into the texture.
        """
        # Ensure the image is in RGBA format and convert to the raw RGBA bytes.
        image_width, image_height = pil_image.size
        image = pil_image.convert("RGBA").tobytes("raw", "RGBA")

        # Bind the texture so that it can be modified.
        self.bind()
        if (self._width == image_width) and (self._height == image_height):
            # Same size - just need to update the texels.
            glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, image_width, image_height,
                            GL_RGBA, GL_UNSIGNED_BYTE, image)
        else:
            # Different size than the last frame (e.g. the Window is resizing)
            # Create a new texture of the correct size.
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, image_width, image_height,
                         0, GL_RGBA, GL_UNSIGNED_BYTE, image)

        self._width = image_width
        self._height = image_height


class MaterialLibrary():  # pylint: disable=too-few-public-methods
    """Load a .mtl material asset, and return the contents as a dictionary.

    Supports the subset of MTL required for the Vector 3D viewer assets.

    :param resource_manager: Manager to load resources from.
    :param asset_key: The key of the asset to load.
    """

    def __init__(self, resource_context: ResourceManager, asset_key: str):
        self._contents = {}
        current_mtl: dict = None

        file_data = resource_context.load('assets', asset_key)

        for line in file_data:
            line = line.decode("utf-8")  # Convert bytes line to a string
            if line.startswith('#'):
                # Ignore comments in the file.
                continue

            values = line.split()
            if not values:
                # Ignore empty lines.
                continue

            attribute_name = values[0]
            if attribute_name == 'newmtl':
                # Create a new empty material.
                current_mtl = self._contents[values[1]] = {}
            elif current_mtl is None:
                raise ValueError("mtl file must start with newmtl statement")
            elif attribute_name == 'map_Kd':
                # Diffuse texture map - load the image into memory.
                image_name = values[1]
                image_file_data = resource_context.load('assets', image_name)
                with Image.open(image_file_data) as image:
                    image_width, image_height = image.size
                    image = image.convert("RGBA").tobytes("raw", "RGBA")

                # Bind the image as a texture that can be used for rendering.
                texture_id = glGenTextures(1)
                current_mtl['texture_Kd'] = texture_id  # pylint: disable=unsupported-assignment-operation

                glBindTexture(GL_TEXTURE_2D, texture_id)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, image_width, image_height,
                             0, GL_RGBA, GL_UNSIGNED_BYTE, image)
            else:
                # Store the values for this attribute as a list of float values.
                current_mtl[attribute_name] = list(map(float, values[1:]))  # pylint: disable=unsupported-assignment-operation

    def get_material_by_name(self, name: str) -> dict:
        """Returns a dict of material attributes"""
        return self._contents[name]


class MeshFace():
    """A face polygon in 3d space - the basic building block of 3D models.

    The actual coordinate data is stored in tables on the host mesh, the face contains
    indexes to those table denoting which values should be used in rendering.

    :param position_ids: Worldspace position ids on the host mesh for this face's vertices.
    :param normal_ids: Normal direction ids on the host mesh for this face's vertices.
    :param tex_ids: Texture coordinate ids on the host mesh for this face's vertices.
    :param active_material: Material name used to render this face.
    """

    def __init__(self, position_ids: List[int], normal_ids: List[int], tex_ids: List[int], active_material: str):
        self._position_ids = position_ids
        self._normal_ids = normal_ids
        self._tex_ids = tex_ids

        self._vertex_count = len(position_ids)

        self._material = active_material

    @property
    def position_ids(self) -> List[int]:
        """Worldspace position ids on the host mesh for this face's vertices."""
        return self._position_ids

    @property
    def normal_ids(self) -> List[int]:
        """Normal direction ids on the host mesh for this face's vertices."""
        return self._normal_ids

    @property
    def tex_ids(self) -> List[int]:
        """Texture coordinate ids on the host mesh for this face's vertices."""
        return self._tex_ids

    @property
    def material(self) -> str:
        """Material name used to render this face."""
        return self._material

    @property
    def vertex_count(self) -> int:
        """The number of vertices on this face - will be either 3 for a triangle, or 4 for a quad"""
        return self._vertex_count


class MeshGroup():
    """A colletions of face polygons which can be rendered as a group by name.

    :param name: The name associated with this part of the 3d mesh collection.
    """

    def __init__(self, name: str):
        self._name = name
        self._faces: List(MeshFace) = []

    @property
    def name(self) -> str:
        """The name associated with the mesh group."""
        return self._name

    @property
    def faces(self) -> List[MeshFace]:
        """All faces associated with the mesh group."""
        return self._faces

    def add_face_by_obj_data(self, source_values: list, active_material: str):
        """Adds a new face to the mesh group.

        Face source data is made up of 3 or 4 vertices
         - e.g. `f v1 v2 v3` or `f v1 v2 v3 v4`

        where each vertex definition is multiple indexes seperated by
        slashes and can follow the following formats:

        position_index
        position_index/tex_coord_index
        position_index/tex_coord_index/normal_index
        position_index//normal_index

        :param source_values: obj data to parse for this face
        :param active_material: the material used to render this face
        """

        position_ids: List(int) = []
        normal_ids: List(int) = []
        tex_ids: List(int) = []

        for vertex in source_values:
            vertex_components = vertex.split('/')

            position_ids.append(int(vertex_components[0]))

            # There's only a texture coordinate if there's at least 2 entries and the 2nd entry is non-zero length
            if len(vertex_components) >= 2 and vertex_components[1]:
                tex_ids.append(int(vertex_components[1]))
            else:
                # OBJ file indexing starts at 1, so use 0 to indicate no entry
                tex_ids.append(0)

            # There's only a normal if there's at least 2 entries and the 2nd entry is non-zero length
            if len(vertex_components) >= 3 and vertex_components[2]:
                normal_ids.append(int(vertex_components[2]))
            else:
                # OBJ file indexing starts at 1, so use 0 to indicate no entry
                normal_ids.append(0)

        self._faces.append(MeshFace(position_ids, normal_ids, tex_ids, active_material))


class MeshData():
    """The loaded / parsed contents of a 3D Wavefront OBJ file.

    This is the intermediary step between the file on the disk, and a renderable
    3D object. It supports the subset of the OBJ file that was used in the
    Vector and Cube assets, and does not attempt to exhaustively support every
    possible setting.

    :param resource_manager: The resource manager to load this mesh from.
    :param asset_key: The key of the OBJ file to load from the resource manager.
    """

    def __init__(self, resource_manager: ResourceManager, asset_key: str):

        # All worldspace vertex positions in this mesh (coordinates stored as list of 3 floats).
        self._vertices: List[List[float]] = []
        # All directional vertex normals in this mesh (coordinates stored as list of 3 floats).
        self._normals: List[List[float]] = []
        # All texture coordinates in this mesh (coordinates stored as list of 2 floats).
        self._tex_coords: List[List[float]] = []

        # All supported mesh groups, indexed by group name.
        self._groups: Dict[str, MeshGroup] = {}

        # A container that MTL material attribute dicts can be fetched from by string key.
        self._material_library: MaterialLibrary = None

        # Resource manager that can be used to load internally referenced assets
        self._resource_manager = resource_manager

        self._logger = util.get_class_logger(__name__, self)

        self.load_from_obj_asset(asset_key)

    @property
    def vertices(self) -> List[List[float]]:
        """All worldspace vertex positions in this mesh."""
        return self._vertices

    @property
    def normals(self) -> List[List[float]]:
        """All directional vertex normals in this mesh."""
        return self._normals

    @property
    def tex_coords(self) -> List[List[float]]:
        """All texture coordinates in this mesh."""
        return self._tex_coords

    @property
    def groups(self) -> Dict[str, MeshGroup]:
        """All supported mesh groups, indexed by group name."""
        return self._groups

    @property
    def material_library(self) -> MaterialLibrary:
        """A container that MTL material attribute dicts can be fetched from by string key."""
        return self._material_library

    def load_from_obj_asset(self, asset_key: str):  # pylint: disable=too-many-branches
        """Loads all mesh data from a specified resource.

        :param asset_key: Key for the desired OBJ asset in the resource_manager.
        """
        active_group_name: str = None
        active_material: str = None

        file_data = self._resource_manager.load('assets', asset_key)

        for data_entry in file_data:

            line = data_entry.decode("utf-8")  # Convert bytes to string
            if line.startswith('#'):
                # ignore comments in the file
                continue

            values = line.split()
            if not values:
                # ignore empty lines
                continue

            if values[0] == 'v':
                # vertex position
                v = list(map(float, values[1:4]))
                self._vertices.append(v)
            elif values[0] == 'vn':
                # vertex normal
                v = list(map(float, values[1:4]))
                self._normals.append(v)
            elif values[0] == 'vt':
                # texture coordinate
                v = list(map(float, values[1:3]))
                self._tex_coords.append(v)
            elif values[0] in ('usemtl', 'usemat'):
                # material
                active_material = values[1]
            elif values[0] == 'mtllib':
                # material library (a filename)
                self._material_library = MaterialLibrary(self._resource_manager, values[1])
            elif values[0] == 'f':
                if not active_group_name in self._groups:
                    self._groups[active_group_name] = MeshGroup(active_group_name)

                group = self._groups[active_group_name]
                group.add_face_by_obj_data(values[1:], active_material)

            elif values[0] == 'o':
                # object name - ignore
                continue
            elif values[0] == 'g':
                # group name (for a sub-mesh)
                active_group_name = values[1]
            elif values[0] == 's':
                # smooth shading (1..20, and 'off') - ignore
                continue
            else:
                self._logger.warning("LoadedObjFile Ignoring unhandled type '%s' in line %s",
                                     values[0], values)


class PrecomputedView():
    """A collection of static 3D object which are pre-computed on the graphics card, so they can
    be quickly drawn when needed."""

    def __init__(self):
        self._display_lists = {}

    @staticmethod
    def _apply_material(material: dict):
        """Utility function to apply a specific MTL material to the current
        openGL rendering state.

        :param material: A dictionary of MTL attributes defining a material.
        """
        def _as_rgba(color):
            if len(color) >= 4:
                return color
            # RGB - add alpha defaulted to 1
            return color + [1.0]

        if 'texture_Kd' in material:
            # use diffuse texture map
            glBindTexture(GL_TEXTURE_2D, material['texture_Kd'])
        else:
            # No texture map
            glBindTexture(GL_TEXTURE_2D, 0)

        # Diffuse light
        mtl_kd_rgba = _as_rgba(material['Kd'])
        glColor(mtl_kd_rgba)

        # Ambient light
        if 'Ka' in material:
            mtl_ka_rgba = _as_rgba(material['Ka'])
            glMaterialfv(GL_FRONT, GL_AMBIENT, mtl_ka_rgba)
            glMaterialfv(GL_FRONT, GL_DIFFUSE, mtl_kd_rgba)
        else:
            glMaterialfv(GL_FRONT, GL_AMBIENT_AND_DIFFUSE, mtl_kd_rgba)

        # Specular light
        if 'Ks' in material:
            mtl_ks_rgba = _as_rgba(material['Ks'])
            glMaterialfv(GL_FRONT, GL_SPECULAR, mtl_ks_rgba)
            if 'Ns' in material:
                specular_exponent = material['Ns']
                glMaterialfv(GL_FRONT, GL_SHININESS, specular_exponent)

    def build_from_mesh_data(self, mesh_data: MeshData):
        """Uses a loaded mesh to create 3d geometry to store in the view.

        All groups in the mesh will pre-computed and stored by name.

        :param mesh_data: the source data that 3d geometry will be pre-computed from.
        """
        material_library = mesh_data.material_library

        for key in mesh_data.groups:
            new_gl_list = glGenLists(1)
            glNewList(new_gl_list, GL_COMPILE)

            group = mesh_data.groups[key]

            glEnable(GL_TEXTURE_2D)
            glFrontFace(GL_CCW)

            for face in group.faces:
                self._apply_material(material_library.get_material_by_name(face.material))

                # Polygon (N verts) with optional normals and tex coords
                glBegin(GL_POLYGON)
                for i in range(face.vertex_count):
                    normal_index = face.normal_ids[i]
                    if normal_index > 0:
                        glNormal3fv(mesh_data.normals[normal_index - 1])
                    tex_coord_index = face.tex_ids[i]
                    if tex_coord_index > 0:
                        glTexCoord2fv(mesh_data.tex_coords[tex_coord_index - 1])
                    glVertex3fv(mesh_data.vertices[face.position_ids[i] - 1])
                glEnd()

            glDisable(GL_TEXTURE_2D)
            glEndList()

            self._display_lists[key] = new_gl_list

    def build_from_render_function(self, name: str, f: callable, *args):
        """Uses an externally provided function to create 3d geometry to store in the view.

        :param name: the key this pre-computed geometry can be draw from.
        :param f: the function used to create the 3d geometry.
        :param *args: any parameters the supplied function is expecting.
        """
        new_gl_list = glGenLists(1)
        glNewList(new_gl_list, GL_COMPILE)
        f(*args)
        glEndList()

        self._display_lists[name] = new_gl_list

    def display_by_key(self, key: str):
        """Renders a specific piece of geometry from the view collection.

        :param key: The pre-computed object to render.
        """
        try:
            glCallList(self._display_lists[key])
        except KeyError:
            raise KeyError('No display list with key {0} present on PrerenderedView'.format(key))

    def display_all(self):
        """Renders all pre-computed geometry in the view collection."""
        for display_list in self._display_lists.values():
            glCallList(display_list)


class Camera():
    """Class containing the state of a 3d camera, used to transform all object in a scene with
    relation to a particular point of view.

    This class is meant to be mutated at run time.

    :param look_at: The initial target of the camera.
    :param up: The initial up vector of the camera.
    :param distance: The initial distance between the camera and it's target.
    :param pitch: The camera's current rotation about its X axis
    :param yaw: The camera's current rotation about its up axis
    """

    def __init__(self, look_at: util.Vector3, up: util.Vector3, distance: float, pitch: float, yaw: float):
        # Camera position and orientation defined by a look-at positions
        # and a pitch/and yaw to rotate around that along with a distance
        self._look_at = look_at
        self._pitch = pitch
        self._yaw = yaw
        self._distance = distance
        self._pos = util.Vector3(0, 0, 0)
        self._up = up
        self._update_pos()

    @property
    def look_at(self) -> util.Vector3:
        """The target position of the camera"""
        return self._look_at

    @look_at.setter
    def look_at(self, look_at):
        self._look_at = look_at

    def move(self, forward_amount: float = 0.0, right_amount: float = 0.0, up_amount: float = 0.0):
        """Offsets the camera's position incrementally.

        :param forward_amount: distance to move along the camera's current forward heading.
        :param right_amount: distance to move along a right angle to the camera's current forward heading.
        :param up_amount: distance to move along the camera's up vector.
        """
        self._look_at += self._up * up_amount

        # Move forward/back and left/right
        pitch = self._pitch
        yaw = self._yaw
        camera_offset = util.Vector3(math.cos(yaw), math.sin(yaw), math.sin(pitch))

        heading = math.atan2(camera_offset.y, camera_offset.x)
        half_pi = math.pi * 0.5

        self._look_at += util.Vector3(
            right_amount * math.cos(heading + half_pi),
            right_amount * math.sin(heading + half_pi),
            0.0)

        self._look_at += util.Vector3(
            forward_amount * math.cos(heading),
            forward_amount * math.sin(heading),
            0.0)

    def zoom(self, amount: float):
        """Moves the camera closer or further from it's target point.

        :param amount: distance to zoom in or out, automatically minimized at 0.1
        """
        self._distance = max(0.1, self._distance + amount)

    def turn(self, yaw_delta: float, pitch_delta: float):
        """Incrementally turns the camera.

        :param yaw_delta: Amount to rotate around the camera's up axis.
        :param pitch_delta: Amount to rotate around the camera's X axis.  This is automatically capped between +/- pi/2
        """
        # Adjust the Camera pitch and yaw
        self._pitch = (self._pitch - pitch_delta)
        self._yaw = (self._yaw + yaw_delta) % (2.0 * math.pi)

        # Clamp pitch to slightyly less than pi/2 to avoid lock/errors at full up/down
        max_rotation = math.pi * 0.49
        self._pitch = max(-max_rotation, min(max_rotation, self._pitch))

    def _update_pos(self):
        """Calculate camera position based on look-at, distance and angles."""
        cos_pitch = math.cos(self._pitch)
        sin_pitch = math.sin(self._pitch)
        cos_yaw = math.cos(self._yaw)
        sin_yaw = math.sin(self._yaw)
        cam_distance = self._distance
        cam_look_at = self._look_at

        self._pos = util.Vector3(
            cam_look_at.x + (cam_distance * cos_pitch * cos_yaw),
            cam_look_at.y + (cam_distance * cos_pitch * sin_yaw),
            cam_look_at.z + (cam_distance * sin_pitch))

    def apply(self):
        """Applies the transform this camera represents to the active OpenGL context."""
        self._update_pos()

        gluLookAt(*self._pos.x_y_z,
                  *self._look_at.x_y_z,
                  *self._up.x_y_z)


class Projector():  # pylint: disable=too-few-public-methods
    """Configuration for how 3d objects are projected onto the 2d window.

    :param fov: (Field of View) The viewing angle in degrees between the center of the window, and the top/bottom.
    :param near_clip_plane: The minimum distance from the camera at which geometry can be rendered.
    :param far_clip_plane: The maximum distance from the camera at which geometry can be rendered.
    """

    def __init__(self, fov: float, near_clip_plane: float, far_clip_plane: float):
        self._fov = fov
        self._near_clip_plane = near_clip_plane
        self._far_clip_plane = far_clip_plane

    def apply(self, window):
        """Applies the transform this projection represents to the active OpenGL context."""

        # Set up the projection matrix
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        fov = self._fov
        aspect_ratio = window.width / window.height
        near_clip_plane = self._near_clip_plane
        far_clip_plane = self._far_clip_plane
        gluPerspective(fov, aspect_ratio, near_clip_plane, far_clip_plane)

        # Switch to model matrix for rendering everything
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()


class Light():  # pylint: disable=too-few-public-methods
    """Configuration for a light in the OpenGL scene that effects the shading of 3d geometry.

    :param ambient_color: Color applied to all geometry in the scene regardless of their relation to the light.
    :param diffuse_color: Color applied to geometry in the scene which is facing the light.
    :param specular_color: Color applied to geometry that is facing signficantly enough toward the light (depending on it's material's shininess).
    :param position: The location of the light (or direction vector in the case of direction lights).
    :param is_directional: Flag that sets the light to shine globally from a specified direction rather than an origin point (i.e. Sun light).
    """

    def __init__(self, ambient_color: List[float], diffuse_color: List[float], specular_color: List[float], position: util.Vector3, is_directional: bool = False):
        self._ambient_color = ambient_color
        self._diffuse_color = diffuse_color
        self._specular_color = specular_color
        # w coordinate of '1' indicates a positional light in opengl, while '0' would indicate a directional light
        self._position_coords = [position.x, position.y, position.z, 0 if is_directional else 1]

    def apply(self, index: int):
        """Applies this light to the active OpenGL context.

        :param index: the internal OpenGL light index to apply this class's data to.
        """
        opengl_index = GL_LIGHT0 + index
        glLightfv(opengl_index, GL_AMBIENT, self._ambient_color)
        glLightfv(opengl_index, GL_DIFFUSE, self._diffuse_color)
        glLightfv(opengl_index, GL_SPECULAR, self._specular_color)
        glLightfv(opengl_index, GL_POSITION, self._position_coords)
        glEnable(opengl_index)


class OpenGLWindow():
    """A Window displaying an OpenGL viewport.

    :param x: The initial x coordinate of the window in pixels.
    :param y: The initial y coordinate of the window in pixels.
    :param width: The initial height of the window in pixels.
    :param height: The initial height of the window in pixels.
    :param window_name: The name / title for the window.
    """

    def __init__(self, x: int, y: int, width: int, height: int, window_name: str):
        self._pos = (x, y)
        #: int: The width of the window
        self._width = width
        #: int: The height of the window
        self._height = height
        self._gl_window = None
        self._window_name = window_name

    @property
    def width(self):
        """The horizontal width of the window"""
        return self._width

    @property
    def height(self):
        """The vertical height of the window:"""
        return self._height

    def initialize(self, display_function: callable):
        """Initialze the OpenGL display parts of the Window.

        Warning:
            Must be called on the same thread as OpenGL (usually the main thread),
        """

        glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)

        glutInitWindowSize(self.width, self.height)
        glutInitWindowPosition(*self._pos)
        self._gl_window = glutCreateWindow(self._window_name)

        glClearColor(0, 0, 0, 0)
        glEnable(GL_DEPTH_TEST)
        glShadeModel(GL_SMOOTH)

        glutIdleFunc(self._idle)
        glutVisibilityFunc(self._visible)
        glutReshapeFunc(self._reshape)

        glutDisplayFunc(display_function)

    def prepare_for_rendering(self, projector: Projector, camera: Camera, lights: List[Light]):
        """Selects the window, clears buffers, and sets up the scene transform and lighting state.

        :param projector: The projector configuration to use for this rendering pass.
        :param camera: The camera object to use for this rendering pass.
        :param lights: The light list to use for this rendering pass.
        """
        glutSetWindow(self._gl_window)

        # Clear the screen and the depth buffer
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Apply our projection so the window is ready to render in perspective
        projector.apply(self)

        # Add scene lights
        light_count = len(lights)
        for i in range(light_count):
            lights[i].apply(i)

        # Set scale from mm to cm
        glScalef(0.1, 0.1, 0.1)

        # Orient the camera
        camera.apply()

    @staticmethod
    def display_rendered_content():
        """Swaps buffers once rendering is finished.
        """
        glutSwapBuffers()

    def _idle(self):  # pylint: disable=no-self-use
        """Called from OpenGL when idle."""
        glutPostRedisplay()

    def _visible(self, vis):
        """Called from OpenGL when visibility changes (windows are either visible
        or completely invisible/hidden)."""
        if vis == GLUT_VISIBLE:
            glutIdleFunc(self._idle)
        else:
            glutIdleFunc(None)

    def _reshape(self, width: int, height: int):
        """Called from OpenGL whenever this window is resized.

        :param width: the new width of the window in pixels.
        :param height: the new height of the window in pixels.
        """
        self._width = width
        self._height = height
        glViewport(0, 0, width, height)
