#!/usr/bin/env python3

# Copyright (c) 2018 Anki, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the file LICENSE.txt or at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License isvi distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Play audio files through Vector's speaker.
"""

import anki_vector


def main():
    args = anki_vector.util.parse_command_args()
    with anki_vector.Robot(args.serial) as robot:
        # You can find these sounds files here:
        # https://github.com/anki/vector-python-sdk/blob/master/examples/sounds/vector_alert.wav
        # https://github.com/anki/vector-python-sdk/blob/master/examples/sounds/vector_bell_whistle.wav
        #
        # Paste these two wav files next to this tutorial to play sounds.
        robot.audio.stream_wav_file("vector_bell_whistle.wav", 75)
        robot.audio.stream_wav_file("vector_alert.wav", 75)


if __name__ == "__main__":
    main()
