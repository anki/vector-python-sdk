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
.. _behavior:

Behavior related classes and functions.

Behaviors represent a complex task which requires Vector's
internal logic to determine how long it will take. This
may include combinations of animation, path planning or
other functionality. Examples include :meth:`drive_on_charger`,
:meth:`set_lift_height`, etc.

For commands such as :meth:`go_to_pose`, :meth:`drive_on_charger` and :meth:`dock_with_cube`,
Vector uses path planning, which refers to the problem of
navigating the robot from point A to B without collisions. Vector
loads known obstacles from his map, creates a path to navigate
around those objects, then starts following the path. If a new obstacle
is found while following the path, a new plan may be created.

The :class:`BehaviorComponent` class in this module contains
functions for all the behaviors.
"""

__all__ = ["MAX_HEAD_ANGLE", "MIN_HEAD_ANGLE",
           "MAX_LIFT_HEIGHT", "MAX_LIFT_HEIGHT_MM", "MIN_LIFT_HEIGHT", "MIN_LIFT_HEIGHT_MM",
           "BehaviorComponent"]


from . import connection, objects, util
from .messaging import protocol

# Constants

#: The minimum angle the robot's head can be set to.
MIN_HEAD_ANGLE = util.degrees(-22.0)

#: The maximum angle the robot's head can be set to
MAX_HEAD_ANGLE = util.degrees(45.0)

# The lowest height-above-ground that lift can be moved to in millimeters.
MIN_LIFT_HEIGHT_MM = 32.0

#: The lowest height-above-ground that lift can be moved to
MIN_LIFT_HEIGHT = util.distance_mm(MIN_LIFT_HEIGHT_MM)

# The largest height-above-ground that lift can be moved to in millimeters.
MAX_LIFT_HEIGHT_MM = 92.0

#: The largest height-above-ground that lift can be moved to
MAX_LIFT_HEIGHT = util.distance_mm(MAX_LIFT_HEIGHT_MM)


# TODO: Expose is_active and priority states of the SDK behavior control from this class.
class BehaviorComponent(util.Component):
    """Run behaviors on Vector"""

    _next_action_id = protocol.FIRST_SDK_TAG

    def __init__(self, robot):
        super().__init__(robot)
        self._motion_profile_map = {}

    # TODO Make the motion_profile_map into a class.
    @property
    def motion_profile_map(self) -> dict:
        """Tells Vector how to drive when receiving navigation and movement actions
        such as go_to_pose and dock_with_cube.

        motion_prof_map values are as follows:
         |  speed_mmps (float)
         |  accel_mmps2 (float)
         |  decel_mmps2 (float)
         |  point_turn_speed_rad_per_sec (float)
         |  point_turn_accel_rad_per_sec2 (float)
         |  point_turn_decel_rad_per_sec2 (float)
         |  dock_speed_mmps (float)
         |  dock_accel_mmps2 (float)
         |  dock_decel_mmps2 (float)
         |  reverse_speed_mmps (float)
         |  is_custom (bool)

        :getter: Returns the motion profile map
        :setter: Sets the motion profile map

        :param motion_prof_map: Provide custom speed, acceleration and deceleration
            values with which the robot goes to the given pose.
        """
        return self._motion_profile_map

    @motion_profile_map.setter
    def motion_profile_map(self, motion_profile_map: dict):
        self._motion_profile_map = motion_profile_map

    def _motion_profile_for_proto(self) -> protocol.PathMotionProfile:
        """Packages the current motion profile into a proto object

        Returns:
            A profile object describing motion which can be passed with any proto action message.
        """
        # TODO: This should be made into its own class
        default_motion_profile = {
            "speed_mmps": 100.0,
            "accel_mmps2": 200.0,
            "decel_mmps2": 500.0,
            "point_turn_speed_rad_per_sec": 2.0,
            "point_turn_accel_rad_per_sec2": 10.0,
            "point_turn_decel_rad_per_sec2": 10.0,
            "dock_speed_mmps": 60.0,
            "dock_accel_mmps2": 200.0,
            "dock_decel_mmps2": 500.0,
            "reverse_speed_mmps": 80.0,
            "is_custom": 1 if self._motion_profile_map else 0
        }
        default_motion_profile.update(self._motion_profile_map)

        return protocol.PathMotionProfile(**default_motion_profile)

    @classmethod
    def _get_next_action_id(cls):
        # Post increment _current_action_id (and loop within the SDK_TAG range)
        next_action_id = cls._next_action_id
        if cls._next_action_id == protocol.LAST_SDK_TAG:
            cls._next_action_id = protocol.FIRST_SDK_TAG
        else:
            cls._next_action_id += 1
        return next_action_id

    # Navigation actions
    @connection.on_connection_thread()
    async def drive_off_charger(self):
        """Drive Vector off the charger

        If Vector is on the charger, drives him off the charger.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                robot.behavior.drive_off_charger()
        """
        drive_off_charger_request = protocol.DriveOffChargerRequest()
        return await self.grpc_interface.DriveOffCharger(drive_off_charger_request)

    @connection.on_connection_thread()
    async def drive_on_charger(self):
        """Drive Vector onto the charger

        Vector will attempt to find the charger and, if successful, he will
        back onto it and start charging.

        Vector's charger has a visual marker so that the robot can locate it
        for self-docking.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                robot.behavior.drive_on_charger()
        """
        drive_on_charger_request = protocol.DriveOnChargerRequest()
        return await self.grpc_interface.DriveOnCharger(drive_on_charger_request)

    @connection.on_connection_thread()
    async def set_eye_color(self, hue: float, saturation: float) -> protocol.SetEyeColorResponse:
        """Set Vector's eye color.

        .. testcode::

            import anki_vector
            import time

            with anki_vector.Robot() as robot:
                print("Set Vector's eye color to purple...")
                robot.behavior.set_eye_color(0.83, 0.76)
                time.sleep(5)

        :param hue: The hue to use for Vector's eyes.
        :param saturation: The saturation to use for Vector's eyes.
        """
        eye_color_request = protocol.SetEyeColorRequest(hue=hue, saturation=saturation)
        return await self.conn.grpc_interface.SetEyeColor(eye_color_request)

    @connection.on_connection_thread()
    async def go_to_pose(self,
                         pose: util.Pose,
                         relative_to_robot: bool = False,
                         num_retries: int = 0) -> protocol.GoToPoseResponse:
        """Tells Vector to drive to the specified pose and orientation.

        In navigating to the requested pose, Vector will use path planning.

        If relative_to_robot is set to True, the given pose will assume the
        robot's pose as its origin.

        Since the robot understands position by monitoring its tread movement,
        it does not understand movement in the z axis. This means that the only
        applicable elements of pose in this situation are position.x position.y
        and rotation.angle_z.

        :param pose: The destination pose.
        :param relative_to_robot: Whether the given pose is relative to
                                  the robot's pose.
        :param num_retries: Number of times to re-attempt action in case of a failure.

        Returns:
            A response from the robot with status information sent when this request successfully completes or fails.

        .. testcode::

            import anki_vector
            from anki_vector.util import degrees, Pose

            with anki_vector.Robot() as robot:
                pose = Pose(x=50, y=0, z=0, angle_z=anki_vector.util.Angle(degrees=0))
                robot.behavior.go_to_pose(pose)
        """
        if relative_to_robot and self.robot.pose:
            pose = self.robot.pose.define_pose_relative_this(pose)

        motion_prof = self._motion_profile_for_proto()
        # @TODO: the id_tag we supply can be used to cancel this action,
        #  however when we implement that we will need some way to get the id_tag
        #  out of this function.
        go_to_pose_request = protocol.GoToPoseRequest(x_mm=pose.position.x,
                                                      y_mm=pose.position.y,
                                                      rad=pose.rotation.angle_z.radians,
                                                      motion_prof=motion_prof,
                                                      id_tag=self._get_next_action_id(),
                                                      num_retries=num_retries)

        return await self.grpc_interface.GoToPose(go_to_pose_request)

    # TODO alignment_type coming out ugly in the docs without real values
    @connection.on_connection_thread()
    async def dock_with_cube(self,
                             target_object: objects.LightCube,
                             approach_angle: util.Angle = None,
                             alignment_type: protocol.AlignmentType = protocol.ALIGNMENT_TYPE_LIFT_PLATE,
                             distance_from_marker: util.Distance = None,
                             num_retries: int = 0) -> protocol.DockWithCubeResponse:
        """Tells Vector to dock with a light cube, optionally using a given approach angle and distance.

        While docking with the cube, Vector will use path planning.

        :param target_object: The LightCube object to dock with.
        :param approach_angle: Angle to approach the dock with.
        :param alignment_type: Which part of the robot to align with the object.
        :param distance_from_marker: How far from the object to approach (0 to dock)
        :param num_retries: Number of times to re-attempt action in case of a failure.

        Returns:
            A response from the robot with status information sent when this request successfully completes or fails.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                robot.world.connect_cube()

                if robot.world.connected_light_cube:
                    dock_response = robot.behavior.dock_with_cube(robot.world.connected_light_cube)
                    docking_result = dock_response.result
        """
        if target_object is None:
            raise Exception("Must supply a target_object to dock_with_cube")

        motion_prof = self._motion_profile_for_proto()

        # @TODO: the id_tag we supply can be used to cancel this action,
        #  however when we implement that we will need some way to get the id_tag
        #  out of this function.
        dock_request = protocol.DockWithCubeRequest(object_id=target_object.object_id,
                                                    alignment_type=alignment_type,
                                                    motion_prof=motion_prof,
                                                    id_tag=self._get_next_action_id(),
                                                    num_retries=num_retries)
        if approach_angle is not None:
            dock_request.use_approach_angle = True
            dock_request.use_pre_dock_pose = True
            dock_request.approach_angle = approach_angle.radians
        if distance_from_marker is not None:
            dock_request.distance_from_marker = distance_from_marker.distance_mm

        return await self.grpc_interface.DockWithCube(dock_request)

    # Movement actions
    @connection.on_connection_thread()
    async def drive_straight(self,
                             distance: util.Distance,
                             speed: util.Speed,
                             should_play_anim: bool = True,
                             num_retries: int = 0) -> protocol.DriveStraightResponse:
        """Tells Vector to drive in a straight line.

        Vector will drive for the specified distance (forwards or backwards)

        Vector must be off of the charger for this movement action.

        :param distance: The distance to drive
            (>0 for forwards, <0 for backwards)
        :param speed: The speed to drive at
            (should always be >0, the abs(speed) is used internally)
        :param should_play_anim: Whether to play idle animations whilst driving
            (tilt head, hum, animated eyes, etc.)
        :param num_retries: Number of times to re-attempt action in case of a failure.

        Returns:
            A response from the robot with status information sent when this request successfully completes or fails.

        .. testcode::

            import anki_vector
            from anki_vector.util import degrees, distance_mm, speed_mmps

            with anki_vector.Robot() as robot:
                robot.behavior.drive_straight(distance_mm(200), speed_mmps(100))
        """

        # @TODO: the id_tag we supply can be used to cancel this action,
        #  however when we implement that we will need some way to get the id_tag
        #  out of this function.
        drive_straight_request = protocol.DriveStraightRequest(speed_mmps=speed.speed_mmps,
                                                               dist_mm=distance.distance_mm,
                                                               should_play_animation=should_play_anim,
                                                               id_tag=self._get_next_action_id(),
                                                               num_retries=num_retries)

        return await self.grpc_interface.DriveStraight(drive_straight_request)

    @connection.on_connection_thread()
    async def turn_in_place(self,
                            angle: util.Angle,
                            speed: util.Angle = util.Angle(0.0),
                            accel: util.Angle = util.Angle(0.0),
                            angle_tolerance: util.Angle = util.Angle(0.0),
                            is_absolute: bool = 0,
                            num_retries: int = 0) -> protocol.TurnInPlaceResponse:
        """Turn the robot around its current position.

        Vector must be off of the charger for this movement action.

        :param angle: The angle to turn. Positive
                values turn to the left, negative values to the right.
        :param speed: Angular turn speed (per second).
        :param accel: Acceleration of angular turn
                (per second squared).
        :param angle_tolerance: angular tolerance
                to consider the action complete (this is clamped to a minimum
                of 2 degrees internally).
        :param is_absolute: True to turn to a specific angle, False to
                turn relative to the current pose.
        :param num_retries: Number of times to re-attempt the turn in case of a failure.

        Returns:
            A response from the robot with status information sent when this request successfully completes or fails.

        .. testcode::

            import anki_vector
            from anki_vector.util import degrees

            with anki_vector.Robot() as robot:
                robot.behavior.turn_in_place(degrees(90))
        """
        turn_in_place_request = protocol.TurnInPlaceRequest(angle_rad=angle.radians,
                                                            speed_rad_per_sec=speed.radians,
                                                            accel_rad_per_sec2=accel.radians,
                                                            tol_rad=angle_tolerance.radians,
                                                            is_absolute=is_absolute,
                                                            id_tag=self._get_next_action_id(),
                                                            num_retries=num_retries)

        return await self.grpc_interface.TurnInPlace(turn_in_place_request)

    @connection.on_connection_thread()
    async def set_head_angle(self,
                             angle: util.Angle,
                             accel: float = 10.0,
                             max_speed: float = 10.0,
                             duration: float = 0.0,
                             num_retries: int = 0) -> protocol.SetHeadAngleResponse:
        """Tell Vector's head to move to a given angle.

        :param angle: Desired angle for Vector's head.
            (:const:`MIN_HEAD_ANGLE` to :const:`MAX_HEAD_ANGLE`).
            (we clamp it to this range internally).
        :param accel: Acceleration of Vector's head in radians per second squared.
        :param max_speed: Maximum speed of Vector's head in radians per second.
        :param duration: Time for Vector's head to move in seconds. A value
                of zero will make Vector try to do it as quickly as possible.
        :param num_retries: Number of times to re-attempt the action in case of a failure.

        Returns:
            A response from the robot with status information sent when this request successfully completes or fails.

        .. testcode::

            import anki_vector
            from anki_vector.util import degrees
            from anki_vector.behavior import MIN_HEAD_ANGLE, MAX_HEAD_ANGLE

            with anki_vector.Robot() as robot:
                # move head from minimum to maximum angle
                robot.behavior.set_head_angle(MIN_HEAD_ANGLE)
                robot.behavior.set_head_angle(MAX_HEAD_ANGLE)
                # move head to middle
                robot.behavior.set_head_angle(degrees(35.0))
        """
        if angle < MIN_HEAD_ANGLE:
            self.logger.warning("head angle %s too small, should be in %f..%f range - clamping",
                                angle.degrees, MIN_HEAD_ANGLE.degrees, MAX_HEAD_ANGLE.degrees)
            angle = MIN_HEAD_ANGLE
        elif angle > MAX_HEAD_ANGLE:
            self.logger.warning("head angle %s too large, should be in %f..%f range - clamping",
                                angle.degrees, MIN_HEAD_ANGLE.degrees, MAX_HEAD_ANGLE.degrees)
            angle = MAX_HEAD_ANGLE

        set_head_angle_request = protocol.SetHeadAngleRequest(angle_rad=angle.radians,
                                                              max_speed_rad_per_sec=max_speed,
                                                              accel_rad_per_sec2=accel,
                                                              duration_sec=duration,
                                                              id_tag=self._get_next_action_id(),
                                                              num_retries=num_retries)

        return await self.grpc_interface.SetHeadAngle(set_head_angle_request)

    @connection.on_connection_thread()
    async def set_lift_height(self,
                              height: float,
                              accel: float = 10.0,
                              max_speed: float = 10.0,
                              duration: float = 0.0,
                              num_retries: int = 0) -> protocol.SetLiftHeightResponse:
        """Tell Vector's lift to move to a given height.

        :param height: desired height for Vector's lift 0.0 (bottom) to
                1.0 (top) (we clamp it to this range internally).
        :param accel: Acceleration of Vector's lift in radians per
                second squared.
        :param max_speed: Maximum speed of Vector's lift in radians per second.
        :param duration: Time for Vector's lift to move in seconds. A value
                of zero will make Vector try to do it as quickly as possible.
        :param num_retries: Number of times to re-attempt the action in case of a failure.

        Returns:
            A response from the robot with status information sent when this request successfully completes or fails.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                robot.behavior.set_lift_height(1.0)
        """

        if height < 0.0:
            self.logger.warning("lift height %s too small, should be in 0..1 range - clamping", height)
            height = MIN_LIFT_HEIGHT_MM
        elif height > 1.0:
            self.logger.warning("lift height %s too large, should be in 0..1 range - clamping", height)
            height = MAX_LIFT_HEIGHT_MM
        else:
            height = MIN_LIFT_HEIGHT_MM + (height * (MAX_LIFT_HEIGHT_MM - MIN_LIFT_HEIGHT_MM))

        set_lift_height_request = protocol.SetLiftHeightRequest(height_mm=height,
                                                                max_speed_rad_per_sec=max_speed,
                                                                accel_rad_per_sec2=accel,
                                                                duration_sec=duration,
                                                                id_tag=self._get_next_action_id(),
                                                                num_retries=num_retries)

        return await self.grpc_interface.SetLiftHeight(set_lift_height_request)
