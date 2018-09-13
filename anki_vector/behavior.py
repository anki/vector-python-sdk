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
Behaviors represent a complex task which requires Vector's
internal logic to determine how long it will take. This
may include combinations of animation, path planning or
other functionality. Examples include drive_on_charger,
set_lift_height, etc.

The :class:`BehaviorComponent` class in this module contains
functions for all the behaviors.
"""

__all__ = ["BehaviorComponent"]


from . import objects, sync, util
from .messaging import protocol


class BehaviorComponent(util.Component):
    """Run behaviors on Vector"""

    _next_action_id = protocol.FIRST_SDK_TAG

    def __init__(self, robot):
        super().__init__(robot)
        self._current_priority = None
        self._is_active = False

        self._motion_profile_map = {}

    # TODO Make the motion_profile_map into a class. Make sure it is readable in the docs b/c currently motion_prof_map param is not readable.
    @property
    def motion_profile_map(self) -> dict:
        """Tells Vector how to drive when receiving navigation and movement actions
        such as go_to_pose and dock_with_cube.

        :getter: Returns the motion profile map
        :setter: Sets the motion profile map

        :param motion_prof_map: Provide custom speed, acceleration and deceleration
            values with which the robot goes to the given pose.
            speed_mmps (float)
            accel_mmps2 (float)
            decel_mmps2 (float)
            point_turn_speed_rad_per_sec (float)
            point_turn_accel_rad_per_sec2 (float)
            point_turn_decel_rad_per_sec2 (float)
            dock_speed_mmps (float)
            dock_accel_mmps2 (float)
            dock_decel_mmps2 (float)
            reverse_speed_mmps (float)
            is_custom (bool)
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

    @property
    def current_priority(self):
        # TODO implement
        return self._current_priority

    @property
    def is_active(self) -> bool:
        # TODO implement
        """True if the behavior is currently active and may run on the robot."""
        return self._is_active

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
    @sync.Synchronizer.wrap
    async def drive_off_charger(self):
        """ Drive Vector off the charger

        If Vector is on the charger, drives him off the charger.

        .. code-block:: python

            robot.behavior.drive_off_charger()
        """
        drive_off_charger_request = protocol.DriveOffChargerRequest()
        return await self.grpc_interface.DriveOffCharger(drive_off_charger_request)

    @sync.Synchronizer.wrap
    async def drive_on_charger(self):
        """ Drive Vector onto the charger

        Vector will attempt to find the charger and, if successful, he will
        back onto it and start charging.

        .. code-block:: python

            robot.behavior.drive_on_charger()
        """
        drive_on_charger_request = protocol.DriveOnChargerRequest()
        return await self.grpc_interface.DriveOnCharger(drive_on_charger_request)

    @sync.Synchronizer.wrap
    async def go_to_pose(self,
                         pose: util.Pose,
                         relative_to_robot: bool = False,
                         num_retries: int = 0) -> protocol.GoToPoseResponse:
        """Tells Vector to drive to the specified pose and orientation.

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
            A response from the robot with status information sent when this action successfully completes or fails.

        .. code-block:: python

            pose = anki_vector.util.Pose(x=50, y=0, z=0, angle_z=anki_vector.util.Angle(degrees=0))
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

    # TODO Check that num_retries is actually working (and if not, same for other num_retries).
    @sync.Synchronizer.wrap
    async def dock_with_cube(self,
                             target_object: objects.LightCube,
                             approach_angle: util.Angle = None,
                             alignment_type: protocol.AlignmentType = protocol.ALIGNMENT_TYPE_LIFT_PLATE,
                             distance_from_marker: util.Distance = None,
                             num_retries: int = 0) -> protocol.DockWithCubeResponse:
        """Tells Vector to dock with a light cube with a given approach angle and distance.

        :param target_object: The LightCube object to dock with.
        :param approach_angle: Angle to approach the dock with.
        :param alignment_type: Which part of the robot to align with the object.
        :param distance_from_marker: How far from the object to approach (0 to dock)
        :param num_retries: Number of times to re-attempt action in case of a failure.

        Returns:
            A response from the robot with status information sent when this action successfully completes or fails.

        .. code-block:: python

            if robot.world.connected_light_cube:
                robot.behavior.dock_with_cube(object_id=robot.world.connected_light_cube)
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
    @sync.Synchronizer.wrap
    async def drive_straight(self,
                             distance: util.Distance,
                             speed: util.Speed,
                             should_play_anim: bool = True,
                             num_retries: int = 0) -> protocol.DriveStraightResponse:
        """Tells Vector to drive in a straight line

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
            A response from the robot with status information sent when this action successfully completes or fails.

        .. code-block:: python

            robot.behavior.drive_straight(distance_mm(100), speed_mmps(100))
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

    @sync.Synchronizer.wrap
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
            A response from the robot with status information sent when this action successfully completes or fails.

        .. code-block:: python

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

    @sync.Synchronizer.wrap
    async def set_head_angle(self,
                             angle: util.Angle,
                             accel: float = 10.0,
                             max_speed: float = 10.0,
                             duration: float = 0.0,
                             num_retries: int = 0) -> protocol.SetHeadAngleResponse:
        """Tell Vector's head to move to a given angle.

        :param angle: Desired angle for Vector's head.
            (:const:`MIN_HEAD_ANGLE` to :const:`MAX_HEAD_ANGLE`).
        :param accel: Acceleration of Vector's head in radians per second squared.
        :param max_speed: Maximum speed of Vector's head in radians per second.
        :param duration: Time for Vector's head to move in seconds. A value
                of zero will make Vector try to do it as quickly as possible.
        :param num_retries: Number of times to re-attempt the action in case of a failure.

        Returns:
            A response from the robot with status information sent when this action successfully completes or fails.

        .. code-block:: python

            robot.behavior.set_head_angle(degrees(50.0))
        """
        set_head_angle_request = protocol.SetHeadAngleRequest(angle_rad=angle.radians,
                                                              max_speed_rad_per_sec=max_speed,
                                                              accel_rad_per_sec2=accel,
                                                              duration_sec=duration,
                                                              id_tag=self._get_next_action_id(),
                                                              num_retries=num_retries)

        return await self.grpc_interface.SetHeadAngle(set_head_angle_request)

    @sync.Synchronizer.wrap
    async def set_lift_height(self,
                              height: float,
                              accel: float = 10.0,
                              max_speed: float = 10.0,
                              duration: float = 0.0,
                              num_retries: int = 0) -> protocol.SetLiftHeightResponse:
        """Tell Vector's lift to move to a given height

        :param height: desired height for Vector's lift 0.0 (bottom) to
                1.0 (top) (we clamp it to this range internally).
        :param accel: Acceleration of Vector's lift in radians per
                second squared.
        :param max_speed: Maximum speed of Vector's lift in radians per second.
        :param duration: Time for Vector's lift to move in seconds. A value
                of zero will make Vector try to do it as quickly as possible.
        :param num_retries: Number of times to re-attempt the action in case of a failure.

        Returns:
            A response from the robot with status information sent when this action successfully completes or fails.

        .. code-block:: python

            robot.behavior.set_lift_height(100.0)
        """
        set_lift_height_request = protocol.SetLiftHeightRequest(height_mm=height,
                                                                max_speed_rad_per_sec=max_speed,
                                                                accel_rad_per_sec2=accel,
                                                                duration_sec=duration,
                                                                id_tag=self._get_next_action_id(),
                                                                num_retries=num_retries)

        return await self.grpc_interface.SetLiftHeight(set_lift_height_request)
