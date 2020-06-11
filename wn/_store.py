
import shelve
from pathlib import Path

dbdir = Path.home() / '.wn_data'


def get_synset(id: str):
    with shelve.open(str(dbdir / 'synsets')) as db:
        return db[id]


def get_lemma(id: str):
    with shelve.open(str(dbdir / 'lemmas')) as db:
        return db[id]
