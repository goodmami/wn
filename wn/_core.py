
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

    def __lt__(self, other):
        if not isinstance(other, _DatabaseEntity):
            return NotImplemented
        elif self._ENTITY_TYPE != other._ENTITY_TYPE:
            return NotImplemented
        else:
            return self._id < other._id

    def __hash__(self):
        return hash((self._ENTITY_TYPE, self._id))


class Lexicon(_DatabaseEntity):
    """A class representing a wordnet lexicon.

    Attributes:
        id: The lexicon's identifier.
        label: The full name of lexicon.
        language: The BCP 47 language code of lexicon.
        email: The email address of the wordnet maintainer.
        license: The URL or name of the wordnet's license.
        version: The version string of the resource.
        url: The project URL of the wordnet.
        citation: The canonical citation for the project.
        metadata: Any extra metadata for the lexicon.
    """
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

    def __repr__(self):
        id, ver, lg = self.id, self.version, self.language
        return f'<Lexicon {id}:{ver} [{lg}]>'


class _LexiconElement(_DatabaseEntity):
    __slots__ = '_lexid', '_wordnet'

    def __init__(
            self,
            _lexid: int = _db.NON_ROWID,
            _id: int = _db.NON_ROWID,
            _wordnet: 'Wordnet' = None
    ):
        super().__init__(_id=_id)
        self._lexid = _lexid  # Database-internal lexicon id
        self._wordnet = _wordnet

    def lexicon(self):
        return _to_lexicon(_db.get_lexicon(self._lexid))


