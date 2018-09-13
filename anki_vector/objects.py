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

"""Object and Power Cube recognition.

Victor can recognize and track a number of different types of objects.

These objects may be visible (currently observed by the robot's camera)
and tappable (in the case of the Power Cube that ships with the robot).

The Power Cube is known as a :class:`LightCube` by the SDK.  The cube has
controllable lights, and sensors that can determine when its being moved
or tapped.

Objects can emit several events such as :class:`EvtObjectObserved` when
the robot sees (or continues to see) the object with its camera, or
:class:`EvtObjectTapped` if a power cube is tapped by a player.  You
can either observe the object's instance directly, or capture all such events
for all objects by observing them on :class:`anki_vector.world.World` instead.

All observable objects have a marker attached to them, which allows Victor
to recognize the object and its position and rotation("pose").
"""


# TODO EvtObjectObserved, EvtObjectTapped, and others in Cozmo's object.py are not implemented. Should they be? If not, remove from docs above?

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['LightCube1Type',
           'OBJECT_VISIBILITY_TIMEOUT',
           'LightCube']

import math
import time

from . import lights, sync, util

from .messaging import protocol

#: Length of time in seconds to go without receiving an observed event before
#: assuming that Victor can no longer see an object.
OBJECT_VISIBILITY_TIMEOUT = 0.4

#: LightCube1Type's markers look like 2 concentric circles with lines and gaps
LightCube1Type = protocol.ObjectType.Value("BLOCK_LIGHTCUBE1")


