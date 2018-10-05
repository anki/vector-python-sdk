.. _troubleshooting:

###############
Troubleshooting
###############


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Failure to Install Python Package
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If your attempt to install Python packages such as opencv-python fails, please upgrade your pip install as follows:

    On macOS and Linux::

        pip3 install -U pip

    On Windows::

        python -m pip install --upgrade pip

    Alternatively on Windows, try::

        py -3 -m pip install --upgrade pip

    On Windows you may also need to update Python setuptools::

        pip install --upgrade setuptools

    Once the pip command is upgraded, retry your Python package installation.


^^^^^^^^^^^^^^^^^^^^^^^^^^^
Failure to run configure.py
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The prerequisites to run `configure.py` are:
* Vector must be powered on.
* You have successfully created an Anki account.
* Vector has been set up with the Vector companion app.
* Vector is connected to the same network as your computer.
* You can see Vector's eyes on his screen.


^^^^^^^^^^^^^^^^^^^^^^^^^^^
How to find your robot name
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Your Vector robot name looks like "Vector-E5S6". Find your robot name by placing Vector on the charger and double clicking Vector's backpack button.


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
How to find your robot serial number
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Your Vector serial number looks like "00e20142". Find your robot serial number on the underside of Vector. Or, find the serial number from Vector's debug screen: double click his backpack, move his arms up and down, then look for "ESN" on his screen.


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
How to find your robot ip address
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Your Vector ip address looks like "192.168.40.134". Find the ip address from Vector's debug screen: double click his backpack, move his arms up and down, then look for "IP" on his screen.



^^^^^^^^^^^^^^^^
Anki SDK Forums
^^^^^^^^^^^^^^^^

Please visit the `Anki SDK Forums <https://forums.anki.com/>`_ to ask questions, find solutions and for general discussion.

----

`Terms and Conditions <https://www.anki.com/en-us/company/terms-and-conditions>`_ and `Privacy Policy <https://www.anki.com/en-us/company/privacy>`_

`Click here to return to the Anki Developer website. <http://developer.anki.com>`_
