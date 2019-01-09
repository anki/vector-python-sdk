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
Animation related classes, functions, events and values.

Animations represent a sequence of highly coordinated movements, faces, lights, and sounds used to demonstrate an emotion or reaction.

Animations can control the following tracks: head, lift, treads, face, audio and backpack lights.

There are two ways to play an animation on Vector: play_animation and play_animation_trigger (not yet implemented). When calling play_animation,
you select the specific animation you want the robot to run. For play_animation_trigger, you select a group of animations, and the robot
will choose which animation from the group to run when you execute the method.

By default, when an SDK program starts, the SDK will request a list of known animations from the robot, which will be loaded into anim_list
in the AnimationComponent.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ["AnimationComponent"]

import concurrent

from google.protobuf import text_format

from . import connection, exceptions, util
from .messaging import protocol


class AnimationComponent(util.Component):
    """Play animations on the robot"""

    def __init__(self, robot):
        super().__init__(robot)
        self._anim_dict = {}

    @property
    def anim_list(self):
        """
        Holds the set of animation names (strings) returned from the robot.

        Animation names are dynamically retrieved from the robot when the Python
        script connects to it.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                print("List all animation names:")
                anim_names = robot.anim.anim_list
                for anim_name in anim_names:
                    print(anim_name)
        """
        if not self._anim_dict:
            self.logger.warning("Anim list was empty. Lazy-loading anim list now.")
            result = self.load_animation_list()
            if isinstance(result, concurrent.futures.Future):
                result.result()
        return list(self._anim_dict.keys())

    async def _ensure_loaded(self):
        """
        This is an optimization for the case where a user doesn't
        need the animation_list. This way, connections aren't delayed
        by the load_animation_list call.

        If this is invoked inside another async function then we
        explicitly await the result.
        """
        if not self._anim_dict:
            self.logger.warning("Anim list was empty. Lazy-loading anim list now.")
            await self._load_animation_list()

    async def _load_animation_list(self):
        req = protocol.ListAnimationsRequest()
        result = await self.grpc_interface.ListAnimations(req)
        self.logger.debug(f"Animation List status={text_format.MessageToString(result.status, as_one_line=True)}, number of animations={len(result.animation_names)}")
        self._anim_dict = {a.name: a for a in result.animation_names}
        return result

    @connection.on_connection_thread(log_messaging=False, requires_control=False)
    async def load_animation_list(self):
        """Request the list of animations from the robot

        When the request has completed, anim_list will be populated with
        the list of animations the robot knows how to run.

        .. testcode::

            import anki_vector

            with anki_vector.AsyncRobot() as robot:
                anim_request = robot.anim.load_animation_list()
                anim_request.result()
                anim_names = robot.anim.anim_list
                for anim_name in anim_names:
                    print(anim_name)
        """
        return await self._load_animation_list()

    @connection.on_connection_thread()
    async def play_animation(self, anim: str, loop_count: int = 1, ignore_body_track: bool = False, ignore_head_track: bool = False, ignore_lift_track: bool = False):
        """Starts an animation playing on a robot.

        Vector must be off of the charger to play an animation.

        Warning: Specific animations may be renamed or removed in future updates of the app.
            If you want your program to work more reliably across all versions
            we recommend using :meth:`play_animation_trigger` instead. (:meth:`play_animation_trigger` is still in development.)

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                robot.anim.play_animation('anim_turn_left_01')

        :param anim: The animation to play. Can be of type str or :class:`anki_vector.protocol.Animation`.
        :param loop_count: Number of times to play the animation.
        :param ignore_body_track: True to ignore the animation track for Vector's body (i.e. the wheels / treads).
        :param ignore_head_track: True to ignore the animation track for Vector's head.
        :param ignore_lift_track: True to ignore the animation track for Vector's lift.
        """
        animation = anim
        if not isinstance(anim, protocol.Animation):
            await self._ensure_loaded()
            if anim not in self.anim_list:
                raise exceptions.VectorException(f"Unknown animation: {anim}")
            animation = self._anim_dict[anim]
        req = protocol.PlayAnimationRequest(animation=animation,
                                            loops=loop_count,
                                            ignore_body_track=ignore_body_track,
                                            ignore_head_track=ignore_head_track,
                                            ignore_lift_track=ignore_lift_track)
        return await self.grpc_interface.PlayAnimation(req)
