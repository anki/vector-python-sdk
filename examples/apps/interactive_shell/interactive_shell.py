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
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Command Line Interface for Vector

This is an example of integrating Vector with an ipython-based command line interface.
"""

import sys

try:
    from IPython.terminal.embed import InteractiveShellEmbed
except ImportError:
    sys.exit('Cannot import from ipython: Do `pip3 install ipython` to install')

import anki_vector

usage = """Use the [tab] key to auto-complete commands, and see all available methods and properties.

For example, type 'robot.' then press the [tab] key and you'll see all the robot functions.
Keep pressing tab to cycle through all of the available options.

All IPython commands work as usual.
Here's some useful syntax:
  robot?   -> Details about 'robot'.
  robot??  -> More detailed information including code for 'robot'.
These commands will work on all objects inside of the shell.

You can even call the functions that send messages to Vector, and he'll respond just like he would in a script.
Try it out! Type:
    robot.anim.play_animation_trigger('GreetAfterLongTime')
"""

args = anki_vector.util.parse_command_args()

ipyshell = InteractiveShellEmbed(banner1='\nWelcome to the Vector Interactive Shell!',
                                 exit_msg='Goodbye\n')

if __name__ == "__main__":
    with anki_vector.Robot(args.serial,
                           show_viewer=True) as robot:
        # Invoke the ipython shell while connected to Vector
        ipyshell(usage)
