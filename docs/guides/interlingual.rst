Interlingual Queries
====================

This guide explains how interlingual queries work within Wn.  To get
started, you'll need at least two lexicons that use interlingual
indices (ILIs).  For this guide, we'll use the Open English WordNet
(``oewn:2021``), the Open German WordNet (``odenet:1.4``), also
known as OdeNet, and the Japanese wordnet (``omw-ja:1.4``).

  >>> import wn
  >>> wn.download('oewn:2021')
  >>> wn.download('odenet:1.4')
  >>> wn.download('omw-ja:1.4')

We will query these wordnets with the following :class:`~wn.Wordnet`
objects:

  >>> en = wn.Wordnet('oewn:2021')
  >>> de = wn.Wordnet('odenet:1.4')

The object for the Japanese wordnet will be discussed and created
below, in :ref:`cross-lingual-relation-traversal`.

What are Interlingual Indices?
------------------------------

It is common for users of the `Princeton WordNet
<https://wordnet.princeton.edu/>`_ to refer to synsets by their `WNDB
<https://wordnet.princeton.edu/documentation/wndb5wn>`_ offset and
type, but this is problematic because the offset is a byte-offset in
the wordnet data files and it will differ for wordnets in other
languages and even between versions of the same wordnet.  Interlingual
indices (ILIs) address this issue by providing stable identifiers for
concepts, whether for a synset across versions of a wordnet or across
languages.

The idea of ILIs was proposed by [Vossen99]_ and it came to fruition
with the release of the Collaborative Interlingual Index (CILI;
[Bond16]_).  CILI therefore represents an instance of, and a namespace
for, ILIs. There could, in theory, be alternative indexes for
particular domains (e.g., names of people or places), but currently
there is only the one.

As an example, the synset for *apricot* (fruit) in WordNet 3.0 is
``07750872-n``, but it is ``07766848-n`` in WordNet 3.1. In OdeNet
1.4, which is not released in the WNDB format and therefore doesn't
use offsets at all, it is ``13235-n`` for the equivalent word
(*Aprikose*). However, all three use the same ILI: ``i77784``.

Not every synset is guaranteed to be associated with an ILI, and some
have the special value ``in`` indicates that the project is proposing
that a new ILI be created in the CILI project for the concept, but
until that happens it cannot be used in interlingual queries.

.. [Vossen99]
   Vossen, Piek, Wim Peters, and Julio Gonzalo.
   "Towards a universal index of meaning."
   In Proceedings of ACL-99 workshop, Siglex-99, standardizing lexical resources, pp. 81-90.
   University of Maryland, 1999.

.. [Bond16]
   Bond, Francis, Piek Vossen, John Philip McCrae, and Christiane Fellbaum.
   "CILI: the Collaborative Interlingual Index."
   In Proceedings of the 8th Global WordNet Conference (GWC), pp. 50-57. 2016.

Using Interlingual Indices
--------------------------

For synsets that have an associated ILI, you can retrieve it via the
:data:`wn.Synset.ili` accessor:

  >>> apricot = en.synsets('apricot')[1]
  >>> apricot.ili
  ILI('i77784')

From this object you can get various properties of the ILI, such as
the ID as a string, its status, and its definition, but if you have
not added CILI to Wn's database it will not be very informative:

  >>> apricot.ili.id
  'i77784'
  >>> apricot.ili.status
  'presupposed'
  >>> apricot.ili.definition() is None
  True

The ``presupposed`` status means that the ILI was in use by a lexicon,
but there is no other source of truth for the index.  CILI can be
downloaded just like a lexicon:

  >>> wn.download('cili:1.0')

Now the status and definition should be more useful:

  >>> apricot.ili.status
  'active'
  >>> apricot.ili.definition()
  'downy yellow to rosy-colored fruit resembling a small peach'

ILI IDs may be used to lookup synsets:

  >>> Aprikose = de.synsets(ili=apricot.ili.id)[0]
  >>> Aprikose.lemmas()
  ['Marille', 'Aprikose']


Translating Words, Senses, and Synsets
--------------------------------------

Rather than manually inserting the ILI IDs into Wn's lookup functions
as shown above, Wn provides the :meth:`wn.Synset.translate` method to
make it easier:

  >>> apricot.translate(lexicon='odenet:1.4')
  [Synset('odenet-13235-n')]

The method returns a list for two reasons: first, it's not guaranteed
that the target lexicon has only one synset with the ILI and, second,
you can translate to more than one lexicon at a time.

