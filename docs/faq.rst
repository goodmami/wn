FAQ
===

Is Wn related to the NLTK's `nltk.corpus.wordnet` module?
---------------------------------------------------------

Only in spirit. There was an effort to develop the NLTK's module as a
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
:doc:`guides/nltk-migration` for more information.

Where are the ``Lemma`` objects? What are ``Word`` and ``Sense`` objects?
-------------------------------------------------------------------------

While senses are essentially links between words (also called "lexical
entries") and synsets, they may contain metadata and be the source or
target of sense relations, so in some ways they are more like nodes
than edges when the wordnet is viewed as a graph. The NLTK chose to
conflate words and senses into a single object called a ``Lemma``, but
Wn keeps them separate. Wn also has an unrelated concept called a
"lemma", but it is merely the canonical form of a word.

Why don't all wordnets share the same synsets?
----------------------------------------------

The `Open Multilingual Wordnet <https://lr.soh.ntu.edu.sg/omw/omw>`_
(OMW) contains wordnets for many languages created using the *expand*
methodology [VOSSEN1998]_, where non-English wordnets provide words on
top of the Princeton WordNet's synset structure. This allows new
wordnets to be built in much less time than starting from scratch, but
with a few drawbacks, such as that words cannot be added if they do
not have a synset in the Princeton WordNet, and that it is difficult
to version the wordnets independently (e.g., for reproducibility of
experiments involving wordnet data) as all are interconnected. Wn,
therefore, creates new synsets for each wordnet added to its database,
and synsets then specify which resource they belong to. Queries can
specify which resources may be examined. Also see
:doc:`guides/interlingual`.

Why does Wn's database get so big?
----------------------------------

The Princeton WordNet 3.0 takes about 104 MiB of disk space in Wn's
database, which is only about 6 MiB more than it takes as a `WN-LMF
XML <https://globalwordnet.github.io/schemas/>`_ file. The NLTK,
however, uses the obsolete WNDB format which is more compact,
requiring only 35 MiB of disk space. The difference with the Open
Multilingual Wordnet 1.3 is more striking: it takes about 466 MiB of
disk space in the database, but only 49 MiB in the NLTK. Part of the
difference here is that the OMW files in the NLTK are simple
tab-separated-value files listing only the words added to each synset
for each language. In addition, Wn creates new synsets for each
wordnet added (see the previous question). One more reason is that Wn
creates various indexes in the database for efficient lookup.


.. [VOSSEN1998] Piek Vossen. 1998. *Introduction to EuroWordNet.* Computers and the Humanities, 32(2): 73--89.
