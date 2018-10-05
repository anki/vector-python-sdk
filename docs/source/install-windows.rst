.. _install-windows:

######################
Installation - Windows
######################

This guide provides instructions on installing the Vector SDK for computers running with a Windows operating system.

^^^^^^^^^^^^^
Prerequisites
^^^^^^^^^^^^^

* Vector is powered on.
* You have successfully created an Anki account.
* Vector has been set up with the Vector companion app.
* Vector is connected to the same network as your computer.
* You can see Vector's eyes on his screen.


^^^^^^^^^^^^^^^^^^^
Python Installation
^^^^^^^^^^^^^^^^^^^


Download the `Python 3.6.1 (or later) executable file from Python.org <https://www.python.org/downloads/windows/>`_ and
run it on your computer.

.. important:: Be sure to tick the "Add Python 3.6 to PATH" checkbox on the Setup screen. Then tap "Install Now" and complete the Python installation.

^^^^^^^^^^^^^^^^
SDK Installation
^^^^^^^^^^^^^^^^

To install the SDK, type the following into a Command Prompt window::

    cd vector-sdk
    pip3 install --user vector-0.4-py3-none-any.whl

.. note:: If you encounter an error during SDK installation, you may need to upgrade your pip install. Try `python -m pip install --upgrade pip` or `py -3 -m pip install --upgrade pip`

.. note:: If you encounter an error during SDK installation, you may need to upgrade your Python Setuptools. Try `py -3 -m pip install --upgrade setuptools`

^^^^^^^^^^^^^^^^^^^^^
Vector Authentication
^^^^^^^^^^^^^^^^^^^^^

To authenticate with the robot, type the following into the Terminal window::

    cd vector-sdk
    py configure.py

You will be prompted for your robot's name, ip address and serial number. You will also be asked for your Anki login and password.

.. note:: Running `configure.py` will automatically download the Vector robot certificate to your computer and store credentials to allow you to connect to Vector. These credentials will be stored under your home directory in folder `.anki_vector`.

.. warning:: These credentials give full access to your robot, including camera stream, audio stream and data. Do not share these credentials.

^^^^^^^^^^^^^^^^^^
Extra Dependencies
^^^^^^^^^^^^^^^^^^

There are a few extra packages that must be installed to run the experimental examples. To install these dependencies, enter this command::

    cd vector-sdk
    pip3 install .[experimental]

^^^^^^^^^^^^^^^
Troubleshooting
^^^^^^^^^^^^^^^

Please see the :doc:`Troubleshooting </troubleshooting>` page for tips, or visit the `Anki SDK Forums <https://forums.anki.com/>`_ to ask questions, find solutions, or for general discussion.

----

`Terms and Conditions <https://www.anki.com/en-us/company/terms-and-conditions>`_ and `Privacy Policy <https://www.anki.com/en-us/company/privacy>`_

`Click here to return to the Anki Developer website. <http://developer.anki.com>`_
