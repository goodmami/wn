
wn.ic
=====

.. automodule:: wn.ic

The mathematical formulae for information content are defined in
`Formal Description`_, and the corresponding Python API function are
described in `Calculating Information Content`_. These functions
require information content weights obtained either by `computing them
from a corpus <Computing Corpus Weights_>`_, or by `loading
pre-computed weights from a file <Reading Pre-computed Information
Content Files_>`_.

.. note::

   The term *information content* can be ambiguous. It often, and most
   accurately, refers to the result of the :func:`information_content`
   function (:math:`\text{IC}(c)` in the mathematical notation), but
   is also sometimes used to refer to the corpus frequencies/weights
   (:math:`\text{freq}(c)` in the mathematical notation) returned by
   :func:`load` or :func:`compute`, as these weights are the basis of
   the value computed by :func:`information_content`. The Wn
   documentation tries to consistently refer to former as the
   *information content value*, or just *information content*, and the
   latter as *information content weights*, or *weights*.


Formal Description
------------------

The Information Content (IC) of a concept (synset) is a measure of its
specificity computed from the wordnet's taxonomy structure and corpus
frequencies. It is defined by Resnik 1995 ([RES95]_), following
information theory, as the negative log-probability of a concept:

.. math::

   \text{IC}(c) = -\log{p(c)}

A concept's probability is the empirical probability over a corpus:

.. math::

   p(c) = \frac{\text{freq}(c)}{N}

Here, :math:`N` is the total count of words of the same category as
concept :math:`c` ([RES95]_ only considered nouns) where each word has
some representation in the wordnet, and :math:`\text{freq}` is defined
as the sum of corpus counts of words in :math:`\text{words}(c)`, which
is the set of words subsumed by concept :math:`c`:

.. math::

   \text{freq}(c) = \sum_{w \in \text{words}(c)}{\text{count}(w)}

It is common for :math:`\text{freq}` to not contain actual frequencies
but instead weights distributed evenly among the synsets for a
word. These weights are calculated as the word frequency divided by
the number of synsets for the word:

.. math::

   \text{freq}_{\text{distributed}}(c)
   = \sum_{w \in \text{words}(c)}{\frac{\text{count}(w)}{|\text{synsets}(w)|}}

.. [RES95] Resnik, Philip. "Using information content to evaluate
   semantic similarity." In Proceedings of the 14th International
   Joint Conference on Artificial Intelligence (IJCAI-95), Montreal,
   Canada, pp. 448-453. 1995.


Example
-------

In the Princeton WordNet, the frequency of a concept like **stone
fruit** is not the number of occurrences of *stone fruit*, but also
includes the counts of the words for its hyponyms (*almond*, *olive*,
etc.) and other taxonomic descendants (*Jordan almond*, *green olive*,
etc.). The word *almond* has two synsets: one for the fruit or nut,
another for the plant. Thus, if the word *almond* is encountered
:math:`n` times in a corpus, then the weight (either the frequency
:math:`n` or distributed weight :math:`\frac{n}{2}`) is added to the
total weights for both synsets and to those of their ancestors, but
not for descendant synsets, such as for **Jordan almond**. The fruit/nut
synset of almond has two hypernym paths which converge on **fruit**:

1. **almond** ⊃ **stone fruit** ⊃ **fruit**
2. **almond** ⊃ **nut** ⊃ **seed** ⊃ **fruit**

The weight is added to each ancestor (**stone fruit**, **nut**,
**seed**, **fruit**, ...) once. That is, the weight is not added to
the convergent ancestor for **fruit** twice, but only once.


Calculating Information Content
-------------------------------

.. autofunction:: information_content
.. autofunction:: synset_probability


Computing Corpus Weights
------------------------

If pre-computed weights are not available for a wordnet or for some
domain, they can be computed given a corpus and a wordnet.

The corpus is an iterable of words. For large corpora it may help to
use a generator for this iterable, but the entire vocabulary (i.e.,
unique words and counts) will be held at once in memory. Multi-word
expressions are also possible if they exist in the wordnet. For
instance, the Princeton WordNet has *stone fruit*, with a single space
delimiting the words, as an entry.

The :class:`wn.Wordnet` object must be instantiated with a single
lexicon, although it may have expand-lexicons for relation
traversal. For best results, the wordnet should use a lemmatizer to
help it deal with inflected wordforms from running text.

.. autofunction:: compute


Reading Pre-computed Information Content Files
----------------------------------------------

The :func:`load` function reads pre-computed information content
weights files as used by the `WordNet::Similarity
<http://wn-similarity.sourceforge.net/>`_ Perl module or the `NLTK
<http://www.nltk.org/>`_ Python package. These files are computed for
a specific version of a wordnet using the synset offsets from the
`WNDB <https://wordnet.princeton.edu/documentation/wndb5wn>`_ format,
which Wn does not use. These offsets therefore must be converted into
an identifier that matches those used by the wordnet. By default,
:func:`load` uses the lexicon identifier from its *wordnet* argument
with synset offsets (padded with 0s to make 8 digits) and
parts-of-speech from the weights file to format an identifier, such as
``pwn-00001174-n``. For wordnets that use a different identifier
scheme, the *get_synset_id* parameter of :func:`load` can be given a
callable created with :func:`wn.util.synset_id_formatter`. It can also
be given another callable with the same signature as shown below:

.. code-block:: python

   get_synset_id(*, offset: int, pos: str) -> str

.. warning::

   The weights files are only valid for the version of wordnet for
   which they were created. Files created for the Princeton WordNet
   3.0 do not work for the Princeton WordNet 3.1 because the offsets
   used in its identifiers are different, although the *get_synset_id*
   parameter of :func:`load` could be given a function that performs a
   suitable mapping. Some `Open Multilingual Wordnet
   <https://github.com/globalwordnet/OMW>`_ wordnets use the Princeton
   WordNet 3.0 offsets in their identifiers and can therefore
   technically use the weights, but this usage is discouraged because
   the distributional properties of text in another language and the
   structure of the other wordnet will not be compatible with that of
   the Princeton WordNet. For these cases, it is recommended to
   compute new weights using :func:`compute`.

.. autofunction:: load
