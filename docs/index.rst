
Wn Documentation
================

Overview
--------

This package provides an interface to wordnet data, from simple lookup
queries, to graph traversals, to more sophisticated algorithms and
metrics. Features include:

- Support for wordnets in the
  `WN-LMF <https://globalwordnet.github.io/schemas/>`_ format
- A `SQLite <https://sqlite.org>`_ database backend for data
  consistency and efficient queries
- Accurate modeling of Words, Senses, and Synsets

Quick Start
-----------

.. code-block:: console

   $ pip install wn

.. code-block:: python

   >>> import wn
   >>> wn.download('ewn:2020')
   >>> wn.synsets('coffee')
   [Synset('ewn-04979718-n'), Synset('ewn-07945591-n'), Synset('ewn-07945759-n'), Synset('ewn-12683533-n')]


Contents
--------

.. toctree::
   :maxdepth: 2

   setup.rst
   cli.rst
   faq.rst

.. toctree::
   :caption: Guides
   :maxdepth: 2

   guides/lexicons.rst
   guides/basic.rst
   guides/interlingual.rst
   guides/wordnet.rst
   guides/lemmatization.rst
   guides/nltk-migration.rst

.. toctree::
   :caption: API Reference
   :maxdepth: 1
   :hidden:

   api/wn.rst
   api/wn.constants.rst
   api/wn.ic.rst
   api/wn.lmf.rst
   api/wn.morphy.rst
   api/wn.project.rst
   api/wn.similarity.rst
   api/wn.taxonomy.rst
   api/wn.util.rst
   api/wn.web.rst
