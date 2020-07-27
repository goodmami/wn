
from typing import List

from wn._api import word, words, synset, synsets
from wn._models import Synset, Word


class WordNet:
    """
    Class for interacting with WordNet data.
    """

    def __init__(self, lexicon: str = None):
        self.lexicon = lexicon

    def word(self, id: str) -> Word:
        return word(id)

    def words(self, form: str = None, pos: str = None) -> List[Word]:
        return words(form=form, pos=pos, lexicon=self.lexicon)

    def synset(self, id: str) -> Synset:
        return synset(id)

    def synsets(self, form: str = None, pos: str = None) -> List[Synset]:
        return synsets(form=form, pos=pos, lexicon=self.lexicon)
