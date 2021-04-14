
"""An implementation of the Morphy lemmatization system for English.

.. seealso::

   The Princeton WordNet `documentation
   <https://wordnet.princeton.edu/documentation/morphy7wn>`_ for the
   original implementation.

"""

from typing import Iterator, Dict, List, Tuple
import warnings

import wn
from wn.constants import NOUN, VERB, ADJ, ADJ_SAT, ADV

POSExceptionMap = Dict[str, List[str]]
ExceptionMap = Dict[str, POSExceptionMap]

POS_LIST = [NOUN, VERB, ADJ, ADJ_SAT, ADV]

DETACHMENT_RULES: Dict[str, List[Tuple[str, str]]] = {
    NOUN: [
        ("s", ""),
        ("ces", "x"),     # added
        ("ses", "s"),
        ("ves", "f"),     # added
        ("ives", "ife"),  # added
        ("xes", "x"),
        ("xes", "xis"),   # added
        ("zes", "z"),
        ("ches", "ch"),
        ("shes", "sh"),
        ("men", "man"),
        ("ies", "y"),
    ],
    VERB: [
        ("s", ""),
        ("ies", "y"),
        ("es", "e"),
        ("es", ""),
        ("ed", "e"),
        ("ed", ""),
        ("ing", "e"),
        ("ing", ""),
    ],
    ADJ: [
        ("er", ""),
        ("est", ""),
        ("er", "e"),
        ("est", "e"),
    ],
    ADV: [],
}
DETACHMENT_RULES[ADJ_SAT] = DETACHMENT_RULES[ADJ]


class Morphy:
    """The Morphy lemmatizer class.

    Arguments:
        wordnet: optional :class:`wn.Wordnet` instance

    Example:

        >>> import wn
        >>> from wn.morphy import Morphy
        >>> m = Morphy()
        >>> list(m('axes'))
        ['axes', 'axe', 'ax', 'axis']
        >>> list(m('geese'))
        ['geese']
        >>> m = Morphy(wn.Wordnet('ewn:2020'))
        >>> list(m('axes'))
        ['axes', 'axe', 'ax', 'axis']
        >>> list(m('geese'))
        ['geese', 'goose']
    """

    def __init__(self, wordnet:  wn.Wordnet = None):
        self._wordnet = wordnet
        if wordnet and any(lex.language != 'en' for lex in wordnet.lexicons()):
            warnings.warn(
                'Morphy is not intended for use with non-English wordnets',
                wn.WnWarning
            )
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
            forms = _iterforms(form, p, self._exceptions[p])
            # from Python 3.7, the following is simply:
            #   yield from iter(set(forms))
            for other in forms:
                if other not in seen:
                    seen.add(other)
                    yield other


def _build_exception_map(wordnet: wn.Wordnet = None) -> ExceptionMap:
    exceptions: ExceptionMap = {pos: {} for pos in POS_LIST}
    if wordnet:
        for word in wordnet.words():
            pos_exc = exceptions[word.pos]
            lemma, *others = word.forms()
            for other in others:
                if other in pos_exc:
                    pos_exc[other].append(lemma)
                else:
                    pos_exc[other] = [lemma]
    return exceptions


def _iterforms(form: str, pos: str, exceptions: POSExceptionMap) -> Iterator[str]:
    yield form

    rules = DETACHMENT_RULES[pos]
    yield from iter(exceptions.get(form, []))

    for suffix, repl in rules:
        if form.endswith(suffix):
            yield f'{form[:-len(suffix)]}{repl}'
