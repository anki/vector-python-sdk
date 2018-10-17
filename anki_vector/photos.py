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
Photo related classes, functions, events and values.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ["PhotographComponent"]

from typing import List

from . import sync, util
from .messaging import protocol


class PhotographComponent(util.Component):
    """Access the photos on Vector.

    .. testcode::

        import anki_vector
        from PIL import Image

        with anki_vector.Robot("my_robot_serial_number") as robot:
            if len(robot.photos.photo_info) > 0:
                first_photo = robot.photos.photo_info[0]
                photo = robot.photos.get_photo(first_photo)
                image = Image.open(io.BytesIO(photo.image))
                image.show()

    :param anki_vector.Robot robot: A reference to an instance of the Robot class. Used to make rpc calls.
    """

    def __init__(self, robot):
        super().__init__(robot)
        self._photo_info: List[protocol.PhotoInfo] = []

    @property
    def photo_info(self) -> List[protocol.PhotoInfo]:
        """The information about what photos are stored on Vector.

        If the photo info hasn't been loaded yet, accessing this property will request it from the robot.

        .. testcode::

            import anki_vector

            photos = robot.photos.photo_info
            if len(photos) > 0:
                photo = photos[0]
                photo.photo_id # the id to use to grab a photo from the robot
                photo.timestamp_utc # utc timestamp of when the photo was taken (according to the robot)
        """
        if not self._photo_info:
            self.logger.debug("Photo list was empty. Lazy-loading photo list now.")
            result = self.load_photo_info()
            if isinstance(result, sync.Synchronizer):
                result.wait_for_completed()
        return self._photo_info

    @sync.Synchronizer.wrap
    async def load_photo_info(self) -> protocol.PhotosInfoResponse:
        """Request the photo information from the robot.

        .. testcode::

            import anki_vector

            robot.photos.load_photo_info()

        :return: The response from the PhotosInfo rpc call
        """
        req = protocol.PhotosInfoRequest()
        result = await self.grpc_interface.PhotosInfo(req)
        self._photo_info = result.photo_infos
        return result

    @sync.Synchronizer.wrap
    @sync.Synchronizer.disable_log
    async def get_photo(self, photo_id: int) -> protocol.PhotoResponse:
        """Download a full-resolution photo from the robot's storage.

        .. testcode::

            import anki_vector
            from PIL import Image

            with anki_vector.Robot("my_robot_serial_number") as robot:
                if len(robot.photos.photo_info) > 0:
                    first_photo = robot.photos.photo_info[0]
                    photo = robot.photos.get_photo(first_photo)
                    image = Image.open(io.BytesIO(photo.image))
                    image.show()

        :param photo_id: The id of the photo to download. It's recommended to get this
                         value from the photo_info list first.

        :return: A response containing all of the photo bytes which may be rendered using
                 another library (like :mod:`PIL`)
        """
        req = protocol.PhotoRequest(photo_id=photo_id)
        return await self.grpc_interface.Photo(req)

    @sync.Synchronizer.wrap
    @sync.Synchronizer.disable_log
    async def get_thumbnail(self, photo_id: int) -> protocol.ThumbnailResponse:
        """Download a thumbnail of a given photo from the robot's storage.

        You may use this function to pull all of the images off the robot in a smaller format, and
        then determine which one to download as full resolution.

        .. testcode::

            import anki_vector
            from PIL import Image

            with anki_vector.Robot("my_robot_serial_number") as robot:
                for photo in robot.photos.photo_info:
                    photo = robot.photos.get_thumbnail(photo)
                    image = Image.open(io.BytesIO(photo.image))
                    image.show()

        :param photo_id: The id of the thumbnail to download. It's recommended to get this
                         value from the photo_info list first.

        :return: A response containing all of the thumbnail bytes which may be rendered using
                 another library (like :mod:`PIL`)
        """
        req = protocol.ThumbnailRequest(photo_id=photo_id)
        return await self.grpc_interface.Thumbnail(req)
