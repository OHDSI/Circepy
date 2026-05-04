"""CohortDefinitionSet — batch cohort generation with incremental caching.

This module provides the Python equivalent of OHDSI/CohortGenerator's
CohortDefinitionSet: a typed container for multiple cohort definitions that can
be generated simultaneously against an ibis backend, with optional checksum-based
incremental skipping.

Example:
    >>> from circe.cohort_definition_set import (
    ...     CohortDefinitionSet,
    ...     generate_cohort_set,
    ... )
    >>> cds = CohortDefinitionSet()
    >>> cds.add(cohort_id=1, cohort_name="Diabetes", expression=expr1)
    >>> cds.add(cohort_id=2, cohort_name="Hypertension", expression=expr2)
    >>> results = generate_cohort_set(
    ...     cds,
    ...     backend=conn,
    ...     cdm_schema="main",
    ...     cohort_table="cohort",
    ...     incremental=True,
    ... )
"""

from ._core import CohortDefinition, CohortDefinitionSet, CohortGenerationResult
from ._generate import generate_cohort_set, summarise_generation_results

__all__ = [
    "CohortDefinition",
    "CohortDefinitionSet",
    "CohortGenerationResult",
    "generate_cohort_set",
    "summarise_generation_results",
]
