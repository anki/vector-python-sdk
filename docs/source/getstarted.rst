===================================
Getting Started With the Vector SDK
===================================

To make sure you get the best experience possible out of the SDK, please ensure you have followed the steps in the :doc:`Initial Setup </initial>`.

-----------------
Anki SDK Forums
-----------------

Please visit our `Anki SDK Forums <https://forums.anki.com/>`_ where you can:

* Get assistance with your code

* Hear about upcoming SDK additions

* Share your work

* Join discussion about the SDK

* Be a part of the Vector SDK Community!


-------------------
Starting Up the SDK
-------------------

1. On the computer, open Terminal (macOS/Linux) or Command Prompt (Windows) and type ``cd vector-sdk``, and press **Enter**.

----------------
Example Program
----------------

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
First Steps - "Hello, World!"
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Let's test your new setup by running a very simple program. This program instructs Vector to say "Hello, World!" - a perfect way to introduce him and you to the world of programming.

"""""""""""
The Program
"""""""""""

1. Please find your robot serial number (ex. 00e20100) located on the underside of Vector, or accessible from Vector's debug screen.

2. Run the program using the same Terminal (macOS/Linux) / Command Prompt (Windows) window mentioned above: 

First, change to the ``tutorials`` sub-directory of the ``examples`` directory.

    a. For macOS and Linux systems, type the following and press **Enter**::

        cd examples/tutorials

    b. For Windows systems, type the following and press **Enter**::

        cd examples\tutorials

Then, run the program.

    a. For macOS and Linux systems, type the following and press **Enter**::

        ./01_hello_world.py --serial {robot_serial_number}

    The same can also be achieved on macOS/Linux with:
	
        python3 01_hello_world.py --serial {robot_serial_number}

    b. For Windows systems, type the following and press **Enter**::

        py 01_hello_world.py --serial {robot_serial_number}

3. If done correctly, Vector will say "Hello, World!"

.. warning:: If Vector does not perform as expected, look at the first Terminal window and make sure no error messages appeared. If you continue to have issues, please seek help in the Forums.

You are now all set up to run Python programs on Vector.



Now that you have run your own Vector program, take a look at the rest of the Vector SDK and at the many other example programs to get more ideas.

`Terms and Conditions <https://www.anki.com/en-us/company/terms-and-conditions>`_ and `Privacy Policy <https://www.anki.com/en-us/company/privacy>`_

`Click here to return to the Anki Developer website. <http://developer.anki.com>`_
