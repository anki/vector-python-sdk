"""
Stores settings such as the type of word (noun selected),
a list of letters of the English alphabet and their weights (frequency of occurrence in the language),
logging configure settings.
"""
from datetime import datetime

LOGGING_LEVEL = 'DEBUG'

WORD_TYPE = 'noun'

ENG_LETTERS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N',
               'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
ENG_LETTERS_WEIGHTS = [0.0817, 0.0149, 0.0278, 0.0425, 0.1270, 0.0223, 0.0202, 0.0609, 0.0697,
                       0.0015, 0.0077, 0.0403, 0.0241, 0.0675, 0.0751, 0.0193, 0.0010, 0.0599,
                       0.0633, 0.0906, 0.0276, 0.0098, 0.0236, 0.0015, 0.0197, 0.0007]

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'colored_console': {
           '()': 'coloredlogs.ColoredFormatter',
           'format': "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
           'datefmt': '%H:%M:%S'
        },
        'format_for_file': {
            'format': "%(asctime)s :: %(levelname)s :: %(funcName)s in %(filename)s (l:%(lineno)d) :: %(message)s",
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {
        'console': {
            'level': LOGGING_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'colored_console',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'level': LOGGING_LEVEL,
            'class': 'logging.FileHandler',
            'formatter': 'format_for_file',
            'filename': f'logs/{LOGGING_LEVEL}_{datetime.today().date()}.log'
        }
    },
    'loggers': {
        '': {
            'level': LOGGING_LEVEL,
            'handlers': ['console', 'file'],
        },
    },
}

"""
Information about weights taken from the 
https://www.m-teach.ru/reference-books/english-handbook/English-alphabet.html

Буква 	Частота
A 	8,17%
B 	1,49%
C 	2,78%
D 	4,25%
E 	12,70%
F 	2,23%
G 	2,02%
H 	6,09%
I 	6,97%
J 	0,15%
K 	0,77%
L 	4,03%
M 	2,41%
N 	6,75%
O 	7,51%
P 	1,93%
Q 	0,10%
R 	5,99%
S 	6,33%
T 	9,06%
U 	2,76%
V 	0,98%
W 	2,36%
X 	0,15%
Y 	1,97%
Z 	0,07%
"""
