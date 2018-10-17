#!/usr/bin/env python3

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

"""Wait for Vector to see a face, and then print output to the console.

This script demonstrates how to set up a listener for an event. It
subscribes to event 'robot_observed_face'. When that event is dispatched,
method 'on_robot_observed_face' is called, which prints text to the console.
"""

import asyncio
import functools

import anki_vector
from anki_vector.events import Events
from anki_vector.util import degrees


def main():
    def on_robot_observed_face(robot, event_type, event):
        """on_robot_observed_face is called when a face is seen"""
        print("Vector sees a face")

    args = anki_vector.util.parse_command_args()
    with anki_vector.Robot(args.serial, enable_vision_mode=True) as robot:
        # If necessary, Move Vector's Head and Lift to make it easy to see his face
        robot.behavior.set_head_angle(degrees(50.0))
        robot.behavior.set_lift_height(0.0)

        on_robot_observed_face = functools.partial(on_robot_observed_face, robot)
        robot.events.subscribe(on_robot_observed_face, Events.robot_observed_face)

        print("------ waiting for face events, press ctrl+c to exit early ------")

        try:
            # Wait 5 seconds to see a face
            robot.loop.run_until_complete(asyncio.sleep(5))
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
