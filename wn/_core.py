
from typing import Any, TypeVar, Optional, List, Tuple, Dict, Set, Iterator

import wn
from wn._util import flatten
from wn import _db


_FAKE_ROOT = '*ROOT*'
_INFERRED_SYNSET = '*INFERRED*'


class _DatabaseEntity:
    __slots__ = '_id',

    _ENTITY_TYPE = ''

    def __init__(self, _id: int = _db.NON_ROWID):
        self._id = _id        # Database-internal id (e.g., rowid)

    def __eq__(self, other):
        if not isinstance(other, _DatabaseEntity):
            return NotImplemented
        # the _id of different kinds of entities, such as Synset and
        # Sense, can be the same, so make sure they are the same type
        # of object first
        return (self._ENTITY_TYPE == other._ENTITY_TYPE
                and self._id == other._id)

    def __hash__(self):
        return hash((self._ENTITY_TYPE, self._id))


class Lexicon(_DatabaseEntity):
    __slots__ = ('id', 'label', 'language', 'email', 'license',
                 'version', 'url', 'citation', 'metadata')
    __module__ = 'wn'

    _ENTITY_TYPE = 'lexicons'

    def __init__(
            self,
            id: str,
            label: str,
            language: str,
            email: str,
            license: str,
            version: str,
            url: str = None,
            citation: str = None,
            metadata: Dict[str, Any] = None,
            _id: int = _db.NON_ROWID,
    ):
        super().__init__(_id=_id)
        self.id = id
        self.label = label
        self.language = language
        self.email = email
        self.license = license
        self.version = version
        self.url = url
        self.citation = citation
        self.metadata = metadata


class _LexiconElement(_DatabaseEntity):
    __slots__ = '_lexid', '_wordnet'

    def __init__(
            self,
            _lexid: int = _db.NON_ROWID,
            _id: int = _db.NON_ROWID,
            _wordnet: 'WordNet' = None
    ):
        super().__init__(_id=_id)
        self._lexid = _lexid  # Database-internal lexicon id
        self._wordnet = _wordnet

    def lexicon(self):
        return _to_lexicon(_db.get_lexicon(self._lexid))


class Word(_LexiconElement):
    __slots__ = 'id', 'pos', '_forms'
    __module__ = 'wn'

    _ENTITY_TYPE = 'entries'

    def __init__(
            self,
            id: str,
            pos: str,
            forms: List[str],
            _lexid: int = _db.NON_ROWID,
            _id: int = _db.NON_ROWID,
            _wordnet: 'WordNet' = None
    ):
        super().__init__(_lexid=_lexid, _id=_id, _wordnet=_wordnet)
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
        iterable = _db.get_senses_for_entry(self._id)
        return [Sense(id, entry_id, synset_id, lexid, rowid, self._wordnet)
                for lexid, rowid, id, entry_id, synset_id in iterable]

    def synsets(self) -> List['Synset']:
        return [sense.synset() for sense in self.senses()]

    def derived_words(self) -> List['Word']:
        return [derived_sense.word()
                for sense in self.senses()
                for derived_sense in sense.get_related('derivation')]

    def translate(
            self,
            lgcode: str = None,
            lexicon: str = None
    ) -> Dict['Sense', List['Word']]:
        result = {}
        for sense in self.senses():
            result[sense] = [
                t_sense.word()
                for t_sense in sense.translate(lgcode=lgcode, lexicon=lexicon)
            ]
        return result


T = TypeVar('T', bound='_Relatable')


