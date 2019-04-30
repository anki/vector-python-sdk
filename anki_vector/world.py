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

"""
Vector's known view of his world.

This view includes objects and faces it knows about and can currently
see with its camera.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['World']

from concurrent import futures
from typing import Iterable

from . import faces
from . import connection
from . import objects
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

    #: callable: The factory function that returns an
    #: :class:`objects.Charger` class or subclass instance.
    charger_factory = objects.Charger

    #: callable: The factory function that returns an
    #: :class:`objects.CustomObject` class or subclass instance.
    custom_object_factory = objects.CustomObject

    #: callable: The factory function that returns an
    #: :class:`objects.FixedCustomObject` class or subclass instance.
    fixed_custom_object_factory = objects.FixedCustomObject

    def __init__(self, robot):
        super().__init__(robot)

        self._custom_object_archetypes = {}

        # Objects by type
        self._faces = {}
        self._light_cube = {objects.LIGHT_CUBE_1_TYPE: self.light_cube_factory(robot=robot)}
        self._custom_objects = {}

        #: :class:`anki_vector.objects.Charger`: Vector's charger.
        #: ``None`` if no charger connected or known about yet.
        self._charger = None  # type: anki_vector.objects.Charger

        # All objects
        self._objects = {}

        # Subscribe to callbacks that updates the world view
        self._robot.events.subscribe(self._on_face_observed,
                                     Events.robot_observed_face,
                                     _on_connection_thread=True)

        self._robot.events.subscribe(self._on_object_observed,
                                     Events.robot_observed_object,
                                     _on_connection_thread=True)

    #### Public Properties ####

    @property
    def all_objects(self):
        """generator: yields each object in the world.

        .. testcode::

            # Print the all objects' class details
            import anki_vector
            with anki_vector.Robot() as robot:
                for obj in robot.world.all_objects:
                    print(obj)

        Returns:
            A generator yielding :class:`anki_vector.faces.Face`, :class:`anki_vector.faces.LightCube`,
            :class:`anki_vector.faces.Charger`, :class:`anki_vector.faces.CustomObject` and
            :class:`anki_vector.faces.FixedCustomObject` instances.
        """
        for obj in self._objects.values():
            yield obj

    @property
    def visible_faces(self) -> Iterable[faces.Face]:
        """generator: yields each face that Vector can currently see.

        .. testcode::

            import time

            import anki_vector
            from anki_vector.events import Events
            from anki_vector.util import degrees

            def test_subscriber(robot, event_type, event):
                print(f"Subscriber called for: {event_type} = {event}")

                for face in robot.world.visible_faces:
                    print("--- Face attributes ---")
                    print(f"Face id: {face.face_id}")
                    print(f"Updated face id: {face.updated_face_id}")
                    print(f"Name: {face.name}")
                    print(f"Expression: {face.expression}")
                    print(f"Timestamp: {face.last_observed_time}")
                    print(f"Pose: {face.pose}")
                    print(f"Image Rect: {face.last_observed_image_rect}")
                    print(f"Expression score: {face.expression_score}")
                    print(f"Left eye: {face.left_eye}")
                    print(f"Right eye: {face.right_eye}")
                    print(f"Nose: {face.nose}")
                    print(f"Mouth: {face.mouth}")

            with anki_vector.Robot(enable_face_detection=True) as robot:
                # If necessary, move Vector's Head and Lift to make it easy to see his face
                robot.behavior.set_head_angle(degrees(45.0))
                robot.behavior.set_lift_height(0.0)

                robot.events.subscribe(test_subscriber, Events.robot_changed_observed_face_id)
                robot.events.subscribe(test_subscriber, Events.robot_observed_face)

                print("------ show vector your face, press ctrl+c to exit early ------")
                try:
                    time.sleep(10)
                except KeyboardInterrupt:
                    robot.disconnect()

        Returns:
            A generator yielding :class:`anki_vector.faces.Face` instances.
        """
        for face in self._faces.values():
            if face.is_visible:
                yield face

    @property
    def custom_object_archetypes(self) -> Iterable[objects.CustomObjectArchetype]:
        """generator: yields each custom object archetype that Vector will look for.

        See :class:`objects.CustomObjectMarkers`.

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                for obj in robot.world.custom_object_archetypes:
                    print(obj)

        Returns:
            A generator yielding CustomObjectArchetype instances
        """
        for obj in self._custom_object_archetypes.values():
            yield obj

    @property
    def visible_custom_objects(self) -> Iterable[objects.CustomObject]:
        """generator: yields each custom object that Vector can currently see.

        See :class:`objects.CustomObjectMarkers`.

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                for obj in robot.world.visible_custom_objects:
                    print(obj)

        Returns:
            A generator yielding CustomObject instances
        """
        for obj in self._custom_objects.values():
            if obj.is_visible:
                yield obj

    @property
    def visible_objects(self) -> Iterable[objects.ObservableObject]:
        """generator: yields each object that Vector can currently see.

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                for obj in robot.world.visible_objects:
                    print(obj)

        Returns:
            A generator yielding Charger, LightCube and CustomObject instances
        """
        for obj in self._objects.values():
            if obj.is_visible:
                yield obj

    @property
    def connected_light_cube(self) -> objects.LightCube:
        """A light cube connected to Vector, if any.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                robot.world.connect_cube()
                if robot.world.connected_light_cube:
                    dock_response = robot.behavior.dock_with_cube(robot.world.connected_light_cube)
        """
        result = None
        cube = self._light_cube.get(objects.LIGHT_CUBE_1_TYPE)
        if cube and cube.is_connected:
            result = cube

        return result

    @property
    def light_cube(self) -> objects.LightCube:
        """Returns the vector light cube object, regardless of its connection status.

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                cube = robot.world.light_cube
                if cube:
                    if cube.is_connected:
                        print("LightCube is connected.")
                    else:
                        print("LightCube isn't connected")

        Raises:
            :class:`ValueError` if the cube_id is invalid.
        """
        cube = self._light_cube.get(objects.LIGHT_CUBE_1_TYPE)
        # Only return the cube if it has an object_id
        if cube.object_id is not None:
            return cube
        return None

    @property
    def charger(self) -> objects.Charger:
        """Returns the most recently observed Vector charger object, or None if no chargers have been observed.

        .. testcode::

            import anki_vector

            # First, place Vector directly in front of his charger so he can observe it.

            with anki_vector.Robot() as robot:
                print('Most recently observed charger: {0}'.format(robot.world.charger))
        """
        if self._charger is not None:
            return self._charger
        return None

    #### Public Methods ####

    def close(self):
        """The world will tear down all its faces and objects."""

        # delete_custom_objects is called before the _objects are torn down to make sure the
        # robot receives cues to remove the internal representations of these objects before
        # we release the SDK side representations
        self.delete_custom_objects()

        for obj in self._objects.values():
            obj.teardown()

        self._robot.events.unsubscribe(self._on_face_observed,
                                       Events.robot_observed_face)

        self._robot.events.unsubscribe(self._on_object_observed,
                                       Events.robot_observed_object)

    def get_object(self, object_id: int):
        """Fetches an object instance with the given id.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                # First get an existing object id, for instance:
                valid_object_id = 1

                # Then use the object_id to retrieve the object instance:
                my_obj = robot.world.get_object(valid_object_id)
        """
        return self._objects.get(object_id)

    def get_face(self, face_id: int) -> faces.Face:
        """Fetches a Face instance with the given id.

        .. testcode::


            import time

            import anki_vector
            from anki_vector.events import Events
            from anki_vector.util import degrees

            def test_subscriber(robot, event_type, event):
                for face in robot.world.visible_faces:
                    print(f"Face id: {face.face_id}")

            with anki_vector.Robot(enable_face_detection=True) as robot:
                # If necessary, move Vector's Head and Lift to make it easy to see his face
                robot.behavior.set_head_angle(degrees(45.0))
                robot.behavior.set_lift_height(0.0)

                robot.events.subscribe(test_subscriber, Events.robot_changed_observed_face_id)
                robot.events.subscribe(test_subscriber, Events.robot_observed_face)

                print("------ show vector your face, press ctrl+c to exit early ------")
                try:
                    time.sleep(5)
                except KeyboardInterrupt:
                    robot.disconnect()
        """
        return self._faces.get(face_id)

    @connection.on_connection_thread()
    async def connect_cube(self) -> protocol.ConnectCubeResponse:
        """Attempt to connect to a cube.

        If a cube is currently connected, this will do nothing.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
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

        await self._robot.events.dispatch_event(event, Events.object_connection_state)

        return result

    @connection.on_connection_thread()
    async def disconnect_cube(self) -> protocol.DisconnectCubeResponse:
        """Requests a disconnection from the currently connected cube.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                robot.world.disconnect_cube()
        """
        req = protocol.DisconnectCubeRequest()
        return await self.grpc_interface.DisconnectCube(req)

    # TODO move out of world.py and into lights.py?
    @connection.on_connection_thread()
    async def flash_cube_lights(self) -> protocol.FlashCubeLightsResponse:
        """Flash cube lights

        Plays the default cube connection animation on the currently
        connected cube's lights.

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                robot.world.flash_cube_lights()
        """
        req = protocol.FlashCubeLightsRequest()
        return await self.grpc_interface.FlashCubeLights(req)

    # TODO move out of world.py and into objects.py?
    @connection.on_connection_thread(requires_control=False)
    async def forget_preferred_cube(self) -> protocol.ForgetPreferredCubeResponse:
        """Forget preferred cube.

        'Forget' the robot's preferred cube. This will cause the robot to
        connect to the cube with the highest RSSI (signal strength) next
        time a connection is requested.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                robot.world.forget_preferred_cube()
        """
        req = protocol.ForgetPreferredCubeRequest()
        return await self.grpc_interface.ForgetPreferredCube(req)

    # TODO move out of world.py and into objects.py?
    @connection.on_connection_thread(requires_control=False)
    async def set_preferred_cube(self, factory_id: str) -> protocol.SetPreferredCubeResponse:
        """Set preferred cube.

        Set the robot's preferred cube and save it to disk. The robot
        will always attempt to connect to this cube if it is available.
        This is only used in simulation (for now).

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                connected_cube = robot.world.connected_light_cube
                if connected_cube:
                    robot.world.set_preferred_cube(connected_cube.factory_id)

        :param factory_id: The unique hardware id of the physical cube.
        """
        req = protocol.SetPreferredCubeRequest(factory_id=factory_id)
        return await self.grpc_interface.SetPreferredCube(req)

    # TODO better place to put this method than world.py?
    @connection.on_connection_thread(requires_control=False)
    async def delete_custom_objects(self,
                                    delete_custom_marker_objects: bool = True,
                                    delete_fixed_custom_objects: bool = True,
                                    delete_custom_object_archetypes: bool = True):
        """Causes the robot to forget about custom objects it currently knows about.

        See :class:`objects.CustomObjectMarkers`.

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                robot.world.delete_custom_objects()
        """

        last_blocking_call = None

        if delete_custom_object_archetypes:
            self._custom_object_archetypes.clear()
            req = protocol.DeleteCustomObjectsRequest(mode=protocol.CustomObjectDeletionMode.Value("DELETION_MASK_ARCHETYPES"))
            last_blocking_call = await self.grpc_interface.DeleteCustomObjects(req)
            delete_custom_marker_objects = True

        if delete_custom_marker_objects:
            self._remove_all_custom_marker_object_instances()
            req = protocol.DeleteCustomObjectsRequest(mode=protocol.CustomObjectDeletionMode.Value("DELETION_MASK_CUSTOM_MARKER_OBJECTS"))
            last_blocking_call = await self.grpc_interface.DeleteCustomObjects(req)

        if delete_fixed_custom_objects:
            self._remove_all_fixed_custom_object_instances()
            req = protocol.DeleteCustomObjectsRequest(mode=protocol.CustomObjectDeletionMode.Value("DELETION_MASK_FIXED_CUSTOM_OBJECTS"))
            last_blocking_call = await self.grpc_interface.DeleteCustomObjects(req)

        return last_blocking_call

    # TODO better place to put this method than world.py?
    @connection.on_connection_thread(requires_control=False)
    async def define_custom_box(self,
                                custom_object_type: objects.CustomObjectTypes,
                                marker_front: objects.CustomObjectMarkers,
                                marker_back: objects.CustomObjectMarkers,
                                marker_top: objects.CustomObjectMarkers,
                                marker_bottom: objects.CustomObjectMarkers,
                                marker_left: objects.CustomObjectMarkers,
                                marker_right: objects.CustomObjectMarkers,
                                depth_mm: float,
                                width_mm: float,
                                height_mm: float,
                                marker_width_mm: float,
                                marker_height_mm: float,
                                is_unique: bool = True) -> objects.CustomObject:
        """Defines a cuboid of custom size and binds it to a specific custom object type.

        The robot will now detect the markers associated with this object and send an
        object_observed message when they are seen. The markers must be placed in the center
        of their respective sides. All 6 markers must be unique.

        See :class:`objects.CustomObjectMarkers`.

        :param custom_object_type: the object type you are binding this custom object to.
        :param marker_front: the marker affixed to the front of the object.
        :param marker_back: the marker affixed to the back of the object.
        :param marker_top: the marker affixed to the top of the object.
        :param marker_bottom: the marker affixed to the bottom of the object.
        :param marker_left: the marker affixed to the left of the object.
        :param marker_right: the marker affixed to the right of the object.
        :param depth_mm: depth of the object (in millimeters) (X axis).
        :param width_mm: width of the object (in millimeters) (Y axis).
        :param height_mm: height of the object (in millimeters) (Z axis).
            (the height of the object)
        :param marker_width_mm: width of the printed marker (in millimeters).
        :param maker_height_mm: height of the printed marker (in millimeters).
        :param is_unique: If True, the robot will assume there is only 1 of this object.
            (and therefore only 1 of each of any of these markers) in the world.

        .. testcode::

            import anki_vector
            with anki_vector.Robot(enable_custom_object_detection=True) as robot:
                robot.world.define_custom_box(custom_object_type=anki_vector.objects.CustomObjectTypes.CustomType00,
                                              marker_front=  anki_vector.objects.CustomObjectMarkers.Circles2,
                                              marker_back=   anki_vector.objects.CustomObjectMarkers.Circles3,
                                              marker_top=    anki_vector.objects.CustomObjectMarkers.Circles4,
                                              marker_bottom= anki_vector.objects.CustomObjectMarkers.Circles5,
                                              marker_left=   anki_vector.objects.CustomObjectMarkers.Triangles2,
                                              marker_right=  anki_vector.objects.CustomObjectMarkers.Triangles3,
                                              depth_mm=20.0, width_mm=20.0, height_mm=20.0,
                                              marker_width_mm=50.0, marker_height_mm=50.0)

        Returns:
            CustomObject instance with the specified dimensions.
            This is None if the definition failed internally.
            Note: No instances of this object are added to the world until they have been seen.

        Raises:
            TypeError if the custom_object_type is of the wrong type.
            ValueError if the 6 markers aren't unique.
        """
        if not isinstance(custom_object_type, objects._CustomObjectType):  # pylint: disable=protected-access
            raise TypeError("Unsupported object_type, requires CustomObjectType")

        # verify all 6 markers are unique
        markers = {marker_front, marker_back, marker_top, marker_bottom, marker_left, marker_right}
        if len(markers) != 6:
            raise ValueError("all markers must be unique for a custom box")

        custom_object_archetype = objects.CustomObjectArchetype(custom_object_type,
                                                                depth_mm, width_mm, height_mm,
                                                                marker_width_mm, marker_height_mm,
                                                                is_unique)

        definition = protocol.CustomBoxDefinition(marker_front=marker_front.id,
                                                  marker_back=marker_back.id,
                                                  marker_top=marker_top.id,
                                                  marker_bottom=marker_bottom.id,
                                                  marker_left=marker_left.id,
                                                  marker_right=marker_right.id,
                                                  x_size_mm=depth_mm,
                                                  y_size_mm=width_mm,
                                                  z_size_mm=height_mm,
                                                  marker_width_mm=marker_width_mm,
                                                  marker_height_mm=marker_height_mm)

        req = protocol.DefineCustomObjectRequest(custom_type=custom_object_type.id,
                                                 is_unique=is_unique,
                                                 custom_box=definition)

        response = await self.grpc_interface.DefineCustomObject(req)

        if response.success:
            type_id = custom_object_archetype.custom_type.id
            self._custom_object_archetypes[type_id] = custom_object_archetype
            return custom_object_archetype

        self.logger.error("Failed to define Custom Object %s", custom_object_archetype)
        return None

    # TODO better place to put this method than world.py?
    @connection.on_connection_thread(requires_control=False)
    async def define_custom_cube(self,
                                 custom_object_type: objects.CustomObjectTypes,
                                 marker: objects.CustomObjectMarkers,
                                 size_mm: float,
                                 marker_width_mm: float,
                                 marker_height_mm: float,
                                 is_unique: bool = True) -> objects.CustomObject:
        """Defines a cube of custom size and binds it to a specific custom object type.

        The robot will now detect the markers associated with this object and send an
        object_observed message when they are seen. The markers must be placed in the center
        of their respective sides.

        See :class:`objects.CustomObjectMarkers`.

        :param custom_object_type: the object type you are binding this custom object to.
        :param marker: the marker affixed to every side of the cube.
        :param size_mm: size of each side of the cube (in millimeters).
        :param marker_width_mm: width of the printed marker (in millimeters).
        :param maker_height_mm: height of the printed marker (in millimeters).
        :param is_unique: If True, the robot will assume there is only 1 of this object
            (and therefore only 1 of each of any of these markers) in the world.

        .. testcode::

            import anki_vector
            with anki_vector.Robot(enable_custom_object_detection=True) as robot:
                robot.world.define_custom_cube(custom_object_type=anki_vector.objects.CustomObjectTypes.CustomType00,
                                               marker=anki_vector.objects.CustomObjectMarkers.Circles2,
                                               size_mm=20.0,
                                               marker_width_mm=50.0, marker_height_mm=50.0)

        Returns:
            CustomObject instance with the specified dimensions.
            This is None if the definition failed internally.
            Note: No instances of this object are added to the world until they have been seen.

        Raises:
            TypeError if the custom_object_type is of the wrong type.
        """

        if not isinstance(custom_object_type, objects._CustomObjectType):  # pylint: disable=protected-access
            raise TypeError("Unsupported object_type, requires CustomObjectType")

        custom_object_archetype = objects.CustomObjectArchetype(custom_object_type,
                                                                size_mm, size_mm, size_mm,
                                                                marker_width_mm, marker_height_mm,
                                                                is_unique)

        definition = protocol.CustomCubeDefinition(marker=marker.id,
                                                   size_mm=size_mm,
                                                   marker_width_mm=marker_width_mm,
                                                   marker_height_mm=marker_height_mm)

        req = protocol.DefineCustomObjectRequest(custom_type=custom_object_type.id,
                                                 is_unique=is_unique,
                                                 custom_cube=definition)

        response = await self.grpc_interface.DefineCustomObject(req)

        if response.success:
            type_id = custom_object_archetype.custom_type.id
            self._custom_object_archetypes[type_id] = custom_object_archetype
            return custom_object_archetype

        self.logger.error("Failed to define Custom Object %s", custom_object_archetype)
        return None

    # TODO better place to put this method than world.py?
    @connection.on_connection_thread(requires_control=False)
    async def define_custom_wall(self,
                                 custom_object_type: objects.CustomObjectTypes,
                                 marker: objects.CustomObjectMarkers,
                                 width_mm: float,
                                 height_mm: float,
                                 marker_width_mm: float,
                                 marker_height_mm: float,
                                 is_unique: bool = True) -> objects.CustomObject:
        """Defines a wall of custom width and height, with a fixed depth of 10mm, and binds it to a specific custom object type.

        The robot will now detect the markers associated with this object and send an
        object_observed message when they are seen. The markers must be placed in the center
        of their respective sides.

        See :class:`objects.CustomObjectMarkers`.

        :param custom_object_type: the object type you are binding this custom object to.
        :param marker: the marker affixed to the front and back of the wall.
        :param width_mm: width of the object (in millimeters). (Y axis).
        :param height_mm: height of the object (in millimeters). (Z axis).
        :param width_mm: width of the wall (along Y axis) (in millimeters).
        :param height_mm: height of the wall (along Z axis) (in millimeters).
        :param marker_width_mm: width of the printed marker (in millimeters).
        :param maker_height_mm: height of the printed marker (in millimeters).
        :param is_unique: If True, the robot will assume there is only 1 of this object
                (and therefore only 1 of each of any of these markers) in the world.

        .. testcode::

            import anki_vector
            with anki_vector.Robot(enable_custom_object_detection=True) as robot:
                robot.world.define_custom_wall(custom_object_type=anki_vector.objects.CustomObjectTypes.CustomType00,
                                               marker=anki_vector.objects.CustomObjectMarkers.Circles2,
                                               width_mm=20.0, height_mm=20.0,
                                               marker_width_mm=50.0, marker_height_mm=50.0)

        Returns:
            CustomObject instance with the specified dimensions.
            This is None if the definition failed internally.
            Note: No instances of this object are added to the world until they have been seen.

        Raises:
            TypeError if the custom_object_type is of the wrong type.
        """

        if not isinstance(custom_object_type, objects._CustomObjectType):  # pylint: disable=protected-access
            raise TypeError("Unsupported object_type, requires CustomObjectType")

        thickness_mm = protocol.ObjectConstants.Value("FIXED_CUSTOM_WALL_THICKNESS_MM")

        custom_object_archetype = objects.CustomObjectArchetype(custom_object_type,
                                                                thickness_mm, width_mm, height_mm,
                                                                marker_width_mm, marker_height_mm,
                                                                is_unique)

        definition = protocol.CustomWallDefinition(marker=marker.id,
                                                   width_mm=width_mm,
                                                   height_mm=height_mm,
                                                   marker_width_mm=marker_width_mm,
                                                   marker_height_mm=marker_height_mm)

        req = protocol.DefineCustomObjectRequest(custom_type=custom_object_type.id,
                                                 is_unique=is_unique,
                                                 custom_wall=definition)

        response = await self.grpc_interface.DefineCustomObject(req)

        if response.success:
            type_id = custom_object_archetype.custom_type.id
            self._custom_object_archetypes[type_id] = custom_object_archetype
            return custom_object_archetype

        self.logger.error("Failed to define Custom Object %s", custom_object_archetype)
        return None

    # TODO better place to put this method than world.py?
    def create_custom_fixed_object(self,
                                   pose: util.Pose,
                                   x_size_mm: float,
                                   y_size_mm: float,
                                   z_size_mm: float,
                                   relative_to_robot: bool = False,
                                   use_robot_origin: bool = True) -> objects.FixedCustomObject:
        """Defines a cuboid of custom size and places it in the world. It cannot be observed.

        See :class:`objects.CustomObjectMarkers`.

        :param pose: The pose of the object we are creating.
        :param x_size_mm: size of the object (in millimeters) in the x axis.
        :param y_size_mm: size of the object (in millimeters) in the y axis.
        :param z_size_mm: size of the object (in millimeters) in the z axis.
        :param relative_to_robot: whether or not the pose given assumes the robot's pose as its origin.
        :param use_robot_origin: whether or not to override the origin_id in the given pose to be
                                 the origin_id of Vector.

        .. testcode::

            import anki_vector
            from anki_vector.util import degrees, Pose

            with anki_vector.Robot() as robot:
                robot.world.create_custom_fixed_object(Pose(100, 0, 0, angle_z=degrees(0)),
                                                       x_size_mm=10, y_size_mm=100, z_size_mm=100,
                                                       relative_to_robot=True)

        Returns:
            FixedCustomObject instance with the specified dimensions and pose.
        """
        # Override the origin of the pose to be the same as the robot's. This will make sure they are in
        # the same space in the robot every time.
        if use_robot_origin:
            pose = util.Pose(x=pose.position.x, y=pose.position.y, z=pose.position.z,
                             q0=pose.rotation.q0, q1=pose.rotation.q1,
                             q2=pose.rotation.q2, q3=pose.rotation.q3,
                             origin_id=self._robot.pose.origin_id)

        # In this case define the given pose to be with respect to the robot's pose as its origin.
        if relative_to_robot:
            pose = self._robot.pose.define_pose_relative_this(pose)

        response = self._create_custom_fixed_object(pose, x_size_mm, y_size_mm, z_size_mm)
        if isinstance(response, futures.Future):
            response = response.result()

        fixed_custom_object = self.fixed_custom_object_factory(
            self._robot,
            pose,
            x_size_mm,
            y_size_mm,
            z_size_mm,
            response.object_id)

        if fixed_custom_object:
            self._objects[fixed_custom_object.object_id] = fixed_custom_object
        return fixed_custom_object

    @connection.on_connection_thread(requires_control=False)
    async def _create_custom_fixed_object(self,
                                          pose: util.Pose,
                                          x_size_mm: float,
                                          y_size_mm: float,
                                          z_size_mm: float):
        """Send the CreateFixedCustomObject rpc call on the connection thread."""
        req = protocol.CreateFixedCustomObjectRequest(
            pose=pose.to_proto_pose_struct(),
            x_size_mm=x_size_mm,
            y_size_mm=y_size_mm,
            z_size_mm=z_size_mm)

        return await self.grpc_interface.CreateFixedCustomObject(req)

    #### Private Methods ####

    def _allocate_custom_marker_object(self, msg):
        # obj is the base object type for this custom object. We make instances of this for every
        # unique object_id we see of this custom object type.
        first_custom_type = protocol.ObjectType.Value("FIRST_CUSTOM_OBJECT_TYPE")
        if msg.object_type < first_custom_type or msg.object_type >= first_custom_type + protocol.CustomType.Value("CUSTOM_TYPE_COUNT"):
            self.logger.error('Received a custom object observation with a type not inside the custom object range: %s. Msg=%s',
                              msg.object_type, msg)
            return None

        # Object observation events contain an object_type.  A subset of that object_type enum maps to the
        # custom_type enum, so we perform the conversion.
        custom_type = msg.object_type - first_custom_type + objects.CustomObjectTypes.CustomType00.id
        archetype = self._custom_object_archetypes.get(custom_type)
        if not archetype:
            self.logger.error('Received a custom object type: %s that has not been defined yet. Msg=%s',
                              msg.object_type, msg)
            return None

        custom_object = self.custom_object_factory(self._robot,
                                                   archetype,
                                                   msg.object_id)

        self.logger.debug('Allocated object_id=%s to CustomObject %s', msg.object_id, custom_object)

        if custom_object:
            self._custom_objects[msg.object_id] = custom_object
        return custom_object

    def _allocate_charger(self, msg):
        charger = self.charger_factory(self._robot, msg.object_id)
        if self._charger:
            self.logger.warning('Allocating multiple chargers: existing charger=%s msg=%s', self._charger, msg)
            return None

        self._charger = charger

        self.logger.debug('Allocated object_id=%s to Charger %s', msg.object_id, charger)
        return charger

    def _remove_all_custom_marker_object_instances(self):
        for obj_id, obj in list(self._custom_objects.items()):
            if isinstance(obj, objects.CustomObject):
                self.logger.info("Removing CustomObject instance: id %s = obj '%s'", obj_id, obj)
                self._custom_objects.pop(obj_id, None)

    def _remove_all_fixed_custom_object_instances(self):
        for obj_id, obj in list(self._custom_objects.items()):
            if isinstance(obj, objects.FixedCustomObject):
                self.logger.info("Removing FixedCustomObject instance: id %s = obj '%s'", obj_id, obj)
                self._custom_objects.pop(obj_id, None)

    #### Private Event Handlers ####

    def _on_face_observed(self, _robot, _event_type, msg):
        """Adds a newly observed face to the world view."""
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
            if face:
                self._faces[face.face_id] = face

    def _on_object_observed(self, _robot, _event_type, msg):
        """Adds a newly observed custom object to the world view."""
        first_custom_type = protocol.ObjectType.Value("FIRST_CUSTOM_OBJECT_TYPE")
        if msg.object_type == objects.LIGHT_CUBE_1_TYPE:
            if msg.object_id not in self._objects:
                light_cube = self._light_cube.get(objects.LIGHT_CUBE_1_TYPE)
                if light_cube:
                    light_cube.object_id = msg.object_id
                    self._objects[msg.object_id] = light_cube

        elif msg.object_type == protocol.ObjectType.Value("CHARGER_BASIC"):
            if msg.object_id not in self._objects:
                charger = self._allocate_charger(msg)
                if charger:
                    self._objects[msg.object_id] = charger

        elif first_custom_type <= msg.object_type < (first_custom_type + protocol.CustomType.Value("CUSTOM_TYPE_COUNT")):
            if msg.object_id not in self._objects:
                custom_object = self._allocate_custom_marker_object(msg)
                if custom_object:
                    self._objects[msg.object_id] = custom_object
