
from typing import Union, Sequence, List, NamedTuple

from wn._types import RelationMap
from wn.constants import SYNSET_RELATIONS, SENSE_RELATIONS
from wn import _store


class Synset(NamedTuple):
    id: str
    ili: str
    pos: str
    definitions: Sequence[str]
    relations: RelationMap
    examples: Sequence[str]
    sense_ids: Sequence[str]

    def __getattr__(self, attr: str) -> List['Synset']:
        if attr in SYNSET_RELATIONS:
            return self.get_related(attr)
        raise AttributeError(attr)

    def get_related(self, relation_type: str) -> List['Synset']:
        return [_store.get_synset(sid) for sid in self.relations.get(relation_type, ())]

    def senses(self) -> List['Sense']:
        return [_store.get_sense(lid) for lid in self.sense_ids]

class Sense(NamedTuple):
    id: str
    synset_id: str
    lemma: str
    pos: str
    script: str
    relations: RelationMap
    examples: Sequence[str]

    def __getattr__(self, attr: str) -> List[Union[Synset, 'Sense']]:
        if attr in SENSE_RELATIONS:
            return self.get_related(attr)
        raise AttributeError(attr)

    def get_related(self, relation_type: str) -> List[Union[Synset, 'Sense']]:
        return [_store.get_sense(sid) for sid in self.relations.get(relation_type, ())]

    def synsets(self):
        return _store.get_synset(self.synset_id)
