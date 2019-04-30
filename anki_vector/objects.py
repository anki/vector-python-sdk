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

"""Object and Light Cube recognition.

Vector can recognize and track a number of different types of objects.

These objects may be visible (currently observed by the robot's camera)
and tappable (in the case of the Light Cube that ships with the robot).

The Light Cube is known as a :class:`LightCube` by the SDK. The cube
has controllable lights, and sensors that can determine when it's being
moved or tapped.

Objects can generate events which can be subscribed to from the anki_vector.events
class, such as object_appeared (of type EvtObjectAppeared), and
object_disappeared (of type EvtObjectDisappeared), which are broadcast
based on both robot originating events and local state.

All observable objects have a marker of a known size attached to them, which allows Vector
to recognize the object and its position and rotation ("pose").  You can attach
markers to your own objects for Vector to recognize by printing them out from the
online documentation.  They will be detected as :class:`CustomObject` instances.

Vector connects to his Light Cube with BLE.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['LIGHT_CUBE_1_TYPE', 'OBJECT_VISIBILITY_TIMEOUT',
           'EvtObjectAppeared', 'EvtObjectDisappeared', 'EvtObjectFinishedMove', 'EvtObjectObserved',
           'Charger', 'CustomObjectArchetype', 'CustomObject', 'CustomObjectMarkers', 'CustomObjectTypes',
           'FixedCustomObject', 'LightCube', 'ObservableObject']

# TODO Curious why events like the following aren't listed? At least some do seem to be supported in other parts of anki_vector.
# EvtObjectTapped, EvtObjectConnectChanged, EvtObjectConnected, EvtObjectLocated, EvtObjectMoving, EvtObjectMovingStarted, EvtObjectMovingStopped


import collections
import math
import time

from . import connection, lights, util
from .events import Events

from .messaging import protocol

#: Length of time in seconds to go without receiving an observed event before
#: assuming that Vector can no longer see an object.
OBJECT_VISIBILITY_TIMEOUT = 0.8


class EvtObjectObserved():  # pylint: disable=too-few-public-methods
    """Triggered whenever an object is visually identified by the robot.

    A stream of these events are produced while an object is visible to the robot.
    Each event has an updated image_box field.

    See EvtObjectAppeared if you only want to know when an object first
    becomes visible.

    .. testcode::

        import time

        import anki_vector
        from anki_vector.events import Events
        from anki_vector.util import degrees

        def handle_object_observed(robot, event_type, event):
            # This will be called whenever an EvtObjectObserved is dispatched -
            # whenever an Object comes into view.
            print(f"--------- Vector observed an object --------- \\n{event.obj}")

        with anki_vector.Robot(default_logging=False,
                               show_viewer=True,
                               show_3d_viewer=True,
                               enable_nav_map_feed=True) as robot:
            # Place Vector's cube where he can see it

            robot.events.subscribe(handle_object_observed, Events.object_observed)

            # If necessary, move Vector's Head and Lift down
            robot.behavior.set_lift_height(0.0)
            robot.behavior.set_head_angle(degrees(0.0))

            time.sleep(3.0)

    :param obj: The object that was observed
    :param image_rect: An :class:`anki_vector.util.ImageRect`: defining where the object is within Vector's camera view
    :param pose: The :class:`anki_vector.util.Pose`: defining the position and rotation of the object
    """

    def __init__(self, obj, image_rect: util.ImageRect, pose: util.Pose):
        self.obj = obj
        self.image_rect = image_rect
        self.pose = pose


class EvtObjectAppeared():  # pylint: disable=too-few-public-methods
    """Triggered whenever an object is first visually identified by a robot.

    This differs from EvtObjectObserved in that it's only triggered when
    an object initially becomes visible.  If it disappears for more than
    OBJECT_VISIBILITY_TIMEOUT seconds and then is seen again, a
    EvtObjectDisappeared will be dispatched, followed by another
    EvtObjectAppeared event.

    For continuous tracking information about a visible object, see
    EvtObjectObserved.

    .. testcode::

        import time

        import anki_vector
        from anki_vector.events import Events
        from anki_vector.util import degrees

        def handle_object_appeared(robot, event_type, event):
            # This will be called whenever an EvtObjectAppeared is dispatched -
            # whenever an Object comes into view.
            print(f"--------- Vector started seeing an object --------- \\n{event.obj}")

        with anki_vector.Robot(default_logging=False,
                               show_viewer=True,
                               show_3d_viewer=True,
                               enable_nav_map_feed=True) as robot:
            # Place Vector's cube where he can see it

            robot.events.subscribe(handle_object_appeared, Events.object_appeared)

            # If necessary, move Vector's Head and Lift down
            robot.behavior.set_lift_height(0.0)
            robot.behavior.set_head_angle(degrees(0.0))

            time.sleep(3.0)

    :param obj: The object that is starting to be observed
    :param image_rect: An :class:`anki_vector.util.ImageRect`: defining where the object is within Vector's camera view
    :param pose: The :class:`anki_vector.util.Pose`: defining the position and rotation of the object
    """

    def __init__(self, obj, image_rect: util.ImageRect, pose: util.Pose):
        self.obj = obj
        self.image_rect = image_rect
        self.pose = pose


class EvtObjectDisappeared():  # pylint: disable=too-few-public-methods
    """Triggered whenever an object that was previously being observed is no longer visible.

    .. testcode::

        import time

        import anki_vector
        from anki_vector.events import Events
        from anki_vector.util import degrees

        def handle_object_disappeared(robot, event_type, event):
            # This will be called whenever an EvtObjectDisappeared is dispatched -
            # whenever an Object goes out of view.
            print(f"--------- Vector stopped seeing an object --------- \\n{event.obj}")

        with anki_vector.Robot(default_logging=False,
                               show_viewer=True,
                               show_3d_viewer=True,
                               enable_nav_map_feed=True) as robot:
            # Place Vector's cube where he can see it

            robot.events.subscribe(handle_object_disappeared, Events.object_disappeared)

            # If necessary, move Vector's Head and Lift down
            robot.behavior.set_lift_height(0.0)
            robot.behavior.set_head_angle(degrees(0.0))

            time.sleep(3.0)

    :param obj: The object that is no longer being observed
    """

    def __init__(self, obj):
        self.obj = obj


class EvtObjectFinishedMove():  # pylint: disable=too-few-public-methods
    """Triggered when an active object stops moving.

    :param obj: The object that moved
    :param move_duration: The duration of the move
    """

    def __init__(self, obj, move_duration: float):
        self.obj = obj
        self.move_duration = move_duration


class ObservableObject(util.Component):
    """Represents any object Vector can see in the world."""

    visibility_timeout = OBJECT_VISIBILITY_TIMEOUT

    def __init__(self, robot, **kw):
        super().__init__(robot, **kw)

        self._pose: util.Pose = None

        #: The time the last event was received.
        #: ``None`` if no events have yet been received.
        self._last_event_time: float = None

        #: The time the element was last observed by the robot.
        #: ``None`` if the element has not yet been observed.
        self._last_observed_time: float = None

        #: The robot's timestamp of the last observed event.
        #: ``None`` if the element has not yet been observed.
        #: In milliseconds relative to robot epoch.
        self._last_observed_robot_timestamp: int = None

        #: The ImageRect defining where the
        #: object was last visible within Vector's camera view.
        #: ``None`` if the element has not yet been observed.
        self._last_observed_image_rect: util.ImageRect = None

        self._is_visible: bool = False
        self._observed_timeout_handler: callable = None

    def __repr__(self):
        extra = self._repr_values()
        if extra:
            extra = ' ' + extra
        if self.pose:
            extra += ' pose=%s' % self.pose

        return '<%s%s is_visible=%s>' % (self.__class__.__name__,
                                         extra, self.is_visible)
    #### Properties ####

    @property
    def pose(self) -> util.Pose:
        """The pose of this object in the world.

        Is ``None`` for elements that don't have pose information.

        .. testcode::

            import anki_vector
            import time

            # First, place a cube directly in front of Vector so he can observe it.

            with anki_vector.Robot() as robot:
                connectionResult = robot.world.connect_cube()
                connected_cube = robot.world.connected_light_cube

                for _ in range(16):
                    connected_cube = robot.world.connected_light_cube
                    if connected_cube:
                        print(connected_cube)
                        print("last observed timestamp: " + str(connected_cube.last_observed_time) + ", robot timestamp: " + str(connected_cube.last_observed_robot_timestamp))
                        print(robot.world.connected_light_cube.pose)
                    time.sleep(0.5)
        """
        return self._pose

    @property
    def last_event_time(self) -> float:
        """Time this object last received an event from Vector."""
        return self._last_event_time

    @property
    def last_observed_time(self) -> float:
        """Time this object was last seen."""
        return self._last_observed_time

    @property
    def last_observed_robot_timestamp(self) -> int:
        """Time this object was last seen according to Vector's time."""
        return self._last_observed_robot_timestamp

    @property
    def time_since_last_seen(self) -> float:
        """Time since this object was last seen. math.inf if never seen.

        .. testcode::

            import anki_vector

            with anki_vector.Robot(enable_face_detection=True) as robot:
                for face in robot.world.visible_faces:
                    print(f"time_since_last_seen: {face.time_since_last_seen}")
        """
        if self._last_observed_time is None:
            return math.inf
        return time.time() - self._last_observed_time

    @property
    def last_observed_image_rect(self) -> util.ImageRect:
        """The location in 2d camera space where this object was last seen."""
        return self._last_observed_image_rect

    @property
    def is_visible(self) -> bool:
        """True if the element has been observed recently, False otherwise.

        "recently" is defined as :attr:`visibility_timeout` seconds.
        """
        return self._is_visible

    #### Private Methods ####

    def _repr_values(self):  # pylint: disable=no-self-use
        return ''

    def _reset_observed_timeout_handler(self):
        if self._observed_timeout_handler is not None:
            self._observed_timeout_handler.cancel()
        self._observed_timeout_handler = self.conn.loop.call_later(self.visibility_timeout, self._observed_timeout)

    def _observed_timeout(self):
        # Triggered when the element is no longer considered "visible".
        # i.e. visibility_timeout seconds after the last observed event.
        self._is_visible = False
        self.conn.run_soon(self._robot.events.dispatch_event(EvtObjectDisappeared(self), Events.object_disappeared))

    def _on_observed(self, pose: util.Pose, image_rect: util.ImageRect, robot_timestamp: int):
        # Called from subclasses on their corresponding observed messages.
        newly_visible = self._is_visible is False
        self._is_visible = True

        now = time.time()
        self._last_observed_time = now
        self._last_observed_robot_timestamp = robot_timestamp
        self._last_event_time = now
        self._last_observed_image_rect = image_rect
        self._pose = pose
        self._reset_observed_timeout_handler()
        self.conn.run_soon(self._robot.events.dispatch_event(EvtObjectObserved(self, image_rect, pose), Events.object_observed))

        if newly_visible:
            self.conn.run_soon(self._robot.events.dispatch_event(EvtObjectAppeared(self, image_rect, pose), Events.object_appeared))


