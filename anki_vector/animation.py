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

There are two ways to play an animation on Vector: play_animation_trigger and play_animation. For play_animation_trigger, you select
a pre-defined group of animations, and the robot will choose which animation from the group to run when you execute the method. When
calling play_animation, you select the specific animation you want the robot to run. We advise you to use play_animation_trigger instead
of play_animation, since individual animations can be deleted between Vector OS versions.

By default, when an SDK program starts, the SDK will request a list of known animation triggers and animations from the robot, which will be loaded
and available from anim_list_triggers and anim_list, respectively, in the AnimationComponent.
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
        self._anim_trigger_dict = {}

    @property
    def anim_list(self):
        """
        Holds the set of animation names (strings) returned from the robot.

        Animation names are dynamically retrieved from the robot when the Python
        script connects to it.

        Warning: Specific animations may be renamed or removed in future updates of the app.
        If you want your program to work more reliably across all versions
        we recommend using anim_trigger_list and :meth:`play_animation_trigger` instead.

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

    @property
    def anim_trigger_list(self):
        """
        Holds the set of animation trigger names (strings) returned from the robot.

        Animation trigger names are dynamically retrieved from the robot when the Python
        script connects to it.

        Playing an animation trigger causes the robot to play an animation of a particular type.

        The robot may pick one of a number of actual animations to play based on
        Vector's mood or emotion, or with random weighting.  Thus playing the same
        trigger twice may not result in the exact same underlying animation playing
        twice.

        To play an exact animation, use :meth:`play_animation`.

        This property holds the set of defined animations triggers to pass to :meth:`play_animation_trigger`.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                print("List all animation trigger names:")
                anim_trigger_names = robot.anim.anim_trigger_list
                for anim_trigger_name in anim_trigger_names:
                    print(anim_trigger_name)
        """
        if not self._anim_trigger_dict:
            self.logger.warning("Anim trigger list was empty. Lazy-loading anim trigger list now.")
            result = self.load_animation_trigger_list()
            if isinstance(result, concurrent.futures.Future):
                result.result()
        return list(self._anim_trigger_dict.keys())

    async def _ensure_loaded(self):
        """
        This is an optimization for the case where a user doesn't
        need the animation_trigger_list or the animation_list. This way,
        connections aren't delayed by the load_animation_triggers_list and
        load_animation_list calls.

        If this is invoked inside another async function then we
        explicitly await the result.
        """
        if not self._anim_dict:
            self.logger.warning("Anim list was empty. Lazy-loading anim list now.")
            await self._load_animation_list()
        if not self._anim_trigger_dict:
            self.logger.warning("Anim trigger list was empty. Lazy-loading anim trigger list now.")
            await self._load_animation_trigger_list()

    async def _load_animation_list(self):
        req = protocol.ListAnimationsRequest()
        result = await self.grpc_interface.ListAnimations(req)
        self.logger.debug(f"Animation List status={text_format.MessageToString(result.status, as_one_line=True)}, number of animations={len(result.animation_names)}")
        self._anim_dict = {a.name: a for a in result.animation_names}
        return result

    async def _load_animation_trigger_list(self):
        req = protocol.ListAnimationTriggersRequest()
        result = await self.grpc_interface.ListAnimationTriggers(req)
        self.logger.debug(f"Animation Triggers List status={text_format.MessageToString(result.status, as_one_line=True)}, number of animation_triggers={len(result.animation_trigger_names)}")
        self._anim_trigger_dict = {a.name: a for a in result.animation_trigger_names}
        return result

    @connection.on_connection_thread(log_messaging=False, requires_control=False)
    async def load_animation_list(self):
        """Request the list of animations from the robot.

        When the request has completed, anim_list will be populated with
        the list of animations the robot knows how to run.

        Warning: Specific animations may be renamed or removed in future updates of the app.
        If you want your program to work more reliably across all versions
        we recommend using animation triggers instead. See :meth:`play_animation_trigger`.

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

    @connection.on_connection_thread(log_messaging=False, requires_control=False)
    async def load_animation_trigger_list(self):
        """Request the list of animation triggers from the robot.

        When the request has completed, anim_trigger_list will be populated with
        the list of animation triggers the robot knows how to run.

        Playing a trigger requests that an animation of a certain class starts playing, rather than an exact
        animation name.

        .. testcode::

            import anki_vector

            with anki_vector.AsyncRobot() as robot:
                anim_trigger_request = robot.anim.load_animation_trigger_list()
                anim_trigger_request.result()
                anim_trigger_names = robot.anim.anim_trigger_list
                for anim_trigger_name in anim_trigger_names:
                    print(anim_trigger_name)
        """
        return await self._load_animation_trigger_list()

    @connection.on_connection_thread()
    async def play_animation_trigger(self, anim_trigger: str, loop_count: int = 1, use_lift_safe: bool = False, ignore_body_track: bool = False, ignore_head_track: bool = False, ignore_lift_track: bool = False):  # START
        """Starts an animation trigger playing on a robot.

        Playing a trigger requests that an animation of a certain class starts playing, rather than an exact
        animation name.

        Vector must be off of the charger to play an animation.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                robot.anim.play_animation_trigger('GreetAfterLongTime')

        :param trigger: The animation trigger to play. Can be of type str or :class:`anki_vector.protocol.AnimationTrigger`.
        :param loop_count: Number of times to play the animation.
        :param use_lift_safe: True to automatically ignore the lift track if Vector is currently carrying an object.
        :param ignore_body_track: True to ignore the animation track for Vector's body (i.e. the wheels / treads).
        :param ignore_head_track: True to ignore the animation track for Vector's head.
        :param ignore_lift_track: True to ignore the animation track for Vector's lift.
        """
        animation_trigger = anim_trigger
        if not isinstance(anim_trigger, protocol.AnimationTrigger):
            await self._ensure_loaded()
            if anim_trigger not in self.anim_trigger_list:
                raise exceptions.VectorException(f"Unknown animation trigger: {anim_trigger}")
            animation_trigger = self._anim_trigger_dict[anim_trigger]
        req = protocol.PlayAnimationTriggerRequest(animation_trigger=animation_trigger,
                                                   loops=loop_count,
                                                   use_lift_safe=use_lift_safe,
                                                   ignore_body_track=ignore_body_track,
                                                   ignore_head_track=ignore_head_track,
                                                   ignore_lift_track=ignore_lift_track)
        return await self.grpc_interface.PlayAnimationTrigger(req)

    @connection.on_connection_thread()
    async def play_animation(self, anim: str, loop_count: int = 1, ignore_body_track: bool = False, ignore_head_track: bool = False, ignore_lift_track: bool = False):
        """Starts an animation playing on a robot.

        Vector must be off of the charger to play an animation.

        Warning: Specific animations may be renamed or removed in future updates of the app.
            If you want your program to work more reliably across all versions
            we recommend using :meth:`play_animation_trigger` instead.

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
