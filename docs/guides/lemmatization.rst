
Lemmatization and Normalization
===============================

Wn provides two methods for expanding queries: lemmatization_ and
normalization_\ . Wn also has a setting that allows `alternative forms
<alternative-forms_>`_ stored in the database to be included in
queries.

.. seealso::

   The :mod:`wn.morphy` module is a basic English lemmatizer included
   with Wn.

.. _lemmatization:

Lemmatization
-------------

When querying a wordnet with wordforms from natural language text, it
is important to be able to find entries for inflected forms as the
database generally contains only lemmatic forms, or *lemmas* (or
*lemmata*, if you prefer irregular plurals).

>>> import wn
>>> ewn = wn.Wordnet('ewn:2020')
>>> ewn.words('plurals')  # no results
[]
>>> ewn.words('plural')
[Word('ewn-plural-n'), Word('ewn-plural-a')]

Lemmas are sometimes called *citation forms* or *dictionary forms* as
they are often used as the head words in dictionary entries. In
Natural Language Processing (NLP), *lemmatization* is a technique
where a possibly inflected word form is transformed to yield a
lemma. In Wn, this concept is generalized somewhat to mean a
transformation that yields a form matching wordforms stored in the
database. For example, the English word *sparrows* is the plural
inflection of *sparrow*, while the word *leaves* is ambiguous between
the plural inflection of the nouns *leaf* and *leave* and the
3rd-person singular inflection of the verb *leave*.

For tasks where high-accuracy is needed, wrapping the wordnet queries
with external tools that handle tokenization, lemmatization, and
part-of-speech tagging will likely yield the best results as this
method can make use of word context. That is, something like this:

.. code-block:: python

   for lemma, pos in fancy_shmancy_analysis(corpus):
       synsets = w.synsets(lemma, pos=pos)

For modest needs, however, Wn provides a way to integrate basic
lemmatization directly into the queries.

Lemmatization in Wn works as follows: if a :class:`wn.Wordnet` object
is instantiated with a *lemmatizer* argument, then queries involving
wordforms (e.g., :meth:`wn.Wordnet.words`, :meth:`wn.Wordnet.senses`,
:meth:`wn.Wordnet.synsets`) will first lemmatize the wordform and then
check all resulting wordforms and parts of speech against the
database as successive queries.

Lemmatization Functions
'''''''''''''''''''''''

The *lemmatizer* argument of :class:`wn.Wordnet` is a callable that
takes two string arguments: (1) the original wordform, and (2) a
part-of-speech or :python:`None`. It returns a dictionary mapping
parts-of-speech to sets of lemmatized wordforms. The signature is as
follows:

.. code-block:: python

   lemmatizer(s: str, pos: Optional[str]) -> Dict[Optional[str], Set[str]]

The part-of-speech may be used by the function to determine which
morphological rules to apply. If the given part-of-speech is
:python:`None`, then it is not specified and any rule may apply. A
lemmatizer that only deinflects should not change any specified
part-of-speech, but this is not a requirement, and a function could be
provided that undoes derivational morphology (e.g., *democratic* →
*democracy*).

Querying With Lemmatization
'''''''''''''''''''''''''''

As the needs of lemmatization differs from one language to another, Wn
does not provide a lemmatizer by default, and therefore it is
unavailable to the convenience functions :func:`wn.words`,
:func:`wn.senses`, and :func:`wn.synsets`. A lemmatizer can be added
to a :class:`wn.Wordnet` object. For example, using :mod:`wn.morphy`:

>>> import wn
>>> from wn.morphy import Morphy
>>> ewn = wn.Wordnet('ewn:2020', lemmatizer=Morphy())
>>> ewn.words('sparrows')
[Word('ewn-sparrow-n')]
>>> ewn.words('leaves')
[Word('ewn-leaf-n'), Word('ewn-leave-n'), Word('ewn-leave-v')]


Querying Without Lemmatization
''''''''''''''''''''''''''''''

When lemmatization is not used, inflected terms may not return any
results:

>>> ewn = wn.Wordnet('ewn:2020')
>>> ewn.words('sparrows')
[]
>>> ewn.words('leaves')
[]

Depending on the lexicon, there may be situations where results are
returned for inflected lemmas, such as when the inflected form is
lexicalized as its own entry:

>>> ewn.words('glasses')
[Word('ewn-glasses-n')]

Or if the lexicon lists the inflected form as an alternative form. For
example, the English Wordnet lists irregular inflections as
alternative forms:

>>> ewn.words('lemmata')
[Word('ewn-lemma-n')]

See below for excluding alternative forms from such queries.

.. _alternative-forms:

Alternative Forms in the Database
---------------------------------

