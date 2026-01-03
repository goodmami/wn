
"""
Wordnet Interface.
"""

__all__ = (
    '__version__',
    'Wordnet',
    'download',
    'add',
    'add_lexical_resource',
    'remove',
    'export',
    'projects',
    'lexicons',
    'Lexicon',
    'word',
    'words',
    'lemmas',
    'Word',
    'Form',
    'Pronunciation',
    'Tag',
    'sense',
    'senses',
    'Sense',
    'Example',
    'Count',
    'synset',
    'synsets',
    'Synset',
    'Definition',
    'Relation',
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
from wn._add import add, add_lexical_resource, remove
from wn._export import export
from wn._download import download
from wn._lexicon import Lexicon
from wn._core import (
    Word, Form, Pronunciation, Tag,
    Sense, Example, Count,
    Synset, Definition,
    Relation,
)
from wn._module_functions import (
    projects,
    lexicons,
    word, words, lemmas,
    sense, senses,
    synset, synsets,
)
from wn._wordnet import Wordnet


__version__ = '0.14.0'
