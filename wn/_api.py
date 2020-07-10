
from typing import List

from wn._models import Word, Synset, Sense
from wn import _store


def word(id: str) -> Word:
    return _store.get_entry(id)


def words(form: str = None,
          pos: str = None,
          lgcode: str = None,
          project: str = None) -> List[Word]:
    return _store.find_entries(form=form, pos=pos, lgcode=lgcode, project=project)


def synset(id: str) -> Synset:
    return _store.get_synset(id)


def synsets(form: str = None,
            pos: str = None,
            lgcode: str = None,
            project: str = None) -> List[Synset]:
    return _store.find_synsets(form=form, pos=pos, lgcode=lgcode, project=project)


def sense(id: str) -> Sense:
    return _store.get_sense(id)
