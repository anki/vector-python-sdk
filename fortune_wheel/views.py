"""
Game app views.
"""

import logging
import os

from dotenv import load_dotenv
from flask import render_template, jsonify, request, redirect

from config import ENG_LETTERS, ENG_LETTERS_WEIGHTS, WORD_TYPE
from fortune_wheel.game import start_game, put_data_to_session, game_process, robot_emotions, shutdown_server
from fortune_wheel.run import flask_app

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

RAPID_API_KEY = os.environ.get("RAPID_API_KEY")
flask_app.config['SECRET_KEY'] = os.environ.get("FLASK_SECRET_KEY")
logger = logging.getLogger(__name__)


@flask_app.route("/")
def index():
    """The view allows to initiate a game, get a random word that needs to be guessed
    and its translation, length of hidden word to render a start board (tableau)."""
    word, translated_word = start_game([WORD_TYPE])
    if word:
        put_data_to_session(word, ENG_LETTERS, ENG_LETTERS_WEIGHTS)
        return render_template("fortune_wheel.html",
                               title='Fortune Wheel', word=word, translated_word=translated_word,
                               letters_number=len(word))
    return redirect(location="/", code=500)


@flask_app.route('/game_turn', methods=['GET'])
def game_turn():
    """The view required to transmit data about the currently selected letter
    and the current player for further processing.
    Returns data about the state of the game.
    """
    current_letter = request.values['letter_key'].lower() if 'letter_key' in request.values else None
    result = game_process(current_letter=current_letter,
                          robot_turn=int(request.values['robot_turn']), )
    return jsonify({'key_value': result['current_letter'].upper(),
                    'repeat': result['repeat'],
                    'guessed': result['guessed'],
                    'game_over': result['game_over'],
                    })


@flask_app.route('/robot_reaction', methods=['GET'])
def robot_reaction():
    """The view that triggers the robot's reaction to the end of the game,
    depending on whether he guessed the last letter."""
    if 'robot_wins' in request.values:
        robot_wins = bool(int(request.values['robot_wins']))
        robot_emotions(robot_wins)
        return jsonify({'robot_wins': robot_wins})
    return jsonify({'robot_wins': False})


@flask_app.get('/shutdown')
def shutdown():
    """The view that triggers the end of the game."""
    shutdown_server()
    return 'Server shutting down...'
