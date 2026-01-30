from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, TypeVar, overload

from wn import taxonomy
from wn._lexicon import (
    LexiconConfiguration,
    LexiconElement,
    LexiconElementWithMetadata,
)
from wn._queries import Pronunciation as PronunciationTuple
from wn._queries import Tag as TagTuple
from wn._queries import (
    find_entries,
    find_synsets,
    get_adjposition,
    get_definitions,
    get_entry_forms,
    get_entry_senses,
    get_examples,
    get_expanded_synset_relations,
    get_lexfile,
    get_lexicalized,
    get_lexicon_extension_bases,
    get_lexicon_extensions,
    get_metadata,
    get_sense_counts,
    get_sense_relations,
    get_sense_synset_relations,
    get_synset_members,
    get_synset_relations,
    get_synsets_for_ilis,
    get_syntactic_behaviours,
    resolve_lexicon_specifiers,
)
from wn._util import unique_list

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from wn._metadata import Metadata


_INFERRED_SYNSET = "*INFERRED*"


class _EntityType(str, enum.Enum):
    """Identifies the database table of an entity."""

    LEXICONS = "lexicons"
    ENTRIES = "entries"
    SENSES = "senses"
    SYNSETS = "synsets"
    SENSE_RELATIONS = "sense_relations"
    SENSE_SYNSET_RELATIONS = "sense_synset_relations"
    SYNSET_RELATIONS = "synset_relations"
    UNSET = ""


_EMPTY_LEXCONFIG = LexiconConfiguration(
    lexicons=(),
    expands=(),
    default_mode=False,
)


class _LexiconDataElement(LexiconElementWithMetadata):
    """Base class for Words, Senses, and Synsets.

    These elements always have a required ID and are used as the
    starting point of secondary queries, so they also store the
    configuration of lexicons used in the original query.
    """

    __slots__ = "_lexconf", "id"

    id: str
    _lexconf: LexiconConfiguration

    def __init__(
        self,
        id: str,
        _lexicon: str = "",
        _lexconf: LexiconConfiguration = _EMPTY_LEXCONFIG,
    ) -> None:
        self.id = id
        self._lexicon = _lexicon
        self._lexconf = _lexconf

    def __eq__(self, other) -> bool:
        if isinstance(other, type(self)) or isinstance(self, type(other)):
            return self.id == other.id and self._lexicon == other._lexicon
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.id, self._lexicon))

    def _get_lexicons(self) -> tuple[str, ...]:
        if self._lexconf.default_mode:
            return (
                self._lexicon,
                *get_lexicon_extension_bases(self._lexicon),
                *get_lexicon_extensions(self._lexicon),
            )
        else:
            return self._lexconf.lexicons


