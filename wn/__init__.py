
"""
Wordnet Interface.
"""

__all__ = (
    '__version__',
    'Wordnet',
    'download',
    'add',
    'remove',
    'export',
    'projects',
    'lexicons',
    'Lexicon',
    'word',
    'words',
    'Word',
    'Form',
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
from wn._add import add, remove
from wn._export import export
from wn._download import download
from wn._core import (
    projects,
    lexicons, Lexicon,
    word, words, Word, Form,
    sense, senses, Sense,
    synset, synsets, Synset,
    Wordnet
)
