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

"""Utility methods for Vector's vision

Vector's can detect various types of objects through his camera feed.

The :class:`VisionComponent` class defined in this module is made available as
:attr:`anki_vector.robot.Robot.vision` and can be used to enable/disable vision
processing on the robot.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['VisionComponent']

from concurrent import futures

from . import util, connection, events
from .messaging import protocol


class VisionComponent(util.Component):  # pylint: disable=too-few-public-methods
    """VisionComponent exposes controls for the robot's internal image processing.

    The :class:`anki_vector.robot.Robot` or :class:`anki_vector.robot.AsyncRobot` instance owns this vision component.

    :param robot: A reference to the owner Robot object.
    """

    def __init__(self, robot):
        super().__init__(robot)

        self._detect_faces = False
        self._detect_custom_objects = False
        self._detect_motion = False
        self._display_camera_feed_on_face = False

        robot.events.subscribe(self._handle_mirror_mode_disabled_event, events.Events.mirror_mode_disabled)
        robot.events.subscribe(self._handle_vision_modes_auto_disabled_event, events.Events.vision_modes_auto_disabled)

    def close(self):
        """Close all the running vision modes and wait for a response."""
        vision_mode = self.disable_all_vision_modes()  # pylint: disable=assignment-from-no-return
        if isinstance(vision_mode, futures.Future):
            vision_mode.result()

    def _handle_mirror_mode_disabled_event(self, _robot, _event_type, _msg):
        self._display_camera_feed_on_face = False

    def _handle_vision_modes_auto_disabled_event(self, _robot, _event_type, _msg):
        self._detect_faces = False
        self._detect_custom_objects = False
        self._detect_motion = False
        self._display_camera_feed_on_face = False

    @property
    def detect_faces(self):
        return self._detect_faces

    @property
    def detect_custom_objects(self):
        return self._detect_custom_objects

    @property
    def detect_motion(self):
        return self._detect_motion

    @property
    def display_camera_feed_on_face(self):
        return self._display_camera_feed_on_face

    @connection.on_connection_thread()
    async def disable_all_vision_modes(self):
        if self.detect_faces:
            await self.enable_face_detection(False, False)
        if self.detect_custom_objects:
            await self.enable_custom_object_detection(False)
        if self.detect_motion:
            await self.enable_motion_detection(False)
        if self.display_camera_feed_on_face:
            await self.enable_display_camera_feed_on_face(False)

    # TODO: add return type hint
    @connection.on_connection_thread()
    async def enable_custom_object_detection(self, detect_custom_objects: bool = True):
        """Enable custom object detection on the robot's camera.

        If custom object detection is being turned off, the robot may still choose to keep it on
        if another subscriber (including one internal to the robot) requests this vision mode be active.

        See :class:`objects.CustomObjectMarkers`.

        :param detect_custom_objects: Specify whether we want the robot to detect custom objects.

        .. testcode::

            import anki_vector
            with anki_vector.Robot() as robot:
                robot.vision.enable_custom_object_detection()
        """
        self._detect_custom_objects = detect_custom_objects

        enable_marker_detection_request = protocol.EnableMarkerDetectionRequest(enable=detect_custom_objects)
        return await self.grpc_interface.EnableMarkerDetection(enable_marker_detection_request)

    # TODO: add return type hint
    @connection.on_connection_thread()
    async def enable_face_detection(
            self,
            detect_faces: bool = True,
            # detect_smile: bool = False,
            estimate_expression: bool = False,
            # detect_blink: bool = False,
            # detect_gaze: bool = False
    ):
        """Enable face detection on the robot's camera

        :param detect_faces: Specify whether we want the robot to detect faces.
        :param detect_smile: Specify whether we want the robot to detect smiles in detected faces.
        :param estimate_expression: Specify whether we want the robot to estimate what expression detected faces are showing.
        :param detect_blink: Specify whether we want the robot to detect how much detected faces are blinking.
        :param detect_gaze: Specify whether we want the robot to detect where detected faces are looking.
        """
        self._detect_faces = detect_faces

        enable_face_detection_request = protocol.EnableFaceDetectionRequest(
            enable=detect_faces,
            enable_smile_detection=False,
            enable_expression_estimation=estimate_expression,
            enable_blink_detection=False,
            enable_gaze_detection=False)
        return await self.grpc_interface.EnableFaceDetection(enable_face_detection_request)

    @connection.on_connection_thread()
    async def enable_motion_detection(self, detect_motion: bool = True):
        """Enable motion detection on the robot's camera

        :param detect_motion: Specify whether we want the robot to detect motion.

        .. testcode::

            import time

            import anki_vector
            from anki_vector.events import Events
            from anki_vector.util import degrees

            def on_robot_observed_motion(robot, event_type, event):
                print("Robot observed motion")

            with anki_vector.Robot(show_viewer=True) as robot:
                robot.events.subscribe(on_robot_observed_motion, Events.robot_observed_motion)

                # If necessary, move Vector's Head and Lift to make it easy to see his face
                robot.behavior.set_head_angle(degrees(45.0))
                robot.behavior.set_lift_height(0.0)

                robot.vision.enable_motion_detection(detect_motion=True)

                print("Vector is waiting to see motion. Make some movement within Vector's camera view")

                time.sleep(3.0)

            robot.events.unsubscribe(on_robot_observed_motion, Events.robot_observed_motion)
        """
        self._detect_motion = detect_motion

        enable_motion_detection_request = protocol.EnableMotionDetectionRequest(enable=detect_motion)
        return await self.grpc_interface.EnableMotionDetection(enable_motion_detection_request)

    # TODO: add return type hint
    @connection.on_connection_thread()
    async def enable_display_camera_feed_on_face(self, display_camera_feed_on_face: bool = True):
        """Display the robot's camera feed on its face along with any detections (if enabled)

        :param display_camera_feed_on_face: Specify whether we want to display the robot's camera feed on its face.

        .. testcode::

            import anki_vector

            import time

            with anki_vector.Robot() as robot:
                robot.vision.enable_display_camera_feed_on_face()
                time.sleep(10.0)
        """
        self._display_camera_feed_on_face = display_camera_feed_on_face

        display_camera_feed_request = protocol.EnableMirrorModeRequest(enable=display_camera_feed_on_face)
        return await self.grpc_interface.EnableMirrorMode(display_camera_feed_request)
