
from typing import TypeVar, Optional, List, Tuple, Set, Iterator
import itertools

import wn
from wn import _db


class Word:
    __slots__ = 'id', 'pos', '_forms'

    def __init__(self, id: str, pos: str, forms: List[str]):
        self.id = id
        self.pos = pos
        self._forms = forms

    def __repr__(self) -> str:
        return f'Word({self.id!r})'

    def lemma(self) -> str:
        return self._forms[0]

    def forms(self) -> List[str]:
        return self._forms

    def senses(self) -> List['Sense']:
        iterable = _db.get_senses_for_entry(self.id)
        return list(itertools.starmap(Sense, iterable))

    def synsets(self) -> List['Synset']:
        return [sense.synset() for sense in self.senses()]

    def derived_words(self) -> List['Word']:
        return [derived_sense.word()
                for sense in self.senses()
                for derived_sense in sense.derivations()]


T = TypeVar('T', bound='_Relatable')


class _Relatable:
    __slots__ = 'id',

    def __init__(self):
        self.id: str = ''

    def get_related(self: T, relation: str) -> List[T]:
        raise NotImplementedError

    def antonyms(self: T) -> List[T]:
        return self.get_related('antonym')

    def similar(self: T) -> List[T]:
        return self.get_related('similar')

    def closure(self: T, relation: str) -> Iterator[T]:
        visited = set()
        queue = self.get_related(relation)
        while queue:
            relatable = queue.pop(0)
            if relatable.id not in visited:
                visited.add(relatable.id)
                yield relatable
                queue.extend(relatable.get_related(relation))

    def relation_paths(self: T, *args: str) -> Iterator[List[T]]:
        paths: List[Tuple[List[T], Set[str]]] = [([self], set([self.id]))]
        while paths:
            path, visited = paths.pop()
            related = [s for s in path[-1].get_related(*args) if s.id not in visited]
            if not related:
                yield path
            else:
                for synset in reversed(related):
                    new_path = list(path) + [synset]
                    new_visited = set(visited) | {synset.id}
                    paths.append((new_path, new_visited))


class Synset(_Relatable):
    __slots__ = 'pos', 'ili'

    def __init__(self, id: str, pos: str, ili: str = None):
        self.id = id
        self.pos = pos
        self.ili = ili

    def __repr__(self) -> str:
        return f'Synset({self.id!r})'

    def definition(self) -> Optional[str]:
        return next(iter(_db.get_definitions_for_synset(self.id)), None)

    def examples(self) -> List[str]:
        return _db.get_examples_for_synset(self.id)

    def senses(self) -> List['Sense']:
        iterable = _db.get_senses_for_synset(self.id)
        return list(itertools.starmap(Sense, iterable))

    def words(self) -> List[Word]:
        return [sense.word() for sense in self.senses()]

    def get_related(self, *args: str) -> List['Synset']:
        iterable = _db.get_synset_relations(self.id, args)
        return list(itertools.starmap(Synset, iterable))

    def hypernym_paths(self) -> Iterator[List['Synset']]:
        return self.relation_paths('hypernym', 'instance_hypernym')

    def holonyms(self) -> List['Synset']:
        return self.get_related(
            'holonym',
            'holo_location',
            'holo_member',
            'holo_part',
            'holo_portion',
            'holo_substance',
        )

    def meronyms(self) -> List['Synset']:
        return self.get_related(
            'meronym',
            'mero_location',
            'mero_member',
            'mero_part',
            'mero_portion',
            'mero_substance',
        )

    def hypernyms(self) -> List['Synset']:
        return self.get_related(
            'hypernym',
            'instance_hypernym'
        )

    def hyponyms(self) -> List['Synset']:
        return self.get_related(
            'hyponym',
            'instance_hyponym'
        )


class Sense(_Relatable):
    __slots__ = '_entry_id', '_synset_id'

    def __init__(self, id: str, entry_id: str, synset_id: str):
        self.id = id
        self._entry_id = entry_id
        self._synset_id = synset_id

    def __repr__(self) -> str:
        return f'Sense({self.id!r})'

    def word(self) -> Word:
        return Word(*next(_db.find_entries(id=self._entry_id)))

    def synset(self) -> Synset:
        return Synset(*next(_db.find_synsets(id=self._synset_id)))

    def get_related(self, *args: str) -> List['Sense']:
        iterable = _db.get_sense_relations(self.id, args)
        return list(itertools.starmap(Sense, iterable))

    def get_related_synsets(self, *args: str) -> List[Synset]:
        iterable = _db.get_sense_synset_relations(self.id, args)
        return list(itertools.starmap(Synset, iterable))

    def derivations(self) -> List['Sense']:
        return self.get_related('derivation')

    def pertainyms(self) -> List['Sense']:
        return self.get_related('pertainym')


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


def word(id: str, lexicon: str = None) -> Word:
    iterable = _db.find_entries(id=id, lexicon=lexicon)
    try:
        return Word(*next(iterable))
    except StopIteration:
        raise wn.Error(f'no such lexical entry: {id}')


def words(form: str = None,
          pos: str = None,
          lgcode: str = None,
          lexicon: str = None) -> List[Word]:
    iterable = _db.find_entries(form=form, pos=pos, lgcode=lgcode, lexicon=lexicon)
    return list(itertools.starmap(Word, iterable))


def synset(id: str, lexicon: str = None) -> Synset:
    iterable = _db.find_synsets(id=id, lexicon=lexicon)
    try:
        return Synset(*next(iterable))
    except StopIteration:
        raise wn.Error(f'no such synset: {id}')


def synsets(form: str = None,
            pos: str = None,
            lgcode: str = None,
            lexicon: str = None) -> List[Synset]:
    iterable = _db.find_synsets(form=form, pos=pos, lgcode=lgcode, lexicon=lexicon)
    return list(itertools.starmap(Synset, iterable))


def sense(id: str) -> Sense:
    return Sense(*_db.get_sense(id))
