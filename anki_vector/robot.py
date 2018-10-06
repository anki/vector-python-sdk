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
The main robot class for managing Vector.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['MAX_HEAD_ANGLE', 'MIN_HEAD_ANGLE', 'AsyncRobot', 'Robot']

import asyncio
import configparser
import functools
import sys
from pathlib import Path

from . import (animation, audio, behavior, camera,
               connection, events, exceptions, faces, motors,
               screen, photos, proximity, sync, util,
               viewer, world)
from .messaging import protocol

# Constants

#: The minimum angle the robot's head can be set to
MIN_HEAD_ANGLE = util.degrees(-22)

#: The maximum angle the robot's head can be set to
MAX_HEAD_ANGLE = util.degrees(45)


class Robot:
    """The Robot object is responsible for managing the state and connections
    to a Vector, and is typically the entry-point to running the sdk.

    The majority of the robot will not work until it is properly connected
    to Vector. There are two ways to get connected:

    1. Using :code:`with`: it works just like opening a file, and will close when
    the :code:`with` block's indentation ends.

    .. code-block:: python

        # Create the robot connection
        with anki_vector.Robot("my_robot_serial_number") as robot:
            # Run your commands
            robot.play_animation("anim_blackjack_victorwin_01")

    2. Using :func:`connect` and :func:`disconnect` to explicitly open and close the connection:
    it allows the robot's connection to continue in the context in which it started.

    .. code-block:: python

        # Create a Robot object
        robot = Robot("my_robot_serial_number")
        # Connect to the Robot
        robot.connect()
        # Run your commands (for example play animation)
        robot.play_animation("anim_blackjack_victorwin_01")
        # Disconnect from Vector
        robot.disconnect()

    :param serial: Vector's serial number. The robot's serial number (ex. 00e20100) is located on the underside of Vector,
                   or accessible from Vector's debug screen. Used to identify which Vector configuration to load.
    :param ip: Vector's IP Address. (optional)
    :param config: A custom :class:`dict` to override values in Vector's configuration. (optional)
                   Example: :code:`{"cert": "/path/to/file.cert", "name": "Vector-XXXX", "guid": "<secret_key>"}`
                   where :code:`cert` is the certificate to identify Vector, :code:`name` is the name on Vector's face
                   when his backpack is double clicked on the charger, and :code:`guid` is the authorization token
                   that identifies the SDK user. Note: Never share your authentication credentials with anyone.
    :param loop: The async loop on which the Vector commands will execute.
    :param default_logging: Disable default logging.
    :param behavior_activation_timeout: The time to wait for control of the robot before failing.
    :param enable_vision_mode: Turn on face detection.
    :param enable_camera_feed: Turn camera feed on/off.
    :param enable_audio_feed: Turn audio feed on/off.
    :param show_viewer: Render camera feed on/off."""

    def __init__(self,
                 serial: str = None,
                 ip: str = None,
                 config: dict = None,
                 loop: asyncio.BaseEventLoop = None,
                 default_logging: bool = True,
                 behavior_activation_timeout: int = 10,
                 cache_animation_list: bool = True,
                 enable_vision_mode: bool = False,
                 enable_camera_feed: bool = True,
                 enable_audio_feed: bool = False,
                 show_viewer: bool = False):

        if default_logging:
            util.setup_basic_logging()
        self.logger = util.get_class_logger(__name__, self)
        self.is_async = False
        self.is_loop_owner = False
        self._original_loop = None
        self.loop = loop
        config = config if config is not None else {}

        if serial is not None:
            config = {**self._read_configuration(serial), **config}

        self._name = config["name"]
        self._ip = ip if ip is not None else config["ip"]
        self._cert_file = config["cert"]
        self._guid = config["guid"]

        self._port = "443"
        if 'port' in config:
            self._port = config["port"]

        if self._name is None or self._ip is None or self._cert_file is None or self._guid is None:
            raise ValueError("The Robot object requires a serial and for Vector to be logged in (using the app then configure.py).\n"
                             "You may also provide the values necessary for connection through the config parameter. ex: "
                             '{"name":"Vector-XXXX", "ip":"XX.XX.XX.XX", "cert":"/path/to/cert_file", "guid":"<secret_key>"}')

        #: :class:`anki_vector.connection.Connection`: The active connection to the robot.
        self.conn = connection.Connection(self._name, ':'.join([self._ip, self._port]), self._cert_file, self._guid)
        self.events = events.EventHandler()
        # placeholders for components before they exist
        self._anim: animation.AnimationComponent = None
        #self._audio: audio.AudioComponent = None // TODO turn on
        self._behavior: behavior.BehaviorComponent = None
        self._camera: camera.CameraComponent = None
        self._faces: faces.FaceComponent = None
        self._motors: motors.MotorComponent = None
        self._screen: screen.ScreenComponent = None
        self._photos: photos.PhotographComponent = None
        self._proximity: proximity.ProximityComponent = None
        self._viewer: viewer.ViewerComponent = None
        self._world: world.World = None

        self.behavior_activation_timeout = behavior_activation_timeout
        self.enable_vision_mode = enable_vision_mode
        self.cache_animation_list = cache_animation_list
        # Robot state/sensor data
        self._pose: util.Pose = None
        self._pose_angle_rad: float = None
        self._pose_pitch_rad: float = None
        self._left_wheel_speed_mmps: float = None
        self._right_wheel_speed_mmps: float = None
        self._head_angle_rad: float = None
        self._lift_height_mm: float = None
        self._accel: util.Vector3 = None
        self._gyro: util.Vector3 = None
        self._carrying_object_id: float = None
        self._head_tracking_object_id: float = None
        self._localized_to_object_id: float = None
        self._last_image_time_stamp: float = None
        self._status: float = None
        self.pending = []

        self._enable_camera_feed = enable_camera_feed
        self._enable_audio_feed = enable_audio_feed
        self._show_viewer = show_viewer

    @staticmethod
    def _read_configuration(serial: str) -> dict:
        """Open the default conf file, and read it into a :class:`configparser.ConfigParser`

        :param serial: Vector's serial number
        """
        home = Path.home() / ".anki_vector"
        conf_file = str(home / "sdk_config.ini")
        parser = configparser.ConfigParser(strict=False)
        parser.read(conf_file)

        try:
            dict_entry = parser[serial]
        except KeyError:
            raise Exception("Could not find matching robot info for serial. Please check your serial number is correct.")

        return dict_entry

    # TODO sample code
    @property
    def robot(self) -> 'Robot':
        """A reference to the Robot object instance."""
        return self

    @property
    def anim(self) -> animation.AnimationComponent:
        """A reference to the AnimationComponent instance."""
        if self._anim is None:
            raise exceptions.VectorNotReadyException("AnimationComponent is not yet initialized")
        return self._anim

    @property
    def audio(self) -> audio.AudioComponent:
        """:class:`anki_vector.audio.AudioComponent`: The audio instance used to control
        Vector's audio feed
        """
        if self._audio is None:
            raise exceptions.VectorNotReadyException("AudioComponent is not yet initialized")
        return self._audio

    @property
    def behavior(self) -> behavior.BehaviorComponent:
        """A reference to the BehaviorComponent instance."""
        return self._behavior

    @property
    def camera(self) -> camera.CameraComponent:
        """:class:`anki_vector.camera.CameraComponent`: The camera instance used to control
        Vector's camera feed.

        .. code-block:: python

            with anki_vector.Robot("my_robot_serial_number") as robot:
                image = Image.fromarray(robot.camera.latest_image)
                image.show()
        """
        if self._camera is None:
            raise exceptions.VectorNotReadyException("CameraComponent is not yet initialized")
        return self._camera

    # TODO sample code
    @property
    def faces(self) -> faces.FaceComponent:
        """A reference to the FaceComponent instance."""
        if self._faces is None:
            raise exceptions.VectorNotReadyException("FaceComponent is not yet initialized")
        return self._faces

    # TODO sample code
    @property
    def motors(self) -> motors.MotorComponent:
        """A reference to the MotorComponent instance."""
        if self._motors is None:
            raise exceptions.VectorNotReadyException("MotorComponent is not yet initialized")
        return self._motors

    # TODO sample code
    @property
    def screen(self) -> screen.ScreenComponent:
        """A reference to the ScreenComponent instance."""
        if self._screen is None:
            raise exceptions.VectorNotReadyException("ScreenComponent is not yet initialized")
        return self._screen

    # TODO sample code
    @property
    def photos(self) -> photos.PhotographComponent:
        """A reference to the PhotographComponent instance."""
        if self._photos is None:
            raise exceptions.VectorNotReadyException("PhotographyComponent is not yet initialized")
        return self._photos

    @property
    def proximity(self) -> proximity.ProximityComponent:
        """Component containing state related to object proximity detection.

        .. code-block:: python

            proximity_data = robot.proximity.last_valid_sensor_reading
            if proximity_data is not None:
                print(proximity_data.distance)
        """
        return self._proximity

    @property
    def viewer(self) -> viewer.ViewerComponent:
        """:class:`anki_vector.viewer.ViewerComponent`: The viewer instance used to render
        Vector's camera feed.

        .. code-block:: python

            with anki_vector.Robot("my_robot_serial_number") as robot:
                # Render video for 10 seconds
                robot.viewer.show_video()
                robot.loop.run_until_complete(utilities.delay_close(10))

                # Disable video render and camera feed for 5 seconds
                robot.viewer.stop_video()
        """
        if self._viewer is None:
            raise exceptions.VectorNotReadyException("ViewerComponent is not yet initialized")
        return self._viewer

    @property
    def world(self) -> world.World:
        """A reference to the World instance, or None if the WorldComponent is not yet initialized."""
        if self._world is None:
            raise exceptions.VectorNotReadyException("WorldComponent is not yet initialized")
        return self._world

    @property
    def pose(self) -> util.Pose:
        """:class:`anki_vector.util.Pose`: The current pose (position and orientation) of Vector.

        .. code-block:: python

            current_robot_pose = robot.pose
        """
        return self._pose

    @property
    def pose_angle_rad(self) -> float:
        """Vector's pose angle (heading in X-Y plane).

        .. code-block:: python

            current_pose_angle_rad = robot.pose_angle_rad
        """
        return self._pose_angle_rad

    @property
    def pose_pitch_rad(self) -> float:
        """Vector's pose pitch (angle up/down).

        .. code-block:: python

            current_pose_pitch_rad = robot.pose_pitch_rad
        """
        return self._pose_pitch_rad

    @property
    def left_wheel_speed_mmps(self) -> float:
        """Vector's left wheel speed in mm/sec

        .. code-block:: python

            current_left_wheel_speed_mmps = robot.left_wheel_speed_mmps
        """
        return self._left_wheel_speed_mmps

    @property
    def right_wheel_speed_mmps(self) -> float:
        """Vector's right wheel speed in mm/sec

        .. code-block:: python

            current_right_wheel_speed_mmps = robot.right_wheel_speed_mmps
        """
        return self._right_wheel_speed_mmps

    @property
    def head_angle_rad(self) -> float:
        """Vector's head angle (up/down).

        .. code-block:: python

            current_head_angle_rad = robot.head_angle_rad
        """
        return self._head_angle_rad

    @property
    def lift_height_mm(self) -> float:
        """Height of Vector's lift from the ground.

        .. code-block:: python

            current_lift_height_mm = robot.lift_height_mm
        """
        return self._lift_height_mm

    @property
    def accel(self) -> util.Vector3:
        """:class:`anki_vector.util.Vector3`: The current accelerometer reading (x, y, z)

        .. code-block:: python

            current_accel = robot.accel
        """
        return self._accel

    @property
    def gyro(self) -> util.Vector3:
        """The current gyroscope reading (x, y, z)

        .. code-block:: python

            current_gyro = robot.gyro
        """
        return self._gyro

    @property
    def carrying_object_id(self) -> int:
        """The ID of the object currently being carried (-1 if none)

        .. code-block:: python

            current_carrying_object_id = robot.carrying_object_id
        """
        return self._carrying_object_id

    @property
    def head_tracking_object_id(self) -> int:
        """The ID of the object the head is tracking to (-1 if none)

        .. code-block:: python

            current_head_tracking_object_id = robot.head_tracking_object_id
        """
        return self._head_tracking_object_id

    @property
    def localized_to_object_id(self) -> int:
        """The ID of the object that the robot is localized to (-1 if none)

        .. code-block:: python

            current_localized_to_object_id = robot.localized_to_object_id
        """
        return self._localized_to_object_id

    # TODO Move to photos or somewhere else
    @property
    def last_image_time_stamp(self) -> int:
        """The robot's timestamp for the last image seen.

        .. code-block:: python

            current_last_image_time_stamp = robot.last_image_time_stamp
        """
        return self._last_image_time_stamp

    @property
    def status(self) -> float:
        """Describes Vector's status.

           Possible values include:
           NoneRobotStatusFlag     = 0
           IS_MOVING               = 0x1
           IS_CARRYING_BLOCK       = 0x2
           IS_PICKING_OR_PLACING   = 0x4
           IS_PICKED_UP            = 0x8
           IS_BUTTON_PRESSED       = 0x10
           IS_FALLING              = 0x20
           IS_ANIMATING            = 0x40
           IS_PATHING              = 0x80
           LIFT_IN_POS             = 0x100
           HEAD_IN_POS             = 0x200
           CALM_POWER_MODE         = 0x400
           IS_BATTERY_DISCONNECTED = 0x800
           IS_ON_CHARGER           = 0x1000
           IS_CHARGING             = 0x2000
           CLIFF_DETECTED          = 0x4000
           ARE_WHEELS_MOVING       = 0x8000
           IS_BEING_HELD           = 0x10000
           IS_MOTION_DETECTED      = 0x20000
           IS_BATTERY_OVERHEATED   = 0x40000

        .. code-block:: python

            current_status = robot.status
        """
        return self._status

    @property
    def enable_audio_feed(self) -> bool:
        """The audio feed enabled/disabled

        :getter: Returns whether the audio feed is enabled
        :setter: Enable/disable the audio feeed

        .. code-block:: python

            with anki_vector.Robot("my_robot_serial_number", enable_audio_feed=True) as robot:
                robot.loop.run_until_complete(utilities.delay_close(5))
                robot.enable_audio_feed = False
                robot.loop.run_until_complete(utilities.delay_close(5))
        """
        return self._enable_audio_feed

    @enable_audio_feed.setter
    def enable_audio_feed(self, enable) -> None:
        self._enable_audio_feed = enable
        if self.enable_audio_feed:
            self.audio.init_audio_feed()

    @property
    def enable_camera_feed(self) -> bool:
        """The camera feed enabled/disabled

        :getter: Returns whether the camera feed is enabled
        :setter: Enable/disable the camera feeed

        .. code-block:: python

            with anki_vector.Robot("my_robot_serial_number", enable_camera_feed=True) as robot:
                robot.loop.run_until_complete(utilities.delay_close(5))
                robot.enable_camera_feed = False
                robot.loop.run_until_complete(utilities.delay_close(5))
        """
        return self._enable_camera_feed

    @enable_camera_feed.setter
    def enable_camera_feed(self, enable) -> None:
        self._enable_camera_feed = enable
        if self.enable_camera_feed:
            self.camera.init_camera_feed()

    # Unpack streamed data to robot's internal properties
    def _unpack_robot_state(self, _, msg):
        self._pose = util.Pose(x=msg.pose.x, y=msg.pose.y, z=msg.pose.z,
                               q0=msg.pose.q0, q1=msg.pose.q1,
                               q2=msg.pose.q2, q3=msg.pose.q3,
                               origin_id=msg.pose.origin_id)
        self._pose_angle_rad = msg.pose_angle_rad
        self._pose_pitch_rad = msg.pose_pitch_rad
        self._left_wheel_speed_mmps = msg.left_wheel_speed_mmps
        self._right_wheel_speed_mmps = msg.right_wheel_speed_mmps
        self._head_angle_rad = msg.head_angle_rad
        self._lift_height_mm = msg.lift_height_mm
        self._accel = util.Vector3(msg.accel.x, msg.accel.y, msg.accel.z)
        self._gyro = util.Vector3(msg.gyro.x, msg.gyro.y, msg.gyro.z)
        self._carrying_object_id = msg.carrying_object_id
        self._head_tracking_object_id = msg.head_tracking_object_id
        self._localized_to_object_id = msg.localized_to_object_id
        self._last_image_time_stamp = msg.last_image_time_stamp
        self._status = msg.status
        self._proximity.on_proximity_update(msg.prox_data)

    def connect(self, timeout: int = 10) -> None:
        """Start the connection to Vector.

        .. code-block:: python

            robot = Robot("my_robot_serial_number")
            robot.connect()
            robot.play_animation("anim_blackjack_victorwin_01")
            robot.disconnect()

        :param timeout: The time to allow for a connection before a
            :class:`anki_vector.exceptions.VectorTimeoutException` is raised.
        """
        if self.loop is None:
            self.logger.debug("Creating asyncio loop")
            self.is_loop_owner = True
            self._original_loop = asyncio.get_event_loop()
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

        self.conn.connect(self.loop, timeout=timeout)
        self.events.start(self.conn, self.loop)

        # Initialize components
        self._anim = animation.AnimationComponent(self)
        self._audio = audio.AudioComponent(self)
        self._behavior = behavior.BehaviorComponent(self)
        self._camera = camera.CameraComponent(self)
        self._faces = faces.FaceComponent(self)
        self._motors = motors.MotorComponent(self)
        self._screen = screen.ScreenComponent(self)
        self._photos = photos.PhotographComponent(self)
        self._proximity = proximity.ProximityComponent(self)
        self._viewer = viewer.ViewerComponent(self)
        self._world = world.World(self)

        if self.cache_animation_list:
            # Load animations so they are ready to play when requested
            anim_request = self._anim.load_animation_list()
            if isinstance(anim_request, sync.Synchronizer):
                anim_request.wait_for_completed()

        # Start audio feed
        if self.enable_audio_feed:
            self.audio.init_audio_feed()

        # Start camera feed
        if self.enable_camera_feed:
            self.camera.init_camera_feed()

        # Start rendering camera feed
        if self._show_viewer:
            self.viewer.show_video()

        # Enable face detection, to allow Vector to add faces to its world view
        self._faces.enable_vision_mode(enable=self.enable_vision_mode)

        # Subscribe to a callback that updates the robot's local properties
        # See Robot properties including robot.pose, robot.accel and robot.gyro to access data from robot_state.
        self.events.subscribe("robot_state", self._unpack_robot_state)

    def disconnect(self) -> None:
        """Close the connection with Vector.

        .. code-block:: python

            robot = Robot("my_robot_serial_number")
            robot.connect()
            robot.play_animation("anim_blackjack_victorwin_01")
            robot.disconnect()
        """
        if self.is_async:
            for task in self.pending:
                task.wait_for_completed()

        vision_mode = self._faces.enable_vision_mode(enable=False)
        if isinstance(vision_mode, sync.Synchronizer):
            vision_mode.wait_for_completed()

        # Stop rendering video
        self.viewer.stop_video()
        # Shutdown camera feed
        self.camera.close_camera_feed()
        # Shutdown audio feed
        self.audio.close_audio_feed()

        self.events.close()
        self.conn.close()
        if self.is_loop_owner:
            try:
                self.loop.close()
            finally:
                self.loop = None
                if self._original_loop is not None:
                    asyncio.set_event_loop(self._original_loop)

    def __enter__(self):
        self.connect(self.behavior_activation_timeout)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    @sync.Synchronizer.wrap
    async def get_battery_state(self) -> protocol.BatteryStateResponse:
        """Check the current state of the battery.

        .. code-block:: python

            battery_state = robot.get_battery_state()
            if battery_state:
                print("Vector's Battery Voltage: {0}".format(battery_state.battery_volts))
        """
        get_battery_state_request = protocol.BatteryStateRequest()
        return await self.conn.grpc_interface.BatteryState(get_battery_state_request)

    @sync.Synchronizer.wrap
    async def get_version_state(self) -> protocol.VersionStateResponse:
        """Get the versioning information for Vector.

        .. code-block:: python

            version_state = robot.get_version_state()
        """
        get_version_state_request = protocol.VersionStateRequest()
        return await self.conn.grpc_interface.VersionState(get_version_state_request)

    @sync.Synchronizer.wrap
    async def get_network_state(self) -> protocol.NetworkStateResponse:
        """Get the network information for Vector.

        .. code-block:: python

            network_state = robot.get_version_state()
        """
        get_network_state_request = protocol.NetworkStateRequest()
        return await self.conn.grpc_interface.NetworkState(get_network_state_request)

    @sync.Synchronizer.wrap
    async def say_text(self, text: str, use_vector_voice: bool = True, duration_scalar: float = 1.0) -> protocol.SayTextResponse:
        """Make Vector speak text.

        .. code-block:: python

            robot.say_text("Hello World")

        :param text: The words for Vector to say.
        :param use_vector_voice: Whether to use Vector's robot voice
                (otherwise, he uses a generic human male voice).
        :param duration_scalar: Adjust the relative duration of the
                generated text to speech audio.

        :return: object that provides the status and utterance state
        """
        say_text_request = protocol.SayTextRequest(text=text,
                                                   use_vector_voice=use_vector_voice,
                                                   duration_scalar=duration_scalar)
        return await self.conn.grpc_interface.SayText(say_text_request)


