
# Anki/DDL Vector - Python SDK

## With support for Production, EscapePod and OSKR robots!

This is a fork of the original Anki Vector Python SDK.

![Vector](docs/source/images/vector-sdk-alpha.jpg)


## Getting Started

You can follow steps [here](https://developer.anki.com/vector/docs/index.html) to set up your Vector robot with the SDK.


### Installation

In case you have previously installed the original anki or ikkez sdk, uninstall it with following commands:
**```
pip uninstall anki_vector
pip uninstall ikkez_vector
```**

To install this SDK, run:
**```
pip install cyb3r_vector_sdk
```**

You can upgrade to latest version with:
**```
pip install cyb3r_vector_sdk --upgrade
```**

In case you will run into dificulties during installation, run this command first:

- Windows:  ```py -m pip install -U pip```
- Linux:    ```python3 -m pip install -U pip```


If you want to know where the SDK is installed use following command:

- Windows:  ```py -c "import anki_vector as _; print(_.__path__)"```
- Linux:    ```python3 -c "import anki_vector as _; print(_.__path__)"```


### SDK Configuration

To configure the SDK for **Prod**, and/or **Prod+OSKR** robot, run:

- Windows:  **```py -m anki_vector.configure```**
- Linux:    **```python3 -m anki_vector.configure```**

To configure the SDK for **EscapePod**, and/or **EP+OSKR** robot, run:

- Windows:  **```py -m anki_vector.configure_pod```**
- Linux:    **```python3 -m anki_vector.configure_pod```**


### SDK Usage - EscapePod

You can either use the ```anki_vector.configure_pod``` in order to save your authentication into the sdk_config.ini file, and use all the [examples](https://github.com/cyb3rdog/vector-python-sdk/tree/master/examples) and your own programs and as you have them, or you can use the Robot object with setting the escape_pod parameter to True, and passing the robot's ip address:

```
    with anki_vector.Robot(ip="192.168.0.148", escape_pod=True) as robot:
        robot.behavior.say_text("Hello Escape Pod")
```


### Documentation

You can generate a local copy of the SDK documetation by
following the instructions in the `docs` folder of this project.

Learn more about Vector: https://www.anki.com/en-us/vector

Learn more about how Vector works: [Vector Bible](https://github.com/GooeyChickenman/victor/blob/master/documentation/Vector-TRM.pdf)

Learn more about the SDK: https://developer.anki.com/

SDK documentation: https://developer.anki.com/vector/docs/index.html

Forums: https://forums.anki.com/


## Privacy Policy and Terms and Conditions

Use of Vector and the Vector SDK is subject to Anki's [Privacy Policy](https://www.anki.com/en-us/company/privacy) and [Terms and Conditions](https://www.anki.com/en-us/company/terms-and-conditions).