class Word(_LexiconElement):
    """A class for words (also called lexical entries) in a wordnet."""
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
            _wordnet: 'Wordnet' = None
    ):
        super().__init__(_lexid=_lexid, _id=_id, _wordnet=_wordnet)
        self.id = id
        self.pos = pos
        self._forms = forms

    def __repr__(self) -> str:
        return f'Word({self.id!r})'

    def lemma(self) -> str:
        """Return the canonical form of the word.

        Example:

            >>> wn.words('wolves')[0].lemma()
            'wolf'

        """
        return self._forms[0]

    def forms(self) -> List[str]:
        """Return the list of all encoded forms of the word.

        Example:

            >>> wn.words('wolf')[0].forms()
            ['wolf', 'wolves']

        """
        return self._forms

    def senses(self) -> List['Sense']:
        """Return the list of senses of the word.

        Example:

            >>> wn.words('zygoma')[0].senses()
            [Sense('ewn-zygoma-n-05292350-01')]

        """
        iterable = _db.get_senses_for_entry(self._id)
        return [Sense(id, entry_id, synset_id, lexid, rowid, self._wordnet)
                for lexid, rowid, id, entry_id, synset_id in iterable]

    def synsets(self) -> List['Synset']:
        """Return the list of synsets of the word.

        Example:

            >>> wn.words('addendum')[0].synsets()
            [Synset('ewn-06411274-n')]

        """
        return [sense.synset() for sense in self.senses()]

    def derived_words(self) -> List['Word']:
        """Return the list of words linked through derivations on the senses.

        Example:

            >>> wn.words('magical')[0].derived_words()
            [Word('ewn-magic-n'), Word('ewn-magic-n')]

        """
        return [derived_sense.word()
                for sense in self.senses()
                for derived_sense in sense.get_related('derivation')]

    def translate(
            self,
            lgcode: str = None,
            lexicon: str = None
    ) -> Dict['Sense', List['Word']]:
        """Return a mapping of word senses to lists of translated words.

        Arguments:
            lgcode: if specified, translate to words with the language code
            lexicon: if specified, translate to words in the target lexicon(s)

        Example:

            >>> w = wn.words('water bottle', pos='n')[0]
            >>> for sense, words in w.translate('ja').items():
            ...     print(sense, [jw.lemma() for jw in words])
            ...
            Sense('ewn-water_bottle-n-04564934-01') ['水筒']

        """
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
            _wordnet: 'Wordnet' = None
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
    """Class for modeling wordnet synsets."""
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
            _wordnet: 'Wordnet' = None
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
            _wordnet: 'Wordnet' = None
    ):
        return cls(id, pos='', ili=ili, _lexid=_lexid, _wordnet=_wordnet)

    def __hash__(self):
        # include ili and lexid in the hash so inferred synsets don't
        # hash the same
        return hash((self._ENTITY_TYPE, self.ili, self._lexid, self._id))

    def __repr__(self) -> str:
        return f'Synset({self.id!r})'

    def definition(self) -> Optional[str]:
        """Return the first definition found for the synset.

        Example:

            >>> wn.synsets('cartwheel', pos='n')[0].definition()
            'a wheel that has wooden spokes and a metal rim'

        """
        return next(iter(_db.get_definitions_for_synset(self._id)), None)

    def examples(self) -> List[str]:
        """Return the list of examples for the synset.

        Example:

            >>> wn.synsets('orbital', pos='a')[0].examples()
            ['"orbital revolution"', '"orbital velocity"']

        """
        return _db.get_examples_for_synset(self._id)

    def senses(self) -> List['Sense']:
        """Return the list of sense members of the synset.

        Example:

            >>> wn.synsets('umbrella', pos='n')[0].senses()
            [Sense('ewn-umbrella-n-04514450-01')]

        """
        iterable = _db.get_senses_for_synset(self._id)
        return [Sense(id, entry_id, synset_id, lexid, rowid, self._wordnet)
                for lexid, rowid, id, entry_id, synset_id in iterable]

    def words(self) -> List[Word]:
        """Return the list of words linked by the synset's senses.

        Example:

            >>> wn.synsets('exclusive', pos='n')[0].words()
            [Word('ewn-scoop-n'), Word('ewn-exclusive-n')]

        """
        return [sense.word() for sense in self.senses()]

    def lemmas(self) -> List[str]:
        """Return the list of lemmas of words for the synset.

        Example:

            >>> wn.synsets('exclusive', pos='n')[0].words()
            ['scoop', 'exclusive']

        """
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
        """Return the list of hypernym paths to a root synset.

        Example:

            >>> for path in wn.synsets('dog', pos='n')[0].hypernym_paths():
            ...     for i, ss in enumerate(path):
            ...         print(' ' * i, ss, ss.lemmas()[0])
            ...
             Synset('pwn-02083346-n') canine
              Synset('pwn-02075296-n') carnivore
               Synset('pwn-01886756-n') eutherian mammal
                Synset('pwn-01861778-n') mammalian
                 Synset('pwn-01471682-n') craniate
                  Synset('pwn-01466257-n') chordate
                   Synset('pwn-00015388-n') animal
                    Synset('pwn-00004475-n') organism
                     Synset('pwn-00004258-n') animate thing
                      Synset('pwn-00003553-n') unit
                       Synset('pwn-00002684-n') object
                        Synset('pwn-00001930-n') physical entity
                         Synset('pwn-00001740-n') entity
             Synset('pwn-01317541-n') domesticated animal
              Synset('pwn-00015388-n') animal
               Synset('pwn-00004475-n') organism
                Synset('pwn-00004258-n') animate thing
                 Synset('pwn-00003553-n') unit
                  Synset('pwn-00002684-n') object
                   Synset('pwn-00001930-n') physical entity
                    Synset('pwn-00001740-n') entity

        """
        return self._hypernym_paths(simulate_root, False)

    def min_depth(self, simulate_root: bool = False) -> int:
        """Return the minimum taxonomy depth of the synset.

        Example:

            >>> wn.synsets('dog', pos='n')[0].min_depth()
            8

        """
        return min(
            (len(path) for path in self.hypernym_paths(simulate_root=simulate_root)),
            default=0
        )

    def max_depth(self, simulate_root: bool = False) -> int:
        """Return the maximum taxonomy depth of the synset.

        Example:

            >>> wn.synsets('dog', pos='n')[0].max_depth()
            13

        """
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
        """Return the shortest path from the synset to the *other* synset.

        Arguments:
            other: endpoint synset of the path
            simulate_root: if :python:`True`, ensure any two synsets
              are always connected by positing a fake root node

        """
        pathmap = self._shortest_hyp_paths(other, simulate_root)
        key = min(pathmap, key=lambda key: len(pathmap[key]), default=None)
        if key is None:
            raise wn.Error(f'no path between {self!r} and {other!r}')
        return pathmap[key]

    def common_hypernyms(
            self, other: 'Synset', simulate_root: bool = False
    ) -> List['Synset']:
        """Return the common hypernyms for the current and *other* synsets.

        Arguments:
            other: synset that is a hyponym of any shared hypernyms
            simulate_root: if :python:`True`, ensure any two synsets
              always share a hypernym by positing a fake root node

        """
        from_self = self._hypernym_paths(simulate_root, True)
        from_other = other._hypernym_paths(simulate_root, True)
        common = set(flatten(from_self)).intersection(flatten(from_other))
        return sorted(common)

    def lowest_common_hypernyms(
            self, other: 'Synset', simulate_root: bool = False
    ) -> List['Synset']:
        """Return the common hypernyms furthest from the root.

        Arguments:
            other: synset that is a hyponym of any shared hypernyms
            simulate_root: if :python:`True`, ensure any two synsets
              always share a hypernym by positing a fake root node

        """
        pathmap = self._shortest_hyp_paths(other, simulate_root)
        # keys of pathmap are (synset, depth_of_synset)
        max_depth: int = max([depth for _, depth in pathmap], default=-1)
        if max_depth == -1:
            return []
        else:
            return [ss for ss, d in pathmap if d == max_depth]

    def holonyms(self) -> List['Synset']:
        """Return the list of synsets related by any holonym relation.

        Any of the following relations are traversed: ``holonym``,
        ``holo_location``, ``holo_member``, ``holo_part``,
        ``holo_portion``, ``holo_substance``.

        """
        return self.get_related(
            'holonym',
            'holo_location',
            'holo_member',
            'holo_part',
            'holo_portion',
            'holo_substance',
        )

    def meronyms(self) -> List['Synset']:
        """Return the list of synsets related by any meronym relation.

        Any of the following relations are traversed: ``meronym``,
        ``mero_location``, ``mero_member``, ``mero_part``,
        ``mero_portion``, ``mero_substance``.

        """
        return self.get_related(
            'meronym',
            'mero_location',
            'mero_member',
            'mero_part',
            'mero_portion',
            'mero_substance',
        )

    def hypernyms(self) -> List['Synset']:
        """Return the list of synsets related by any hypernym relation.

        Both the ``hypernym`` and ``instance_hypernym`` relations are
        traversed.

        """
        return self.get_related(
            'hypernym',
            'instance_hypernym'
        )

    def hyponyms(self) -> List['Synset']:
        """Return the list of synsets related by any hyponym relation.

        Both the ``hyponym`` and ``instance_hyponym`` relations are
        traversed.

        """
        return self.get_related(
            'hyponym',
            'instance_hyponym'
        )

    def translate(self, lgcode: str = None, lexicon: str = None) -> List['Synset']:
        """Return a list of translated synsets.

        Arguments:
            lgcode: if specified, translate to synsets with the language code
            lexicon: if specified, translate to synsets in the target lexicon(s)

        Example:

            >>> es = wn.synsets('araña', lgcode='es')[0]
            >>> en = es.translate(lexicon='ewn')[0]
            >>> en.lemmas()
            ['spider']

        """

        ili = self.ili
        if not ili:
            return []
        return synsets(ili=ili, lgcode=lgcode, lexicon=lexicon)


