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
Photo related classes, functions, events and values.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ["PhotographComponent"]

import concurrent
from typing import List

from . import connection, util
from .messaging import protocol


class PhotographComponent(util.Component):
    """Access the photos on Vector.

    .. testcode::

        import anki_vector
        import io
        from PIL import Image

        with anki_vector.Robot() as robot:
            for photo_info in robot.photos.photo_info:
                print(f"Opening photo {photo_info.photo_id}")
                photo = robot.photos.get_photo(photo_info.photo_id)
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

            with anki_vector.Robot() as robot:
                for photo_info in robot.photos.photo_info:
                    print(f"photo_info.photo_id: {photo_info.photo_id}") # the id to use to grab a photo from the robot
                    print(f"photo_info.timestamp_utc: {photo_info.timestamp_utc}") # utc timestamp of when the photo was taken (according to the robot)
        """
        if not self._photo_info:
            self.logger.debug("Photo list was empty. Lazy-loading photo list now.")
            result = self.load_photo_info()
            if isinstance(result, concurrent.futures.Future):
                result.result()
        return self._photo_info

    @connection.on_connection_thread()
    async def load_photo_info(self) -> protocol.PhotosInfoResponse:
        """Request the photo information from the robot.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                photo_info = robot.photos.load_photo_info()
                print(f"photo_info: {photo_info}")

        :return: UTC timestamp of the photo and additional data.
        """
        req = protocol.PhotosInfoRequest()
        result = await self.grpc_interface.PhotosInfo(req)
        self._photo_info = result.photo_infos
        return result

    @connection.on_connection_thread(log_messaging=False)
    async def get_photo(self, photo_id: int) -> protocol.PhotoResponse:
        """Download a full-resolution photo from the robot's storage.

        .. testcode::

            import anki_vector
            import io
            from PIL import Image

            with anki_vector.Robot() as robot:
                for photo_info in robot.photos.photo_info:
                    print(f"Opening photo {photo_info.photo_id}")
                    photo = robot.photos.get_photo(photo_info.photo_id)
                    image = Image.open(io.BytesIO(photo.image))
                    image.show()

        :param photo_id: The id of the photo to download. It's recommended to get this
                         value from the photo_info list first.

        :return: A response containing all of the photo bytes which may be rendered using
                 another library (like :mod:`PIL`)
        """
        req = protocol.PhotoRequest(photo_id=photo_id)
        return await self.grpc_interface.Photo(req)

    @connection.on_connection_thread(log_messaging=False)
    async def get_thumbnail(self, photo_id: int) -> protocol.ThumbnailResponse:
        """Download a thumbnail of a given photo from the robot's storage.

        You may use this function to pull all of the images off the robot in a smaller format, and
        then determine which one to download as full resolution.

        .. testcode::

            import anki_vector
            from PIL import Image
            import io

            with anki_vector.Robot() as robot:
                for photo_info in robot.photos.photo_info:
                    photo = robot.photos.get_thumbnail(photo_info.photo_id)
                    image = Image.open(io.BytesIO(photo.image))
                    image.show()

        :param photo_id: The id of the thumbnail to download. It's recommended to get this
                         value from the photo_info list first.

        :return: A response containing all of the thumbnail bytes which may be rendered using
                 another library (like :mod:`PIL`)
        """
        req = protocol.ThumbnailRequest(photo_id=photo_id)
        return await self.grpc_interface.Thumbnail(req)
