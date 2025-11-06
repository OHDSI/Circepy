Command-Line Interface
======================

CIRCE Python provides a comprehensive command-line interface for working with cohort definitions.

Overview
--------

The ``circe`` command provides four main subcommands:

* ``validate`` - Validate cohort definitions
* ``generate-sql`` - Generate SQL from cohort definitions
* ``render-markdown`` - Render cohort definitions as markdown
* ``process`` - Combined validation, SQL generation, and rendering

Getting Help
------------

.. code-block:: bash

   # General help
   circe --help

   # Help for specific command
   circe validate --help
   circe generate-sql --help
   circe render-markdown --help
   circe process --help

Validate Command
----------------

Validate a cohort expression JSON file against the CIRCE standard.

Basic Usage
~~~~~~~~~~~

.. code-block:: bash

   circe validate cohort.json

Options
~~~~~~~

.. code-block:: text

   --verbose, -v    Display all validation warnings including INFO level
   --quiet, -q      Suppress non-error output

Exit Codes
~~~~~~~~~~

* ``0`` - Valid (no errors or warnings)
* ``1`` - Invalid (errors found)
* ``2`` - Valid but has warnings

Examples
~~~~~~~~

.. code-block:: bash

   # Validate with verbose output
   circe validate cohort.json --verbose

   # Quiet mode (only errors)
   circe validate cohort.json --quiet

   # Check exit code in scripts
   if circe validate cohort.json; then
       echo "Cohort is valid"
   else
       echo "Cohort has errors"
   fi

Generate SQL Command
--------------------

Generate SQL from a cohort expression.

Basic Usage
~~~~~~~~~~~

.. code-block:: bash

   # Output to stdout
   circe generate-sql cohort.json

   # Output to file
   circe generate-sql cohort.json --output cohort.sql

Options
~~~~~~~

.. code-block:: text

   --output, -o FILE       Output SQL file path
   --sql-options FILE      JSON file with BuildExpressionQueryOptions
   --cdm-schema SCHEMA     CDM schema name (default: @cdm_database_schema)
   --vocab-schema SCHEMA   Vocabulary schema name (default: @vocabulary_database_schema)
   --cohort-id ID          Cohort ID for SQL generation
   --validate              Validate before generating SQL (default: True)
   --no-validate           Skip validation
   --verbose, -v           Verbose output
   --quiet, -q             Suppress non-error output

Examples
~~~~~~~~

.. code-block:: bash

   # Basic SQL generation
   circe generate-sql cohort.json --output output.sql

   # With custom schema names
   circe generate-sql cohort.json \\
       --cdm-schema my_cdm \\
       --vocab-schema my_vocab \\
       --cohort-id 123 \\
       --output cohort_123.sql

   # Skip validation for faster generation
   circe generate-sql cohort.json --no-validate --output fast.sql

   # Pipe to file
   circe generate-sql cohort.json > cohort.sql

SQL Options File
~~~~~~~~~~~~~~~~

Create a JSON file with custom SQL generation options:

.. code-block:: json

   {
       "cdmSchema": "my_cdm",
       "vocabularySchema": "my_vocab",
       "targetTable": "#cohort_inclusion",
       "resultsSchema": "results",
       "generateStats": true
   }

Use it with:

.. code-block:: bash

   circe generate-sql cohort.json --sql-options options.json

Render Markdown Command
------------------------

Render a cohort expression to human-readable markdown.

Basic Usage
~~~~~~~~~~~

.. code-block:: bash

   # Output to stdout
   circe render-markdown cohort.json

   # Output to file
   circe render-markdown cohort.json --output cohort.md

Options
~~~~~~~

.. code-block:: text

   --output, -o FILE    Output markdown file path
   --validate           Validate before rendering (default: True)
   --no-validate        Skip validation
   --verbose, -v        Verbose output
   --quiet, -q          Suppress non-error output

Examples
~~~~~~~~

.. code-block:: bash

   # Render to file
   circe render-markdown cohort.json --output description.md

   # Skip validation
   circe render-markdown cohort.json --no-validate --output quick.md

   # View in terminal (with less)
   circe render-markdown cohort.json | less

Process Command
---------------

Process a cohort expression with multiple operations.

Basic Usage
~~~~~~~~~~~

