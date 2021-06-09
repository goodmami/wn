Basic Usage
===========

.. seealso::

   This document covers the basics of querying wordnets, filtering
   results, and performing secondary queries on the results. For
   adding, removing, or inspecting lexicons, see :doc:`lexicons`. For
   more information about interlingual queries, see
   :doc:`interlingual`.

For the most basic queries, Wn provides several module functions for
retrieving words, senses, and synsets:

>>> import wn
>>> wn.words('pike')
[Word('ewn-pike-n')]
>>> wn.senses('pike')
[Sense('ewn-pike-n-03311555-04'), Sense('ewn-pike-n-07795351-01'), Sense('ewn-pike-n-03941974-01'), Sense('ewn-pike-n-03941726-01'), Sense('ewn-pike-n-02563739-01')]
>>> wn.synsets('pike')
[Synset('ewn-03311555-n'), Synset('ewn-07795351-n'), Synset('ewn-03941974-n'), Synset('ewn-03941726-n'), Synset('ewn-02563739-n')]

Once you start working with multiple wordnets, these simple queries
may return more than desired:

>>> wn.words('pike')
[Word('ewn-pike-n'), Word('wnja-n-66614')]
>>> wn.words('chat')
[Word('ewn-chat-n'), Word('ewn-chat-v'), Word('frawn-lex14803'), Word('frawn-lex21897')]

You can specify which language or lexicon you wish to query:

>>> wn.words('pike', lang='ja')
[Word('wnja-n-66614')]
>>> wn.words('chat', lexicon='frawn')
[Word('frawn-lex14803'), Word('frawn-lex21897')]

But it might be easier to create a :class:`~wn.Wordnet` object and use
it for queries:

>>> wnja = wn.Wordnet(lang='ja')
>>> wnja.words('pike')
[Word('wnja-n-66614')]
>>> frawn = wn.Wordnet(lexicon='frawn')
>>> frawn.words('chat')
[Word('frawn-lex14803'), Word('frawn-lex21897')]

In fact, the simple queries above implicitly create such a
:class:`~wn.Wordnet` object, but one that includes all installed
lexicons.


.. _primary-queries:

Primary Queries
---------------

The queries shown above are "primary" queries, meaning they are the
first step in a user's interaction with a wordnet. Operations
performed on the resulting objects are then `secondary
queries`_. Primary queries optionally take several fields for
filtering the results, namely the word form and part of
speech. Synsets may also be filtered by an interlingual index (ILI).

Searching for Words
'''''''''''''''''''

The :func:`wn.words()` function returns a list of :class:`~wn.Word`
objects that match the given word form or part of speech:

>>> wn.words('pencil')
[Word('ewn-pencil-n'), Word('ewn-pencil-v')]
>>> wn.words('pencil', pos='v')
[Word('ewn-pencil-v')]

Calling the function without a word form will return all words in the
database:

>>> len(wn.words())
311711
>>> len(wn.words(pos='v'))
29419
>>> len(wn.words(pos='v', lexicon='ewn'))
11595

If you know the word identifier used by a lexicon, you can retrieve
the word directly with the :func:`wn.word()` function. Identifiers are
guaranteed to be unique within a single lexicon, but not across
lexicons, so it's best to call this function from an instantiated
:class:`~wn.Wordnet` object or with the ``lexicon`` parameter
specified. If multiple words are found when querying multiple
lexicons, only the first is returned.

>>> wn.word('ewn-pencil-n', lexicon='ewn')
Word('ewn-pencil-n')


Searching for Senses
''''''''''''''''''''

The :func:`wn.senses()` and :func:`wn.sense()` functions behave
similarly to :func:`wn.words()` and :func:`wn.word()`, except that
they return matching :class:`~wn.Sense` objects.

>>> wn.senses('plow', pos='n')
[Sense('ewn-plow-n-03973894-01')]
>>> wn.sense('ewn-plow-v-01745745-01')
Sense('ewn-plow-v-01745745-01')

Senses represent a relationship between a :class:`~wn.Word` and a
:class:`~wn.Synset`. Seen as an edge between nodes, senses are often
given less prominence than words or synsets, but they are the natural
locus of several interesting features such as sense relations (e.g.,
for derived words) and the natural level of representation for
translations to other languages.

Searching for Synsets
'''''''''''''''''''''

The :func:`wn.synsets()` and :func:`wn.synset()` functions are like
those above but allow the ``ili`` parameter for filtering by
interlingual index, which is useful in interlingual queries:

>>> wn.synsets('scepter')
[Synset('ewn-14467142-n'), Synset('ewn-07282278-n')]
>>> wn.synset('ewn-07282278-n').ili
'i74874'
>>> wn.synsets(ili='i74874')
[Synset('ewn-07282278-n'), Synset('wnja-07267573-n'), Synset('frawn-07267573-n')]


Secondary Queries
-----------------

Once you have gotten some results from a primary query, you can
perform operations on the :class:`~wn.Word`, :class:`~wn.Sense`, or
:class:`~wn.Synset` objects to get at further information in the
wordnet.

Exploring Words
'''''''''''''''

Here are some of the things you can do with :class:`~wn.Word` objects:

>>> w = wn.words('goose')[0]
>>> w.pos  # part of speech
'n'
>>> w.forms()  # other word forms (e.g., irregular inflections)
['goose', 'geese']
>>> w.lemma()  # canonical form
'goose'
>>> w.derived_words()
[Word('ewn-gosling-n'), Word('ewn-goosy-s'), Word('ewn-goosey-s')]
>>> w.senses()
[Sense('ewn-goose-n-01858313-01'), Sense('ewn-goose-n-10177319-06'), Sense('ewn-goose-n-07662430-01')]
>>> w.synsets()
[Synset('ewn-01858313-n'), Synset('ewn-10177319-n'), Synset('ewn-07662430-n')]

Since translations of a word into another language depend on the sense
used, :meth:`Word.translate <wn.Word.translate>` returns a dictionary
mapping each sense to words in the target language:

>>> for sense, ja_words in w.translate(lang='ja').items():
...     print(sense, ja_words)
... 
Sense('ewn-goose-n-01858313-01') [Word('wnja-n-1254'), Word('wnja-n-33090'), Word('wnja-n-38995')]
Sense('ewn-goose-n-10177319-06') []
Sense('ewn-goose-n-07662430-01') [Word('wnja-n-1254')]


Exploring Senses
''''''''''''''''

Compared to :class:`~wn.Word` and :class:`~wn.Synset` objects, there
are relatively few operations available on :class:`~wn.Sense`
objects. Sense relations and translations, however, are important
operations on senses.

>>> s = wn.senses('dark', pos='n')[0]
>>> s.word()    # each sense links to a single word
Word('ewn-dark-n')
>>> s.synset()  # each sense links to a single synset
Synset('ewn-14007000-n')
>>> s.get_related('antonym')
[Sense('ewn-light-n-14006789-01')]
>>> s.get_related('derivation')
[Sense('ewn-dark-a-00273948-01')]
>>> s.translate(lang='fr')  # translation returns a list of senses
[Sense('frawn-lex52992--13983515-n')]
>>> s.translate(lang='fr')[0].word().lemma()
'obscurité'


Exploring Synsets
'''''''''''''''''

Many of the operations people care about happen on synsets, such as
hierarchical relations and metrics.

>>> ss = wn.synsets('hound', pos='n')[0]
>>> ss.senses()
[Sense('ewn-hound-n-02090203-01'), Sense('ewn-hound_dog-n-02090203-02')]
>>> ss.words()
[Word('ewn-hound-n'), Word('ewn-hound_dog-n')]
>>> ss.lemmas()
['hound', 'hound dog']
>>> ss.definition()
'any of several breeds of dog used for hunting typically having large drooping ears'
>>> ss.hypernyms()
[Synset('ewn-02089774-n')]
>>> ss.hypernyms()[0].lemmas()
['hunting dog']
>>> len(ss.hyponyms())
20
>>> ss.hyponyms()[0].lemmas()
['Afghan', 'Afghan hound']
>>> ss.max_depth()
15
>>> ss.shortest_path(wn.synsets('dog', pos='n')[0])
[Synset('ewn-02090203-n'), Synset('ewn-02089774-n'), Synset('ewn-02086723-n')]
>>> ss.translate(lang='fr')  # translation returns a list of synsets
[Synset('frawn-02087551-n')]
>>> ss.translate(lang='fr')[0].lemmas()
['chien', 'chien de chasse']


Filtering by Language
---------------------

The ``lang`` parameter of :func:`wn.words()`, :func:`wn.senses()`,
:func:`wn.synsets()`, and :class:`~wn.Wordnet` allows a single `BCP 47
<https://en.wikipedia.org/wiki/IETF_language_tag>`_ language
code. When this parameter is used, only entries in the specified
language will be returned.

>>> import wn
>>> wn.words('chat')
[Word('ewn-chat-n'), Word('ewn-chat-v'), Word('frawn-lex14803'), Word('frawn-lex21897')]
>>> wn.words('chat', lang='fr')
[Word('frawn-lex14803'), Word('frawn-lex21897')]

If a language code not used by any lexicon is specified, a
:exc:`wn.Error` is raised.


Filtering by Lexicon
--------------------

The ``lexicon`` parameter of :func:`wn.words()`, :func:`wn.senses()`,
:func:`wn.synsets()`, and :class:`~wn.Wordnet` take a string of
space-delimited :ref:`lexicon specifiers
<lexicon-specifiers>`. Entries in a lexicon whose ID matches one of
the lexicon specifiers will be returned. For these, the following
rules are used:

- A full ``id:version`` string (e.g., ``ewn:2020``) selects a specific
  lexicon
- Only a lexicon ``id`` (e.g., ``ewn``) selects the most recently
  added lexicon with that ID
- A star ``*`` may be used to match any lexicon; a star may not
  include a version

>>> wn.words('chat', lexicon='ewn:2020')
[Word('ewn-chat-n'), Word('ewn-chat-v')]
>>> wn.words('chat', lexicon='wnja')
[]
>>> wn.words('chat', lexicon='wnja frawn')
[Word('frawn-lex14803'), Word('frawn-lex21897')]
