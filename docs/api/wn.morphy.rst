
wn.morphy
=========

.. automodule:: wn.morphy

.. seealso::

   The Princeton WordNet `documentation
   <https://wordnet.princeton.edu/documentation/morphy7wn>`_ describes
   the original implementation of Morphy.

   The :doc:`../guides/lemmatization` guide describes how Wn handles
   lemmatization in general.


Initialized and Uninitialized Morphy
------------------------------------

There are two ways of using Morphy in Wn: initialized and
uninitialized.

Unintialized Morphy is a simple callable that returns lemma
*candidates* for some given wordform. That is, the results might not
be valid lemmas, but this is not a problem in practice because
subsequent queries against the database will filter out the invalid
ones. This callable is obtained by creating a :class:`Morphy` object
with no arguments:

>>> from wn import morphy
>>> m = morphy.Morphy()

As an uninitialized Morphy cannot predict which lemmas in the result
are valid, it always returns the original form and any transformations
it can find for each part of speech:

>>> m('lemmata', pos='n')  # exceptional form
{'n': {'lemmata'}}
>>> m('lemmas', pos='n')   # regular morphology with part-of-speech
{'n': {'lemma', 'lemmas'}}
>>> m('lemmas')            # regular morphology for any part-of-speech
{None: {'lemmas'}, 'n': {'lemma'}, 'v': {'lemma'}}
>>> m('wolves')            # invalid forms may be returned
{None: {'wolves'}, 'n': {'wolf', 'wolve'}, 'v': {'wolve', 'wolv'}}


This lemmatizer can also be used with a :class:`wn.Wordnet` object to
expand queries:

>>> import wn
>>> ewn = wn.Wordnet('ewn:2020')
>>> ewn.words('lemmas')
[]
>>> ewn = wn.Wordnet('ewn:2020', lemmatizer=morphy.Morphy())
>>> ewn.words('lemmas')
[Word('ewn-lemma-n')]

An initialized Morphy is created with a :class:`wn.Wordnet` object as
its argument. It then uses the wordnet to build lists of valid lemmas
and exceptional forms (this takes a few seconds). Once this is done,
it will only return lemmas it knows about:

>>> ewn = wn.Wordnet('ewn:2020')
>>> m = morphy.Morphy(ewn)
>>> m('lemmata', pos='n')  # exceptional form
{'n': {'lemma'}}
>>> m('lemmas', pos='n')   # regular morphology with part-of-speech
{'n': {'lemma'}}
>>> m('lemmas')            # regular morphology for any part-of-speech
{'n': {'lemma'}}
>>> m('wolves')            # invalid forms are pre-filtered
{'n': {'wolf'}}

In order to use an initialized Morphy lemmatizer with a
:class:`wn.Wordnet` object, it must be assigned to the object after
creation:

>>> ewn = wn.Wordnet('ewn:2020')  # default: lemmatizer=None
>>> ewn.words('lemmas')
[]
>>> ewn.lemmatizer = morphy.Morphy(ewn)
>>> ewn.words('lemmas')
[Word('ewn-lemma-n')]

There is little to no difference in the results obtained from a
:class:`wn.Wordnet` object using an initialized or uninitialized
:class:`Morphy` object, but there may be slightly different
performance profiles for future queries.


Default Morphy Lemmatizer
-------------------------

As a convenience, an uninitialized Morphy lemmatizer is provided in
this module via the :data:`morphy` member.

.. data:: morphy

   A :class:`Morphy` object created without a :class:`wn.Wordnet`
   object.


The Morphy Class
----------------

.. autoclass:: Morphy
