#!/usr/bin/env python3

"""
Calls specific messages on the robot, with expected results and verifies that the robot's responses match up
 - Exceptions will be raised if a response is of the wrong type, or has the wrong data
 - Exceptions will be raised if the interface defines a message that is neither on the test list or ignore list

Note that the following messages are intentionally not in here because they are unreliable due to environmental
factors (e.g., there is no cube, robot fails to drive onto the charger, robot might not be able to move to the
requested pose due to a wall, etc.):
 - DriveOnCharger/DriveOffCharger
 - GoToPose
 - MeetVictor
"""

import asyncio
import logging
import os
import sys

from google.protobuf.json_format import MessageToJson

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
import anki_vector  # pylint: disable=wrong-import-position

from anki_vector.messaging import protocol  # pylint: disable=wrong-import-position
from anki_vector.messaging import client  # pylint: disable=wrong-import-position

Interface = client.ExternalInterfaceServicer

# Both the EventStream and RobotStream should be kicked off automatically when we initialize a
# connection.while I feel it could be useful to verify these events come from the robot in
# response to the correct stimula and that the robot state correctly represents its actual state,
# testing the scope of these two messages feels different from the other direct send->response
# cases and as it will probably require webots state management feels improper for a rapid smoke
# test.
#  - nicolas 06/18/18
MESSAGES_TO_IGNORE = [
    Interface.EventStream,
]


class TestResultMatches:
    """Result that matches"""
    _value = None

    def __init__(self, value):
        """Create a TestResultMatches object"""
        self._value = value

    def get_target_type(self):
        """Get the expected return type"""
        return type(self._value)

    def test_with(self, target):
        """test with"""
        errors = []

        expected_type = type(self._value)
        expected_fields = [a[1] for a in self._value.ListFields()]

        target_type = type(target)
        target_fields = [a[1] for a in target.ListFields()]

        # Casting as string makes the equality check work
        if str(target_type) != str(expected_type):
            errors.append(
                'TypeError: received output of type {0} when expecting output of type {1}'.format(
                    target_type, expected_type))

        elif len(expected_fields) != len(target_fields):
            errors.append(
                'TypeError: received output that appears to be a different type or contains different contents {0} than the expected output type {1}.  received contents [{2}] while [{3}] expected.'.format(
                    target_type,
                    expected_type,
                    target_fields,
                    expected_fields))

        else:
            # This does not perform a deep comparison, which is difficult to
            # implement in a generic way
            for idx, expected in enumerate(expected_fields):
                if target_fields[idx] != expected:
                    errors.append(
                        'ValueError: received output with incorrect response {0}, was expecting {1}, failure occurred with field "{2}"'.format(
                            str(target_fields), str(expected_fields), str(
                                target_fields[idx])))
        return errors


class TestResultIsTypeWithStatusAndFieldNames:
    """Result with status and field names"""
    _expected_type = None
    _status = None
    _field_names = []

    def __init__(self, expected_type, status, field_names):
        """Create a TestResultIsTypeWithStatusAndFieldNames object"""
        self._expected_type = expected_type
        self._status = status
        self._field_names = field_names

    def get_target_type(self):
        """Get the expected return type"""
        return self._expected_type

    def test_with(self, target):
        """test with"""
        errors = []

        target_type = type(target)
        target_field_names = target.DESCRIPTOR.fields_by_name.keys()

        # Casting as string makes the equality check work
        if str(target_type) != str(self._expected_type):
            errors.append(
                'TypeError: received output of type {0} when expecting output of type {1}'.format(
                    target_type, self._expected_type))

        elif len(self._field_names) + 1 != len(target.ListFields()):
            errors.append(
                'TypeError: received output of type {0} that has {1} fields when {2} were expected'.format(
                    target_type, len(
                        target.ListFields()), len(
                            self._field_names) + 1))

        elif target.status != self._status:
            errors.append('TypeError: received output with status \'{0}\' when \'{1}\' was expected'.format(
                str(target.status), str(self._status)))

        else:

            for field in self._field_names:
                if field not in target_field_names:
                    errors.append(
                        'ValueError: received output with without the expected field "{0}"'.format(field))
        return errors


