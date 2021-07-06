
from typing import (
    Type,
    TypeVar,
    Callable,
    Optional,
    List,
    Tuple,
    Dict,
    Set,
    Sequence,
    Iterator,
)
import warnings

import wn
from wn._types import (
    Metadata,
    NormalizeFunction,
    LemmatizeFunction,
)
from wn._util import normalize_form
from wn._db import NON_ROWID
from wn._queries import (
    find_lexicons,
    find_ilis,
    find_proposed_ilis,
    find_entries,
    find_senses,
    find_synsets,
    get_lexicon,
    get_modified,
    get_lexicon_dependencies,
    get_lexicon_extension_bases,
    get_lexicon_extensions,
    get_form_pronunciations,
    get_form_tags,
    get_entry_senses,
    get_sense_relations,
    get_sense_synset_relations,
    get_synset_relations,
    get_synset_members,
    get_synsets_for_ilis,
    get_examples,
    get_definitions,
    get_syntactic_behaviours,
    get_metadata,
    get_lexicalized,
    get_adjposition,
    get_sense_counts,
    get_lexfile,
)
from wn import taxonomy

_INFERRED_SYNSET = '*INFERRED*'


class _DatabaseEntity:
    __slots__ = '_id',

    _ENTITY_TYPE = ''

    def __init__(self, _id: int = NON_ROWID):
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


class ILI(_DatabaseEntity):
    """A class for interlingual indices."""
    __slots__ = 'id', 'status', '_definition'
    __module__ = 'wn'

    def __init__(
        self,
        id: Optional[str],
        status: str,
        definition: str = None,
        _id: int = NON_ROWID,
    ):
        super().__init__(_id=_id)
        self.id = id
        self.status = status
        self._definition = definition

    def __repr__(self) -> str:
        return f'ILI({repr(self.id) if self.id else "*PROPOSED*"})'

    def definition(self) -> Optional[str]:
        return self._definition

    def metadata(self) -> Metadata:
        """Return the ILI's metadata."""
        table = 'proposed_ilis' if self.status == 'proposed' else 'ilis'
        return get_metadata(self._id, table)


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
        logo: A URL or path to a project logo.
    """
    __slots__ = ('id', 'label', 'language', 'email', 'license',
                 'version', 'url', 'citation', 'logo')
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
        logo: str = None,
        _id: int = NON_ROWID,
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
        self.logo = logo

    def __repr__(self):
        id, ver, lg = self.id, self.version, self.language
        return f'<Lexicon {id}:{ver} [{lg}]>'

    def metadata(self) -> Metadata:
        """Return the lexicon's metadata."""
        return get_metadata(self._id, 'lexicons')

    def specifier(self) -> str:
        """Return the *id:version* lexicon specifier."""
        return f'{self.id}:{self.version}'

    def modified(self) -> bool:
        """Return True if the lexicon has local modifications."""
        return get_modified(self._id)

    def requires(self) -> Dict[str, Optional['Lexicon']]:
        """Return the lexicon dependencies."""
        return dict(
            (f'{id}:{version}',
             None if _id is None else _to_lexicon(get_lexicon(_id)))
            for id, version, _, _id in get_lexicon_dependencies(self._id)
        )

    def extends(self) -> Optional['Lexicon']:
        """Return the lexicon this lexicon extends, if any.

        If this lexicon is not an extension, return None.
        """
        bases = get_lexicon_extension_bases(self._id, depth=1)
        if bases:
            return _to_lexicon(get_lexicon(bases[0]))
        return None

    def extensions(self, depth: int = 1) -> List['Lexicon']:
        """Return the list of lexicons extending this one.

        By default, only direct extensions are included. This is
        controlled by the *depth* parameter, which if you view
        extensions as children in a tree where the current lexicon is
        the root, *depth=1* are the immediate extensions. Increasing
        this number gets extensions of extensions, or setting it to a
        negative number gets all "descendant" extensions.

        """
        return [_to_lexicon(get_lexicon(rowid))
                for rowid in get_lexicon_extensions(self._id, depth=depth)]


class _LexiconElement(_DatabaseEntity):
    __slots__ = '_lexid', '_wordnet'

    def __init__(
            self,
            _lexid: int = NON_ROWID,
            _id: int = NON_ROWID,
            _wordnet: 'Wordnet' = None
    ):
        super().__init__(_id=_id)
        self._lexid = _lexid  # Database-internal lexicon id
        if _wordnet is None:
            _wordnet = Wordnet()
        self._wordnet: 'Wordnet' = _wordnet

    def lexicon(self):
        return _to_lexicon(get_lexicon(self._lexid))

    def _get_lexicon_ids(self) -> Tuple[int, ...]:
        if self._wordnet._default_mode:
            return tuple(
                {self._lexid}
                | set(get_lexicon_extension_bases(self._lexid))
                | set(get_lexicon_extensions(self._lexid))
            )
        else:
            return self._wordnet._lexicon_ids


class Pronunciation:
    """A class for word form pronunciations."""

    __slots__ = 'value', 'variety', 'notation', 'phonemic', 'audio'

    def __init__(
        self,
        value: str,
        variety: str = None,
        notation: str = None,
        phonemic: bool = True,
        audio: str = None,
    ):
        self.value = value
        self.variety = variety
        self.notation = notation
        self.phonemic = phonemic
        self.audio = audio


class Tag:
    """A general-purpose tag class for word forms."""
    __slots__ = 'tag', 'category',
    __module__ = 'wn'

    def __init__(self, tag: str, category: str):
        self.tag = tag
        self.category = category

    def __eq__(self, other):
        if not isinstance(other, Tag):
            return NotImplemented
        return self.tag == other.tag and self.category == other.category


class Form(str):
    """A word-form string with additional attributes."""
    __slots__ = '_id', 'id', 'script',
    __module__ = 'wn'

    _id: int
    id: Optional[str]
    script: Optional[str]

    def __new__(
        cls,
        form: str,
        id: str = None,
        script: str = None,
        _id: int = NON_ROWID
    ):
        obj = str.__new__(cls, form)  # type: ignore
        obj.id = id
        obj.script = script
        obj._id = _id
        return obj

    def __eq__(self, other):
        if isinstance(other, Form) and self.script != other.script:
            return False
        return str.__eq__(self, other)

    def __hash__(self):
        script = self.script
        if script is None:
            return str.__hash__(self)
        return hash((str(self), self.script))

    def pronunciations(self) -> List[Pronunciation]:
        return [Pronunciation(*data) for data in get_form_pronunciations(self._id)]

    def tags(self) -> List[Tag]:
        return [Tag(tag, category) for tag, category in get_form_tags(self._id)]


class Word(_LexiconElement):
    """A class for words (also called lexical entries) in a wordnet."""
    __slots__ = 'id', 'pos', '_forms'
    __module__ = 'wn'

    _ENTITY_TYPE = 'entries'

    def __init__(
            self,
            id: str,
            pos: str,
            forms: List[Tuple[str, Optional[str], Optional[str], int]],
            _lexid: int = NON_ROWID,
            _id: int = NON_ROWID,
            _wordnet: 'Wordnet' = None
    ):
        super().__init__(_lexid=_lexid, _id=_id, _wordnet=_wordnet)
        self.id = id
        self.pos = pos
        self._forms = forms

    def __repr__(self) -> str:
        return f'Word({self.id!r})'

    def lemma(self) -> Form:
        """Return the canonical form of the word.

        Example:

            >>> wn.words('wolves')[0].lemma()
            'wolf'

        """
        return Form(*self._forms[0])

    def forms(self) -> List[Form]:
        """Return the list of all encoded forms of the word.

        Example:

            >>> wn.words('wolf')[0].forms()
            ['wolf', 'wolves']

        """
        return [Form(*form_data) for form_data in self._forms]

    def senses(self) -> List['Sense']:
        """Return the list of senses of the word.

        Example:

            >>> wn.words('zygoma')[0].senses()
            [Sense('ewn-zygoma-n-05292350-01')]

        """
        lexids = self._get_lexicon_ids()
        iterable = get_entry_senses(self._id, lexids)
        return [Sense(*sense_data, self._wordnet) for sense_data in iterable]

    def metadata(self) -> Metadata:
        """Return the word's metadata."""
        return get_metadata(self._id, 'entries')

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
        self, lexicon: str = None, *, lang: str = None,
    ) -> Dict['Sense', List['Word']]:
        """Return a mapping of word senses to lists of translated words.

        Arguments:
            lexicon: if specified, translate to words in the target lexicon(s)
            lang: if specified, translate to words with the language code

        Example:

            >>> w = wn.words('water bottle', pos='n')[0]
            >>> for sense, words in w.translate(lang='ja').items():
            ...     print(sense, [jw.lemma() for jw in words])
            ...
            Sense('ewn-water_bottle-n-04564934-01') ['水筒']

        """
        result = {}
        for sense in self.senses():
            result[sense] = [
                t_sense.word()
                for t_sense in sense.translate(lang=lang, lexicon=lexicon)
            ]
        return result


T = TypeVar('T', bound='_Relatable')


class _Relatable(_LexiconElement):
    __slots__ = 'id',

    def __init__(
            self,
            id: str,
            _lexid: int = NON_ROWID,
            _id: int = NON_ROWID,
            _wordnet: 'Wordnet' = None
    ):
        super().__init__(_lexid=_lexid, _id=_id, _wordnet=_wordnet)
        self.id = id

    def relations(self: T, *args: str) -> Dict[str, List[T]]:
        raise NotImplementedError

    def get_related(self: T, *args: str) -> List[T]:
        raise NotImplementedError

    def closure(self: T, *args: str) -> Iterator[T]:
        visited = set()
        queue = self.get_related(*args)
        while queue:
            relatable = queue.pop(0)
            if relatable.id not in visited:
                visited.add(relatable.id)
                yield relatable
                queue.extend(relatable.get_related(*args))

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
    __slots__ = 'pos', '_ili'
    __module__ = 'wn'

    _ENTITY_TYPE = 'synsets'

    def __init__(
            self,
            id: str,
            pos: str,
            ili: str = None,
            _lexid: int = NON_ROWID,
            _id: int = NON_ROWID,
            _wordnet: 'Wordnet' = None
    ):
        super().__init__(id=id, _lexid=_lexid, _id=_id, _wordnet=_wordnet)
        self.pos = pos
        self._ili = ili

    @classmethod
    def empty(
            cls,
            id: str,
            ili: str = None,
            _lexid: int = NON_ROWID,
            _wordnet: 'Wordnet' = None
    ):
        return cls(id, pos='', ili=ili, _lexid=_lexid, _wordnet=_wordnet)

    @property
    def ili(self):
        if self._ili:
            row = next(find_ilis(id=self._ili), None)
        else:
            row = next(find_proposed_ilis(synset_rowid=self._id), None)
        if row is not None:
            return ILI(*row)
        return None

    def __hash__(self):
        # include ili and lexid in the hash so inferred synsets don't
        # hash the same
        return hash((self._ENTITY_TYPE, self._ili, self._lexid, self._id))

    def __repr__(self) -> str:
        return f'Synset({self.id!r})'

    def definition(self) -> Optional[str]:
        """Return the first definition found for the synset.

        Example:

            >>> wn.synsets('cartwheel', pos='n')[0].definition()
            'a wheel that has wooden spokes and a metal rim'

        """
        lexids = self._get_lexicon_ids()
        return next(
            (text for text, _, _, _ in get_definitions(self._id, lexids)),
            None
        )

    def examples(self) -> List[str]:
        """Return the list of examples for the synset.

        Example:

            >>> wn.synsets('orbital', pos='a')[0].examples()
            ['"orbital revolution"', '"orbital velocity"']

        """
        lexids = self._get_lexicon_ids()
        exs = get_examples(self._id, 'synsets', lexids)
        return [ex for ex, _, _ in exs]

    def senses(self) -> List['Sense']:
        """Return the list of sense members of the synset.

        Example:

            >>> wn.synsets('umbrella', pos='n')[0].senses()
            [Sense('ewn-umbrella-n-04514450-01')]

        """
        lexids = self._get_lexicon_ids()
        iterable = get_synset_members(self._id, lexids)
        return [Sense(*sense_data, self._wordnet) for sense_data in iterable]

    def lexicalized(self) -> bool:
        """Return True if the synset is lexicalized."""
        return get_lexicalized(self._id, 'synsets')

    def lexfile(self) -> Optional[str]:
        """Return the lexicographer file name for this synset, if any."""
        return get_lexfile(self._id)

    def metadata(self) -> Metadata:
        """Return the synset's metadata."""
        return get_metadata(self._id, 'synsets')

    def words(self) -> List[Word]:
        """Return the list of words linked by the synset's senses.

        Example:

            >>> wn.synsets('exclusive', pos='n')[0].words()
            [Word('ewn-scoop-n'), Word('ewn-exclusive-n')]

        """
        return [sense.word() for sense in self.senses()]

    def lemmas(self) -> List[Form]:
        """Return the list of lemmas of words for the synset.

        Example:

            >>> wn.synsets('exclusive', pos='n')[0].words()
            ['scoop', 'exclusive']

        """
        return [w.lemma() for w in self.words()]

    def relations(self, *args: str) -> Dict[str, List['Synset']]:
        """Return a mapping of relation names to lists of synsets.

        One or more relation names may be given as positional
        arguments to restrict the relations returned. If no such
        arguments are given, all relations starting from the synset
        are returned.

        See :meth:`get_related` for getting a flat list of related
        synsets.

        Example:

            >>> button_rels = wn.synsets('button')[0].relations()
            >>> for relname, sslist in button_rels.items():
            ...     print(relname, [ss.lemmas() for ss in sslist])
            ...
            hypernym [['fixing', 'holdfast', 'fastener', 'fastening']]
            hyponym [['coat button'], ['shirt button']]

        """
        d: Dict[str, List['Synset']] = {}
        for relname, ss in self._get_relations(args):
            if relname in d:
                d[relname].append(ss)
            else:
                d[relname] = [ss]
        return d

    def get_related(self, *args: str) -> List['Synset']:
        """Return the list of related synsets.

        One or more relation names may be given as positional
        arguments to restrict the relations returned. If no such
        arguments are given, all relations starting from the synset
        are returned.

        This method does not preserve the relation names that lead to
        the related synsets. For a mapping of relation names to
        related synsets, see :meth:`relations`.

        Example:

            >>> fulcrum = wn.synsets('fulcrum')[0]
            >>> [ss.lemmas() for ss in fulcrum.get_related()]
            [['pin', 'pivot'], ['lever']]
        """
        return [ss for _, ss in self._get_relations(args)]

    def _get_relations(self, args: Sequence[str]) -> List[Tuple[str, 'Synset']]:
        targets: List[Tuple[str, 'Synset']] = []

        lexids = self._get_lexicon_ids()

        # first get relations from the current lexicon(s)
        if self._id != NON_ROWID:
            relations = list(get_synset_relations({self._id}, args, lexids))
            targets.extend((row[0], Synset(*row[2:], self._wordnet))
                           for row in relations
                           if row[5] in lexids)

        # then attempt to expand via ILI
        if self._ili is not None and self._wordnet and self._wordnet._expanded_ids:
            expids = self._wordnet._expanded_ids

            # get expanded relation
            expss = find_synsets(ili=self._ili, lexicon_rowids=expids)
            rowids = {rowid for _, _, _, _, rowid in expss} - {self._id, NON_ROWID}
            relations = list(get_synset_relations(rowids, args, expids))
            ilis = {row[4] for row in relations} - {None}

            # map back to target lexicons
            seen = {ss._id for _, ss in targets}
            for row in get_synsets_for_ilis(ilis, lexicon_rowids=lexids):
                if row[-1] not in seen:
                    targets.append((row[0], Synset(*row, self._wordnet)))

            # add empty synsets for ILIs without a target in lexids
            unseen_ilis = ilis - {tgt._ili for _, tgt in targets}
            for rel_row in relations:
                if rel_row[4] in unseen_ilis:
                    ss = Synset.empty(
                        id=_INFERRED_SYNSET,
                        ili=rel_row[4],
                        _lexid=self._lexid,
                        _wordnet=self._wordnet
                    )
                    targets.append((rel_row[0], ss))

        return targets

    def hypernym_paths(self, simulate_root: bool = False) -> List[List['Synset']]:
        """Return the list of hypernym paths to a root synset."""
        return taxonomy.hypernym_paths(self, simulate_root=simulate_root)

    def min_depth(self, simulate_root: bool = False) -> int:
        """Return the minimum taxonomy depth of the synset."""
        return taxonomy.min_depth(self, simulate_root=simulate_root)

    def max_depth(self, simulate_root: bool = False) -> int:
        """Return the maximum taxonomy depth of the synset."""
        return taxonomy.max_depth(self, simulate_root=simulate_root)

    def shortest_path(
            self, other: 'Synset', simulate_root: bool = False
    ) -> List['Synset']:
        """Return the shortest path from the synset to the *other* synset."""
        return taxonomy.shortest_path(
            self, other, simulate_root=simulate_root
        )

    def common_hypernyms(
            self, other: 'Synset', simulate_root: bool = False
    ) -> List['Synset']:
        """Return the common hypernyms for the current and *other* synsets."""
        return taxonomy.common_hypernyms(
            self, other, simulate_root=simulate_root
        )

    def lowest_common_hypernyms(
            self, other: 'Synset', simulate_root: bool = False
    ) -> List['Synset']:
        """Return the common hypernyms furthest from the root."""
        return taxonomy.lowest_common_hypernyms(
            self, other, simulate_root=simulate_root
        )

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

    def translate(self, lexicon: str = None, *, lang: str = None) -> List['Synset']:
        """Return a list of translated synsets.

        Arguments:
            lexicon: if specified, translate to synsets in the target lexicon(s)
            lang: if specified, translate to synsets with the language code

        Example:

            >>> es = wn.synsets('araña', lang='es')[0]
            >>> en = es.translate(lexicon='ewn')[0]
            >>> en.lemmas()
            ['spider']

        """
        ili = self._ili
        if not ili:
            return []
        return synsets(ili=ili, lang=lang, lexicon=lexicon)


class Count(int):
    """A count of sense occurrences in some corpus."""
    __module__ = 'wn'

    _id: int

    def __new__(cls, value, _id: int = NON_ROWID):
        obj = int.__new__(cls, value)  # type: ignore
        obj._id = _id
        return obj

    def metadata(self) -> Metadata:
        """Return the count's metadata."""
        return get_metadata(self._id, 'counts')


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
            _lexid: int = NON_ROWID,
            _id: int = NON_ROWID,
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

    def examples(self) -> List[str]:
        """Return the list of examples for the sense."""
        lexids = self._get_lexicon_ids()
        exs = get_examples(self._id, 'senses', lexids)
        return [ex for ex, _, _ in exs]

    def lexicalized(self) -> bool:
        """Return True if the sense is lexicalized."""
        return get_lexicalized(self._id, 'senses')

    def adjposition(self) -> Optional[str]:
        """Return the adjective position of the sense.

        Values include :python:`"a"` (attributive), :python:`"p"`
        (predicative), and :python:`"ip"` (immediate
        postnominal). Note that this is only relevant for adjectival
        senses. Senses for other parts of speech, or for adjectives
        that are not annotated with this feature, will return
        ``None``.

        """
        return get_adjposition(self._id)

    def frames(self) -> List[str]:
        """Return the list of subcategorization frames for the sense."""
        lexids = self._get_lexicon_ids()
        return get_syntactic_behaviours(self._id, lexids)

    def counts(self) -> List[Count]:
        """Return the corpus counts stored for this sense."""
        lexids = self._get_lexicon_ids()
        return [Count(value, _id=_id)
                for value, _id in get_sense_counts(self._id, lexids)]

    def metadata(self) -> Metadata:
        """Return the sense's metadata."""
        return get_metadata(self._id, 'senses')

    def relations(self, *args: str) -> Dict[str, List['Sense']]:
        """Return a mapping of relation names to lists of senses.

        One or more relation names may be given as positional
        arguments to restrict the relations returned. If no such
        arguments are given, all relations starting from the sense
        are returned.

        See :meth:`get_related` for getting a flat list of related
        senses.

        """
        d: Dict[str, List['Sense']] = {}
        for relname, s in self._get_relations(args):
            if relname in d:
                d[relname].append(s)
            else:
                d[relname] = [s]
        return d

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
        return [s for _, s in self._get_relations(args)]

    def _get_relations(self, args: Sequence[str]) -> List[Tuple[str, 'Sense']]:
        lexids = self._get_lexicon_ids()
        iterable = get_sense_relations(self._id, args, lexids)
        return [(relname, Sense(sid, eid, ssid, lexid, rowid, self._wordnet))
                for relname, _, sid, eid, ssid, lexid, rowid in iterable
                if lexids is None or lexid in lexids]

    def get_related_synsets(self, *args: str) -> List[Synset]:
        """Return a list of related synsets."""
        lexids = self._get_lexicon_ids()
        iterable = get_sense_synset_relations(self._id, args, lexids)
        return [Synset(ssid, pos, ili, lexid, rowid, self._wordnet)
                for _, _, ssid, pos, ili, lexid, rowid in iterable
                if lexids is None or lexid in lexids]

    def translate(self, lexicon: str = None, *, lang: str = None) -> List['Sense']:
        """Return a list of translated senses.

        Arguments:
            lexicon: if specified, translate to senses in the target lexicon(s)
            lang: if specified, translate to senses with the language code

        Example:

            >>> en = wn.senses('petiole', lang='en')[0]
            >>> pt = en.translate(lang='pt')[0]
            >>> pt.word().lemma()
            'pecíolo'

        """
        synset = self.synset()
        return [t_sense
                for t_synset in synset.translate(lang=lang, lexicon=lexicon)
                for t_sense in t_synset.senses()]


# Useful for factory functions of Word, Sense, or Synset
C = TypeVar('C', Word, Sense, Synset)


class Wordnet:

    """Class for interacting with wordnet data.

    A wordnet object acts essentially as a filter by first selecting
    matching lexicons and then searching only within those lexicons
    for later queries. On instantiation, a *lang* argument is a `BCP
    47`_ language code that restricts the selected lexicons to those
    whose language matches the given code. A *lexicon* argument is a
    space-separated list of lexicon specifiers that more directly
    selects lexicons by their ID and version; this is preferable when
    there are multiple lexicons in the same language or multiple
    version with the same ID.

    Some wordnets were created by translating the words from a larger
    wordnet, namely the Princeton WordNet, and then relying on the
    larger wordnet for structural relations. An *expand* argument is a
    second space-separated list of lexicon specifiers which are used
    for traversing relations, but not as the results of
    queries. Setting *expand* to an empty string (:python:`expand=''`)
    disables expand lexicons.

    The *normalizer* argument takes a callable that normalizes word
    forms in order to expand the search. The default function
    downcases the word and removes diacritics via NFKD_ normalization
    so that, for example, searching for *san josé* in the English
    WordNet will find the entry for *San Jose*. Setting *normalizer*
    to :python:`None` disables normalization and forces exact-match
    searching.

    The *lemmatizer* argument may be :python:`None`, which is the
    default and disables lemmatizer-based query expansion, or a
    callable that takes a word form and optional part of speech and
    returns base forms of the original word. To support lemmatizers
    that use the wordnet for instantiation, such as :mod:`wn.morphy`,
    the lemmatizer may be assigned to the :attr:`lemmatizer` attribute
    after creation.

    If the *search_all_forms* argument is :python:`True` (the
    default), searches of word forms consider all forms in the
    lexicon; if :python:`False`, only lemmas are searched. Non-lemma
    forms may include, depending on the lexicon, morphological
    exceptions, alternate scripts or spellings, etc.

    .. _BCP 47: https://en.wikipedia.org/wiki/IETF_language_tag
    .. _NFKD: https://en.wikipedia.org/wiki/Unicode_equivalence#Normal_forms

    Attributes:

        lemmatizer: A lemmatization function or :python:`None`.

    """

    __slots__ = ('_lexicons', '_lexicon_ids', '_expanded', '_expanded_ids',
                 '_default_mode', '_normalizer', 'lemmatizer',
                 '_search_all_forms',)
    __module__ = 'wn'

    def __init__(
        self,
        lexicon: str = None,
        *,
        lang: str = None,
        expand: str = None,
        normalizer: Optional[NormalizeFunction] = normalize_form,
        lemmatizer: Optional[LemmatizeFunction] = None,
        search_all_forms: bool = True,
    ):
        # default mode means any lexicon is searched or expanded upon,
        # but relation traversals only target the source's lexicon
        self._default_mode = (not lexicon and not lang)

        lexs = list(find_lexicons(lexicon or '*', lang=lang))
        self._lexicons: Tuple[Lexicon, ...] = tuple(map(_to_lexicon, lexs))
        self._lexicon_ids: Tuple[int, ...] = tuple(lx._id for lx in self._lexicons)

        self._expanded: Tuple[Lexicon, ...] = ()
        if expand is None:
            if self._default_mode:
                expand = '*'
            else:
                deps = [(id, ver, _id)
                        for lex in self._lexicons
                        for id, ver, _, _id in get_lexicon_dependencies(lex._id)]
                # warn only if a dep is missing and a lexicon was specified
                if not self._default_mode:
                    missing = ' '.join(
                        f'{id}:{ver}' for id, ver, _id in deps if _id is None
                    )
                    if missing:
                        warnings.warn(
                            f'lexicon dependencies not available: {missing}',
                            wn.WnWarning
                        )
                expand = ' '.join(
                    f'{id}:{ver}' for id, ver, _id in deps if _id is not None
                )
        if expand:
            self._expanded = tuple(map(_to_lexicon, find_lexicons(lexicon=expand)))
        self._expanded_ids: Tuple[int, ...] = tuple(lx._id for lx in self._expanded)

        self._normalizer = normalizer
        self.lemmatizer = lemmatizer
        self._search_all_forms = search_all_forms

    def lexicons(self):
        """Return the list of lexicons covered by this wordnet."""
        return self._lexicons

    def expanded_lexicons(self):
        """Return the list of expand lexicons for this wordnet."""
        return self._expanded

    def word(self, id: str) -> Word:
        """Return the first word in this wordnet with identifier *id*."""
        iterable = find_entries(id=id, lexicon_rowids=self._lexicon_ids)
        try:
            return Word(*next(iterable), self)
        except StopIteration:
            raise wn.Error(f'no such lexical entry: {id}')

    def words(self, form: str = None, pos: str = None) -> List[Word]:
        """Return the list of matching words in this wordnet.

        Without any arguments, this function returns all words in the
        wordnet's selected lexicons. A *form* argument restricts the
        words to those matching the given word form, and *pos*
        restricts words by their part of speech.

        """
        return _find_helper(self, Word, find_entries, form, pos)

    def synset(self, id: str) -> Synset:
        """Return the first synset in this wordnet with identifier *id*."""
        iterable = find_synsets(id=id, lexicon_rowids=self._lexicon_ids)
        try:
            return Synset(*next(iterable), self)
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
        return _find_helper(self, Synset, find_synsets, form, pos, ili=ili)

    def sense(self, id: str) -> Sense:
        """Return the first sense in this wordnet with identifier *id*."""
        iterable = find_senses(id=id, lexicon_rowids=self._lexicon_ids)
        try:
            return Sense(*next(iterable), self)
        except StopIteration:
            raise wn.Error(f'no such sense: {id}')

    def senses(self, form: str = None, pos: str = None) -> List[Sense]:
        """Return the list of matching senses in this wordnet.

        Without any arguments, this function returns all senses in the
        wordnet's selected lexicons. A *form* argument restricts the
        senses to those whose word matches the given word form, and
        *pos* restricts senses by their word's part of speech.

        """
        return _find_helper(self, Sense, find_senses, form, pos)

    def ili(self, id: str) -> ILI:
        """Return the first ILI in this wordnet with identifer *id*."""
        iterable = find_ilis(id=id, lexicon_rowids=self._lexicon_ids)
        try:
            return ILI(*next(iterable))
        except StopIteration:
            raise wn.Error(f'no such ILI: {id}')

    def ilis(self, status: str = None) -> List[ILI]:
        """Return the list of ILIs in this wordnet.

        If *status* is given, only return ILIs with a matching status.

        """
        iterable = find_ilis(status=status, lexicon_rowids=self._lexicon_ids)
        return [ILI(*ili_data) for ili_data in iterable]


def _to_lexicon(data) -> Lexicon:
    rowid, id, label, language, email, license, version, url, citation, logo = data
    return Lexicon(
        id,
        label,
        language,
        email,
        license,
        version,
        url=url,
        citation=citation,
        logo=logo,
        _id=rowid
    )


def _find_helper(
    w: Wordnet,
    cls: Type[C],
    query_func: Callable,
    form: Optional[str],
    pos: Optional[str],
    ili: str = None
) -> List[C]:
    """Return the list of matching wordnet entities.

    If the wordnet has a normalizer and the search includes a word
    form, the original word form is searched against both the
    original and normalized columns in the database. Then, if no
    results are found, the search is repeated with the normalized
    form. If the wordnet does not have a normalizer, only exact
    string matches are used.

    """
    kwargs: Dict = {
        'lexicon_rowids': w._lexicon_ids,
        'search_all_forms': w._search_all_forms,
    }
    if ili is not None:
        kwargs['ili'] = ili

    # easy case is when there is no form
    if form is None:
        return [cls(*data, w)  # type: ignore
                for data in query_func(pos=pos, **kwargs)]

    # if there's a form, we may need to lemmatize and normalize
    lemmatize = w.lemmatizer
    normalize = w._normalizer
    kwargs['normalized'] = bool(normalize)

    forms = lemmatize(form, pos) if lemmatize else {}
    # if no lemmatizer or word not covered by lemmatizer, back off to
    # the original form and pos
    if not forms:
        forms = {pos: {form}}

    results = [
        cls(*data, w)  # type: ignore
        for _pos, _forms in forms.items()
        for data in query_func(forms=_forms, pos=_pos, **kwargs)
    ]
    if not results and normalize:
        results = [
            cls(*data, w)  # type: ignore
            for _pos, _forms in forms.items()
            for data in query_func(
                forms=[normalize(f) for f in _forms], pos=_pos, **kwargs
            )
        ]
    return results


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


def lexicons(*, lexicon: str = None, lang: str = None) -> List[Lexicon]:
    """Return the lexicons matching a language or lexicon specifier.

    Example:

        >>> wn.lexicons(lang='en')
        [<Lexicon ewn:2020 [en]>, <Lexicon pwn:3.0 [en]>]

    """
    try:
        w = Wordnet(lang=lang, lexicon=lexicon)
    except wn.Error:
        return []
    else:
        return w.lexicons()


def word(id: str, *, lexicon: str = None, lang: str = None) -> Word:
    """Return the word with *id* in *lexicon*.

    This will create a :class:`Wordnet` object using the *lang* and
    *lexicon* arguments. The *id* argument is then passed to the
    :meth:`Wordnet.word` method.

    >>> wn.word('ewn-cell-n')
    Word('ewn-cell-n')

    """
    return Wordnet(lang=lang, lexicon=lexicon).word(id=id)


def words(
    form: str = None,
    pos: str = None,
    *,
    lexicon: str = None,
    lang: str = None,
) -> List[Word]:
    """Return the list of matching words.

    This will create a :class:`Wordnet` object using the *lang* and
    *lexicon* arguments. The remaining arguments are passed to the
    :meth:`Wordnet.words` method.

    >>> len(wn.words())
    282902
    >>> len(wn.words(pos='v'))
    34592
    >>> wn.words(form="scurry")
    [Word('ewn-scurry-n'), Word('ewn-scurry-v')]

    """
    return Wordnet(lang=lang, lexicon=lexicon).words(form=form, pos=pos)


