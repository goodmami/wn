
import enum
import textwrap
import warnings
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from typing import Literal, Optional, TypeVar, Union, overload

import wn
from wn._types import (
    Metadata,
    NormalizeFunction,
    LemmatizeFunction,
)
from wn._util import (
    normalize_form,
    unique_list,
    format_lexicon_specifier,
)
from wn._queries import (
    find_ilis,
    find_existing_ilis,
    find_proposed_ilis,
    find_entries,
    find_senses,
    find_synsets,
    get_lexicon,
    get_modified,
    get_lexicon_dependencies,
    get_lexicon_extension_bases,
    get_lexicon_extensions,
    get_entry_forms,
    get_entry_senses,
    get_sense_relations,
    get_sense_synset_relations,
    get_synset_relations,
    get_expanded_synset_relations,
    get_synset_members,
    get_synsets_for_ilis,
    get_examples,
    get_definitions,
    get_syntactic_behaviours,
    get_metadata,
    get_ili_metadata,
    get_proposed_ili_metadata,
    get_lexicalized,
    get_adjposition,
    get_sense_counts,
    get_lexfile,
    resolve_lexicon_specifiers,
)
from wn import taxonomy

_INFERRED_SYNSET = '*INFERRED*'


class _EntityType(str, enum.Enum):
    """Identifies the database table of an entity."""
    LEXICONS = 'lexicons'
    ENTRIES = 'entries'
    SENSES = 'senses'
    SYNSETS = 'synsets'
    SENSE_RELATIONS = 'sense_relations'
    SENSE_SYNSET_RELATIONS = 'sense_synset_relations'
    SYNSET_RELATIONS = 'synset_relations'
    UNSET = ''


@dataclass(frozen=True)  # slots=True from Python 3.10
class ILI:
    """A class for interlingual indices."""
    __module__ = 'wn'
    __slots__ = '_id', 'status', '_definition'

    _id: Optional[str]
    status: str
    _definition: Optional[str]

    def __eq__(self, other) -> bool:
        raise NotImplementedError

    def __hash__(self) -> int:
        raise NotImplementedError

    @property
    def id(self) -> Optional[str]:
        return self._id

    def definition(self) -> Optional[str]:
        return self._definition

    def metadata(self) -> Metadata:
        """Return the ILI's metadata."""
        raise NotImplementedError


@dataclass(frozen=True)  # slots=True from Python 3.10
class _ExistingILI(ILI):
    """A class for interlingual indices."""
    __module__ = 'wn'

    _id: str
    status: str
    _definition: Optional[str]

    def __eq__(self, other) -> bool:
        if isinstance(other, _ExistingILI):
            return self._id == other._id
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f'ILI({repr(self._id)})'

    def metadata(self) -> Metadata:
        """Return the ILI's metadata."""
        return get_ili_metadata(self._id)


@dataclass(frozen=True)  # slots=True from Python 3.10
class _ProposedILI(ILI):
    __module__ = 'wn'
    __slots__ = '_synset', '_lexicon'

    _id: None
    status: str
    _definition: Optional[str]
    _synset: str
    _lexicon: str

    def __eq__(self, other) -> bool:
        if isinstance(other, _ProposedILI):
            return (
                self._synset == other._synset
                and self._lexicon == other._lexicon
            )
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self._synset, self._lexicon))

    def metadata(self) -> Metadata:
        """Return the ILI's metadata."""
        return get_proposed_ili_metadata(self._synset, self._lexicon)


@dataclass(eq=True, frozen=True)  # slots=True from Python 3.10
class Lexicon:
    """A class representing a wordnet lexicon."""
    __module__ = 'wn'

    id: str
    label: str
    language: str
    email: str
    license: str
    version: str
    url: Optional[str] = None
    citation: Optional[str] = None
    logo: Optional[str] = None
    _metadata: Optional[Metadata] = field(default=None, hash=False)
    _specifier: str = field(init=False, hash=False)

    def __post_init__(self) -> None:
        specifier = format_lexicon_specifier(self.id, self.version)
        object.__setattr__(self, '_specifier', specifier)

    def __repr__(self):
        return f'<Lexicon {self._specifier} [{self.language}]>'

    def metadata(self) -> Metadata:
        """Return the lexicon's metadata."""
        return self._metadata if self._metadata is not None else {}

    def specifier(self) -> str:
        """Return the *id:version* lexicon specifier."""
        return self._specifier

    def modified(self) -> bool:
        """Return True if the lexicon has local modifications."""
        return get_modified(self._specifier)

    def requires(self) -> dict[str, Optional['Lexicon']]:
        """Return the lexicon dependencies."""
        return dict(
            (spec,
             None if added is None else _to_lexicon(spec))
            for spec, _, added in get_lexicon_dependencies(self._specifier)
        )

    def extends(self) -> Optional['Lexicon']:
        """Return the lexicon this lexicon extends, if any.

        If this lexicon is not an extension, return None.
        """
        bases = get_lexicon_extension_bases(self._specifier, depth=1)
        if bases:
            return _to_lexicon(bases[0])
        return None

    def extensions(self, depth: int = 1) -> list['Lexicon']:
        """Return the list of lexicons extending this one.

        By default, only direct extensions are included. This is
        controlled by the *depth* parameter, which if you view
        extensions as children in a tree where the current lexicon is
        the root, *depth=1* are the immediate extensions. Increasing
        this number gets extensions of extensions, or setting it to a
        negative number gets all "descendant" extensions.

        """
        return [
            _to_lexicon(spec)
            for spec in get_lexicon_extensions(self._specifier, depth=depth)
        ]

    def describe(self, full: bool = True) -> str:
        """Return a formatted string describing the lexicon.

        The *full* argument (default: :python:`True`) may be set to
        :python:`False` to omit word and sense counts.

        Also see: :meth:`Wordnet.describe`

        """
        lexspecs = (self.specifier(),)
        substrings: list[str] = [
            f'{self._specifier}',
            f'  Label  : {self.label}',
            f'  URL    : {self.url}',
            f'  License: {self.license}',
        ]
        if full:
            substrings.extend([
                f'  Words  : {_desc_counts(find_entries, lexspecs)}',
                f'  Senses : {sum(1 for _ in find_senses(lexicons=lexspecs))}',
            ])
        substrings.extend([
            f'  Synsets: {_desc_counts(find_synsets, lexspecs)}',
            f'  ILIs   : {sum(1 for _ in find_ilis(lexicons=lexspecs)):>6}',
        ])
        return '\n'.join(substrings)