MESSAGES_TO_TEST = [
    # DriveWheels message
    (Interface.DriveWheels,
     protocol.DriveWheelsRequest(left_wheel_mmps=0.0,
                                 right_wheel_mmps=0.0,
                                 left_wheel_mmps2=0.0,
                                 right_wheel_mmps2=0.0),
     TestResultMatches(protocol.DriveWheelsResponse(status=protocol.ResponseStatus(code=protocol.ResponseStatus.REQUEST_PROCESSING)))),  # pylint: disable=no-member
    # MoveHead message
    (Interface.MoveHead,
     protocol.MoveHeadRequest(speed_rad_per_sec=0.0),
     TestResultMatches(protocol.MoveHeadResponse(status=protocol.ResponseStatus(code=protocol.ResponseStatus.REQUEST_PROCESSING)))),  # pylint: disable=no-member
    # MoveLift message
    (Interface.MoveLift,
     protocol.MoveLiftRequest(speed_rad_per_sec=0.0),
     TestResultMatches(protocol.MoveLiftResponse(status=protocol.ResponseStatus(code=protocol.ResponseStatus.REQUEST_PROCESSING)))),  # pylint: disable=no-member
    # PlayAnimation message
    (Interface.PlayAnimation,
     protocol.PlayAnimationRequest(animation=protocol.Animation(name='anim_blackjack_victorwin_01'), loops=1),
     TestResultMatches(protocol.PlayAnimationResponse(status=protocol.ResponseStatus(code=protocol.ResponseStatus.RESPONSE_RECEIVED), result=1))),  # pylint: disable=no-member
    # ListAnimations message
    (Interface.ListAnimations,
     protocol.ListAnimationsRequest(),
     TestResultIsTypeWithStatusAndFieldNames(protocol.ListAnimationsResponse, protocol.ResponseStatus(code=protocol.ResponseStatus.RESPONSE_RECEIVED), ['animation_names'])),  # pylint: disable=no-member
    # DisplayFaceImageRGB message
    (Interface.DisplayFaceImageRGB,
     protocol.DisplayFaceImageRGBRequest(face_data=bytes(anki_vector.color.Color(rgb=[255, 0, 0]).rgb565_bytepair * 17664), duration_ms=1000, interrupt_running=True),
     TestResultMatches(protocol.DisplayFaceImageRGBResponse(status=protocol.ResponseStatus(code=protocol.ResponseStatus.REQUEST_PROCESSING)))),  # pylint: disable=no-member
    # UpdateEnrolledFaceByID message
    (Interface.UpdateEnrolledFaceByID,
     protocol.UpdateEnrolledFaceByIDRequest(
         face_id=1, old_name="Bobert", new_name="Boberta"),
     TestResultMatches(protocol.UpdateEnrolledFaceByIDResponse(status=protocol.ResponseStatus(code=protocol.ResponseStatus.REQUEST_PROCESSING)))),  # pylint: disable=no-member
    # SetFaceToEnroll message
    (Interface.SetFaceToEnroll,
     protocol.SetFaceToEnrollRequest(name="Boberta",
                                     observed_id=1,
                                     save_id=0,
                                     save_to_robot=True,
                                     say_name=True,
                                     use_music=True),
     TestResultMatches(protocol.SetFaceToEnrollResponse(status=protocol.ResponseStatus(code=protocol.ResponseStatus.REQUEST_PROCESSING)))),  # pylint: disable=no-member
    # CancelFaceEnrollment message
    (Interface.CancelFaceEnrollment,
     protocol.CancelFaceEnrollmentRequest(),
     TestResultMatches(protocol.CancelFaceEnrollmentResponse(status=protocol.ResponseStatus(code=protocol.ResponseStatus.REQUEST_PROCESSING)))),  # pylint: disable=no-member
    # EraseEnrolledFaceByID message
    (Interface.EraseEnrolledFaceByID,
     protocol.EraseEnrolledFaceByIDRequest(face_id=1),
     TestResultMatches(protocol.EraseEnrolledFaceByIDResponse(status=protocol.ResponseStatus(code=protocol.ResponseStatus.REQUEST_PROCESSING)))),  # pylint: disable=no-member
    # EraseAllEnrolledFaces message
    (Interface.EraseAllEnrolledFaces,
     protocol.EraseAllEnrolledFacesRequest(),
     TestResultMatches(protocol.EraseAllEnrolledFacesResponse(status=protocol.ResponseStatus(code=protocol.ResponseStatus.REQUEST_PROCESSING)))),  # pylint: disable=no-member
    # RequestEnrolledNames message
    (Interface.RequestEnrolledNames,
     protocol.RequestEnrolledNamesRequest(),
     TestResultMatches(protocol.RequestEnrolledNamesResponse(status=protocol.ResponseStatus(code=protocol.ResponseStatus.RESPONSE_RECEIVED), faces=[]))),  # pylint: disable=no-member
    # EnableVisionMode message
    (client.ExternalInterfaceServicer.EnableVisionMode,
     protocol.EnableVisionModeRequest(mode=protocol.VisionMode.Value(
         "VISION_MODE_DETECTING_FACES"), enable=True),
     TestResultMatches(protocol.EnableVisionModeResponse(status=protocol.ResponseStatus(code=protocol.ResponseStatus.REQUEST_PROCESSING)))),  # pylint: disable=no-member

    # DriveStraight message
    (client.ExternalInterfaceServicer.DriveStraight,
     protocol.DriveStraightRequest(speed_mmps=0.0,
                                   dist_mm=0.0,
                                   should_play_animation=False,
                                   id_tag=protocol.FIRST_SDK_TAG + 1),
     TestResultMatches(protocol.DriveStraightResponse(status=protocol.ResponseStatus(code=protocol.ResponseStatus.RESPONSE_RECEIVED),    # pylint: disable=no-member
                                                      result=protocol.ActionResult(code=protocol.ActionResult.ACTION_RESULT_SUCCESS)))),  # pylint: disable=no-member

    # TurnInPlace message
    (client.ExternalInterfaceServicer.TurnInPlace,
     protocol.TurnInPlaceRequest(angle_rad=0.0,
                                 speed_rad_per_sec=0.0,
                                 accel_rad_per_sec2=0.0,
                                 tol_rad=0.0,
                                 is_absolute=False,
                                 id_tag=protocol.FIRST_SDK_TAG + 2),
     TestResultMatches(protocol.TurnInPlaceResponse(status=protocol.ResponseStatus(code=protocol.ResponseStatus.RESPONSE_RECEIVED),    # pylint: disable=no-member
                                                    result=protocol.ActionResult(code=protocol.ActionResult.ACTION_RESULT_SUCCESS)))),  # pylint: disable=no-member

    # SetHeadAngle message
    (client.ExternalInterfaceServicer.SetHeadAngle,
     protocol.SetHeadAngleRequest(angle_rad=0.0,
                                  max_speed_rad_per_sec=0.0,
                                  accel_rad_per_sec2=0.0,
                                  duration_sec=0.0,
                                  id_tag=protocol.FIRST_SDK_TAG + 3),
     TestResultMatches(protocol.SetHeadAngleResponse(status=protocol.ResponseStatus(code=protocol.ResponseStatus.RESPONSE_RECEIVED),    # pylint: disable=no-member
                                                     result=protocol.ActionResult(code=protocol.ActionResult.ACTION_RESULT_SUCCESS)))),  # pylint: disable=no-member

    # SetLiftHeight message
    (client.ExternalInterfaceServicer.SetLiftHeight,
     protocol.SetLiftHeightRequest(height_mm=0.0,
                                   max_speed_rad_per_sec=0.0,
                                   accel_rad_per_sec2=0.0,
                                   duration_sec=0.0,
                                   id_tag=protocol.FIRST_SDK_TAG + 4),
     TestResultMatches(protocol.SetLiftHeightResponse(status=protocol.ResponseStatus(code=protocol.ResponseStatus.RESPONSE_RECEIVED),    # pylint: disable=no-member
                                                      result=protocol.ActionResult(code=protocol.ActionResult.ACTION_RESULT_SUCCESS)))),  # pylint: disable=no-member

    # ConnectCube message
    (client.ExternalInterfaceServicer.ConnectCube,
     protocol.ConnectCubeRequest(),
     TestResultIsTypeWithStatusAndFieldNames(protocol.ConnectCubeResponse,
                                             protocol.ResponseStatus(code=protocol.ResponseStatus.RESPONSE_RECEIVED),  # pylint: disable=no-member
                                             ["success", "factory_id"])),

    # DisconnectCube message
    (client.ExternalInterfaceServicer.DisconnectCube,
     protocol.DisconnectCubeRequest(),
     TestResultMatches(protocol.DisconnectCubeResponse(status=protocol.ResponseStatus(code=protocol.ResponseStatus.REQUEST_PROCESSING)))),  # pylint: disable=no-member

    # FlashCubeLights message
    (client.ExternalInterfaceServicer.FlashCubeLights,
     protocol.FlashCubeLightsRequest(),
     TestResultMatches(protocol.FlashCubeLightsResponse(status=protocol.ResponseStatus(code=protocol.ResponseStatus.REQUEST_PROCESSING)))),  # pylint: disable=no-member

    # SetPreferredCube message
    (client.ExternalInterfaceServicer.SetPreferredCube,
     protocol.SetPreferredCubeRequest(factory_id="11:11:11:11:11:11"),
     TestResultMatches(protocol.SetPreferredCubeResponse(status=protocol.ResponseStatus(code=protocol.ResponseStatus.REQUEST_PROCESSING)))),  # pylint: disable=no-member

    # ForgetPreferredCube message
    (client.ExternalInterfaceServicer.ForgetPreferredCube,
     protocol.ForgetPreferredCubeRequest(),
     TestResultMatches(protocol.ForgetPreferredCubeResponse(status=protocol.ResponseStatus(code=protocol.ResponseStatus.REQUEST_PROCESSING)))),  # pylint: disable=no-member

    # SetCubeLights message
    # Note: We don't have the proper object id from the ConnectCube response, but we can test that the message is properly sent
    (client.ExternalInterfaceServicer.SetCubeLights,
     protocol.SetCubeLightsRequest(
         object_id=1,
         on_color=[anki_vector.color.green.int_color] * 4,
         off_color=[anki_vector.color.blue.int_color] * 4,
         on_period_ms=[1000] * 4,
         off_period_ms=[1000] * 4,
         transition_on_period_ms=[1000] * 4,
         transition_off_period_ms=[1000] * 4,
         offset=[0, 0, 0, 0],
         relative_to_x=0.0,
         relative_to_y=0.0,
         rotate=False,
         make_relative=protocol.SetCubeLightsRequest.OFF),  # pylint: disable=no-member
     TestResultMatches(protocol.SetCubeLightsResponse(status=protocol.ResponseStatus(code=protocol.ResponseStatus.REQUEST_PROCESSING)))),  # pylint: disable=no-member

    # TODO: Enable testcase once issue described below is resolved
    # This test currently fails since the BatteryStateResponse message may contain default values, and the assertion to
    # to check the number of fields retrieved does not account for default fields and thus causes a mismatch.
    # # BatteryState message
    # (client.ExternalInterfaceServicer.BatteryState,
    #  protocol.BatteryStateRequest(),
    #  TestResultIsTypeWithStatusAndFieldNames(protocol.BatteryStateResponse,
    #                                          protocol.ResponseStatus(code=protocol.ResponseStatus.RESPONSE_RECEIVED),  # pylint: disable=no-member
    #                                          ["battery_level", "battery_volts", "is_charging", "is_on_charger_platform"])),

    # VersionState message
    (client.ExternalInterfaceServicer.VersionState,
     protocol.VersionStateRequest(),
     TestResultIsTypeWithStatusAndFieldNames(protocol.VersionStateResponse,
                                             protocol.ResponseStatus(code=protocol.ResponseStatus.RESPONSE_RECEIVED),  # pylint: disable=no-member
                                             ["os_version", "engine_build_id"])),

    # NetworkState message
    (client.ExternalInterfaceServicer.NetworkState,
     protocol.NetworkStateRequest(),
     TestResultIsTypeWithStatusAndFieldNames(protocol.NetworkStateResponse,
                                             protocol.ResponseStatus(code=protocol.ResponseStatus.RESPONSE_RECEIVED),  # pylint: disable=no-member
                                             ["network_stats"])),

    # SayText message
    (client.ExternalInterfaceServicer.SayText,
     protocol.SayTextRequest(text="hello", use_vector_voice=True),
     TestResultIsTypeWithStatusAndFieldNames(protocol.SayTextResponse,
                                             protocol.ResponseStatus(code=protocol.ResponseStatus.RESPONSE_RECEIVED),  # pylint: disable=no-member
                                             ["state"])),

    # NOTE: Add additional messages here
]


