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

"""Face recognition and enrollment.

Vector is capable of recognizing human faces, tracking their position and rotation
("pose") and assigning names to them via an enrollment process.

The :class:`anki_vector.world.World` object keeps track of faces the robot currently
knows about, along with those that are currently visible to the camera.

Each face is assigned a :class:`Face` object, which generates a number of
observable events whenever the face is observed or when the face id is updated.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['Expression', 'Face', 'FaceComponent']

from enum import Enum
from typing import List

from . import connection, util, objects, events
from .messaging import protocol

#: Length of time in seconds to go without receiving an observed event before
#: assuming that Vector can no longer see a face.
FACE_VISIBILITY_TIMEOUT = objects.OBJECT_VISIBILITY_TIMEOUT


class EvtFaceObserved():  # pylint: disable=too-few-public-methods
    """Triggered whenever a face is visually identified by the robot.

    A stream of these events are produced while a face is visible to the robot.
    Each event has an updated image_rect field.

    See EvtFaceAppeared if you only want to know when a face first
    becomes visible.

    .. testcode::

        import time

        import anki_vector
        from anki_vector.events import Events
        from anki_vector.util import degrees

        def handle_face_observed(robot, event_type, event):
            # This will be called whenever an EvtFaceObserved is dispatched -
            # whenever an face comes into view.
            print(f"--------- Vector observed an face --------- \\n{event.face}")

        with anki_vector.Robot(enable_face_detection = True,
                               show_viewer=True) as robot:
            robot.events.subscribe(handle_face_observed, Events.face_observed)

            # If necessary, move Vector's Head and Lift in position to see a face
            robot.behavior.set_lift_height(0.0)
            robot.behavior.set_head_angle(degrees(45.0))

            time.sleep(5.0)

    :param face: The Face instance that was observed
    :param image_rect: An :class:`anki_vector.util.ImageRect`: defining where the face is within Vector's camera view
    :param name: The name of the face
    :param pose: The :class:`anki_vector.util.Pose`: defining the position and rotation of the face
    """

    def __init__(self, face, image_rect: util.ImageRect, name, pose: util.Pose):
        self.face = face
        self.image_rect = image_rect
        self.name = name
        self.pose = pose


class EvtFaceAppeared():  # pylint: disable=too-few-public-methods
    """Triggered whenever a face is first visually identified by a robot.

    This differs from EvtFaceObserved in that it's only triggered when
    a face initially becomes visible.  If it disappears for more than
    FACE_VISIBILITY_TIMEOUT seconds and then is seen again, a
    EvtFaceDisappeared will be dispatched, followed by another
    EvtFaceAppeared event.

    For continuous tracking information about a visible face, see
    EvtFaceObserved.

    .. testcode::

        import time

        import anki_vector
        from anki_vector.events import Events
        from anki_vector.util import degrees

        def handle_face_appeared(robot, event_type, event):
            # This will be called whenever an EvtFaceAppeared is dispatched -
            # whenever an face comes into view.
            print(f"--------- Vector started seeing an face --------- \\n{event.face}")


        def handle_face_disappeared(robot, event_type, event):
            # This will be called whenever an EvtFaceDisappeared is dispatched -
            # whenever an face goes out of view.
            print(f"--------- Vector stopped seeing an face --------- \\n{event.face}")


        with anki_vector.Robot(enable_face_detection = True,
                               show_viewer=True) as robot:
            robot.events.subscribe(handle_face_appeared, Events.face_appeared)
            robot.events.subscribe(handle_face_disappeared, Events.face_disappeared)

            # If necessary, move Vector's Head and Lift in position to see a face
            robot.behavior.set_lift_height(0.0)
            robot.behavior.set_head_angle(degrees(45.0))

            time.sleep(5.0)

    :param face:'The Face instance that appeared
    :param image_rect: An :class:`anki_vector.util.ImageRect`: defining where the face is within Vector's camera view
    :param name: The name of the face
    :param pose: The :class:`anki_vector.util.Pose`: defining the position and rotation of the face
    """

    def __init__(self, face, image_rect: util.ImageRect, name, pose: util.Pose):
        self.face = face
        self.image_rect = image_rect
        self.name = name
        self.pose = pose


class EvtFaceDisappeared():  # pylint: disable=too-few-public-methods
    """Triggered whenever a face that was previously being observed is no longer visible.

    .. testcode::

        import time

        import anki_vector
        from anki_vector.events import Events
        from anki_vector.util import degrees

        def handle_face_appeared(robot, event_type, event):
            # This will be called whenever an EvtFaceAppeared is dispatched -
            # whenever an face comes into view.
            print(f"--------- Vector started seeing an face --------- \\n{event.face}")


        def handle_face_disappeared(robot, event_type, event):
            # This will be called whenever an EvtFaceDisappeared is dispatched -
            # whenever an face goes out of view.
            print(f"--------- Vector stopped seeing an face --------- \\n{event.face}")


        with anki_vector.Robot(enable_face_detection = True,
                               show_viewer=True) as robot:
            robot.events.subscribe(handle_face_appeared, Events.face_appeared)
            robot.events.subscribe(handle_face_disappeared, Events.face_disappeared)

            # If necessary, move Vector's Head and Lift in position to see a face
            robot.behavior.set_lift_height(0.0)
            robot.behavior.set_head_angle(degrees(45.0))

            time.sleep(5.0)

    :param face: The Face instance that is no longer being observed
    """

    def __init__(self, face):
        self.face = face


class Expression(Enum):
    """Facial expressions that Vector can distinguish.

    Facial expression not recognized.
    Call :func:`anki_vector.robot.Robot.vision.enable_face_detection(detect_faces=True)` to enable recognition.
    """
    UNKNOWN = protocol.FacialExpression.Value("EXPRESSION_UNKNOWN")
    #: Facial expression neutral
    NEUTRAL = protocol.FacialExpression.Value("EXPRESSION_NEUTRAL")
    #: Facial expression happiness
    HAPPINESS = protocol.FacialExpression.Value("EXPRESSION_HAPPINESS")
    #: Facial expression surprise
    SURPRISE = protocol.FacialExpression.Value("EXPRESSION_SURPRISE")
    #: Facial expression anger
    ANGER = protocol.FacialExpression.Value("EXPRESSION_ANGER")
    #: Facial expression sadness
    SADNESS = protocol.FacialExpression.Value("EXPRESSION_SADNESS")


class Face(objects.ObservableObject):
    """A single face that Vector has detected.

    May represent a face that has previously been enrolled, in which case
    :attr:`name` will hold the name that it was enrolled with.

    Each Face instance has a :attr:`face_id` integer - This may change if
    Vector later gets an improved view and makes a different prediction about
    which face he is looking at.
    """

    def __init__(self,
                 robot,
                 pose: util.Pose,
                 image_rect: util.ImageRect,
                 face_id: int,
                 name: str,
                 expression: str,
                 expression_score: List[int],
                 left_eye: List[protocol.CladPoint],
                 right_eye: List[protocol.CladPoint],
                 nose: List[protocol.CladPoint],
                 mouth: List[protocol.CladPoint],
                 instantiation_timestamp: float,
                 **kw):

        super(Face, self).__init__(robot, **kw)

        self._face_id = face_id
        self._updated_face_id = None
        self._name = name
        self._expression = expression

        # Individual expression values histogram, sums to 100
        # (Exception: all zero if expression=Unknown)
        self._expression_score = expression_score

        # Face landmarks
        self._left_eye = left_eye
        self._right_eye = right_eye
        self._nose = nose
        self._mouth = mouth

        self._on_observed(pose, image_rect, instantiation_timestamp)

        self._robot.events.subscribe(self._on_face_observed,
                                     events.Events.robot_observed_face)

        self._robot.events.subscribe(self._on_face_id_changed,
                                     events.Events.robot_changed_observed_face_id)

    def __repr__(self):
        return (f"<{self.__class__.__name__} Face id: {self.face_id} "
                f"Updated face id: {self.updated_face_id} Name: {self.name} "
                f"Expression: {protocol.FacialExpression.Name(self.expression)}>")

    def teardown(self):
        """All faces will be torn down by the world when no longer needed."""
        self._robot.events.unsubscribe(self._on_face_observed,
                                       events.Events.robot_observed_face)

        self._robot.events.unsubscribe(self._on_face_id_changed,
                                       events.Events.robot_changed_observed_face_id)

    @property
    def face_id(self) -> int:
        """The internal ID assigned to the face.

        This value can only be assigned once as it is static in the engine.

        :getter: Returns the face ID
        :setter: Sets the face ID

        .. testcode::

            import time

            import anki_vector
            from anki_vector.events import Events
            from anki_vector.util import degrees

            def test_subscriber(robot, event_type, event):
                print(f"Subscriber called for: {event_type} = {event}")

                for face in robot.world.visible_faces:
                    print(f"Visible face id: {face.face_id}")

            with anki_vector.Robot(enable_face_detection=True) as robot:
                # If necessary, move Vector's Head and Lift to make it easy to see his face
                robot.behavior.set_head_angle(degrees(45.0))
                robot.behavior.set_lift_height(0.0)

                robot.events.subscribe(test_subscriber, Events.robot_changed_observed_face_id)
                robot.events.subscribe(test_subscriber, Events.robot_observed_face)

                print("------ show vector your face, press ctrl+c to exit early ------")
                try:
                    time.sleep(10)
                except KeyboardInterrupt:
                    robot.disconnect()
        """
        return self._face_id if self._updated_face_id is None else self._updated_face_id

    @face_id.setter
    def face_id(self, face_id: str):
        if self._face_id is not None:
            raise ValueError(f"Cannot change face ID once set (from {self._face_id} to {face_id})")
        self._face_id = face_id

    @property
    def has_updated_face_id(self) -> bool:
        """True if this face been updated / superseded by a face with a new ID.

        .. testcode::

            import time

            import anki_vector
            from anki_vector.events import Events
            from anki_vector.util import degrees

            def test_subscriber(robot, event_type, event):
                print(f"Subscriber called for: {event_type} = {event}")

                for face in robot.world.visible_faces:
                    was_face_originally_unrecognized_but_is_now_recognized = face.has_updated_face_id

            with anki_vector.Robot(enable_face_detection=True) as robot:
                # If necessary, move Vector's Head and Lift to make it easy to see his face
                robot.behavior.set_head_angle(degrees(45.0))
                robot.behavior.set_lift_height(0.0)

                robot.events.subscribe(test_subscriber, Events.robot_changed_observed_face_id)
                robot.events.subscribe(test_subscriber, Events.robot_observed_face)

                print("------ show vector your face, press ctrl+c to exit early ------")
                try:
                    time.sleep(10)
                except KeyboardInterrupt:
                    robot.disconnect()
        """
        return self._updated_face_id is not None

    @property
    def updated_face_id(self) -> int:
        """The ID for the face that superseded this one (if any, otherwise :meth:`face_id`)

        .. testcode::

            import time

            import anki_vector
            from anki_vector.events import Events
            from anki_vector.util import degrees

            def test_subscriber(robot, event_type, event):
                print(f"Subscriber called for: {event_type} = {event}")

                for face in robot.world.visible_faces:
                    print(f"Updated face id: {face.updated_face_id}")

            with anki_vector.Robot(enable_face_detection=True) as robot:
                # If necessary, move Vector's Head and Lift to make it easy to see his face
                robot.behavior.set_head_angle(degrees(45.0))
                robot.behavior.set_lift_height(0.0)

                robot.events.subscribe(test_subscriber, Events.robot_changed_observed_face_id)
                robot.events.subscribe(test_subscriber, Events.robot_observed_face)

                print("------ show vector your face, press ctrl+c to exit early ------")
                try:
                    time.sleep(10)
                except KeyboardInterrupt:
                    robot.disconnect()
        """
        if self._updated_face_id:
            return self._updated_face_id
        return self._face_id

    @property
    def name(self) -> str:
        """The name Vector has associated with the face.

        This string will be empty if the face is not recognized or enrolled.

        .. testcode::

            import time

            import anki_vector
            from anki_vector.events import Events
            from anki_vector.util import degrees

            def test_subscriber(robot, event_type, event):
                print(f"Subscriber called for: {event_type} = {event}")

                for face in robot.world.visible_faces:
                    print(f"Face name: {face.name}")

            with anki_vector.Robot(enable_face_detection=True) as robot:
                # If necessary, move Vector's Head and Lift to make it easy to see his face
                robot.behavior.set_head_angle(degrees(45.0))
                robot.behavior.set_lift_height(0.0)

                robot.events.subscribe(test_subscriber, Events.robot_changed_observed_face_id)
                robot.events.subscribe(test_subscriber, Events.robot_observed_face)

                print("------ show vector your face, press ctrl+c to exit early ------")
                try:
                    time.sleep(10)
                except KeyboardInterrupt:
                    robot.disconnect()
        """
        return self._name

    @property
    def expression(self) -> str:
        """The facial expression Vector has recognized on the face.

        Will be :attr:`Expression.UNKNOWN` by default if you haven't called
        :meth:`anki_vector.robot.Robot.vision.enable_face_detection(detect_faces=True, estimate_emotion=True)` to enable
        the facial expression estimation. Otherwise it will be equal to one of:
        :attr:`Expression.NEUTRAL`, :attr:`Expression.HAPPINESS`,
        :attr:`Expression.SURPRISE`, :attr:`Expression.ANGER`,
        or :attr:`Expression.SADNESS`.

        .. testcode::

            import time

            import anki_vector
            from anki_vector.events import Events
            from anki_vector.util import degrees

            def test_subscriber(robot, event_type, event):
                print(f"Subscriber called for: {event_type} = {event}")

                for face in robot.world.visible_faces:
                    print(f"Expression: {face.expression}")

            with anki_vector.Robot(enable_face_detection=True) as robot:
                # If necessary, move Vector's Head and Lift to make it easy to see his face
                robot.behavior.set_head_angle(degrees(45.0))
                robot.behavior.set_lift_height(0.0)

                robot.events.subscribe(test_subscriber, Events.robot_changed_observed_face_id)
                robot.events.subscribe(test_subscriber, Events.robot_observed_face)

                print("------ show vector your face, press ctrl+c to exit early ------")
                try:
                    time.sleep(10)
                except KeyboardInterrupt:
                    robot.disconnect()
        """
        return self._expression

    @property
    def expression_score(self) -> List[int]:
        """The score/confidence that :attr:`expression` was correct.

        Will be 0 if expression is :attr:`Expression.UNKNOWN` (e.g. if
        :meth:`anki_vector.robot.Robot.vision.enable_face_detection(detect_faces=True, estimate_emotion=True)` wasn't
        called yet). The maximum possible score is 100.

        .. testcode::

            import time

            import anki_vector
            from anki_vector.events import Events
            from anki_vector.util import degrees

            def test_subscriber(robot, event_type, event):
                print(f"Subscriber called for: {event_type} = {event}")

                for face in robot.world.visible_faces:
                    print(f"Expression score: {face.expression_score}")

            with anki_vector.Robot(enable_face_detection=True) as robot:
                # If necessary, move Vector's Head and Lift to make it easy to see his face
                robot.behavior.set_head_angle(degrees(45.0))
                robot.behavior.set_lift_height(0.0)

                robot.events.subscribe(test_subscriber, Events.robot_changed_observed_face_id)
                robot.events.subscribe(test_subscriber, Events.robot_observed_face)

                print("------ show vector your face, press ctrl+c to exit early ------")
                try:
                    time.sleep(10)
                except KeyboardInterrupt:
                    robot.disconnect()
        """
        return self._expression_score

    @property
    def left_eye(self) -> List[protocol.CladPoint]:
        """sequence of tuples of float (x,y): points representing the outline of the left eye.

        .. testcode::

            import time

            import anki_vector
            from anki_vector.events import Events
            from anki_vector.util import degrees

            def test_subscriber(robot, event_type, event):
                print(f"Subscriber called for: {event_type} = {event}")

                for face in robot.world.visible_faces:
                    print(f"Left eye: {face.left_eye}")

            with anki_vector.Robot(enable_face_detection=True) as robot:
                # If necessary, move Vector's Head and Lift to make it easy to see his face
                robot.behavior.set_head_angle(degrees(45.0))
                robot.behavior.set_lift_height(0.0)

                robot.events.subscribe(test_subscriber, Events.robot_changed_observed_face_id)
                robot.events.subscribe(test_subscriber, Events.robot_observed_face)

                print("------ show vector your face, press ctrl+c to exit early ------")
                try:
                    time.sleep(10)
                except KeyboardInterrupt:
                    robot.disconnect()
        """
        return self._left_eye

    @property
    def right_eye(self) -> List[protocol.CladPoint]:
        """sequence of tuples of float (x,y): points representing the outline of the right eye.

        .. testcode::

            import time

            import anki_vector
            from anki_vector.events import Events
            from anki_vector.util import degrees

            def test_subscriber(robot, event_type, event):
                print(f"Subscriber called for: {event_type} = {event}")

                for face in robot.world.visible_faces:
                    print(f"Right eye: {face.right_eye}")

            with anki_vector.Robot(enable_face_detection=True) as robot:
                # If necessary, move Vector's Head and Lift to make it easy to see his face
                robot.behavior.set_head_angle(degrees(45.0))
                robot.behavior.set_lift_height(0.0)

                robot.events.subscribe(test_subscriber, Events.robot_changed_observed_face_id)
                robot.events.subscribe(test_subscriber, Events.robot_observed_face)

                print("------ show vector your face, press ctrl+c to exit early ------")
                try:
                    time.sleep(10)
                except KeyboardInterrupt:
                    robot.disconnect()
        """
        return self._right_eye

    @property
    def nose(self) -> List[protocol.CladPoint]:
        """sequence of tuples of float (x,y): points representing the outline of the nose.

        .. testcode::

            import time

            import anki_vector
            from anki_vector.events import Events
            from anki_vector.util import degrees

            def test_subscriber(robot, event_type, event):
                print(f"Subscriber called for: {event_type} = {event}")

                for face in robot.world.visible_faces:
                    print(f"Nose: {face.nose}")

            with anki_vector.Robot(enable_face_detection=True) as robot:
                # If necessary, move Vector's Head and Lift to make it easy to see his face
                robot.behavior.set_head_angle(degrees(45.0))
                robot.behavior.set_lift_height(0.0)

                robot.events.subscribe(test_subscriber, Events.robot_changed_observed_face_id)
                robot.events.subscribe(test_subscriber, Events.robot_observed_face)

                print("------ show vector your face, press ctrl+c to exit early ------")
                try:
                    time.sleep(10)
                except KeyboardInterrupt:
                    robot.disconnect()
        """
        return self._nose

    @property
    def mouth(self) -> List[protocol.CladPoint]:
        """sequence of tuples of float (x,y): points representing the outline of the mouth.

        .. testcode::

            import time

            import anki_vector
            from anki_vector.events import Events
            from anki_vector.util import degrees

            def test_subscriber(robot, event_type, event):
                print(f"Subscriber called for: {event_type} = {event}")

                for face in robot.world.visible_faces:
                    print(f"Mouth: {face.mouth}")

            with anki_vector.Robot(enable_face_detection=True) as robot:
                # If necessary, move Vector's Head and Lift to make it easy to see his face
                robot.behavior.set_head_angle(degrees(45.0))
                robot.behavior.set_lift_height(0.0)

                robot.events.subscribe(test_subscriber, Events.robot_changed_observed_face_id)
                robot.events.subscribe(test_subscriber, Events.robot_observed_face)

                print("------ show vector your face, press ctrl+c to exit early ------")
                try:
                    time.sleep(10)
                except KeyboardInterrupt:
                    robot.disconnect()
        """
        return self._mouth

    #### Private Event Handlers ####

    def _on_face_observed(self, _robot, _event_type, msg):
        """Unpacks the face observed stream data from Vector into a Face instance."""
        if self._face_id == msg.face_id:

            pose = util.Pose(x=msg.pose.x, y=msg.pose.y, z=msg.pose.z,
                             q0=msg.pose.q0, q1=msg.pose.q1,
                             q2=msg.pose.q2, q3=msg.pose.q3,
                             origin_id=msg.pose.origin_id)
            image_rect = util.ImageRect(msg.img_rect.x_top_left,
                                        msg.img_rect.y_top_left,
                                        msg.img_rect.width,
                                        msg.img_rect.height)

            self._name = msg.name

            self._expression = msg.expression
            self._expression_score = msg.expression_values
            self._left_eye = msg.left_eye
            self._right_eye = msg.right_eye
            self._nose = msg.nose
            self._mouth = msg.mouth
            self._on_observed(pose, image_rect, msg.timestamp)

    def _on_face_id_changed(self, _robot, _event_type, msg):
        """Updates the face id when a tracked face (negative ID) is recognized and
        receives a positive ID or when face records get merged"""
        if self._face_id == msg.old_id:
            self._updated_face_id = msg.new_id


class FaceComponent(util.Component):
    """Manage the state of the faces on the robot."""

    @connection.on_connection_thread(requires_control=False)
    async def request_enrolled_names(self) -> protocol.RequestEnrolledNamesRequest:
        """Asks the robot for the list of names attached to faces that it can identify.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                name_data_list = robot.faces.request_enrolled_names()
                print(f"{name_data_list}")
        """
        req = protocol.RequestEnrolledNamesRequest()
        return await self.grpc_interface.RequestEnrolledNames(req)

    @connection.on_connection_thread(requires_control=False)
    async def update_enrolled_face_by_id(self, face_id: int, old_name: str, new_name: str):
        """Update the name enrolled for a given face.

        :param face_id: The ID of the face to rename.
        :param old_name: The old name of the face (must be correct, otherwise message is ignored).
        :param new_name: The new name for the face.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                robot.faces.update_enrolled_face_by_id(1, 'Hanns', 'Boris')
        """
        req = protocol.UpdateEnrolledFaceByIDRequest(face_id=face_id,
                                                     old_name=old_name, new_name=new_name)
        return await self.grpc_interface.UpdateEnrolledFaceByID(req)

    @connection.on_connection_thread(requires_control=False)
    async def erase_enrolled_face_by_id(self, face_id: int):
        """Erase the enrollment (name) record for the face with this ID.

        :param face_id: The ID of the face to erase.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                robot.faces.erase_enrolled_face_by_id(1)
        """
        req = protocol.EraseEnrolledFaceByIDRequest(face_id=face_id)
        return await self.grpc_interface.EraseEnrolledFaceByID(req)

    @connection.on_connection_thread(requires_control=False)
    async def erase_all_enrolled_faces(self):
        """Erase the enrollment (name) records for all faces.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                robot.faces.erase_all_enrolled_faces()
        """
        req = protocol.EraseAllEnrolledFacesRequest()
        return await self.grpc_interface.EraseAllEnrolledFaces(req)
