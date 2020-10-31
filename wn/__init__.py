
"""
Wordnet Interface.
"""

__all__ = (
    '__version__',
    'WordNet',
    'download',
    'add',
    'remove',
    'lexicons',
    'Lexicon',
    'word',
    'words',
    'Word',
    'sense',
    'senses',
    'Sense',
    'synset',
    'synsets',
    'Synset',
    'Error',
    'Warning',
)

from wn._meta import __version__
from wn._exceptions import Error, Warning
from wn._config import config  # noqa: F401
from wn._db import add, remove
from wn._download import download
from wn._core import (
    lexicons, Lexicon,
    word, words, Word,
    sense, senses, Sense,
    synset, synsets, Synset,
    WordNet
)
