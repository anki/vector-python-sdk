"""
Contains functions that ensure the game process.
"""
import logging
import os
import random
from time import sleep

import flask
import requests
from dotenv import load_dotenv
from flask.sessions import SessionMixin

from fortune_wheel.run import flask_app

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

RANDOM_WORD_KEY = os.environ.get("RANDOM_WORD_KEY")
RAPID_API_KEY = os.environ.get("RAPID_API_KEY")
logger = logging.getLogger(__name__)


class GameException(Exception):
    """Game exception class."""

    def __init__(self, message=''):
        self.message = message
        super().__init__(self.message)


def shutdown_server():
    """End of the game. Manual flask completion."""
    print('Завершение игры...')
    os._exit(0)


def getting_random_word(word_type: str) -> str:
    """Getting a random word from the API."""
    try:
        url = 'https://api.api-ninjas.com/v1/randomword'
        result = requests.get(url, headers={'X-Api-Key': RANDOM_WORD_KEY}, params={'type': word_type})
        if result.status_code == requests.codes.ok:
            return result.json()['word'].lower()
        raise GameException(message='Something wrong with api-ninjas.com')
    except GameException as ex:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        logger.error(message)
        return ''


def start_game(conf_dict: list) -> tuple[str, str]:
    """Getting the translation of the hidden word from the API."""
    try:
        word_type = conf_dict.pop()
        word = getting_random_word(word_type)
        if word:
            url = "https://microsoft-translator-text.p.rapidapi.com/translate"

            querystring = {"api-version": "3.0", "to[0]": "ru", "textType": "plain", "profanityAction": "NoAction"}

            payload = [{"Text": word}]
            headers = {
                "content-type": "application/json",
                "X-RapidAPI-Key": RAPID_API_KEY,
                "X-RapidAPI-Host": "microsoft-translator-text.p.rapidapi.com"
            }
            response = requests.request("POST", url, json=payload, headers=headers, params=querystring)
            if response.status_code == requests.codes.ok:
                return word, response.json()[0]['translations'][0]['text']
        raise GameException(message='Something wrong with microsoft-translator-text.p.rapidapi.com')
    except GameException as ex:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        logger.error(message)
        return '', 'Извините, что-то пошло не так...'


def get_random_letter(letters_list: list, weights: list) -> str:
    """Returns Returns a random letter of the English alphabet
    according to the weights (frequency of occurrence of this letter in English)."""
    return random.choices(letters_list, weights)[0]


def put_data_to_session(hidden_word: str, letters_list: list, letters_weights: list):
    """Puts the initial data into the session."""
    game_data = {
        'hidden_word': hidden_word,
        'letters_list': letters_list,
        'letters_weights': letters_weights,
        'guessed_letters': [],
        'wrong_letters': [],
        'need_to_guess_letters': list(set(hidden_word)),
    }
    flask.session.update(game_data)
    flask.session.modified = True


def game_process(current_letter, robot_turn=True, guessed=False, game_over=False):
    """
    The main process of processing player moves.
    Checks whether the player or robot has guessed the letter.
    Adds the current letters to the lists of already chosen correct and incorrect letters.
    Checks whether the word has been guessed completely.
    Updates session data.
    """
    try:
        game_data = flask.session
        if robot_turn:
            while not current_letter or current_letter in game_data['guessed_letters'] \
                    or current_letter in game_data['wrong_letters']:
                current_letter = get_random_letter(game_data['letters_list'],
                                                   game_data['letters_weights']).lower()

        if current_letter in game_data['need_to_guess_letters']:
            guessed = True
            repeat = put_letter_in_list(current_letter, game_data, 'guessed_letters')
        else:
            repeat = put_letter_in_list(current_letter, game_data, 'wrong_letters')

        flask.session.update(game_data)
        flask.session.modified = True

        if set(game_data['need_to_guess_letters']) == set(game_data['guessed_letters']):
            game_over = True

        if robot_turn:
            vector = flask_app.vector_import.vector
            vector.behavior.say_text(current_letter)

        return {
            'current_letter': current_letter,
            'repeat': repeat,
            'guessed': guessed,
            'game_over': game_over
        }
    except GameException as ex:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        logger.error(message)
        return {
            'current_letter': 'Извините, что-то сломалось :(',
            'repeat': False,
            'guessed': guessed,
            'game_over': True
        }
    except Exception as err:
        raise GameException(message=f'Something wrong with game_process script: '
                                    f'{type(err).__name__}, {err.args}')


def put_letter_in_list(current_letter: str, game_data: SessionMixin, game_data_list_name: str) -> bool:
    """Adds the current letters to the lists of already chosen correct and incorrect letters."""
    if current_letter not in game_data[game_data_list_name]:
        game_data[game_data_list_name].append(current_letter)
        return False
    return True


def robot_emotions(robot_wins: bool) -> None:
    """Determines the emotions of the robot depending on whether he won or lost."""
    try:
        vector = flask_app.vector_import.vector
        sleep(1.5)
        robot_reaction = 'GreetAfterLongTime' if robot_wins else 'FrustratedByFailureMajor'
        end_text = 'Yippee!!! I won!' if robot_wins else 'Congratulations...'
        vector.behavior.say_text(end_text)
        vector.anim.play_animation_trigger(robot_reaction)
    except GameException as ex:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        logger.error(message)
    except Exception as err:
        raise GameException(message=f'Something wrong with game_process script: '
                                    f'{type(err).__name__}, {err.args}')
    finally:
        return
