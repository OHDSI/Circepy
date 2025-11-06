SQL Generation
===============

Generate SQL queries from cohort definitions for execution against OMOP CDM databases.

Quick Start
-----------

.. code-block:: python

   from circe.api import build_cohort_query
   
   sql = build_cohort_query(
       cohort,
       cdm_schema="my_cdm",
       vocab_schema="my_vocab",
       cohort_id=1
   )

For detailed examples, see the ``examples/generate_sql.py`` file in the repository.

Advanced SQL Generation
-----------------------

Use custom options for more control over SQL generation.

CLI SQL Generation
------------------

See :doc:`../cli` for command-line SQL generation options.

Next Steps
----------

* :doc:`validation` - Validate before generating
* :doc:`../cli` - CLI SQL generation