#: LIGHT_CUBE_1_TYPE's markers look like 2 concentric circles with lines and gaps.
LIGHT_CUBE_1_TYPE = protocol.ObjectType.Value("BLOCK_LIGHTCUBE1")


class LightCube(ObservableObject):
    """Represents Vector's Cube.

    The LightCube object has four LEDs that Vector can actively manipulate and communicate with.

    As Vector drives around, he uses the position of objects that he recognizes, including his cube,
    to localize himself, taking note of the :class:`anki_vector.util.Pose` of the objects.

    You can subscribe to cube events including :class:`anki_vector.events.Events.object_tapped`,
    :class:`anki_vector.events.Events.object_appeared`, and :class:`anki_vector.events.Events.object_disappeared`.

    Vector supports 1 LightCube.

    See parent class :class:`ObservableObject` for additional properties
    and methods.
    """

    #: Length of time in seconds to go without receiving an observed event before
    #: assuming that Vector can no longer see an object. Can be overridden in subclasses.
    visibility_timeout = OBJECT_VISIBILITY_TIMEOUT

    def __init__(self, robot, **kw):
        super().__init__(robot, **kw)

        #: The time the object was last tapped.
        #: ``None`` if the cube wasn't tapped yet.
        self._last_tapped_time: float = None

        #: The robot's timestamp of the last tapped event.
        #: ``None`` if the cube wasn't tapped yet.
        #: In milliseconds relative to robot epoch.
        self._last_tapped_robot_timestamp: int = None

        #: The time the object was last moved.
        #: ``None`` if the cube wasn't moved yet.
        self._last_moved_time: float = None

        #: The robot's timestamp of the last move event.
        #: ``None`` if the cube wasn't moved yet.
        #: In milliseconds relative to robot epoch.
        self._last_moved_robot_timestamp: int = None

        #: The time the object started moving when last moved.
        self._last_moved_start_time: float = None

        #: The robot's timestamp of when the object started moving when last moved.
        #: ``None`` if the cube wasn't moved yet.
        #: In milliseconds relative to robot epoch.
        self._last_moved_start_robot_timestamp: int = None

        #: The time the last up axis event was received.
        #: ``None`` if no events have yet been received.
        self._last_up_axis_changed_time: float = None

        #: The robot's timestamp of the last up axis event.
        #: ``None`` if the there has not been an up axis event.
        #: In milliseconds relative to robot epoch.
        self._last_up_axis_changed_robot_timestamp: int = None

        # The object's up_axis value from the last time it changed.
        self._up_axis: protocol.UpAxis = None

        #: True if the cube's accelerometer indicates that the cube is moving.
        self._is_moving: bool = False

        #: True if the cube is currently connected to the robot via radio.
        self._is_connected: bool = False

        #: angular distance from the current reported up axis
        #: ``None`` if the object has not yet been observed.
        self._top_face_orientation_rad: float = None

        self._object_id: str = None

        #: unique identification of the physical cube
        self._factory_id: str = None

        #: Subscribe to relevant events
        self.robot.events.subscribe(self._on_object_connection_state_changed,
                                    Events.object_connection_state)

        self.robot.events.subscribe(self._on_object_moved,
                                    Events.object_moved)

        self.robot.events.subscribe(self._on_object_stopped_moving,
                                    Events.object_stopped_moving)

        self.robot.events.subscribe(self._on_object_up_axis_changed,
                                    Events.object_up_axis_changed)

        self.robot.events.subscribe(self._on_object_tapped,
                                    Events.object_tapped)

        self.robot.events.subscribe(self._on_object_observed,
                                    Events.robot_observed_object)

        self.robot.events.subscribe(self._on_object_connection_lost,
                                    Events.cube_connection_lost)

    #### Public Methods ####

    def teardown(self):
        """All faces will be torn down by the world when no longer needed."""
        self.robot.events.unsubscribe(self._on_object_connection_state_changed,
                                      Events.object_connection_state)

        self.robot.events.unsubscribe(self._on_object_moved,
                                      Events.object_moved)

        self.robot.events.unsubscribe(self._on_object_stopped_moving,
                                      Events.object_stopped_moving)

        self.robot.events.unsubscribe(self._on_object_up_axis_changed,
                                      Events.object_up_axis_changed)

        self.robot.events.unsubscribe(self._on_object_tapped,
                                      Events.object_tapped)

        self.robot.events.unsubscribe(self._on_object_observed,
                                      Events.robot_observed_object)

        self.robot.events.unsubscribe(self._on_object_connection_lost,
                                      Events.cube_connection_lost)

    @connection.on_connection_thread()
    async def set_light_corners(self,
                                light1: lights.Light,
                                light2: lights.Light,
                                light3: lights.Light,
                                light4: lights.Light,
                                color_profile: lights.ColorProfile = lights.WHITE_BALANCED_CUBE_PROFILE):
        """Set the light for each corner.

        .. testcode::

            import anki_vector

            import time

            with anki_vector.Robot() as robot:
                robot.world.connect_cube()

                if robot.world.connected_light_cube:
                    cube = robot.world.connected_light_cube

                    cube.set_light_corners(anki_vector.lights.blue_light,
                                           anki_vector.lights.green_light,
                                           anki_vector.lights.red_light,
                                           anki_vector.lights.white_light)
                    time.sleep(3)

                    cube.set_lights_off()

        :param light1: The settings for the first light.
        :param light2: The settings for the second light.
        :param light3: The settings for the third light.
        :param light4: The settings for the fourth light.
        :param color_profile: The profile to be used for the cube lights
        """
        params = lights.package_request_params((light1, light2, light3, light4), color_profile)
        req = protocol.SetCubeLightsRequest(
            object_id=self._object_id,
            on_color=params['on_color'],
            off_color=params['off_color'],
            on_period_ms=params['on_period_ms'],
            off_period_ms=params['off_period_ms'],
            transition_on_period_ms=params['transition_on_period_ms'],
            transition_off_period_ms=params['transition_off_period_ms'],
            offset=[0, 0, 0, 0],
            relative_to_x=0.0,
            relative_to_y=0.0,
            rotate=False,
            make_relative=protocol.SetCubeLightsRequest.OFF)  # pylint: disable=no-member
        return await self.grpc_interface.SetCubeLights(req)

    def set_lights(self, light: lights.Light, color_profile: lights.ColorProfile = lights.WHITE_BALANCED_CUBE_PROFILE):
        """Set all lights on the cube

        .. testcode::

            import anki_vector

            import time

            with anki_vector.Robot() as robot:
                robot.world.connect_cube()

                if robot.world.connected_light_cube:
                    cube = robot.world.connected_light_cube

                    # Set cube lights to yellow
                    cube.set_lights(anki_vector.lights.yellow_light)
                    time.sleep(3)

                    cube.set_lights_off()

        :param light: The settings for the lights
        :param color_profile: The profile to be used for the cube lights
        """
        return self.set_light_corners(light, light, light, light, color_profile)

    def set_lights_off(self, color_profile: lights.ColorProfile = lights.WHITE_BALANCED_CUBE_PROFILE):
        """Set all lights off on the cube

        .. testcode::

            import anki_vector

            import time

            with anki_vector.Robot() as robot:
                robot.world.connect_cube()

                if robot.world.connected_light_cube:
                    cube = robot.world.connected_light_cube

                    # Set cube lights to yellow
                    cube.set_lights(anki_vector.lights.yellow_light)
                    time.sleep(3)

                    # Turn off cube lights
                    cube.set_lights_off()

        :param color_profile: The profile to be used for the cube lights
        """

        return self.set_light_corners(lights.off_light, lights.off_light, lights.off_light, lights.off_light, color_profile)

    #### Private Methods ####

    def _repr_values(self):
        return 'object_id=%s' % self.object_id

    #### Properties ####

    @property
    def last_tapped_time(self) -> float:
        """The time the object was last tapped in SDK time.

        .. testcode::

            import time
            import anki_vector

            with anki_vector.Robot() as robot:
                print("disconnecting from any connected cube...")
                robot.world.disconnect_cube()

                time.sleep(2)

                print("connect to a cube...")
                connectionResult = robot.world.connect_cube()

                print("For the next 8 seconds, please tap and move the cube. Cube properties will be logged to console.")
                for _ in range(16):
                    connected_cube = robot.world.connected_light_cube
                    if connected_cube:
                        print(f'last_tapped_time: {connected_cube.last_tapped_time}')
                    time.sleep(0.5)
        """
        return self._last_tapped_time

    @property
    def last_tapped_robot_timestamp(self) -> float:
        """The time the object was last tapped in robot time.

        .. testcode::

            import time
            import anki_vector

            with anki_vector.Robot() as robot:
                print("disconnecting from any connected cube...")
                robot.world.disconnect_cube()

                time.sleep(2)

                print("connect to a cube...")
                connectionResult = robot.world.connect_cube()

                print("For the next 8 seconds, please tap and move the cube. Cube properties will be logged to console.")
                for _ in range(16):
                    connected_cube = robot.world.connected_light_cube
                    if connected_cube:
                        print(f'last_tapped_robot_timestamp: {connected_cube.last_tapped_robot_timestamp}')
                    time.sleep(0.5)
        """
        return self._last_tapped_robot_timestamp

    @property
    def last_moved_time(self) -> float:
        """The time the object was last moved in SDK time.

        .. testcode::

            import time
            import anki_vector

            with anki_vector.Robot() as robot:
                print("disconnecting from any connected cube...")
                robot.world.disconnect_cube()

                time.sleep(2)

                print("connect to a cube...")
                connectionResult = robot.world.connect_cube()

                print("For the next 8 seconds, please tap and move the cube. Cube properties will be logged to console.")
                for _ in range(16):
                    connected_cube = robot.world.connected_light_cube
                    if connected_cube:
                        print(f'last_moved_time: {connected_cube.last_moved_time}')
                    time.sleep(0.5)
        """
        return self._last_moved_time

    @property
    def last_moved_robot_timestamp(self) -> float:
        """The time the object was last moved in robot time.

        .. testcode::

            import time
            import anki_vector

            with anki_vector.Robot() as robot:
                print("disconnecting from any connected cube...")
                robot.world.disconnect_cube()

                time.sleep(2)

                print("connect to a cube...")
                connectionResult = robot.world.connect_cube()

                print("For the next 8 seconds, please tap and move the cube. Cube properties will be logged to console.")
                for _ in range(16):
                    connected_cube = robot.world.connected_light_cube
                    if connected_cube:
                        print(f'last_moved_robot_timestamp: {connected_cube.last_moved_robot_timestamp}')
                    time.sleep(0.5)
        """
        return self._last_moved_robot_timestamp

    @property
    def last_moved_start_time(self) -> float:
        """The time the object most recently started moving in SDK time.

        .. testcode::

            import time
            import anki_vector

            with anki_vector.Robot() as robot:
                print("disconnecting from any connected cube...")
                robot.world.disconnect_cube()

                time.sleep(2)

                print("connect to a cube...")
                connectionResult = robot.world.connect_cube()

                print("For the next 8 seconds, please tap and move the cube. Cube properties will be logged to console.")
                for _ in range(16):
                    connected_cube = robot.world.connected_light_cube
                    if connected_cube:
                        print(f'last_moved_start_time: {connected_cube.last_moved_start_time}')
                    time.sleep(0.5)
        """
        return self._last_moved_start_time

    @property
    def last_moved_start_robot_timestamp(self) -> float:
        """The time the object more recently started moving in robot time.

        .. testcode::

            import time
            import anki_vector

            with anki_vector.Robot() as robot:
                print("disconnecting from any connected cube...")
                robot.world.disconnect_cube()

                time.sleep(2)

                print("connect to a cube...")
                connectionResult = robot.world.connect_cube()

                print("For the next 8 seconds, please tap and move the cube. Cube properties will be logged to console.")
                for _ in range(16):
                    connected_cube = robot.world.connected_light_cube
                    if connected_cube:
                        print(f'last_moved_start_robot_timestamp: {connected_cube.last_moved_start_robot_timestamp}')
                    time.sleep(0.5)
        """
        return self._last_moved_start_robot_timestamp

    @property
    def last_up_axis_changed_time(self) -> float:
        """The time the object's orientation last changed in SDK time.

        .. testcode::

            import time
            import anki_vector

            with anki_vector.Robot() as robot:
                print("disconnecting from any connected cube...")
                robot.world.disconnect_cube()

                time.sleep(2)

                print("connect to a cube...")
                connectionResult = robot.world.connect_cube()

                print("For the next 8 seconds, please tap and move the cube. Cube properties will be logged to console.")
                for _ in range(16):
                    connected_cube = robot.world.connected_light_cube
                    if connected_cube:
                        print(f'last_up_axis_changed_time: {connected_cube.last_up_axis_changed_time}')
                    time.sleep(0.5)
        """
        return self._last_up_axis_changed_time

    @property
    def last_up_axis_changed_robot_timestamp(self) -> float:
        """Time the object's orientation last changed in robot time.

        .. testcode::

            import time
            import anki_vector

            with anki_vector.Robot() as robot:
                print("disconnecting from any connected cube...")
                robot.world.disconnect_cube()

                time.sleep(2)

                print("connect to a cube...")
                connectionResult = robot.world.connect_cube()

                print("For the next 8 seconds, please tap and move the cube. Cube properties will be logged to console.")
                for _ in range(16):
                    connected_cube = robot.world.connected_light_cube
                    if connected_cube:
                        print(f'last_up_axis_changed_robot_timestamp: {connected_cube.last_up_axis_changed_robot_timestamp}')
                    time.sleep(0.5)
        """
        return self._last_up_axis_changed_robot_timestamp

    @property
    def up_axis(self) -> protocol.UpAxis:
        """The object's up_axis value from the last time it changed.

        .. testcode::

            import time
            import anki_vector

            with anki_vector.Robot() as robot:
                print("disconnecting from any connected cube...")
                robot.world.disconnect_cube()

                time.sleep(2)

                print("connect to a cube...")
                connectionResult = robot.world.connect_cube()

                print("For the next 8 seconds, please tap and move the cube. Cube properties will be logged to console.")
                for _ in range(16):
                    connected_cube = robot.world.connected_light_cube
                    if connected_cube:
                        print(f'up_axis: {connected_cube.up_axis}')
                    time.sleep(0.5)
        """
        return self._up_axis

    @property
    def is_moving(self) -> bool:
        """True if the cube's accelerometer indicates that the cube is moving.

        .. testcode::

            import time
            import anki_vector

            with anki_vector.Robot() as robot:
                print("disconnecting from any connected cube...")
                robot.world.disconnect_cube()

                time.sleep(2)

                print("connect to a cube...")
                connectionResult = robot.world.connect_cube()

                print("For the next 8 seconds, please tap and move the cube. Cube properties will be logged to console.")
                for _ in range(16):
                    connected_cube = robot.world.connected_light_cube
                    if connected_cube:
                        print(f'is_moving: {connected_cube.is_moving}')
                    time.sleep(0.5)
        """
        return self._is_moving

    @property
    def is_connected(self) -> bool:
        """True if the cube is currently connected to the robot.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                robot.world.connect_cube()
                if robot.world.connected_light_cube:
                    cube = robot.world.connected_light_cube
                    print(f"{cube.is_connected}")
        """
        return self._is_connected

    @property
    def top_face_orientation_rad(self) -> float:
        """Angular distance from the current reported up axis.

        .. testcode::

            import time
            import anki_vector

            with anki_vector.Robot() as robot:
                print("disconnecting from any connected cube...")
                robot.world.disconnect_cube()

                time.sleep(2)

                print("connect to a cube...")
                connectionResult = robot.world.connect_cube()

                print("For the next 8 seconds, please tap and move the cube. Cube properties will be logged to console.")
                for _ in range(16):
                    connected_cube = robot.world.connected_light_cube
                    if connected_cube:
                        print(f'top_face_orientation_rad: {connected_cube.top_face_orientation_rad}')
                    time.sleep(0.5)
        """
        return self._top_face_orientation_rad

    @property
    def factory_id(self) -> str:
        """The unique hardware id of the physical cube.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                robot.world.connect_cube()
                if robot.world.connected_light_cube:
                    cube = robot.world.connected_light_cube
                    print(f"{cube.factory_id}")
        """
        return self._factory_id

    @factory_id.setter
    def factory_id(self, value: str):
        self._factory_id = value

    @property
    def descriptive_name(self) -> str:
        """A descriptive name for this ObservableObject instance.

        Note: Sub-classes should override this to add any other relevant info
        for that object type.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                robot.world.connect_cube()
                if robot.world.connected_light_cube:
                    cube = robot.world.connected_light_cube
                    print(f"{cube.descriptive_name}")
        """
        return f"{self.__class__.__name__}\nid={self._object_id}\nfactory_id={self._factory_id}\nis_connected={self._is_connected}"

    @property
    def object_id(self) -> int:
        """The internal ID assigned to the object.

        This value can only be assigned once as it is static on the robot.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                robot.world.connect_cube()
                if robot.world.connected_light_cube:
                    cube = robot.world.connected_light_cube
                    print(f"{cube.object_id}")
        """
        return self._object_id

    @object_id.setter
    def object_id(self, value: str):
        if self._object_id is not None:
            # We cannot currently rely on robot ensuring that object ID remains static
            # E.g. in the case of a cube disconnecting and reconnecting it's removed
            # and then re-added to blockworld which results in a new ID.
            self.logger.warning("Changing object_id for %s from %s to %s", self.__class__, self._object_id, value)
        else:
            self.logger.debug("Setting object_id for %s to %s", self.__class__, value)
        self._object_id = value

    #### Private Event Handlers ####

    def _on_object_connection_state_changed(self, _robot, _event_type, msg):
        if msg.object_type == LIGHT_CUBE_1_TYPE:
            self._object_id = msg.object_id

            if self._factory_id != msg.factory_id:
                self.logger.debug('Factory id changed from {0} to {1}'.format(self._factory_id, msg.factory_id))
                self._factory_id = msg.factory_id

            if self._is_connected != msg.connected:
                if msg.connected:
                    self.logger.debug('Object connected: %s', self)
                else:
                    self.logger.debug('Object disconnected: %s', self)
                self._is_connected = msg.connected

    def _on_object_moved(self, _robot, _event_type, msg):
        if msg.object_id == self._object_id:
            now = time.time()
            started_moving = not self._is_moving
            self._is_moving = True
            self._last_event_time = now
            self._last_moved_time = now
            self._last_moved_robot_timestamp = msg.timestamp

            if started_moving:
                self._last_moved_start_time = now
                self._last_moved_start_robot_timestamp = msg.timestamp
        else:
            self.logger.warning('An object not currently tracked by the world moved with id {0}'.format(msg.object_id))

    async def _on_object_stopped_moving(self, _robot, _event_type, msg):
        if msg.object_id == self._object_id:
            now = time.time()
            self._last_event_time = now
            move_duration = 0.0

            # _is_moving might already be false.
            # This happens for very short movements that are immediately
            # considered stopped (no acceleration info is present)
            if self._is_moving:
                self._is_moving = False
                move_duration = now - self._last_moved_start_time
            await self._robot.events.dispatch_event(EvtObjectFinishedMove(self, move_duration), Events.object_finished_move)
        else:
            self.logger.warning('An object not currently tracked by the world stopped moving with id {0}'.format(msg.object_id))

    def _on_object_up_axis_changed(self, _robot, _event_type, msg):
        if msg.object_id == self._object_id:

            now = time.time()
            self._up_axis = msg.up_axis
            self._last_event_time = now
            self._last_up_axis_changed_time = now
            self._last_up_axis_changed_robot_timestamp = msg.timestamp
        else:
            self.logger.warning('Up Axis changed on an object not currently tracked by the world with id {0}'.format(msg.object_id))

    def _on_object_tapped(self, _robot, _event_type, msg):
        if msg.object_id == self._object_id:

            now = time.time()
            self._last_event_time = now
            self._last_tapped_time = now
            self._last_tapped_robot_timestamp = msg.timestamp
        else:
            self.logger.warning('Tapped an object not currently tracked by the world with id {0}'.format(msg.object_id))

    def _on_object_observed(self, _robot, _event_type, msg):
        if msg.object_id == self._object_id:

            pose = util.Pose(x=msg.pose.x, y=msg.pose.y, z=msg.pose.z,
                             q0=msg.pose.q0, q1=msg.pose.q1,
                             q2=msg.pose.q2, q3=msg.pose.q3,
                             origin_id=msg.pose.origin_id)
            image_rect = util.ImageRect(msg.img_rect.x_top_left,
                                        msg.img_rect.y_top_left,
                                        msg.img_rect.width,
                                        msg.img_rect.height)
            self._top_face_orientation_rad = msg.top_face_orientation_rad

            self._on_observed(pose, image_rect, msg.timestamp)

    def _on_object_connection_lost(self, _robot, _event_type, msg):
        if msg.object_id == self._object_id:
            self._is_connected = False


