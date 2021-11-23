
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
    'Pronunciation',
    'Tag',
    'sense',
    'senses',
    'Sense',
    'Count',
    'synset',
    'synsets',
    'Synset',
    'ili',
    'ilis',
    'ILI',
    'Error',
    'DatabaseError',
    'ConfigurationError',
    'ProjectError',
    'WnWarning',
)

from wn._exceptions import (
    Error,
    DatabaseError,
    ConfigurationError,
    ProjectError,
    WnWarning,
)
from wn._config import config  # noqa: F401
from wn._add import add, remove
from wn._export import export
from wn._download import download
from wn._core import (
    projects,
    lexicons, Lexicon,
    word, words, Word, Form, Pronunciation, Tag,
    sense, senses, Sense, Count,
    synset, synsets, Synset,
    ili, ilis, ILI,
    Wordnet
)

__version__ = '0.9.1'
