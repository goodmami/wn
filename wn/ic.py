
r"""Information Content

The Information Content (IC) of a concept (synset) is a measure of its
specificity computed from the wordnet's taxonomy structure and corpus
frequencies. It is defined by Resnik 1995 ([RES95]_), following
information theory, as the negative log-probability of a concept:

.. math::

   IC(c) = -\log{p(c)}

A concept's probability is the empirical probability over a corpus:

.. math::

   p(c) = \frac{\text{freq}(c)}{N}

Here, :math:`N` is the total count of words of the same category as
concept :math:`c` ([RES95]_ only considered nouns) where each word has
some representation in the wordnet, and :math:`\text{freq}` is defined
as the sum of corpus counts of words in :math:`\text{words}(c)`, which
is the set of words subsumed by concept :math:`c`:

.. math::

   \text{freq}(c) = \sum_{n \in \text{words}(c)}{\text{count}(n)}


.. [RES95] Resnik, Philip. "Using information content to evaluate
   semantic similarity." In Proceedings of the 14th International
   Joint Conference on Artificial Intelligence (IJCAI-95), Montreal,
   Canada, pp. 448-453. 1995.

"""

from typing import Iterable, Dict
from collections import Counter

from wn._core import Synset, Wordnet
from wn.constants import NOUN, VERB, ADJ, ADV, ADJ_SAT

# Just use a subset of all available parts of speech
IC_PARTS_OF_SPEECH = frozenset((NOUN, VERB, ADJ, ADV))


Corpus = Iterable[str]
IC = Dict[str, Dict[Synset, float]]  # {pos: {synset: ic}}


def compute(
    corpus: Corpus,
    wordnet: Wordnet,
    distribute_weight: bool = True,
    smoothing: float = 1.0
) -> IC:

    counts = Counter(corpus)

    # intialize with the smoothing value
    ic: IC = {pos: {synset: smoothing
                    for synset in wordnet.synsets(pos=pos)}
              for pos in IC_PARTS_OF_SPEECH}
    # pretend ADJ_SAT is just ADJ
    for synset in wordnet.synsets(pos=ADJ_SAT):
        ic[ADJ][synset] = smoothing

    for word, count in counts.items():
        synsets = wordnet.synsets(word)
        num = len(synsets)
        if num == 0:
            continue
        weight = count / num if distribute_weight else count
        for synset in synsets:
            pos = synset.pos
            if pos == ADJ_SAT:
                pos = ADJ
            if pos not in IC_PARTS_OF_SPEECH:
                continue
            ic[pos][synset] += weight

    return ic
