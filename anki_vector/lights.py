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

"""Helper routines for dealing with Vector's lights and colors."""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['MAX_COLOR_PROFILE', 'WHITE_BALANCED_BACKPACK_PROFILE', 'WHITE_BALANCED_CUBE_PROFILE',
           'blue_light', 'cyan_light', 'green_light', 'magenta_light', 'off_light',
           'red_light', 'white_light', 'yellow_light',
           'Color', 'ColorProfile', 'Light', 'package_request_params']

from .color import Color, green, red, blue, cyan, magenta, yellow, white, off

# TODO Needs a better docstring. Can't describe a ColorProfile as a Color profile.


class ColorProfile:
    """A Color profile to be used with messages involving Lights.

    :param red_multiplier: Scaling value for the brightness of red Lights
    :param green_multiplier: Scaling value for the brightness of green Lights
    :param blue_multiplier: Scaling value for the brightness of blue Lights
    """

    def __init__(self, red_multiplier: float, green_multiplier: float, blue_multiplier: float):
        self._red_multiplier = red_multiplier
        self._green_multiplier = green_multiplier
        self._blue_multiplier = blue_multiplier

    # TODO Needs docs, param types, sample code
    def augment_color(self, original_color):
        rgb = [
            (original_color.int_color >> 24) & 0xff,
            (original_color.int_color >> 16) & 0xff,
            (original_color.int_color >> 8) & 0xff
        ]

        rgb[0] = int(self._red_multiplier * rgb[0])
        rgb[1] = int(self._green_multiplier * rgb[1])
        rgb[2] = int(self._blue_multiplier * rgb[2])

        result_int_code = (rgb[0] << 24) | (rgb[1] << 16) | (rgb[2] << 8) | 0xff
        return Color(result_int_code)

    # TODO Needs example code, more descriptive docs
    @property
    def red_multiplier(self):
        """float: The multiplier used on the red channel."""
        return self._red_multiplier

    # TODO Needs example code, more descriptive docs
    @property
    def green_multiplier(self):
        """float: The multiplier used on the red channel."""
        return self._green_multiplier

    # TODO Needs example code, more descriptive docs
    @property
    def blue_multiplier(self):
        """float: The multiplier used on the red channel."""
        return self._blue_multiplier


#: :class:`ColorProfile`:  Color profile to get the maximum possible brightness out of each LED.
MAX_COLOR_PROFILE = ColorProfile(red_multiplier=1.0,
                                 green_multiplier=1.0,
                                 blue_multiplier=1.0)

#: :class:`ColorProfile`:  Color profile balanced so that a max color value more closely resembles pure white.
# TODO: Balance this more carefully once robots with proper color pipe
# hardware becomes available
WHITE_BALANCED_BACKPACK_PROFILE = ColorProfile(red_multiplier=1.0,
                                               green_multiplier=0.825,
                                               blue_multiplier=0.81)

#: :class:`ColorProfile`:  Color profile balanced so that a max color value more closely resembles pure white.
# TODO: Balance this more carefully once robots with proper color pipe
# hardware becomes available
WHITE_BALANCED_CUBE_PROFILE = ColorProfile(red_multiplier=1.0,
                                           green_multiplier=0.95,
                                           blue_multiplier=0.7)


class Light:
    """Lights are used with Vector's LightCube and backpack.

    Lights may either be "on" or "off", though in practice any colors may be
    assigned to either state (including no color/light).
    """

    def __init__(self,
                 on_color: Color = off,
                 off_color: Color = off,
                 on_period_ms: int = 250,
                 off_period_ms: int = 0,
                 transition_on_period_ms: int = 0,
                 transition_off_period_ms: int = 0):
        self._on_color = on_color
        self._off_color = off_color
        self._on_period_ms = on_period_ms
        self._off_period_ms = off_period_ms
        self._transition_on_period_ms = transition_on_period_ms
        self._transition_off_period_ms = transition_off_period_ms

    @property
    def on_color(self) -> Color:
        """The color shown when the light is on."""
        return self._on_color

    @on_color.setter
    def on_color(self, color):
        if not isinstance(color, Color):
            raise TypeError("Must specify a Color")
        self._on_color = color

    @property
    def off_color(self) -> Color:
        """The color shown when the light is off."""
        return self._off_color

    @off_color.setter
    def off_color(self, color):
        if not isinstance(color, Color):
            raise TypeError("Must specify a Color")
        self._off_color = color

    @property
    def on_period_ms(self) -> int:
        """The number of milliseconds the light should be "on" for for each cycle."""
        return self._on_period_ms

    @on_period_ms.setter
    def on_period_ms(self, ms):
        if not 0 < ms < 2**32:
            raise ValueError("Invalid value")
        self._on_period_ms = ms

    @property
    def off_period_ms(self) -> int:
        """The number of milliseconds the light should be "off" for for each cycle."""
        return self._off_period_ms

    @off_period_ms.setter
    def off_period_ms(self, ms):
        if not 0 < ms < 2**32:
            raise ValueError("Invalid value")
        self._off_period_ms = ms

    @property
    def transition_on_period_ms(self) -> int:
        """The number of milliseconds to take to transition the light to the on color."""
        return self._transition_on_period_ms

    @transition_on_period_ms.setter
    def transition_on_period_ms(self, ms):
        if not 0 < ms < 2**32:
            raise ValueError("Invalid value")
        self._transition_on_period_ms = ms

    @property
    def transition_off_period_ms(self) -> int:
        """The number of milliseconds to take to transition the light to the off color."""
        return self._transition_off_period_ms

    @transition_off_period_ms.setter
    def transition_off_period_ms(self, ms):
        if not 0 < ms < 2**32:
            raise ValueError("Invalid value")
        self._transition_off_period_ms = ms


# TODO needs docs, param types. Should this be private?
def package_request_params(lights, color_profile):
    merged_params = {}
    for light in lights:
        for attr_name in vars(light):
            attr_name = attr_name[1:]
            attr_val = getattr(light, attr_name)
            if isinstance(attr_val, Color):
                attr_val = color_profile.augment_color(attr_val).int_color
            merged_params.setdefault(attr_name, []).append(attr_val)
    return merged_params

# TODO Add sample code for the following light instances?


#: :class:`Light`: A steady green colored LED light.
green_light = Light(on_color=green)

#: :class:`Light`: A steady red colored LED light.
red_light = Light(on_color=red)

#: :class:`Light`: A steady blue colored LED light.
blue_light = Light(on_color=blue)

#: :class:`Light`: A steady cyan colored LED light.
cyan_light = Light(on_color=cyan)

#: :class:`Light`: A steady magenta colored LED light.
magenta_light = Light(on_color=magenta)

#: :class:`Light`: A steady yellow colored LED light.
yellow_light = Light(on_color=yellow)

#: :class:`Light`: A steady white colored LED light.
white_light = Light(on_color=white)

#: :class:`Light`: A steady off (non-illuminated LED light).
off_light = Light(on_color=off)
