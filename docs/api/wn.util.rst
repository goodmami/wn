wn.util
=======

.. automodule:: wn.util

.. autofunction:: synset_id_formatter

.. autoclass:: ProgressHandler
   :members:

   .. attribute:: kwargs

      A dictionary storing the updateable parameters for the progress
      handler. The keys are:

      - ``message`` (:class:`str`) -- a generic message or name
      - ``count`` (:class:`int`) -- the current progress counter
      - ``total`` (:class:`int`) -- the expected final value of the counter
      - ``unit`` (:class:`str`) -- the unit of measurement
      - ``status`` (:class:`str`) -- the current status of the process

.. autoclass:: ProgressBar
   :members:
