

__all__ = (
    '__version__',
    'WordNet',
    'add',
    'synset',
    'synsets',
    'lemma',
)

from wn._meta import __version__
from wn._api import add, synset, synsets, lemma
from wn.wordnet import WordNet
