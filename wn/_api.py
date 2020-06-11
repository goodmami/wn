
from typing import List
from pathlib import Path

from wn._types import AnyPath
from wn._models import Synset, Lemma
from wn import _store


def add(source: AnyPath) -> None:
    source = Path(source)
    if source.suffix.lower() == 'xml':
        _add_lmf(source)
    else:
        raise Exception(f'unsupported wordnet format: {source!s}')


def _add_lmf(source):
    from wn import lmf
    lexicon = lmf.load(source)
    return []


def synset(id: str) -> Synset:
    pass


def synsets(form: str = None,
            id: str = None,
            ili: str = None,
            pos: str = None,
            lgcode: str = None,
            project: str = None) -> List[Synset]:
    return []


def lemma(id: str) -> Lemma:
    pass
