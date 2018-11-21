# Anki Vector - Python SDK

## Getting Started

Before connecting, you will need:

* Vector's Name: This is the name displayed on his face for BLE pairing after you double-click while Vector is on the charger. Example: `Vector-A1B2`
* Vector's IP Address: The ip address can be found by first placing Vector on the charger, then double-clicking the button on his back, and finally raising and lowering his arms. It is possible for your ip to change based on your network settings, so it must be updated accordingly. Example: `192.168.43.48`
* Vector's Serial Number: You may find this number on the underside of your robot. Example: `00e20115`

These will be needed to run the configure.py script and set up authentication from your device to your Vector.

Your device must have Python 3.6.1 or later installed. Please see the documentation pages mentioned below for instructions to install Python.


---

Check out the documentation for setup instructions by opening docs/build/html/index.html in your browser.

---

During setup, you will configure your `anki_vector` SDK authentication from a terminal using `configure.py`.

By running this script, you will be asked to provide your Anki account credentials, and the script will download an authentication token and cert that will grant you access to the robot and his capabilities (such as camera and audio) as well as data stored on the robot (such as faces and photos).

The downloaded access token is equivalent to your account credentials. It will be stored in your user directory (~/.anki_vector) along with a robot identity certificate and other useful data for establishing a connection. Do not share your access token.

If you have any trouble, please post to the Vector forums at https://forums.anki.com/

---

If you encounter any issues, please reach out to the forums team and let us know at https://forums.anki.com/

---

Use of Vector and the Vector SDK is subject to Anki's Privacy Policy and Terms and Conditions.

https://www.anki.com/en-us/company/privacy
https://www.anki.com/en-us/company/terms-and-conditions
