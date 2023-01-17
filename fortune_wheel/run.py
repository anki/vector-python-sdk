# !/home/marina/PycharmProjects/Vector-robot/Envs/bin/python3
"""
Starting the game.
"""

import logging
import logging.config
import os
import sys
import webbrowser
from threading import Thread
from time import sleep

from dotenv import load_dotenv

import anki_vector
from fortune_wheel import flask_app
from fortune_wheel.config import LOGGING_CONFIG

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

RAPID_API_KEY = os.environ.get('RAPID_API_KEY')
flask_app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY')
logging.config.dictConfig(LOGGING_CONFIG)

logger = logging.getLogger(__name__)


class VectorImportClass:
    """
    The class required to be able to import a robot object.
    """

    def __init__(self, robot):
        self.vector = robot


class RunFlask:
    """The class is a redesigned flask_helpers mini library by the Vector developers.
    I took from it only what we need for the game.
    """
    enable_flask_logging = False
    open_page = True
    open_page_delay = 1.0
    new_flag = 0
    auto_raise = True
    running = False

    def __init__(self, app, host_ip, host_port):
        self.app = app
        self.ip = host_ip
        self.port = str(host_port)

    def run_flask(self):
        """
        Run the Flask webserver on specified host and port
        optionally also open that same host:port page in your browser to connect.
        Also, disable logging in Flask (it's enabled by default).
        """
        if not self.enable_flask_logging:
            logger.setLevel(logging.ERROR)
        if self.open_page:
            self.delayed_open_web_browser(f"http://{self.ip}:{self.port}")
        self.app.run(host=self.ip, port=self.port, use_evalex=False, threaded=True)

    def delayed_open_web_browser(self, url, specific_browser=None):
        """
        we add a delay (dispatched in another thread) to open the page so that the flask webserver is open
        before the webpage requests any data.
        """
        thread = Thread(target=self.sleep_and_open_web_browser,
                        kwargs=dict(url=url, specific_browser=specific_browser))
        thread.daemon = True
        thread.start()
        self.running = True

    def sleep_and_open_web_browser(self, url, specific_browser):
        """
        E.g. On OSX the following would use the Chrome browser app from that location
        specific_browser = 'open -a /Applications/Google\ Chrome.app %s'.
        """
        sleep(self.open_page_delay)
        browser = webbrowser
        if specific_browser:
            browser = webbrowser.get(specific_browser)
        browser.open(url, new=self.new_flag, autoraise=self.auto_raise)


def run(current_app=flask_app, count_connections=1):
    """The main script for starting the game and establishing a connection with the robot."""
    game_process = RunFlask(current_app, '127.0.0.1', 5000)
    while not game_process.running:
        try:
            if count_connections >= 10:
                print('Соединение не состоялось. Возможно, Вектор устал и ему нужно подзарядиться...')
                break
            print(f'Попытка #{count_connections} установки соединения с роботом...')
            args = anki_vector.util.parse_command_args()
            with anki_vector.AsyncRobot(args.serial, enable_face_detection=True,
                                        enable_custom_object_detection=True) as robot:
                current_app.vector_import = VectorImportClass(robot)
                robot.behavior.say_text("Let's play!")
                game_process.run_flask()
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            logger.error(message)
            print(f'Попытка #{count_connections} установки соединения с роботом не удалась. Пробуем еще раз...')
            count_connections += 1


if __name__ == '__main__':
    try:
        run()
    except KeyboardInterrupt as e:
        print('If you want to finish the game, click Finish in the web application.')
    except anki_vector.exceptions.VectorConnectionException as e:
        sys.exit("A connection error occurred: %s" % e)
