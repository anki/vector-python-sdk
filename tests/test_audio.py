#!/usr/bin/env python3

"""
Exports a wav clip from the robot's audio stream
"""

import os
import sys
from tempfile import gettempdir

try:
    from scipy.io import wavfile
except ImportError as exc:
    sys.exit("Cannot import scipy: Do `pip3 install scipy` to install")

import utilities
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import anki_vector  # pylint: disable=wrong-import-position

output_filename = 'audiosample.wav'


def main():
    """main execution"""
    args = anki_vector.util.parse_command_args()

    print("------ begin audio export test ------")

    with anki_vector.Robot(args.serial, enable_audio_feed=True) as robot:

        robot.loop.run_until_complete(utilities.delay_close(8))

        print('samples: {0}'.format(len(robot.audio.raw_audio_waveform_history)))

        output_folder = os.path.join(gettempdir(), 'vector_sdk')
        os.makedirs(output_folder, exist_ok=True)

        path = os.path.join(output_folder, output_filename)
        wavfile.write(path, anki_vector.messaging.protocol.PROCESSED_SAMPLE_RATE, robot.audio.raw_audio_waveform_history)

        print("------ finished audio export test, results saved to: {0} ------".format(path))


if __name__ == '__main__':
    main()