class _Relatable(_LexiconElement):
    __slots__ = 'id',

    def __init__(
            self,
            id: str,
            _lexid: int = _db.NON_ROWID,
            _id: int = _db.NON_ROWID,
            _wordnet: 'WordNet' = None
    ):
        super().__init__(_lexid=_lexid, _id=_id, _wordnet=_wordnet)
        self.id = id

    def get_related(self: T, relation: str) -> List[T]:
        raise NotImplementedError

    def closure(self: T, relation: str) -> Iterator[T]:
        visited = set()
        queue = self.get_related(relation)
        while queue:
            relatable = queue.pop(0)
            if relatable.id not in visited:
                visited.add(relatable.id)
                yield relatable
                queue.extend(relatable.get_related(relation))

    def relation_paths(self: T, *args: str, end: T = None) -> Iterator[List[T]]:
        agenda: List[Tuple[List[T], Set[T]]] = [
            ([target], {self, target})
            for target in self.get_related(*args)
            if target._id != self._id  # avoid self loops?
        ]
        while agenda:
            path, visited = agenda.pop()
            if end is not None and path[-1] == end:
                yield path
            else:
                related = [target for target in path[-1].get_related(*args)
                           if target not in visited]
                if related:
                    for synset in reversed(related):
                        new_path = list(path) + [synset]
                        new_visited = visited | {synset}
                        agenda.append((new_path, new_visited))
                elif end is None:
                    yield path


