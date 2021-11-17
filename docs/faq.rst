FAQ
===

Is Wn related to the NLTK's `nltk.corpus.wordnet` module?
---------------------------------------------------------

Only in spirit. There was an effort to develop the `NLTK`_\ 's module as a
standalone package (see https://github.com/nltk/wordnet/), but
development had slowed. Wn has the same broad goals and a similar API
as that standalone package, but fundamental architectural differences
demanded a complete rewrite, so Wn was created as a separate
project. With approval from the other package's maintainer, Wn
acquired the `wn <https://pypi.org/project/wn>`_ project on PyPI and
can be seen as its successor.

Is Wn compatible with the NLTK's module?
----------------------------------------

The API is intentionally similar, but not exactly the same (for
instance see the next question), and there are differences in the ways
that results are retrieved, particularly for non-English wordnets. See
:doc:`guides/nltk-migration` for more information. Also see
:ref:`princeton-wordnet`.

Where are the ``Lemma`` objects? What are ``Word`` and ``Sense`` objects?
-------------------------------------------------------------------------

Unlike the original `WNDB`_ data format of the original WordNet, the
`WN-LMF`_ XML format grants words (called *lexical entries* in WN-LMF
and a :class:`~wn.Word` object in Wn) and word senses
(:class:`~wn.Sense` in Wn) explicit, first-class status alongside
synsets.  While senses are essentially links between words and
synsets, they may contain metadata and be the source or target of
sense relations, so in some ways they are more like nodes than edges
when the wordnet is viewed as a graph. The `NLTK`_\ 's module, using
the WNDB format, combines the information of a word and a sense into a
single object called a ``Lemmas``. Wn also has an unrelated concept
called a :meth:`~wn.Word.lemma`, but it is merely the canonical form
of a word.

.. _princeton-wordnet:

Where is the Princeton WordNet data?
------------------------------------

The original English wordnet, named simply *WordNet* but often
referred to as the *Princeton WordNet* to better distinguish it from
other projects, is specifically the data distributed by Princeton in
the `WNDB`_ format. The `Open Multilingual Wordnet <OMW_>`_ (OMW)
packages an export of the WordNet data as the *OMW English Wordnet
based on WordNet 3.0* which is used by Wn (with the lexicon ID
``omw-en``). It also has a similar export for WordNet 3.1 data
(``omw-en31``). Both of these are highly compatible with the original
data and can be used as drop-in replacements.

Prior to Wn version 0.9 (and, correspondingly, prior to the `OMW
data`_ version 1.4), the ``pwn:3.0`` and ``pwn:3.1`` English wordnets
distributed by OMW were incorrectly called the *Princeton WordNet*
(for WordNet 3.0 and 3.1, respectively). From Wn version 0.9 (and from
version 1.4 of the OMW data), these are called the *OMW English
Wordnet based on WordNet 3.0/3.1* (``omw-en:1.4`` and
``omw-en31:1.4``, respectively). These lexicons are intentionally
compatible with the original WordNet data, and the 1.4 versions are
even more compatible than the previous ``pwn:3.0`` and ``pwn:3.1``
lexicons, so it is strongly recommended to use them over the previous
versions.

.. _OMW data: https://github.com/omwn/omw-data

Why don't all wordnets share the same synsets?
----------------------------------------------

The `Open Multilingual Wordnet <OMW_>`_ (OMW) contains wordnets for
many languages created using the *expand* methodology [VOSSEN1998]_,
where non-English wordnets provide words on top of the English
wordnet's synset structure. This allows new wordnets to be built in
much less time than starting from scratch, but with a few drawbacks,
such as that words cannot be added if they do not have a synset in the
English wordnet, and that it is difficult to version the wordnets
independently (e.g., for reproducibility of experiments involving
wordnet data) as all are interconnected. Wn, therefore, creates new
synsets for each wordnet added to its database, and synsets then
specify which resource they belong to. Queries can specify which
resources may be examined. Also see :doc:`guides/interlingual`.

Why does Wn's database get so big?
----------------------------------

The *OMW English Wordnet based on WordNet 3.0* takes about 114 MiB of
disk space in Wn's database, which is only about 8 MiB more than it
takes as a `WN-LMF`_ XML file. The `NLTK`_, however, uses the obsolete
`WNDB`_ format which is more compact, requiring only 35 MiB of disk
space. The difference with the Open Multilingual Wordnet 1.4 is more
striking: it takes about 659 MiB of disk space in the database, but
only 49 MiB in the NLTK. Part of the difference here is that the OMW
files in the NLTK are simple tab-separated-value files listing only
the words added to each synset for each language. In addition, Wn
creates new synsets for each wordnet added (see the previous
question). One more reason is that Wn creates various indexes in the
database for efficient lookup.

.. _NLTK: https://www.nltk.org/
.. _OMW: http://github.com/omwn
.. [VOSSEN1998] Piek Vossen. 1998. *Introduction to EuroWordNet.* Computers and the Humanities, 32(2): 73--89.
.. _Open English Wordnet 2021: https://en-word.net/
.. _WNDB: https://wordnet.princeton.edu/documentation/wndb5wn
.. _WN-LMF: https://globalwordnet.github.io/schemas/
