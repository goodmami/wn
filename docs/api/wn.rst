
wn
===

.. automodule:: wn

Project Management Functions
----------------------------

.. autofunction:: download
.. autofunction:: add
.. autofunction:: remove
.. autofunction:: projects

Wordnet Query Functions
-----------------------

.. autofunction:: word
.. autofunction:: words
.. autofunction:: sense
.. autofunction:: senses
.. autofunction:: synset
.. autofunction:: synsets
.. autofunction:: lexicons

The Wordnet Class
-----------------

.. autoclass:: Wordnet

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


The wn.config Object
--------------------

Wn's data storage and retrieval can be configured through the
:data:`wn.config` object.

.. seealso::

   :doc:`../guides/setup` describes how to configure Wn using the
   :data:`wn.config` instance.

.. autodata:: config

It is an instance of the :class:`~wn._config.WNConfig` class, which is
defined in a non-public module and is not meant to be instantiated
directly. Configuration should occur through the single
:data:`wn.config` instance.

.. autoclass:: wn._config.WNConfig

   .. autoattribute:: data_directory
   .. autoattribute:: database_path
   .. autoattribute:: downloads_directory
   .. automethod:: add_project
   .. automethod:: add_project_version
   .. automethod:: get_project_info
   .. automethod:: get_cache_path
   .. automethod:: update
   .. automethod:: load_index


Exceptions
----------

.. autoexception:: Error
