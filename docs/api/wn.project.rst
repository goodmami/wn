wn.project
==========

.. automodule:: wn.project

.. autofunction:: get_project
.. autofunction:: iterpackages
.. autofunction:: is_package_directory
.. autofunction:: is_collection_directory

Project Classes
---------------

Projects can be simple resource files, :class:`Package` directories,
or :class:`Collection` directories. For API consistency, resource
files are modeled as a virtual package (:class:`ResourceOnlyPackage`).

.. class:: Project

   The base class for packages and collections.

   This class is not used directly, but all subclasses will implement
   the methods listed here.

   .. autoproperty:: path
   .. automethod:: readme
   .. automethod:: license
   .. automethod:: citation

.. autoclass:: Package
   :show-inheritance:

   .. autoproperty:: type
   .. automethod:: resource_file

.. autoclass:: ResourceOnlyPackage
   :show-inheritance:

.. autoclass:: Collection
   :show-inheritance:

   .. automethod:: packages
