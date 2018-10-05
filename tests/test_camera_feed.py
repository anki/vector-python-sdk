#!/usr/bin/env python3

"""
Test camera feed
"""

import os
import sys
import utilities

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import anki_vector  # pylint: disable=wrong-import-position


def main():
    """main execution"""
    args = anki_vector.util.parse_command_args()

    print("------ begin testing camera feed ------")

    # Receive camera feed from robot
    with anki_vector.Robot(args.serial, show_viewer=True) as robot:
        print("------ waiting for image events, press ctrl+c to exit early ------")
        try:
            # Render video for 10 seconds
            robot.loop.run_until_complete(utilities.delay_close(10))

            # Disable video render for 5 seconds
            robot.viewer.stop_video()
            robot.loop.run_until_complete(utilities.delay_close(5))

            # Render video for 10 seconds
            robot.viewer.show_video()
            robot.loop.run_until_complete(utilities.delay_close(10))

            # Disable video render and camera feed for 5 seconds
            robot.viewer.stop_video()
            robot.enable_camera_feed = False
            robot.loop.run_until_complete(utilities.delay_close(5))

            # Try enabling video, after re-enabling camera feed
            robot.enable_camera_feed = True
            robot.viewer.show_video(timeout=5)
            robot.loop.run_until_complete(utilities.delay_close(10))

        except KeyboardInterrupt:
            print("------ image test aborted ------")

    print("------ finished testing camera feed ------")


if __name__ == '__main__':
    main()