class Charger(ObservableObject):
    """Vector's charger object, which the robot can observe and drive toward.
    We get an :class:`anki_vector.objects.EvtObjectObserved` message when the
    robot sees the charger.

    See parent class :class:`ObservableObject` for additional properties
    and methods.

    .. testcode::

        import anki_vector

        # Position Vector so he can see his charger
        with anki_vector.Robot() as robot:
            if robot.world.charger:
                print('Robot is aware of charger: {0}'.format(robot.world.charger))
    """

    def __init__(self, robot, object_id: int, **kw):
        super().__init__(robot, **kw)

        self._object_id = object_id

        self.robot.events.subscribe(self._on_object_observed,
                                    Events.robot_observed_object)

    #### Public Methods ####

    def teardown(self):
        """All objects will be torn down by the world when the world closes."""

        self.robot.events.unsubscribe(self._on_object_observed,
                                      Events.robot_observed_object)

    #### Properties ####
    @property
    def object_id(self) -> int:
        """The internal ID assigned to the object.

        .. testcode::

            import anki_vector

            # Position Vector so he can see his charger
            with anki_vector.Robot() as robot:
                if robot.world.charger:
                    charger_object_id = robot.world.charger.object_id
                    print(f"charger_object_id: {charger_object_id}")

        This value can only be assigned once as it is static on the robot.
        """
        return self._object_id

    @object_id.setter
    def object_id(self, value: str):
        if self._object_id is not None:
            # We cannot currently rely on robot ensuring that object ID remains static
            # E.g. in the case of a cube disconnecting and reconnecting it's removed
            # and then re-added to blockworld which results in a new ID.
            self.logger.warning("Changing object_id for %s from %s to %s", self.__class__, self._object_id, value)
        else:
            self.logger.debug("Setting object_id for %s to %s", self.__class__, value)
        self._object_id = value

    @property
    def descriptive_name(self) -> str:
        """A descriptive name for this ObservableObject instance.

        Note: Sub-classes should override this to add any other relevant info
        for that object type.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                if robot.world.charger:
                    print(f"{robot.world.charger.descriptive_name}")
        """
        return f"{self.__class__.__name__} id={self._object_id}"

    #### Private Methods ####

    def _on_object_observed(self, _robot, _event_type, msg):
        if msg.object_id == self._object_id:

            pose = util.Pose(x=msg.pose.x, y=msg.pose.y, z=msg.pose.z,
                             q0=msg.pose.q0, q1=msg.pose.q1,
                             q2=msg.pose.q2, q3=msg.pose.q3,
                             origin_id=msg.pose.origin_id)
            image_rect = util.ImageRect(msg.img_rect.x_top_left,
                                        msg.img_rect.y_top_left,
                                        msg.img_rect.width,
                                        msg.img_rect.height)

            self._on_observed(pose, image_rect, msg.timestamp)


