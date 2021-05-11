
"""A simple English lemmatizer that finds and removes known suffixes.

"""

from typing import Optional, Dict, Set, List, Tuple
from enum import Flag, auto

import wn
from wn._types import LemmatizeResult
from wn.constants import NOUN, VERB, ADJ, ADJ_SAT, ADV, PARTS_OF_SPEECH

POSExceptionMap = Dict[str, Set[str]]
ExceptionMap = Dict[str, POSExceptionMap]


class _System(Flag):
    """Flags to track suffix rules in various implementations of Morphy."""
    PWN = auto()
    NLTK = auto()
    WN = auto()
    ALL = PWN | NLTK | WN


_PWN = _System.PWN
_NLTK = _System.NLTK
_WN = _System.WN
_ALL = _System.ALL


Rule = Tuple[str, str, _System]

DETACHMENT_RULES: Dict[str, List[Rule]] = {
    NOUN: [
        ("s",    "",    _ALL),
        ("ces",  "x",   _WN),
        ("ses",  "s",   _ALL),
        ("ves",  "f",   _NLTK | _WN),
        ("ives", "ife", _WN),
        ("xes",  "x",   _ALL),
        ("xes",  "xis", _WN),
        ("zes",  "z",   _ALL),
        ("ches", "ch",  _ALL),
        ("shes", "sh",  _ALL),
        ("men",  "man", _ALL),
        ("ies",  "y",   _ALL),
    ],
    VERB: [
        ("s",   "",  _ALL),
        ("ies", "y", _ALL),
        ("es",  "e", _ALL),
        ("es",  "",  _ALL),
        ("ed",  "e", _ALL),
        ("ed",  "",  _ALL),
        ("ing", "e", _ALL),
        ("ing", "",  _ALL),
    ],
    ADJ: [
        ("er",  "",  _ALL),
        ("est", "",  _ALL),
        ("er",  "e", _ALL),
        ("est", "e", _ALL),
    ],
    ADV: [],
}
DETACHMENT_RULES[ADJ_SAT] = DETACHMENT_RULES[ADJ]


class Morphy:
    """The Morphy lemmatizer class.

    Objects of this class are callables that take a wordform and an
    optional part of speech and return a dictionary mapping parts of
    speech to lemmas. If objects of this class are not created with a
    :class:`wn.Wordnet` object, the returned lemmas may be invalid.

    Arguments:
        wordnet: optional :class:`wn.Wordnet` instance

    Example:

        >>> import wn
        >>> from wn.morphy import Morphy
        >>> ewn = wn.Wordnet('ewn:2020')
        >>> m = Morphy(ewn)
        >>> m('axes', pos='n')
        {'n': {'axe', 'ax', 'axis'}}
        >>> m('geese', pos='n')
        {'n': {'goose'}}
        >>> m('gooses')
        {'n': {'goose'}, 'v': {'goose'}}
        >>> m('goosing')
        {'v': {'goose'}}

    """

    def __init__(self, wordnet: Optional[wn.Wordnet] = None):
        self._rules = {
            pos: [rule for rule in rules if rule[2] & _System.WN]
            for pos, rules in DETACHMENT_RULES.items()
        }
        exceptions: ExceptionMap = {pos: {} for pos in PARTS_OF_SPEECH}
        all_lemmas: Dict[str, Set[str]] = {pos: set() for pos in PARTS_OF_SPEECH}
        if wordnet:
            for word in wordnet.words():
                pos = word.pos
                pos_exc = exceptions[pos]
                lemma, *others = word.forms()
                # store every lemma whether it has other forms or not
                all_lemmas[pos].add(lemma)
                # those with other forms map to the original lemmas
                for other in others:
                    if other in pos_exc:
                        pos_exc[other].add(lemma)
                    else:
                        pos_exc[other] = {lemma}
            self._initialized = True
        else:
            self._initialized = False
        self._exceptions = exceptions
        self._all_lemmas = all_lemmas

    def __call__(self, form: str, pos: Optional[str] = None) -> LemmatizeResult:
        result = {}
        if not self._initialized:
            result[pos] = {form}  # always include original when not initialized

        if pos is None:
            pos_list = list(DETACHMENT_RULES)
        elif pos in DETACHMENT_RULES:
            pos_list = [pos]
        else:
            pos_list = []  # not handled by morphy

        no_pos_forms = result.get(None, set())  # avoid unnecessary duplicates
        for _pos in pos_list:
            candidates = self._morphstr(form, _pos) - no_pos_forms
            if candidates:
                result.setdefault(_pos, set()).update(candidates)

        return result

    def _morphstr(self, form: str, pos: str) -> Set[str]:
        candidates: Set[str] = set()

        initialized = self._initialized
        if initialized:
            all_lemmas = self._all_lemmas[pos]
            if form in all_lemmas:
                candidates.add(form)
            candidates.update(self._exceptions[pos].get(form, set()))
        else:
            all_lemmas = set()

        for suffix, repl, _ in self._rules[pos]:
            # avoid applying rules that perform full suppletion
            if form.endswith(suffix) and len(suffix) < len(form):
                candidate = f'{form[:-len(suffix)]}{repl}'
                if not initialized or candidate in all_lemmas:
                    candidates.add(candidate)

        return candidates


morphy = Morphy()
