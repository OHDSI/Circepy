Creating Cohort Definitions
============================

This guide shows how to create cohort definitions using CIRCE Python.

Basic Cohort Structure
-----------------------

Every cohort expression has these components:

.. code-block:: python

   from circe import CohortExpression
   from circe.cohortdefinition import PrimaryCriteria
   
   cohort = CohortExpression(
       title="My Cohort",           # Optional description
       concept_sets=[...],           # Concept definitions
       primary_criteria=...,         # Required: initial events
       additional_criteria=...,      # Optional: filters
       inclusion_rules=[...],        # Optional: additional rules
       qualified_limit=...,          # Optional: event selection
       expression_limit=...,         # Optional: person selection
       collapse_settings=...,        # Optional: era collapse
       censor_window=...,            # Optional: censoring dates
       censoring_criteria=[...]      # Optional: censoring events
   )

For complete examples, see :doc:`../quickstart` and :doc:`examples`.

Working with Concept Sets
--------------------------

See :doc:`concepts` for detailed information about concept sets.

Defining Primary Criteria
--------------------------

See :doc:`concepts` for detailed information about primary criteria.

Adding Time-Based Criteria
---------------------------

See :doc:`concepts` for information about time windows and correlated criteria.

Age and Gender Restrictions
----------------------------

See :doc:`concepts` for demographic filtering options.

Using Inclusion Rules
---------------------

See :doc:`concepts` for inclusion rule details.

Cohort Exit and Censoring
--------------------------

Define when persons exit the cohort or when observation ends.

Next Steps
----------

* :doc:`sql_generation` - Generate SQL
* :doc:`validation` - Validate cohorts
* :doc:`examples` - More examples

