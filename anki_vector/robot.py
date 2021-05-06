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
This contains the :class:`Robot` and :class:`AsyncRobot` classes for managing Vector.

:class:`Robot` will run all behaviors in sequence and directly return the results.

:class:`AsyncRobot` will instead provide a :class:`concurrent.futures.Future` which the
caller may use to obtain the result when they desire.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['Robot', 'AsyncRobot']

import concurrent
import functools

from . import (animation, audio, behavior, camera,
               events, faces, motors, nav_map, screen,
               photos, proximity, status, touch,
               util, viewer, vision, world)
from .connection import (Connection,
                         on_connection_thread,
                         ControlPriorityLevel)
from .exceptions import (VectorNotReadyException,
                         VectorPropertyValueNotReadyException,
                         VectorUnreliableEventStreamException)
from .viewer import (ViewerComponent, Viewer3DComponent)
from .messaging import protocol
from .mdns import VectorMdns


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
            robot.anim.play_animation_trigger("GreetAfterLongTime")

    2. Using :func:`connect` and :func:`disconnect` to explicitly open and close the connection:
    it allows the robot's connection to continue in the context in which it started.

    .. testcode::

        import anki_vector

        # Create a Robot object
        robot = anki_vector.Robot()
        # Connect to the Robot
        robot.connect()
        # Run your commands
        robot.anim.play_animation_trigger("GreetAfterLongTime")
        # Disconnect from Vector
        robot.disconnect()

    :param serial: Vector's serial number. The robot's serial number (ex. 00e20100) is located on the underside of Vector,
                   or accessible from Vector's debug screen. Used to identify which Vector configuration to load.
    :param ip: Vector's IP address. (optional)
    :param name: Vector's name (in format :code:`"Vector-XXXX"`) to be used for mDNS discovery. If a Vector with the given name
                 is discovered, the :code:`ip` parameter (and config field) will be overridden.
    :param config: A custom :class:`dict` to override values in Vector's configuration. (optional)
                   Example: :code:`{"cert": "/path/to/file.cert", "name": "Vector-XXXX", "guid": "<secret_key>"}`
                   where :code:`cert` is the certificate to identify Vector, :code:`name` is the name on Vector's face
                   when his backpack is double-clicked on the charger, and :code:`guid` is the authorization token
                   that identifies the SDK user. Note: Never share your authentication credentials with anyone.
    :param default_logging: Toggle default logging.
    :param behavior_activation_timeout: The time to wait for control of the robot before failing.
    :param cache_animation_lists: Get the list of animation triggers and animations available at startup.
    :param enable_face_detection: Turn on face detection.
    :param estimate_facial_expression: Turn estimating facial expression on/off. Enabling :code:`estimate_facial_expression`
                                       returns a facial expression, the expression values and the :class:`anki_vector.util.ImageRect`
                                       for observed face regions (eyes, nose, and mouth) as part of the :code:`RobotObservedFace` event.
                                       It is turned off by default as the number of :code:`RobotObservedFace` events
                                       are reduced due to the increased processing time.
    :param enable_audio_feed: Turn audio feed on/off.
    :param enable_custom_object_detection: Turn custom object detection on/off.
    :param enable_nav_map_feed: Turn navigation map feed on/off.
    :param show_viewer: Specifies whether to display a view of Vector's camera in a window.
    :param show_3d_viewer: Specifies whether to display a 3D view of Vector's understanding of the world in a window.
    :param behavior_control_level: Request control of Vector's behavior system at a specific level of control.  Pass
                                :code:`None` if behavior control is not needed.
                                See :class:`ControlPriorityLevel` for more information."""

    def __init__(self,
                 serial: str = None,
                 ip: str = None,
                 name: str = None,
                 config: dict = None,
                 escape_pod: bool = None,
                 default_logging: bool = True,
                 behavior_activation_timeout: int = 10,
                 cache_animation_lists: bool = True,
                 enable_face_detection: bool = False,
                 estimate_facial_expression: bool = False,
                 enable_audio_feed: bool = False,
                 enable_custom_object_detection: bool = False,
                 enable_nav_map_feed: bool = None,
                 show_viewer: bool = False,
                 show_3d_viewer: bool = False,
                 behavior_control_level: ControlPriorityLevel = ControlPriorityLevel.DEFAULT_PRIORITY):
        if default_logging:
            util.setup_basic_logging()
        self.logger = util.get_class_logger(__name__, self)
        self._force_async = False
        config = config if config is not None else {}
        config = {**util.read_configuration(serial, name, self.logger, escape_pod or False), **config}
        escape_pod = config.get("escape_pod", False) if escape_pod is None else escape_pod

        if name is not None:
            vector_mdns = VectorMdns.find_vector(name)

            if vector_mdns is not None:
                ip = vector_mdns['ipv4']

        self._escape_pod = escape_pod
        self._name = config["name"] if 'name' in config else None
        self._cert_file = config["cert"] if 'cert' in config else None
        self._guid = config["guid"] if 'guid' in config else None
        self._port = config["port"] if 'port' in config else "443"
        self._ip = ip or config.get("ip")
        if self._ip is None and 'ip' in config:
            self._ip = config["ip"]

        if (not escape_pod) and (self._name is None or self._ip is None or self._cert_file is None or self._guid is None):
            raise ValueError("The Robot object requires a serial and for Vector to be logged in (using the app then running the `python3 -m anki_vector.configure`).\n"
                             "You may also provide the values necessary for connection through the config parameter. ex: "
                             '{"name":"Vector-XXXX", "ip":"XX.XX.XX.XX", "cert":"/path/to/cert_file", "guid":"<secret_key>"}')

        if (escape_pod) and (self._ip is None):
            raise ValueError('Could not find the sdk configuration file. Please run `python3 -m anki_vector.configure_pod` to set up your Vector for SDK usage.')

        #: :class:`anki_vector.connection.Connection`: The active connection to the robot.
        self._conn = Connection(self._name, ':'.join([self._ip, self._port]), self._cert_file, self._guid, self._escape_pod, behavior_control_level=behavior_control_level)
        self._events = events.EventHandler(self)

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
        self.estimate_facial_expression = estimate_facial_expression
        self.enable_custom_object_detection = enable_custom_object_detection
        self.cache_animation_lists = cache_animation_lists

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

        self._enable_audio_feed = enable_audio_feed
        if enable_nav_map_feed is not None:
            self._enable_nav_map_feed = enable_nav_map_feed
        else:
            self._enable_nav_map_feed = False
        self._show_viewer = show_viewer
        self._show_3d_viewer = show_3d_viewer
        if show_3d_viewer and enable_nav_map_feed is None:
            self.logger.warning("enable_nav_map_feed should be True for 3d viewer to render correctly.")
            self._enable_nav_map_feed = True

    @property
    def force_async(self) -> bool:
        """A flag used to determine if this is a :class:`Robot` or :class:`AsyncRobot`."""
        return self._force_async

    @property
    def conn(self) -> Connection:
        """A reference to the :class:`~anki_vector.connection.Connection` instance."""
        return self._conn

    @property
    def events(self) -> events.EventHandler:
        """A reference to the :class:`~anki_vector.events.EventHandler` instance."""
        return self._events

    @property
    def anim(self) -> animation.AnimationComponent:
        """A reference to the :class:`~anki_vector.animation.AnimationComponent` instance."""
        if self._anim is None:
            raise VectorNotReadyException("AnimationComponent is not yet initialized")
        return self._anim

    @property
    def audio(self) -> audio.AudioComponent:
        """The audio instance used to control Vector's microphone feed and speaker playback."""

        if self._audio is None:
            raise VectorNotReadyException("AudioComponent is not yet initialized")
        return self._audio

    @property
    def behavior(self) -> behavior.BehaviorComponent:
        """A reference to the :class:`~anki_vector.behavior.BehaviorComponent` instance."""
        return self._behavior

    @property
    def camera(self) -> camera.CameraComponent:
        """The :class:`~anki_vector.camera.CameraComponent` instance used to control Vector's camera feed.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                robot.camera.init_camera_feed()
                image = robot.camera.latest_image
                image.raw_image.show()
        """
        if self._camera is None:
            raise VectorNotReadyException("CameraComponent is not yet initialized")
        return self._camera

    @property
    def faces(self) -> faces.FaceComponent:
        """A reference to the :class:`~anki_vector.faces.FaceComponent` instance."""
        if self._faces is None:
            raise VectorNotReadyException("FaceComponent is not yet initialized")
        return self._faces

    @property
    def motors(self) -> motors.MotorComponent:
        """A reference to the :class:`~anki_vector.motors.MotorComponent` instance."""
        if self._motors is None:
            raise VectorNotReadyException("MotorComponent is not yet initialized")
        return self._motors

    @property
    def nav_map(self) -> nav_map.NavMapComponent:
        """A reference to the :class:`~anki_vector.nav_map.NavMapComponent` instance."""
        if self._nav_map is None:
            raise VectorNotReadyException("NavMapComponent is not yet initialized")
        return self._nav_map

    @property
    def screen(self) -> screen.ScreenComponent:
        """A reference to the :class:`~anki_vector.screen.ScreenComponent` instance."""
        if self._screen is None:
            raise VectorNotReadyException("ScreenComponent is not yet initialized")
        return self._screen

    @property
    def photos(self) -> photos.PhotographComponent:
        """A reference to the :class:`~anki_vector.photos.PhotographComponent` instance."""
        if self._photos is None:
            raise VectorNotReadyException("PhotographyComponent is not yet initialized")
        return self._photos

    @property
    def proximity(self) -> proximity.ProximityComponent:
        """:class:`~anki_vector.proximity.ProximityComponent` containing state related to object proximity detection.

        .. code-block:: python

            import anki_vector
            with anki_vector.Robot() as robot:
                proximity_data = robot.proximity.last_sensor_reading
                if proximity_data is not None:
                    print(proximity_data.distance)
        """
        return self._proximity

    @property
    def touch(self) -> touch.TouchComponent:
        """:class:`~anki_vector.touch.TouchComponent` containing state related to object touch detection.

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                print('Robot is being touched: {0}'.format(robot.touch.last_sensor_reading.is_being_touched))
        """
        return self._touch

    @property
    def viewer(self) -> ViewerComponent:
        """The :class:`~anki_vector.viewer.ViewerComponent` instance used to render Vector's camera feed.

        .. testcode::

            import time

            import anki_vector

            with anki_vector.Robot() as robot:
                # Render video for 5 seconds
                robot.viewer.show()
                time.sleep(5)

                # Disable video render and camera feed for 5 seconds
                robot.viewer.close()
        """
        if self._viewer is None:
            raise VectorNotReadyException("ViewerComponent is not yet initialized")
        return self._viewer

    @property
    def viewer_3d(self) -> Viewer3DComponent:
        """The :class:`~anki_vector.viewer.Viewer3DComponent` instance used to render Vector's navigation map.

        .. testcode::

            import time

            import anki_vector

            with anki_vector.Robot(show_3d_viewer=True, enable_nav_map_feed=True) as robot:
                # Render 3D view of navigation map for 5 seconds
                time.sleep(5)
        """
        if self._viewer_3d is None:
            raise VectorNotReadyException("Viewer3DComponent is not yet initialized")
        return self._viewer_3d

    @property
    def vision(self) -> vision.VisionComponent:
        """:class:`~anki_vector.vision.VisionComponent` containing functionality related to vision based object detection.

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                robot.vision.enable_custom_object_detection()
        """
        return self._vision

    @property
    def world(self) -> world.World:
        """A reference to the :class:`~anki_vector.world.World` instance, or None if the World is not yet initialized."""
        if self._world is None:
            raise VectorNotReadyException("WorldComponent is not yet initialized")
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
            from anki_vector.util import degrees

            # Set the robot so that he can see a cube.
            with anki_vector.Robot() as robot:
                robot.behavior.set_head_angle(degrees(0.0))
                robot.behavior.set_lift_height(0.0)

                robot.world.connect_cube()

                if robot.world.connected_light_cube:
                    robot.behavior.pickup_object(robot.world.connected_light_cube)

                print("carrying_object_id: ", robot.carrying_object_id)
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
        # TODO add audio feed enablement when ready

    # Unpack streamed data to robot's internal properties
    def _unpack_robot_state(self, _robot, _event_type, msg):
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
            robot.anim.play_animation_trigger("GreetAfterLongTime")
            robot.disconnect()

        :param timeout: The time to allow for a connection before a
            :class:`anki_vector.exceptions.VectorTimeoutException` is raised.
        """
        self.conn.connect(timeout=timeout)
        self.events.start(self.conn)

        # Initialize components
        self._anim = animation.AnimationComponent(self)
        self._audio = audio.AudioComponent(self)
        self._behavior = behavior.BehaviorComponent(self)
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
        self._camera = camera.CameraComponent(self)

        if self.cache_animation_lists:
            # Load animation triggers and animations so they are ready to play when requested
            anim_request = self._anim.load_animation_list()
            if isinstance(anim_request, concurrent.futures.Future):
                anim_request.result()
            anim_trigger_request = self._anim.load_animation_trigger_list()
            if isinstance(anim_trigger_request, concurrent.futures.Future):
                anim_trigger_request.result()

        # TODO enable audio feed when ready

        # Start rendering camera feed
        if self._show_viewer:
            self.camera.init_camera_feed()
            self.viewer.show()

        if self._show_3d_viewer:
            self.viewer_3d.show()

        if self._enable_nav_map_feed:
            self.nav_map.init_nav_map_feed()

        # Enable face detection, to allow Vector to add faces to its world view
        if self.conn.requires_behavior_control:
            face_detection = self.vision.enable_face_detection(detect_faces=self.enable_face_detection, estimate_expression=self.estimate_facial_expression)
            if isinstance(face_detection, concurrent.futures.Future):
                face_detection.result()
            object_detection = self.vision.enable_custom_object_detection(detect_custom_objects=self.enable_custom_object_detection)
            if isinstance(object_detection, concurrent.futures.Future):
                object_detection.result()

        # Subscribe to a callback that updates the robot's local properties
        self.events.subscribe(self._unpack_robot_state,
                              events.Events.robot_state,
                              _on_connection_thread=True)

        # get the camera configuration from the robot
        response = self._camera.get_camera_config()
        if isinstance(response, concurrent.futures.Future):
            response = response.result()
        self._camera.set_config(response)

        # Subscribe to a callback for camera exposure settings
        self.events.subscribe(self._camera.update_state,
                              events.Events.camera_settings_update,
                              _on_connection_thread=True)

        # access the pose to prove it has gotten back from the event stream once
        try:
            if not self.pose:
                pass
        except VectorPropertyValueNotReadyException as e:
            raise VectorUnreliableEventStreamException() from e

    def disconnect(self) -> None:
        """Close the connection with Vector.

        .. testcode::

            import anki_vector
            robot = anki_vector.Robot()
            robot.connect()
            robot.anim.play_animation_trigger("GreetAfterLongTime")
            robot.disconnect()
        """
        if self.conn.requires_behavior_control:
            self.vision.close()

        # Stop rendering video
        self.viewer.close()

        # Stop rendering 3d video
        self.viewer_3d.close()

        # Shutdown camera feed
        self.camera.close_camera_feed()

        # TODO shutdown audio feed when available

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

    @on_connection_thread(requires_control=False)
    async def get_battery_state(self) -> protocol.BatteryStateResponse:
        """Check the current state of the robot and cube batteries.

        The robot is considered fully-charged above 4.1 volts. At 3.6V, the robot is approaching low charge.

        Robot battery level values are as follows:

        +-------+---------+---------------------------------------------------------------+
        | Value | Level   | Description                                                   |
        +=======+=========+===============================================================+
        | 1     | Low     | 3.6V or less. If on charger, 4V or less.                      |
        +-------+---------+---------------------------------------------------------------+
        | 2     | Nominal | Normal operating levels.                                      |
        +-------+---------+---------------------------------------------------------------+
        | 3     | Full    | This state can only be achieved when Vector is on the charger |
        +-------+---------+---------------------------------------------------------------+

        Cube battery level values are shown below:

        +-------+---------+---------------------------------------------------------------+
        | Value | Level   | Description                                                   |
        +=======+=========+===============================================================+
        | 1     | Low     | 1.1V or less.                                                 |
        +-------+---------+---------------------------------------------------------------+
        | 2     | Normal  | Normal operating levels.                                      |
        +-------+---------+---------------------------------------------------------------+

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                print("Connecting to a cube...")
                robot.world.connect_cube()

                battery_state = robot.get_battery_state()
                if battery_state:
                    print("Robot battery voltage: {0}".format(battery_state.battery_volts))
                    print("Robot battery Level: {0}".format(battery_state.battery_level))
                    print("Robot battery is charging: {0}".format(battery_state.is_charging))
                    print("Robot is on charger platform: {0}".format(battery_state.is_on_charger_platform))
                    print("Robot suggested charger time: {0}".format(battery_state.suggested_charger_sec))
                    print("Cube battery level: {0}".format(battery_state.cube_battery.level))
                    print("Cube battery voltage: {0}".format(battery_state.cube_battery.battery_volts))
                    print("Cube battery seconds since last reading: {0}".format(battery_state.cube_battery.time_since_last_reading_sec))
                    print("Cube battery factory id: {0}".format(battery_state.cube_battery.factory_id))
        """
        get_battery_state_request = protocol.BatteryStateRequest()
        return await self.conn.grpc_interface.BatteryState(get_battery_state_request)

    @on_connection_thread(requires_control=False)
    async def get_version_state(self) -> protocol.VersionStateResponse:
        """Get the versioning information for Vector, including Vector's os_version and engine_build_id.

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                version_state = robot.get_version_state()
                if version_state:
                    print("Robot os_version: {0}".format(version_state.os_version))
                    print("Robot engine_build_id: {0}".format(version_state.engine_build_id))
        """
        get_version_state_request = protocol.VersionStateRequest()
        return await self.conn.grpc_interface.VersionState(get_version_state_request)


class AsyncRobot(Robot):
    """The AsyncRobot object is just like the Robot object, but allows multiple commands
    to be executed at the same time. To achieve this, all grpc function calls also
    return a :class:`concurrent.futures.Future`.

    1. Using :code:`with`: it works just like opening a file, and will close when
    the :code:`with` block's indentation ends.

    .. testcode::

        import anki_vector
        from anki_vector.util import degrees

        # Create the robot connection
        with anki_vector.AsyncRobot() as robot:
            # Start saying text asynchronously
            say_future = robot.behavior.say_text("Now is the time")
            # Turn robot, wait for completion
            turn_future = robot.behavior.turn_in_place(degrees(3*360))
            turn_future.result()
            # Play greet animation trigger, wait for completion
            greet_future = robot.anim.play_animation_trigger("GreetAfterLongTime")
            greet_future.result()
            # Make sure text has been spoken
            say_future.result()

    2. Using :func:`connect` and :func:`disconnect` to explicitly open and close the connection:
    it allows the robot's connection to continue in the context in which it started.

    .. testcode::

        import anki_vector
        from anki_vector.util import degrees

        # Create a Robot object
        robot = anki_vector.AsyncRobot()
        # Connect to Vector
        robot.connect()
        # Start saying text asynchronously
        say_future = robot.behavior.say_text("Now is the time")
        # Turn robot, wait for completion
        turn_future = robot.behavior.turn_in_place(degrees(3 * 360))
        turn_future.result()
        # Play greet animation trigger, wait for completion
        greet_future = robot.anim.play_animation_trigger("GreetAfterLongTime")
        greet_future.result()
        # Make sure text has been spoken
        say_future.result()
        # Disconnect from Vector
        robot.disconnect()

    When getting callbacks from the event stream, it's important to understand that function calls
    return a :class:`concurrent.futures.Future` and not an :class:`asyncio.Future`. This means any
    async callback functions will need to use :func:`asyncio.wrap_future` to be able to await the
    function's response.

    .. testcode::

        import asyncio
        import time

        import anki_vector

        async def callback(robot, event_type, event):
            await asyncio.wrap_future(robot.anim.play_animation_trigger('GreetAfterLongTime'))
            await asyncio.wrap_future(robot.behavior.set_head_angle(anki_vector.util.degrees(40)))

        if __name__ == "__main__":
            args = anki_vector.util.parse_command_args()
            with anki_vector.AsyncRobot(serial=args.serial, enable_face_detection=True) as robot:
                robot.behavior.set_head_angle(anki_vector.util.degrees(40))
                robot.events.subscribe(callback, anki_vector.events.Events.robot_observed_face)

                # Waits 10 seconds. Show Vector your face.
                time.sleep(10)

    :param serial: Vector's serial number. The robot's serial number (ex. 00e20100) is located on the underside of Vector,
                   or accessible from Vector's debug screen. Used to identify which Vector configuration to load.
    :param ip: Vector's IP Address. (optional)
    :param config: A custom :class:`dict` to override values in Vector's configuration. (optional)
                   Example: :code:`{"cert": "/path/to/file.cert", "name": "Vector-XXXX", "guid": "<secret_key>"}`
                   where :code:`cert` is the certificate to identify Vector, :code:`name` is the name on Vector's face
                   when his backpack is double-clicked on the charger, and :code:`guid` is the authorization token
                   that identifies the SDK user. Note: Never share your authentication credentials with anyone.
    :param default_logging: Toggle default logging.
    :param behavior_activation_timeout: The time to wait for control of the robot before failing.
    :param cache_animation_lists: Get the list of animation triggers and animations available at startup.
    :param enable_face_detection: Turn on face detection.
    :param estimate_facial_expression: Turn estimating facial expression on/off.
    :param enable_audio_feed: Turn audio feed on/off.
    :param enable_custom_object_detection: Turn custom object detection on/off.
    :param enable_nav_map_feed: Turn navigation map feed on/off.
    :param show_viewer: Specifies whether to display a view of Vector's camera in a window.
    :param show_3d_viewer: Specifies whether to display a 3D view of Vector's understanding of the world in a window.
    :param behavior_control_level: Request control of Vector's behavior system at a specific level of control.  Pass
                                   :code:`None` if behavior control is not needed.
                                   See :class:`ControlPriorityLevel` for more information."""

    @functools.wraps(Robot.__init__)
    def __init__(self, *args, **kwargs):
        super(AsyncRobot, self).__init__(*args, **kwargs)
        self._force_async = True
