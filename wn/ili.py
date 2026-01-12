"""Interlingual Indices

This module provides classes and functions for inspecting Interlingual
Index (ILI) objects, both existing and proposed and including their
definitions and any metadata, for synsets and lexicons.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from itertools import zip_longest
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol, overload

from wn._lexicon import Lexicon, LexiconElementWithMetadata
from wn._metadata import HasMetadata
from wn._queries import (
    find_ilis,
    find_proposed_ilis,
    get_ili,
)
from wn._wordnet import Wordnet

if TYPE_CHECKING:
    from collections.abc import Iterator

    from wn._core import Synset
    from wn._metadata import Metadata
    from wn._types import AnyPath


class ILIStatus(str, Enum):
    __module__ = "wn"

    UNKNOWN = "unknown"  # no information available
    ACTIVE = "active"  # attested in ILI file and marked as active
    PRESUPPOSED = "presupposed"  # used by lexicon, ILI file not loaded
    PROPOSED = "proposed"  # proposed by lexicon for addition to ILI


@dataclass(slots=True)
class ILIDefinition(HasMetadata):
    """Class for modeling ILI definitions."""

    __module__ = "wn"

    text: str
    _metadata: Metadata | None = field(default=None, compare=False, repr=False)
    _lexicon: str | None = field(default=None, compare=False, repr=False)

    def metadata(self) -> Metadata:
        """Return the ILI's metadata."""
        return self._metadata if self._metadata is not None else {}

    def confidence(self) -> float:
        c = self.metadata().get("confidenceScore")
        if c is None:
            if self._lexicon:
                # ProposedILIs are lexicon elements and inherit their
                # lexicon's confidence value
                c = Lexicon.from_specifier(self._lexicon).confidence()
            else:
                # Regular ILIs are not lexicon elements
                c = 1.0
        return float(c)


class ILIProtocol(Protocol):
    _definition_text: str | None
    _definition_metadata: Metadata | None

    @property
    def id(self) -> str | None:
        """The ILI identifier."""
        ...

    @property
    def status(self) -> ILIStatus:
        """The status of the ILI."""
        ...

    @overload
    def definition(self, *, data: Literal[False] = False) -> str | None: ...
    @overload
    def definition(self, *, data: Literal[True] = True) -> ILIDefinition | None: ...

    # fallback for non-literal bool argument
    @overload
    def definition(self, *, data: bool) -> str | ILIDefinition | None: ...

    def definition(self, *, data: bool = False) -> str | ILIDefinition | None:
        """Return the ILI's definition.

        If the *data* argument is :python:`False` (the default), the
        definition is returned as a :class:`str` type. If it is
        :python:`True`, a :class:`wn.ILIDefinition` object is used instead.

        Note that :class:`ILI` objects will not have definitions unless
        an ILI resource has been added, but :class:`ProposedILI` objects
        will have definitions if one is provided by the proposing lexicon.

        """
        if data and self._definition_text:
            return ILIDefinition(
                self._definition_text,
                _metadata=self._definition_metadata,
                # lexicon is defined only for proposed ILIs
                _lexicon=getattr(self, "_lexicon", None),
            )
        return self._definition_text


@dataclass(frozen=True, slots=True)
class ILI(ILIProtocol):
    """A class for interlingual indices."""

    __module__ = "wn"

    id: str
    status: ILIStatus = field(
        default=ILIStatus.UNKNOWN, repr=False, hash=False, compare=False
    )
    _definition_text: str | None = field(
        default=None, repr=False, hash=False, compare=False
    )
    _definition_metadata: Metadata | None = field(
        default=None, repr=False, hash=False, compare=False
    )


@dataclass(frozen=True, slots=True)
class ProposedILI(LexiconElementWithMetadata, ILIProtocol):
    __module__ = "wn"

    _synset: str
    _lexicon: str
    _definition_text: str | None = field(
        default=None, repr=False, hash=False, compare=False
    )
    _definition_metadata: Metadata | None = field(
        default=None, repr=False, hash=False, compare=False
    )

    @property
    def id(self) -> Literal[None]:
        """Always return :python:`None`.

        Proposed ILIs do not have identifiers. This method is kept for
        interface consistency.

        """
        return None

    @property
    def status(self) -> Literal[ILIStatus.PROPOSED]:
        """Always return :attr:`ILIStatus.PROPOSED`.

        Proposed ILI objects are only used for ILIs that are proposed.

        """
        return ILIStatus.PROPOSED

    def synset(self) -> Synset:
        """Return the synset object associated with the proposed ILI."""
        return Wordnet(self._lexicon).synset(self._synset)


