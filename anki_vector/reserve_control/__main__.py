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

""" Reserve SDK Behavior Control

While this script runs, other SDK scripts may run and Vector will not perform most
default behaviors before/after they complete.  This will keep Vector still.

High priority behaviors like returning to the charger in a low battery situation,
or retreating from a cliff will still take precedence.
"""

from anki_vector import behavior, util


def hold_control():
    args = util.parse_command_args()
    with behavior.ReserveBehaviorControl(args.serial):
        input("Vector behavior control reserved for SDK.  Hit 'Enter' to release control.")


if __name__ == "__main__":
    hold_control()
