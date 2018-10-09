#!/usr/bin/env python3

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

"""Show a photo taken by Vector.

Grabs the pictures off of Vector and open them via PIL.

Before running this script, please make sure you have successfully
had Vector take a photo by saying, "Hey Vector! Take a photo."
"""

import io

try:
    from PIL import Image
except ImportError:
    sys.exit("Cannot import from PIL: Do `pip3 install --user Pillow` to install")

import anki_vector


def main():
    args = anki_vector.util.parse_command_args()
    with anki_vector.Robot(args.serial) as robot:
        photo_info_list = robot.photos.photo_info
        for photo in robot.photos.photo_info:
            print(f"Opening photo {photo.photo_id}")
            val = robot.photos.get_photo(photo.photo_id)
            image = Image.open(io.BytesIO(val.image))
            image.show()
        else:
            print('\n\nNo photos found on Vector. Ask him to take a photo first by saying, "Hey Vector! Take a photo."\n\n')

if __name__ == "__main__":
    main()
