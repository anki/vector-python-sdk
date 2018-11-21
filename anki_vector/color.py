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

"""
Colors to be used with a light or Vector's screen.
"""


class Color:
    """A Color to be used with a Light or Vector's screen.

    Either int_color or rgb may be used to specify the actual color.
    Any alpha components (from int_color) are ignored - all colors are fully opaque.

    :param int_color: A 32 bit value holding the binary RGBA value (where A
            is ignored and forced to be fully opaque).
    :param rgb: A tuple holding the integer values from 0-255 for (reg, green, blue)
    :param name: A name to assign to this color.
    """

    def __init__(self, int_color: int = None, rgb: tuple = None, name: str = None):
        self.name = name
        self._int_color = 0
        if int_color is not None:
            self._int_color = int_color | 0xff
        elif rgb is not None:
            self._int_color = (rgb[0] << 24) | (rgb[1] << 16) | (rgb[2] << 8) | 0xff

    @property
    def int_color(self) -> int:
        """The encoded integer value of the color."""
        return self._int_color

    @property
    def rgb565_bytepair(self):
        """bytes[]: Two bytes representing an int16 color with rgb565 encoding.

        This format reflects the robot's Screen color range, and performing this
        conversion will reduce network traffic when sending Screen data.
        """

        red5 = ((self._int_color >> 24) & 0xff) >> 3
        green6 = ((self._int_color >> 16) & 0xff) >> 2
        blue5 = ((self._int_color >> 8) & 0xff) >> 3

        green3_hi = green6 >> 3
        green3_low = green6 & 0x07

        int_565_color_lowbyte = (green3_low << 5) | blue5
        int_565_color_highbyte = (red5 << 3) | green3_hi

        return [int_565_color_highbyte, int_565_color_lowbyte]


#: :class:`Color`: Green color instance.
green = Color(name="green", int_color=0x00ff00ff)

#: :class:`Color`: Red color instance.
red = Color(name="red", int_color=0xff0000ff)

#: :class:`Color`: Blue color instance.
blue = Color(name="blue", int_color=0x0000ffff)

#: :class:`Color`: Cyan color instance.
cyan = Color(name="cyan", int_color=0x00ffffff)

#: :class:`Color`: Magenta color instance.
magenta = Color(name="magenta", int_color=0xff00ffff)

#: :class:`Color`: Yellow color instance.
yellow = Color(name="yellow", int_color=0xffff00ff)

#: :class:`Color`: White color instance.
white = Color(name="white", int_color=0xffffffff)

#: :class:`Color`: Instance representing no color (i.e., lights off).
off = Color(name="off")
