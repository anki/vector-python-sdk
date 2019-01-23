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

"""This module provides the camera viewer's render process.

It should be launched in a separate process to allow Vector to run freely while
the viewer is rendering.

It uses python-opencv, an image processing library which is available on most
platforms. It also depends on the Pillow library for image processing.
"""

import multiprocessing as mp
import os
import sys

try:
    import numpy as np
except ImportError as exc:
    sys.exit("Cannot import numpy: Do `pip3 install numpy` to install")

try:
    import cv2
except ImportError as exc:
    sys.exit("Cannot import opencv-python: Do `pip3 install opencv-python` to install")


def main(queue: mp.Queue, event: mp.Event, overlays: list = None, timeout: float = 10.0) -> None:
    """Rendering the frames in another process. This allows the UI to have the
    main thread of its process while the user code continues to execute.

    :param queue: A queue to send frames between the user's main thread and the viewer process.
    :param event: An event to signal that the viewer process has closed.
    :param overlays: overlays to be drawn on the images of the renderer.
    :param timeout: The time without a new frame before the process will exit.
    """
    is_windows = os.name == 'nt'
    window_name = "Vector Camera Feed"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    try:
        image = queue.get(True, timeout=timeout)
        while image:
            if event.is_set():
                break
            if overlays:
                for overlay in overlays:
                    overlay.apply_overlay(image)
            image = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2RGB)
            cv2.imshow(window_name, np.array(image))
            cv2.waitKey(1)
            if not is_windows and cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                break
            image = queue.get(True, timeout=timeout)
    except TimeoutError:
        pass
    except KeyboardInterrupt:
        pass
    finally:
        event.set()
        cv2.destroyWindow(window_name)
        cv2.waitKey(1)


__all__ = ['main']
