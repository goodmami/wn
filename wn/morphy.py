
"""An implementation of the Morphy lemmatization system for English.

.. seealso::

   The Princeton WordNet `documentation
   <https://wordnet.princeton.edu/documentation/morphy7wn>`_ for the
   original implementation.

"""

from typing import Iterator, Dict, Set, List, Tuple
import warnings
from enum import Flag, auto

import wn
from wn.constants import NOUN, VERB, ADJ, ADJ_SAT, ADV

POSExceptionMap = Dict[str, Set[str]]
ExceptionMap = Dict[str, POSExceptionMap]

POS_LIST = [NOUN, VERB, ADJ, ADJ_SAT, ADV]
ALL_LEMMAS = ''  # assumption: no alternative form should be the empty string


class System(Flag):
    """Flags to track suffix rules in various implementations of Morphy.

    These are available at the module level, as well (e.g., `morphy.PWN`).
    """
    PWN = auto()
    NLTK = auto()
    WN = auto()
    ALL = PWN | NLTK | WN


PWN = System.PWN
NLTK = System.NLTK
WN = System.WN
_ALL = System.ALL


Rule = Tuple[str, str, System]

DETACHMENT_RULES: Dict[str, List[Rule]] = {
    NOUN: [
        ("s",    "",    _ALL),
        ("ces",  "x",   WN),
        ("ses",  "s",   _ALL),
        ("ves",  "f",   NLTK | WN),
        ("ives", "ife", WN),
        ("xes",  "x",   _ALL),
        ("xes",  "xis", WN),
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


class Morphy(wn.Lemmatizer):
    """The Morphy lemmatizer class.

    Arguments:
        wordnet: optional :class:`wn.Wordnet` instance

    Example:

        >>> import wn
        >>> from wn.morphy import Morphy
        >>> ewn = wn.Wordnet('ewn:2020')
        >>> m = Morphy(ewn)
        >>> list(m('axes'))
        ['axe', 'ax', 'axis']
        >>> list(m('geese'))
        ['goose']
    """

    search_all_forms = False

    def __init__(self, wordnet: wn.Wordnet, system: System = WN):
        if any(lex.language != 'en' for lex in wordnet.lexicons()):
            warnings.warn(
                'Morphy is not intended for use with non-English wordnets',
                wn.WnWarning
            )
        self._wordnet = wordnet
        self._system = system
        self._rules = {pos: [rule for rule in rules if rule[2] & system]
                       for pos, rules in DETACHMENT_RULES.items()}
        self._exceptions = _build_exception_map(wordnet)

    def __call__(self, form: str, pos: str = None) -> Iterator[str]:
        if pos is None:
            poslist = POS_LIST
        elif pos not in POS_LIST:
            raise wn.Error(f'unsupported or invalid part of speech: {pos}')
        else:
            poslist = [pos]

        seen = set()
        for p in poslist:
            forms = _iterforms(form, self._rules[p], self._exceptions[p])
            # from Python 3.7, the following is simply:
            #   yield from iter(set(forms))
            for other in forms:
                if other not in seen:
                    seen.add(other)
                    yield other


def _build_exception_map(wordnet: wn.Wordnet) -> ExceptionMap:
    exceptions: ExceptionMap = {pos: {ALL_LEMMAS: set()} for pos in POS_LIST}
    if wordnet:
        for word in wordnet.words():
            pos_exc = exceptions[word.pos]
            lemma, *others = word.forms()
            # store every lemma whether it has other forms or not
            pos_exc[ALL_LEMMAS].add(lemma)
            # those with other forms map to the original lemmas
            for other in others:
                if other in pos_exc:
                    pos_exc[other].add(lemma)
                else:
                    pos_exc[other] = {lemma}
    return exceptions


def _iterforms(
    form: str,
    rules: List[Rule],
    exceptions: POSExceptionMap
) -> Iterator[str]:
    pos_lemmas = exceptions[ALL_LEMMAS]

    if form in pos_lemmas:
        yield form

    yield from iter(exceptions.get(form, []))

    for suffix, repl, _ in rules:
        # avoid applying rules that perform full suppletion
        if form.endswith(suffix) and len(suffix) < len(form):
            _form = f'{form[:-len(suffix)]}{repl}'
            if _form in pos_lemmas:
                yield _form