def get(id: str) -> ILI | None:
    """Get the ILI object with the given id.

    The *id* argument is a string ILI identifier. If *id* does not
    match a known ILI, :python:`None` is returned. Note that a
    :python:`None` value does not necessarily mean that there is no
    such ILI, but rather that no resource declaring that ILI has been
    loaded into Wn's database.

    Example:

    >>> from wn import ili
    >>> ili.get("i12345")
    ILI('i12345')
    >>> ili.get("i0") is None
    True

    """
    if row := get_ili(id=id):
        id, status, defn, meta = row
        return ILI(
            id,
            status=ILIStatus(status),
            _definition_text=defn,
            _definition_metadata=meta,
        )
    return None


def get_all(
    *,
    status: ILIStatus | str | None = None,
    lexicon: str | None = None,
) -> list[ILI]:
    """Get the list of all matching ILI objects.

    The *status* argument may be a string matching a single
    :class:`ILIStatus`, or a union of one or more :class:`ILIStatus`
    values. The *lexicon* argument is a space-separated string of
    lexicon specifiers. All ILIs with a matching status and lexicon
    will be returned.

    Example:

    >>> from wn import ili
    >>> len(ili.get_all())
    117442

    """
    if isinstance(status, str):
        status = ILIStatus(status)
    lexicons = lexicon.split() if lexicon else []
    return [
        ILI(
            id,
            status=ILIStatus(status),
            _definition_text=defn,
            _definition_metadata=meta,
        )
        for id, status, defn, meta in find_ilis(status=status, lexicons=lexicons)
    ]


def get_proposed(synset: Synset) -> ProposedILI | None:
    """Get a proposed ILI for *synset* if it exists.

    The synset itself does not give a good indication if it has an
    associated proposed ILI. The :attr:`wn.Synset.ili` value will be
    :python:`None`, but this is also true if there is no ILI at all.
    In most cases it is easier to list the proposed ILIs for a lexicon
    using :func:`get_all_proposed`, then to retrieve their associated
    synsets.

    Example:

    >>> import wn
    >>> from wn import ili
    >>> en = wn.Wordnet("oewn:2024")
    >>> en.synset("oewn-00002935-r").ili is None
    True
    >>> ili.get_proposed(en.synset("oewn-00002935-r"))
    ProposedILI(_synset='oewn-00002935-r', _lexicon='oewn:2024')

    """
    results = find_proposed_ilis(
        synset_id=synset.id,
        lexicons=(synset.lexicon().specifier(),),
    )
    if row := next(results, None):
        return ProposedILI(*row)
    return None


def get_all_proposed(lexicon: str | None = None) -> list[ProposedILI]:
    """Get the list of all proposed ILI objects.

    The *lexicon* argument is a space-separated string of lexicon
    specifiers. Proposed ILIs matching the lexicon will be returned.

    Example:

    >>> from wn import ili
    >>> proposed = ili.get_all_proposed("oewn:2024")
    >>> proposed[0]
    ProposedILI(_synset='oewn-00002935-r', _lexicon='oewn:2024')
    >>> proposed[0].synset()
    Synset('oewn-00002935-r')

    """
    lexicons = lexicon.split() if lexicon else []
    return [ProposedILI(*row) for row in find_proposed_ilis(lexicons=lexicons)]


def is_ili_tsv(source: AnyPath) -> bool:
    """Return True if *source* is an ILI tab-separated-value file.

    This only checks that the first column, split by tabs, of the
    first line is 'ili' or 'ILI'. It does not check if each line has
    the correct number of columns.

    """
    source = Path(source).expanduser()
    if source.is_file():
        try:
            with source.open("rb") as fh:
                return next(fh).split(b"\t")[0] in (b"ili", b"ILI")
        except (StopIteration, IndexError):
            pass
    return False


def load_tsv(source: AnyPath) -> Iterator[dict[str, str]]:
    """Yield data from an ILI tab-separated-value file.

    This function yields dictionaries mapping field names to values.
    The *source* argument is a path to an ILI file.

    Example:

    >>> from wn import ili
    >>> obj = next(ili._load_tsv("cili.tsv"))
    >>> obj.keys()
    dict_keys(['ili', 'definition'])
    >>> obj["ili"]
    'i1'

    """
    source = Path(source).expanduser()
    with source.open(encoding="utf-8") as fh:
        header = next(fh).rstrip("\r\n")
        fields = tuple(map(str.lower, header.split("\t")))
        for line in fh:
            yield dict(
                zip_longest(
                    fields,
                    line.rstrip("\r\n").split("\t"),
                    fillvalue="",
                )
            )
