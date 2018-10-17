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

All observable objects have a marker of a known size attached to them,
which allows Vector to recognize the object and its position and rotation("pose").

Vector connects to his Light Cubes with BLE.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['LIGHT_CUBE_1_TYPE', 'OBJECT_VISIBILITY_TIMEOUT',
           'EvtObjectObserved', 'EvtObjectAppeared', 'EvtObjectDisappeared', 'EvtObjectFinishedMove',
           'LightCube']

import math
import time

from . import lights, sync, util
from .events import Events

from .messaging import protocol


class EvtObjectObserved():  # pylint: disable=too-few-public-methods
    """Triggered whenever an object is visually identified by the robot.

    A stream of these events are produced while an object is visible to the robot.
    Each event has an updated image_box field.

    See EvtObjectAppeared if you only want to know when an object first
    becomes visible.

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


#: Length of time in seconds to go without receiving an observed event before
#: assuming that Vector can no longer see an object.
OBJECT_VISIBILITY_TIMEOUT = 0.4


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

            last_seen_time = obj.time_since_last_seen
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
        self._observed_timeout_handler = self._robot.loop.call_later(
            self.visibility_timeout, self._observed_timeout)

    def _observed_timeout(self):
        # Triggered when the element is no longer considered "visible".
        # i.e. visibility_timeout seconds after the last observed event.
        self._is_visible = False
        self._robot.events.dispatch_event(EvtObjectDisappeared(self), Events.object_disappeared)

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
        self._robot.events.dispatch_event(EvtObjectObserved(self, image_rect, pose), Events.object_observed)

        if newly_visible:
            self._robot.events.dispatch_event(EvtObjectAppeared(self, image_rect, pose), Events.object_appeared)


#: LIGHT_CUBE_1_TYPE's markers look like 2 concentric circles with lines and gaps.
LIGHT_CUBE_1_TYPE = protocol.ObjectType.Value("BLOCK_LIGHTCUBE1")


class LightCube(ObservableObject):
    """Represents Vector's Cube."""

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
        self.robot.events.subscribe(
            self._on_object_connection_state_changed,
            Events.object_connection_state)

        self.robot.events.subscribe(
            self._on_object_moved,
            Events.object_moved)

        self.robot.events.subscribe(
            self._on_object_stopped_moving,
            Events.object_stopped_moving)

        self.robot.events.subscribe(
            self._on_object_up_axis_changed,
            Events.object_up_axis_changed)

        self.robot.events.subscribe(
            self._on_object_tapped,
            Events.object_tapped)

        self.robot.events.subscribe(
            self._on_object_observed,
            Events.robot_observed_object)

        self.robot.events.subscribe(
            self._on_object_connection_lost,
            Events.cube_connection_lost)

    #### Public Methods ####

    def teardown(self):
        """All faces will be torn down by the world when no longer needed."""
        self.robot.events.unsubscribe(
            self._on_object_connection_state_changed,
            Events.object_connection_state)

        self.robot.events.unsubscribe(
            self._on_object_moved,
            Events.object_moved)

        self.robot.events.unsubscribe(
            self._on_object_stopped_moving,
            Events.object_stopped_moving)

        self.robot.events.unsubscribe(
            self._on_object_up_axis_changed,
            Events.object_up_axis_changed)

        self.robot.events.unsubscribe(
            self._on_object_tapped,
            Events.object_tapped)

        self.robot.events.unsubscribe(
            self._on_object_observed,
            Events.robot_observed_object)

        self.robot.events.unsubscribe(
            self._on_object_connection_lost,
            Events.cube_connection_lost)

    @sync.Synchronizer.wrap
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

            with anki_vector.Robot("my_robot_serial_number") as robot:
                # ensure we are connected to a cube
                robot.world.connect_cube()

                if robot.world.connected_light_cube:
                    cube = robot.world.connected_light_cube

                    cube.set_light_corners(anki_vector.lights.blue_light,
                                           anki_vector.lights.green_light,
                                           anki_vector.lights.red_light,
                                           anki_vector.lights.white_light)
                    time.sleep(3)

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

            with anki_vector.Robot("my_robot_serial_number") as robot:
                # ensure we are connected to a cube
                robot.world.connect_cube()

                if robot.world.connected_light_cube:
                    cube = robot.world.connected_light_cube

                    # Set cube lights to yellow
                    cube.set_lights(anki_vector.lights.yellow_light)
                    time.sleep(3)

        :param light: The settings for the lights
        :param color_profile: The profile to be used for the cube lights
        """
        return self.set_light_corners(light, light, light, light, color_profile)

    def set_lights_off(self, color_profile: lights.ColorProfile = lights.WHITE_BALANCED_CUBE_PROFILE):
        """Set all lights off on the cube

        .. testcode::

            import anki_vector

            import time

            with anki_vector.Robot("my_robot_serial_number") as robot:
                # ensure we are connected to a cube
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

            import anki_vector

            with anki_vector.Robot("my_robot_serial_number") as robot:
                last_tapped_time = robot.world.connected_light_cube.last_tapped_time
        """
        return self._last_tapped_time

    @property
    def last_tapped_robot_timestamp(self) -> float:
        """The time the object was last tapped in robot time.

        .. testcode::

            import anki_vector

            with anki_vector.Robot("my_robot_serial_number") as robot:
                last_tapped_robot_timestamp = robot.world.connected_light_cube.last_tapped_robot_timestamp
        """
        return self._last_tapped_robot_timestamp

    @property
    def last_moved_time(self) -> float:
        """The time the object was last moved in SDK time.

        .. testcode::

            import anki_vector

            with anki_vector.Robot("my_robot_serial_number") as robot:
                last_moved_time = robot.world.connected_light_cube.last_moved_time
        """
        return self._last_moved_time

    @property
    def last_moved_robot_timestamp(self) -> float:
        """The time the object was last moved in robot time.

        .. testcode::

            import anki_vector

            with anki_vector.Robot("my_robot_serial_number") as robot:
                last_moved_robot_timestamp = robot.world.connected_light_cube.last_moved_robot_timestamp
        """
        return self._last_moved_robot_timestamp

    @property
    def last_moved_start_time(self) -> float:
        """The time the object most recently started moving in SDK time.

        .. testcode::

            import anki_vector

            with anki_vector.Robot("my_robot_serial_number") as robot:
                last_moved_start_time = robot.world.connected_light_cube.last_moved_start_time
        """
        return self._last_moved_start_time

    @property
    def last_moved_start_robot_timestamp(self) -> float:
        """The time the object more recently started moving in robot time.

        .. testcode::

            import anki_vector

            with anki_vector.Robot("my_robot_serial_number") as robot:
                last_moved_start_robot_timestamp = robot.world.connected_light_cube.last_moved_start_robot_timestamp
        """
        return self._last_moved_start_robot_timestamp

    @property
    def last_up_axis_changed_time(self) -> float:
        """The time the object's orientation last changed in SDK time.

        .. testcode::

            import anki_vector

            with anki_vector.Robot("my_robot_serial_number") as robot:
                last_up_axis_changed_time = robot.world.connected_light_cube.last_up_axis_changed_time
        """
        return self._last_up_axis_changed_time

    @property
    def last_up_axis_changed_robot_timestamp(self) -> float:
        """Time the object's orientation last changed in robot time.

        .. testcode::

            import anki_vector

            with anki_vector.Robot("my_robot_serial_number") as robot:
                last_up_axis_changed_robot_timestamp = robot.world.connected_light_cube.last_up_axis_changed_robot_timestamp
        """
        return self._last_up_axis_changed_robot_timestamp

    @property
    def up_axis(self) -> protocol.UpAxis:
        """The object's up_axis value from the last time it changed.

        .. testcode::

            import anki_vector

            with anki_vector.Robot("my_robot_serial_number") as robot:
                up_axis = robot.world.connected_light_cube.up_axis
        """
        return self._up_axis

    @property
    def is_moving(self) -> bool:
        """True if the cube's accelerometer indicates that the cube is moving.

        .. testcode::

            import anki_vector

            with anki_vector.Robot("my_robot_serial_number") as robot:
                is_moving = robot.world.connected_light_cube.is_moving
        """
        return self._is_moving

    @property
    def is_connected(self) -> bool:
        """True if the cube is currently connected to the robot.

        .. testcode::

            import anki_vector

            with anki_vector.Robot("my_robot_serial_number") as robot:
                is_connected = robot.world.connected_light_cube.is_connected
        """
        return self._is_connected

    @property
    def top_face_orientation_rad(self) -> float:
        """Angular distance from the current reported up axis.

        .. testcode::

            import anki_vector

            with anki_vector.Robot("my_robot_serial_number") as robot:
                top_face_orientation_rad = robot.world.connected_light_cube.top_face_orientation_rad
        """
        return self._top_face_orientation_rad

    @property
    def factory_id(self) -> str:
        """The unique hardware id of the physical cube.

        .. testcode::

            import anki_vector

            with anki_vector.Robot("my_robot_serial_number") as robot:
                factory_id = robot.world.connected_light_cube.factory_id
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

            with anki_vector.Robot("my_robot_serial_number") as robot:
                descriptive_name = robot.world.connected_light_cube.descriptive_name
        """
        return "{0} id={1} factory_id={2} is_connected={3}".format(self.__class__.__name__, self._object_id, self._factory_id, self._is_connected)

    @property
    def object_id(self) -> int:
        """The internal ID assigned to the object.

        This value can only be assigned once as it is static on the robot.

        .. testcode::

            import anki_vector

            with anki_vector.Robot("my_robot_serial_number") as robot:
                object_id = robot.world.connected_light_cube.object_id
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

    def _on_object_connection_state_changed(self, _, msg):
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

    def _on_object_moved(self, _, msg):
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

    def _on_object_stopped_moving(self, _, msg):
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
            self._robot.events.dispatch_event(EvtObjectFinishedMove(self, move_duration), Events.object_finished_move)
        else:
            self.logger.warning('An object not currently tracked by the world stopped moving with id {0}'.format(msg.object_id))

    def _on_object_up_axis_changed(self, _, msg):
        if msg.object_id == self._object_id:

            now = time.time()
            self._up_axis = msg.up_axis
            self._last_event_time = now
            self._last_up_axis_changed_time = now
            self._last_up_axis_changed_robot_timestamp = msg.timestamp
        else:
            self.logger.warning('Up Axis changed on an object not currently tracked by the world with id {0}'.format(msg.object_id))

    def _on_object_tapped(self, _, msg):
        if msg.object_id == self._object_id:

            now = time.time()
            self._last_event_time = now
            self._last_tapped_time = now
            self._last_tapped_robot_timestamp = msg.timestamp
        else:
            self.logger.warning('Tapped an object not currently tracked by the world with id {0}'.format(msg.object_id))

    def _on_object_observed(self, _, msg):
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
        else:
            self.logger.warning('Observed an object not currently tracked by the world with id {0}'.format(msg.object_id))

    def _on_object_connection_lost(self, _, msg):
        if msg.object_id == self._object_id:
            self._is_connected = False
