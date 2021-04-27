# Copyright (c) 2018 Anki, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the file LICENSE.txt or at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This module provides 3D classes for running the OpenGL Viewer.

It should be launched in a separate process to allow Vector to run freely while
the viewer is rendering.

It uses PyOpenGL, a Python OpenGL 3D graphics library which is available on most
platforms. It also depends on the Pillow library for image processing.

Warning:
    This package requires Python to have the PyOpenGL package installed, along
    with an implementation of GLUT (OpenGL Utility Toolkit).

    To install the Python packages on Mac and Linux do ``python3 -m pip install --user "cyb3r_vector_sdk[3dviewer]"``

    To install the Python packages on Windows do ``py -3 -m pip install --user "cyb3r_vector_sdk[3dviewer]"``

    On Windows and Linux you must also install freeglut (macOS / OSX has one
    preinstalled).

    On Linux: ``sudo apt-get install freeglut3``

    On Windows: Go to http://freeglut.sourceforge.net/ to get a ``freeglut.dll``
    file. It's included in any of the `Windows binaries` downloads. Place the DLL
    next to your Python script, or install it somewhere in your PATH to allow any
    script to use it."
"""

import multiprocessing as mp

from . import opengl_viewer


def main(close_event: mp.Event,
         input_intent_queue: mp.Queue,
         nav_map_queue: mp.Queue,
         world_frame_queue: mp.Queue,
         extra_render_function_queue: mp.Queue,
         user_data_queue: mp.Queue,
         show_viewer_controls: bool = True):
    """Run the 3D Viewer window. This is intended to run on a background process.

    .. code-block:: python

        import multiprocessing as mp

        from anki_vector import opengl

        ctx = mp.get_context('spawn')
        close_event = ctx.Event()
        input_intent_queue = ctx.Queue(maxsize=10)
        nav_map_queue = ctx.Queue(maxsize=10)
        world_frame_queue = ctx.Queue(maxsize=10)
        extra_render_function_queue = ctx.Queue(maxsize=1)
        user_data_queue = ctx.Queue()
        process = ctx.Process(target=opengl.main,
                              args=(close_event,
                                    input_intent_queue,
                                    nav_map_queue,
                                    world_frame_queue,
                                    extra_render_function_queue,
                                    user_data_queue),
                              daemon=True)
        process.start()

    :param close_event: Used to notify each process when done rendering.
    :type close_event: multiprocessing.Event
    :param input_intent_queue: Sends key commands from the 3D viewer process to the main process.
    :type input_intent_queue: multiprocessing.Queue
    :param nav_map_queue: Updates the 3D viewer process with the latest navigation map.
    :type nav_map_queue: multiprocessing.Queue
    :param world_frame_queue: Provides the 3D viewer with details about the world.
    :type world_frame_queue: multiprocessing.Queue
    :param extra_render_function_queue: Functions to be executed in the 3D viewer process.
    :type extra_render_function_queue: multiprocessing.Queue
    :param user_data_queue: A queue that may be used outside the SDK to pass information to the viewer process.
        May be used by ``extra_render_function_queue`` functions.
    :param show_viewer_controls: Specifies whether to draw controls on the view.
    """
    viewer = opengl_viewer.OpenGLViewer(close_event,
                                        input_intent_queue,
                                        nav_map_queue,
                                        world_frame_queue,
                                        extra_render_function_queue,
                                        user_data_queue,
                                        show_viewer_controls=show_viewer_controls)
    viewer.run()


__all__ = ['main']
