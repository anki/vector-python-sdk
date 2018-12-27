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

"""3d Viewer example, with remote control.

This is an example of how you can use the 3D viewer with a program, and the
3D Viewer and controls will work automatically.
"""

import time
import functools
import threading

import anki_vector
from anki_vector.events import Events

target_discovered = False
wake_word_heard = False

try:
    from IPython.terminal.embed import InteractiveShellEmbed
except ImportError:
    sys.exit('Cannot import from ipython: Do `pip3 install ipython` to install')

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
    robot.anim.load_animation_list()
    robot.anim.play_animation('anim_pounce_success_02')

Use Ctrl+D && Ctrl+C to quit.
"""

def main():
  evt = threading.Event()

  def restore_to_normal(robot):
    robot.behavior.conn._has_control = True
    robot.behavior.drive_on_charger()
    robot.motors.set_head_motor(-3.0)
    robot.motors.set_head_motor(0)
    robot.motors.set_lift_motor(0)
    robot.motors.set_wheel_motors(0, 0)
    squint(robot)
    robot.say_text("I'll - be - back.")

  def awaken(robot):
    robot.motors.set_head_motor(9.0)


  def red_eyes(robot):
    robot.behavior.conn._has_control = True
    robot.behavior.set_eye_color(
      hue=9.0, 
      saturation=1.0
    )
    time.sleep(0.03)

  def get_determined(robot):
    red_eyes(robot)
    robot.behavior.conn._has_control = True
    animation = 'anim_eyepose_determined'
    robot.anim.play_animation(animation)

  def squint(robot):
    red_eyes(robot)
    robot.behavior.conn._has_control = True
    animation = 'anim_eyepose_squint'
    robot.anim.play_animation(animation)

  def scowl(robot):
    red_eyes(robot)
    robot.behavior.conn._has_control = True
    animation = 'anim_eyepose_furious'
    robot.anim.play_animation(animation)

  def get_agressive(robot):
    robot.motors.set_lift_motor(9.0)
    time.sleep(0.3)
    robot.motors.set_lift_motor(-9.0)
    squint(robot)

    robot.motors.set_lift_motor(9.0)
    time.sleep(0.3)
    robot.motors.set_lift_motor(-9.0)
    squint(robot)

    robot.motors.set_lift_motor(9.0)
    time.sleep(0.3)
    robot.motors.set_lift_motor(-9.0)
    scowl(robot)

  def on_wake_word(robot, event_type, event):
    get_agressive(robot)
    robot.behavior.conn._has_control = False
    robot.conn.request_control()

    global wake_word_heard
    if not wake_word_heard:
      wake_word_heard = True
      robot.say_text("I only acknowledge commands from skynet.")
      evt.set()


  def on_robot_observed_face(robot, event_type, event):
    global target_discovered
    if not target_discovered:
      target_discovered = True
      scowl(robot)
      robot.say_text("Target identified...resistance is futile.")
      get_agressive(robot)
      evt.set()

  # START HERE
  args = anki_vector.util.parse_command_args()
  ipyshell = InteractiveShellEmbed(banner1='\nvectorsh >>>', exit_msg="Hasta la Vista, Baby.\n")

  with anki_vector.Robot(
    args.serial,
    show_viewer=True,
    show_3d_viewer=True,
    enable_camera_feed=True,
    enable_custom_object_detection=True,
    enable_face_detection=True,
    enable_nav_map_feed=True
  ) as robot:
        
    # Initiate Vectinator
    get_determined(robot)
    awaken(robot)
    robot.say_text('Vectinator Initiated!')
    #robot.behavior.drive_off_charger()

    # Find a Target
    # TODO: Trigger everytime a face is observed
    on_robot_observed_face = functools.partial(on_robot_observed_face, robot)
    robot.events.subscribe(on_robot_observed_face, Events.robot_observed_face)
    robot.say_text('Locating Targets...')
    squint(robot)

    # Initialize Speech
    # TODO: Trigger event everytime, "Hey Vectinator!" is heard
    on_wake_word = functools.partial(on_wake_word, robot)
    robot.events.subscribe(on_wake_word, Events.wake_word)

    # Prototype in real-time
    ipyshell(usage)

    restore_to_normal(robot)
    exit

if __name__ == "__main__":
    main()
