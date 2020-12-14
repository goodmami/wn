Migrating from the NLTK
=======================

This guide is for users of the `NLTK <https://www.nltk.org/>`_\ 's
``nltk.corpus.wordnet`` module who are migrating to Wn. It is not
guaranteed that Wn will produce the same results as the NLTK's module,
but with some care its behavior can be very similar.

Overview
--------

One important thing to note is that Wn will search all wordnets in the
database by default where the NLTK would only search the English.

>>> from nltk.corpus import wordnet as nltk_wn
>>> nltk_wn.synsets('chat')                 # only English
>>> nltk_wn.synsets('chat', lang='fra')     # only French
>>> import wn
>>> wn.synsets('chat')                      # all wordnets
>>> wn.synsets('chat', lang='fr')           # only French

With Wn it helps to create a :class:`wn.Wordnet` object to pre-filter
the results by language or lexicon.

>>> pwn = wn.Wordnet('pwn', '3.0')
>>> pwn.synsets('chat')                     # only Princeton WordNet 3.0

Equivalent Operations
---------------------

The following table lists equivalent API calls for the NLTK's wordnet
module and Wn assuming the respective modules have been instantiated
(in separate Python sessions) as follows:

NLTK:

>>> from nltk.corpus import wordnet as wn
>>> ss = wn.synsets("chat", pos="v")[0]

Wn:

>>> import wn
>>> pwn = wn.Wordnet('pwn', '3.0')
>>> ss = pwn.synsets("chat", pos="v")[0]

.. default-role:: python

Primary Queries
'''''''''''''''

=========================================  =========================================
NLTK                                       Wn
=========================================  =========================================
`wn.langs()`                               `[lex.language for lex in wn.lexicons()]`
`wn.lemmas("chat")`                        --
--                                         `pwn.words("chat")`
--                                         `pwn.senses("chat")`
`wn.synsets("chat")`                       `pwn.synsets("chat")`
`wn.synsets("chat", pos="v")`              `pwn.synsets("chat", pos="v")`
`wn.all_synsets()`                         `pwn.synsets()`
`wn.all_synsets(pos="v")`                  `pwn.synsets(pos="v")`
`wn.all_lemma_names()`                     `[w.lemma() for w in pwn.words()]`
=========================================  =========================================

Synsets -- Basic
''''''''''''''''

===================  =================
NLTK                 Wn
===================  =================
`ss.lemmas()`        --
--                   `ss.senses()`
--                   `ss.words()`
`ss.lemmas_names()`  `ss.lemmas()`
`ss.definition()`    `ss.definition()`
`ss.examples()`      `ss.examples()`
`ss.pos()`           `ss.pos`
===================  =================

Synsets -- Relations
''''''''''''''''''''

==========================================  =====================================
NLTK                                        Wn
==========================================  =====================================
`ss.hypernyms()`                            `ss.get_related("hypernym")`
`ss.instance_hypernyms()`                   `ss.get_related("instance_hypernym")`
`ss.hypernyms() + ss.instance_hypernyms()`  `ss.hypernyms()`
`ss.hyponyms()`                             `ss.get_related("hyponym")`
`ss.member_holonyms()`                      `ss.get_related("holo_member")`
`ss.member_meronyms()`                      `ss.get_related("mero_member")`
`ss.closure(lambda x: x.hypernyms())`       `ss.closure("hypernym")`
==========================================  =====================================

Synsets -- Taxonomic Structure
''''''''''''''''''''''''''''''

================================  =========================================================
NLTK                              Wn
================================  =========================================================
`ss.min_depth()`                  `ss.min_depth()`
`ss.max_depth()`                  `ss.max_depth()`
`ss.hypernym_paths()`             `[list(reversed([ss] + p)) for p in ss.hypernym_paths()]`
`ss.common_hypernyms(ss)`         `ss.common_hypernyms(ss)`
`ss.lowest_common_hypernyms(ss)`  `ss.lowest_common_hypernyms(ss)`
`ss.shortest_path_distance(ss)`   `len(ss.shortest_path(ss))`
================================  =========================================================

.. reset default role
.. default-role::

(these tables are incomplete)
