Cohort Validation
==================

Validate cohort definitions to catch errors before generating SQL.

Basic Validation
----------------

.. code-block:: python

   from circe.check.check import check_cohort_expression
   
   warnings = check_cohort_expression(cohort)
   
   if not warnings:
       print("✓ Cohort is valid!")

Validation checks for over 40 different potential issues.

Handling Warnings
-----------------

Warnings have severity levels: ERROR, WARNING, INFO.

See ``examples/validate_cohort.py`` for complete examples.

CLI Validation
--------------

See :doc:`../cli` for command-line validation.

Next Steps
----------

* :doc:`sql_generation` - Generate SQL after validation
* :doc:`../cli` - CLI validation options

