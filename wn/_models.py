
from typing import Union, Sequence, List, NamedTuple

from wn._types import RelationMap
from wn.constants import SYNSET_RELATIONS, SENSE_RELATIONS
from wn._store import get_lemma, get_synset


class Synset(NamedTuple):
    id: str
    ili: str
    pos: str
    definitions: Sequence[str]
    relations: RelationMap
    examples: Sequence[str]
    lemma_ids: Sequence[str]

    def __getattr__(self, attr: str) -> List['Synset']:
        if attr in SYNSET_RELATIONS:
            return self.get_related(attr)
        raise AttributeError(attr)

    def get_related(self, relation_type: str) -> List['Synset']:
        return [get_synset(sid) for sid in self.relations.get(relation_type, ())]

    def lemmas(self) -> List['Lemma']:
        return [get_lemma(lid) for lid in self.lemma_ids]


class Lemma(NamedTuple):
    sense_id: str
    synset_id: str
    form: str
    pos: str
    script: str
    relations: RelationMap
    examples: Sequence[str]

    def __getattr__(self, attr: str) -> List[Union[Synset, 'Lemma']]:
        if attr in SENSE_RELATIONS:
            return self.get_related(attr)
        raise AttributeError(attr)

    def get_related(self, relation_type: str) -> List[Union[Synset, 'Lemma']]:
        return [get_lemma(sid) for sid in self.relations.get(relation_type, ())]

    def synsets(self):
        return get_synset(self.synset_id)
