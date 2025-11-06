Quick Start
===========

This guide will help you get started with CIRCE Python in just a few minutes.

Installation
------------

First, install CIRCE Python:

.. code-block:: bash

   pip install ohdsi-circe

Using the CLI
-------------

The easiest way to use CIRCE is through the command-line interface.

Validate a Cohort
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   circe validate my_cohort.json

Generate SQL
~~~~~~~~~~~~

.. code-block:: bash

   circe generate-sql my_cohort.json --output cohort.sql

Render Markdown
~~~~~~~~~~~~~~~

.. code-block:: bash

   circe render-markdown my_cohort.json --output cohort.md

Using the Python API
--------------------

Basic Example
~~~~~~~~~~~~~

Create a simple cohort definition:

.. code-block:: python

   from circe import CohortExpression
   from circe.cohortdefinition import PrimaryCriteria, ConditionOccurrence
   from circe.cohortdefinition.core import ObservationFilter, ResultLimit
   from circe.vocabulary import ConceptSet, ConceptSetExpression, ConceptSetItem, Concept

   # Define a concept set for Type 2 Diabetes
   diabetes_concepts = ConceptSet(
       id=1,
       name="Type 2 Diabetes",
       expression=ConceptSetExpression(
           items=[
               ConceptSetItem(
                   concept=Concept(
                       concept_id=201826,
                       concept_name="Type 2 diabetes mellitus"
                   ),
                   include_descendants=True
               )
           ]
       )
   )

   # Create primary criteria
   primary_criteria = PrimaryCriteria(
       criteria_list=[
           ConditionOccurrence(
               codeset_id=1,
               first=True
           )
       ],
       observation_window=ObservationFilter(prior_days=0, post_days=0),
       primary_limit=ResultLimit(type="All")
   )

   # Create cohort expression
   cohort = CohortExpression(
       title="Type 2 Diabetes Patients",
       concept_sets=[diabetes_concepts],
       primary_criteria=primary_criteria
   )

Generate SQL
~~~~~~~~~~~~

.. code-block:: python

   from circe.api import build_cohort_query

   sql = build_cohort_query(
       cohort,
       cdm_schema="my_cdm_schema",
       vocab_schema="my_vocab_schema",
       cohort_id=1
   )

   print(sql)

Load from JSON
~~~~~~~~~~~~~~

.. code-block:: python

   from circe import cohort_expression_from_json

   # Load from JSON string
   with open('cohort.json', 'r') as f:
       json_data = f.read()

   cohort = cohort_expression_from_json(json_data)

Validate Cohort
~~~~~~~~~~~~~~~

.. code-block:: python

   from circe.check import Checker

   checker = Checker()
   warnings = checker.check(cohort)

   if not warnings:
       print("✓ Cohort is valid!")
   else:
       for warning in warnings:
           print(f"{warning.severity}: {warning.message}")

Working with Examples
---------------------

CIRCE Python includes several example scripts in the ``examples/`` directory:

Basic Cohort
~~~~~~~~~~~~

.. code-block:: bash

   cd examples
   python basic_cohort.py

This creates a simple Type 2 Diabetes cohort and generates SQL.

Complex Cohort
~~~~~~~~~~~~~~

.. code-block:: bash

   python complex_cohort.py

Demonstrates advanced features like time windows and correlated criteria.

SQL Generation
~~~~~~~~~~~~~~

.. code-block:: bash

   python generate_sql.py

Shows different methods for generating SQL.

Validation
~~~~~~~~~~

.. code-block:: bash

   python validate_cohort.py

Demonstrates cohort validation workflows.

Common Patterns
---------------

Creating Concept Sets
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from circe.vocabulary import ConceptSet, ConceptSetExpression, ConceptSetItem, Concept

   concept_set = ConceptSet(
       id=1,
       name="My Concept Set",
       expression=ConceptSetExpression(
           items=[
               ConceptSetItem(
                   concept=Concept(concept_id=12345),
                   include_descendants=True,
                   is_excluded=False
               )
           ]
       )
   )

Time Windows
~~~~~~~~~~~~

.. code-block:: python

   from circe.cohortdefinition.core import Window, WindowBound

   # 30 days after index
   window = Window(
       start=WindowBound(days=0, coeff=-1),
       end=WindowBound(days=30, coeff=1),
       use_index_end=False,
       use_event_end=False
   )

Age Restrictions
~~~~~~~~~~~~~~~~

.. code-block:: python

   from circe.cohortdefinition.core import NumericRange

   # Age 18-65
   condition = ConditionOccurrence(
       codeset_id=1,
       age=NumericRange(value=18, op="gte"),
       age_at_end=NumericRange(value=65, op="lte")
   )

Next Steps
----------

* :doc:`user_guide/cohort_definitions` - Learn about cohort definitions in depth
* :doc:`user_guide/sql_generation` - Master SQL generation
* :doc:`user_guide/validation` - Validate your cohorts
* :doc:`api/cohortdefinition` - API reference for cohort definitions
* :doc:`user_guide/examples` - More examples and use cases