class Synset(_Relatable):
    __slots__ = 'pos', 'ili'
    __module__ = 'wn'

    _ENTITY_TYPE = 'synsets'

    def __init__(
            self,
            id: str,
            pos: str,
            ili: str = None,
            _lexid: int = _db.NON_ROWID,
            _id: int = _db.NON_ROWID,
            _wordnet: 'WordNet' = None
    ):
        super().__init__(id=id, _lexid=_lexid, _id=_id, _wordnet=_wordnet)
        self.pos = pos
        self.ili = ili

    @classmethod
    def empty(
            cls,
            id: str,
            ili: str = None,
            _lexid: int = _db.NON_ROWID,
            _wordnet: 'WordNet' = None
    ):
        return cls(id, pos='', ili=ili, _lexid=_lexid, _wordnet=_wordnet)

    def __hash__(self):
        # include ili and lexid in the hash so inferred synsets don't
        # hash the same
        return hash((self._ENTITY_TYPE, self.ili, self._lexid, self._id))

    def __repr__(self) -> str:
        return f'Synset({self.id!r})'

    def definition(self) -> Optional[str]:
        return next(iter(_db.get_definitions_for_synset(self._id)), None)

    def examples(self) -> List[str]:
        return _db.get_examples_for_synset(self._id)

    def senses(self) -> List['Sense']:
        iterable = _db.get_senses_for_synset(self._id)
        return [Sense(id, entry_id, synset_id, lexid, rowid, self._wordnet)
                for lexid, rowid, id, entry_id, synset_id in iterable]

    def words(self) -> List[Word]:
        return [sense.word() for sense in self.senses()]

    def lemmas(self) -> List[str]:
        return [w.lemma() for w in self.words()]

    def get_related(self, *args: str) -> List['Synset']:
        # if no lgcode or lexicon constraints were applied, use _lexid
        # of current entity
        lexids: Tuple[int, ...] = (self._lexid,)
        expids: Tuple[int, ...] = (self._lexid,)
        if self._wordnet:
            lexids = self._wordnet._lexicon_ids or lexids
            expids = self._wordnet._expanded_ids or lexids
        rowids = {self._id} - {_db.NON_ROWID}

        # expand search via ILI if possible
        if self.ili is not None and expids:
            expss = _db.find_synsets(ili=self.ili, lexicon_rowids=expids)
            rowids.update(rowid for _, rowid, _, _, _ in expss)

        related: List['Synset'] = []
        if rowids:
            targets = {Synset(id, pos, ili, lexid, rowid, self._wordnet)
                       for lexid, rowid, id, pos, ili
                       in _db.get_synset_relations(rowids, args)}
            ilis = {ss.ili for ss in targets if ss.ili is not None}
            targets.update(Synset(id, pos, ili, lexid, rowid, self._wordnet)
                           for lexid, rowid, id, pos, ili
                           in _db.get_synsets_for_ilis(ilis, lexicon_rowids=lexids))
            related.extend(ss for ss in targets if ss._lexid in lexids)
            # add empty synsets for ILIs without a target in lexids
            for ili in (ilis - {tgt.ili for tgt in related}):
                related.append(
                    Synset.empty(
                        id=_INFERRED_SYNSET,
                        ili=ili,
                        _lexid=self._lexid,
                        _wordnet=self._wordnet
                    )
                )
        return related

    def _hypernym_paths(
            self, simulate_root: bool, include_self: bool
    ) -> List[List['Synset']]:
        paths = list(self.relation_paths('hypernym', 'instance_hypernym'))
        if include_self:
            paths = [[self] + path for path in paths] or [[self]]
        if simulate_root and self.id != _FAKE_ROOT:
            root = Synset.empty(
                id=_FAKE_ROOT, _lexid=self._lexid, _wordnet=self._wordnet
            )
            paths = [path + [root] for path in paths]
        return paths

    def hypernym_paths(self, simulate_root: bool = False) -> List[List['Synset']]:
        return self._hypernym_paths(simulate_root, False)

    def min_depth(self, simulate_root: bool = False) -> int:
        return min(
            (len(path) for path in self.hypernym_paths(simulate_root=simulate_root)),
            default=0
        )

    def max_depth(self, simulate_root: bool = False) -> int:
        return max(
            (len(path) for path in self.hypernym_paths(simulate_root=simulate_root)),
            default=0
        )

    def _shortest_hyp_paths(
            self, other: 'Synset', simulate_root: bool
    ) -> Dict[Tuple['Synset', int], List['Synset']]:
        if self == other:
            return {(self, 0): []}

        from_self = self._hypernym_paths(simulate_root, True)
        from_other = other._hypernym_paths(simulate_root, True)
        common = set(flatten(from_self)).intersection(flatten(from_other))

        if not common:
            return {}

        # Compute depths of common hypernyms from their distances.
        # Doing this now avoid more expensive lookups later.
        depths: Dict['Synset', int] = {}
        # subpaths accumulates paths to common hypernyms from both sides
        subpaths: Dict['Synset', Tuple[List[List['Synset']], List[List['Synset']]]]
        subpaths = {ss: ([], []) for ss in common}
        for which, paths in (0, from_self), (1, from_other):
            for path in paths:
                for dist, ss in enumerate(path):
                    if ss in common:
                        # self or other subpath to ss (not including ss)
                        subpaths[ss][which].append(path[:dist + 1])
                        # keep maximum depth
                        depth = len(path) - dist - 1
                        if ss not in depths or depths[ss] < depth:
                            depths[ss] = depth

        shortest: Dict[Tuple['Synset', int], List['Synset']] = {}
        for ss in common:
            from_self_subpaths, from_other_subpaths = subpaths[ss]
            shortest_from_self = min(from_self_subpaths, key=len)
            # for the other path, we need to reverse it and remove the pivot synset
            shortest_from_other = min(from_other_subpaths, key=len)[-2::-1]
            shortest[(ss, depths[ss])] = shortest_from_self + shortest_from_other

        return shortest

    def shortest_path(
            self, other: 'Synset', simulate_root: bool = False
    ) -> List['Synset']:
        pathmap = self._shortest_hyp_paths(other, simulate_root)
        key = min(pathmap, key=lambda key: len(pathmap[key]), default=None)
        if key is None:
            raise wn.Error(f'no path between {self!r} and {other!r}')
        return pathmap[key]

    def common_hypernyms(
            self, other: 'Synset', simulate_root: bool = False
    ) -> List['Synset']:
        return [ss for ss, _ in self._shortest_hyp_paths(other, simulate_root)]

    def lowest_common_hypernyms(
            self, other: 'Synset', simulate_root: bool = False
    ) -> List['Synset']:
        pathmap = self._shortest_hyp_paths(other, simulate_root)
        # keys of pathmap are (synset, depth_of_synset)
        max_depth: int = max([depth for _, depth in pathmap], default=-1)
        if max_depth == -1:
            return []
        else:
            return [ss for ss, d in pathmap if d == max_depth]

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

    def translate(self, lgcode: str = None, lexicon: str = None) -> List['Synset']:
        ili = self.ili
        if not ili:
            return []
        return synsets(ili=ili, lgcode=lgcode, lexicon=lexicon)