class CustomObjectArchetype():
    """An object archetype defined by the SDK. It is bound to a specific objectType e.g ``CustomType00``.

    This defined object is given a size in the x,y and z axis. The dimensions
    of the markers on the object are also defined.

    See :class:`CustomObjectMarkers`.

    When the robot observes custom objects, they will be linked to these archetypes.
    These can be created using the methods
    :meth:`~anki_vector.world.World.define_custom_box`,
    :meth:`~anki_vector.world.World.define_custom_cube`, or
    :meth:`~anki_vector.world.World.define_custom_wall`.
    """

    def __init__(self,
                 custom_type: protocol.CustomType,
                 x_size_mm: float,
                 y_size_mm: float,
                 z_size_mm: float,
                 marker_width_mm: float,
                 marker_height_mm: float,
                 is_unique: bool):

        self._custom_type = custom_type
        self._x_size_mm = x_size_mm
        self._y_size_mm = y_size_mm
        self._z_size_mm = z_size_mm
        self._marker_width_mm = marker_width_mm
        self._marker_height_mm = marker_height_mm
        self._is_unique = is_unique

    #### Properties ####

    @property
    def custom_type(self) -> protocol.CustomType:
        """id of this archetype on the robot.

        See :class:`CustomObjectMarkers`.

        .. testcode::

            import anki_vector
            with anki_vector.Robot(enable_custom_object_detection=True) as robot:
                for obj in robot.world.custom_object_archetypes:
                    print('custom object archetype defined with type: {0}'.format(obj.custom_type))
        """
        return self._custom_type

    @property
    def x_size_mm(self) -> float:
        """Size of this object in its X axis, in millimeters.

        See :class:`CustomObjectMarkers`.

        .. testcode::

            import anki_vector
            with anki_vector.Robot(enable_custom_object_detection=True) as robot:
                for obj in robot.world.custom_object_archetypes:
                    print('custom object archetype defined with dimensions: {0}mm x {1}mm x {2}mm'.format(obj.x_size_mm, obj.y_size_mm, obj.z_size_mm))
        """
        return self._x_size_mm

    @property
    def y_size_mm(self) -> float:
        """Size of this object in its Y axis, in millimeters.

        See :class:`CustomObjectMarkers`.

        .. testcode::

            import anki_vector
            with anki_vector.Robot(enable_custom_object_detection=True) as robot:
                for obj in robot.world.custom_object_archetypes:
                    print('custom object archetype defined with dimensions: {0}mm x {1}mm x {2}mm'.format(obj.x_size_mm, obj.y_size_mm, obj.z_size_mm))
        """
        return self._y_size_mm

    @property
    def z_size_mm(self) -> float:
        """Size of this object in its Z axis, in millimeters.

        See :class:`CustomObjectMarkers`.

        .. testcode::

            import anki_vector
            with anki_vector.Robot(enable_custom_object_detection=True) as robot:
                for obj in robot.world.custom_object_archetypes:
                    print('custom object archetype defined with dimensions: {0}mm x {1}mm x {2}mm'.format(obj.x_size_mm, obj.y_size_mm, obj.z_size_mm))
        """
        return self._z_size_mm

    @property
    def marker_width_mm(self) -> float:
        """Width in millimeters of the marker on this object.

        See :class:`CustomObjectMarkers`.

        .. testcode::

            import anki_vector
            with anki_vector.Robot(enable_custom_object_detection=True) as robot:
                for obj in robot.world.custom_object_archetypes:
                    print('custom object archetype defined with marker size: {0}mm x {1}mm'.format(obj.marker_width_mm, obj.marker_height_mm))
        """
        return self._marker_width_mm

    @property
    def marker_height_mm(self) -> float:
        """Height in millimeters of the marker on this object.

        See :class:`CustomObjectMarkers`.

        .. testcode::

            import anki_vector
            with anki_vector.Robot(enable_custom_object_detection=True) as robot:
                for obj in robot.world.custom_object_archetypes:
                    print('custom object archetype defined with marker size: {0}mm x {1}mm'.format(obj.marker_width_mm, obj.marker_height_mm))
        """
        return self._marker_height_mm

    @property
    def is_unique(self) -> bool:
        """True if there should only be one of this object type in the world.

        See :class:`CustomObjectMarkers`.
        """
        return self._is_unique

    #### Private Methods ####

    def __repr__(self):
        return ('custom_type={self.custom_type} '
                'x_size_mm={self.x_size_mm:.1f} '
                'y_size_mm={self.y_size_mm:.1f} '
                'z_size_mm={self.z_size_mm:.1f} '
                'marker_width_mm={self.marker_width_mm:.1f} '
                'marker_height_mm={self.marker_height_mm:.1f} '
                'is_unique={self.is_unique}'.format(self=self))


