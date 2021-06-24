wn.similarity
=============

.. automodule:: wn.similarity

Taxonomy-based Metrics
----------------------

The `Path <Path Similarity_>`_, `Leacock-Chodorow <Leacock-Chodorow
Similarity_>`_, and `Wu-Palmer <Wu-Palmer Similarity_>`_ similarity
metrics work by finding path distances in the hypernym/hyponym
taxonomy. As such, they are most useful when the synsets are, in fact,
arranged in a taxonomy. For the Princeton WordNet and derivative
wordnets, synsets for nouns and verbs are arranged taxonomically: the
nouns mostly form a single structure with a single root while verbs
form many smaller structures with many roots. Synsets for the other
parts of speech do not use hypernym/hyponym relations at all. This
situation may be different for other wordnet projects or future
versions of the English wordnets.

The similarity metrics tend to fail when the synsets are not connected
by some path. When the synsets are in different parts of speech, or
even in separate lexicons, this failure is acceptable and
expected. But for cases like the verbs in the Princeton WordNet, it
might be more useful to pretend that there is some unique root for all
verbs so as to create a path connecting any two of them. For this
purpose, the *simulate_root* parameter is available on the
:func:`path`, :func:`lch`, and :func:`wup` functions, where it is
passed on to calls to :meth:`wn.Synset.shortest_path` and
:meth:`wn.Synset.lowest_common_hypernyms`. Setting *simulate_root* to
:python:`True` can, however, give surprising results if the words are
from a different lexicon. Currently, computing similarity for synsets
from a different part of speech raises an error.


Path Similarity
'''''''''''''''

When :math:`p` is the length of the shortest path between two synsets,
the path similarity is:

.. math::

   \frac{1}{p + 1}

The similarity score ranges between 0.0 and 1.0, where the higher the
score is, the more similar the synsets are. The score is 1.0 when a
synset is compared to itself, and 0.0 when there is no path between
the two synsets (i.e., the path distance is infinite).

.. autofunction:: path


.. _leacock-chodorow-similarity:

Leacock-Chodorow Similarity
'''''''''''''''''''''''''''

When :math:`p` is the length of the shortest path between two synsets
and :math:`d` is the maximum taxonomy depth, the Leacock-Chodorow
similarity is:

.. math::

   -\text{log}(\frac{p + 1}{2d})

.. autofunction:: lch


Wu-Palmer Similarity
''''''''''''''''''''

When *LCS* is the lowest common hypernym (also called "least common
subsumer") between two synsets, :math:`i` is the shortest path
distance from the first synset to *LCS*, :math:`j` is the shortest
path distance from the second synset to *LCS*, and :math:`k` is the
number of nodes (distance + 1) from *LCS* to the root node, then the
Wu-Palmer similarity is:

.. math::

   \frac{2k}{i + j + 2k}

.. autofunction:: wup

