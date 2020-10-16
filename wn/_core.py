
from typing import Any, TypeVar, Optional, List, Tuple, Dict, Set, Iterator

import wn
from wn import _db


# NOTE: Separation of Concerns
#
# This module hooks into the wn._db module but generally interacts
# only through publicly known identifiers. One exception is the rowids
# of Words, Synsets, and Senses. Without these we would need a 3-tuple
# of (id, lexicon-id, lexicon-version) in order to uniquely find
# particular rows in the database, and the queries in wn._db would
# become much more complicated. These rowids should not be exposed to
# the users, and further coupling to the wn._db module is discouraged.

class Lexicon:
    __slots__ = ('_id', 'id', 'label', 'language', 'email', 'license',
                 'version', 'url', 'citation', 'metadata')

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
            _id: int = -1,
    ):
        self._id = _id
        self.id = id
        self.label = label
        self.language = language
        self.email = email
        self.license = license
        self.version = version
        self.url = url
        self.citation = citation
        self.metadata = metadata


class _LexiconElement:
    __slots__ = '_id', '_wordnet'

    def __init__(self, _id: int = -1, _wordnet: 'WordNet' = None):
        self._id = _id  # Database-internal id (e.g., rowid)
        self._wordnet = _wordnet


class Word(_LexiconElement):
    __slots__ = 'id', 'pos', '_forms'

    def __init__(
            self,
            id: str,
            pos: str,
            forms: List[str],
            _id: int = -1,
            _wordnet: 'WordNet' = None
    ):
        super().__init__(_id=_id, _wordnet=_wordnet)
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
        return [Sense(id, entry_id, synset_id, rowid, self._wordnet)
                for rowid, id, entry_id, synset_id in iterable]

    def synsets(self) -> List['Synset']:
        return [sense.synset() for sense in self.senses()]

    def derived_words(self) -> List['Word']:
        return [derived_sense.word()
                for sense in self.senses()
                for derived_sense in sense.derivations()]


T = TypeVar('T', bound='_Relatable')


class _Relatable(_LexiconElement):
    __slots__ = 'id',

    def __init__(self, id: str, _id: int = -1, _wordnet: 'WordNet' = None):
        super().__init__(_id=_id, _wordnet=_wordnet)
        self.id = id

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

    def __init__(
            self,
            id: str,
            pos: str,
            ili: str = None,
            _id: int = -1,
            _wordnet: 'WordNet' = None
    ):
        super().__init__(id=id, _id=_id, _wordnet=_wordnet)
        self.pos = pos
        self.ili = ili

    def __repr__(self) -> str:
        return f'Synset({self.id!r})'

    def definition(self) -> Optional[str]:
        return next(iter(_db.get_definitions_for_synset(self._id)), None)

    def examples(self) -> List[str]:
        return _db.get_examples_for_synset(self._id)

    def senses(self) -> List['Sense']:
        iterable = _db.get_senses_for_synset(self._id)
        return [Sense(id, entry_id, synset_id, rowid, self._wordnet)
                for rowid, id, entry_id, synset_id in iterable]

    def words(self) -> List[Word]:
        return [sense.word() for sense in self.senses()]

    def lemmas(self) -> List[str]:
        return [w.lemma() for w in self.words()]

    def get_related(self, *args: str) -> List['Synset']:
        lexids = None
        expids = None
        if self._wordnet:
            lexids = self._wordnet._lexicon_ids
            expids = self._wordnet._expanded_ids or lexids
        iterable = _db.get_synset_relations(
            self._id,
            args,
            lexicon_rowids=lexids,
            expand_rowids=expids
        )
        return [Synset(id, pos, ili, rowid, self._wordnet)
                for rowid, id, pos, ili in iterable]

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

    def __init__(
            self,
            id: str,
            entry_id: str,
            synset_id: str,
            _id: int = -1,
            _wordnet: 'WordNet' = None
    ):
        super().__init__(id=id, _id=_id, _wordnet=_wordnet)
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
        return [Sense(id, entry_id, synset_id, rowid, self._wordnet)
                for rowid, id, entry_id, synset_id in iterable]

    def get_related_synsets(self, *args: str) -> List[Synset]:
        iterable = _db.get_sense_synset_relations(self._id, args)
        return [Synset(id, pos, ili, rowid, self._wordnet)
                for rowid, id, pos, ili in iterable]

    def derivations(self) -> List['Sense']:
        return self.get_related('derivation')

    def pertainyms(self) -> List['Sense']:
        return self.get_related('pertainym')


class WordNet:
    """
    Class for interacting with WordNet data.
    """

    __slots__ = 'lgcode', '_lexicons', '_lexicon_ids', '_expanded', '_expanded_ids'

    def __init__(self, lgcode: str = None, lexicon: str = None, expand: str = None):
        self.lgcode = lgcode

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

    def word(self, id: str) -> Word:
        iterable = _db.find_entries(id=id, lexicon_rowids=self._lexicon_ids)
        try:
            rowid, id, pos, forms = next(iterable)
            return Word(id, pos, forms, rowid, self)
        except StopIteration:
            raise wn.Error(f'no such lexical entry: {id}')

    def words(self, form: str = None, pos: str = None) -> List[Word]:
        iterable = _db.find_entries(
            form=form, pos=pos, lexicon_rowids=self._lexicon_ids
        )
        return [Word(id, pos, forms, rowid, self)
                for rowid, id, pos, forms in iterable]

    def synset(self, id: str) -> Synset:
        iterable = _db.find_synsets(id=id, lexicon_rowids=self._lexicon_ids)
        try:
            rowid, id, pos, ili = next(iterable)
            return Synset(id, pos, ili, rowid, self)
        except StopIteration:
            raise wn.Error(f'no such synset: {id}')

    def synsets(
        self, form: str = None, pos: str = None, ili: str = None
    ) -> List[Synset]:
        iterable = _db.find_synsets(
            form=form, pos=pos, ili=ili, lexicon_rowids=self._lexicon_ids
        )
        return [Synset(id, pos, ili, rowid, self) for rowid, id, pos, ili in iterable]

    def sense(self, id: str) -> Sense:
        iterable = _db.find_senses(id=id, lexicon_rowids=self._lexicon_ids)
        try:
            rowid, id, entry_id, synset_id = next(iterable)
            return Sense(id, entry_id, synset_id, rowid, self)
        except StopIteration:
            raise wn.Error(f'no such sense: {id}')

    def senses(self, form: str = None, pos: str = None) -> List[Sense]:
        iterable = _db.find_senses(
            form=form, pos=pos, lexicon_rowids=self._lexicon_ids
        )
        return [Sense(id, entry_id, synset_id, rowid, self)
                for rowid, id, entry_id, synset_id in iterable]


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
