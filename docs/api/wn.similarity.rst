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

   -\text{log}\left(\frac{p + 1}{2d}\right)

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


Information Content-based Metrics
---------------------------------

The `Resnik <Resnik Similarity_>`_, `Jiang-Conrath <Jiang-Conrath
Similarity_>`_, and `Lin <Lin Similarity_>`_ similarity metrics work
by computing the information content of the synsets and/or that of
their lowest common hypernyms. They therefore require information
content weights (see :mod:`wn.ic`), and the values returned
necessarily depend on the weights used.


Resnik Similarity
'''''''''''''''''

The Resnik similarity (`Resnik 1995
<https://arxiv.org/pdf/cmp-lg/9511007.pdf>`_) is the maximum
information content value of the common subsumers (hypernym ancestors)
of the two synsets. Formally it is defined as follows, where
:math:`c_1` and :math:`c_2` are the two synsets being compared.

.. math::

   \text{max}_{c \in \text{S}(c_1, c_2)} \text{IC}(c)

Since a synset's information content is always equal or greater than
the information content of its hypernyms, :math:`S(c_1, c_2)` above is
more efficiently computed using the lowest common hypernyms instead of
all common hypernyms.

.. autofunction:: res


Jiang-Conrath Similarity
''''''''''''''''''''''''

The Jiang-Conrath similarity metric (`Jiang and Conrath, 1997
<https://www.aclweb.org/anthology/O97-1002.pdf>`_) combines the ideas
of the taxonomy-based and information content-based metrics. It is
defined as follows, where :math:`c_1` and :math:`c_2` are the two
synsets being compared and :math:`c_0` is the lowest common hypernym
of the two with the highest information content weight:

.. math::

   \frac{1}{\text{IC}(c_1) + \text{IC}(c_2) - 2(\text{IC}(c_0))}

This equation is the simplified form given in the paper were several
parameterized terms are cancelled out because the full form is not
often used in practice.

There are two special cases:

1. If the information content of :math:`c_0`, :math:`c_1`, and
   :math:`c_2` are all zero, the metric returns zero. This occurs when
   both :math:`c_1` and :math:`c_2` are the root node, but it can also
   occur if the synsets did not occur in the corpus and the smoothing
   value was set to zero.

2. Otherwise if :math:`c_1 + c_2 = 2c_0`, the metric returns
   infinity. This occurs when the two synsets are the same, one is a
   descendant of the other, etc., such that they have the same
   frequency as each other and as their lowest common hypernym.

.. autofunction:: jcn


Lin Similarity
''''''''''''''

Another formulation of information content-based similarity is the Lin
metric (`Lin 1997 <https://www.aclweb.org/anthology/P97-1009.pdf>`_),
which is defined as follows, where :math:`c_1` and :math:`c_2` are the
two synsets being compared and :math:`c_0` is the lowest common
hypernym with the highest information content weight:

.. math::

   \frac{2(\text{IC}(c_0))}{\text{IC}(c_1) + \text{IC}(c_0)}

One special case is if either synset has an information content value
of zero, in which case the metric returns zero.

.. autofunction:: lin