def _desc_counts(query: Callable, lexspecs: Sequence[str]) -> str:
    count: dict[str, int] = {}
    for _, pos, *_ in query(lexicons=lexspecs):
        if pos not in count:
            count[pos] = 1
        else:
            count[pos] += 1
    subcounts = ', '.join(f'{pos}: {count[pos]}' for pos in sorted(count))
    return f'{sum(count.values()):>6} ({subcounts})'


@dataclass
class _LexiconConfiguration:
    # slots=True from Python 3.10
    __slots__ = "lexicons", "expands", "default_mode"
    lexicons: tuple[str, ...]
    expands: tuple[str, ...]
    default_mode: bool


_EMPTY_LEXCONFIG = _LexiconConfiguration(
    lexicons=(),
    expands=(),
    default_mode=False,
)


class _LexiconElement:
    __slots__ = 'id', '_lexicon', '_lexconf'

    id: str

    def __init__(
        self,
        id: str,
        _lexicon: str = '',
        _lexconf: _LexiconConfiguration = _EMPTY_LEXCONFIG,
    ):
        self.id = id
        self._lexicon = _lexicon  # source lexicon specifier
        self._lexconf = _lexconf

    def __eq__(self, other) -> bool:
        if isinstance(other, type(self)) or isinstance(self, type(other)):
            return (
                self.id == other.id
                and self._lexicon == other._lexicon
            )
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.id, self._lexicon))

    def lexicon(self) -> Lexicon:
        return _to_lexicon(self._lexicon)

    def _get_lexicons(self) -> tuple[str, ...]:
        if self._lexconf.default_mode:
            return tuple([
                self._lexicon,
                *get_lexicon_extension_bases(self._lexicon),
                *get_lexicon_extensions(self._lexicon)
            ])
        else:
            return self._lexconf.lexicons


@dataclass(frozen=True)  # slots=True from Python 3.10
class Pronunciation:
    """A class for word form pronunciations."""

    __module__ = 'wn'

    value: str
    variety: Optional[str] = None
    notation: Optional[str] = None
    phonemic: bool = True
    audio: Optional[str] = None


@dataclass(frozen=True)  # slots=True from Python 3.10
class Tag:
    """A general-purpose tag class for word forms."""
    __module__ = 'wn'
    __slots__ = 'tag', 'category'

    tag: str
    category: str


@dataclass(frozen=True)  # slots=True from Python 3.10
class Form:
    """A word-form."""
    __module__ = 'wn'

    value: str
    id: Optional[str] = field(default=None, repr=False, compare=False)
    script: Optional[str] = field(default=None, repr=False)
    _pronunciations: tuple[Pronunciation, ...] = field(
        default_factory=tuple, repr=False, compare=False
    )
    _tags: tuple[Tag, ...] = field(
        default_factory=tuple, repr=False, compare=False
    )

    def pronunciations(self) -> list[Pronunciation]:
        return list(self._pronunciations)

    def tags(self) -> list[Tag]:
        return list(self._tags)


def _make_form(
    form: str,
    id: Optional[str],
    script: Optional[str],
    prons: list[tuple[str, Optional[str], Optional[str], bool, Optional[str]]],
    tags: list[tuple[str, str]],
) -> Form:
    return Form(
        form,
        id=id,
        script=script,
        _pronunciations=tuple(Pronunciation(*data) for data in prons),
        _tags=tuple(Tag(*data) for data in tags),
    )


