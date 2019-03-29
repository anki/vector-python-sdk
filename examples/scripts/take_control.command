#!/bin/bash
# This file is provided as a convenience for initiating reserved behavior
# control for SDK scripts.  Mac users can double-click on this file in
# the Finder to open a Terminal window and execute a Python script so
# that most default behaviors will be suppressed before/after other SDK
# scripts execute.  This will keep Vector still between SDK scripts.
#
# Allowing the script to complete or closing the Terminal window will
# restore behavior control to the robot.

python3 -m anki_vector.reserve_control
