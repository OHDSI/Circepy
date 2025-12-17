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

# ---------------------------------------------------------------------
# Embedded interpreter (e.g. R reticulate) bootstrapping for Pydantic
# ---------------------------------------------------------------------
import sys
import pkgutil
import importlib
import inspect
from pydantic import BaseModel
import circe as package

def safe_model_rebuild(package):
    """
    Force-rebuild all Pydantic models in the given package.
    In embedded environments like R's reticulate, this avoids
    'ValueError: call stack is not deep enough' during instantiation.
    """
    try:
        for loader, module_name, is_pkg in pkgutil.walk_packages(
            package.__path__, package.__name__ + "."
        ):
            try:
                mod = importlib.import_module(module_name)
            except ImportError:
                continue

            for name, obj in inspect.getmembers(mod):
                if inspect.isclass(obj) and issubclass(obj, BaseModel):
                    try:
                        # Rebuild Pydantic v2 models
                        obj.model_rebuild(raise_errors=False)
                        # Eager instantiation to trigger lazy resolution early
                        try:
                            obj()
                        except Exception:
                            # Ignore models requiring mandatory args
                            pass
                    except Exception:
                        pass
    except Exception:
        pass

# ---------------------------------------------------------------------

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
    "safe_model_rebuild"
]