:class:`~wn.Sense` objects also have a :meth:`~wn.Sense.translate`
method, returning a list of senses instead of synsets:

  >>> de_senses = apricot.senses()[0].translate(lexicon='odenet:1.4')
  >>> [s.word().lemma() for s in de_senses]
  ['Marille', 'Aprikose']

:class:`~wn.Word` have a :meth:`~wn.Word.translate` method, too, but
it works a bit differently. Since each word may be part of multiple
synsets, the method returns a mapping of each word sense to the list
of translated words:

  >>> result = en.words('apricot')[0].translate(lexicon='odenet:1.4')
  >>> for sense, de_words in result.items():
  ...     print(sense, [w.lemma() for w in de_words])
  ... 
  Sense('oewn-apricot__1.20.00..') []
  Sense('oewn-apricot__1.13.00..') ['Marille', 'Aprikose']
  Sense('oewn-apricot__1.07.00..') ['lachsrosa', 'lachsfarbig', 'in Lachs', 'lachsfarben', 'lachsrot', 'lachs']

The three senses above are for *apricot* as a tree, a fruit, and a
color. OdeNet does not have a synset for apricot trees, or it has one
not associated with the appropriate ILI, and therefore it could not
translate any words for that sense.


.. _cross-lingual-relation-traversal:

Cross-lingual Relation Traversal
--------------------------------

ILIs have a second use in Wn, which is relation traversal for wordnets
that depend on other lexicons, i.e., those created with the *expand*
methodology. These wordnets, such as many of those in the `Open
Multilingual Wordnet <https://github.com/omwn/>`_, do not include
synset relations on their own as they were built using the English
WordNet as their taxonomic scaffolding. Trying to load such a lexicon
when the lexicon it requires is not added to the database presents a
warning to the user:

  >>> ja = wn.Wordnet('omw-ja:1.4')
  [...] WnWarning: lexicon dependencies not available: omw-en:1.4
  >>> ja.expanded_lexicons()
  []

.. warning::

   Do not rely on the presence of a warning to determine if the
   lexicon has its expand lexicon loaded. Python's default warning
   filter may only show the warning the first time it is
   encountered. Instead, inspect :meth:`wn.Wordnet.expanded_lexicons`
   to see if it is non-empty.

When a dependency is unmet, Wn only issues a warning, not an error,
and you can continue to use the lexicon as it is, but it won't be
useful for exploring relations such as hypernyms and hyponyms:

  >>> anzu = ja.synsets(ili='i77784')[0]
  >>> anzu.lemmas()
  ['アンズ', 'アプリコット', '杏']
  >>> anzu.hypernyms()
  []

One way to resolve this issue is to install the lexicon it requires:

  >>> wn.download('omw-en:1.4')
  >>> ja = wn.Wordnet('omw-ja:1.4')  # no warning
  >>> ja.expanded_lexicons()
  [<Lexicon omw-en:1.4 [en]>]

Wn will detect the dependency and load ``omw-en:1.4`` as the *expand*
lexicon for ``omw-ja:1.4`` when the former is in the database. You may
also specify an expand lexicon manually, even one that isn't the
specified dependency:

  >>> ja = wn.Wordnet('omw-ja:1.4', expand='oewn:2021')  # no warning
  >>> ja.expanded_lexicons()
  [<Lexicon oewn:2021 [en]>]

In this case, the Open English WordNet is an actively-developed fork
of the lexicon that ``omw-ja:1.4`` depends on, and it should contain
all the relations, so you'll see little difference between using it
and ``omw-en:1.4``. This works because the relations are found using
ILIs and not synset offsets. You may still prefer to use the specified
dependency if you have strict compatibility needs, such as for
experiment reproducibility and/or compatibility with the `NLTK
<https://nltk.org>`_. Using some other lexicon as the expand lexicon
may yield very different results. For instance, ``odenet:1.4`` is much
smaller than the English wordnets and has fewer relations, so it would
not be a good substitute for ``omw-ja:1.4``'s expand lexicon.

When an appropriate expand lexicon is loaded, relations between
synsets, such as hypernyms, are more likely to be present:

  >>> anzu = ja.synsets(ili='i77784')[0]  # recreate the synset object
  >>> anzu.hypernyms()
  [Synset('omw-ja-07705931-n')]
  >>> anzu.hypernyms()[0].lemmas()
  ['果物']
  >>> anzu.hypernyms()[0].translate(lexicon='oewn:2021')[0].lemmas()
  ['edible fruit']
