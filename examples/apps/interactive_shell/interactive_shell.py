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

"""Command Line Interface for Vector

This is an example of integrating Vector with an ipython-based command line interface.
"""

import sys

try:
    from IPython.terminal.embed import InteractiveShellEmbed
except ImportError:
    sys.exit('Cannot import from ipython: Do `pip3 install ipython` to install')

import anki_vector

usage = ('This is an IPython interactive shell for Vector.\n'
         'All commands are executed within Vector\'s running connection loop.\n'
         'Use the [tab] key to auto-complete commands, and see all available methods.\n'
         'All IPython commands work as usual. See below for some useful syntax:\n'
         '  ?         -> Introduction and overview of IPython\'s features.\n'
         '  object?   -> Details about \'object\'.\n'
         '  object??  -> More detailed, verbose information about \'object\'.')

args = anki_vector.util.parse_test_args()

ipyshell = InteractiveShellEmbed(banner1='\nWelcome to the Vector Shell!',
                                 exit_msg='Goodbye\n')


with anki_vector.Robot(args.serial, port=args.port) as robot:
    # Invoke the ipython shell while connected to Vector
    ipyshell(usage)
