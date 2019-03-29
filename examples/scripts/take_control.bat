:: This file is provided as a convenience for initiating reserved behavior
:: control for SDK scripts.  Windows users can double-click on this file in
:: Windows Explorer to open a cmd.exe window and execute a Python script so
:: that most default behaviors will be suppressed before/after other SDK
:: scripts execute.  This will keep Vector still between SDK scripts.
::
:: Allowing the script to complete or closing the cmd.exe window will
:: restore behavior control to the robot.

start python -m anki_vector.reserve_control
