"""
SQL Query Builders for Cohort Definition.

This module contains SQL query builders that generate SQL queries from cohort definition criteria,
mirroring the Java CIRCE-BE builder classes.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from .utils import BuilderUtils, BuilderOptions, CriteriaColumn
from .base import CriteriaSqlBuilder
from .condition_occurrence import ConditionOccurrenceSqlBuilder
from .drug_exposure import DrugExposureSqlBuilder
from .procedure_occurrence import ProcedureOccurrenceSqlBuilder
from .death import DeathSqlBuilder
from .visit_occurrence import VisitOccurrenceSqlBuilder
from .observation import ObservationSqlBuilder
from .measurement import MeasurementSqlBuilder
from .device_exposure import DeviceExposureSqlBuilder
from .specimen import SpecimenSqlBuilder
from .condition_era import ConditionEraSqlBuilder
from .drug_era import DrugEraSqlBuilder
from .dose_era import DoseEraSqlBuilder
from .observation_period import ObservationPeriodSqlBuilder
from .payer_plan_period import PayerPlanPeriodSqlBuilder
from .visit_detail import VisitDetailSqlBuilder
from .location_region import LocationRegionSqlBuilder

__all__ = [
    # Utility classes
    "BuilderUtils", "BuilderOptions", "CriteriaColumn",
    
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
    "LocationRegionSqlBuilder"
]
