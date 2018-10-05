#!/usr/bin/env python3

"""
Test say text
"""

import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import anki_vector  # pylint: disable=wrong-import-position


def main():
    args = anki_vector.util.parse_command_args()

    print("------ begin testing text-to-speech ------")

    with anki_vector.Robot(args.serial) as robot:
        robot.say_text("hello", use_vector_voice=True)
        time.sleep(1)  # Avoid overlapping messages
        robot.say_text("hello", use_vector_voice=False)

    print("------ end testing text-to-speech ------")


if __name__ == "__main__":
    main()
