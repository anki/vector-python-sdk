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

"""Face recognition and enrollment.

Vector is capable of recognizing human faces, tracking their position and rotation
("pose") and assigning names to them via an enrollment process.

The :class:`anki_vector.world.World` object keeps track of faces the robot currently
knows about, along with those that are currently visible to the camera.

Each face is assigned a :class:`Face` object, which generates a number of
observable events whenever the face is observed, has its ID updated.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['Expression', 'Face', 'FaceComponent']

from enum import Enum
import math
import time

from . import sync, util
from .messaging import protocol


class Expression(Enum):
    """Facial expressions that Vector can distinguish.

    Facial expression not recognized.
    Call :func:`anki_vector.robot.Robot.enable_vision_mode` to enable recognition.
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


class Face:
    """A single face that Vector has detected.

    May represent a face that has previously been enrolled, in which case
    :attr:`name` will hold the name that it was enrolled with.

    Each Face instance has a :attr:`face_id` integer - This may change if
    Vector later gets an improved view and makes a different prediction about
    which face he is looking at.
    """

    def __init__(self, face_id=None):
        self._face_id = face_id
        self._updated_face_id = None
        self._name = ''
        self._expression = None
        self._last_observed_time: int = None
        self._last_observed_robot_timestamp: int = None
        self._pose = None
        self._face_rect = None

        # Individual expression values histogram, sums to 100 (Exception: all
        # zero if expression=Unknown)
        self._expression_score = None

        # Face landmarks
        self._left_eye = None
        self._right_eye = None
        self._nose = None
        self._mouth = None

    def __repr__(self):
        return (f"<{self.__class__.__name__} Face id: {self.face_id} "
                f"Updated face id: {self.updated_face_id} Name: {self.name} "
                f"Expression: {protocol.FacialExpression.Name(self.expression)}>")

    # TODO sample code
    @property
    def face_id(self):
        """The internal ID assigned to the face.

        This value can only be assigned once as it is static in the engine.

        :getter: Returns the face ID
        :setter: Sets the face ID
        """
        return self._face_id if self._updated_face_id is None else self._updated_face_id

    # TODO sample code
    @face_id.setter
    def face_id(self, face_id):
        if self._face_id is not None:
            raise ValueError(f"Cannot change face ID once set (from {self._face_id} to {face_id})")
        self._face_id = face_id

    @property
    def has_updated_face_id(self) -> bool:
        """True if this face been updated / superseded by a face with a new ID.

        .. code-block:: python

            was_face_originally_unrecognized_but_is_now_recognized = face.has_updated_face_id
        """
        return self._updated_face_id is not None

    # TODO sample code
    @property
    def updated_face_id(self) -> int:
        """The ID for the face that superseded this one (if any, otherwise :meth:`face_id`)"""
        if self._updated_face_id:
            return self._updated_face_id
        return self._face_id

    # TODO sample code
    @property
    def name(self):
        """string: The name Vector has associated with the face.

        This string will be empty if the face is not recognized or enrolled.
        """
        return self._name

    # TODO sample code
    @property
    def last_observed_time(self) -> float:
        """The time the face was last observed by the robot.
        ``None`` if the face has not yet been observed.
        """
        return self._last_observed_time

    @property
    def time_since_last_seen(self) -> float:
        """The time since this face was last seen (math.inf if never)

        .. code-block:: python

            last_seen_time = face.time_since_last_seen
        """
        if self._last_observed_time is None:
            return math.inf
        return time.time() - self._last_observed_time

    # TODO sample code
    @property
    def timestamp(self):
        """int: Timestamp of event"""
        return self._last_observed_robot_timestamp

    # TODO sample code
    @property
    def pose(self):
        """:class:`anki_vector.util.Pose`: Position and rotation of the face observed"""
        return self._pose

    # TODO sample code
    @property
    def face_rect(self) -> util.ImageRect:
        """Rect representing position of face."""
        return self._face_rect

    # TODO sample code
    @property
    def expression(self):
        """string: The facial expression Vector has recognized on the face.

        Will be :attr:`Expression.UNKNOWN` by default if you haven't called
        :meth:`anki_vector.robot.Robot.enable_vision_mode` to enable
        the facial expression estimation. Otherwise it will be equal to one of:
        :attr:`Expression.NEUTRAL`, :attr:`Expression.HAPPINESS`,
        :attr:`Expression.SURPRISE`, :attr:`Expression.ANGER`,
        or :attr:`Expression.SADNESS`.
        """
        return self._expression

    # TODO sample code
    @property
    def expression_score(self):
        """int: The score/confidence that :attr:`expression` was correct.

        Will be 0 if expression is :attr:`Expression.UNKNOWN` (e.g. if
        :meth:`anki_vector.robot.Robot.enable_vision_mode` wasn't
        called yet). The maximum possible score is 100.
        """
        return self._expression_score

    # TODO sample code
    @property
    def left_eye(self):
        """sequence of tuples of float (x,y): points representing the outline of the left eye."""
        return self._left_eye

    # TODO sample code
    @property
    def right_eye(self):
        """sequence of tuples of float (x,y): points representing the outline of the right eye."""
        return self._right_eye

    # TODO sample code
    @property
    def nose(self):
        """sequence of tuples of float (x,y): points representing the outline of the nose."""
        return self._nose

    # TODO sample code
    @property
    def mouth(self):
        """sequence of tuples of float (x,y): points representing the outline of the mouth."""
        return self._mouth

    def unpack_face_stream_data(self, msg):
        """Unpacks the face observed stream data from Vector into a Face instance."""
        self._face_id = msg.face_id
        self._name = msg.name
        self._last_observed_time = time.time()
        self._last_observed_robot_timestamp = msg.timestamp
        self._pose = util.Pose(x=msg.pose.x, y=msg.pose.y, z=msg.pose.z,
                               q0=msg.pose.q0, q1=msg.pose.q1,
                               q2=msg.pose.q2, q3=msg.pose.q3,
                               origin_id=msg.pose.origin_id)
        self._face_rect = util.ImageRect(msg.img_rect.x_top_left,
                                         msg.img_rect.y_top_left,
                                         msg.img_rect.width,
                                         msg.img_rect.height)
        self._expression = msg.expression
        self._expression_score = msg.expression_values
        self._left_eye = msg.left_eye
        self._right_eye = msg.right_eye
        self._nose = msg.nose
        self._mouth = msg.mouth


