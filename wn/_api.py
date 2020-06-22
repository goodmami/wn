
from typing import List

from wn._models import Synset, Sense
from wn import _store


def synset(id: str) -> Synset:
    pass


def synsets(form: str = None,
            id: str = None,
            ili: str = None,
            pos: str = None,
            lgcode: str = None,
            project: str = None) -> List[Synset]:
    return []


def sense(id: str) -> Sense:
    pass