class Word(_LexiconElement):
    """A class for words (also called lexical entries) in a wordnet."""
    __slots__ = 'pos',
    __module__ = 'wn'

    _ENTITY_TYPE = _EntityType.ENTRIES

    pos: str

    def __init__(
        self,
        id: str,
        pos: str,
        _lexicon: str = '',
        _lexconf: _LexiconConfiguration = _EMPTY_LEXCONFIG,
    ):
        super().__init__(id=id, _lexicon=_lexicon, _lexconf=_lexconf)
        self.pos = pos

    def __repr__(self) -> str:
        return f'Word({self.id!r})'

    @overload
    def lemma(self, *, data: Literal[False] = False) -> str: ...
    @overload
    def lemma(self, *, data: Literal[True] = True) -> Form: ...

    # fallback for non-literal bool argument
    @overload
    def lemma(self, *, data: bool) -> Union[str, Form]: ...

    def lemma(self, *, data: bool = False) -> Union[str, Form]:
        """Return the canonical form of the word.

        If the *data* argument is :python:`False` (the default), the
        lemma is returned as a :class:`str` type. If it is
        :python:`True`, a :class:`wn.Form` object is used instead.

        Example:

            >>> wn.words('wolves')[0].lemma()
            'wolf'
            >>> wn.words('wolves')[0].lemma(data=True)
            Form(value='wolf')

        """
        lexicons = self._get_lexicons()
        lemma_data = next(get_entry_forms(self.id, lexicons))
        if data:
            return _make_form(*lemma_data)
        else:
            return lemma_data[0]

    @overload
    def forms(self, *, data: Literal[False] = False) -> list[str]: ...
    @overload
    def forms(self, *, data: Literal[True] = True) -> list[Form]: ...

    # fallback for non-literal bool argument
    @overload
    def forms(self, *, data: bool) -> Union[list[str], list[Form]]: ...

    def forms(self, *, data: bool = False) -> Union[list[str], list[Form]]:
        """Return the list of all encoded forms of the word.

        If the *data* argument is :python:`False` (the default), the
        forms are returned as :class:`str` types. If it is
        :python:`True`, :class:`wn.Form` objects are used instead.

        Example:

            >>> wn.words('wolf')[0].forms()
            ['wolf', 'wolves']
            >>> wn.words('wolf')[0].forms(data=True)
            [Form(value='wolf'), Form(value='wolves')]

        """
        lexicons = self._get_lexicons()
        form_data = list(get_entry_forms(self.id, lexicons))
        if data:
            return [_make_form(*data) for data in form_data]
        else:
            return [form for form, *_ in form_data]

    def senses(self) -> list['Sense']:
        """Return the list of senses of the word.

        Example:

            >>> wn.words('zygoma')[0].senses()
            [Sense('ewn-zygoma-n-05292350-01')]

        """
        lexicons = self._get_lexicons()
        iterable = get_entry_senses(self.id, lexicons)
        return [Sense(*sense_data, _lexconf=self._lexconf) for sense_data in iterable]

    def metadata(self) -> Metadata:
        """Return the word's metadata."""
        return get_metadata(self.id, self._lexicon, 'entries')

    def synsets(self) -> list['Synset']:
        """Return the list of synsets of the word.

        Example:

            >>> wn.words('addendum')[0].synsets()
            [Synset('ewn-06411274-n')]

        """
        return [sense.synset() for sense in self.senses()]

    def derived_words(self) -> list['Word']:
        """Return the list of words linked through derivations on the senses.

        Example:

            >>> wn.words('magical')[0].derived_words()
            [Word('ewn-magic-n'), Word('ewn-magic-n')]

        """
        return [derived_sense.word()
                for sense in self.senses()
                for derived_sense in sense.get_related('derivation')]

    def translate(
        self, lexicon: Optional[str] = None, *, lang: Optional[str] = None,
    ) -> dict['Sense', list['Word']]:
        """Return a mapping of word senses to lists of translated words.

        Arguments:
            lexicon: lexicon specifier of translated words
            lang: BCP-47 language code of translated words

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


class Relation:
    """A class to model relations between senses or synsets."""

    __slots__ = 'name', 'source_id', 'target_id', '_metadata', '_lexicon'
    __module__ = 'wn'

    name: str
    source_id: str
    target_id: str

    def __init__(
        self,
        name: str,
        source_id: str,
        target_id: str,
        lexicon: str,
        *,
        metadata: Optional[Metadata] = None,
    ):
        self.name = name
        self.source_id = source_id
        self.target_id = target_id
        self._lexicon = lexicon
        self._metadata: Metadata = metadata or {}

    def __repr__(self) -> str:
        return (
            self.__class__.__name__
            + f"({self.name!r}, {self.source_id!r}, {self.target_id!r})"
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, Relation):
            return NotImplemented
        return (
            self.name == other.name
            and self.source_id == other.source_id
            and self.target_id == other.target_id
            and self._lexicon == other._lexicon
            and self.subtype == other.subtype
        )

    def __hash__(self) -> int:
        datum = self.name, self.source_id, self.target_id, self._lexicon, self.subtype
        return hash(datum)

    @property
    def subtype(self) -> Optional[str]:
        """
        The value of the ``dc:type`` metadata.

        If ``dc:type`` is not specified in the metadata, ``None`` is
        returned instead.
        """
        return self._metadata.get("type")

    def lexicon(self) -> Lexicon:
        """Return the :class:`Lexicon` where the relation is defined."""
        return _to_lexicon(self._lexicon)

    def metadata(self) -> Metadata:
        """Return the relation's metadata."""
        return self._metadata


T = TypeVar('T', bound='_Relatable')