class Sense(_Relatable):
    __slots__ = '_entry_id', '_synset_id'
    __module__ = 'wn'

    _ENTITY_TYPE = 'senses'

    def __init__(
            self,
            id: str,
            entry_id: str,
            synset_id: str,
            _lexid: int = _db.NON_ROWID,
            _id: int = _db.NON_ROWID,
            _wordnet: 'WordNet' = None
    ):
        super().__init__(id=id, _lexid=_lexid, _id=_id, _wordnet=_wordnet)
        self._entry_id = entry_id
        self._synset_id = synset_id

    def __repr__(self) -> str:
        return f'Sense({self.id!r})'

    def word(self) -> Word:
        return word(id=self._entry_id)

    def synset(self) -> Synset:
        return synset(id=self._synset_id)

    def get_related(self, *args: str) -> List['Sense']:
        iterable = _db.get_sense_relations(self._id, args)
        return [Sense(id, entry_id, synset_id, lexid, rowid, self._wordnet)
                for lexid, rowid, id, entry_id, synset_id in iterable]

    def get_related_synsets(self, *args: str) -> List[Synset]:
        iterable = _db.get_sense_synset_relations(self._id, args)
        return [Synset(id, pos, ili, lexid, rowid, self._wordnet)
                for lexid, rowid, id, pos, ili in iterable]

    def translate(self, lgcode: str = None, lexicon: str = None) -> List['Sense']:
        synset = self.synset()
        return [t_sense
                for t_synset in synset.translate(lgcode=lgcode, lexicon=lexicon)
                for t_sense in t_synset.senses()]


class WordNet:
    """
    Class for interacting with WordNet data.
    """

    __slots__ = '_lgcode', '_lexicons', '_lexicon_ids', '_expanded', '_expanded_ids'
    __module__ = 'wn'

    def __init__(self, lgcode: str = None, lexicon: str = None, expand: str = None):
        self._lgcode = lgcode

        self._lexicons: Tuple[Lexicon, ...] = ()
        if lgcode or lexicon:
            self._lexicons = tuple(
                map(_to_lexicon, _db.find_lexicons(lgcode=lgcode, lexicon=lexicon))
            )
        self._lexicon_ids: Tuple[int, ...] = tuple(lx._id for lx in self._lexicons)

        self._expanded: Tuple[Lexicon, ...] = ()
        if expand is None:
            expand = '*'  # TODO: use project-specific settings
        if expand:
            self._expanded = tuple(
                map(_to_lexicon, _db.find_lexicons(lexicon=expand))
            )
        self._expanded_ids: Tuple[int, ...] = tuple(lx._id for lx in self._expanded)

    @property
    def lgcode(self) -> Optional[str]:
        return self._lgcode

    def lexicons(self): return self._lexicons
    def expanded_lexicons(self): return self._expanded

    def word(self, id: str) -> Word:
        iterable = _db.find_entries(id=id, lexicon_rowids=self._lexicon_ids)
        try:
            lexid, rowid, id, pos, forms = next(iterable)
            return Word(id, pos, forms, lexid, rowid, self)
        except StopIteration:
            raise wn.Error(f'no such lexical entry: {id}')

    def words(self, form: str = None, pos: str = None) -> List[Word]:
        iterable = _db.find_entries(
            form=form, pos=pos, lexicon_rowids=self._lexicon_ids
        )
        return [Word(id, pos, forms, lexid, rowid, self)
                for lexid, rowid, id, pos, forms in iterable]

    def synset(self, id: str) -> Synset:
        iterable = _db.find_synsets(id=id, lexicon_rowids=self._lexicon_ids)
        try:
            lexid, rowid, id, pos, ili = next(iterable)
            return Synset(id, pos, ili, lexid, rowid, self)
        except StopIteration:
            raise wn.Error(f'no such synset: {id}')

    def synsets(
        self, form: str = None, pos: str = None, ili: str = None
    ) -> List[Synset]:
        iterable = _db.find_synsets(
            form=form, pos=pos, ili=ili, lexicon_rowids=self._lexicon_ids
        )
        return [Synset(id, pos, ili, lexid, rowid, self)
                for lexid, rowid, id, pos, ili in iterable]

    def sense(self, id: str) -> Sense:
        iterable = _db.find_senses(id=id, lexicon_rowids=self._lexicon_ids)
        try:
            lexid, rowid, id, entry_id, synset_id = next(iterable)
            return Sense(id, entry_id, synset_id, lexid, rowid, self)
        except StopIteration:
            raise wn.Error(f'no such sense: {id}')

    def senses(self, form: str = None, pos: str = None) -> List[Sense]:
        iterable = _db.find_senses(
            form=form, pos=pos, lexicon_rowids=self._lexicon_ids
        )
        return [Sense(id, entry_id, synset_id, lexid, rowid, self)
                for lexid, rowid, id, entry_id, synset_id in iterable]


