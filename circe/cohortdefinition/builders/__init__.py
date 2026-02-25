"""
SQL Query Builders for Cohort Definition.

This module contains SQL query builders that generate SQL queries from cohort definition criteria,
mirroring the Java CIRCE-BE builder classes.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from .base import CriteriaSqlBuilder
from .condition_era import ConditionEraSqlBuilder
from .condition_occurrence import ConditionOccurrenceSqlBuilder
from .death import DeathSqlBuilder
from .device_exposure import DeviceExposureSqlBuilder
from .dose_era import DoseEraSqlBuilder
from .drug_era import DrugEraSqlBuilder
from .drug_exposure import DrugExposureSqlBuilder
from .location_region import LocationRegionSqlBuilder
from .measurement import MeasurementSqlBuilder
from .observation import ObservationSqlBuilder
from .observation_period import ObservationPeriodSqlBuilder
from .payer_plan_period import PayerPlanPeriodSqlBuilder
from .procedure_occurrence import ProcedureOccurrenceSqlBuilder
from .specimen import SpecimenSqlBuilder
from .utils import BuilderOptions, BuilderUtils, CriteriaColumn
from .visit_detail import VisitDetailSqlBuilder
from .visit_occurrence import VisitOccurrenceSqlBuilder

__all__ = [
    # Utility classes
    "BuilderUtils",
    "BuilderOptions",
    "CriteriaColumn",
    # Base builder class
    "CriteriaSqlBuilder",
    # Specific builders
    "ConditionOccurrenceSqlBuilder",
    "DrugExposureSqlBuilder",
    "ProcedureOccurrenceSqlBuilder",
    "DeathSqlBuilder",
    "VisitOccurrenceSqlBuilder",
    "ObservationSqlBuilder",
    "MeasurementSqlBuilder",
    "DeviceExposureSqlBuilder",
    "SpecimenSqlBuilder",
    "ConditionEraSqlBuilder",
    "DrugEraSqlBuilder",
    "DoseEraSqlBuilder",
    "ObservationPeriodSqlBuilder",
    "PayerPlanPeriodSqlBuilder",
    "VisitDetailSqlBuilder",
    "LocationRegionSqlBuilder",
]