async def test_message(robot, message_name, message_input, test_class, errors):
    """Test a single message"""
    # The message_src is used mostly so we can easily verify that the name is supported by the servicer.
    # In terms of actually making the call its simpler to invoke on the robot
    message_call = getattr(robot.conn.grpc_interface, message_name)

    print(
        "Sending: \"{0}\"".format(MessageToJson(message_input,
                                                including_default_value_fields=True,
                                                preserving_proto_field_name=True)))
    result = await message_call(message_input)
    print(
        "Received: \"{0}\"".format(MessageToJson(result,
                                                 including_default_value_fields=True,
                                                 preserving_proto_field_name=True)))

    new_errors = test_class.test_with(result)

    for err in new_errors:
        errors.append('{0}: {1}'.format(message_name, err))


async def run_message_test(robot, message, expected_test_list, errors):
    """Run the test on a messages"""
    message_call = message[0]
    input_data = message[1]
    test_class = message[2]
    target_type = test_class.get_target_type()

    message_name = message_call.__name__
    # make sure we are using the correct input class for this message
    expected_input_type = expected_test_list[message_name]['input'].name
    received_input_type = type(input_data).__name__
    if received_input_type != expected_input_type:
        errors.append('InputData: A test for a message of type {0} expects input data of the type {1}, but {2} was supplied'.format(message_name,
                                                                                                                                    expected_input_type,
                                                                                                                                    received_input_type))
        return

    # make sure we are using the correct output class for this message
    expected_output_type = expected_test_list[message_name]['output'].name
    received_output_type = target_type.__name__
    if received_output_type != expected_output_type:
        errors.append('OutputData: A test for a message of type {0} expects output data of the type {1}, but {2} was supplied'.format(message_name,
                                                                                                                                      expected_output_type,
                                                                                                                                      received_output_type))
        return

    print("testing {}".format(message_name))
    await test_message(robot, message_name, input_data, test_class, errors)
    del expected_test_list[message_name]