def _to_lexicon(data) -> Lexicon:
    rowid, id, label, language, email, license, version, url, citation, metadata = data
    return Lexicon(
        id,
        label,
        language,
        email,
        license,
        version,
        url=url,
        citation=citation,
        metadata=metadata,
        _id=rowid
    )


def lexicons(lgcode: str = None, lexicon: str = None) -> List[Lexicon]:
    """Return the lexicons matching a language or identifier key."""
    if lexicon is None:
        lexicon = '*'
    return WordNet(lgcode=lgcode, lexicon=lexicon).lexicons()


def word(id: str, lexicon: str = None) -> Word:
    """Return the word with *id* in *lexicon*.

    If *lexicon* is not given, all lexicons will be searched, but only
    the first result, in arbitrary order, will be returned. If no
    words match, `None` is returned.

    >>> wn.word('ewn-cell-n')
    Word('ewn-cell-n')

    """
    return WordNet(lexicon=lexicon).word(id=id)


def words(form: str = None,
          pos: str = None,
          lgcode: str = None,
          lexicon: str = None) -> List[Word]:
    """Return the list of matching words.

    The *form*, *pos*, *lgcode*, and *lexicon* parameters act as
    filters---i.e., if all are omitted, all known words will be
    returned.

    >>> len(wn.words())
    282902
    >>> len(wn.words(pos='v'))
    34592
    >>> wn.words(form="scurry")
    [Word('ewn-scurry-n'), Word('ewn-scurry-v')]

    """
    return WordNet(lgcode=lgcode, lexicon=lexicon).words(form=form, pos=pos)


def synset(id: str, lexicon: str = None) -> Synset:
    """Return the synset with *id* in *lexicon*.

    If *lexicon* is not given, all lexicons will be searched, but only
    the first result, in arbitrary order, will be returned. If no
    words match, `None` is returned.

    >>> wn.synset('ewn-03311152-n')
    Synset('ewn-03311152-n')

    """
    return WordNet(lexicon=lexicon).synset(id=id)


def synsets(form: str = None,
            pos: str = None,
            ili: str = None,
            lgcode: str = None,
            lexicon: str = None) -> List[Synset]:
    """Return the list of matching synsets.

    >>> len(wn.synsets('couch'))
    4
    >>> wn.synsets('couch', pos='v')
    [Synset('ewn-00983308-v')]

    """
    return WordNet(lgcode=lgcode, lexicon=lexicon).synsets(form=form, pos=pos, ili=ili)


def senses(form: str = None,
           pos: str = None,
           lgcode: str = None,
           lexicon: str = None) -> List[Sense]:
    """Return the list of matching senses.

    >>> len(wn.senses('twig'))
    3
    >>> wn.senses('twig', pos='n')
    [Sense('ewn-twig-n-13184889-02')]

    """
    return WordNet(lgcode=lgcode, lexicon=lexicon).senses(form=form, pos=pos)


def sense(id: str, lexicon: str = None) -> Sense:
    """Return the sense with *id* in *lexicon*.

    If *lexicon* is not given, all lexicons will be searched, but only
    the first result, in arbitrary order, will be returned. If no
    words match, `None` is returned.

    >>> wn.sense('ewn-flutter-v-01903884-02')
    Sense('ewn-flutter-v-01903884-02')

    """
    return WordNet(lexicon=lexicon).sense(id=id)
