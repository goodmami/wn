
__all__ = (
    '__version__',
    'WordNet',
    'get_project_info',
    'download',
    'add',
    'synset',
    'synsets',
    'lemma',
    'Error',
)

from wn._exceptions import Error
from wn._meta import __version__
from wn._projects import get_project_info
from wn._store import add
from wn._download import download
from wn._api import synset, synsets, sense
from wn.wordnet import WordNet
