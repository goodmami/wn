
"""
Wordnet Interface.
"""

__all__ = (
    '__version__',
    'Wordnet',
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
)

from wn._meta import __version__
from wn._exceptions import Error
from wn._config import config  # noqa: F401
from wn._db import add, remove
from wn._download import download
from wn._core import (
    lexicons, Lexicon,
    word, words, Word,
    sense, senses, Sense,
    synset, synsets, Synset,
    Wordnet
)
