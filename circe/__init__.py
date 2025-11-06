"""
CIRCE Python Implementation

A Python implementation of the OHDSI CIRCE-BE (Cohort Inclusion and Restriction Criteria Engine)
for generating SQL queries from cohort definitions in the OMOP Common Data Model.

This package provides:
- Cohort expression modeling and validation
- SQL query generation for cohort definitions
- Concept set management
- Print-friendly output generation
- Comprehensive checking and validation

GUARD RAIL: This package implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.

Version: 1.0.0
Author: CIRCE Python Implementation Team
License: Apache License 2.0
"""

__version__ = "1.0.0"
__author__ = "CIRCE Python Implementation Team"
__email__ = "circe-python@ohdsi.org"
__license__ = "Apache License 2.0"

# Main exports
from .cohortdefinition import CohortExpression
from .vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem
from .api import (
    cohort_expression_from_json,
    build_cohort_query,
    cohort_print_friendly,
)

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    # Main cohort class
    "CohortExpression",
    # Vocabulary classes
    "Concept", "ConceptSet", "ConceptSetExpression", "ConceptSetItem",
    # API functions
    "cohort_expression_from_json",
    "build_cohort_query",
    "cohort_print_friendly",
]
