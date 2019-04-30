.. _advanced-tips:

#############
Advanced Tips
#############

.. _moving_between_wifi:

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Moving Vector between WiFi networks
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When you move Vector from one WiFi network to another (using the Vector App),
or if your Vector's IP changes, the SDK will need to determine Vector's new IP address.
There are two ways to accomplish this. 

****************************
1. Automatic: mDNS Discovery
****************************

The SDK will automatically discover your Vector, even on a new WiFi network, 
when you connect as follows::

    import anki_vector

    with anki_vector.Robot(name="Vector-A1B2") as robot:
        # The sdk will try to connect to 'Vector A1B2', 
        # even if its IP address has changed. 
        pass

You will need to install the ``zeroconf`` package to use this feature::

    pip3 install --user zeroconf

*******************************
2. Manual: Update Configuration
*******************************

Alternatively, you can manually make changes to your SDK setup. To assist in this migration, the ``anki_vector.configure``
executable submodule provides a ``-u`` parameter to quickly reconnect to Vector.

To update your connection, you will need to find the IP address on
Vector's face, and the serial number of the robot you are updating.
Then from your terminal run::

    python3 -m anki_vector.configure -u "<your_new_ip>" -s "<your_robot_serial_number>"


^^^^^^^^^^^^^^^^^^^^^^
Using multiple Vectors
^^^^^^^^^^^^^^^^^^^^^^

If your device is configured to use more than one robot, you can specify
which robot you want to use by passing its serial number as a parameter
to the Robot constructor::


  with anki_vector.Robot("00e20142") as robot:
    robot.anim.play_animation_trigger("GreetAfterLongTime")


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

When running the ``anki_vector.configure`` executable submodule, you must provide Vector's ip and name.
To avoid typing these in, you can instead create environment variables
ANKI_ROBOT_HOST and VECTOR_ROBOT_NAME. Then ``anki_vector.configure`` will automatically pick
up those settings::

    export ANKI_ROBOT_HOST="192.168.42.42"
    export VECTOR_ROBOT_NAME=Vector-A1B2

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Keeping Vector Still Between SDK Scripts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Vector can be controlled so that (like Cozmo) he will not move between SDK scripts.  There are three options for entering this mode of operation:

* Control can be reserved from the command prompt: ``python3 -m anki_vector.reserve_control``  Vector will remain still between SDK scripts until the script/process is exited.
* There are OS-specific scripts (Mac/Win) in the ``examples/scripts/`` folder that can be double-clicked to more easily reserve behavior control.  The script will open in a new window; closing the window or otherwise stopping the script will release control back to the built-in robot behaviors.
* A single Python file can explicitly reserve control using the ``ReserveBehaviorControl`` object.  Consult the ``anki_vector.connection`` `documentation <https://developer.anki.com/vector/docs/generated/anki_vector.connection.html>`_ for more information.

While normal robot behaviors are suppressed, Vector may look 'broken'.  Closing the SDK scripts, disconnecting from the
robot, or restarting the robot will all release behavior control.



----

`Terms and Conditions <https://www.anki.com/en-us/company/terms-and-conditions>`_ and `Privacy Policy <https://www.anki.com/en-us/company/privacy>`_

`Click here to return to the Anki Developer website. <https://developer.anki.com>`_
