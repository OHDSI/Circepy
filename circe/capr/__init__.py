"""
Capr-style API for building OHDSI cohort definitions.

This module provides a fluent interface modeled after the OHDSI/Capr R package
for constructing cohort definitions in Python.

Example:
    >>> from circe.capr import (
    ...     cohort, entry, attrition, exit_strategy,
    ...     condition_occurrence, drug_exposure,
    ...     at_least, during_interval, event_starts
    ... )
    >>> 
    >>> t2dm_cohort = cohort(
    ...     entry=entry(
    ...         condition_occurrence(concept_set_id=1, first_occurrence=True),
    ...         observation_window=(365, 0)
    ...     )
    ... )
"""

from circe.capr.cohort import cohort, entry, exit_strategy, era
from circe.capr.query import (
    condition_occurrence, condition_era,
    drug_exposure, drug_era, dose_era,
    procedure, measurement, observation,
    visit, visit_detail,
    device_exposure, specimen, death,
    observation_period, payer_plan_period, location_region
)
from circe.capr.criteria import (
    at_least, at_most, exactly,
    with_all, with_any
)
from circe.capr.window import (
    during_interval, event_starts, event_ends,
    continuous_observation
)
from circe.capr.attrition import attrition
from circe.capr.templates import (
    sensitive_disease_cohort,
    specific_disease_cohort,
    acute_disease_cohort,
    chronic_disease_cohort,
    new_user_drug_cohort
)

__all__ = [
    # Cohort construction
    "cohort", "entry", "exit_strategy", "era", "attrition",
    
    # Domain queries - Conditions
    "condition_occurrence", "condition_era",
    
    # Domain queries - Drugs
    "drug_exposure", "drug_era", "dose_era",
    
    # Domain queries - Other clinical
    "procedure", "measurement", "observation",
    "visit", "visit_detail",
    "device_exposure", "specimen", "death",
    
    # Domain queries - Administrative
    "observation_period", "payer_plan_period", "location_region",
    
    # Occurrence counting
    "at_least", "at_most", "exactly",
    
    # Grouping
    "with_all", "with_any",
    
    # Time windows
    "during_interval", "event_starts", "event_ends",
    "continuous_observation",
    
    # Templates
    "sensitive_disease_cohort",
    "specific_disease_cohort", 
    "acute_disease_cohort",
    "chronic_disease_cohort",
    "new_user_drug_cohort"
]
