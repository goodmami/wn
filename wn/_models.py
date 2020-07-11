
from typing import Optional, Union, List

from wn import _store


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
        return _store.get_senses_for_entry(self.id)


class Synset:
    __slots__ = 'id', 'pos', 'ili'

    def __init__(self, id: str, pos: str, ili: str = None):
        self.id = id
        self.pos = pos
        self.ili = ili

    def __repr__(self) -> str:
        return f'Synset({self.id!r})'

    def definition(self) -> Optional[str]:
        return next(iter(_store.get_definitions_for_synset(self.id)), None)

    def examples(self) -> List[str]:
        return _store.get_examples_for_synset(self.id)

    def get_related(self, relation_type: str) -> List['Synset']:
        return _store.get_synset_relations(self.id, relation_type)

    def senses(self) -> List['Sense']:
        return _store.get_senses_for_synset(self.id)


class Sense:
    __slots__ = 'id', '_entry_id', '_synset_id', 'key'

    def __init__(self, id: str, entry_id: str, synset_id: str, key: str = None):
        self.id = id
        self._entry_id = entry_id
        self._synset_id = synset_id
        self.key = key

    def __repr__(self) -> str:
        return f'Sense({self.id!r})'

    def get_related(self, relation_type: str) -> List[Union[Synset, 'Sense']]:
        return _store.get_sense_relations(self.id, relation_type)

    def word(self) -> Word:
        return _store.get_entry(self._entry_id)

    def synset(self) -> Synset:
        return _store.get_synset(self._synset_id)
