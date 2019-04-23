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

"""
Class and enumeration related to voice commands received by Vector.

When under SDK behavior control, recognized voice commands will be sent as
events.  SDK users can respond with their own scripted actions.

"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['UserIntentEvent', 'UserIntent']

from enum import Enum


class UserIntentEvent(Enum):
    """List of UserIntent events available to the SDK.

    Vector's voice recognition allows for variation in
    grammar and word selection, so the examples are not
    the only way to invoke the voice commands.

    This list reflect only the voice commands available
    to the SDK, as some are not available for development
    use."""
    #: example  "How old are you?"
    character_age = 0
    #: example  "Check the timer."
    check_timer = 1
    #: example  "Go explore."
    explore_start = 2
    #: example  "Stop the timer."
    global_stop = 3
    #: example  "Goodbye!"
    greeting_goodbye = 4
    #: example  "Good morning!"
    greeting_goodmorning = 5
    #: example  "Hello!"
    greeting_hello = 6
    #: example  "I hate you."
    imperative_abuse = 7
    #: example  "Yes."
    imperative_affirmative = 8
    #: example  "I'm sorry."
    imperative_apology = 9
    #: example  "Come here."
    imperative_come = 10
    #: example  "Dance."
    imperative_dance = 11
    #: example  "Fetch your cube."
    imperative_fetchcube = 12
    #: example  "Find your cube."
    imperative_findcube = 13
    #: example  "Look at me."
    imperative_lookatme = 14
    #: example  "I love you."
    imperative_love = 15
    #: example  "Good Robot."
    imperative_praise = 16
    #: example  "No."
    imperative_negative = 17
    #: example  "Bad Robot."
    imperative_scold = 18
    #: example  "Volume 2."
    imperative_volumelevel = 19
    #: example  "Volume up."
    imperative_volumeup = 20
    #: example  "Volume down."
    imperative_volumedown = 21
    #: example  "Go forward."
    movement_forward = 22
    #: example  "Go backward."
    movement_backward = 23
    #: example  "Turn left."
    movement_turnleft = 24
    #: example  "Turn right."
    movement_turnright = 25
    #: example  "Turn around."
    movement_turnaround = 26
    #: example  "I have a question."
    knowledge_question = 27
    #: example  "What's my name?"
    names_ask = 28
    #: example  "Play a game."
    play_anygame = 29
    #: example  "Play a trick."
    play_anytrick = 30
    #: example  "Let's play Blackjack."
    play_blackjack = 31
    #: example  "Fist bump."
    play_fistbump = 32
    #: example  "Pick up your cube."
    play_pickupcube = 33
    #: example  "Pop a wheelie."
    play_popawheelie = 34
    #: example  "Roll your cube."
    play_rollcube = 35
    #: example  "Happy holidays!"
    seasonal_happyholidays = 36
    #: example  "Happy new year!"
    seasonal_happynewyear = 37
    #: example  "Set timer for 10 minutes"
    set_timer = 38
    #: example  "What time is it?"
    show_clock = 39
    #: example  "Take a selfie."
    take_a_photo = 40
    #: example  "What is the weather report?"
    weather_response = 41


class UserIntent:
    """Class for containing voice command information from the event stream.
    This class, and the contained :class:`UserIntentEvent` include all of the
    voice commands that the SDK can intercept.

    Some UserIntents include information returned from the cloud and used
    when evaluating the voice commands.  This information can be parsed as
    a JSON formatted string.

    .. testcode::

        import json
        import threading

        import anki_vector
        from anki_vector.events import Events
        from anki_vector.user_intent import UserIntent, UserIntentEvent

        def on_user_intent(robot, event_type, event, done):
            user_intent = UserIntent(event)
            if user_intent.intent_event is UserIntentEvent.weather_response:
                data = json.loads(user_intent.intent_data)
                print(f"Weather report for {data['speakableLocationString']}: "
                      f"{data['condition']}, temperature {data['temperature']} degrees")
                done.set()

        with anki_vector.Robot() as robot:
            done = threading.Event()
            robot.events.subscribe(on_user_intent, Events.user_intent, done)

            print('------ Vector is waiting to be asked "Hey Vector!  What is the weather report?" Press ctrl+c to exit early ------')

            try:
                if not done.wait(timeout=10):
                    print('------ Vector never heard a request for the weather report ------')
            except KeyboardInterrupt:
                pass

    :param event: an event containing UserIntent data
    """

    def __init__(self, event):
        self._intent_event = UserIntentEvent(event.intent_id)
        self._intent_data = event.json_data

    @property
    def intent_event(self) -> UserIntentEvent:
        """ This returns the voice command event as a UserIntentEvent"""
        return self._intent_event

    @property
    def intent_data(self) -> str:
        """
        This gives access to any voice command specific data in JSON format.

        Some voice commands contain information from processing.  For example, asking Vector
        "Hey Vector, what is the weather?" will return the current location and the weather
        forecast.

        Voice commands without additional information will have an empty intent_data.
        """
        return self._intent_data
