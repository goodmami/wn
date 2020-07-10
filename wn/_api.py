
from typing import List

from wn._models import Word, Synset, Sense
from wn import _store


def word(id: str) -> Word:
    return _store.get_entry(id)


def synset(id: str) -> Synset:
    return _store.get_synset(id)


def synsets(form: str = None,
            id: str = None,
            ili: str = None,
            pos: str = None,
            lgcode: str = None,
            project: str = None) -> List[Synset]:
    return []


def sense(id: str) -> Sense:
    pass
