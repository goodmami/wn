
wn.ic
=====

.. automodule:: wn.ic

Description
-----------

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

That is, the frequency of a concept like **stone fruit** is not the
number of occurrences of *stone fruit* or *stone fruits*, but also
includes the counts of *almond*, *almonds*, *peach*, etc. In
algorithmic terms, when encountering a word, the counts of the synsets
of the word and all of the synsets' taxonomic ancestors are
incremented.

It is common for :math:`\text{freq}` to not contain actual frequencies
but instead weights. These weights are calculated as the word
frequency divided by the number of synsets for that word.

.. note::

   The term *information content* can be ambiguous. It sometimes
   refers to the result of the :func:`information_content` function,
   but is also used to refer to the corpus frequencies/weights in the
   data structure returned by :func:`load` or :func:`compute`, as
   these weights are the basis of the value computed by
   :func:`information_content`. The Wn documentation tries to
   consistently refer to former as the *information content value* and
   the latter as *information content weights*.

.. [RES95] Resnik, Philip. "Using information content to evaluate
   semantic similarity." In Proceedings of the 14th International
   Joint Conference on Artificial Intelligence (IJCAI-95), Montreal,
   Canada, pp. 448-453. 1995.


Calculating Information Content
-------------------------------

.. autofunction:: information_content
.. autofunction:: synset_probability


Computing Corpus Weights
------------------------

.. autofunction:: compute


Reading Pre-computed Information Content Files
----------------------------------------------

.. autofunction:: load
