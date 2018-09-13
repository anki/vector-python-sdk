# Anki Vector - Python SDK

## Getting Started

Before connecting, you will need:

* Vector's Name: This is the name displayed on his face for BLE pairing after you double click while Vector is on the charger. Example: `Vector-A1B2`
* Vector's IP Address: The ip address can be found by first placing Vector on the charger, then double-clicking the button on his back, and finally raising and lowering his arms. It is possible for your ip to change based on your network settings, so it must be updated accordingly. Example: `192.168.43.48`
* Vector's Serial Number: You may find this number on the underside of your robot. Example: `00e20115`

These will be needed to run the configure.py script and set up authentication with your Vector.

## Installation Steps

Install python3:

```bash
brew install python
```

---

Either:

* In the future, you may download the required python packages from PyPi: `pip3 install anki_vector`

Or:

* Install a specific build of the Anki Vector SDK using `pip3 install .`

---

Then configure your `anki_vector` SDK authentication from a terminal using:

```bash
python3 configure.py
```

If you have any trouble, please contact a member of the SDK team.

---

Run the scripts under `examples/tutorials` to test out the installation using:

```bash
python3 examples/tutorials/01_hello_world.py -e ${VECTOR_SERIAL_NUMBER}
```

> Note: Replace `${VECTOR_SERIAL_NUMBER}` with your robot's serial number.

---

Until the documentation is uploaded to the anki.com website, check out the documentation:

```bash
cd docs
make html
open build/html/index.html
```

If you encounter any issues, please reach out to the SDK team and let us know.
