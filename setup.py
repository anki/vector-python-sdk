# Copyright (c) 2018 Anki, Inc.

"""
Vector SDK, by Anki.

Vector is the home robot who hangs out and helps out.

This library lets you take command of Vector and write programs for him.

Vector features:

    * A camera with advanced vision system
    * A robotic lifter
    * Independent tank treads
    * Pivotable head
    * An accelerometer
    * A gyroscope
    * Cliff detection
    * Face recognition
    * Path planning
    * Animation and behavior systems
    * Light cube, with LEDs, an accelerometer and tap detection
    * Single point time-of-flight NIR Laser
    * Capactive casing

This SDK provides users with access to take control of Vector and write simple
or advanced programs with him.

Requirements:
    * Python 3.6.1 or later

Optional requirements for camera image processing/display:
    * Pillow
    * NumPy

Optional requirements for 3D viewer/visualization:
    * PyOpenGL
    * Pillow
"""

import os.path
import sys
from setuptools import setup

if sys.version_info < (3, 6, 1):
    sys.exit('The Anki Vector SDK requires Python 3.6.1 or later')

HERE = os.path.abspath(os.path.dirname(__file__))

def fetch_version():
    """Get the version from the package"""
    with open(os.path.join(HERE, 'anki_vector', 'version.py')) as version_file:
        versions = {}
        exec(version_file.read(), versions)
        return versions

VERSION_DATA = fetch_version()
VERSION = VERSION_DATA['__version__']

def get_requirements():
    """Load the requirements from requirements.txt into a list"""
    reqs = []
    with open(os.path.join(HERE, 'requirements.txt')) as requirements_file:
        for line in requirements_file:
            reqs.append(line.strip())
    return reqs

setup(
    name='anki_vector',
    version=VERSION,
    description="SDK for Anki's Vector robot, the home robot who hangs out and helps out",
    long_description=__doc__,
    url='https://developer.anki.com',
    author='Anki, Inc',
    author_email='developer@anki.com',
    license='Apache License, Version 2.0',
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3.6',
    ],
    zip_safe=True,
    keywords='anki vector robot robotics sdk'.split(),
    packages=['anki_vector', 'anki_vector.messaging'],
    package_data={
        'anki_vector': ['LICENSE.txt', 'assets/*.obj', 'assets/*.mtl', 'assets/*.jpg',
                  'assets/LICENSE.txt']
    },
    install_requires=get_requirements(),
    extras_require={
        '3dviewer': ['PyOpenGL>=3.1'],
        'docs': ['sphinx', 'sphinx_rtd_theme', 'sphinx_autodoc_typehints'],
        'experimental': ['keras', 'scikit-learn', 'scipy', 'tensorflow'],
        'test': ['pytest', 'requests', 'requests_toolbelt'],
    }
)
