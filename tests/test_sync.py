#!/usr/bin/env python3

"""
Test Synchronizer to make sure it works properly in all combinations:
* Synchronous robot using with syntax
* Synchronous robot using try finally syntax
* Asynchronous robot using with syntax
* Asynchronous robot using try finally syntax
* Lastly disconnecting and reconnecting with the same robot
"""

import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import anki_vector  # pylint: disable=wrong-import-position


def main():
    """main execution"""
    args = anki_vector.util.parse_command_args()

    print("------ begin testing sync ------")

    def test_subscriber(event_type, event):
        """test that subscriptions work"""
        print(f"Subscriber called for: {event_type} = {event}")

    print("------ Synchronous Robot using with ------")
    with anki_vector.Robot(args.serial) as robot:
        robot.events.subscribe('robot_state', test_subscriber)
        robot.anim.play_animation("anim_blackjack_victorwin_01")

    print("------ Synchronous Robot using with ------")
    with anki_vector.Robot(args.serial) as robot:
        robot.events.subscribe('test1', test_subscriber)
        robot.anim.play_animation("anim_blackjack_victorwin_01")
        robot.events.unsubscribe('test1', test_subscriber)
        robot.events.unsubscribe('test1', test_subscriber)
        robot.motors.set_wheel_motors(100.0, -100.0)

    time.sleep(2)

    print("------ Synchronous Robot using try finally ------")
    robot = anki_vector.Robot(args.serial)
    robot.events.subscribe('test1', test_subscriber)
    try:
        robot.connect()
        robot.anim.play_animation("anim_blackjack_victorwin_01")
        robot.motors.set_wheel_motors(-100.0, 100.0)
    finally:
        robot.disconnect()

    time.sleep(2)

    print("------ Asynchronous Robot using with ------")
    with anki_vector.AsyncRobot(args.serial) as robot:
        robot.events.subscribe('robot_state', test_subscriber)
        robot.anim.play_animation("anim_blackjack_victorwin_01").wait_for_completed()
        robot.motors.set_wheel_motors(-100.0, 100.0).wait_for_completed()

    time.sleep(2)

    print("------ Asynchronous Robot using try finally ------")
    robot = anki_vector.AsyncRobot(args.serial)
    robot.events.subscribe('robot_state', test_subscriber)
    try:
        robot.connect()
        robot.anim.play_animation("anim_blackjack_victorwin_01").wait_for_completed()
        robot.motors.set_wheel_motors(100.0, -100.0).wait_for_completed()
    finally:
        robot.disconnect()

    time.sleep(2)

    print("------ Repeated Robot using try finally ------")
    # Reuse the same robot from a previous connection
    try:
        robot.connect()
        robot.anim.play_animation("anim_blackjack_victorwin_01").wait_for_completed()
        robot.motors.set_wheel_motors(0.0, 0.0).wait_for_completed()
    finally:
        robot.disconnect()

    print("------ finish testing sync ------")


if __name__ == "__main__":
    main()
