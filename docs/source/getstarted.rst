===================================
Getting Started With the Vector SDK
===================================

To make sure you get the best experience possible out of the SDK, please ensure you have followed the steps in the :doc:`Initial Setup </initial>`.

---------------------
Anki Developer Forums
---------------------

Please visit our `Anki Developer Forums <https://forums.anki.com/>`_ where you can:

* Get assistance with your code

* Hear about upcoming SDK additions

* Share your work

* Join discussion about the SDK

* Be a part of the Vector SDK Community!


-------------
Prerequisites
-------------

* You have completed the Installation steps, found here: :ref:`initial`
* You have downloaded and extracted the example programs, found here: :doc:`Downloads </downloads>`
* The Vector companion app is *not* currently connected to Vector.
* Vector is connected to the same network as your computer.
* You can see Vector's eyes on his screen.

-------------------
Starting Up the SDK
-------------------

On the computer, open Terminal (macOS/Linux) or Command Prompt (Windows) and type ``cd anki_vector_sdk_examples``, where *anki_vector_sdk_examples* is the directory you extracted the examples into, and press **Enter**.

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

1. Run the program using the same Terminal (macOS/Linux) / Command Prompt (Windows) window mentioned above. First, change to the ``tutorials`` sub-directory::

        cd tutorials

Then, run the program.

    a. For macOS and Ubuntu 18.04 systems, type the following and press **Enter**::

        ./01_hello_world.py

    The same can also be achieved with::
	
        python3 01_hello_world.py

    b. For Windows systems, type the following and press **Enter**::

        py 01_hello_world.py

    c. For Ubuntu 16.04 systems, type the following and press **Enter**::

        python3.6 01_hello_world.py


2. If done correctly, Vector will say "Hello, World!"

.. warning:: If Vector does not perform as expected, look at the first Terminal window and make sure no error messages appeared. If you continue to have issues, please seek help in the Forums.

.. note:: If you have more than one Vector configured on your device, you can pass the serial number of the Vector you want to use at the command line:
    ``./01_hello_world.py --serial {robot_serial_number}``


You are now all set up to run Python programs on Vector.



Now that you have run your own Vector program, take a look at the rest of the Vector SDK and at the many other example programs to get more ideas.

`Terms and Conditions <https://www.anki.com/en-us/company/terms-and-conditions>`_ and `Privacy Policy <https://www.anki.com/en-us/company/privacy>`_

`Click here to return to the Anki Developer website. <https://developer.anki.com>`_