class AsyncRobot(Robot):
    """The AsyncRobot object is just like the Robot object, but allows multiple commands
    to be executed at the same time. To achieve this, all function calls also
    return a :class:`sync.Synchronizer`.

    1. Using :code:`with`: it works just like opening a file, and will close when
    the :code:`with` block's indentation ends.

    .. code-block:: python

        # Create the robot connection
        with AsyncRobot("my_robot_serial_number") as robot:
            # Run your commands
            robot.play_animation("anim_blackjack_victorwin_01").wait_for_completed()

    2. Using :func:`connect` and :func:`disconnect` to explicitly open and close the connection:
    it allows the robot's connection to continue in the context in which it started.

    .. code-block:: python

        # Create a Robot object
        robot = AsyncRobot("my_robot_serial_number")
        # Connect to Vector
        robot.connect()
        # Run your commands
        robot.play_animation("anim_blackjack_victorwin_01").wait_for_completed()
        # Disconnect from Vector
        robot.disconnect()

    :param serial: Vector's serial number. Used to identify which Vector configuration to load.
    :param ip: Vector's IP Address. (optional)
    :param config: A custom :class:`dict` to override values in Vector's configuration. (optional)
                   Example: :code:`{"cert": "/path/to/file.cert", "name": "Vector-XXXX", "guid": "<secret_key>"}`
                   where :code:`cert` is the certificate to identify Vector, :code:`name` is the name on Vector's face
                   when his backpack is double clicked on the charger, and :code:`guid` is the authorization token
                   that identifies the SDK user. Note: Never share your authentication credentials with anyone.
    :param loop: The async loop on which the Vector commands will execute.
    :param default_logging: Disable default logging.
    :param behavior_activation_timeout: The time to wait for control of the robot before failing.
    :param enable_vision_mode: Turn on face detection.
    :param enable_camera_feed: Turn camera feed on/off.
    :param enable_audio_feed: Turn audio feed on/off.
    :param show_viewer: Render camera feed on/off."""

    @functools.wraps(Robot.__init__)
    def __init__(self, *args, **kwargs):
        super(AsyncRobot, self).__init__(*args, **kwargs)
        self.is_async = True

    # TODO Should be private? Better method name? If not private, Add docstring and sample code
    def add_pending(self, task):
        self.pending += [task]

    # TODO Should be private? Better method name? If not private, Add docstring and sample code
    def remove_pending(self, task):
        self.pending = [x for x in self.pending if x is not task]