class Sense(_Relatable):
    """Class for modeling wordnet senses."""
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
            _wordnet: 'Wordnet' = None
    ):
        super().__init__(id=id, _lexid=_lexid, _id=_id, _wordnet=_wordnet)
        self._entry_id = entry_id
        self._synset_id = synset_id

    def __repr__(self) -> str:
        return f'Sense({self.id!r})'

    def word(self) -> Word:
        """Return the word of the sense.

        Example:

            >>> wn.senses('spigot')[0].word()
            Word('pwn-spigot-n')

        """
        return word(id=self._entry_id)

    def synset(self) -> Synset:
        """Return the synset of the sense.

        Example:

            >>> wn.senses('spigot')[0].synset()
            Synset('pwn-03325088-n')

        """
        return synset(id=self._synset_id)

    def get_related(self, *args: str) -> List['Sense']:
        """Return a list of related senses.

        One or more relation types should be passed as arguments which
        determine the kind of relations returned.

        Example:

            >>> physics = wn.senses('physics', lexicon='ewn')[0]
            >>> for sense in physics.get_related('has_domain_topic'):
            ...     print(sense.word().lemma())
            ...
            coherent
            chaotic
            incoherent

        """
        iterable = _db.get_sense_relations(self._id, args)
        return [Sense(id, entry_id, synset_id, lexid, rowid, self._wordnet)
                for lexid, rowid, id, entry_id, synset_id in iterable]

    def get_related_synsets(self, *args: str) -> List[Synset]:
        """Return a list of related synsets."""
        iterable = _db.get_sense_synset_relations(self._id, args)
        return [Synset(id, pos, ili, lexid, rowid, self._wordnet)
                for lexid, rowid, id, pos, ili in iterable]

    def translate(self, lgcode: str = None, lexicon: str = None) -> List['Sense']:
        """Return a list of translated senses.

        Arguments:
            lgcode: if specified, translate to senses with the language code
            lexicon: if specified, translate to senses in the target lexicon(s)

        Example:

            >>> en = wn.senses('petiole', lgcode='en')[0]
            >>> pt = en.translate('pt')[0]
            >>> pt.word().lemma()
            'pecíolo'

        """
        synset = self.synset()
        return [t_sense
                for t_synset in synset.translate(lgcode=lgcode, lexicon=lexicon)
                for t_sense in t_synset.senses()]


