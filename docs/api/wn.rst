
wn
===

.. automodule:: wn

Lexicon Management Functions
----------------------------

.. autofunction:: download
.. autofunction:: add
.. autofunction:: remove

Wordnet Query Functions
-----------------------

.. autofunction:: word
.. autofunction:: words
.. autofunction:: sense
.. autofunction:: senses
.. autofunction:: synset
.. autofunction:: synsets
.. autofunction:: lexicons

The WordNet Class
-----------------

.. autoclass:: WordNet

   .. attribute:: lgcode

      The value of the language-code filter used in object
      instantiation, if any.

   .. automethod:: word
   .. automethod:: words
   .. automethod:: sense
   .. automethod:: senses
   .. automethod:: synset
   .. automethod:: synsets
   .. automethod:: lexicons
   .. automethod:: expanded_lexicons

The Word Class
--------------

.. autoclass:: Word

   .. attribute:: id

      The identifier used within a lexicon.

   .. attribute:: pos

      The part of speech of the Word.

   .. automethod:: lemma
   .. automethod:: forms
   .. automethod:: senses
   .. automethod:: synsets
   .. automethod:: derived_words
   .. automethod:: translate


The Sense Class
---------------

.. autoclass:: Sense

   .. attribute:: id

      The identifier used within a lexicon.

   .. automethod:: word
   .. automethod:: synset
   .. automethod:: get_related
   .. automethod:: get_related_synsets
   .. automethod:: closure
   .. automethod:: relation_paths
   .. automethod:: translate

The Synset Class
----------------

.. autoclass:: Synset

   .. attribute:: id

      The identifier used within a lexicon.

   .. attribute:: pos

      The part of speech of the Synset.

   .. attribute:: ili

      The interlingual index of the Synset.

   .. automethod:: definition
   .. automethod:: examples
   .. automethod:: senses
   .. automethod:: words
   .. automethod:: lemmas
   .. automethod:: hypernyms
   .. automethod:: hyponyms
   .. automethod:: holonyms
   .. automethod:: meronyms
   .. automethod:: hypernym_paths
   .. automethod:: lowest_common_hypernyms
   .. automethod:: get_related
   .. automethod:: closure
   .. automethod:: relation_paths
   .. automethod:: translate

The Lexicon Class
-----------------

.. autoclass:: Lexicon

   .. attribute:: id
   .. attribute:: label
   .. attribute:: language
   .. attribute:: email
   .. attribute:: license
   .. attribute:: version
   .. attribute:: url
   .. attribute:: citation
   .. attribute:: metadata

Exceptions
----------

.. autoexception:: Error
