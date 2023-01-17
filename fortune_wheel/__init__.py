"""
Initialization of the Flask application for game and imports.
"""

import sys
try:
    from flask import Flask
except ImportError:
    sys.exit("Cannot import from flask: Do `pip3 install --user flask` to install")

flask_app = Flask(__name__)

from fortune_wheel import views
