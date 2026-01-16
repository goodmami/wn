from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, NamedTuple, Protocol, TypeVar

from wn._metadata import HasMetadata
from wn._queries import (
    find_entries,
    find_ilis,
    find_senses,
    find_synsets,
    get_lexicon,
    get_lexicon_dependencies,
    get_lexicon_extension_bases,
    get_lexicon_extensions,
    get_modified,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from wn._metadata import Metadata

DEFAULT_CONFIDENCE = 1.0


Self = TypeVar("Self", bound="Lexicon")  # typing.Self, python_version>=3.11


@dataclass(repr=False, eq=True, frozen=True, slots=True)
class Lexicon(HasMetadata):
    """A class representing a wordnet lexicon."""

    __module__ = "wn"

    _specifier: str
    id: str
    label: str
    language: str
    email: str
    license: str
    version: str
    url: str | None = None
    citation: str | None = None
    logo: str | None = None
    _metadata: Metadata | None = field(default=None, hash=False)

    @classmethod
    def from_specifier(cls: type[Self], specifier: str) -> Self:
        data = get_lexicon(specifier)
        spec, id, label, lang, email, license, version, url, citation, logo, meta = data
        return cls(
            spec,
            id,
            label,
            lang,
            email,
            license,
            version,
            url=url,
            citation=citation,
            logo=logo,
            _metadata=meta,
        )

    def __repr__(self):
        return f"<Lexicon {self._specifier} [{self.language}]>"

    def specifier(self) -> str:
        """Return the *id:version* lexicon specifier."""
        return self._specifier

    def confidence(self) -> float:
        """Return the confidence score of the lexicon.

        If the lexicon does not specify a confidence score, it defaults to 1.0.
        """
        return float(self.metadata().get("confidenceScore", DEFAULT_CONFIDENCE))

    def modified(self) -> bool:
        """Return True if the lexicon has local modifications."""
        return get_modified(self._specifier)

    def requires(self) -> dict[str, Lexicon | None]:
        """Return the lexicon dependencies."""
        return {
            spec: (None if added is None else Lexicon.from_specifier(spec))
            for spec, _, added in get_lexicon_dependencies(self._specifier)
        }

    def extends(self) -> Lexicon | None:
        """Return the lexicon this lexicon extends, if any.

        If this lexicon is not an extension, return None.
        """
        bases = get_lexicon_extension_bases(self._specifier, depth=1)
        if bases:
            return Lexicon.from_specifier(bases[0])
        return None

    def extensions(self, depth: int = 1) -> list[Lexicon]:
        """Return the list of lexicons extending this one.

        By default, only direct extensions are included. This is
        controlled by the *depth* parameter, which if you view
        extensions as children in a tree where the current lexicon is
        the root, *depth=1* are the immediate extensions. Increasing
        this number gets extensions of extensions, or setting it to a
        negative number gets all "descendant" extensions.

        """
        return [
            Lexicon.from_specifier(spec)
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
            f"{self._specifier}",
            f"  Label  : {self.label}",
            f"  URL    : {self.url}",
            f"  License: {self.license}",
        ]
        if full:
            substrings.extend(
                [
                    f"  Words  : {_desc_counts(find_entries, lexspecs)}",
                    f"  Senses : {sum(1 for _ in find_senses(lexicons=lexspecs))}",
                ]
            )
        substrings.extend(
            [
                f"  Synsets: {_desc_counts(find_synsets, lexspecs)}",
                f"  ILIs   : {sum(1 for _ in find_ilis(lexicons=lexspecs)):>6}",
            ]
        )
        return "\n".join(substrings)


def _desc_counts(query: Callable, lexspecs: Sequence[str]) -> str:
    count: dict[str, int] = {}
    for _, pos, *_ in query(lexicons=lexspecs):
        if pos not in count:
            count[pos] = 1
        else:
            count[pos] += 1
    subcounts = ", ".join(f"{pos}: {count[pos]}" for pos in sorted(count))
    return f"{sum(count.values()):>6} ({subcounts})"


class LexiconElement(Protocol):
    """Protocol for elements defined within a lexicon."""

    _lexicon: str  # source lexicon specifier

    def lexicon(self) -> Lexicon:
        """Return the lexicon containing the element."""
        return Lexicon.from_specifier(self._lexicon)


class LexiconElementWithMetadata(LexiconElement, HasMetadata, Protocol):
    """Protocol for lexicon elements with metadata."""

    def confidence(self) -> float:
        """Return the confidence score of the element.

        If the element does not have an explicit confidence score, the
        value defaults to that of the lexicon containing the element.
        """
        c = self.metadata().get("confidenceScore")
        if c is None:
            c = self.lexicon().confidence()
        return float(c)


class LexiconConfiguration(NamedTuple):
    lexicons: tuple[str, ...]
    expands: tuple[str, ...]
    default_mode: bool
