#!/usr/bin/env python3

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

"""Contains the state of an environment being explored by the robot.
This is a support class for the proximity_mapper example.

Includes a utility for rendering the state in openGL.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['ClearedTerritory', 'MapState', 'Wall', 'WallSegment']

from math import cos, sin, pi
from typing import List

from anki_vector.util import Vector3

import opengl

try:
    from OpenGL.GL import (GL_AMBIENT, GL_BLEND, GL_DIFFUSE, GL_FILL, GL_FRONT, GL_FRONT_AND_BACK, GL_LIGHTING,
                           GL_LINES, GL_ONE_MINUS_SRC_ALPHA, GL_POINTS, GL_QUADS, GL_SHININESS, GL_SPECULAR, GL_SRC_ALPHA,
                           glBegin, glBlendFunc, glColor, glDisable, glEnable, glEnd, glMaterialfv, glNormal3f,
                           glPointSize, glPolygonMode, glVertex3f)

except ImportError as import_exc:
    opengl.raise_opengl_or_pillow_import_error(import_exc)


# Constants

#: Visually represent not just walls, but open/loose nodes, territories and navigation
#: points in the 3d viewer.
RENDER_METADATA_OBJECTS = True

#: Display color of potential exploration targets in the 3d viewer.
NODE_OPEN_RENDER_COLOR = [0.0, 1.0, 1.0, 0.75]
#: Display size (in pixels) of potential exploration targets in the 3d viewer.
NODE_OPEN_RENDER_SIZE = 5.0

#: Display color of detected proximity collisions in the 3d viewer.
#: These nodes will be collected into walls, and will only live long term if isolated
#: too far from any other contact points
NODE_CONTACT_RENDER_COLOR = [1.0, 0.0, 0.0, 0.75]
#: Display size (in pixels) of detected proximity collisions in the 3d viewer.
NODE_CONTACT_RENDER_SIZE = 2.0

#: Display color of the rendered disc for the position the robot will next navigate to.
NAV_POINT_RENDER_COLOR = [0.0, 1.0, 0.0, 1.0]
#: Sections of the rendered disc for the position the robot will next navigate to.
NAV_POINT_RENDER_SECTIONS = 16
#: Display size of the rendered disc for the position the robot will next navigate to.
NAV_POINT_RENDER_SIZE = 25.0

#: Display color of the rendered disc for the territories the robot has already explored.
TERRITORY_RENDER_COLOR = [0.15, 0.6, 1.0, 1.0]
#: Sections of the rendered disc for the territories the robot has already explored.
TERRITORY_RENDER_SECTIONS = 32

#: Display color for the walls the robot has identified in the environment.
WALL_RENDER_COLOR = [1.0, 0.4, 0.1, 1.0]
#: Render height of the walls the robot has identified in the environment.
#: This values is purely cosmetic.  As the proximity sensor is at a static height and
#: always faces forward, the robot has no way of detecting through this method how tall the
#: obstacles are, so the 100mm height was tuned to be similar to Vector in the viewer
#: rather than reflecting the objects in the environment.
WALL_RENDER_HEIGHT_MM = 100.0


class WallSegment:
    """Two points defining a segment of wall in the world

    :param a: The first end of the wall segment expected to be in the xy plane
    :param b: The second end of the wall segment expected to be in the xy plane
    """

    def __init__(self, a: Vector3, b: Vector3):
        self._a = a
        self._b = b

        # precalculate the normal for use in the render call
        aToB = b - a
        facing_vector = aToB.cross(Vector3(0, 0, 1))
        self._normal = facing_vector.normalized

    @property
    def a(self) -> Vector3:
        """:return: The first end of the wall segment."""
        return self._a

    @property
    def b(self) -> Vector3:
        """:return: The second end of the wall segment."""
        return self._b

    @property
    def normal(self) -> Vector3:
        """:return: The precalculated normal of the wall segment."""
        return self._normal


class Wall:
    """A chain of WallSegments making up a continuous wall in 3d space

    :param segment: The initial wall segment for this wall
    """

    def __init__(self, segment: WallSegment):
        self._vertices = [segment.a, segment.b]

    def insert_head(self, vertex: Vector3):
        """Adds a new vertex to the front of the wall

        :param vertex: The coordinates of the vertex being added to the front of the wall.
            This point is expected to be near the current head, and in the same xy plane.
        """
        self._vertices.insert(0, vertex)

    def insert_tail(self, vertex: Vector3):
        """Adds a new vertex to the end of the wall

        :param vertex: The coordinates of the vertex being added to the end of the wall.
            This point is expected to be near the current tail, and in the same xy plane.
        """
        self._vertices.append(vertex)

    @property
    def vertices(self) -> List[Vector3]:
        """:return: All the vertices defining the ground vertices of the wall."""
        return self._vertices

    @property
    def segments(self) -> List[WallSegment]:
        """:return: Constructs and returns the WallSegments which make up this wall."""
        result: List[WallSegment] = []
        for i in range(len(self._vertices) - 1):
            result.append(WallSegment(self._vertices[i], self._vertices[i + 1]))
        return result


class ClearedTerritory:
    """A zone of space that the robot has already explored.  These are used to
    prevent the robot from populating new open nodes in finished areas.

    Cleared Territories always exist in the x-y plane.

    :param center: Centerpoint of the zone
    :param radius: The size of the zone
    """

    def __init__(self, center: Vector3, radius: Vector3):
        self._center = center
        self._radius = radius

    @property
    def center(self) -> Vector3:
        """:return: The centerpoint of the territory."""
        return self._center

    @property
    def radius(self) -> float:
        """:return: The radius of the territory."""
        return self._radius


class MapState:
    """A collection of walls, nodes, and territories defining the area the robot
    is exploring.
    """

    def __init__(self):
        self._open_nodes: List[Vector3] = []
        self._contact_nodes: List[Vector3] = []
        self._walls: List[Wall] = []
        self._cleared_territories: List[ClearedTerritory] = []
        self._collection_active: bool = False

    @staticmethod
    def _set_color(color: List[float]):
        """Modifies the OpenGL state's active material with a specific color
        used on the specular & diffuse channels, with limited ambient.

        This function must be invoked inside the OpenGL render loop.

        :param color: the color to use for the material
        """
        glColor(color)
        glMaterialfv(GL_FRONT, GL_AMBIENT, [color[0] * 0.1, color[1] * 0.1, color[2] * 0.1, 1.0])
        glMaterialfv(GL_FRONT, GL_DIFFUSE, color)
        glMaterialfv(GL_FRONT, GL_SPECULAR, color)

        glMaterialfv(GL_FRONT, GL_SHININESS, 10.0)

    @classmethod
    def _render_points(cls, point_list: List[Vector3], size: float, color: List[float]):
        """Draws a collection of points in the OpenGL 3D worldspace.

        This function must be invoked inside the OpenGL render loop.

        :param point_list: the points to render in the view context
        :param size: the size in pixels of each point
        :param color: the color to render the points
        """
        glPointSize(size)
        cls._set_color(color)
        glBegin(GL_POINTS)
        for point in point_list:
            glVertex3f(point.x, point.y, point.z)
        glEnd()

    @classmethod
    def _render_circle(cls, center: Vector3, radius: float, sections: int, color: List[float]):
        """Draws a circle out of dashed lines around a center point in the x-y plane.

        This function must be invoked inside the OpenGL render loop.

        :param center: the center point of the rendered circle
        :param radius: the size of the rendered circle
        :param sections: the number of vertices used in the dashed line circle
        :param color: the color to render the points
        """
        cls._set_color(color)
        glBegin(GL_LINES)
        for i in range(sections):
            theta = pi * 2.0 * float(i) / float(sections - 1)
            glVertex3f(center.x + cos(theta) * radius,
                       center.y + sin(theta) * radius,
                       center.z)
        glEnd()

    @classmethod
    def _render_wall(cls, wall: Wall, height: float, color: List[float]):
        """Draws walls out of quads in the 3d viewer.  The walls are drawn a
        constant height above their ground-plane points, as a convention.

        This function must be invoked inside the OpenGL render loop.

        :param wall_list: the walls to draw
        :param radius: the size of the rendered circle
        :param sections: the number of vertices used in the dashed line circle
        :param color: the color to render the points
        """
        cls._set_color(color)

        glBegin(GL_QUADS)
        for wall_segment in wall.segments:
            glNormal3f(wall_segment.normal.x, wall_segment.normal.y, wall_segment.normal.z)
            glVertex3f(wall_segment.a.x, wall_segment.a.y, wall_segment.a.z)
            glVertex3f(wall_segment.b.x, wall_segment.b.y, wall_segment.b.z)
            glVertex3f(wall_segment.b.x, wall_segment.b.y, wall_segment.b.z + height)
            glVertex3f(wall_segment.a.x, wall_segment.a.y, wall_segment.a.z + height)
        glEnd()

    @property
    def open_nodes(self) -> List[Vector3]:
        """:return: Points on the map which have no proximity detections between
        themselves and the proximity scan origin point that found them.

        These are safe points for the robot to drive to.
        """
        return self._open_nodes

    @open_nodes.setter
    def open_nodes(self, open_nodes: List[Vector3]):
        self._open_nodes = open_nodes

    @property
    def contact_nodes(self) -> List[Vector3]:
        """:return: Points where an obstacle has been detected, but are too far
        from other contacts to construct a wall from.
        """
        return self._contact_nodes

    @property
    def walls(self) -> List[Wall]:
        """:return: Chains of points denoting barriers detected by the proximity
        sensor.
        """
        return self._walls

    @property
    def cleared_territories(self) -> List[ClearedTerritory]:
        """:return: Regions of space the robot has finished scanning.  Any points
        inside one of these regions can be considered accurate in terms of
        detected boundaries.
        """
        return self._cleared_territories

    @property
    def collection_active(self) -> bool:
        """:return: Whether or not proximity data should currently be collected."""
        return self._collection_active

    @collection_active.setter
    def collection_active(self, collection_active: bool):
        self._collection_active = collection_active

    def render(self):
        """Low level OpenGL calls to render the current state in an opengl_viewer.

        Can be added to a viewer with the following code, telling the viewer to call this
        whenever it redraws its geometry.
        .. code-block:: python

            my_opengl_viewer.add_render_call(my_map_state.render)
        """
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_BLEND)

        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glDisable(GL_LIGHTING)

        if RENDER_METADATA_OBJECTS:
            self._render_points(self._contact_nodes, NODE_CONTACT_RENDER_SIZE, NODE_CONTACT_RENDER_COLOR)
            self._render_points(self._open_nodes, NODE_OPEN_RENDER_SIZE, NODE_OPEN_RENDER_COLOR)

            # render the nav point open sample
            if self._cleared_territories and self._open_nodes:
                self._render_circle(self._open_nodes[0], NAV_POINT_RENDER_SIZE, NAV_POINT_RENDER_SECTIONS, NAV_POINT_RENDER_COLOR)

            for cleared_territory in self._cleared_territories:
                self._render_circle(cleared_territory.center, cleared_territory.radius, TERRITORY_RENDER_SECTIONS, TERRITORY_RENDER_COLOR)

        glEnable(GL_LIGHTING)
        for wall in self._walls:
            self._render_wall(wall, WALL_RENDER_HEIGHT_MM, WALL_RENDER_COLOR)