class FaceComponent(util.Component):
    """Manage the state of the faces on the robot."""

    # TODO document, needs sample code and return value. It returns an array of LoadedKnownFace
    @sync.Synchronizer.wrap
    async def request_enrolled_names(self):
        req = protocol.RequestEnrolledNamesRequest()
        return await self.grpc_interface.RequestEnrolledNames(req)

    # TODO needs sample code
    @sync.Synchronizer.wrap
    async def update_enrolled_face_by_id(self, face_id: int, old_name: str, new_name: str):
        """Update the name enrolled for a given face.

        :param face_id: The ID of the face to rename.
        :param old_name: The old name of the face (must be correct, otherwise message is ignored).
        :param new_name: The new name for the face.
        """
        req = protocol.UpdateEnrolledFaceByIDRequest(faceID=face_id,
                                                     oldName=old_name, newName=new_name)
        return await self.grpc_interface.UpdateEnrolledFaceByID(req)

    # TODO needs sample code
    @sync.Synchronizer.wrap
    async def erase_enrolled_face_by_id(self, face_id: int):
        """Erase the enrollment (name) record for the face with this ID.

        :param face_id: The ID of the face to erase.
        """
        req = protocol.EraseEnrolledFaceByIDRequest(faceID=face_id)
        return await self.grpc_interface.EraseEnrolledFaceByID(req)

    # TODO needs sample code
    @sync.Synchronizer.wrap
    async def erase_all_enrolled_faces(self):
        """Erase the enrollment (name) records for all faces."""
        req = protocol.EraseAllEnrolledFacesRequest()
        return await self.grpc_interface.EraseAllEnrolledFaces(req)

    # TODO move out of face component? This is general to objects, not specific to faces? Move to new vision component? Needs sample code.
    # TODO improve list of modes as shown in docs
    @sync.Synchronizer.wrap
    async def enable_vision_mode(self, enable: bool, mode: protocol.VisionMode = protocol.VisionMode.Value("VISION_MODE_DETECTING_FACES")):
        """Enable a vision mode

        The vision system can be enabled for modes including the following:
        Marker detection: `VISION_MODE_DETECTING_MARKERS`
        Face detection and recognition: `VISION_MODE_DETECTING_FACES`
        Motion detection: `VISION_MODE_DETECTING_MOTION`

        :param enable: Enable/Disable the mode specified.
        :param mode: Specifies the vision mode to edit.
        """
        enable_vision_mode_request = protocol.EnableVisionModeRequest(mode=mode, enable=enable)
        return await self.grpc_interface.EnableVisionMode(enable_vision_mode_request)
