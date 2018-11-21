.. _advanced-tips:

#############
Advanced Tips
#############

.. _moving_between_wifi:

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Moving Vector between WiFi networks
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When you move Vector from one WiFi network to another (using the Vector App),
or if your Vector's IP changes,  you will also need to make some changes to
your SDK setup. To assist in this migration, ``configure.py`` provides a ``-u``
parameter to quickly reconnect to Vector.

To update your connection, you will need to find the IP address on
Vector's face, and the serial number of the robot you are updating.
Then from your terminal run::

    python3 configure.py -u "<your_new_ip>" -s "<your_robot_serial_number>"


^^^^^^^^^^^^^^^^^^^^^^
Using multiple Vectors
^^^^^^^^^^^^^^^^^^^^^^

If your device is configured to use more than one robot, you can specify
which robot you want to use by passing its serial number as a parameter
to the Robot constructor::


  with anki_vector.Robot("00e20142") as robot:        
    robot.anim.play_animation('anim_pounce_success_02')


Alternatively, you can pass a ``--serial`` flag on the command
line, and ``anki_vector.util.parse_command_args`` will parse out
the serial number::

    ./01_hello_world.py --serial 00e20142


^^^^^^^^^^^^^^^^^^^^^
Set ANKI_ROBOT_SERIAL
^^^^^^^^^^^^^^^^^^^^^

In order to avoid entering Vector's serial number for each program run,
you can create environment variable ``ANKI_ROBOT_SERIAL``
and set it to Vector's serial number::

    export ANKI_ROBOT_SERIAL=00e20100


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Set ANKI_ROBOT_HOST and VECTOR_ROBOT_NAME
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When running ``configure.py``, you must provide Vector's ip and name.
To avoid typing these in, you can instead create environment variables
ANKI_ROBOT_HOST and VECTOR_ROBOT_NAME. Then ``configure.py`` will automatically pick
up those settings::

    export ANKI_ROBOT_HOST="192.168.42.42"
    export VECTOR_ROBOT_NAME=Vector-A1B2



----

`Terms and Conditions <https://www.anki.com/en-us/company/terms-and-conditions>`_ and `Privacy Policy <https://www.anki.com/en-us/company/privacy>`_

`Click here to return to the Anki Developer website. <http://developer.anki.com>`_
