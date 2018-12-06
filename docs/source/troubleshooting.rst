.. _troubleshooting:

###############
Troubleshooting
###############


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Failure to Install Python Package
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you run into trouble installing Python packages, please upgrade your pip install as follows:

    On macOS and Linux::

        pip3 install -U pip

    On Windows::

        python -m pip install --upgrade pip

    Alternatively on Windows, try::

        py -3 -m pip install --upgrade pip

    You may also need to update Python setuptools (for instance, for error ``AttributeError: '_NamespacePath' object has no attribute 'sort'``)::

        pip install --upgrade setuptools

    After applying these updates, retry your Python package installation.


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Tutorial program does not run
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Before running a Python program, be sure you can see Vector's eyes. If instead you see an image of a mobile device, the Customer Care Info screen, a missing Wifi icon, or something else, please complete setup of your Vector first and then you will be ready set up the SDK.

Also, check whether Vector's IP address has changed since the last time you ran ``anki_vector.configure``. If so, see :ref:`moving_between_wifi` to set up the robot with the new IP address.


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Failure to run anki_vector.configure
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The prerequisites to run the ``anki_vector.configure`` executable submodule successfully are:

* You have successfully created an Anki account.
* Vector has been set up with the Vector companion app.
* The Vector companion app is *not* currently connected to Vector.
* Vector is connected to the same network as your computer.
* The ``anki_vector`` Python package must be installed.
* You can see Vector's eyes on his screen.


^^^^^^^^^^^^^^^^^^^^^^^^^^^
Vector behaves unexpectedly
^^^^^^^^^^^^^^^^^^^^^^^^^^^

You may need to reboot your robot when you are finished running programs with the pre-alpha Vector SDK.


^^^^^^^^^^^^^^^^^^^^^
Can't find robot name
^^^^^^^^^^^^^^^^^^^^^

Your Vector robot name looks like "Vector-E5S6". Find your robot name by placing Vector on the charger and double-clicking Vector's backpack button.


^^^^^^^^^^^^^^^^^^^^^^^^
Can't find serial number
^^^^^^^^^^^^^^^^^^^^^^^^

Your Vector's serial number looks like "00e20142". Find your robot serial number on the underside of Vector. Or, find the serial number from Vector's debug screen: double-click his backpack, move his arms up and down, then look for "ESN" on his screen.


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Can't find Vector's IP address
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Your Vector IP address looks like "192.168.40.134". Find the IP address from Vector's debug screen: double-click his backpack, move his arms up and down, then look for "IP" on his screen.


^^^^^^^^^^^^^^^^^^^^^
Anki Developer Forums
^^^^^^^^^^^^^^^^^^^^^

Please visit the `Anki Developer Forums <https://forums.anki.com/>`_ to ask questions, find solutions and for general discussion.

----

`Terms and Conditions <https://www.anki.com/en-us/company/terms-and-conditions>`_ and `Privacy Policy <https://www.anki.com/en-us/company/privacy>`_

`Click here to return to the Anki Developer website. <https://developer.anki.com>`_