class CustomObject(ObservableObject):
    """An object defined by the SDK observed by the robot.  The object will
    reference a :class:`CustomObjectArchetype`, with additional instance data.

    These objects are created automatically by the engine when Vector observes
    an object with custom markers. For Vector to see one of these you must first
    define an archetype with custom markers, via one of the following methods:
    :meth:`~anki_vector.world.World.define_custom_box`.
    :meth:`~anki_vector.world.World.define_custom_cube`, or
    :meth:`~anki_vector.world.World.define_custom_wall`

    See :class:`CustomObjectMarkers`.
    """

    def __init__(self,
                 robot,
                 archetype: CustomObjectArchetype,
                 object_id: int, **kw):
        super().__init__(robot, **kw)

        self._object_id = object_id
        self._archetype = archetype

        self.robot.events.subscribe(self._on_object_observed,
                                    Events.robot_observed_object)

    #### Public Methods ####

    def teardown(self):
        """All objects will be torn down by the world when no longer needed.

        See :class:`CustomObjectMarkers`.
        """

        self.robot.events.unsubscribe(self._on_object_observed,
                                      Events.robot_observed_object)

    #### Properties ####

    @property
    def object_id(self) -> int:
        """The internal ID assigned to the object.

        This value can only be assigned once as it is static on the robot.

        See :class:`CustomObjectMarkers`.

        .. testcode::

            import anki_vector
            from anki_vector.objects import CustomObjectMarkers, CustomObjectTypes

            with anki_vector.Robot(enable_custom_object_detection=True) as robot:
                robot.world.define_custom_cube(custom_object_type=CustomObjectTypes.CustomType00,
                                               marker=CustomObjectMarkers.Circles2,
                                               size_mm=20.0,
                                               marker_width_mm=50.0, marker_height_mm=50.0)

                # have the robot observe a custom object in the real world with the Circles2 marker

                for obj in robot.world.visible_custom_objects:
                    print('custom object seen with id: {0}'.format(obj.object_id))
        """
        return self._object_id

    @object_id.setter
    def object_id(self, value: str):
        if self._object_id is not None:
            # We cannot currently rely on robot ensuring that object ID remains static
            # E.g. in the case of a cube disconnecting and reconnecting it's removed
            # and then re-added to robot's internal world model which results in a new ID.
            self.logger.warning("Changing object_id for %s from %s to %s", self.__class__, self._object_id, value)
        else:
            self.logger.debug("Setting object_id for %s to %s", self.__class__, value)
        self._object_id = value

    @property
    def archetype(self) -> CustomObjectArchetype:
        """Archetype defining this custom object's properties.

        See :class:`CustomObjectMarkers`.

        .. testcode::

            import anki_vector
            from anki_vector.objects import CustomObjectMarkers, CustomObjectTypes

            with anki_vector.Robot(enable_custom_object_detection=True) as robot:
                robot.world.define_custom_cube(custom_object_type=CustomObjectTypes.CustomType00,
                                               marker=CustomObjectMarkers.Circles2,
                                               size_mm=20.0,
                                               marker_width_mm=50.0, marker_height_mm=50.0)

                # have the robot observe a custom object in the real world with the Circles2 marker

                for obj in robot.world.visible_custom_objects:
                    print('custom object seen with archetype: {0}'.format(obj.archetype))
        """
        return self._archetype

    @property
    def descriptive_name(self) -> str:
        """A descriptive name for this CustomObject instance.

        See :class:`CustomObjectMarkers`.

        .. testcode::

            import anki_vector
            from anki_vector.objects import CustomObjectMarkers, CustomObjectTypes

            with anki_vector.Robot(enable_custom_object_detection=True) as robot:
                robot.world.define_custom_cube(custom_object_type=CustomObjectTypes.CustomType00,
                                               marker=CustomObjectMarkers.Circles2,
                                               size_mm=20.0,
                                               marker_width_mm=50.0, marker_height_mm=50.0)

                # have the robot observe a custom object in the real world with the Circles2 marker

                for obj in robot.world.visible_custom_objects:
                    print('custom object seen with name: {0}'.format(obj.descriptive_name))
        """
        return "%s id=%d" % (self.__class__.__name__, self.object_id)

    #### Private Methods ####

    def _repr_values(self):
        return ('object_type={archetype.custom_type} '
                'x_size_mm={archetype.x_size_mm:.1f} '
                'y_size_mm={archetype.y_size_mm:.1f} '
                'z_size_mm={archetype.z_size_mm:.1f} '
                'is_unique={archetype.is_unique}'.format(archetype=self._archetype))

    def _on_object_observed(self, _robot, _event_type, msg):
        if msg.object_id == self._object_id:

            pose = util.Pose(x=msg.pose.x, y=msg.pose.y, z=msg.pose.z,
                             q0=msg.pose.q0, q1=msg.pose.q1,
                             q2=msg.pose.q2, q3=msg.pose.q3,
                             origin_id=msg.pose.origin_id)
            image_rect = util.ImageRect(msg.img_rect.x_top_left,
                                        msg.img_rect.y_top_left,
                                        msg.img_rect.width,
                                        msg.img_rect.height)

            self._on_observed(pose, image_rect, msg.timestamp)