async def run_message_tests(robot, future):
    """Run all the tests on messages"""
    warnings = []
    errors = []

    # compile a list of all functions in the interface and the input/output
    # classes we expect them to utilize
    all_methods_in_interface = protocol.DESCRIPTOR.services_by_name['ExternalInterface'].methods
    expected_test_list = {}
    for method in all_methods_in_interface:
        expected_test_list[method.name] = {
            'input': method.input_type,
            'output': method.output_type,
        }

    # strip out any messages that we're explicitly ignoring
    for ignored in MESSAGES_TO_IGNORE:
        del expected_test_list[ignored.__name__]

    # run through all listed test cases
    for msg in MESSAGES_TO_TEST:
        # make sure we are expecting this message
        name = msg[0].__name__
        if name in expected_test_list:
            await run_message_test(robot, msg, expected_test_list, errors)
        else:
            errors.append('NotImplemented: A test was defined for the {0} message, which is not in the interface'.format(name))

    # squawk if we missed any messages in the inteface
    if not expected_test_list:
        warnings.append('NotImplemented: The following messages exist in the interface and do not have a corresponding test: {0}'.format(str(expected_test_list)))

    future.set_result({'warnings': warnings, 'errors': errors})


def main():
    """main execution"""
    args = anki_vector.util.parse_command_args()

    logger = logging.getLogger('anki_vector')
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler('robot_messages_debug.log')
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    with anki_vector.Robot(args.serial, default_logging=False) as robot:
        print("------ beginning tests ------")

        future = asyncio.Future()
        robot.loop.run_until_complete(run_message_tests(robot, future))

        test_results = future.result()
        warnings = test_results['warnings']
        errors = test_results['errors']

        if warnings:
            print("------ warnings! ------")
            for warn in warnings:
                print(warn)

        print('\n')
        if not errors:
            print("------ all tests finished successfully! ------")
            print('\n')
        else:
            print("------ tests finished with {0} errors! ------".format(len(errors)))
            for err in errors:
                print(err)
            sys.exit(1)


if __name__ == "__main__":
    main()