class Wordnet:
    """Class for interacting with wordnet data.

    A wordnet object acts essentially as a filter by first selecting
    matching lexicons and then searching only within those lexicons
    for later queries. On instantiation, a *lgcode* argument is a
    BCP47 language code that restricts the selected lexicons to those
    whose language matches the given code. A *lexicon* argument is a
    space-separated list of lexicon specifiers that more directly
    select lexicons by their ID and version; this is preferable when
    there are multiple lexicons in the same language or multiple
    version with the same ID.

    Some wordnets were created by translating the words from a larger
    wordnet, namely the Princeton WordNet, and then relying on the
    larger wordnet for structural relations. An *expand* argument is a
    second space-separated list of lexicon specifiers which are used
    for traversing relations, but not as the results of queries.

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
        """The BCP47 language code of lexicons in the wordnet."""
        return self._lgcode

    def lexicons(self):
        """Return the list of lexicons covered by this wordnet."""
        return self._lexicons

    def expanded_lexicons(self):
        """Return the list of expand lexicons for this wordnet."""
        return self._expanded

    def word(self, id: str) -> Word:
        """Return the first word in this wordnet with identifier *id*."""
        iterable = _db.find_entries(id=id, lexicon_rowids=self._lexicon_ids)
        try:
            lexid, rowid, id, pos, forms = next(iterable)
            return Word(id, pos, forms, lexid, rowid, self)
        except StopIteration:
            raise wn.Error(f'no such lexical entry: {id}')

    def words(self, form: str = None, pos: str = None) -> List[Word]:
        """Return the list of matching words in this wordnet.

        Without any arguments, this function returns all words in the
        wordnet's selected lexicons. A *form* argument restricts the
        words to those matching the given word form, and *pos*
        restricts words by their part of speech.

        """
        iterable = _db.find_entries(
            form=form, pos=pos, lexicon_rowids=self._lexicon_ids
        )
        return [Word(id, pos, forms, lexid, rowid, self)
                for lexid, rowid, id, pos, forms in iterable]

    def synset(self, id: str) -> Synset:
        """Return the first synset in this wordnet with identifier *id*."""
        iterable = _db.find_synsets(id=id, lexicon_rowids=self._lexicon_ids)
        try:
            lexid, rowid, id, pos, ili = next(iterable)
            return Synset(id, pos, ili, lexid, rowid, self)
        except StopIteration:
            raise wn.Error(f'no such synset: {id}')

    def synsets(
        self, form: str = None, pos: str = None, ili: str = None
    ) -> List[Synset]:
        """Return the list of matching synsets in this wordnet.

        Without any arguments, this function returns all synsets in
        the wordnet's selected lexicons. A *form* argument restricts
        synsets to those whose member words match the given word
        form. A *pos* argument restricts synsets to those with the
        given part of speech. An *ili* argument restricts synsets to
        those with the given interlingual index; generally this should
        select a unique synset within a single lexicon.

        """
        iterable = _db.find_synsets(
            form=form, pos=pos, ili=ili, lexicon_rowids=self._lexicon_ids
        )
        return [Synset(id, pos, ili, lexid, rowid, self)
                for lexid, rowid, id, pos, ili in iterable]

    def sense(self, id: str) -> Sense:
        """Return the first sense in this wordnet with identifier *id*."""
        iterable = _db.find_senses(id=id, lexicon_rowids=self._lexicon_ids)
        try:
            lexid, rowid, id, entry_id, synset_id = next(iterable)
            return Sense(id, entry_id, synset_id, lexid, rowid, self)
        except StopIteration:
            raise wn.Error(f'no such sense: {id}')

    def senses(self, form: str = None, pos: str = None) -> List[Sense]:
        """Return the list of matching senses in this wordnet.

        Without any arguments, this function returns all senses in the
        wordnet's selected lexicons. A *form* argument restricts the
        senses to those whose word matches the given word form, and
        *pos* restricts senses by their word's part of speech.

        """
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


def projects() -> List[Dict]:
    """Return the list of indexed projects.

    This returns the same dictionaries of information as
    :meth:`wn.config.get_project_info
    <wn._config.WNConfig.get_project_info>`, but for all indexed
    projects.

    Example:

        >>> infos = wn.projects()
        >>> len(infos)
        36
        >>> infos[0]['label']
        'Open English WordNet'

    """
    index = wn.config.index
    return [
        wn.config.get_project_info(f'{project_id}:{version}')
        for project_id, project_info in index.items()
        for version in project_info['versions']
    ]


def lexicons(lgcode: str = None, lexicon: str = None) -> List[Lexicon]:
    """Return the lexicons matching a language or lexicon specifier.

    Example:

        >>> wn.lexicons('en')
        [<Lexicon ewn:2020 [en]>, <Lexicon pwn:3.0 [en]>]

    """
    if lexicon is None:
        lexicon = '*'
    return Wordnet(lgcode=lgcode, lexicon=lexicon).lexicons()


def word(id: str, lgcode: str = None, lexicon: str = None) -> Word:
    """Return the word with *id* in *lexicon*.

    This will create a :class:`Wordnet` object using the *lgcode* and
    *lexicon* arguments. The *id* argument is then passed to the
    :meth:`Wordnet.word` method.

    >>> wn.word('ewn-cell-n')
    Word('ewn-cell-n')

    """
    return Wordnet(lgcode=lgcode, lexicon=lexicon).word(id=id)


def words(form: str = None,
          pos: str = None,
          lgcode: str = None,
          lexicon: str = None) -> List[Word]:
    """Return the list of matching words.

    This will create a :class:`Wordnet` object using the *lgcode* and
    *lexicon* arguments. The remaining arguments are passed to the
    :meth:`Wordnet.words` method.

    >>> len(wn.words())
    282902
    >>> len(wn.words(pos='v'))
    34592
    >>> wn.words(form="scurry")
    [Word('ewn-scurry-n'), Word('ewn-scurry-v')]

    """
    return Wordnet(lgcode=lgcode, lexicon=lexicon).words(form=form, pos=pos)


def synset(id: str, lgcode: str = None, lexicon: str = None) -> Synset:
    """Return the synset with *id* in *lexicon*.

    This will create a :class:`Wordnet` object using the *lgcode* and
    *lexicon* arguments. The *id* argument is then passed to the
    :meth:`Wordnet.synset` method.

    >>> wn.synset('ewn-03311152-n')
    Synset('ewn-03311152-n')

    """
    return Wordnet(lgcode=lgcode, lexicon=lexicon).synset(id=id)


def synsets(form: str = None,
            pos: str = None,
            ili: str = None,
            lgcode: str = None,
            lexicon: str = None) -> List[Synset]:
    """Return the list of matching synsets.

    This will create a :class:`Wordnet` object using the *lgcode* and
    *lexicon* arguments. The remaining arguments are passed to the
    :meth:`Wordnet.synsets` method.

    >>> len(wn.synsets('couch'))
    4
    >>> wn.synsets('couch', pos='v')
    [Synset('ewn-00983308-v')]

    """
    return Wordnet(lgcode=lgcode, lexicon=lexicon).synsets(form=form, pos=pos, ili=ili)


def senses(form: str = None,
           pos: str = None,
           lgcode: str = None,
           lexicon: str = None) -> List[Sense]:
    """Return the list of matching senses.

    This will create a :class:`Wordnet` object using the *lgcode* and
    *lexicon* arguments. The remaining arguments are passed to the
    :meth:`Wordnet.senses` method.

    >>> len(wn.senses('twig'))
    3
    >>> wn.senses('twig', pos='n')
    [Sense('ewn-twig-n-13184889-02')]

    """
    return Wordnet(lgcode=lgcode, lexicon=lexicon).senses(form=form, pos=pos)


def sense(id: str, lgcode: str = None, lexicon: str = None) -> Sense:
    """Return the sense with *id* in *lexicon*.

    This will create a :class:`Wordnet` object using the *lgcode* and
    *lexicon* arguments. The *id* argument is then passed to the
    :meth:`Wordnet.sense` method.

    >>> wn.sense('ewn-flutter-v-01903884-02')
    Sense('ewn-flutter-v-01903884-02')

    """
    return Wordnet(lgcode=lgcode, lexicon=lexicon).sense(id=id)
