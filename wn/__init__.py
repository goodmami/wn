
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
from wn._db import is_schema_compatible
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

if not is_schema_compatible():
    installed = '\n  '.join(f'{lex.id}:{lex.version}' for lex in lexicons())
    raise Error(
        "Wn's schema has changed and is no longer compatible with the "
        f"database. Please move or delete {config.database_path} and "
        "rebuild it. Note that the following lexicons are currently "
        f"installed:\n  {installed}"
    )