# TODO Instead inherit from ObservableObject, like for Cozmo?
# TODO In this class, how are we deciding whether a member has a leading underscore or not?
class LightCube(util.Component):
    """Represents Vector's Cube"""

    #: Length of time in seconds to go without receiving an observed event before
    #: assuming that Victor can no longer see an element. Can be overridden in sub
    #: classes.
    visibility_timeout = OBJECT_VISIBILITY_TIMEOUT

    def __init__(self, robot, world, **kw):
        super().__init__(robot, **kw)
        #: :class:`anki_vector.world.World`: The robot's world in which this element is located.
        self._world = world

        self._pose = None

        #: float: The time the object was last tapped
        #: ``None`` if the cube wasn't tapped yet.
        self.last_tapped_time = None

        #: int: The robot's timestamp of the last tapped event.
        #: ``None`` if the cube wasn't tapped yet.
        #: In milliseconds relative to robot epoch.
        self.last_tapped_robot_timestamp = None

        #: float: The time the object was last moved
        #: ``None`` if the cube wasn't moved yet.
        self.last_moved_time = None

        #: float: The time the object started moving when last moved
        self.last_moved_start_time = None

        #: int: The robot's timestamp of the last move event.
        #: ``None`` if the cube wasn't moved yet.
        #: In milliseconds relative to robot epoch.
        self.last_moved_robot_timestamp = None

        #: int: The robot's timestamp of when the object started moving when last moved
        #: ``None`` if the cube wasn't moved yet.
        #: In milliseconds relative to robot epoch.
        self.last_moved_start_robot_timestamp = None

        #: float: The time the last up axis event was received.
        #: ``None`` if no events have yet been received.
        self.last_up_axis_changed_time = None

        #: int: The robot's timestamp of the last up axis event.
        #: ``None`` if the there has not been an up axis event.
        #: In milliseconds relative to robot epoch.
        self.last_up_axis_changed_robot_timestamp = None

        #: float: The time the last event was received.
        #: ``None`` if no events have yet been received.
        self.last_event_time = None

        #: float: The time the element was last observed by the robot.
        #: ``None`` if the element has not yet been observed.
        self.last_observed_time = None

        #: int: The robot's timestamp of the last observed event.
        #: ``None`` if the element has not yet been observed.
        #: In milliseconds relative to robot epoch.
        self.last_observed_robot_timestamp = None

        # The object's up_axis value from the last time it changed.
        self.up_axis = None

        #: bool: True if the cube's accelerometer indicates that the cube is moving.
        self.is_moving = False

        #: bool: True if the cube is currently connected to the robot via radio.
        self.is_connected = False

        #: :class:`~anki_vector.util.ImageRect`: The ImageRect defining where the
        #: object was last visible within Victor's camera view.
        #: ``None`` if the element has not yet been observed.
        self._last_observed_image_rect = None

        #: float: angular distance from the current reported up axis
        #: ``None`` if the element has not yet been observed.
        self._top_face_orientation_rad = None

        self._is_visible = False
        self._observed_timeout_handler = None

        self._object_id = None

        #: string: unique identification of the physical cube
        self._factory_id = None

    def __repr__(self):
        extra = self._repr_values()
        if extra:
            extra = ' ' + extra
        if self.pose:
            extra += ' pose=%s' % self.pose

        return '<%s%s is_visible=%s>' % (self.__class__.__name__,
                                         extra, self.is_visible)

    #### Public Methods ####

    @sync.Synchronizer.wrap
    async def set_light_corners(self,
                                light1: lights.Light,
                                light2: lights.Light,
                                light3: lights.Light,
                                light4: lights.Light,
                                color_profile: lights.ColorProfile = lights.WHITE_BALANCED_CUBE_PROFILE):
        """Set the light for each corner

        .. code-block:: python

            # ensure we are connected to a cube
            robot.world.connect_cube()

            if robot.world.connected_light_cube:
                cube = robot.world.connected_light_cube

                # Set cube lights to red, green, blue, and white
                cube.set_light_corners(anki_vector.lights.blue_light,
                                       anki_vector.lights.green_light,
                                       anki_vector.lights.red_light,
                                       anki_vector.lights.white_light)
                time.sleep(2.5)

        :param light1: The settings for the first light.
        :param light2: The settings for the second light.
        :param light3: The settings for the third light.
        :param light4: The settings for the fourth light.
        :param color_profile: The profile to be used for the cube lights
        """
        params = lights.package_request_params((light1, light2, light3, light4), color_profile)
        print(params)
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

        .. code-block:: python

            # ensure we are connected to a cube
            robot.world.connect_cube()

            if robot.world.connected_light_cube:
                cube = robot.world.connected_light_cube

                # Set cube lights to yellow
                cube.set_lights(anki_vector.lights.yellow_light)

        :param light: The settings for the lights
        :param color_profile: The profile to be used for the cube lights
        """
        return self.set_light_corners(light, light, light, light, color_profile)

    def set_lights_off(self, color_profile: lights.ColorProfile = lights.WHITE_BALANCED_CUBE_PROFILE):
        """Set all lights off on the cube

        .. code-block:: python

            # ensure we are connected to a cube
            robot.world.connect_cube()

            if robot.world.connected_light_cube:
                cube = robot.world.connected_light_cube

                # Set cube lights to yellow
                cube.set_lights(anki_vector.lights.yellow_light)
                time.sleep(2.5)

                # Turn off cube lights
                cube.set_lights_off()

        :param color_profile: The profile to be used for the cube lights
        """

        return self.set_light_corners(lights.off_light, lights.off_light, lights.off_light, lights.off_light, color_profile)

    #### Private Methods ####

    def _repr_values(self):
        return 'object_id=%s' % self.object_id

    def _reset_observed_timeout_handler(self):
        if self._observed_timeout_handler is not None:
            self._observed_timeout_handler.cancel()
        self._observed_timeout_handler = self._robot.loop.call_later(
            self.visibility_timeout, self._observed_timeout)

    def _observed_timeout(self):
        # triggered when the element is no longer considered "visible"
        # ie. visibility_timeout seconds after the last observed event
        self._is_visible = False
        self._dispatch_disappeared_event()

    def _dispatch_observed_event(self, image_rect):
        # @TODO: feed this into a proper event system
        # Image Rect refers to the bounding rect in victors vision where the object was seen
        pass

    def _dispatch_appeared_event(self, image_rect):
        # @TODO: feed this into a proper event system
        # Image Rect refers to the bounding rect in victors vision where the object was seen
        pass

    def _dispatch_disappeared_event(self):
        # @TODO: feed this into a proper event system
        pass

    def _on_observed(self, image_rect, timestamp):
        # Called from subclasses on their corresponding observed messages
        newly_visible = self._is_visible is False
        self._is_visible = True

        now = time.time()
        self.last_observed_time = now
        self.last_observed_robot_timestamp = timestamp
        self.last_event_time = now
        self._last_observed_image_rect = image_rect
        self._reset_observed_timeout_handler()
        self._dispatch_observed_event(image_rect)

        if newly_visible:
            self._dispatch_appeared_event(image_rect)

    #### Properties ####

    @property
    def factory_id(self) -> str:
        """The unique hardware id of the physical cube."""
        return self._factory_id

    @factory_id.setter
    def factory_id(self, factory_id):
        self._factory_id = factory_id

    @property
    def descriptive_name(self) -> str:
        """A descriptive name for this ObservableObject instance."""
        # Note: Sub-classes should override this to add any other relevant info
        # for that object type.
        return "{0} id={1} factory_id={2} is_connected={3}".format(self.__class__.__name__, self.object_id, self._factory_id, self.is_connected)

    @property
    def pose(self) -> util.Pose:
        """The pose of the element in the world.

        Is ``None`` for elements that don't have pose information.
        """
        return self._pose

    @property
    def time_since_last_seen(self) -> float:
        """The time since this element was last seen. math.inf if never seen."""
        if self.last_observed_time is None:
            return math.inf
        return time.time() - self.last_observed_time

    @property
    def is_visible(self) -> bool:
        """True if the element has been observed recently, False otherwise.

        "recently" is defined as :attr:`visibility_timeout` seconds.
        """
        return self._is_visible

    @property
    def object_id(self) -> int:
        """The internal ID assigned to the object.

        This value can only be assigned once as it is static on the robot.
        """
        return self._object_id

    @object_id.setter
    def object_id(self, value):
        if self._object_id is not None:
            # We cannot currently rely on robot ensuring that object ID remains static
            # E.g. in the case of a cube disconnecting and reconnecting it's removed
            # and then re-added to blockworld which results in a new ID.
            self.logger.warning("Changing object_id for %s from %s to %s", self.__class__, self._object_id, value)
        else:
            self.logger.debug("Setting object_id for %s to %s", self.__class__, value)
        self._object_id = value

    #### Private Event Handlers ####
    def _dispatch_observed_event(self, image_rect):
        # @TODO: Figure out events
        self.logger.debug('Object Observed (object_id: {0} at: {1})'.format(self.object_id, image_rect))

    def _dispatch_appeared_event(self, image_rect):
        # @TODO: Figure out events
        self.logger.debug('Object Appeared (object_id: {0} at: {1})'.format(self.object_id, image_rect))

    def _dispatch_disappeared_event(self):
        # @TODO: Figure out events
        self.logger.debug('Object Disappeared (object_id: {0})'.format(self.object_id))

    #### Public Event Handlers ####
    # TODO Should this be private? If not, need docstring
    def on_tapped(self, msg):
        now = time.time()
        self.last_event_time = now
        self.last_tapped_time = now
        self.last_tapped_robot_timestamp = msg.timestamp
        self.logger.debug('Object Tapped (object_id: {0} at {1})'.format(self.object_id, msg.timestamp))

    # TODO Should this be private? If not, need docstring
    def on_moved(self, msg):  # pylint: disable=unused-argument
        now = time.time()
        started_moving = not self.is_moving
        self.is_moving = True
        self.last_event_time = now
        self.last_moved_time = now
        self.last_moved_robot_timestamp = msg.timestamp

        if started_moving:
            self.last_moved_start_time = now
            self.last_moved_start_robot_timestamp = msg.timestamp
            self.logger.debug('Object Moved (object_id: {0})'.format(self.object_id))

    # TODO Should this be private? If not, need docstring
    def on_stopped_moving(self, msg):  # pylint: disable=unused-argument
        now = time.time()
        self.last_event_time = now
        if self.is_moving:
            self.is_moving = False
            move_duration = now - self.last_moved_start_time
        else:
            # This happens for very short movements that are immediately
            # considered stopped (no acceleration info is present)
            move_duration = 0.0
        # @TODO: Figure out events
        self.logger.debug('Object Stopped Moving (object_id: {0} after a duration of {1})'.format(self.object_id, move_duration))

    # TODO Should this be private? If not, need docstring
    def on_up_axis_changed(self, msg):
        now = time.time()
        self.up_axis = msg.up_axis
        self.last_event_time = now
        self.last_up_axis_changed_time = now
        self.last_up_axis_changed_robot_timestamp = msg.timestamp
        # @TODO: Figure out events
        self.logger.debug('Object Up Axis Changed (object_id: {0} now has up axis {1})'.format(self.object_id, msg.up_axis))

    # TODO Should this be private? If not, need docstring
    def on_observed(self, msg):
        self._pose = util.Pose(x=msg.pose.x, y=msg.pose.y, z=msg.pose.z,
                               q0=msg.pose.q0, q1=msg.pose.q1,
                               q2=msg.pose.q2, q3=msg.pose.q3,
                               origin_id=msg.pose.origin_id)
        image_rect = util.ImageRect(msg.img_rect.x_top_left,
                                    msg.img_rect.y_top_left,
                                    msg.img_rect.width,
                                    msg.img_rect.height)
        self._on_observed(image_rect, msg.timestamp)
        self._top_face_orientation_rad = msg.top_face_orientation_rad

    # TODO Should this be private? If not, need docstring
    def on_connection_state_changed(self, connected, factory_id):
        if self._factory_id != factory_id:
            self.logger.debug('Factory id changed from {0} to {1}'.format(self._factory_id, factory_id))
        if self.is_connected != connected:
            if connected:
                self.logger.debug('Object connected: %s', self)
            else:
                self.logger.debug('Object disconnected: %s', self)
            self.is_connected = connected
            # @TODO: Figure out events
            self.logger.debug('Object Connection State Changed (object_id: {0} now has connection state {1})'.format(self.object_id, connected))
