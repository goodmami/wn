wn.ili
======

.. automodule:: wn.ili

.. note::

   See :doc:`../guides/interlingual` for background and usage information about
   ILIs.


Functions for Getting ILI Objects
---------------------------------

The following functions are for getting individual :class:`ILI` and
:class:`ProposedILI` objects from ILI identifiers or synsets, respectively, or
to list all such known objects.

.. autofunction:: get
.. autofunction:: get_all
.. autofunction:: get_proposed
.. autofunction:: get_all_proposed


ILI Status
----------

The status of an ILI object (:attr:`ILI.status` or :attr:`ProposedILI.status`)
indicates what is known about its validity. Explicit information about ILIs can
be added to Wn with :func:`wn.add` (e.g., :python:`wn.add("cili")`), but without
it Wn can only make a guess.

If a lexicon has synsets referencing some ILI identifier and no ILI file has
been loaded, that ILI would have a status of :attr:`ILIStatus.PRESUPPOSED`. If
an ILI file has been loaded that lists the identifier, it would have a status of
:attr:`ILIStatus.ACTIVE`, whether or not a lexicon has been added that uses
the ILI. Both of these cases use :class:`ILI` objects.

A synset in the WN-LMF format may also propose a new ILI. It won't have an
identifier, but it should have a definition. These have the status of
:attr:`ILIStatus.PROPOSED`. The :class:`ProposedILI` is used for these objects,
and that is the only status they have.

The :attr:`ILIStatus.UNKNOWN` status is just a default (e.g., when manually
creating an :class:`ILI` object) and won't be encountered in normal scenarios.

.. autoclass:: ILIStatus

   .. autoattribute:: UNKNOWN
   .. autoattribute:: ACTIVE
   .. autoattribute:: PRESUPPOSED
   .. autoattribute:: PROPOSED


ILI Classes
-----------

.. autoclass:: ILI

   .. autoattribute:: id

      The ILI identifier.

   .. autoattribute:: status

      The status of the ILI.

   .. automethod:: definition


.. autoclass:: ProposedILI

   .. autoproperty:: id
   .. autoproperty:: status
   .. automethod:: definition
   .. automethod:: synset
   .. automethod:: lexicon


ILI Definitions
---------------

Most likely someone inspecting the definition of an :class:`ILI` or
:class:`ProposedILI` only cares about the definition text, but for
completeness' sake the :class:`ILIDefinition` object models the text
along with any metadata that may have appeared in the WN-LMF lexicon
file. ILI files do not currently model metadata.

.. autoclass:: ILIDefinition

   .. autoattribute:: text
   .. automethod:: metadata
