wn.compat
=========

Compatibility modules for Wn.

This subpackage is a namespace for compatibility modules when working
with particular lexicons. Wn is designed to be agnostic to the
language or lexicon and not favor one over the other (with the
exception of :mod:`wn.morphy`, which is English-specific). However,
there are some kinds of functionality that would be useful to
include in Wn, even if they don't generalize to all lexicons.

Included modules
----------------

.. toctree::
   :maxdepth: 1

   wn.compat.sensekey.rst