def synset(id: str, *, lexicon: str = None, lang: str = None) -> Synset:
    """Return the synset with *id* in *lexicon*.

    This will create a :class:`Wordnet` object using the *lang* and
    *lexicon* arguments. The *id* argument is then passed to the
    :meth:`Wordnet.synset` method.

    >>> wn.synset('ewn-03311152-n')
    Synset('ewn-03311152-n')

    """
    return Wordnet(lang=lang, lexicon=lexicon).synset(id=id)


def synsets(
    form: str = None,
    pos: str = None,
    ili: str = None,
    *,
    lexicon: str = None,
    lang: str = None,
) -> List[Synset]:
    """Return the list of matching synsets.

    This will create a :class:`Wordnet` object using the *lang* and
    *lexicon* arguments. The remaining arguments are passed to the
    :meth:`Wordnet.synsets` method.

    >>> len(wn.synsets('couch'))
    4
    >>> wn.synsets('couch', pos='v')
    [Synset('ewn-00983308-v')]

    """
    return Wordnet(lang=lang, lexicon=lexicon).synsets(form=form, pos=pos, ili=ili)


def senses(
    form: str = None,
    pos: str = None,
    *,
    lexicon: str = None,
    lang: str = None,
) -> List[Sense]:
    """Return the list of matching senses.

    This will create a :class:`Wordnet` object using the *lang* and
    *lexicon* arguments. The remaining arguments are passed to the
    :meth:`Wordnet.senses` method.

    >>> len(wn.senses('twig'))
    3
    >>> wn.senses('twig', pos='n')
    [Sense('ewn-twig-n-13184889-02')]

    """
    return Wordnet(lang=lang, lexicon=lexicon).senses(form=form, pos=pos)


def sense(id: str, *, lexicon: str = None, lang: str = None) -> Sense:
    """Return the sense with *id* in *lexicon*.

    This will create a :class:`Wordnet` object using the *lang* and
    *lexicon* arguments. The *id* argument is then passed to the
    :meth:`Wordnet.sense` method.

    >>> wn.sense('ewn-flutter-v-01903884-02')
    Sense('ewn-flutter-v-01903884-02')

    """
    return Wordnet(lang=lang, lexicon=lexicon).sense(id=id)


def ili(id: str, *, lexicon: str = None, lang: str = None) -> ILI:
    """Return the interlingual index with *id*.

    This will create a :class:`Wordnet` object using the *lang* and
    *lexicon* arguments. The *id* argument is then passed to the
    :meth:`Wordnet.ili` method.

    >>> wn.ili(id='i1234')
    ILI('i1234')
    >>> wn.ili(id='i1234').status
    'presupposed'

    """
    return Wordnet(lang=lang, lexicon=lexicon).ili(id=id)


def ilis(
    status: str = None,
    *,
    lexicon: str = None,
    lang: str = None,
) -> List[ILI]:
    """Return the list of matching interlingual indices.

    This will create a :class:`Wordnet` object using the *lang* and
    *lexicon* arguments. The remaining arguments are passed to the
    :meth:`Wordnet.ilis` method.

    >>> len(wn.ilis())
    120071
    >>> len(wn.ilis(status='proposed'))
    2573
    >>> wn.ilis(status='proposed')[-1].definition()
    'the neutrino associated with the tau lepton.'
    >>> len(wn.ilis(lang='de'))
    13818

    """
    return Wordnet(lang=lang, lexicon=lexicon).ilis(status=status)