class _Relatable(_LexiconElement):

    def relations(self: T, *args: str) -> dict[str, list[T]]:
        raise NotImplementedError

    def get_related(self: T, *args: str) -> list[T]:
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

    def relation_paths(
        self: T,
        *args: str,
        end: Optional[T] = None
    ) -> Iterator[list[T]]:
        agenda: list[tuple[list[T], set[T]]] = [
            ([target], {self, target})
            for target in self.get_related(*args)
            if target != self  # avoid self loops?
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


@dataclass(frozen=True)  # slots=True from Python 3.10
class Example:
    """Class for modeling Sense and Synset examples."""
    __module__ = 'wn'

    text: str
    language: Optional[str] = None
    _metadata: Optional[Metadata] = field(default=None, repr=False, compare=False)

    def metadata(self) -> Metadata:
        """Return the example's metadata."""
        return self._metadata if self._metadata is not None else {}


@dataclass(frozen=True)  # slots=True from Python 3.10
class Definition:
    """Class for modeling Synset definitions."""
    __module__ = 'wn'

    text: str
    language: Optional[str] = None
    source_sense_id: Optional[str] = field(default=None, compare=False)
    _metadata: Optional[Metadata] = field(default=None, compare=False, repr=False)

    def metadata(self) -> Metadata:
        """Return the example's metadata."""
        return self._metadata if self._metadata is not None else {}


class Synset(_Relatable):
    """Class for modeling wordnet synsets."""
    __slots__ = 'pos', '_ili'
    __module__ = 'wn'

    _ENTITY_TYPE = _EntityType.SYNSETS

    pos: str

    def __init__(
        self,
        id: str,
        pos: str,
        ili: Optional[str] = None,
        _lexicon: str = '',
        _lexconf: _LexiconConfiguration = _EMPTY_LEXCONFIG,
    ):
        super().__init__(id=id, _lexicon=_lexicon, _lexconf=_lexconf)
        self.pos = pos
        self._ili = ili

    @classmethod
    def empty(
        cls,
        id: str,
        ili: Optional[str] = None,
        _lexicon: str = '',
        _lexconf: _LexiconConfiguration = _EMPTY_LEXCONFIG,
    ):
        return cls(id, pos='', ili=ili, _lexicon=_lexicon, _lexconf=_lexconf)

    def __eq__(self, other) -> bool:
        # include ili in the hash so inferred synsets don't hash the same
        if isinstance(other, Synset):
            return (
                self.id == other.id
                and self._ili == other._ili
                and self._lexicon == other._lexicon
            )
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.id, self._ili, self._lexicon))

    def __repr__(self) -> str:
        return f'Synset({self.id!r})'

    @property
    def ili(self) -> Optional[ILI]:
        if self._ili and (e_ili := next(find_existing_ilis(id=self._ili), None)):
            return _ExistingILI(*e_ili)
        elif p_ili := next(find_proposed_ilis(synset_id=self.id), None):
            return _ProposedILI(*p_ili)
        return None

    @overload
    def definition(self, *, data: Literal[False] = False) -> Optional[str]: ...
    @overload
    def definition(self, *, data: Literal[True] = True) -> Optional[Definition]: ...

    # fallback for non-literal bool argument
    @overload
    def definition(self, *, data: bool) -> Union[str, Definition, None]: ...

    def definition(self, *, data: bool = False) -> Union[str, Definition, None]:
        """Return the first definition found for the synset.

        If the *data* argument is :python:`False` (the default), the
        definition is returned as a :class:`str` type. If it is
        :python:`True`, a :class:`wn.Definition` object is used instead.

        Example:

            >>> wn.synsets('cartwheel', pos='n')[0].definition()
            'a wheel that has wooden spokes and a metal rim'
            >>> wn.synsets('cartwheel', pos='n')[0].definition(data=True)
            [Definition(text='a wheel that has wooden spokes and a metal rim',
              language=None, source_sense_id=None)]

        """
        lexicons = self._get_lexicons()
        if defns := get_definitions(self.id, lexicons):
            text, lang, sense_id, meta = defns[0]
            if data:
                return Definition(
                    text,
                    language=lang,
                    source_sense_id=sense_id,
                    _metadata=meta,
                )
            else:
                return text
        return None

    @overload
    def definitions(self, *, data: Literal[False] = False) -> list[str]: ...
    @overload
    def definitions(self, *, data: Literal[True] = True) -> list[Definition]: ...

    # fallback for non-literal bool argument
    @overload
    def definitions(self, *, data: bool) -> Union[list[str], list[Definition]]: ...

    def definitions(self, *, data: bool = False) -> Union[list[str], list[Definition]]:
        """Return the list of definitions for the synset.

        If the *data* argument is :python:`False` (the default), the
        definitions are returned as :class:`str` objects. If it is
        :python:`True`, :class:`wn.Definition` objects are used instead.

        Example:

            >>> wn.synsets('tea', pos='n')[0].definitions()
            ['a beverage made by steeping tea leaves in water']
            >>> wn.synsets('tea', pos='n')[0].definitions(data=True)
            [Definition(text='a beverage made by steeping tea leaves in water',
              language=None, source_sense_id=None)]

        """
        lexicons = self._get_lexicons()
        defns = get_definitions(self.id, lexicons)
        if data:
            return [
                Definition(text, language=lang, source_sense_id=sid, _metadata=meta)
                for text, lang, sid, meta in defns
            ]
        else:
            return [text for text, *_ in defns]

    @overload
    def examples(self, *, data: Literal[False] = False) -> list[str]: ...
    @overload
    def examples(self, *, data: Literal[True] = True) -> list[Example]: ...

    # fallback for non-literal bool argument
    @overload
    def examples(self, *, data: bool) -> Union[list[str], list[Example]]: ...

    def examples(self, *, data: bool = False) -> Union[list[str], list[Example]]:
        """Return the list of examples for the synset.

        If the *data* argument is :python:`False` (the default), the
        examples are returned as :class:`str` types. If it is
        :python:`True`, :class:`wn.Example` objects are used instead.

        Example:

            >>> wn.synsets('orbital', pos='a')[0].examples()
            ['"orbital revolution"', '"orbital velocity"']

        """
        lexicons = self._get_lexicons()
        exs = get_examples(self.id, 'synsets', lexicons)
        if data:
            return [
                Example(text, language=lang, _metadata=meta) for text, lang, meta in exs
            ]
        else:
            return [text for text, _, _ in exs]

    def senses(self) -> list['Sense']:
        """Return the list of sense members of the synset.

        Example:

            >>> wn.synsets('umbrella', pos='n')[0].senses()
            [Sense('ewn-umbrella-n-04514450-01')]

        """
        lexicons = self._get_lexicons()
        iterable = get_synset_members(self.id, lexicons)
        return [Sense(*sense_data, _lexconf=self._lexconf) for sense_data in iterable]

    def lexicalized(self) -> bool:
        """Return True if the synset is lexicalized."""
        return get_lexicalized(self.id, self._lexicon, 'synsets')

    def lexfile(self) -> Optional[str]:
        """Return the lexicographer file name for this synset, if any."""
        return get_lexfile(self.id, self._lexicon)

    def metadata(self) -> Metadata:
        """Return the synset's metadata."""
        return get_metadata(self.id, self._lexicon, 'synsets')

    def words(self) -> list[Word]:
        """Return the list of words linked by the synset's senses.

        Example:

            >>> wn.synsets('exclusive', pos='n')[0].words()
            [Word('ewn-scoop-n'), Word('ewn-exclusive-n')]

        """
        return [sense.word() for sense in self.senses()]

    @overload
    def lemmas(self, *, data: Literal[False] = False) -> list[str]: ...
    @overload
    def lemmas(self, *, data: Literal[True] = True) -> list[Form]: ...

    # fallback for non-literal bool argument
    @overload
    def lemmas(self, *, data: bool) -> Union[list[str], list[Form]]: ...

    def lemmas(self, *, data: bool = False) -> Union[list[str], list[Form]]:
        """Return the list of lemmas of words for the synset.

        If the *data* argument is :python:`False` (the default), the
        lemmas are returned as :class:`str` types. If it is
        :python:`True`, :class:`wn.Form` objects are used instead.

        Example:

            >>> wn.synsets('exclusive', pos='n')[0].lemmas()
            ['scoop', 'exclusive']
            >>> wn.synsets('exclusive', pos='n')[0].lemmas(data=True)
            [Form(value='scoop'), Form(value='exclusive')]

        """
        # exploded instead of data=data due to mypy issue
        # https://github.com/python/mypy/issues/14764
        if data:
            return [w.lemma(data=True) for w in self.words()]
        else:
            return [w.lemma(data=False) for w in self.words()]

    def relations(self, *args: str) -> dict[str, list['Synset']]:
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
        # inner dict is used as an order-preserving set
        relmap: dict[str, dict[Synset, bool]] = {}
        for relation, synset in self._iter_relations(*args):
            relmap.setdefault(relation.name, {})[synset] = True
        # now convert inner dicts to lists
        return {relname: list(ss_dict) for relname, ss_dict in relmap.items()}

    def get_related(self, *args: str) -> list['Synset']:
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
        return unique_list(synset for _, synset in self._iter_relations(*args))

    def relation_map(self) -> dict[Relation, 'Synset']:
        """Return a dict mapping :class:`Relation` objects to targets."""
        return dict(self._iter_relations())

    def _iter_relations(self, *args: str) -> Iterator[tuple[Relation, 'Synset']]:
        # first get relations from the current lexicon(s)
        yield from self._iter_local_relations(args)
        # then attempt to expand via ILI
        if self._ili is not None and self._lexconf.expands:
            yield from self._iter_expanded_relations(args)

    def _iter_local_relations(
        self,
        args: Sequence[str],
    ) -> Iterator[tuple[Relation, 'Synset']]:
        _lexconf = self._lexconf
        lexicons = self._get_lexicons()
        iterable = get_synset_relations(self.id, self._lexicon, args, lexicons)
        for relname, rellex, metadata, _, ssid, pos, ili, tgtlex in iterable:
            synset_rel = Relation(relname, self.id, ssid, rellex, metadata=metadata)
            synset = Synset(
                ssid,
                pos,
                ili,
                _lexicon=tgtlex,
                _lexconf=_lexconf,
            )
            yield synset_rel, synset

    def _iter_expanded_relations(
        self,
        args: Sequence[str],
    ) -> Iterator[tuple[Relation, 'Synset']]:
        assert self._ili is not None, 'cannot get expanded relations without an ILI'
        _lexconf = self._lexconf
        lexicons = self._get_lexicons()

        iterable = get_expanded_synset_relations(self._ili, args, _lexconf.expands)
        for relname, lexicon, metadata, srcid, ssid, _, ili, *_ in iterable:
            if ili is None:
                continue
            synset_rel = Relation(
                relname, srcid, ssid, lexicon, metadata=metadata
            )
            local_ss_rows = list(get_synsets_for_ilis([ili], lexicons=lexicons))

            if local_ss_rows:
                for row in local_ss_rows:
                    yield synset_rel, Synset(*row, _lexconf=_lexconf)
            else:
                synset = Synset.empty(
                    id=_INFERRED_SYNSET,
                    ili=ili,
                    _lexicon=self._lexicon,
                    _lexconf=_lexconf,
                )
                yield synset_rel, synset

    def hypernym_paths(self, simulate_root: bool = False) -> list[list['Synset']]:
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
    ) -> list['Synset']:
        """Return the shortest path from the synset to the *other* synset."""
        return taxonomy.shortest_path(
            self, other, simulate_root=simulate_root
        )

    def common_hypernyms(
            self, other: 'Synset', simulate_root: bool = False
    ) -> list['Synset']:
        """Return the common hypernyms for the current and *other* synsets."""
        return taxonomy.common_hypernyms(
            self, other, simulate_root=simulate_root
        )

    def lowest_common_hypernyms(
            self, other: 'Synset', simulate_root: bool = False
    ) -> list['Synset']:
        """Return the common hypernyms furthest from the root."""
        return taxonomy.lowest_common_hypernyms(
            self, other, simulate_root=simulate_root
        )

    def holonyms(self) -> list['Synset']:
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

    def meronyms(self) -> list['Synset']:
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

    def hypernyms(self) -> list['Synset']:
        """Return the list of synsets related by any hypernym relation.

        Both the ``hypernym`` and ``instance_hypernym`` relations are
        traversed.

        """
        return self.get_related(
            'hypernym',
            'instance_hypernym'
        )

    def hyponyms(self) -> list['Synset']:
        """Return the list of synsets related by any hyponym relation.

        Both the ``hyponym`` and ``instance_hyponym`` relations are
        traversed.

        """
        return self.get_related(
            'hyponym',
            'instance_hyponym'
        )

    def translate(
        self,
        lexicon: Optional[str] = None,
        *,
        lang: Optional[str] = None
    ) -> list['Synset']:
        """Return a list of translated synsets.

        Arguments:
            lexicon: lexicon specifier of translated synsets
            lang: BCP-47 language code of translated synsets

        Example:

            >>> es = wn.synsets('araña', lang='es')[0]
            >>> en = es.translate(lexicon='ewn')[0]
            >>> en.lemmas()
            ['spider']

        """
        ili = self._ili
        if not ili:
            return []
        return Wordnet(lexicon=lexicon, lang=lang).synsets(ili=ili)