@dataclass(frozen=True, slots=True)
class Pronunciation(LexiconElement):
    """A class for word form pronunciations."""

    __module__ = "wn"

    value: str
    variety: str | None = None
    notation: str | None = None
    phonemic: bool = True
    audio: str | None = None
    _lexicon: str = field(default="", repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class Tag(LexiconElement):
    """A general-purpose tag class for word forms."""

    __module__ = "wn"

    tag: str
    category: str
    _lexicon: str = field(default="", repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class Form(LexiconElement):
    """A word-form."""

    __module__ = "wn"

    value: str
    id: str | None = field(default=None, repr=False, compare=False)
    script: str | None = field(default=None, repr=False)
    _lexicon: str = field(default="", repr=False, compare=False)
    _pronunciations: tuple[Pronunciation, ...] = field(
        default_factory=tuple, repr=False, compare=False
    )
    _tags: tuple[Tag, ...] = field(default_factory=tuple, repr=False, compare=False)

    def pronunciations(self) -> list[Pronunciation]:
        return list(self._pronunciations)

    def tags(self) -> list[Tag]:
        return list(self._tags)


def _make_form(
    form: str,
    id: str | None,
    script: str | None,
    lexicon: str,
    prons: list[PronunciationTuple],
    tags: list[TagTuple],
) -> Form:
    return Form(
        form,
        id=id,
        script=script,
        _lexicon=lexicon,
        _pronunciations=tuple(Pronunciation(*data) for data in prons),
        _tags=tuple(Tag(*data) for data in tags),
    )


class Word(_LexiconDataElement):
    """A class for words (also called lexical entries) in a wordnet."""

    __slots__ = ("pos",)
    __module__ = "wn"

    _ENTITY_TYPE = _EntityType.ENTRIES

    pos: str

    def __init__(
        self,
        id: str,
        pos: str,
        _lexicon: str = "",
        _lexconf: LexiconConfiguration = _EMPTY_LEXCONFIG,
    ):
        super().__init__(id=id, _lexicon=_lexicon, _lexconf=_lexconf)
        self.pos = pos

    def __repr__(self) -> str:
        return f"Word({self.id!r})"

    @overload
    def lemma(self, *, data: Literal[False] = False) -> str: ...
    @overload
    def lemma(self, *, data: Literal[True] = True) -> Form: ...

    # fallback for non-literal bool argument
    @overload
    def lemma(self, *, data: bool) -> str | Form: ...

    def lemma(self, *, data: bool = False) -> str | Form:
        """Return the canonical form of the word.

        If the *data* argument is :python:`False` (the default), the
        lemma is returned as a :class:`str` type. If it is
        :python:`True`, a :class:`wn.Form` object is used instead.

        Example:

            >>> wn.words("wolves")[0].lemma()
            'wolf'
            >>> wn.words("wolves")[0].lemma(data=True)
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
    def forms(self, *, data: bool) -> list[str] | list[Form]: ...

    def forms(self, *, data: bool = False) -> list[str] | list[Form]:
        """Return the list of all encoded forms of the word.

        If the *data* argument is :python:`False` (the default), the
        forms are returned as :class:`str` types. If it is
        :python:`True`, :class:`wn.Form` objects are used instead.

        Example:

            >>> wn.words("wolf")[0].forms()
            ['wolf', 'wolves']
            >>> wn.words("wolf")[0].forms(data=True)
            [Form(value='wolf'), Form(value='wolves')]

        """
        lexicons = self._get_lexicons()
        form_data = list(get_entry_forms(self.id, lexicons))
        if data:
            return [_make_form(*data) for data in form_data]
        else:
            return [form for form, *_ in form_data]

    def senses(self) -> list[Sense]:
        """Return the list of senses of the word.

        Example:

            >>> wn.words("zygoma")[0].senses()
            [Sense('ewn-zygoma-n-05292350-01')]

        """
        lexicons = self._get_lexicons()
        iterable = get_entry_senses(self.id, lexicons)
        return [Sense(*sense_data, _lexconf=self._lexconf) for sense_data in iterable]

    def metadata(self) -> Metadata:
        """Return the word's metadata."""
        return get_metadata(self.id, self._lexicon, "entries")

    def synsets(self) -> list[Synset]:
        """Return the list of synsets of the word.

        Example:

            >>> wn.words("addendum")[0].synsets()
            [Synset('ewn-06411274-n')]

        """
        return [sense.synset() for sense in self.senses()]

    def derived_words(self) -> list[Word]:
        """Return the list of words linked through derivations on the senses.

        Example:

            >>> wn.words("magical")[0].derived_words()
            [Word('ewn-magic-n'), Word('ewn-magic-n')]

        """
        return [
            derived_sense.word()
            for sense in self.senses()
            for derived_sense in sense.get_related("derivation")
        ]

    def translate(
        self,
        lexicon: str | None = None,
        *,
        lang: str | None = None,
    ) -> dict[Sense, list[Word]]:
        """Return a mapping of word senses to lists of translated words.

        Arguments:
            lexicon: lexicon specifier of translated words
            lang: BCP-47 language code of translated words

        Example:

            >>> w = wn.words("water bottle", pos="n")[0]
            >>> for sense, words in w.translate(lang="ja").items():
            ...     print(sense, [jw.lemma() for jw in words])
            Sense('ewn-water_bottle-n-04564934-01') ['水筒']

        """
        result = {}
        for sense in self.senses():
            result[sense] = [
                t_sense.word()
                for t_sense in sense.translate(lang=lang, lexicon=lexicon)
            ]
        return result


class Relation(LexiconElementWithMetadata):
    """A class to model relations between senses or synsets."""

    __slots__ = "_lexicon", "_metadata", "name", "source_id", "target_id"
    __module__ = "wn"

    name: str
    source_id: str
    target_id: str
    _metadata: Metadata | None

    def __init__(
        self,
        name: str,
        source_id: str,
        target_id: str,
        lexicon: str,
        *,
        metadata: Metadata | None = None,
    ):
        self.name = name
        self.source_id = source_id
        self.target_id = target_id
        self._lexicon = lexicon
        self._metadata = metadata

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
    def subtype(self) -> str | None:
        """
        The value of the ``dc:type`` metadata.

        If ``dc:type`` is not specified in the metadata, ``None`` is
        returned instead.
        """
        return self.metadata().get("type")


T = TypeVar("T", bound="_Relatable")


class _Relatable(_LexiconDataElement):
    @overload
    def relations(
        self: T, *args: str, data: Literal[False] = False
    ) -> dict[str, list[T]]: ...
    @overload
    def relations(
        self: T, *args: str, data: Literal[True] = True
    ) -> dict[Relation, T]: ...

    # fallback for non-literal bool argument
    @overload
    def relations(
        self: T, *args: str, data: bool = False
    ) -> dict[str, list[T]] | dict[Relation, T]: ...

    def relations(
        self: T, *args: str, data: bool = False
    ) -> dict[str, list[T]] | dict[Relation, T]:
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

    def relation_paths(self: T, *args: str, end: T | None = None) -> Iterator[list[T]]:
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
                related = [
                    target
                    for target in path[-1].get_related(*args)
                    if target not in visited
                ]
                if related:
                    for synset in reversed(related):
                        new_path = [*path, synset]
                        new_visited = visited | {synset}
                        agenda.append((new_path, new_visited))
                elif end is None:
                    yield path


@dataclass(frozen=True, slots=True)
class Example(LexiconElementWithMetadata):
    """Class for modeling Sense and Synset examples."""

    __module__ = "wn"

    text: str
    language: str | None = None
    _lexicon: str = ""
    _metadata: Metadata | None = field(default=None, repr=False, compare=False)

    def metadata(self) -> Metadata:
        """Return the example's metadata."""
        return self._metadata if self._metadata is not None else {}


@dataclass(frozen=True, slots=True)
class Definition(LexiconElementWithMetadata):
    """Class for modeling Synset definitions."""

    __module__ = "wn"

    text: str
    language: str | None = None
    source_sense_id: str | None = field(default=None, compare=False)
    _lexicon: str = ""
    _metadata: Metadata | None = field(default=None, compare=False, repr=False)

    def metadata(self) -> Metadata:
        """Return the example's metadata."""
        return self._metadata if self._metadata is not None else {}


class Synset(_Relatable):
    """Class for modeling wordnet synsets."""

    __slots__ = "_ili", "pos"
    __module__ = "wn"

    _ENTITY_TYPE = _EntityType.SYNSETS

    pos: str
    _ili: str | None

    def __init__(
        self,
        id: str,
        pos: str,
        ili: str | None = None,
        _lexicon: str = "",
        _lexconf: LexiconConfiguration = _EMPTY_LEXCONFIG,
    ):
        super().__init__(id=id, _lexicon=_lexicon, _lexconf=_lexconf)
        self.pos = pos
        self._ili = ili

    @classmethod
    def empty(
        cls,
        id: str,
        ili: str | None = None,
        _lexicon: str = "",
        _lexconf: LexiconConfiguration = _EMPTY_LEXCONFIG,
    ):
        return cls(id, pos="", ili=ili, _lexicon=_lexicon, _lexconf=_lexconf)

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
        return f"Synset({self.id!r})"

    @property
    def ili(self) -> str | None:
        return self._ili

    @overload
    def definition(self, *, data: Literal[False] = False) -> str | None: ...
    @overload
    def definition(self, *, data: Literal[True] = True) -> Definition | None: ...

    # fallback for non-literal bool argument
    @overload
    def definition(self, *, data: bool) -> str | Definition | None: ...

    def definition(self, *, data: bool = False) -> str | Definition | None:
        """Return the first definition found for the synset.

        If the *data* argument is :python:`False` (the default), the
        definition is returned as a :class:`str` type. If it is
        :python:`True`, a :class:`wn.Definition` object is used instead.

        Example:

            >>> wn.synsets("cartwheel", pos="n")[0].definition()
            'a wheel that has wooden spokes and a metal rim'
            >>> wn.synsets("cartwheel", pos="n")[0].definition(data=True)
            [Definition(text='a wheel that has wooden spokes and a metal rim',
              language=None, source_sense_id=None)]

        """
        lexicons = self._get_lexicons()
        if defns := get_definitions(self.id, lexicons):
            text, lang, sense_id, lex, meta = defns[0]
            if data:
                return Definition(
                    text,
                    language=lang,
                    source_sense_id=sense_id,
                    _lexicon=lex,
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
    def definitions(self, *, data: bool) -> list[str] | list[Definition]: ...

    def definitions(self, *, data: bool = False) -> list[str] | list[Definition]:
        """Return the list of definitions for the synset.

        If the *data* argument is :python:`False` (the default), the
        definitions are returned as :class:`str` objects. If it is
        :python:`True`, :class:`wn.Definition` objects are used instead.

        Example:

            >>> wn.synsets("tea", pos="n")[0].definitions()
            ['a beverage made by steeping tea leaves in water']
            >>> wn.synsets("tea", pos="n")[0].definitions(data=True)
            [Definition(text='a beverage made by steeping tea leaves in water',
              language=None, source_sense_id=None)]

        """
        lexicons = self._get_lexicons()
        defns = get_definitions(self.id, lexicons)
        if data:
            return [
                Definition(
                    text,
                    language=lang,
                    source_sense_id=sid,
                    _lexicon=lex,
                    _metadata=meta,
                )
                for text, lang, sid, lex, meta in defns
            ]
        else:
            return [text for text, *_ in defns]

    @overload
    def examples(self, *, data: Literal[False] = False) -> list[str]: ...
    @overload
    def examples(self, *, data: Literal[True] = True) -> list[Example]: ...

    # fallback for non-literal bool argument
    @overload
    def examples(self, *, data: bool) -> list[str] | list[Example]: ...

    def examples(self, *, data: bool = False) -> list[str] | list[Example]:
        """Return the list of examples for the synset.

        If the *data* argument is :python:`False` (the default), the
        examples are returned as :class:`str` types. If it is
        :python:`True`, :class:`wn.Example` objects are used instead.

        Example:

            >>> wn.synsets("orbital", pos="a")[0].examples()
            ['"orbital revolution"', '"orbital velocity"']

        """
        lexicons = self._get_lexicons()
        exs = get_examples(self.id, "synsets", lexicons)
        if data:
            return [
                Example(text, language=lang, _lexicon=lex, _metadata=meta)
                for text, lang, lex, meta in exs
            ]
        else:
            return [text for text, *_ in exs]

    def senses(self) -> list[Sense]:
        """Return the list of sense members of the synset.

        Example:

            >>> wn.synsets("umbrella", pos="n")[0].senses()
            [Sense('ewn-umbrella-n-04514450-01')]

        """
        lexicons = self._get_lexicons()
        iterable = get_synset_members(self.id, lexicons)
        return [Sense(*sense_data, _lexconf=self._lexconf) for sense_data in iterable]

    def lexicalized(self) -> bool:
        """Return True if the synset is lexicalized."""
        return get_lexicalized(self.id, self._lexicon, "synsets")

    def lexfile(self) -> str | None:
        """Return the lexicographer file name for this synset, if any."""
        return get_lexfile(self.id, self._lexicon)

    def metadata(self) -> Metadata:
        """Return the synset's metadata."""
        return get_metadata(self.id, self._lexicon, "synsets")

    def words(self) -> list[Word]:
        """Return the list of words linked by the synset's senses.

        Example:

            >>> wn.synsets("exclusive", pos="n")[0].words()
            [Word('ewn-scoop-n'), Word('ewn-exclusive-n')]

        """
        return [sense.word() for sense in self.senses()]

    @overload
    def lemmas(self, *, data: Literal[False] = False) -> list[str]: ...
    @overload
    def lemmas(self, *, data: Literal[True] = True) -> list[Form]: ...

    # fallback for non-literal bool argument
    @overload
    def lemmas(self, *, data: bool) -> list[str] | list[Form]: ...

    def lemmas(self, *, data: bool = False) -> list[str] | list[Form]:
        """Return the list of lemmas of words for the synset.

        If the *data* argument is :python:`False` (the default), the
        lemmas are returned as :class:`str` types. If it is
        :python:`True`, :class:`wn.Form` objects are used instead.

        Example:

            >>> wn.synsets("exclusive", pos="n")[0].lemmas()
            ['scoop', 'exclusive']
            >>> wn.synsets("exclusive", pos="n")[0].lemmas(data=True)
            [Form(value='scoop'), Form(value='exclusive')]

        """
        # exploded instead of data=data due to mypy issue
        # https://github.com/python/mypy/issues/14764
        if data:
            return [w.lemma(data=True) for w in self.words()]
        else:
            return [w.lemma(data=False) for w in self.words()]

    @overload
    def relations(
        self, *args: str, data: Literal[False] = False
    ) -> dict[str, list[Synset]]: ...
    @overload
    def relations(
        self, *args: str, data: Literal[True] = True
    ) -> dict[Relation, Synset]: ...

    # fallback for non-literal bool argument
    @overload
    def relations(
        self, *args: str, data: bool = False
    ) -> dict[str, list[Synset]] | dict[Relation, Synset]: ...

    def relations(
        self, *args: str, data: bool = False
    ) -> dict[str, list[Synset]] | dict[Relation, Synset]:
        """Return a mapping of synset relations.

        One or more relation names may be given as positional
        arguments to restrict the relations returned. If no such
        arguments are given, all relations starting from the synset
        are returned.

        If the *data* argument is :python:`False` (default), the
        returned object maps from the relation name (a :class:`str`)
        to a list of :class:`Synset` objects. If *data* is
        :python:`True`, it instead maps from a :class:`Relation` to
        a single :class:`Synset`.

        See :meth:`get_related` for getting a flat list of related
        synsets.

        Example:

            >>> button_rels = wn.synsets("button")[0].relations()
            >>> for relname, sslist in button_rels.items():
            ...     print(relname, [ss.lemmas() for ss in sslist])
            hypernym [['fixing', 'holdfast', 'fastener', 'fastening']]
            hyponym [['coat button'], ['shirt button']]

        """
        if data:
            return dict(self._iter_relations())
        else:
            # inner dict is used as an order-preserving set
            relmap: dict[str, dict[Synset, bool]] = {}
            for relation, synset in self._iter_relations(*args):
                relmap.setdefault(relation.name, {})[synset] = True
                # now convert inner dicts to lists
            return {relname: list(ss_dict) for relname, ss_dict in relmap.items()}

    def get_related(self, *args: str) -> list[Synset]:
        """Return the list of related synsets.

        One or more relation names may be given as positional
        arguments to restrict the relations returned. If no such
        arguments are given, all relations starting from the synset
        are returned.

        This method does not preserve the relation names that lead to
        the related synsets. For a mapping of relation names to
        related synsets, see :meth:`relations`.

        Example:

            >>> fulcrum = wn.synsets("fulcrum")[0]
            >>> [ss.lemmas() for ss in fulcrum.get_related()]
            [['pin', 'pivot'], ['lever']]
        """
        return unique_list(synset for _, synset in self._iter_relations(*args))

    def _iter_relations(self, *args: str) -> Iterator[tuple[Relation, Synset]]:
        # first get relations from the current lexicon(s)
        yield from self._iter_local_relations(args)
        # then attempt to expand via ILI
        if self._ili is not None and self._lexconf.expands:
            yield from self._iter_expanded_relations(args)

    def _iter_local_relations(
        self,
        args: Sequence[str],
    ) -> Iterator[tuple[Relation, Synset]]:
        _lexconf = self._lexconf
        lexicons = self._get_lexicons()
        iterable = get_synset_relations(
            self.id, self._lexicon, args, lexicons, lexicons
        )
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
    ) -> Iterator[tuple[Relation, Synset]]:
        assert self._ili is not None, "cannot get expanded relations without an ILI"
        _lexconf = self._lexconf
        lexicons = self._get_lexicons()

        iterable = get_expanded_synset_relations(self._ili, args, _lexconf.expands)
        for relname, lexicon, metadata, srcid, ssid, _, ili, *_ in iterable:
            if ili is None:
                continue
            synset_rel = Relation(relname, srcid, ssid, lexicon, metadata=metadata)
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

    def hypernym_paths(self, simulate_root: bool = False) -> list[list[Synset]]:
        """Return the list of hypernym paths to a root synset."""
        return taxonomy.hypernym_paths(self, simulate_root=simulate_root)

    def min_depth(self, simulate_root: bool = False) -> int:
        """Return the minimum taxonomy depth of the synset."""
        return taxonomy.min_depth(self, simulate_root=simulate_root)

    def max_depth(self, simulate_root: bool = False) -> int:
        """Return the maximum taxonomy depth of the synset."""
        return taxonomy.max_depth(self, simulate_root=simulate_root)

    def shortest_path(self, other: Synset, simulate_root: bool = False) -> list[Synset]:
        """Return the shortest path from the synset to the *other* synset."""
        return taxonomy.shortest_path(self, other, simulate_root=simulate_root)

    def common_hypernyms(
        self, other: Synset, simulate_root: bool = False
    ) -> list[Synset]:
        """Return the common hypernyms for the current and *other* synsets."""
        return taxonomy.common_hypernyms(self, other, simulate_root=simulate_root)

    def lowest_common_hypernyms(
        self, other: Synset, simulate_root: bool = False
    ) -> list[Synset]:
        """Return the common hypernyms furthest from the root."""
        return taxonomy.lowest_common_hypernyms(
            self, other, simulate_root=simulate_root
        )

    def holonyms(self) -> list[Synset]:
        """Return the list of synsets related by any holonym relation.

        Any of the following relations are traversed: ``holonym``,
        ``holo_location``, ``holo_member``, ``holo_part``,
        ``holo_portion``, ``holo_substance``.

        """
        return self.get_related(
            "holonym",
            "holo_location",
            "holo_member",
            "holo_part",
            "holo_portion",
            "holo_substance",
        )

    def meronyms(self) -> list[Synset]:
        """Return the list of synsets related by any meronym relation.

        Any of the following relations are traversed: ``meronym``,
        ``mero_location``, ``mero_member``, ``mero_part``,
        ``mero_portion``, ``mero_substance``.

        """
        return self.get_related(
            "meronym",
            "mero_location",
            "mero_member",
            "mero_part",
            "mero_portion",
            "mero_substance",
        )

    def hypernyms(self) -> list[Synset]:
        """Return the list of synsets related by any hypernym relation.

        Both the ``hypernym`` and ``instance_hypernym`` relations are
        traversed.

        """
        return self.get_related("hypernym", "instance_hypernym")

    def hyponyms(self) -> list[Synset]:
        """Return the list of synsets related by any hyponym relation.

        Both the ``hyponym`` and ``instance_hyponym`` relations are
        traversed.

        """
        return self.get_related("hyponym", "instance_hyponym")

    def translate(
        self, lexicon: str | None = None, *, lang: str | None = None
    ) -> list[Synset]:
        """Return a list of translated synsets.

        Arguments:
            lexicon: lexicon specifier of translated synsets
            lang: BCP-47 language code of translated synsets

        Example:

            >>> es = wn.synsets("araña", lang="es")[0]
            >>> en = es.translate(lexicon="ewn")[0]
            >>> en.lemmas()
            ['spider']

        """
        ili = self._ili
        if not ili:
            return []
        lexicons = resolve_lexicon_specifiers(lexicon=(lexicon or "*"), lang=lang)
        return [
            Synset(*data, _lexconf=self._lexconf)
            for data in get_synsets_for_ilis((ili,), lexicons)
        ]


@dataclass(frozen=True, slots=True)
class Count(LexiconElementWithMetadata):
    """A count of sense occurrences in some corpus."""

    __module__ = "wn"

    value: int
    _lexicon: str = ""
    _metadata: Metadata | None = field(default=None, repr=False, compare=False)


class Sense(_Relatable):
    """Class for modeling wordnet senses."""

    __slots__ = "_entry_id", "_synset_id"
    __module__ = "wn"

    _ENTITY_TYPE = _EntityType.SENSES

    def __init__(
        self,
        id: str,
        entry_id: str,
        synset_id: str,
        _lexicon: str = "",
        _lexconf: LexiconConfiguration = _EMPTY_LEXCONFIG,
    ):
        super().__init__(id=id, _lexicon=_lexicon, _lexconf=_lexconf)
        self._entry_id = entry_id
        self._synset_id = synset_id

    def __repr__(self) -> str:
        return f"Sense({self.id!r})"

    def word(self) -> Word:
        """Return the word of the sense.

        Example:

            >>> wn.senses("spigot")[0].word()
            Word('pwn-spigot-n')

        """
        lexicons = self._get_lexicons()
        id, pos, lex = next(find_entries(id=self._entry_id, lexicons=lexicons))
        return Word(id, pos, _lexicon=lex, _lexconf=self._lexconf)

    def synset(self) -> Synset:
        """Return the synset of the sense.

        Example:

            >>> wn.senses("spigot")[0].synset()
            Synset('pwn-03325088-n')

        """
        lexicons = self._get_lexicons()
        id, pos, ili, lex = next(find_synsets(id=self._synset_id, lexicons=lexicons))
        return Synset(id, pos, ili=ili, _lexicon=lex, _lexconf=self._lexconf)

    @overload
    def examples(self, *, data: Literal[False] = False) -> list[str]: ...
    @overload
    def examples(self, *, data: Literal[True] = True) -> list[Example]: ...

    # fallback for non-literal bool argument
    @overload
    def examples(self, *, data: bool) -> list[str] | list[Example]: ...

    def examples(self, *, data: bool = False) -> list[str] | list[Example]:
        """Return the list of examples for the sense.

        If the *data* argument is :python:`False` (the default), the
        examples are returned as :class:`str` types. If it is
        :python:`True`, :class:`wn.Example` objects are used instead.
        """
        lexicons = self._get_lexicons()
        exs = get_examples(self.id, "senses", lexicons)
        if data:
            return [
                Example(text, language=lang, _lexicon=lex, _metadata=meta)
                for text, lang, lex, meta in exs
            ]
        else:
            return [text for text, *_ in exs]

    def lexicalized(self) -> bool:
        """Return True if the sense is lexicalized."""
        return get_lexicalized(self.id, self._lexicon, "senses")

    def adjposition(self) -> str | None:
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
    def counts(self, *, data: bool) -> list[int] | list[Count]: ...

    def counts(self, *, data: bool = False) -> list[int] | list[Count]:
        """Return the corpus counts stored for this sense."""
        lexicons = self._get_lexicons()
        count_data = list(get_sense_counts(self.id, lexicons))
        if data:
            return [
                Count(value, _lexicon=lex, _metadata=metadata)
                for value, lex, metadata in count_data
            ]
        else:
            return [value for value, *_ in count_data]

    def metadata(self) -> Metadata:
        """Return the sense's metadata."""
        return get_metadata(self.id, self._lexicon, "senses")

    @overload
    def relations(
        self, *args: str, data: Literal[False] = False
    ) -> dict[str, list[Sense]]: ...
    @overload
    def relations(
        self, *args: str, data: Literal[True] = True
    ) -> dict[Relation, Sense]: ...

    # fallback for non-literal bool argument
    @overload
    def relations(
        self, *args: str, data: bool = False
    ) -> dict[str, list[Sense]] | dict[Relation, Sense]: ...

    def relations(
        self, *args: str, data: bool = False
    ) -> dict[str, list[Sense]] | dict[Relation, Sense]:
        """Return a mapping of relation names to lists of senses.

        One or more relation names may be given as positional
        arguments to restrict the relations returned. If no such
        arguments are given, all relations starting from the sense
        are returned.

        If the *data* argument is :python:`False` (default), the
        returned object maps from the relation name (a :class:`str`)
        to a list of :class:`Sense` objects. If *data* is
        :python:`True`, it instead maps from a :class:`Relation` to
        a single :class:`Sense`.

        See :meth:`get_related` for getting a flat list of related
        senses.

        """
        if data:
            return dict(self._iter_sense_relations())
        else:
            # inner dict is used as an order-preserving set
            relmap: dict[str, dict[Sense, bool]] = {}
            for relation, sense in self._iter_sense_relations(*args):
                relmap.setdefault(relation.name, {})[sense] = True
            # now convert inner dicts to lists
            return {relname: list(s_dict) for relname, s_dict in relmap.items()}

    @overload
    def synset_relations(
        self, *args: str, data: Literal[False] = False
    ) -> dict[str, list[Synset]]: ...
    @overload
    def synset_relations(
        self, *args: str, data: Literal[True] = True
    ) -> dict[Relation, Synset]: ...

    # fallback for non-literal bool argument
    @overload
    def synset_relations(
        self, *args: str, data: bool = False
    ) -> dict[str, list[Synset]] | dict[Relation, Synset]: ...

    def synset_relations(
        self, *args: str, data: bool = False
    ) -> dict[str, list[Synset]] | dict[Relation, Synset]:
        """Return a mapping of relation names to lists of synsets.

        One or more relation names may be given as positional
        arguments to restrict the relations returned. If no such
        arguments are given, all relations starting from the sense
        are returned.

        If the *data* argument is :python:`False` (default), the
        returned object maps from the relation name (a :class:`str`)
        to a list of :class:`Synset` objects. If *data* is
        :python:`True`, it instead maps from a :class:`Relation` to
        a single :class:`Synset`.

        See :meth:`get_related_synsets` for getting a flat list of
        related synsets.

        """
        if data:
            return dict(self._iter_sense_synset_relations())
        else:
            # inner dict is used as an order-preserving set
            relmap: dict[str, dict[Synset, bool]] = {}
            for relation, synset in self._iter_sense_synset_relations(*args):
                relmap.setdefault(relation.name, {})[synset] = True
            # now convert inner dicts to lists
            return {relname: list(ss_dict) for relname, ss_dict in relmap.items()}

    def get_related(self, *args: str) -> list[Sense]:
        """Return a list of related senses.

        One or more relation types should be passed as arguments which
        determine the kind of relations returned.

        Example:

            >>> physics = wn.senses("physics", lexicon="ewn")[0]
            >>> for sense in physics.get_related("has_domain_topic"):
            ...     print(sense.word().lemma())
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

    def _iter_sense_relations(self, *args: str) -> Iterator[tuple[Relation, Sense]]:
        lexicons = self._get_lexicons()
        iterable = get_sense_relations(self.id, args, lexicons, lexicons)
        for relname, lexicon, metadata, sid, eid, ssid, lexid in iterable:
            relation = Relation(relname, self.id, sid, lexicon, metadata=metadata)
            sense = Sense(sid, eid, ssid, lexid, _lexconf=self._lexconf)
            yield relation, sense

    def _iter_sense_synset_relations(
        self,
        *args: str,
    ) -> Iterator[tuple[Relation, Synset]]:
        lexicons = self._get_lexicons()
        iterable = get_sense_synset_relations(self.id, args, lexicons, lexicons)
        for relname, lexicon, metadata, _, ssid, pos, ili, lexid in iterable:
            relation = Relation(relname, self.id, ssid, lexicon, metadata=metadata)
            synset = Synset(ssid, pos, ili, lexid, _lexconf=self._lexconf)
            yield relation, synset

    def translate(
        self, lexicon: str | None = None, *, lang: str | None = None
    ) -> list[Sense]:
        """Return a list of translated senses.

        Arguments:
            lexicon: lexicon specifier of translated senses
            lang: BCP-47 language code of translated senses

        Example:

            >>> en = wn.senses("petiole", lang="en")[0]
            >>> pt = en.translate(lang="pt")[0]
            >>> pt.word().lemma()
            'pecíolo'

        """
        synset = self.synset()
        return [
            t_sense
            for t_synset in synset.translate(lang=lang, lexicon=lexicon)
            for t_sense in t_synset.senses()
        ]
