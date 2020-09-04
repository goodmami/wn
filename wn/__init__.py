
"""
Wordnet Interface.
"""

__all__ = (
    '__version__',
    'WordNet',
    'download',
    'add',
    'word',
    'words',
    'synset',
    'synsets',
    'sense',
    'Error',
)


# This exception are defined here so the traceback says, e.g.,
# `wn.Error` and not `wn._exceptions.Error`; if this behavior can be
# cleanly implmented in some other way, then I'd be happy to move
# non-import code out of __init__.py

class Error(Exception):
    """Generic error class for invalid wordnet operations."""


from wn._meta import __version__
from wn._config import config
from wn._store import add
from wn._download import download
from wn._api import word, words, synset, synsets, sense
from wn.wordnet import WordNet
