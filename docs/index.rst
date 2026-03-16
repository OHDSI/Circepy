OHDSI CIRCE Python Documentation
==================================

.. image:: https://img.shields.io/badge/python-3.8%2B-blue
   :target: https://www.python.org/downloads/
   :alt: Python 3.8+

.. image:: https://img.shields.io/badge/tests-896%20passed-brightgreen
   :alt: Tests

.. image:: https://img.shields.io/badge/coverage-71%25-brightgreen
   :alt: Coverage

.. image:: https://img.shields.io/badge/license-Apache%202.0-blue.svg
   :target: https://opensource.org/licenses/Apache-2.0
   :alt: License

A Python implementation of the OHDSI CIRCE-BE (Cohort Inclusion and Restriction Criteria Engine) for generating SQL queries from cohort definitions in the OMOP Common Data Model.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   installation
   quickstart
   cli

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   user_guide/concepts
   user_guide/cohort_definitions
   user_guide/sql_generation
   user_guide/validation
   user_guide/examples

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/cohortdefinition
   api/vocabulary
   api/check
   api/builders
   api/api_functions

.. toctree::
   :maxdepth: 2
   :caption: Developer Guide

   developer/contributing
   developer/architecture
   developer/extensions
   developer/testing
   developer/release

.. toctree::
   :maxdepth: 1
   :caption: Additional Information

   faq
   troubleshooting
   changelog
   license

Overview
--------

CIRCE Python provides a comprehensive toolkit for working with OMOP CDM cohort definitions:

* **Cohort Definition Modeling**: Create and validate cohort expressions using Pydantic models
* **SQL Generation**: Generate SQL queries from cohort definitions for OMOP CDM v5.x
* **Concept Set Management**: Handle concepts and concept sets from OMOP vocabularies
* **Validation & Checking**: Comprehensive validation with 40+ checker implementations
* **Print-Friendly Output**: Generate human-readable markdown descriptions
* **CLI Interface**: Command-line tools for validation, SQL generation, and rendering

Key Features
------------

* **896 passing tests** with 71% code coverage
* **18+ SQL builders** for all OMOP CDM domains
* **Full cohort expression validation**
* **Markdown rendering** for human-readable descriptions
* **Complete CLI interface** with 4 commands
* **Java interoperability** - supports both camelCase and snake_case field names

Quick Example
-------------

.. code-block:: python

   from circe import CohortExpression
   from circe.cohortdefinition import PrimaryCriteria, ConditionOccurrence
   from circe.api import build_cohort_query

   # Create a simple cohort
   cohort = CohortExpression(
       title="Type 2 Diabetes Patients",
       primary_criteria=PrimaryCriteria(
           criteria_list=[
               ConditionOccurrence(codeset_id=1, first=True)
           ]
       )
   )

   # Generate SQL
   sql = build_cohort_query(cohort, cdm_schema="my_cdm", cohort_id=1)

Support
-------

* **Repository**: https://github.com/OHDSI/circe-be-python
* **Issues**: https://github.com/OHDSI/circe-be-python/issues
* **PyPI**: https://pypi.org/project/ohdsi-circe/

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

