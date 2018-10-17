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


^^^^^^^^^^^^^^^^^^^^^^^^^^^
Failure to run configure.py
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The prerequisites to run ``configure.py`` are:

* Vector is powered on.
* You have successfully created an Anki account.
* Vector has been set up with the Vector companion app.
* You have updated Vector to OS 1.0.1 or later. Check the OS version by putting Vector on the charger, double-tapping his backpack button, and raising and lowering his arms once.
* The Vector companion app is *not* currently connected to Vector.
* Vector is connected to the same network as your computer.
* You can see Vector's eyes on his screen.


^^^^^^^^^^^^^^^^^^^^^
Can't find robot name
^^^^^^^^^^^^^^^^^^^^^

Your Vector robot name looks like "Vector-E5S6". Find your robot name by placing Vector on the charger and double-clicking Vector's backpack button.


^^^^^^^^^^^^^^^^^^^^^^^^
Can't find serial number
^^^^^^^^^^^^^^^^^^^^^^^^

Your Vector's serial number looks like "00e20142". Find your robot serial number on the underside of Vector. Or, find the serial number from Vector's debug screen: double-click his backpack, move his arms up and down, then look for "ESN" on his screen.


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Can't find Vector's ip address
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Your Vector ip address looks like "192.168.40.134". Find the ip address from Vector's debug screen: double-click his backpack, move his arms up and down, then look for "IP" on his screen.


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Tutorial program does not run
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Before running a program, be sure that you can see Vector's eyes. The robot should not be displaying another screen.


^^^^^^^^^^^^^^^
Anki SDK Forums
^^^^^^^^^^^^^^^

Please visit the `Anki SDK Forums <https://forums.anki.com/>`_ to ask questions, find solutions and for general discussion.

----

`Terms and Conditions <https://www.anki.com/en-us/company/terms-and-conditions>`_ and `Privacy Policy <https://www.anki.com/en-us/company/privacy>`_

`Click here to return to the Anki Developer website. <http://developer.anki.com>`_
