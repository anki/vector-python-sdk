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

"""
Vector's known view of his world.

This view includes objects and faces it knows about and can currently
see with its camera.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['World']

from . import faces
from . import objects
from . import sync
from . import util

from .events import Events
from .messaging import protocol


class World(util.Component):
    """Represents the state of the world, as known to Vector."""

    #: callable: The factory function that returns a
    #: :class:`faces.Face` class or subclass instance
    face_factory = faces.Face

    #: callable: The factory function that returns an
    #: :class:`objects.LightCube` class or subclass instance.
    light_cube_factory = objects.LightCube

    def __init__(self, robot):
        super().__init__(robot)

        self._faces = {}

        self._light_cube = {objects.LIGHT_CUBE_1_TYPE: self.light_cube_factory(robot=robot)}

        # Subscribe to a callback that updates the world view
        robot.events.subscribe(
            self._on_face_observed,
            Events.robot_observed_face)

    def close(self):
        """The world will tear down all its faces and objects."""
        for face in self._faces.values():
            face.teardown()

        for cube in self._light_cube.values():
            cube.teardown()

    @property
    def visible_faces(self):
        """generator: yields each face that Vector can currently see.

        .. code-block:: python

            # Print the visible face's attributes
            for face in robot.world.visible_faces:
                print("Face attributes:")
                print(f"Face id: {face.face_id}")
                print(f"Updated face id: {face.updated_face_id}")
                print(f"Name: {face.name}")
                print(f"Expression: {face.expression}")
                print(f"Timestamp: {face.timestamp}")
                print(f"Pose: {face.pose}")
                print(f"Image Rect: {face.face_rect}")
                print(f"Expression score: {face.expression_score}")
                print(f"Left eye: {face.left_eye}")
                print(f"Right eye: {face.right_eye}")
                print(f"Nose: {face.nose}")
                print(f"Mouth: {face.mouth}")

        Returns:
            A generator yielding :class:`anki_vector.faces.Face` instances
        """
        for face in self._faces.values():
            yield face

    def get_face(self, face_id: int) -> faces.Face:
        """Fetches a Face instance with the given id."""
        return self._faces.get(face_id)

    def get_light_cube(self) -> objects.LightCube:
        """Returns the vector light cube object, regardless of its connection status.

        .. code-block:: python

            cube = robot.world.get_light_cube()
            print('LightCube {0} connected.'.format("is" if cube.is_connected else "isn't"))

        Raises:
            :class:`ValueError` if the cube_id is invalid.
        """
        cube = self._light_cube.get(objects.LIGHT_CUBE_1_TYPE)
        # Only return the cube if it has an object_id
        if cube.object_id is not None:
            return cube
        return None

    @property
    def connected_light_cube(self) -> objects.LightCube:
        """A light cube connected to Vector, if any.

        .. code-block:: python

            robot.world.connect_cube()
            if robot.world.connected_light_cube:
                dock_response = robot.behavior.dock_with_cube(robot.world.connected_light_cube)
        """
        result = None
        cube = self._light_cube.get(objects.LIGHT_CUBE_1_TYPE)
        if cube and cube.is_connected:
            result = cube

        return result

    @sync.Synchronizer.wrap
    async def connect_cube(self) -> protocol.ConnectCubeResponse:
        """Attempt to connect to a cube.

        If a cube is currently connected, this will do nothing.

        .. code-block:: python

            robot.world.connect_cube()
        """
        req = protocol.ConnectCubeRequest()
        result = await self.grpc_interface.ConnectCube(req)

        # dispatch cube connected message
        event = protocol.ObjectConnectionState(
            object_id=result.object_id,
            factory_id=result.factory_id,
            connected=result.success,
            object_type=objects.LIGHT_CUBE_1_TYPE)

        self._robot.events.dispatch_event(event, Events.object_connection_state)

        return result

    @sync.Synchronizer.wrap
    async def disconnect_cube(self) -> protocol.DisconnectCubeResponse:
        """Requests a disconnection from the currently connected cube.

        .. code-block:: python

            robot.world.disconnect_cube()
        """
        req = protocol.DisconnectCubeRequest()
        return await self.grpc_interface.DisconnectCube(req)

    @sync.Synchronizer.wrap
    async def flash_cube_lights(self) -> protocol.FlashCubeLightsResponse:
        """Flash cube lights

        Plays the default cube connection animation on the currently
        connected cube's lights.
        """
        req = protocol.FlashCubeLightsRequest()
        return await self.grpc_interface.FlashCubeLights(req)

    @sync.Synchronizer.wrap
    async def forget_preferred_cube(self) -> protocol.ForgetPreferredCubeResponse:
        """Forget preferred cube.

        'Forget' the robot's preferred cube. This will cause the robot to
        connect to the cube with the highest RSSI (signal strength) next
        time a connection is requested.

        .. code-block:: python

            robot.world.forget_preferred_cube()
        """
        req = protocol.ForgetPreferredCubeRequest()
        return await self.grpc_interface.ForgetPreferredCube(req)

    @sync.Synchronizer.wrap
    async def set_preferred_cube(self, factory_id: str) -> protocol.SetPreferredCubeResponse:
        """Set preferred cube.

        Set the robot's preferred cube and save it to disk. The robot
        will always attempt to connect to this cube if it is available.
        This is only used in simulation (for now).

        .. code-block:: python

            connected_cube = robot.world.connected_light_cube
            if connected_cube:
                robot.world.set_preferred_cube(connected_cube.factory_id)

        :param factory_id: The unique hardware id of the physical cube.
        """
        req = protocol.SetPreferredCubeRequest(factory_id=factory_id)
        return await self.grpc_interface.SetPreferredCube(req)

    #### Private Event Handlers ####

    def _on_face_observed(self, _, msg):
        """Adds/Updates the world view when a face is observed."""
        if msg.face_id not in self._faces:
            pose = util.Pose(x=msg.pose.x, y=msg.pose.y, z=msg.pose.z,
                             q0=msg.pose.q0, q1=msg.pose.q1,
                             q2=msg.pose.q2, q3=msg.pose.q3,
                             origin_id=msg.pose.origin_id)
            image_rect = util.ImageRect(msg.img_rect.x_top_left,
                                        msg.img_rect.y_top_left,
                                        msg.img_rect.width,
                                        msg.img_rect.height)
            face = self.face_factory(self.robot,
                                     pose, image_rect, msg.face_id, msg.name, msg.expression, msg.expression_values,
                                     msg.left_eye, msg.right_eye, msg.nose, msg.mouth, msg.timestamp)
            self._faces[face.face_id] = face