@dataclass(frozen=True)  # slots=True from Python 3.10
class Count:
    """A count of sense occurrences in some corpus."""
    __module__ = 'wn'

    value: int
    _metadata: Optional[Metadata] = field(default=None, repr=False, compare=False)

    def metadata(self) -> Metadata:
        """Return the count's metadata."""
        return self._metadata if self._metadata is not None else {}


class Sense(_Relatable):
    """Class for modeling wordnet senses."""
    __slots__ = '_entry_id', '_synset_id'
    __module__ = 'wn'

    _ENTITY_TYPE = _EntityType.SENSES

    def __init__(
        self,
        id: str,
        entry_id: str,
        synset_id: str,
        _lexicon: str = '',
        _lexconf: _LexiconConfiguration = _EMPTY_LEXCONFIG,
    ):
        super().__init__(id=id, _lexicon=_lexicon, _lexconf=_lexconf)
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
        lexicons = self._get_lexicons()
        word_data = next(find_entries(id=self._entry_id, lexicons=lexicons))
        return Word(*word_data, _lexconf=self._lexconf)

    def synset(self) -> Synset:
        """Return the synset of the sense.

        Example:

            >>> wn.senses('spigot')[0].synset()
            Synset('pwn-03325088-n')

        """
        lexicons = self._get_lexicons()
        synset_data = next(find_synsets(id=self._synset_id, lexicons=lexicons))
        return Synset(*synset_data, _lexconf=self._lexconf)


    @overload
    def examples(self, *, data: Literal[False] = False) -> list[str]: ...
    @overload
    def examples(self, *, data: Literal[True] = True) -> list[Example]: ...

    # fallback for non-literal bool argument
    @overload
    def examples(self, *, data: bool) -> Union[list[str], list[Example]]: ...

    def examples(self, *, data: bool = False) -> Union[list[str], list[Example]]:
        """Return the list of examples for the sense.

        If the *data* argument is :python:`False` (the default), the
        examples are returned as :class:`str` types. If it is
        :python:`True`, :class:`wn.Example` objects are used instead.
        """
        lexicons = self._get_lexicons()
        exs = get_examples(self.id, 'senses', lexicons)
        if data:
            return [
                Example(text, language=lang, _metadata=meta) for text, lang, meta in exs
            ]
        else:
            return [text for text, _, _ in exs]

    def lexicalized(self) -> bool:
        """Return True if the sense is lexicalized."""
        return get_lexicalized(self.id, self._lexicon, 'senses')

    def adjposition(self) -> Optional[str]:
        """Return the adjective position of the sense.

        Values include :python:`"a"` (attributive), :python:`"p"`
        (predicative), and :python:`"ip"` (immediate
        postnominal). Note that this is only relevant for adjectival
        senses. Senses for other parts of speech, or for adjectives
        that are not annotated with this feature, will return
        ``None``.

        """
        return get_adjposition(self.id, self._lexicon)

    def frames(self) -> list[str]:
        """Return the list of subcategorization frames for the sense."""
        lexicons = self._get_lexicons()
        return get_syntactic_behaviours(self.id, lexicons)

    @overload
    def counts(self, *, data: Literal[False] = False) -> list[int]: ...
    @overload
    def counts(self, *, data: Literal[True] = True) -> list[Count]: ...

    # fallback for non-literal bool argument
    @overload
    def counts(self, *, data: bool) -> Union[list[int], list[Count]]: ...

    def counts(self, *, data: bool = False) -> Union[list[int], list[Count]]:
        """Return the corpus counts stored for this sense."""
        lexicons = self._get_lexicons()
        count_data = list(get_sense_counts(self.id, lexicons))
        if data:
            return [Count(value, _metadata=metadata) for value, metadata in count_data]
        else:
            return [value for value, _ in count_data]

    def metadata(self) -> Metadata:
        """Return the sense's metadata."""
        return get_metadata(self.id, self._lexicon, 'senses')

    def relations(self, *args: str) -> dict[str, list['Sense']]:
        """Return a mapping of relation names to lists of senses.

        One or more relation names may be given as positional
        arguments to restrict the relations returned. If no such
        arguments are given, all relations starting from the sense
        are returned.

        See :meth:`get_related` for getting a flat list of related
        senses.

        """
        # inner dict is used as an order-preserving set
        relmap: dict[str, dict[Sense, bool]] = {}
        for relation, sense in self._iter_sense_relations(*args):
            relmap.setdefault(relation.name, {})[sense] = True
        # now convert inner dicts to lists
        return {relname: list(s_dict) for relname, s_dict in relmap.items()}

    def relation_map(self) -> dict[Relation, 'Sense']:
        """Return a dict mapping :class:`Relation` objects to targets."""
        return dict(self._iter_sense_relations())

    def get_related(self, *args: str) -> list['Sense']:
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
        return unique_list(sense for _, sense in self._iter_sense_relations(*args))

    def get_related_synsets(self, *args: str) -> list[Synset]:
        """Return a list of related synsets."""
        return unique_list(
            synset for _, synset in self._iter_sense_synset_relations(*args)
        )

    def _iter_sense_relations(self, *args: str) -> Iterator[tuple[Relation, 'Sense']]:
        iterable = get_sense_relations(self.id, args, self._get_lexicons())
        for relname, lexicon, metadata, sid, eid, ssid, lexid in iterable:
            relation = Relation(relname, self.id, sid, lexicon, metadata=metadata)
            sense = Sense(
                sid, eid, ssid, lexid, _lexconf=self._lexconf
            )
            yield relation, sense

    def _iter_sense_synset_relations(
        self,
        *args: str,
    ) -> Iterator[tuple[Relation, 'Synset']]:
        iterable = get_sense_synset_relations(self.id, args, self._get_lexicons())
        for relname, lexicon, metadata, _, ssid, pos, ili, lexid in iterable:
            relation = Relation(relname, self.id, ssid, lexicon, metadata=metadata)
            synset = Synset(
                ssid, pos, ili, lexid, _lexconf=self._lexconf
            )
            yield relation, synset

    def translate(
        self,
        lexicon: Optional[str] = None,
        *,
        lang: Optional[str] = None
    ) -> list['Sense']:
        """Return a list of translated senses.

        Arguments:
            lexicon: lexicon specifier of translated senses
            lang: BCP-47 language code of translated senses

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
    for later queries. Lexicons can be selected on instantiation with
    the *lexicon* or *lang* parameters. The *lexicon* parameter is a
    string with a space-separated list of :ref:`lexicon specifiers
    <lexicon-specifiers>`. The *lang* argument is a `BCP 47`_ language
    code that selects any lexicon matching the given language code. As
    the *lexicon* argument more precisely selects lexicons, it is the
    recommended method of instantiation. Omitting both *lexicon* and
    *lang* arguments triggers :ref:`default-mode <default-mode>`
    queries.

    Some wordnets were created by translating the words from a larger
    wordnet, namely the Princeton WordNet, and then relying on the
    larger wordnet for structural relations. An *expand* argument is a
    second space-separated list of lexicon specifiers which are used
    for traversing relations, but not as the results of
    queries. Setting *expand* to an empty string (:python:`expand=''`)
    disables expand lexicons. For more information, see
    :ref:`cross-lingual-relation-traversal`.

    The *normalizer* argument takes a callable that normalizes word
    forms in order to expand the search. The default function
    downcases the word and removes diacritics via NFKD_ normalization
    so that, for example, searching for *san josé* in the English
    WordNet will find the entry for *San Jose*. Setting *normalizer*
    to :python:`None` disables normalization and forces exact-match
    searching. For more information, see :ref:`normalization`.

    The *lemmatizer* argument may be :python:`None`, which is the
    default and disables lemmatizer-based query expansion, or a
    callable that takes a word form and optional part of speech and
    returns base forms of the original word. To support lemmatizers
    that use the wordnet for instantiation, such as :mod:`wn.morphy`,
    the lemmatizer may be assigned to the :attr:`lemmatizer` attribute
    after creation. For more information, see :ref:`lemmatization`.

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

    __slots__ = ('_lexconf', '_default_mode',
                 '_normalizer', 'lemmatizer',
                 '_search_all_forms',)
    __module__ = 'wn'

    def __init__(
        self,
        lexicon: Optional[str] = None,
        *,
        lang: Optional[str] = None,
        expand: Optional[str] = None,
        normalizer: Optional[NormalizeFunction] = normalize_form,
        lemmatizer: Optional[LemmatizeFunction] = None,
        search_all_forms: bool = True,
    ):
        if lexicon or lang:
            lexicons = tuple(resolve_lexicon_specifiers(lexicon or '*', lang=lang))
        else:
            lexicons = ()
        if lang and len(lexicons) > 1:
            warnings.warn(
                f'multiple lexicons match {lang=}: {lexicons!r}; '
                'use the lexicon parameter instead to avoid this warning',
                wn.WnWarning,
                stacklevel=2,
            )

        # default mode means any lexicon is searched or expanded upon,
        # but relation traversals only target the source's lexicon
        default_mode = (not lexicon and not lang)
        expand = _resolve_lexicon_dependencies(expand, lexicons, default_mode)
        expands = tuple(resolve_lexicon_specifiers(expand)) if expand else ()

        self._lexconf = _LexiconConfiguration(
            lexicons=lexicons,
            expands=expands,
            default_mode=default_mode,
        )

        self._normalizer = normalizer
        self.lemmatizer = lemmatizer
        self._search_all_forms = search_all_forms

    def lexicons(self) -> list[Lexicon]:
        """Return the list of lexicons covered by this wordnet."""
        return list(map(_to_lexicon, self._lexconf.lexicons))

    def expanded_lexicons(self) -> list[Lexicon]:
        """Return the list of expand lexicons for this wordnet."""
        return list(map(_to_lexicon, self._lexconf.expands))

    def word(self, id: str) -> Word:
        """Return the first word in this wordnet with identifier *id*."""
        iterable = find_entries(id=id, lexicons=self._lexconf.lexicons)
        try:
            return Word(*next(iterable), _lexconf=self._lexconf)
        except StopIteration:
            raise wn.Error(f'no such lexical entry: {id}') from None

    def words(
        self,
        form: Optional[str] = None,
        pos: Optional[str] = None
    ) -> list[Word]:
        """Return the list of matching words in this wordnet.

        Without any arguments, this function returns all words in the
        wordnet's selected lexicons. A *form* argument restricts the
        words to those matching the given word form, and *pos*
        restricts words by their part of speech.

        """
        return _find_helper(self, Word, find_entries, form, pos)

    def synset(self, id: str) -> Synset:
        """Return the first synset in this wordnet with identifier *id*."""
        iterable = find_synsets(id=id, lexicons=self._lexconf.lexicons)
        try:
            return Synset(*next(iterable), _lexconf=self._lexconf)
        except StopIteration:
            raise wn.Error(f'no such synset: {id}') from None

    def synsets(
        self,
        form: Optional[str] = None,
        pos: Optional[str] = None,
        ili: Optional[Union[str, ILI]] = None
    ) -> list[Synset]:
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
        iterable = find_senses(id=id, lexicons=self._lexconf.lexicons)
        try:
            return Sense(*next(iterable), _lexconf=self._lexconf)
        except StopIteration:
            raise wn.Error(f'no such sense: {id}') from None

    def senses(
        self,
        form: Optional[str] = None,
        pos: Optional[str] = None
    ) -> list[Sense]:
        """Return the list of matching senses in this wordnet.

        Without any arguments, this function returns all senses in the
        wordnet's selected lexicons. A *form* argument restricts the
        senses to those whose word matches the given word form, and
        *pos* restricts senses by their word's part of speech.

        """
        return _find_helper(self, Sense, find_senses, form, pos)

    def ili(self, id: str) -> ILI:
        """Return the first ILI in this wordnet with identifer *id*."""
        iterable = find_existing_ilis(id=id, lexicons=self._lexconf.lexicons)
        try:
            return _ExistingILI(*next(iterable))
        except StopIteration:
            raise wn.Error(f'no such ILI: {id}') from None

    def ilis(self, status: Optional[str] = None) -> list[ILI]:
        """Return the list of ILIs in this wordnet.

        If *status* is given, only return ILIs with a matching status.

        """
        iterable = find_ilis(status=status, lexicons=self._lexconf.lexicons)
        return [
            _ProposedILI(id, *data) if id is None else _ExistingILI(id, *data)
            for id, *data in iterable
        ]

    def describe(self) -> str:
        """Return a formatted string describing the lexicons in this wordnet.

        Example:

            >>> oewn = wn.Wordnet('oewn:2021')
            >>> print(oewn.describe())
            Primary lexicons:
              oewn:2021
                Label  : Open English WordNet
                URL    : https://github.com/globalwordnet/english-wordnet
                License: https://creativecommons.org/licenses/by/4.0/
                Words  : 163161 (a: 8386, n: 123456, r: 4481, s: 15231, v: 11607)
                Senses : 211865
                Synsets: 120039 (a: 7494, n: 84349, r: 3623, s: 10727, v: 13846)
                ILIs   : 120039

        """
        substrings = ['Primary lexicons:']
        for lex in self.lexicons():
            substrings.append(textwrap.indent(lex.describe(), '  '))
        if self._lexconf.expands:
            substrings.append('Expand lexicons:')
            for lex in self.expanded_lexicons():
                substrings.append(textwrap.indent(lex.describe(full=False), '  '))
        return '\n'.join(substrings)


def _resolve_lexicon_dependencies(
    expand: Optional[str],
    lexicons: Sequence[str],
    default_mode: bool,
) -> str:
    if expand is not None:
        return expand.strip()
    if default_mode:
        return "*"
    # find dependencies specified by the lexicons
    deps = [
        (depspec, added)
        for lexspec in lexicons
        for depspec, _, added in get_lexicon_dependencies(lexspec)
    ]
    missing = ' '.join(spec for spec, added in deps if not added)
    if missing:
        warnings.warn(
            f'lexicon dependencies not available: {missing}',
            wn.WnWarning,
            stacklevel=3,
        )
    return ' '.join(spec for spec, added in deps if added)


def _to_lexicon(specifier: str) -> Lexicon:
    data = get_lexicon(specifier)
    id, label, language, email, license, version, url, citation, logo, meta = data
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
        _metadata=meta,
    )


def _find_helper(
    w: Wordnet,
    cls: type[C],
    query_func: Callable,
    form: Optional[str],
    pos: Optional[str],
    ili: Optional[Union[str, ILI]] = None
) -> list[C]:
    """Return the list of matching wordnet entities.

    If the wordnet has a normalizer and the search includes a word
    form, the original word form is searched against both the
    original and normalized columns in the database. Then, if no
    results are found, the search is repeated with the normalized
    form. If the wordnet does not have a normalizer, only exact
    string matches are used.

    """
    kwargs: dict = {
        'lexicons': w._lexconf.lexicons,
        'search_all_forms': w._search_all_forms,
    }
    if isinstance(ili, str):
        kwargs['ili'] = ili
    elif isinstance(ili, ILI):
        kwargs['ili'] = ili.id
    elif ili is not None:
        raise TypeError(
            "ili argument must be a string, an ILI, or None, "
            f"not {type(ili).__name__!r}"
        )

    # easy case is when there is no form
    if form is None:
        return [cls(*data, _lexconf=w._lexconf)  # type: ignore
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

    # we want unique results here, but a set can make the order
    # erratic, so filter manually later
    results = [
        cls(*data, _lexconf=w._lexconf)  # type: ignore
        for _pos, _forms in forms.items()
        for data in query_func(forms=_forms, pos=_pos, **kwargs)
    ]
    if not results and normalize:
        results = [
            cls(*data, _lexconf=w._lexconf)  # type: ignore
            for _pos, _forms in forms.items()
            for data in query_func(
                forms=[normalize(f) for f in _forms], pos=_pos, **kwargs
            )
        ]
    unique_results: list[C] = []
    seen: set[C] = set()
    for result in results:
        if result not in seen:
            unique_results.append(result)
            seen.add(result)
    return unique_results