class _CustomObjectType(collections.namedtuple('_CustomObjectType', 'name id')):
    # Tuple mapping between Proto CustomObjectType name and ID
    # All instances will be members of CustomObjectType

    # Keep _CustomObjectType as lightweight as a normal namedtuple
    __slots__ = ()

    def __str__(self):
        return 'CustomObjectTypes.%s' % self.name


class CustomObjectTypes():  # pylint: disable=too-few-public-methods
    """Defines all available custom object types.

    For use with world.define_custom methods such as
    :meth:`anki_vector.world.World.define_custom_box`,
    :meth:`anki_vector.world.World.define_custom_cube`, and
    :meth:`anki_vector.world.World.define_custom_wall`

    See :class:`CustomObjectMarkers`.

    .. testcode::

        import anki_vector
        from anki_vector.objects import CustomObjectMarkers, CustomObjectTypes

        with anki_vector.Robot(enable_custom_object_detection=True) as robot:
            robot.world.define_custom_cube(custom_object_type=CustomObjectTypes.CustomType00,
                                           marker=CustomObjectMarkers.Circles2,
                                           size_mm=20.0,
                                           marker_width_mm=50.0, marker_height_mm=50.0)
    """

    #: CustomType00 - the first custom object type
    CustomType00 = _CustomObjectType("CustomType00", protocol.CustomType.Value("CUSTOM_TYPE_00"))

    #:
    CustomType01 = _CustomObjectType("CustomType01", protocol.CustomType.Value("CUSTOM_TYPE_01"))

    #:
    CustomType02 = _CustomObjectType("CustomType02", protocol.CustomType.Value("CUSTOM_TYPE_02"))

    #:
    CustomType03 = _CustomObjectType("CustomType03", protocol.CustomType.Value("CUSTOM_TYPE_03"))

    #:
    CustomType04 = _CustomObjectType("CustomType04", protocol.CustomType.Value("CUSTOM_TYPE_04"))

    #:
    CustomType05 = _CustomObjectType("CustomType05", protocol.CustomType.Value("CUSTOM_TYPE_05"))

    #:
    CustomType06 = _CustomObjectType("CustomType06", protocol.CustomType.Value("CUSTOM_TYPE_06"))

    #:
    CustomType07 = _CustomObjectType("CustomType07", protocol.CustomType.Value("CUSTOM_TYPE_07"))

    #:
    CustomType08 = _CustomObjectType("CustomType08", protocol.CustomType.Value("CUSTOM_TYPE_08"))

    #:
    CustomType09 = _CustomObjectType("CustomType09", protocol.CustomType.Value("CUSTOM_TYPE_09"))

    #:
    CustomType10 = _CustomObjectType("CustomType10", protocol.CustomType.Value("CUSTOM_TYPE_10"))

    #:
    CustomType11 = _CustomObjectType("CustomType11", protocol.CustomType.Value("CUSTOM_TYPE_11"))

    #:
    CustomType12 = _CustomObjectType("CustomType12", protocol.CustomType.Value("CUSTOM_TYPE_12"))

    #:
    CustomType13 = _CustomObjectType("CustomType13", protocol.CustomType.Value("CUSTOM_TYPE_13"))

    #:
    CustomType14 = _CustomObjectType("CustomType14", protocol.CustomType.Value("CUSTOM_TYPE_14"))

    #:
    CustomType15 = _CustomObjectType("CustomType15", protocol.CustomType.Value("CUSTOM_TYPE_15"))

    #:
    CustomType16 = _CustomObjectType("CustomType16", protocol.CustomType.Value("CUSTOM_TYPE_16"))

    #:
    CustomType17 = _CustomObjectType("CustomType17", protocol.CustomType.Value("CUSTOM_TYPE_17"))

    #:
    CustomType18 = _CustomObjectType("CustomType18", protocol.CustomType.Value("CUSTOM_TYPE_18"))

    #: CustomType19 - the last custom object type
    CustomType19 = _CustomObjectType("CustomType19", protocol.CustomType.Value("CUSTOM_TYPE_19"))


