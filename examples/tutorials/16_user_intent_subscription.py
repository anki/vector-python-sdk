#!/usr/bin/env python3

# Copyright (c) 2019 Anki, Inc.
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

"""Return information about a voice commands given to Vector

The user_intent event is only dispatched when the SDK program has
requested behavior control and Vector gets a voice command.

After the robot hears "Hey Vector! ..." and a valid voice command is given
(for example "...what time is it?") the event will be dispatched and displayed.
"""

import threading

import anki_vector
from anki_vector.events import Events
from anki_vector.user_intent import UserIntent


def main():
    def on_user_intent(robot, event_type, event, done):
        user_intent = UserIntent(event)
        print(f"Received {user_intent.intent_event}")
        print(user_intent.intent_data)
        done.set()

    args = anki_vector.util.parse_command_args()
    with anki_vector.Robot(args.serial) as robot:
        done = threading.Event()
        robot.events.subscribe(on_user_intent, Events.user_intent, done)

        print('------ Vector is waiting for a voice command like "Hey Vector!  What time is it?" Press ctrl+c to exit early ------')

        try:
            if not done.wait(timeout=10):
                print('------ Vector never heard a voice command ------')
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
