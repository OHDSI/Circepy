"""
State-Based Fluent Builder for OHDSI Cohort Definitions.

This module provides a guided, L LM-friendly API where each method returns
an object with only valid next methods. The API guides users through
cohort construction step by step.

Example:
    >>> from circe.cohort_builder import Cohort
    >>> 
    >>> cohort = (
    ...     Cohort("T2DM Patients")
    ...     .with_condition(concept_set_id=1)
    ...     .first_occurrence()
    ...     .with_observation(prior_days=365)
    ...     .require_condition(concept_set_id=1)
    ...         .within_days_before(365)
    ...     .exclude_drug(concept_set_id=2)
    ...         .anytime_before()
    ...     .build()
    ... )
"""

from circe.cohort_builder.builder import CohortBuilder, CohortWithEntry, CohortWithCriteria

__all__ = [
    "CohortBuilder",
    "CohortWithEntry",
    "CohortWithCriteria"
]