class _CustomObjectMarker(collections.namedtuple('_CustomObjectMarker', 'name id')):
    # Tuple mapping between Proto CustomObjectMarker name and ID
    # All instances will be members of CustomObjectMarker

    # Keep _CustomObjectMarker as lightweight as a normal namedtuple
    __slots__ = ()

    def __str__(self):
        return 'CustomObjectMarkers.%s' % self.name


class CustomObjectMarkers():  # pylint: disable=too-few-public-methods
    """Defines all available custom object markers.

    For use with world.define_custom methods such as
    :meth:`anki_vector.world.World.define_custom_box`,
    :meth:`anki_vector.world.World.define_custom_cube`, and
    :meth:`anki_vector.world.World.define_custom_wall`

    See :class:`CustomObject`.

    .. testcode::

        import anki_vector
        from anki_vector.objects import CustomObjectMarkers, CustomObjectTypes

        with anki_vector.Robot(enable_custom_object_detection=True) as robot:
            robot.world.define_custom_cube(custom_object_type=CustomObjectTypes.CustomType00,
                                           marker=CustomObjectMarkers.Circles2,
                                           size_mm=20.0,
                                           marker_width_mm=50.0, marker_height_mm=50.0)
    """

    #: .. image:: ../images/custom_markers/SDK_2Circles.png
    Circles2 = _CustomObjectMarker("Circles2", protocol.CustomObjectMarker.Value("CUSTOM_MARKER_CIRCLES_2"))

    #: .. image:: ../images/custom_markers/SDK_3Circles.png
    Circles3 = _CustomObjectMarker("Circles3", protocol.CustomObjectMarker.Value("CUSTOM_MARKER_CIRCLES_3"))

    #: .. image:: ../images/custom_markers/SDK_4Circles.png
    Circles4 = _CustomObjectMarker("Circles4", protocol.CustomObjectMarker.Value("CUSTOM_MARKER_CIRCLES_4"))

    #: .. image:: ../images/custom_markers/SDK_5Circles.png
    Circles5 = _CustomObjectMarker("Circles5", protocol.CustomObjectMarker.Value("CUSTOM_MARKER_CIRCLES_5"))

    #: .. image:: ../images/custom_markers/SDK_2Diamonds.png
    Diamonds2 = _CustomObjectMarker("Diamonds2", protocol.CustomObjectMarker.Value("CUSTOM_MARKER_DIAMONDS_2"))

    #: .. image:: ../images/custom_markers/SDK_3Diamonds.png
    Diamonds3 = _CustomObjectMarker("Diamonds3", protocol.CustomObjectMarker.Value("CUSTOM_MARKER_DIAMONDS_3"))

    #: .. image:: ../images/custom_markers/SDK_4Diamonds.png
    Diamonds4 = _CustomObjectMarker("Diamonds4", protocol.CustomObjectMarker.Value("CUSTOM_MARKER_DIAMONDS_4"))

    #: .. image:: ../images/custom_markers/SDK_5Diamonds.png
    Diamonds5 = _CustomObjectMarker("Diamonds5", protocol.CustomObjectMarker.Value("CUSTOM_MARKER_DIAMONDS_5"))

    #: .. image:: ../images/custom_markers/SDK_2Hexagons.png
    Hexagons2 = _CustomObjectMarker("Hexagons2", protocol.CustomObjectMarker.Value("CUSTOM_MARKER_HEXAGONS_2"))

    #: .. image:: ../images/custom_markers/SDK_3Hexagons.png
    Hexagons3 = _CustomObjectMarker("Hexagons3", protocol.CustomObjectMarker.Value("CUSTOM_MARKER_HEXAGONS_3"))

    #: .. image:: ../images/custom_markers/SDK_4Hexagons.png
    Hexagons4 = _CustomObjectMarker("Hexagons4", protocol.CustomObjectMarker.Value("CUSTOM_MARKER_HEXAGONS_4"))

    #: .. image:: ../images/custom_markers/SDK_5Hexagons.png
    Hexagons5 = _CustomObjectMarker("Hexagons5", protocol.CustomObjectMarker.Value("CUSTOM_MARKER_HEXAGONS_5"))

    #: .. image:: ../images/custom_markers/SDK_2Triangles.png
    Triangles2 = _CustomObjectMarker("Triangles2", protocol.CustomObjectMarker.Value("CUSTOM_MARKER_TRIANGLES_2"))

    #: .. image:: ../images/custom_markers/SDK_3Triangles.png
    Triangles3 = _CustomObjectMarker("Triangles3", protocol.CustomObjectMarker.Value("CUSTOM_MARKER_TRIANGLES_3"))

    #: .. image:: ../images/custom_markers/SDK_4Triangles.png
    Triangles4 = _CustomObjectMarker("Triangles4", protocol.CustomObjectMarker.Value("CUSTOM_MARKER_TRIANGLES_4"))

    #: .. image:: ../images/custom_markers/SDK_5Triangles.png
    Triangles5 = _CustomObjectMarker("Triangles5", protocol.CustomObjectMarker.Value("CUSTOM_MARKER_TRIANGLES_5"))


