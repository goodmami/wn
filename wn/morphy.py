
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
        >>> from wn.constants import NOUN
        >>> from wn.morphy import Morphy
        >>> ewn = wn.Wordnet('ewn:2020')
        >>> m = Morphy(ewn)
        >>> list(m('axes', NOUN))
        ['axe', 'ax', 'axis']
        >>> list(m('geese', NOUN))
        ['goose']
    """

    search_all_forms = False
    parts_of_speech = {NOUN, VERB, ADJ, ADJ_SAT, ADV}

    def __init__(self, wordnet: wn.Wordnet, system: System = WN):
        if any(lex.language != 'en' for lex in wordnet.lexicons()):
            warnings.warn(
                'Morphy is not intended for use with non-English wordnets',
                wn.WnWarning
            )
        self._wordnet = wordnet
        self._system = system
        self._rules = {
            pos: [rule for rule in rules if rule[2] & system]
            for pos, rules in DETACHMENT_RULES.items()
        }
        self._exceptions: ExceptionMap = {
            pos: {} for pos in self.parts_of_speech
        }
        self._all_lemmas: Dict[str, Set[str]] = {
            pos: set() for pos in self.parts_of_speech
        }
        self._build()

    def __call__(self, form: str, pos: str) -> Iterator[str]:
        if pos not in self.parts_of_speech:
            return

        exceptions = self._exceptions[pos]
        rules = self._rules[pos]
        pos_lemmas = self._all_lemmas[pos]

        # original lemma
        if form in pos_lemmas:
            yield form

        seen = set()  # don't yield the same form more than once per pos

        # lemmas from exceptions
        for _form in exceptions.get(form, []):
            seen.add(_form)
            yield _form

        # lemmas from morphological detachment
        for suffix, repl, _ in rules:
            # avoid applying rules that perform full suppletion
            if form.endswith(suffix) and len(suffix) < len(form):
                _form = f'{form[:-len(suffix)]}{repl}'
                if _form in pos_lemmas and _form not in seen:
                    seen.add(_form)
                    yield _form

    def _build(self) -> None:
        exceptions = self._exceptions
        all_lemmas = self._all_lemmas
        for word in self._wordnet.words():
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
