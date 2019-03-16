#!/usr/bin/env python3

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

"""This example demonstrates how you can define custom objects.

The example defines several custom objects (2 cubes, a wall and a box). When
Vector sees the markers for those objects he will report that he observed an
object of that size and shape there.

You can adjust the markers, marker sizes, and object sizes to fit whatever
object you have and the exact size of the markers that you print out.
"""

import time

import anki_vector
from anki_vector.objects import CustomObjectMarkers, CustomObjectTypes


def handle_object_appeared(robot, event_type, event):
    # This will be called whenever an EvtObjectAppeared is dispatched -
    # whenever an Object comes into view.
    print(f"--------- Vector started seeing an object --------- \n{event.obj}")


def handle_object_disappeared(robot, event_type, event):
    # This will be called whenever an EvtObjectDisappeared is dispatched -
    # whenever an Object goes out of view.
    print(f"--------- Vector stopped seeing an object --------- \n{event.obj}")


def main():
    args = anki_vector.util.parse_command_args()
    with anki_vector.Robot(args.serial,
                           default_logging=False,
                           show_viewer=True,
                           show_3d_viewer=True,
                           enable_custom_object_detection=True,
                           enable_nav_map_feed=True) as robot:
        # Add event handlers for whenever Vector sees a new object
        robot.events.subscribe(handle_object_appeared, anki_vector.events.Events.object_appeared)
        robot.events.subscribe(handle_object_disappeared, anki_vector.events.Events.object_disappeared)

        # define a unique cube (44mm x 44mm x 44mm) (approximately the same size as Vector's light cube)
        # with a 50mm x 50mm Circles2 image on every face. Note that marker_width_mm and marker_height_mm
        # parameter values must match the dimensions of the printed marker.
        cube_obj = robot.world.define_custom_cube(custom_object_type=CustomObjectTypes.CustomType00,
                                                  marker=CustomObjectMarkers.Circles2,
                                                  size_mm=44.0,
                                                  marker_width_mm=50.0,
                                                  marker_height_mm=50.0,
                                                  is_unique=True)

        # define a unique cube (88mm x 88mm x 88mm) (approximately 2x the size of Vector's light cube)
        # with a 50mm x 50mm Circles3 image on every face.
        big_cube_obj = robot.world.define_custom_cube(custom_object_type=CustomObjectTypes.CustomType01,
                                                      marker=CustomObjectMarkers.Circles3,
                                                      size_mm=88.0,
                                                      marker_width_mm=50.0,
                                                      marker_height_mm=50.0,
                                                      is_unique=True)

        # define a unique wall (150mm x 120mm (x10mm thick for all walls)
        # with a 50mm x 30mm Triangles2 image on front and back
        wall_obj = robot.world.define_custom_wall(custom_object_type=CustomObjectTypes.CustomType02,
                                                  marker=CustomObjectMarkers.Triangles2,
                                                  width_mm=150,
                                                  height_mm=120,
                                                  marker_width_mm=50,
                                                  marker_height_mm=30,
                                                  is_unique=True)

        # define a unique box (20mm deep x 20mm width x20mm tall)
        # with a different 50mm x 50mm image on each of the 6 faces
        box_obj = robot.world.define_custom_box(custom_object_type=CustomObjectTypes.CustomType03,
                                                marker_front=CustomObjectMarkers.Diamonds2,   # front
                                                marker_back=CustomObjectMarkers.Hexagons2,    # back
                                                marker_top=CustomObjectMarkers.Hexagons3,     # top
                                                marker_bottom=CustomObjectMarkers.Hexagons4,  # bottom
                                                marker_left=CustomObjectMarkers.Triangles3,   # left
                                                marker_right=CustomObjectMarkers.Triangles4,  # right
                                                depth_mm=20.0,
                                                width_mm=20.0,
                                                height_mm=20.0,
                                                marker_width_mm=50.0,
                                                marker_height_mm=50.0,
                                                is_unique=True)

        if ((cube_obj is not None) and (big_cube_obj is not None) and
                (wall_obj is not None) and (box_obj is not None)):
            print("All objects defined successfully!")
        else:
            print("One or more object definitions failed!")
            return

        print("\n\nShow a marker specified in the Python script to Vector and you will see the related 3d objects\n"
              "display in Vector's 3d_viewer window. You will also see messages print every time a custom object\n"
              "enters or exits Vector's view. Markers can be found from the docs under CustomObjectMarkers.\n\n")

        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