.. code-block:: bash

   # Validate, generate SQL, and render markdown
   circe process cohort.json --validate --sql --markdown

Options
~~~~~~~

.. code-block:: text

   --validate              Validate the cohort expression
   --sql [FILE]            Generate SQL (optional file path)
   --markdown [FILE]       Render markdown (optional file path)
   --sql-options FILE      JSON file with BuildExpressionQueryOptions
   --cdm-schema SCHEMA     CDM schema name
   --vocab-schema SCHEMA   Vocabulary schema name
   --cohort-id ID          Cohort ID
   --verbose, -v           Verbose output
   --quiet, -q             Suppress non-error output

Examples
~~~~~~~~

.. code-block:: bash

   # All operations with default filenames
   circe process cohort.json --validate --sql --markdown

   # Custom output files
   circe process cohort.json \\
       --sql my_cohort.sql \\
       --markdown my_cohort.md

   # Only SQL generation
   circe process cohort.json --sql

   # With custom schema
   circe process cohort.json \\
       --sql \\
       --cdm-schema production_cdm \\
       --cohort-id 42

Common Workflows
----------------

Development Workflow
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # 1. Validate cohort
   circe validate cohort.json

   # 2. Generate SQL and markdown for review
   circe process cohort.json --sql --markdown

   # 3. Review generated files
   cat cohort.sql
   cat cohort.md

Production Workflow
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Validate and generate with production settings
   circe process cohort.json \\
       --validate \\
       --sql production.sql \\
       --cdm-schema prod_cdm \\
       --vocab-schema prod_vocab \\
       --cohort-id 1001

Batch Processing
~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Process multiple cohorts
   for cohort in cohorts/*.json; do
       echo "Processing $cohort"
       circe process "$cohort" --validate --sql --markdown
   done

CI/CD Integration
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   #!/bin/bash
   # Validate all cohorts in CI
   
   EXIT_CODE=0
   for cohort in cohorts/*.json; do
       if ! circe validate "$cohort" --quiet; then
           echo "❌ $cohort failed validation"
           EXIT_CODE=1
       else
           echo "✓ $cohort is valid"
       fi
   done
   
   exit $EXIT_CODE

Environment Variables
---------------------

CIRCE Python respects the following environment variables:

.. code-block:: bash

   # Default CDM schema
   export CIRCE_CDM_SCHEMA=my_cdm

   # Default vocabulary schema
   export CIRCE_VOCAB_SCHEMA=my_vocab

   # Use in commands (when CLI supports it in future versions)
   circe generate-sql cohort.json

Logging and Output
------------------

Verbose Mode
~~~~~~~~~~~~

Use ``-v`` or ``--verbose`` for detailed output:

.. code-block:: bash

   circe validate cohort.json --verbose

Quiet Mode
~~~~~~~~~~

Use ``-q`` or ``--quiet`` to suppress informational output:

.. code-block:: bash

   circe generate-sql cohort.json --quiet --output cohort.sql

Return Codes in Scripts
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Capture exit code
   circe validate cohort.json
   RESULT=$?

   if [ $RESULT -eq 0 ]; then
       echo "Success"
   elif [ $RESULT -eq 1 ]; then
       echo "Validation errors"
   elif [ $RESULT -eq 2 ]; then
       echo "Validation warnings"
   fi

Troubleshooting
---------------

Command Not Found
~~~~~~~~~~~~~~~~~

If ``circe`` command is not found after installation:

.. code-block:: bash

   # Try with python -m
   python -m circe.cli --help

   # Or reinstall
   pip install --force-reinstall ohdsi-circe

Permission Errors
~~~~~~~~~~~~~~~~~

If you get permission errors accessing files:

.. code-block:: bash

   # Check file permissions
   ls -l cohort.json

   # Make file readable
   chmod 644 cohort.json

JSON Parse Errors
~~~~~~~~~~~~~~~~~

If you get JSON parsing errors:

.. code-block:: bash

   # Validate JSON syntax with jq
   jq . cohort.json

   # Or with python
   python -m json.tool cohort.json

Next Steps
----------

* :doc:`user_guide/cohort_definitions` - Learn about cohort definitions
* :doc:`user_guide/validation` - Understand validation
* :doc:`user_guide/sql_generation` - Master SQL generation

