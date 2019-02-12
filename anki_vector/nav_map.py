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

"""A 2D navigation memory map of the world around Vector.

Vector builds a memory map of the navigable world around him as he drives
around. This is mostly based on where objects are seen (the cubes, charger, and
any custom objects), and also includes where Vector detects cliffs/drops, and
visible edges (e.g. sudden changes in color).

This differs from a standard occupancy map in that it doesn't deal with
probabilities of occupancy, but instead encodes what type of content is there.

To use the map you must first call :meth:`anki_vector.nav_map.NavMapComponent.init_nav_map_feed`
with a positive frequency so that the data is streamed to the SDK.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['EvtNavMapUpdate',
           'NavMapComponent', 'NavMapGrid', 'NavMapGridNode',
           'NavNodeContentTypes']

import asyncio
from concurrent.futures import CancelledError
from enum import Enum
from logging import Logger
from typing import List

from . import util
from .events import Events
from .exceptions import VectorException
from .messaging import protocol


class EvtNavMapUpdate():  # pylint: disable=too-few-public-methods
    """Dispatched when a new nav map is received.

    :param nav_map: The current state of the robot's nav map.
    """

    def __init__(self, nav_map):
        self.nav_map = nav_map


class NavNodeContentTypes(Enum):  # pylint: disable=too-few-public-methods
    """The content types for a :class:`NavMapGridNode`.
    """

    #: The contents of the node is unknown.
    Unknown = protocol.NavNodeContentType.Value("NAV_NODE_UNKNOWN")

    #: The node is clear of obstacles, because Vector has seen objects on the
    #: other side, but it might contain a cliff. The node will be marked as
    #: either :attr:`Cliff` or :attr:`ClearOfCliff` once Vector has driven there.
    ClearOfObstacle = protocol.NavNodeContentType.Value("NAV_NODE_CLEAR_OF_OBSTACLE")

    #: The node is clear of any cliffs (a sharp drop) or obstacles.
    ClearOfCliff = protocol.NavNodeContentType.Value("NAV_NODE_CLEAR_OF_CLIFF")

    #: The node contains a :class:`~anki_vector.objects.LightCube`.
    ObstacleCube = protocol.NavNodeContentType.Value("NAV_NODE_OBSTACLE_CUBE")

    #: The node contains a proximity detected obstacle which has not been explored.
    ObstacleProximity = protocol.NavNodeContentType.Value("NAV_NODE_OBSTACLE_PROXIMITY")

    #: The node contains a proximity detected obstacle which has been explored.
    ObstacleProximityExplored = protocol.NavNodeContentType.Value("NAV_NODE_OBSTACLE_PROXIMITY_EXPLORED")

    #: The node contains an unrecognized obstacle.
    ObstacleUnrecognized = protocol.NavNodeContentType.Value("NAV_NODE_OBSTACLE_UNRECOGNIZED")

    #: The node contains a cliff (a sharp drop).
    Cliff = protocol.NavNodeContentType.Value("NAV_NODE_CLIFF")

    #: The node contains a visible edge (based on the camera feed).
    InterestingEdge = protocol.NavNodeContentType.Value("NAV_NODE_INTERESTING_EDGE")

    # This entry is undocumented and not currently used
    NonInterestingEdge = protocol.NavNodeContentType.Value("NAV_NODE_NON_INTERESTING_EDGE")


class NavMapGridNode:
    """A node in a :class:`NavMapGrid`.

    Leaf nodes contain content, all other nodes are split into 4 equally sized
    children.

    Child node indices are stored in the following X,Y orientation:

        +---+----+---+
        | ^ | 2  | 0 |
        +---+----+---+
        | Y | 3  | 1 |
        +---+----+---+
        |   | X->|   |
        +---+----+---+
    """

    def __init__(self, depth: int, size: float, center: util.Vector3, parent: 'NavMapGridNode', logger: Logger):
        #: The depth of this node (i.e. how far down the quad-tree it is).
        self.depth = depth

        #: The size (width or length) of this square node.
        self.size = size

        #: The center of this node.
        self.center = center

        #: The parent of this node. Is ``None`` for the root node.
        self.parent = parent

        #: ``None`` for leaf nodes, a list of 4 child nodes otherwise.
        self.children: List[NavMapGridNode] = None

        #: The content type in this node. Only leaf nodes have content,
        #: this is ``None`` for all other nodes.
        self.content: protocol.NavNodeContentType = None

        self._next_child = 0  # Used when building to track which branch to follow

        self._logger = logger

    def __repr__(self):
        return '<%s center: %s size: %s content: %s>' % (
            self.__class__.__name__, self.center, self.size, self.content)

    def contains_point(self, x: float, y: float) -> bool:
        """Test if the node contains the given x,y coordinates.

        :param x: x coordinate for the point.
        :param y: y coordinate for the point.

        Returns:
            True if the node contains the point, False otherwise.
        """
        half_size = self.size * 0.5
        dist_x = abs(self.center.x - x)
        dist_y = abs(self.center.y - y)
        return (dist_x <= half_size) and (dist_y <= half_size)

    def _get_node(self, x: float, y: float, assumed_in_bounds: bool) -> 'NavMapGridNode':
        if not assumed_in_bounds and not self.contains_point(x, y):
            # point is out of bounds
            return None

        if self.children is None:
            return self

        x_offset = 2 if x < self.center.x else 0
        y_offset = 1 if y < self.center.y else 0
        child_node = self.children[x_offset + y_offset]
        # child node is by definition in bounds / on boundary
        return child_node._get_node(x, y, True)  # pylint: disable=protected-access

    def get_node(self, x: float, y: float) -> 'NavMapGridNode':
        """Get the node at the given x,y coordinates.

        :param x: x coordinate for the point.
        :param y: y coordinate for the point.

        Returns:
            The smallest node that includes the point.
            Will be ``None`` if the point is outside of the map.
        """
        return self._get_node(x, y, assumed_in_bounds=False)

    def get_content(self, x: float, y: float) -> protocol.NavNodeContentType:
        """Get the node's content at the given x,y coordinates.

        :param x: x coordinate for the point.
        :param y: y coordinate for the point.

        Returns:
            The content included at that point. Will be :attr:`NavNodeContentTypes.Unknown`
            if the point is outside of the map.
        """
        node = self.get_node(x, y)
        if node:
            return node.content

        return NavNodeContentTypes.Unknown

    def add_child(self, content: protocol.NavNodeContentType, depth: int) -> bool:
        """Add a child node to the quad tree.

        The quad-tree is serialized to a flat list of nodes, we deserialize
        back to a quad-tree structure here, with the depth of each node
        indicating where it is placed.

        :param content: The content to store in the leaf node.
        :param depth: The depth that this leaf node is located at.

        Returns:
            True if parent should use the next child for future add_child
            calls.
        """
        if depth > self.depth:
            self._logger.error("NavMapGridNode depth %s > %s", depth, self.depth)
        if self._next_child > 3:
            self._logger.error("NavMapGridNode _next_child %s (>3) at depth %s", self._next_child, self.depth)

        if self.depth == depth:
            if self.content is not None:
                self._logger.error("NavMapGridNode: Clobbering %s at depth %s with %s",
                                   self.content, self.depth, content)
            self.content = content
            # This node won't be further subdivided, and is now full
            return True

        if self.children is None:
            # Create 4 child nodes for quad-tree structure
            next_depth = self.depth - 1
            next_size = self.size * 0.5
            offset = next_size * 0.5
            center1 = util.Vector3(self.center.x + offset, self.center.y + offset, self.center.z)
            center2 = util.Vector3(self.center.x + offset, self.center.y - offset, self.center.z)
            center3 = util.Vector3(self.center.x - offset, self.center.y + offset, self.center.z)
            center4 = util.Vector3(self.center.x - offset, self.center.y - offset, self.center.z)
            self.children = [NavMapGridNode(next_depth, next_size, center1, self, self._logger),
                             NavMapGridNode(next_depth, next_size, center2, self, self._logger),
                             NavMapGridNode(next_depth, next_size, center3, self, self._logger),
                             NavMapGridNode(next_depth, next_size, center4, self, self._logger)]
        if self.children[self._next_child].add_child(content, depth):
            # Child node is now full, start using the next child
            self._next_child += 1

        if self._next_child > 3:
            # All children are now full - parent should start using the next child
            return True

        # Empty children remain - parent can keep using this child
        return False


class NavMapGrid:
    """A navigation memory map, stored as a quad-tree."""

    def __init__(self, msg: protocol.NavMapFeedResponse, logger: Logger):
        #: The origin ID for the map. Only maps and :class:`~anki_vector.util.Pose`
        #: objects of the same origin ID are in the same coordinate frame and
        #: can therefore be compared.
        self.origin_id = msg.origin_id
        root_center = util.Vector3(msg.map_info.root_center_x, msg.map_info.root_center_y, msg.map_info.root_center_z)
        self._root_node = NavMapGridNode(msg.map_info.root_depth, msg.map_info.root_size_mm, root_center, None, logger)
        for quad in msg.quad_infos:
            self.add_quad(quad.content, quad.depth)

        self._logger = logger

    def __repr__(self):
        return '<%s center: %s size: %s>' % (
            self.__class__.__name__, self.center, self.size)

    @property
    def root_node(self) -> NavMapGridNode:
        """The root node for the grid, contains all other nodes."""
        return self._root_node

    @property
    def size(self) -> float:
        """The size (width or length) of the square grid."""
        return self._root_node.size

    @property
    def center(self) -> util.Vector3:
        """The center of this map."""
        return self._root_node.center

    def contains_point(self, x: float, y: float) -> bool:
        """Test if the map contains the given x,y coordinates.

        :param x: x coordinate for the point.
        :param y: y coordinate for the point.

        Returns:
            True if the map contains the point, False otherwise.
        """
        return self._root_node.contains_point(x, y)

    def get_node(self, x: float, y: float) -> NavMapGridNode:
        """Get the node at the given x,y coordinates.

        :param x: x coordinate for the point.
        :param y: y coordinate for the point.

        Returns:
            The smallest node that includes the point.
            Will be ``None`` if the point is outside of the map.
        """
        return self._root_node.get_node(x, y)

    def get_content(self, x: float, y: float) -> protocol.NavNodeContentType:
        """Get the map's content at the given x,y coordinates.

        :param x: x coordinate for the point.
        :param y: y coordinate for the point.

        .. testcode::

            import anki_vector

            with anki_vector.Robot(enable_nav_map_feed=True) as robot:
                # Make sure Vector drives around so the nav map will update
                robot.behavior.drive_off_charger()
                robot.motors.set_wheel_motors(-100, 100)
                latest_nav_map = robot.nav_map.latest_nav_map
                content = latest_nav_map.get_content(0.0, 100.0)
                print(f"Sampling point at 0.0, 100.0 and found content: {content}")

        Returns:
            The content included at that point. Will be :attr:`NavNodeContentTypes.Unknown`
            if the point is outside of the map.
        """
        return self._root_node.get_content(x, y)

    def add_quad(self, content: protocol.NavNodeContentType, depth: int):
        """Adds a new quad to the nav map.

        :param content: What content this node contains.
        :param depth: How deep in the navMap this node is.
        """
        self._root_node.add_child(content, depth)


class NavMapComponent(util.Component):
    """Represents Vector's navigation memory map.

    The NavMapComponent object subscribes for nav memory map updates from the robot to store and dispatch.

    The :class:`anki_vector.robot.Robot` or :class:`anki_vector.robot.AsyncRobot` instance hosts this component.

    .. testcode::

        import anki_vector

        with anki_vector.Robot(enable_nav_map_feed=True) as robot:
                # Make sure Vector drives around so the nav map will update
                robot.behavior.drive_off_charger()
                robot.motors.set_wheel_motors(-100, 100)
                latest_nav_map = robot.nav_map.latest_nav_map

    :param robot: A reference to the owner Robot object.
    """

    def __init__(self, robot):
        super().__init__(robot)

        self._latest_nav_map: NavMapGrid = None
        self._nav_map_feed_task: asyncio.Task = None

    @property
    @util.block_while_none()
    def latest_nav_map(self) -> NavMapGrid:
        """:class:`NavMapGrid`: The most recently processed image received from the robot.

        .. testcode::

            import anki_vector

            with anki_vector.Robot(enable_nav_map_feed=True) as robot:
                # Make sure Vector drives around so the nav map will update
                robot.behavior.drive_off_charger()
                robot.motors.set_wheel_motors(-100, 100)
                latest_nav_map = robot.nav_map.latest_nav_map
        """
        if not self._nav_map_feed_task or self._nav_map_feed_task.done():
            raise VectorException("Nav map not initialized. Check that Robot parameter enable_nav_map_feed is set to True.")
        return self._latest_nav_map

    def init_nav_map_feed(self, frequency: float = 0.5) -> None:
        """Begin nav map feed task.

        :param frequency: How frequently to send nav map updates.
        """
        if not self._nav_map_feed_task or self._nav_map_feed_task.done():
            self._nav_map_feed_task = self.conn.loop.create_task(self._request_and_handle_nav_maps(frequency))

    def close_nav_map_feed(self) -> None:
        """Cancel nav map feed task."""
        if self._nav_map_feed_task:
            self._nav_map_feed_task.cancel()
            future = self.conn.run_coroutine(self._nav_map_feed_task)
            future.result()
            self._nav_map_feed_task = None

    async def _request_and_handle_nav_maps(self, frequency: float) -> None:
        """Queries and listens for nav map feed events from the robot.
        Received events are parsed by a helper function.

        :param frequency: How frequently to send nav map updates.
        """
        try:
            req = protocol.NavMapFeedRequest(frequency=frequency)
            async for evt in self.grpc_interface.NavMapFeed(req):
                self._latest_nav_map = NavMapGrid(evt, self.logger)
                await self._robot.events.dispatch_event(evt, Events.nav_map_update)
        except CancelledError:
            self.logger.debug('Nav Map feed task was cancelled. This is expected during disconnection.')
