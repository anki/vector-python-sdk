.. _install-macos:

###########################
Installation - macOS / OS X
###########################

This guide provides instructions on installing the Vector SDK for computers running with a macOS operating system.

^^^^^^^^^^^^^
Prerequisites
^^^^^^^^^^^^^

* Vector is powered on.
* You have successfully created an Anki account.
* Vector has been set up with the Vector companion app.
* You have updated Vector to OS 1.0.1 or later. Check the OS version by putting Vector on the charger, double-tapping his backpack button, and raising and lowering his arms once.
* The Vector companion app is *not* currently connected to Vector.
* Vector is connected to the same network as your computer.
* You can see Vector's eyes on his screen.


^^^^^^^^^^^^^^^^^^^
Python Installation
^^^^^^^^^^^^^^^^^^^

1. Install `Homebrew <http://brew.sh>`_ on your system according to the latest instructions. If you already had brew installed then update it by opening a Terminal window and typing in the following::

    brew update

2. Once Homebrew is installed and updated, type the following into the Terminal window to install the latest version of Python 3::

    brew install python3

The Vector SDK supports Python 3.6.1 or later.


^^^^^^^^^^^^^^^^
SDK Installation
^^^^^^^^^^^^^^^^

To install the SDK, navigate into the SDK folder and type the following into a Terminal window::

    cd vector_python_sdk_0.4.0
    python3 -m pip install .

^^^^^^^^^^^^^^^^^^^^^
Vector Authentication
^^^^^^^^^^^^^^^^^^^^^

To authenticate with the robot, type the following into the Terminal window::

    cd vector_python_sdk_0.4.0
    ./configure.py

You will be prompted for your robot's name, ip address and serial number. You will also be asked for your Anki login and password. Make sure to use the same account that was used to set up your Vector.

You will see "SUCCESS!" when this script successfully completes.

.. note:: Running ``configure.py`` will automatically download the Vector robot certificate to your computer and store credentials to allow you to connect to Vector. These credentials will be stored under your home directory in folder ``.anki_vector``.

.. warning:: These credentials give full access to your robot, including camera stream, audio stream and data. Do not share these credentials.

^^^^^^^^^^^^^^^
Troubleshooting
^^^^^^^^^^^^^^^

Please see the :doc:`Troubleshooting </troubleshooting>` page for tips, or visit the `Anki SDK Forums <https://forums.anki.com/>`_ to ask questions, find solutions, or for general discussion.

----

`Terms and Conditions <https://www.anki.com/en-us/company/terms-and-conditions>`_ and `Privacy Policy <https://www.anki.com/en-us/company/privacy>`_

`Click here to return to the Anki Developer website. <http://developer.anki.com>`_
