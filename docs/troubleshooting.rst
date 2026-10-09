Troubleshooting
===============

Common Issues and Solutions
----------------------------

Import Errors
~~~~~~~~~~~~~

If you encounter import errors:

.. code-block:: bash

   cd Circepy
   uv sync --extra dev

SQL Generation Issues
~~~~~~~~~~~~~~~~~~~~~

1. Validate your cohort first: ``circe validate cohort.json``
2. Check concept IDs are valid OMOP concepts
3. Verify schema names are correct

Performance Considerations
~~~~~~~~~~~~~~~~~~~~~~~~~~

* SQL generation typically completes in < 1 second
* Validation runs in < 500ms for most cohorts
* Memory usage scales with criteria count (typically < 100MB)

Getting Help
------------

If you can't resolve an issue:

1. Check existing GitHub issues
2. Create a new issue with:
   * Python version
   * CIRCE version
   * Error message
   * Minimal reproduction example