class FixedCustomObject(util.Component):
    """A fixed object defined by the SDK. It is given a pose and x,y,z sizes.

    This object cannot be observed by the robot so its pose never changes.
    The position is static in Vector's world view; once instantiated, these
    objects never move. This could be used to make Vector aware of objects and
    know to plot a path around them even when they don't have any markers.

    To create these use :meth:`~anki_vector.world.World.create_custom_fixed_object`

    .. testcode::

        import anki_vector
        from anki_vector.util import degrees, Pose
        import time

        with anki_vector.Robot(enable_custom_object_detection=True) as robot:
            robot.world.create_custom_fixed_object(Pose(100, 0, 0, angle_z=degrees(0)),
                                                   10, 100, 100, relative_to_robot=True)
    """

    def __init__(self,
                 robot,
                 pose: util.Pose,
                 x_size_mm: float,
                 y_size_mm: float,
                 z_size_mm: float,
                 object_id: int, **kw):
        super().__init__(robot, **kw)
        self._pose = pose
        self._x_size_mm = x_size_mm
        self._y_size_mm = y_size_mm
        self._z_size_mm = z_size_mm
        self._object_id = object_id

    def __repr__(self):
        return ('<%s pose=%s object_id=%d x_size_mm=%.1f y_size_mm=%.1f z_size_mm=%.1f=>' %
                (self.__class__.__name__, self.pose, self.object_id,
                 self.x_size_mm, self.y_size_mm, self.z_size_mm))

    #### Public Methods ####

    def teardown(self):
        pass

    #### Properties ####
    @property
    def object_id(self) -> int:
        """The internal ID assigned to the object.

        This value can only be assigned once as it is static in the engine.

        .. testcode::

            import anki_vector
            from anki_vector.util import degrees, Pose
            import time

            with anki_vector.Robot(enable_custom_object_detection=True) as robot:
                obj = robot.world.create_custom_fixed_object(Pose(100, 0, 0, angle_z=degrees(0)),
                                                                  10, 100, 100, relative_to_robot=True)
                print('fixed custom object id: {0}'.format(obj.object_id))
        """
        return self._object_id

    @object_id.setter
    def object_id(self, value: int):
        if self._object_id is not None:
            raise ValueError("Cannot change object ID once set (from %s to %s)" % (self._object_id, value))
        self.logger.debug("Updated object_id for %s from %s to %s", self.__class__, self._object_id, value)
        self._object_id = value

    @property
    def pose(self) -> util.Pose:
        """The pose of the object in the world.

        .. testcode::

            import anki_vector
            from anki_vector.util import degrees, Pose
            import time

            with anki_vector.Robot(enable_custom_object_detection=True) as robot:
                obj = robot.world.create_custom_fixed_object(Pose(100, 0, 0, angle_z=degrees(0)),
                                                                  10, 100, 100, relative_to_robot=True)
                print('fixed custom object id: {0}'.format(obj.pose))
        """
        return self._pose

    @property
    def x_size_mm(self) -> float:
        """The length of the object in its X axis, in millimeters.

        .. testcode::

            import anki_vector
            from anki_vector.util import degrees, Pose
            import time

            with anki_vector.Robot(enable_custom_object_detection=True) as robot:
                obj = robot.world.create_custom_fixed_object(Pose(100, 0, 0, angle_z=degrees(0)),
                                                                  10, 100, 100, relative_to_robot=True)
                print('fixed custom object size: {0}mm x {1}mm x {2}mm'.format(obj.x_size_mm, obj.y_size_mm, obj.z_size_mm))
        """
        return self._x_size_mm

    @property
    def y_size_mm(self) -> float:
        """The length of the object in its Y axis, in millimeters.

        .. testcode::

            import anki_vector
            from anki_vector.util import degrees, Pose
            import time

            with anki_vector.Robot(enable_custom_object_detection=True) as robot:
                obj = robot.world.create_custom_fixed_object(Pose(100, 0, 0, angle_z=degrees(0)),
                                                                  10, 100, 100, relative_to_robot=True)
                print('fixed custom object size: {0}mm x {1}mm x {2}mm'.format(obj.x_size_mm, obj.y_size_mm, obj.z_size_mm))
        """
        return self._y_size_mm

    @property
    def z_size_mm(self) -> float:
        """The length of the object in its Z axis, in millimeters.

        .. testcode::

            import anki_vector
            from anki_vector.util import degrees, Pose
            import time

            with anki_vector.Robot(enable_custom_object_detection=True) as robot:
                obj = robot.world.create_custom_fixed_object(Pose(100, 0, 0, angle_z=degrees(0)),
                                                                  10, 100, 100, relative_to_robot=True)
                print('fixed custom object size: {0}mm x {1}mm x {2}mm'.format(obj.x_size_mm, obj.y_size_mm, obj.z_size_mm))
        """
        return self._z_size_mm
