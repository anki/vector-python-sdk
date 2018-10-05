# Copyright (c) 2018 Anki, Inc.

"""
Vector SDK, by Anki.

Requirements:
    * Python 3.6.1 or later
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

def get_requirements() -> list:
    """Load the requirements from requirements.txt into a list"""
    reqs = []
    with open(os.path.join(HERE, 'requirements.txt')) as requirements_file:
        for line in requirements_file:
            reqs.append(line.strip())
    return reqs

setup(
    name='anki_vector',
    version=VERSION,
    description="SDK for Anki's Vector robot",
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
    install_requires=get_requirements(),
    extras_require={
        '3dviewer': ['PyOpenGL>=3.1'],
        'experimental': ['keras', 'scikit-learn', 'scipy', 'tensorflow'],
        'test': ['pytest', 'requests', 'requests_toolbelt'],
    }
)
