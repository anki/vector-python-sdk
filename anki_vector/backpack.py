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
Backpack related classes, functions, events and values.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ["BackpackComponent"]


from . import lights, sync, util
from .messaging import protocol


class BackpackComponent(util.Component):
    """Manage Vector's Backpack lights"""
    @sync.Synchronizer.wrap
    async def set_backpack_lights(self,
                                  light1: lights.Light,
                                  light2: lights.Light,
                                  light3: lights.Light,
                                  backpack_color_profile: lights.ColorProfile = lights.WHITE_BALANCED_BACKPACK_PROFILE):
        """Set the lights on Vector's backpack.

        The light descriptions below are all from Vector's perspective.

        .. code-block:: python

            # Set backpack to different shades of red using int codes for 4 seconds
            robot.backpack.set_backpack_lights(
                anki_vector.lights.Light(anki_vector.color.Color(int_color=0xff0000ff)),
                anki_vector.lights.Light(anki_vector.color.Color(int_color=0x1f0000ff)),
                anki_vector.lights.Light(anki_vector.color.Color(int_color=0x4f0000ff)))
            time.sleep(4.0)

        :param light1: The front backpack light
        :param light2: The center backpack light
        :param light3: The rear backpack light
        :param backpack_color_profile: The color profile to use with the backpack light setting
        """
        params = lights.package_request_params((light1, light2, light3), backpack_color_profile)
        set_backpack_lights_request = protocol.SetBackpackLightsRequest(**params)

        return await self.grpc_interface.SetBackpackLights(set_backpack_lights_request)

    def set_all_backpack_lights(self,
                                light: lights.Light,
                                color_profile: lights.ColorProfile = lights.WHITE_BALANCED_BACKPACK_PROFILE):
        """Set the lights on Vector's backpack to the same color.

        .. code-block:: python

            robot.backpack.set_all_backpack_lights(anki_vector.lights.magenta_light, anki_vector.lights.MAX_COLOR_PROFILE)
            time.sleep(4)

        :param light: The lights for Vector's backpack.
        :param color_profile: The profile to be used for the backpack lights.
        """
        light_arr = [light] * 3
        return self.set_backpack_lights(*light_arr, color_profile)
