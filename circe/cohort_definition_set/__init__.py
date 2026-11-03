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
    >>> # Reuse checkpoints across definitions that share pipeline prefixes:
    >>> results = generate_cohort_set(
    ...     cds,
    ...     backend=conn,
    ...     cdm_schema="main",
    ...     cohort_table="cohort",
    ...     shared=True,
    ... )
"""

from ..decomposition import Decomposition, DerivedCohort, decompose_cohort_set
from ._core import CohortDefinition, CohortDefinitionSet, CohortGenerationResult
from ._generate import async_generate_cohort_set, generate_cohort_set, summarise_generation_results
from ._legacy import (
    CohortSource,
    LegacyCohortDefinitionSet,
    LegacyCohortSetError,
    LegacyCohortSetReport,
    LoadedCohortDefinition,
    MissingCohortDefinitionFileError,
    SkippedCohort,
    UnsupportedLegacyFeatureError,
    load_cohort_definition_set,
)
from ._legacy_sql import (
    LegacySqlComparison,
    render_legacy_sql,
    verify_against_legacy_sql,
)

__all__ = [
    "CohortDefinition",
    "CohortDefinitionSet",
    "CohortGenerationResult",
    "CohortSource",
    "LegacyCohortDefinitionSet",
    "LegacyCohortSetError",
    "LegacyCohortSetReport",
    "LoadedCohortDefinition",
    "LegacySqlComparison",
    "render_legacy_sql",
    "verify_against_legacy_sql",
    "MissingCohortDefinitionFileError",
    "SkippedCohort",
    "UnsupportedLegacyFeatureError",
    "load_cohort_definition_set",
    "Decomposition",
    "DerivedCohort",
    "decompose_cohort_set",
    "async_generate_cohort_set",
    "generate_cohort_set",
    "summarise_generation_results",
]
