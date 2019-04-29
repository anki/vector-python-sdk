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

It uses Tkinter, a standard Python GUI package.
It also depends on the Pillow library for image processing.
"""

import multiprocessing as mp
import sys
import tkinter as tk

try:
    from PIL import ImageTk
except ImportError:
    sys.exit("Cannot import from PIL: Do `pip3 install --user Pillow` to install")


class TkCameraViewer:  # pylint: disable=too-few-public-methods
    """A Tkinter based camera video feed.

    :param queue: A queue to send frames between the user's main thread and the viewer process.
    :param event: An event to signal that the viewer process has closed.
    :param overlays: Overlays to be drawn on the images of the renderer.
    :param timeout: The time without a new frame before the process will exit.
    :param force_on_top: Specifies whether the window should be forced on top of all others.
    """

    def __init__(self, queue: mp.Queue, event: mp.Event, overlays: list = None, timeout: float = 10.0, force_on_top: bool = True):
        self.tk_root = tk.Tk()
        self.width = None
        self.height = None
        self.queue = queue
        self.event = event
        self.overlays = overlays
        self.timeout = timeout
        self.tk_root.title("Vector Camera Feed")
        self.tk_root.protocol("WM_DELETE_WINDOW", self._delete_window)
        self.tk_root.bind("<Configure>", self._resize_window)
        if force_on_top:
            self.tk_root.wm_attributes("-topmost", 1)
        self.label = tk.Label(self.tk_root, borderwidth=0)
        self.label.pack(fill=tk.BOTH, expand=True)

    def _delete_window(self) -> None:
        """Handle window close event."""
        self.event.set()
        self.tk_root.destroy()

    def _resize_window(self, evt: tk.Event) -> None:
        """Handle window resize event.

        :param evt: A Tkinter window event (keyboard, mouse events, etc).
        """
        self.width = evt.width
        self.height = evt.height

    def draw_frame(self) -> None:
        """Display an image on to a Tkinter label widget."""
        try:
            image = self.queue.get(True, timeout=self.timeout)
        except:
            return
        self.width, self.height = image.size
        while image:
            if self.event.is_set():
                break
            if self.overlays:
                for overlay in self.overlays:
                    overlay.apply_overlay(image)
            if (self.width, self.height) != image.size:
                image = image.resize((self.width, self.height))
            tk_image = ImageTk.PhotoImage(image)
            self.label.config(image=tk_image)
            self.label.image = tk_image
            self.tk_root.update_idletasks()
            self.tk_root.update()
            try:
                image = self.queue.get(True, timeout=self.timeout)
            except:
                return


def main(queue: mp.Queue, event: mp.Event, overlays: list = None, timeout: float = 10.0, force_on_top: bool = False) -> None:
    """Rendering the frames in another process. This allows the UI to have the
    main thread of its process while the user code continues to execute.

    :param queue: A queue to send frames between the user's main thread and the viewer process.
    :param event: An event to signal that the viewer process has closed.
    :param overlays: Overlays to be drawn on the images of the renderer.
    :param timeout: The time without a new frame before the process will exit.
    :param force_on_top: Specifies whether the window should be forced on top of all others.
    """

    try:
        tk_viewer = TkCameraViewer(queue, event, overlays, timeout, force_on_top)
        tk_viewer.draw_frame()
    except TimeoutError:
        pass
    except KeyboardInterrupt:
        pass
    finally:
        event.set()


__all__ = ['TkCameraViewer', 'main']
