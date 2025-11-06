Architecture
============

CIRCE Python follows the architecture of the Java CIRCE-BE implementation.

Package Structure
-----------------

* **cohortdefinition/** - Core cohort classes and SQL builders
* **vocabulary/** - Concept and concept set management
* **check/** - Validation framework
* **helper/** - Utility functions
* **api.py** - High-level API
* **cli.py** - Command-line interface

SQL Generation
--------------

SQL generation uses a template-based approach with domain-specific builders.

Validation Framework
--------------------

The validation framework uses a checker pattern with pluggable validators.

