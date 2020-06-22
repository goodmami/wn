

__all__ = (
    '__version__',
    'WordNet',
    'get_project_info',
    'add',
    'synset',
    'synsets',
    'lemma',
    'Error',
)

from wn._exceptions import Error
from wn._meta import __version__
from wn._api import add, synset, synsets, lemma
from wn._projects import get_project_info
from wn.wordnet import WordNet
