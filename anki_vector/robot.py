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
The main robot class for managing Vector.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['AsyncRobot', 'Robot']

import concurrent
import configparser
import functools
from pathlib import Path

from . import (animation, audio, behavior, camera,
               connection, events, exceptions, faces,
               motors, nav_map, screen, photos, proximity,
               status, touch, util, viewer, vision, world)
from .viewer import (ViewerComponent, Viewer3DComponent)
from .messaging import protocol


class Robot:
    """The Robot object is responsible for managing the state and connections
    to a Vector, and is typically the entry-point to running the sdk.

    The majority of the robot will not work until it is properly connected
    to Vector. There are two ways to get connected:

    1. Using :code:`with`: it works just like opening a file, and will close when
    the :code:`with` block's indentation ends.


    .. testcode::

        import anki_vector

        # Create the robot connection
        with anki_vector.Robot() as robot:
            # Run your commands
            robot.anim.play_animation("anim_turn_left_01")

    2. Using :func:`connect` and :func:`disconnect` to explicitly open and close the connection:
    it allows the robot's connection to continue in the context in which it started.

    .. testcode::

        import anki_vector

        # Create a Robot object
        robot = anki_vector.Robot()
        # Connect to the Robot
        robot.connect()
        # Run your commands
        robot.anim.play_animation("anim_turn_left_01")
        # Disconnect from Vector
        robot.disconnect()

    :param serial: Vector's serial number. The robot's serial number (ex. 00e20100) is located on the underside of Vector,
                   or accessible from Vector's debug screen. Used to identify which Vector configuration to load.
    :param ip: Vector's IP address. (optional)
    :param config: A custom :class:`dict` to override values in Vector's configuration. (optional)
                   Example: :code:`{"cert": "/path/to/file.cert", "name": "Vector-XXXX", "guid": "<secret_key>"}`
                   where :code:`cert` is the certificate to identify Vector, :code:`name` is the name on Vector's face
                   when his backpack is double-clicked on the charger, and :code:`guid` is the authorization token
                   that identifies the SDK user. Note: Never share your authentication credentials with anyone.
    :param default_logging: Toggle default logging.
    :param behavior_activation_timeout: The time to wait for control of the robot before failing.
    :param cache_animation_list: Get the list of animations available at startup.
    :param enable_face_detection: Turn on face detection.
    :param enable_camera_feed: Turn camera feed on/off.
    :param enable_audio_feed: Turn audio feed on/off.
    :param enable_custom_object_detection: Turn custom object detection on/off.
    :param enable_nav_map_feed: Turn navigation map feed on/off.
    :param show_viewer: Render camera feed on/off.
    :param show_3d_viewer: Render camera feed on/off.
    :param requires_behavior_control: Request control of Vector's behavior system."""

    def __init__(self,
                 serial: str = None,
                 ip: str = None,
                 config: dict = None,
                 default_logging: bool = True,
                 behavior_activation_timeout: int = 10,
                 cache_animation_list: bool = True,
                 enable_face_detection: bool = False,
                 enable_camera_feed: bool = False,
                 enable_audio_feed: bool = False,
                 enable_custom_object_detection: bool = False,
                 enable_nav_map_feed: bool = None,
                 show_viewer: bool = False,
                 show_3d_viewer: bool = False,
                 requires_behavior_control: bool = True):
        if default_logging:
            util.setup_basic_logging()
        self.logger = util.get_class_logger(__name__, self)
        self._force_async = False
        config = config if config is not None else {}
        config = {**self._read_configuration(serial), **config}

        self._name = config["name"]
        self._ip = ip if ip is not None else config["ip"]
        self._cert_file = config["cert"]
        self._guid = config["guid"]

        self._port = "443"
        if 'port' in config:
            self._port = config["port"]

        if self._name is None or self._ip is None or self._cert_file is None or self._guid is None:
            raise ValueError("The Robot object requires a serial and for Vector to be logged in (using the app then running the anki_vector.configure executable submodule).\n"
                             "You may also provide the values necessary for connection through the config parameter. ex: "
                             '{"name":"Vector-XXXX", "ip":"XX.XX.XX.XX", "cert":"/path/to/cert_file", "guid":"<secret_key>"}')

        #: :class:`anki_vector.connection.Connection`: The active connection to the robot.
        self._conn = connection.Connection(self._name, ':'.join([self._ip, self._port]), self._cert_file, self._guid, requires_behavior_control=requires_behavior_control)
        self._events = events.EventHandler()

        # placeholders for components before they exist
        self._anim: animation.AnimationComponent = None
        self._audio: audio.AudioComponent = None
        self._behavior: behavior.BehaviorComponent = None
        self._camera: camera.CameraComponent = None
        self._faces: faces.FaceComponent = None
        self._motors: motors.MotorComponent = None
        self._nav_map: nav_map.NavMapComponent = None
        self._screen: screen.ScreenComponent = None
        self._photos: photos.PhotographComponent = None
        self._proximity: proximity.ProximityComponent = None
        self._touch: touch.TouchComponent = None
        self._viewer: viewer.ViewerComponent = None
        self._viewer_3d: viewer.Viewer3DComponent = None
        self._vision: vision.VisionComponent = None
        self._world: world.World = None

        self.behavior_activation_timeout = behavior_activation_timeout
        self.enable_face_detection = enable_face_detection
        self.enable_custom_object_detection = enable_custom_object_detection
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
        self._status: status.RobotStatus = status.RobotStatus()
        self.pending = []

        self._enable_camera_feed = enable_camera_feed
        self._enable_audio_feed = enable_audio_feed
        if enable_nav_map_feed is not None:
            self._enable_nav_map_feed = enable_nav_map_feed
        else:
            self._enable_nav_map_feed = False
        self._show_viewer = show_viewer
        if show_viewer and not enable_camera_feed:
            self.logger.warning("enable_camera_feed should be True for viewer to render correctly.")
            self._enable_camera_feed = True
        self._show_3d_viewer = show_3d_viewer
        if show_3d_viewer and enable_nav_map_feed is None:
            self.logger.warning("enable_nav_map_feed should be True for 3d viewer to render correctly.")
            self._enable_nav_map_feed = True

    def _read_configuration(self, serial: str) -> dict:
        """Open the default conf file, and read it into a :class:`configparser.ConfigParser`

        :param serial: Vector's serial number
        """
        home = Path.home() / ".anki_vector"
        conf_file = str(home / "sdk_config.ini")
        parser = configparser.ConfigParser(strict=False)
        parser.read(conf_file)

        sections = parser.sections()
        if not sections:
            raise Exception('\n\nCould not find the sdk configuration file. Please run `python3 -m anki_vector.configure` to set up your Vector for SDK usage.')
        elif serial is None and len(sections) == 1:
            serial = sections[0]
            self.logger.warning("No serial number provided. Automatically selecting {}".format(serial))
        elif serial is None:
            raise Exception('\n\nFound multiple robot serial numbers. Please provide the serial number of the Robot you want to control.\n'
                            'Example: ./01_hello_world.py --serial {robot_serial_number}')

        serial = serial.lower()
        config = {k.lower(): v for k, v in parser.items()}
        try:
            dict_entry = config[serial]
        except KeyError:
            raise Exception('\n\nCould not find matching robot info for given serial number: {}. Please check your serial number is correct.\n'
                            'Example: ./01_hello_world.py --serial {{robot_serial_number}}'.format(serial))

        return dict_entry

    @property
    def force_async(self) -> bool:
        """A reference to the Robot object instance."""
        return self._force_async

    @property
    def conn(self) -> connection.Connection:
        """A reference to the Connection instance."""
        return self._conn

    @property
    def events(self) -> events.EventHandler:
        """A reference to the EventHandler instance."""
        return self._events

    @property
    def anim(self) -> animation.AnimationComponent:
        """A reference to the AnimationComponent instance."""
        if self._anim is None:
            raise exceptions.VectorNotReadyException("AnimationComponent is not yet initialized")
        return self._anim

    @property
    def audio(self) -> audio.AudioComponent:
        """The audio instance used to control Vector's audio feed."""

        print("\n\nNote: Audio stream is not yet supported and does not yet come from Vector's microphones.\n\n")

        if self._audio is None:
            raise exceptions.VectorNotReadyException("AudioComponent is not yet initialized")
        return self._audio

    @property
    def behavior(self) -> behavior.BehaviorComponent:
        """A reference to the BehaviorComponent instance."""
        return self._behavior

    @property
    def camera(self) -> camera.CameraComponent:
        """The camera instance used to control Vector's camera feed.

        .. testcode::

            import anki_vector

            with anki_vector.Robot(enable_camera_feed=True) as robot:
                image = robot.camera.latest_image
                image.show()
        """
        if self._camera is None:
            raise exceptions.VectorNotReadyException("CameraComponent is not yet initialized")
        return self._camera

    @property
    def faces(self) -> faces.FaceComponent:
        """A reference to the FaceComponent instance."""
        if self._faces is None:
            raise exceptions.VectorNotReadyException("FaceComponent is not yet initialized")
        return self._faces

    @property
    def motors(self) -> motors.MotorComponent:
        """A reference to the MotorComponent instance."""
        if self._motors is None:
            raise exceptions.VectorNotReadyException("MotorComponent is not yet initialized")
        return self._motors

    @property
    def nav_map(self) -> nav_map.NavMapComponent:
        """A reference to the NavMapComponent instance."""
        if self._nav_map is None:
            raise exceptions.VectorNotReadyException("NavMapComponent is not yet initialized")
        return self._nav_map

    @property
    def screen(self) -> screen.ScreenComponent:
        """A reference to the ScreenComponent instance."""
        if self._screen is None:
            raise exceptions.VectorNotReadyException("ScreenComponent is not yet initialized")
        return self._screen

    @property
    def photos(self) -> photos.PhotographComponent:
        """A reference to the PhotographComponent instance."""
        if self._photos is None:
            raise exceptions.VectorNotReadyException("PhotographyComponent is not yet initialized")
        return self._photos

    @property
    def proximity(self) -> proximity.ProximityComponent:
        """Component containing state related to object proximity detection.

        ..code-block ::

            import anki_vector
            with anki_vector.Robot() as robot:
                proximity_data = robot.proximity.last_valid_sensor_reading
                if proximity_data is not None:
                    print(proximity_data.distance)
        """
        return self._proximity

    @property
    def touch(self) -> touch.TouchComponent:
        """Component containing state related to object touch detection.

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                print('Robot is being touched: {0}'.format(robot.touch.last_sensor_reading.is_being_touched))
        """
        return self._touch

    @property
    def viewer(self) -> ViewerComponent:
        """The viewer instance used to render Vector's camera feed.

        .. testcode::

            import time

            import anki_vector

            with anki_vector.Robot(show_viewer=True) as robot:
                # Render video for 5 seconds
                robot.viewer.show_video()
                time.sleep(5)

                # Disable video render and camera feed for 5 seconds
                robot.viewer.stop_video()
        """
        if self._viewer is None:
            raise exceptions.VectorNotReadyException("ViewerComponent is not yet initialized")
        return self._viewer

    @property
    def viewer_3d(self) -> Viewer3DComponent:
        """The 3D viewer instance used to render Vector's navigation map.

        .. testcode::

            import time

            import anki_vector

            with anki_vector.Robot(show_3d_viewer=True, enable_nav_map_feed=True) as robot:
                # Render 3D view of navigation map for 5 seconds
                time.sleep(5)
        """
        if self._viewer_3d is None:
            raise exceptions.VectorNotReadyException("Viewer3DComponent is not yet initialized")
        return self._viewer_3d

    @property
    def vision(self) -> vision.VisionComponent:
        """Component containing functionality related to vision based object detection.

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                robot.vision.enable_custom_object_detection()
        """
        return self._vision

    @property
    def world(self) -> world.World:
        """A reference to the World instance, or None if the WorldComponent is not yet initialized."""
        if self._world is None:
            raise exceptions.VectorNotReadyException("WorldComponent is not yet initialized")
        return self._world

    @property
    @util.block_while_none()
    def pose(self) -> util.Pose:
        """:class:`anki_vector.util.Pose`: The current pose (position and orientation) of Vector.

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                current_robot_pose = robot.pose
        """
        return self._pose

    @property
    @util.block_while_none()
    def pose_angle_rad(self) -> float:
        """Vector's pose angle (heading in X-Y plane).

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                current_pose_angle_rad = robot.pose_angle_rad
        """
        return self._pose_angle_rad

    @property
    @util.block_while_none()
    def pose_pitch_rad(self) -> float:
        """Vector's pose pitch (angle up/down).

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                current_pose_pitch_rad = robot.pose_pitch_rad
        """
        return self._pose_pitch_rad

    @property
    @util.block_while_none()
    def left_wheel_speed_mmps(self) -> float:
        """Vector's left wheel speed in mm/sec

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                current_left_wheel_speed_mmps = robot.left_wheel_speed_mmps
        """
        return self._left_wheel_speed_mmps

    @property
    @util.block_while_none()
    def right_wheel_speed_mmps(self) -> float:
        """Vector's right wheel speed in mm/sec

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                current_right_wheel_speed_mmps = robot.right_wheel_speed_mmps
        """
        return self._right_wheel_speed_mmps

    @property
    @util.block_while_none()
    def head_angle_rad(self) -> float:
        """Vector's head angle (up/down).

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                current_head_angle_rad = robot.head_angle_rad
        """
        return self._head_angle_rad

    @property
    @util.block_while_none()
    def lift_height_mm(self) -> float:
        """Height of Vector's lift from the ground.

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                current_lift_height_mm = robot.lift_height_mm
        """
        return self._lift_height_mm

    @property
    @util.block_while_none()
    def accel(self) -> util.Vector3:
        """:class:`anki_vector.util.Vector3`: The current accelerometer reading (x, y, z)

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                current_accel = robot.accel
        """
        return self._accel

    @property
    @util.block_while_none()
    def gyro(self) -> util.Vector3:
        """The current gyroscope reading (x, y, z)

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                current_gyro = robot.gyro
        """
        return self._gyro

    @property
    @util.block_while_none()
    def carrying_object_id(self) -> int:
        """The ID of the object currently being carried (-1 if none)

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                current_carrying_object_id = robot.carrying_object_id
        """
        return self._carrying_object_id

    @property
    @util.block_while_none()
    def head_tracking_object_id(self) -> int:
        """The ID of the object the head is tracking to (-1 if none)

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                current_head_tracking_object_id = robot.head_tracking_object_id
        """
        return self._head_tracking_object_id

    @property
    @util.block_while_none()
    def localized_to_object_id(self) -> int:
        """The ID of the object that the robot is localized to (-1 if none)

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                current_localized_to_object_id = robot.localized_to_object_id
        """
        return self._localized_to_object_id

    # TODO Move to photos or somewhere else
    @property
    @util.block_while_none()
    def last_image_time_stamp(self) -> int:
        """The robot's timestamp for the last image seen.

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                current_last_image_time_stamp = robot.last_image_time_stamp
        """
        return self._last_image_time_stamp

    @property
    def status(self) -> status.RobotStatus:
        """A property that exposes various status properties of the robot.

        This status provides a simple mechanism to, for example, detect if any
        of Vector's motors are moving, determine if Vector is being held, or if
        he is on the charger.  The full list is available in the
        :class:`RobotStatus <anki_vector.status.RobotStatus>` class documentation.

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                if robot.status.is_being_held:
                    print("Vector is being held!")
                else:
                    print("Vector is not being held.")
        """
        return self._status

    @property
    def enable_audio_feed(self) -> bool:
        """The audio feed enabled/disabled

        :getter: Returns whether the audio feed is enabled
        :setter: Enable/disable the audio feed

        .. code-block:: python

            import asyncio
            import time

            import anki_vector

            with anki_vector.Robot(enable_audio_feed=True) as robot:
                time.sleep(5)
                robot.enable_audio_feed = False
                time.sleep(5)
        """
        # TODO When audio is ready, convert `.. code-block:: python` to `.. testcode::`
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
        :setter: Enable/disable the camera feed

        .. testcode::

            import asyncio
            import time

            import anki_vector

            with anki_vector.Robot(enable_camera_feed=True) as robot:
                time.sleep(5)
                robot.enable_camera_feed = False
                time.sleep(5)
        """
        return self._enable_camera_feed

    @enable_camera_feed.setter
    def enable_camera_feed(self, enable) -> None:
        self._enable_camera_feed = enable
        if self.enable_camera_feed:
            self.camera.init_camera_feed()
        else:
            self.camera.close_camera_feed()

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
        self._status.set(msg.status)

    def connect(self, timeout: int = 10) -> None:
        """Start the connection to Vector.

        .. testcode::

            import anki_vector

            robot = anki_vector.Robot()
            robot.connect()
            robot.anim.play_animation("anim_turn_left_01")
            robot.disconnect()

        :param timeout: The time to allow for a connection before a
            :class:`anki_vector.exceptions.VectorTimeoutException` is raised.
        """
        self.conn.connect(timeout=timeout)
        self.events.start(self.conn)

        # Initialize components
        self._anim = animation.AnimationComponent(self)
        # self._audio = audio.AudioComponent(self) # TODO turn on
        self._behavior = behavior.BehaviorComponent(self)
        self._camera = camera.CameraComponent(self)
        self._faces = faces.FaceComponent(self)
        self._motors = motors.MotorComponent(self)
        self._nav_map = nav_map.NavMapComponent(self)
        self._screen = screen.ScreenComponent(self)
        self._photos = photos.PhotographComponent(self)
        self._proximity = proximity.ProximityComponent(self)
        self._touch = touch.TouchComponent(self)
        self._viewer = viewer.ViewerComponent(self)
        self._viewer_3d = viewer.Viewer3DComponent(self)
        self._vision = vision.VisionComponent(self)
        self._world = world.World(self)

        if self.cache_animation_list:
            # Load animations so they are ready to play when requested
            anim_request = self._anim.load_animation_list()
            if isinstance(anim_request, concurrent.futures.Future):
                anim_request.result()

        # Start audio feed
        if self.enable_audio_feed:
            self.audio.init_audio_feed()

        # Start camera feed
        if self.enable_camera_feed:
            self.camera.init_camera_feed()

        # Start rendering camera feed
        if self._show_viewer:
            self.viewer.show_video()

        if self._show_3d_viewer:
            self.viewer_3d.show()

        if self._enable_nav_map_feed:
            self.nav_map.init_nav_map_feed()

        # Enable face detection, to allow Vector to add faces to its world view
        if self.conn.requires_behavior_control:
            face_detection = self.vision.enable_face_detection(detect_faces=self.enable_face_detection, estimate_expression=False)
            if isinstance(face_detection, concurrent.futures.Future):
                face_detection.result()
            object_detection = self.vision.enable_custom_object_detection(detect_custom_objects=self.enable_custom_object_detection)
            if isinstance(object_detection, concurrent.futures.Future):
                object_detection.result()

        # Subscribe to a callback that updates the robot's local properties
        self.events.subscribe(self._unpack_robot_state,
                              events.Events.robot_state,
                              on_connection_thread=True)

        # access the pose to prove it has gotten back from the event stream once.
        while not self.pose:
            pass

    def disconnect(self) -> None:
        """Close the connection with Vector.

        .. testcode::

            import anki_vector
            robot = anki_vector.Robot()
            robot.connect()
            robot.anim.play_animation("anim_turn_left_01")
            robot.disconnect()
        """
        if self.conn.requires_behavior_control:
            self.vision.close()

        # Stop rendering video
        self.viewer.stop_video()
        # Stop rendering 3d video
        self.viewer_3d.close()
        # Shutdown camera feed
        self.camera.close_camera_feed()
        self._enable_camera_feed = False
        # Shutdown audio feed
        if self._audio is not None:
            self._audio.close_audio_feed()
        # Shutdown nav map feed
        self.nav_map.close_nav_map_feed()
        # Close the world and cleanup its objects
        self.world.close()

        self.proximity.close()
        self.touch.close()

        self.events.close()
        self.conn.close()

    def __enter__(self):
        self.connect(self.behavior_activation_timeout)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    @connection.on_connection_thread(requires_control=False)
    async def get_battery_state(self) -> protocol.BatteryStateResponse:
        """Check the current state of the robot and cube batteries.

        Vector is considered fully-charged above 4.1 volts. At 3.6V, the robot is approaching low charge.

        Battery_level values are as follows:
         |  Low = 1: 3.6V or less. If on charger, 4V or less.
         |  Nominal = 2
         |  Full = 3: This state can only be achieved when Vector is on the charger.

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                battery_state = robot.get_battery_state()
                if battery_state:
                    print("Robot battery voltage: {0}".format(battery_state.battery_volts))
                    print("Robot battery Level: {0}".format(battery_state.battery_level))
                    print("Robot battery is charging: {0}".format(battery_state.is_charging))
                    print("Robot is on charger platform: {0}".format(battery_state.is_on_charger_platform))
                    print("Robot's suggested charger time: {0}".format(battery_state.suggested_charger_sec))
        """
        get_battery_state_request = protocol.BatteryStateRequest()
        return await self.conn.grpc_interface.BatteryState(get_battery_state_request)

    @connection.on_connection_thread(requires_control=False)
    async def get_version_state(self) -> protocol.VersionStateResponse:
        """Get the versioning information for Vector, including Vector's os_version and engine_build_id.

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                version_state = robot.get_version_state()
        """
        get_version_state_request = protocol.VersionStateRequest()
        return await self.conn.grpc_interface.VersionState(get_version_state_request)

    @connection.on_connection_thread(requires_control=False)
    async def get_network_state(self) -> protocol.NetworkStateResponse:
        """Get the network information for Vector.

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                network_state = robot.get_network_state()
        """
        get_network_state_request = protocol.NetworkStateRequest()
        return await self.conn.grpc_interface.NetworkState(get_network_state_request)

    @connection.on_connection_thread()
    async def say_text(self, text: str, use_vector_voice: bool = True, duration_scalar: float = 1.0) -> protocol.SayTextResponse:
        """Make Vector speak text.

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
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
    to be executed at the same time. To achieve this, all grpc function calls also
    return a :class:`concurrent.futures.Future`.

    1. Using :code:`with`: it works just like opening a file, and will close when
    the :code:`with` block's indentation ends.

    .. testcode::

        import anki_vector
        # Create the robot connection
        with anki_vector.AsyncRobot() as robot:
            # Run your commands
            robot.anim.play_animation("anim_turn_left_01").result()

    2. Using :func:`connect` and :func:`disconnect` to explicitly open and close the connection:
    it allows the robot's connection to continue in the context in which it started.

    .. testcode::

        import anki_vector
        # Create a Robot object
        robot = anki_vector.AsyncRobot()
        # Connect to Vector
        robot.connect()
        # Run your commands
        robot.anim.play_animation("anim_turn_left_01").result()
        # Disconnect from Vector
        robot.disconnect()

    :param serial: Vector's serial number. Used to identify which Vector configuration to load.
    :param ip: Vector's IP Address. (optional)
    :param config: A custom :class:`dict` to override values in Vector's configuration. (optional)
                   Example: :code:`{"cert": "/path/to/file.cert", "name": "Vector-XXXX", "guid": "<secret_key>"}`
                   where :code:`cert` is the certificate to identify Vector, :code:`name` is the name on Vector's face
                   when his backpack is double-clicked on the charger, and :code:`guid` is the authorization token
                   that identifies the SDK user. Note: Never share your authentication credentials with anyone.
    :param default_logging: Toggle default logging.
    :param behavior_activation_timeout: The time to wait for control of the robot before failing.
    :param enable_face_detection: Turn on face detection.
    :param enable_camera_feed: Turn camera feed on/off.
    :param enable_audio_feed: Turn audio feed on/off.
    :param show_viewer: Render camera feed on/off.
    :param requires_behavior_control: Request control of Vector's behavior system."""

    @functools.wraps(Robot.__init__)
    def __init__(self, *args, **kwargs):
        super(AsyncRobot, self).__init__(*args, **kwargs)
        self._force_async = True

    # TODO Should be private? Better method name? If not private, Add docstring and sample code
    def add_pending(self, task):
        self.pending += [task]

    # TODO Should be private? Better method name? If not private, Add docstring and sample code
    def remove_pending(self, task):
        self.pending = [x for x in self.pending if x is not task]