A lexicon may include alternative forms in addition to lemmas for each
word, and by default these are included in queries. What exactly is
included as an alternative form depends on the lexicon. The English
Wordnet, for example, adds irregular inflections (or "exceptional
forms"), while the Japanese Wordnet includes the same word in multiple
orthographies (original, hiragana, katakana, and two romanizations).
For the English Wordnet, this means that you might get basic
lemmatization for irregular forms only:

>>> ewn = wn.Wordnet('ewn:2020')
>>> ewn.words('learnt', pos='v')
[Word('ewn-learn-v')]
>>> ewn.words('learned', pos='v')
[]

If this is undesirable, the alternative forms can be excluded from
queries with the *search_all_forms* parameter:

>>> ewn = wn.Wordnet('ewn:2020', search_all_forms=False)
>>> ewn.words('learnt', pos='v')
[]
>>> ewn.words('learned', pos='v')
[]


.. _normalization:

Normalization
-------------

While lemmatization deals with morphological variants of words,
normalization handles minor orthographic variants. Normalized forms,
however, may be invalid as wordforms in the target language, and as
such they are only used behind the scenes for query expansion and not
presented to users. For instance, a user might attempt to look up
*résumé* in the English wordnet, but the wordnet only contains the
form without diacritics: *resume*. With strict string matching, the
entry would not be found using the wordform in the query. By
normalizing the query word, the entry can be found. Similarly in the
Spanish wordnet, *año* (year) and *ano* (anus) are two different
words. A user who types *año* likely does not want to get results for
*ano*, but one who types *ano* may be a non-Spanish speaker who is
unaware of the missing diacritic or does not have an input method that
allows them to type the diacritic, so this query would return both
entries by matching against the normalized forms in the database. Wn
handles all of these use cases.

When a lexicon is added to the database, potentially two wordforms are
inserted for every one in the lexicon: the original wordform and a
normalized form. When querying against the database, the original
query string is first compared with the original wordforms and, if
normalization is enabled, with the normalized forms in the database as
well. If this first attempt yields no results and if normalization is
enabled, the query string is normalized and tried again.

Normalization Functions
'''''''''''''''''''''''

The normalized form is obtained from a *normalizer* function, passed
as an argument to :class:`wn.Wordnet`, that takes a single string
argument and returns a string. That is, a function with the following
signature:

.. code-block:: python

   normalizer(s: str) -> str

While custom *normalizer* functions could be used, in practice the
choice is either the default normalizer or :python:`None`. The default
normalizer works by downcasing the string and performing NFKD_
normalization to remove diacritics. If the normalized form is the same
as the original, only the original is inserted into the database.

.. table:: Examples of normalization
   :align: center

   =============  ===============
   Original Form  Normalized Form
   =============  ===============
   résumé         resume
   año            ano
   San José       san jose
   ハラペーニョ   ハラヘーニョ
   =============  ===============

.. _NFKD: https://en.wikipedia.org/wiki/Unicode_equivalence#Normal_forms

Querying With Normalization
'''''''''''''''''''''''''''

By default, normalization is enabled when a :class:`wn.Wordnet` is
created. Enabling normalization does two things: it allows queries to
check the original wordform in the query against the normalized forms
in the database and, if no results are returned in the first step, it
allows the queried wordform to be normalized as a back-off technique.

>>> ewn = wn.Wordnet('ewn:2020')
>>> ewn.words('résumé')
[Word('ewn-resume-v'), Word('ewn-resume-n')]
>>> spa = wn.Wordnet('spawn:1.3+omw')
>>> spa.words('año')
[Word('spawn-lex57514')]
>>> spa.words('ano')
[Word('spawn-lex34109'), Word('spawn-lex57514')]

.. note::

   Users may supply a custom *normalizer* function to the
   :class:`wn.Wordnet` object, but currently this is discouraged as
   the result is unlikely to match normalized forms in the database
   and there is not yet a way to customize the normalization of forms
   added to the database.

Querying Without Normalization
''''''''''''''''''''''''''''''

Normalization can be disabled by passing :python:`None` as the
argument of the *normalizer* parameter of :class:`wn.Wordnet`. The
queried wordform will not be checked against normalized forms in the
database and neither will it be normalized as a back-off technique.

>>> ewn = wn.Wordnet('ewn:2020', normalizer=None)
>>> ewn.words('résumé')
[]
>>> spa = wn.Wordnet('spawn:1.3+omw', normalizer=None)
>>> spa.words('año')
[Word('spawn-lex57514')]
>>> spa.words('ano')
[Word('spawn-lex34109')]

.. note::

   It is not possible to disable normalization for the convenience
   functions :func:`wn.words`, :func:`wn.senses`, and
   :func:`wn.synsets`.
