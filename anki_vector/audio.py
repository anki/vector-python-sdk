# Copyright (c) 2019 Anki, Inc.
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

"""Support for accessing Vector's audio.

Vector's speakers can be used for playing user-provided audio.
TODO Ability to access the Vector's audio stream to come.

The :class:`AudioComponent` class defined in this module is made available as
:attr:`anki_vector.robot.Robot.audio` and can be used to play audio data on the robot.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['AudioComponent']

import asyncio
from concurrent import futures
from enum import Enum
import time
import wave
from google.protobuf.text_format import MessageToString
from . import util
from .connection import on_connection_thread
from .exceptions import VectorExternalAudioPlaybackException
from .messaging import protocol


MAX_ROBOT_AUDIO_CHUNK_SIZE = 1024  # 1024 is maximum, larger sizes will fail
DEFAULT_FRAME_SIZE = MAX_ROBOT_AUDIO_CHUNK_SIZE // 2


class RobotVolumeLevel(Enum):
    """Use these values for setting the master audio volume.  See :meth:`set_master_volume`

    Note that muting the robot is not supported from the SDK.
    """
    LOW = 0
    MEDIUM_LOW = 1
    MEDIUM = 2
    MEDIUM_HIGH = 3
    HIGH = 4


class AudioComponent(util.Component):
    """Handles audio on Vector.

    The AudioComponent object plays audio data to Vector's speaker.
    Ability to access the Vector's audio stream to come.

    The :class:`anki_vector.robot.Robot` or :class:`anki_vector.robot.AsyncRobot` instance
    owns this audio component.

    .. testcode::

        import anki_vector

        with anki_vector.Robot() as robot:
            robot.audio.stream_wav_file('../examples/sounds/vector_alert.wav')
    """

    # TODO restore audio feed code when ready

    def __init__(self, robot):
        super().__init__(robot)
        self._is_shutdown = False
        # don't create asyncio.Events here, they are not thread-safe
        self._is_active_event = None
        self._done_event = None

    @on_connection_thread(requires_control=False)
    async def set_master_volume(self, volume: RobotVolumeLevel) -> protocol.MasterVolumeResponse:
        """Sets Vector's master volume level.

        Note that muting the robot is not supported from the SDK.

        .. testcode::

            import anki_vector
            from anki_vector import audio

            with anki_vector.Robot(behavior_control_level=None) as robot:
                robot.audio.set_master_volume(audio.RobotVolumeLevel.MEDIUM_HIGH)

        :param volume: the robot's desired volume
        """

        volume_request = protocol.MasterVolumeRequest(volume_level=volume.value)
        return await self.conn.grpc_interface.SetMasterVolume(volume_request)

    def _open_file(self, filename):
        _reader = wave.open(filename, 'rb')
        _params = _reader.getparams()
        self.logger.info("Playing audio file %s", filename)

        if _params.sampwidth != 2 or _params.nchannels != 1 or _params.framerate > 16025 or _params.framerate < 8000:
            raise VectorExternalAudioPlaybackException(
                f"Audio format must be 8000-16025 hz, 16 bits, 1 channel.  "
                f"Found {_params.framerate} hz/{_params.sampwidth*8} bits/{_params.nchannels} channels")

        return _reader, _params

    async def _request_handler(self, reader, params, volume):
        """Handles generating request messages for the AudioPlaybackStream."""
        frames = params.nframes  # 16 bit samples, not bytes

        # send preparation message
        msg = protocol.ExternalAudioStreamPrepare(audio_frame_rate=params.framerate, audio_volume=volume)
        msg = protocol.ExternalAudioStreamRequest(audio_stream_prepare=msg)

        yield msg
        await asyncio.sleep(0)  # give event loop a chance to process messages

        # count of full and partial chunks
        total_chunks = (frames + DEFAULT_FRAME_SIZE - 1) // DEFAULT_FRAME_SIZE
        curr_chunk = 0
        start_time = time.time()
        self.logger.debug("Starting stream time %f", start_time)

        while frames > 0 and not self._done_event.is_set():
            read_count = min(frames, DEFAULT_FRAME_SIZE)
            audio_data = reader.readframes(read_count)
            msg = protocol.ExternalAudioStreamChunk(audio_chunk_size_bytes=len(audio_data), audio_chunk_samples=audio_data)
            msg = protocol.ExternalAudioStreamRequest(audio_stream_chunk=msg)
            yield msg
            await asyncio.sleep(0)

            # check if streaming is way ahead of audio playback time
            elapsed = time.time() - start_time
            expected_data_count = elapsed * params.framerate
            time_ahead = (curr_chunk * DEFAULT_FRAME_SIZE - expected_data_count) / params.framerate
            if time_ahead > 1.0:
                self.logger.debug("waiting %f to catchup chunk %f", time_ahead - 0.5, curr_chunk)
                await asyncio.sleep(time_ahead - 0.5)
            frames = frames - read_count
            curr_chunk += 1
            if curr_chunk == total_chunks:
                # last chunk:  time to stop stream
                msg = protocol.ExternalAudioStreamComplete()
                msg = protocol.ExternalAudioStreamRequest(audio_stream_complete=msg)

                yield msg
                await asyncio.sleep(0)

        reader.close()

        # Need the done message from the robot
        await self._done_event.wait()
        self._done_event.clear()

    @on_connection_thread(requires_control=True)
    async def stream_wav_file(self, filename, volume=50):
        """ Plays audio using Vector's speakers.

        .. testcode::

            import anki_vector

            with anki_vector.Robot() as robot:
                robot.audio.stream_wav_file('../examples/sounds/vector_alert.wav')

        :param filename: the filename/path to the .wav audio file
        :param volume: the audio playback level (0-100)
        """

        # TODO make this support multiple simultaneous sound playback
        if self._is_active_event is None:
            self._is_active_event = asyncio.Event()

        if self._is_active_event.is_set():
            raise VectorExternalAudioPlaybackException("Cannot start audio when another sound is playing")

        if volume < 0 or volume > 100:
            raise VectorExternalAudioPlaybackException("Volume must be between 0 and 100")
        _file_reader, _file_params = self._open_file(filename)
        playback_error = None
        self._is_active_event.set()

        if self._done_event is None:
            self._done_event = asyncio.Event()

        try:
            async for response in self.grpc_interface.ExternalAudioStreamPlayback(self._request_handler(_file_reader, _file_params, volume)):
                self.logger.info("ExternalAudioStream %s", MessageToString(response, as_one_line=True))
                response_type = response.WhichOneof("audio_response_type")
                if response_type == 'audio_stream_playback_complete':
                    playback_error = None
                elif response_type == 'audio_stream_buffer_overrun':
                    playback_error = response_type
                elif response_type == 'audio_stream_playback_failyer':
                    playback_error = response_type
                self._done_event.set()
        except asyncio.CancelledError:
            self.logger.debug('Audio Stream future was cancelled.')
        except futures.CancelledError:
            self.logger.debug('Audio Stream handler task was cancelled.')
        finally:
            self._is_active_event = None
            self._done_event = None

        if playback_error is not None:
            raise VectorExternalAudioPlaybackException(f"Error reported during audio playback {playback_error}")
