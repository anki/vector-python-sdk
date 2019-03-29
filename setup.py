# Copyright (c) 2018 Anki, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the file LICENSE.txt or at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
The Vector SDK gives you direct access to Vector's unprecedented set of advanced sensors, AI capabilities, and robotics technologies including computer vision, intelligent mapping and navigation, and a groundbreaking collection of expressive animations.

It's powerful but easy to use, complex but not complicated, and versatile enough to be used across a wide range of domains including enterprise, research, and entertainment. Find out more at https://developer.anki.com

Vector SDK documentation: https://developer.anki.com/vector/docs/

Official developer forum: https://forums.anki.com/

Requirements:
    * Python 3.6.1 or later
"""

import os.path
import sys
from setuptools import setup

if sys.version_info < (3, 6, 1):
    sys.exit('The Vector SDK requires Python 3.6.1 or later')

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
    description="The Vector SDK is a connected vision- and character-based robotics platform for everyone.",
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
    keywords='anki vector robot robotics sdk ai vision'.split(),
    packages=['anki_vector', 'anki_vector.camera_viewer', 'anki_vector.configure', 'anki_vector.messaging', 'anki_vector.opengl', 'anki_vector.reserve_control'],
    package_data={
        'anki_vector': ['LICENSE.txt', 'opengl/assets/*.obj', 'opengl/assets/*.mtl', 'opengl/assets/*.jpg',
                  'opengl/assets/LICENSE.txt']
    },
    install_requires=get_requirements(),
    extras_require={
        '3dviewer': ['PyOpenGL>=3.1'],
        'docs': ['sphinx', 'sphinx_rtd_theme', 'sphinx_autodoc_typehints'],
        'experimental': ['keras', 'scikit-learn', 'scipy', 'tensorflow'],
        'test': ['pytest', 'requests', 'requests_toolbelt'],
    }
)
