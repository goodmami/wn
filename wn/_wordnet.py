import textwrap
import warnings
from collections.abc import Callable, Iterator, Sequence
from typing import Literal, TypeVar, overload

from wn._core import Form, Pronunciation, Sense, Synset, Tag, Word
from wn._exceptions import Error, WnWarning
from wn._lexicon import Lexicon, LexiconConfiguration
from wn._queries import (
    find_entries,
    find_lemmas,
    find_senses,
    find_synsets,
    get_lexicon_dependencies,
    resolve_lexicon_specifiers,
)
from wn._types import (
    LemmatizeFunction,
    NormalizeFunction,
)
from wn._util import normalize_form

# Useful for factory functions of Word, Sense, or Synset
C = TypeVar("C", Word, Sense, Synset)


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

    __slots__ = (
        "_default_mode",
        "_lexconf",
        "_normalizer",
        "_search_all_forms",
        "lemmatizer",
    )
    __module__ = "wn"

    def __init__(
        self,
        lexicon: str | None = None,
        *,
        lang: str | None = None,
        expand: str | None = None,
        normalizer: NormalizeFunction | None = normalize_form,
        lemmatizer: LemmatizeFunction | None = None,
        search_all_forms: bool = True,
    ):
        if lexicon or lang:
            lexicons = tuple(resolve_lexicon_specifiers(lexicon or "*", lang=lang))
        else:
            lexicons = ()
        if lang and len(lexicons) > 1:
            warnings.warn(
                f"multiple lexicons match {lang=}: {lexicons!r}; "
                "use the lexicon parameter instead to avoid this warning",
                WnWarning,
                stacklevel=2,
            )

        # default mode means any lexicon is searched or expanded upon,
        # but relation traversals only target the source's lexicon
        default_mode = not lexicon and not lang
        expand = _resolve_lexicon_dependencies(expand, lexicons, default_mode)
        expands = tuple(resolve_lexicon_specifiers(expand)) if expand else ()

        self._lexconf = LexiconConfiguration(
            lexicons=lexicons,
            expands=expands,
            default_mode=default_mode,
        )

        self._normalizer = normalizer
        self.lemmatizer = lemmatizer
        self._search_all_forms = search_all_forms

    def lexicons(self) -> list[Lexicon]:
        """Return the list of lexicons covered by this wordnet."""
        return list(map(Lexicon.from_specifier, self._lexconf.lexicons))

    def expanded_lexicons(self) -> list[Lexicon]:
        """Return the list of expand lexicons for this wordnet."""
        return list(map(Lexicon.from_specifier, self._lexconf.expands))

    def word(self, id: str) -> Word:
        """Return the first word in this wordnet with identifier *id*."""
        iterable = find_entries(id=id, lexicons=self._lexconf.lexicons)
        try:
            id, pos, lex = next(iterable)
            return Word(id, pos, _lexicon=lex, _lexconf=self._lexconf)
        except StopIteration:
            raise Error(f"no such lexical entry: {id}") from None

    def words(self, form: str | None = None, pos: str | None = None) -> list[Word]:
        """Return the list of matching words in this wordnet.

        Without any arguments, this function returns all words in the
        wordnet's selected lexicons. A *form* argument restricts the
        words to those matching the given word form, and *pos*
        restricts words by their part of speech.

        """
        return _find_helper(self, Word, find_entries, form, pos)

    @overload
    def lemmas(
        self,
        form: str | None = None,
        pos: str | None = None,
        *,
        data: Literal[False] = False,
    ) -> list[str]: ...
    @overload
    def lemmas(
        self,
        form: str | None = None,
        pos: str | None = None,
        *,
        data: Literal[True] = True,
    ) -> list[Form]: ...

    # fallback for non-literal bool argument
    @overload
    def lemmas(
        self, form: str | None = None, pos: str | None = None, *, data: bool
    ) -> list[str] | list[Form]: ...

    def lemmas(
        self, form: str | None = None, pos: str | None = None, *, data: bool = False
    ) -> list[str] | list[Form]:
        """Return the list of lemmas for matching words in this wordnet.

        Without any arguments, this function returns all distinct lemma
        forms in the wordnet's selected lexicons. A *form* argument
        restricts the words to those matching the given word form, and
        *pos* restricts words by their part of speech.

        If the *data* argument is :python:`False` (the default), only
        distinct lemma forms are returned as :class:`str` types. If it
        is :python:`True`, :class:`wn.Form` objects are returned for
        all matching entries, which may include multiple Form objects
        with the same lemma string.

        Example:

            >>> wn.Wordnet().lemmas("wolves")
            ['wolf']
            >>> wn.Wordnet().lemmas("wolves", data=True)
            [Form(value='wolf')]

        """
        form_data = _find_lemmas(self, form, pos, load_details=data)

        if data:
            return [
                Form(
                    form,
                    id=id,
                    script=script,
                    _lexicon=lex,
                    _pronunciations=tuple(Pronunciation(*p) for p in prons),
                    _tags=tuple(Tag(*t) for t in tags),
                )
                for form, id, script, lex, prons, tags in form_data
            ]

        # When data=False, extract and deduplicate strings
        return list(dict.fromkeys(fd[0] for fd in form_data))

    def synset(self, id: str) -> Synset:
        """Return the first synset in this wordnet with identifier *id*."""
        iterable = find_synsets(id=id, lexicons=self._lexconf.lexicons)
        try:
            id, pos, ili, lex = next(iterable)
            return Synset(id, pos, ili=ili, _lexicon=lex, _lexconf=self._lexconf)
        except StopIteration:
            raise Error(f"no such synset: {id}") from None

    def synsets(
        self, form: str | None = None, pos: str | None = None, ili: str | None = None
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
            id, eid, ssid, lex = next(iterable)
            return Sense(id, eid, ssid, _lexicon=lex, _lexconf=self._lexconf)
        except StopIteration:
            raise Error(f"no such sense: {id}") from None

    def senses(self, form: str | None = None, pos: str | None = None) -> list[Sense]:
        """Return the list of matching senses in this wordnet.

        Without any arguments, this function returns all senses in the
        wordnet's selected lexicons. A *form* argument restricts the
        senses to those whose word matches the given word form, and
        *pos* restricts senses by their word's part of speech.

        """
        return _find_helper(self, Sense, find_senses, form, pos)

    def describe(self) -> str:
        """Return a formatted string describing the lexicons in this wordnet.

        Example:

            >>> oewn = wn.Wordnet("oewn:2021")
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
        substrings = ["Primary lexicons:"]
        for lex in self.lexicons():
            substrings.append(textwrap.indent(lex.describe(), "  "))
        if self._lexconf.expands:
            substrings.append("Expand lexicons:")
            for lex in self.expanded_lexicons():
                substrings.append(textwrap.indent(lex.describe(full=False), "  "))
        return "\n".join(substrings)


def _resolve_lexicon_dependencies(
    expand: str | None,
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
    missing = " ".join(spec for spec, added in deps if not added)
    if missing:
        warnings.warn(
            f"lexicon dependencies not available: {missing}",
            WnWarning,
            stacklevel=3,
        )
    return " ".join(spec for spec, added in deps if added)


def _find_lemmas(
    w: Wordnet, form: str | None, pos: str | None, load_details: bool = False
) -> Iterator[tuple]:
    """Return an iterator of matching lemma form data.

    This works like _find_helper but returns raw form tuples instead of
    Word/Sense/Synset objects. The load_details parameter controls whether
    pronunciations and tags are loaded from the database.
    """
    kwargs: dict = {
        "lexicons": w._lexconf.lexicons,
        "search_all_forms": w._search_all_forms,
        "load_details": load_details,
    }

    # easy case is when there is no form
    if form is None:
        yield from find_lemmas(pos=pos, **kwargs)
        return

    # if there's a form, we may need to lemmatize and normalize
    normalize = w._normalizer
    kwargs["normalized"] = bool(normalize)

    lemmatize = w.lemmatizer
    forms = lemmatize(form, pos) if lemmatize else {}
    # if no lemmatizer or word not covered by lemmatizer, back off to
    # the original form and pos
    if not forms:
        forms = {pos: {form}}

    yield from _query_with_forms(find_lemmas, forms, normalize, kwargs)


def _query_with_forms(
    query_func: Callable,
    forms: dict[str | None, set[str]],
    normalize: NormalizeFunction | None,
    kwargs: dict,
) -> list[tuple]:
    """Query database with forms, falling back to normalized forms if needed.

    Queries the database for each pos/forms combination. If a normalizer
    is available and the original forms return no results, queries again
    with normalized forms.
    """
    results = []
    for _pos, _forms in forms.items():
        results.extend(query_func(forms=_forms, pos=_pos, **kwargs))

    # Only try normalized forms if we got no results with original forms
    if not results and normalize:
        for _pos, _forms in forms.items():
            normalized_forms = [normalize(f) for f in _forms]
            results.extend(query_func(forms=normalized_forms, pos=_pos, **kwargs))

    return results


def _find_helper(
    w: Wordnet,
    cls: type[C],
    query_func: Callable,
    form: str | None,
    pos: str | None,
    ili: str | None = None,
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
        "lexicons": w._lexconf.lexicons,
        "search_all_forms": w._search_all_forms,
    }
    if ili:
        kwargs["ili"] = ili

    # easy case is when there is no form
    # (for type checking, it is hard to guess the correct number of
    #  fields in data, so ignore here and further down)
    if form is None:
        return [
            cls(*data, _lexconf=w._lexconf)  # type: ignore
            for data in query_func(pos=pos, **kwargs)
        ]

    # if there's a form, we may need to lemmatize and normalize
    normalize = w._normalizer
    kwargs["normalized"] = bool(normalize)

    lemmatize = w.lemmatizer
    forms = lemmatize(form, pos) if lemmatize else {}
    # if no lemmatizer or word not covered by lemmatizer, back off to
    # the original form and pos
    if not forms:
        forms = {pos: {form}}

    results_data = _query_with_forms(query_func, forms, normalize, kwargs)

    # we want unique results here, but a set can make the order
    # erratic, so filter manually
    results = [
        cls(*data, _lexconf=w._lexconf)  # type: ignore
        for data in results_data
    ]
    unique_results: list[C] = []
    seen: set[C] = set()
    for result in results:
        if result not in seen:
            unique_results.append(result)
            seen.add(result)
    return unique_results
