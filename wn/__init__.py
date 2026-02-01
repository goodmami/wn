"""
Wordnet Interface.
"""

__all__ = (
    "ConfigurationError",
    "Count",
    "DatabaseError",
    "Definition",
    "Error",
    "Example",
    "Form",
    "Lexicon",
    "ProjectError",
    "Pronunciation",
    "Relation",
    "Sense",
    "Synset",
    "Tag",
    "WnWarning",
    "Word",
    "Wordnet",
    "__version__",
    "add",
    "add_lexical_resource",
    "download",
    "export",
    "lemmas",
    "lexicons",
    "projects",
    "remove",
    "reset_database",
    "sense",
    "senses",
    "synset",
    "synsets",
    "word",
    "words",
)

from wn._add import add, add_lexical_resource, remove
from wn._config import config  # noqa: F401
from wn._core import (
    Count,
    Definition,
    Example,
    Form,
    Pronunciation,
    Relation,
    Sense,
    Synset,
    Tag,
    Word,
)
from wn._download import download
from wn._exceptions import (
    ConfigurationError,
    DatabaseError,
    Error,
    ProjectError,
    WnWarning,
)
from wn._export import export
from wn._lexicon import Lexicon
from wn._module_functions import (
    lemmas,
    lexicons,
    projects,
    reset_database,
    sense,
    senses,
    synset,
    synsets,
    word,
    words,
)
from wn._wordnet import Wordnet

__version__ = "1.0.0rc0"
