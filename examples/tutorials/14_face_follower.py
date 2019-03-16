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

"""Make Vector turn toward a face.

This script shows off the turn_towards_face behavior. It will wait for a face
and then constantly turn towards it to keep it in frame.
"""

import anki_vector
from anki_vector.events import Events
from anki_vector.util import degrees
import time

def main():
    args = anki_vector.util.parse_command_args()
    with anki_vector.AsyncRobot(args.serial, enable_face_detection=True, show_viewer=True) as robot:
        robot.behavior.drive_off_charger()

        # If necessary, move Vector's Head and Lift to make it easy to see his face
        robot.behavior.set_head_angle(degrees(45.0))
        robot.behavior.set_lift_height(0.0)

        face_to_follow = None

        print("------ show vector your face, press ctrl+c to exit early ------")
        try:        
            while True:
                turn_future = None
                if face_to_follow:
                    # start turning towards the face
                    turn_future = robot.behavior.turn_towards_face(face_to_follow)

                if not (face_to_follow and face_to_follow.is_visible):
                    # find a visible face, timeout if nothing found after a short while
                    for face in robot.world.visible_faces:
                        face_to_follow = face
                        break

                if turn_future != None:
                    # Complete the turn action if one was in progress
                    turn_future.result()

                time.sleep(.1)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()
