Command Line Interface
======================

Some of Wn's functionality is exposed via the command line.

Global Options
--------------

.. option:: -d DIR, --dir DIR

   Change to use ``DIR`` as the data directory prior to invoking any
   commands.

Subcommands
-----------

download
--------

You can give one or more project specifiers to the ``download``
subcommand:

.. code-block:: console

   $ python -m wn download pwn:3.0 omw

.. option:: --index FILE

   With the ``--index`` option, you can point to a TOML file that will
   be loaded with :meth:`wn.config.load_index
   <wn._config.WNConfig.load_index>` prior to downloading:

   .. code-block:: console

      $ python -m wn download --index my-index.toml mywn

lexicons
--------

The ``lexicons`` subcommand lets you quickly see what is installed:

.. code-block:: console

   $ python -m wn lexicons
   litwn:1.3+omw    [lt]   Lithuanian  WordNet
   nnown:1.3+omw    [nn]   Norwegian Wordnet
   jpnwn:1.3+omw    [jp]   Japanese Wordnet
   nobwn:1.3+omw    [nb]   Norwegian Wordnet
   arbwn:1.3+omw    [arb]  Arabic WordNet (AWN v2)
   porwn:1.3+omw    [pt]   OpenWN-PT
   cmnwn:1.3+omw    [zh]   Chinese Open Wordnet
   pwn:3.0          [en]   Princeton WordNet 3.0
   pwn:3.1          [en]   Princeton WordNet 3.1

.. option:: -l LG, --lang LG
.. option:: --lexicon SPEC

   The ``--lang`` or ``--lexicon`` option can help you narrow down
   the results:

   .. code-block:: console

      $ python -m wn lexicons --lang en
      pwn:3.0          [en]   Princeton WordNet 3.0
      pwn:3.1          [en]   Princeton WordNet 3.1
      $ python -m wn lexicons --lexicon "litwn pwn:* jpnwn:1.3+omw"
      litwn:1.3+omw    [lt]   Lithuanian  WordNet
      jpnwn:1.3+omw    [jp]   Japanese Wordnet
      pwn:3.0          [en]   Princeton WordNet 3.0
      pwn:3.1          [en]   Princeton WordNet 3.1
