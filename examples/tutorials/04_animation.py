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

"""Play an animation on Vector

Play an animation by name.
"""

import anki_vector


def main():
    args = anki_vector.util.parse_test_args()
    with anki_vector.Robot(args.serial, port=args.port) as robot:
        robot.behavior.drive_off_charger()

        # Play an animation via its name.
        #
        # Warning: Future versions of the app might change these, so for future-proofing
        # we recommend using play_animation_trigger when it becomes available.
        #
        # See the remote_control_cozmo.py example in apps for an easy way to see
        # the available animations.
        animation = 'anim_pounce_success_02'
        print("Playing animation by name: " + animation)
        robot.anim.play_animation(animation)


if __name__ == "__main__":
    main()
