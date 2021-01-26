
wn
===

.. automodule:: wn

Project Management Functions
----------------------------

.. autofunction:: download
.. autofunction:: add
.. autofunction:: remove
.. autofunction:: export
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
   .. automethod:: metadata
   .. automethod:: derived_words
   .. automethod:: translate


The Form Class
--------------

.. class:: Form

   The return value of :meth:`Word.lemma` and the members of the list
   returned by :meth:`Word.forms` are :class:`Form` objects. These are
   a basic subclass of Python's :class:`str` class with an additional
   attribute, :attr:`script`. Form objects without any specified
   script behave exactly as a regular string (they are equal and hash
   to the same value), but if they have different script values they
   are unequal and hash differently, even if the string itself is
   identical.

   >>> inu = wn.words('犬', lexicon='wnja')[0]
   >>> inu.forms()[3]
   'いぬ'
   >>> inu.forms()[3].script
   'hira'

   The :attr:`script` is often unspecified (i.e., ``None``) and this
   carries the implicit meaning that the form uses the canonical
   script for the word's language or wordnet, whatever it may be.

   .. attribute:: script

      The script of the word form. This should be an `ISO 15924
      <https://en.wikipedia.org/wiki/ISO_15924>`_ code, or ``None``.


The Sense Class
---------------

.. autoclass:: Sense

   .. attribute:: id

      The identifier used within a lexicon.

   .. automethod:: word
   .. automethod:: synset
   .. automethod:: metadata
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
   .. automethod:: lexicalized
   .. automethod:: metadata
   .. automethod:: words
   .. automethod:: lemmas
   .. automethod:: hypernyms
   .. automethod:: hyponyms
   .. automethod:: holonyms
   .. automethod:: meronyms
   .. automethod:: hypernym_paths
   .. automethod:: min_depth
   .. automethod:: max_depth
   .. automethod:: shortest_path
   .. automethod:: common_hypernyms
   .. automethod:: lowest_common_hypernyms
   .. automethod:: get_related
   .. automethod:: closure
   .. automethod:: relation_paths
   .. automethod:: translate

The Lexicon Class
-----------------

.. autoclass:: Lexicon

   .. automethod:: metadata
   .. automethod:: specifier

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
   .. attribute:: allow_multithreading

      If set to :python:`True`, the database connection may be shared
      across threads. In this case, it is the user's responsibility to
      ensure that multiple threads don't try to write to the database
      at the same time. The default is :python:`False`.

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
