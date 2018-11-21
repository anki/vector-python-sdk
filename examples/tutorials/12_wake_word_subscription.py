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

"""Wait for Vector to hear "Hey Vector!" and then play an animation.

The wake_word event only is dispatched when the SDK program has
not requested behavior control. After the robot hears "Hey Vector!"
and the event is received, you can then request behavior control
and control the robot. See the 'requires_behavior_control' method in
connection.py for more information.
"""


import threading

import anki_vector
from anki_vector.events import Events

wake_word_heard = False


def main():
    args = anki_vector.util.parse_command_args()
    with anki_vector.Robot(args.serial, requires_behavior_control=False, cache_animation_list=False) as robot:
        evt = threading.Event()

        async def on_wake_word(event_type, event):
            await robot.conn.request_control()

            global wake_word_heard
            if not wake_word_heard:
                wake_word_heard = True
                await robot.say_text("Hello")
                evt.set()

        robot.events.subscribe(on_wake_word, Events.wake_word)

        print('------ Vector is waiting to hear "Hey Vector!" Press ctrl+c to exit early ------')

        try:
            if not evt.wait(timeout=10):
                print('------ Vector never heard "Hey Vector!" ------')
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
