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

Author: CIRCE Python Implementation Team
License: Apache License 2.0
"""

__version__ = "0.1.0"
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

from circe.cohortdefinition import (
    CohortExpression, Criteria, CorelatedCriteria, DemographicCriteria,
    Occurrence, CriteriaColumn, InclusionRule, CollapseType, DateType,
    ResultLimit, Period, DateRange, NumericRange, DateAdjustment,
    ObservationFilter, CollapseSettings, EndStrategy, PrimaryCriteria,
    CriteriaGroup, ConceptSetSelection, Window, TextFilter, GeoCriteria, WindowedCriteria,
    DateOffsetStrategy, CustomEraStrategy, ConditionOccurrence, DrugExposure,
    InclusionRule, WindowBound,
    ProcedureOccurrence, VisitOccurrence, Observation, Measurement, DeviceExposure,
    Specimen, Death, VisitDetail, ObservationPeriod, PayerPlanPeriod, LocationRegion,
    ConditionEra, DrugEra, DoseEra
)

from typing import Dict

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



def get_json_schema() -> dict:
    """
    Generate a combined JSON Schema from your Pydantic models
    in the same shape as the Java version.
    """
    # Map name → Pydantic model
    models: Dict[str, type] = {
        "CohortExpression": CohortExpression,
        "ConceptSet": ConceptSet,
        "ConceptSetExpression": ConceptSetExpression,
        "ConceptSetItem": ConceptSetItem,
        "Concept": Concept,
        "ResultLimit": ResultLimit,
        "CriteriaGroup": CriteriaGroup,
        "CorelatedCriteria": CorelatedCriteria,
        "Occurrence": Occurrence,
        "DemographicCriteria": DemographicCriteria,
        "DateRange": DateRange,
        "ConceptSetSelection": ConceptSetSelection,
        "NumericRange": NumericRange,
        "EndStrategy": EndStrategy,
        "PrimaryCriteria": PrimaryCriteria,
        "Criteria": Criteria,
        "DateAdjustment": DateAdjustment,
        "ObservationFilter": ObservationFilter,
        "CollapseSettings": CollapseSettings,
        "Period": Period,
        # Missing models added
        "WindowedCriteria": WindowedCriteria,
        "ConditionOccurrence": ConditionOccurrence,
        "DrugExposure": DrugExposure,
        "ProcedureOccurrence": ProcedureOccurrence,
        "VisitOccurrence": VisitOccurrence,
        "Observation": Observation,
        "Measurement": Measurement,
        "DeviceExposure": DeviceExposure,
        "Specimen": Specimen,
        "Death": Death,
        "VisitDetail": VisitDetail,
        "ObservationPeriod": ObservationPeriod,
        "PayerPlanPeriod": PayerPlanPeriod,
        "LocationRegion": LocationRegion,
        "ConditionEra": ConditionEra,
        "DrugEra": DrugEra,
        "DoseEra": DoseEra,
        "GeoCriteria": GeoCriteria,
        "DateOffsetStrategy": DateOffsetStrategy,
        "CustomEraStrategy": CustomEraStrategy,
        "Window": Window,
        "TextFilter": TextFilter,
        "InclusionRule": InclusionRule,
        "WindowBound": WindowBound
    }

    # Build root-level $defs with each schema
    defs: Dict[str, dict] = {}
    for name, model in models.items():
        # Use by_alias=True so JSON keys match Java casing if you set aliases in models
        schema = model.model_json_schema(by_alias=True)
        # Remove nested $defs if present (avoid double nesting)
        schema.pop("$defs", None)
        defs[name] = schema

    # Assemble root schema, referencing CohortExpression
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://github.com/OHDSI/circe-be/java-schema.json",
        "title": "CIRCE-BE Java Implementation Schema",
        "description": "JSON Schema extracted from Java CIRCE-BE source code",
        "version": "1.3.3",
        "type": "object",
        "$defs": defs,
        "properties": {
            "CohortExpression": {"$ref": "#/$defs/CohortExpression"}
        },
        "required": ["CohortExpression"]
    }



# ---------------------------------------------------------------------
__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    # Main cohort class
    "CohortExpression",
    "get_json_schema",
    # Vocabulary classes
    "Concept", "ConceptSet", "ConceptSetExpression", "ConceptSetItem",
    # API functions
    "cohort_expression_from_json",
    "build_cohort_query",
    "cohort_print_friendly",
    "safe_model_rebuild"
]
