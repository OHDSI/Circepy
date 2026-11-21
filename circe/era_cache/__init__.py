"""Era-level feature cache.

The cache stores the *events* a feature selects, as eras, at person level.  It
does not store a value for a cohort, an index date or a time-at-risk window.
Those are applied when reading, so one build serves many cohorts and many
windows.

Example::

    from circe.era_cache import EraCache, EraFeatureSpec, build_era_cache

    specs = [
        EraFeatureSpec(name="T2DM", source_table="condition_occurrence",
                       concept_ids=(201826,), include_descendants=True),
    ]
    outcome = build_era_cache(
        specs, backend=conn, cache_schema="feature_cache",
        cdm_schema="cdm", vocabulary_schema="vocab",
    )
    cache = EraCache(conn, schema="feature_cache")
    cache.explain()
"""

from .build import BuildOutcome, EraCache, build_era_cache
from .cohort_eras import CohortEraSpec, build_cohort_eras
from .identity import cache_key
from .keys import ENGINE_FINGERPRINT, ENGINE_VERSION, era_feature_key
from .read import feature_membership, feature_values, load_cohort, prevalence
from .schema import (
    CATEGORICAL_TABLE,
    CONTINUOUS_TABLE,
    LARGE_TABLES,
    PRESENCE_TABLE,
    REGISTRY_TABLE,
)
from .specs import ContinuousPredicate, EraFeatureSpec

__all__ = [
    "CATEGORICAL_TABLE",
    "CONTINUOUS_TABLE",
    "BuildOutcome",
    "CohortEraSpec",
    "ContinuousPredicate",
    "ENGINE_FINGERPRINT",
    "ENGINE_VERSION",
    "EraCache",
    "EraFeatureSpec",
    "LARGE_TABLES",
    "PRESENCE_TABLE",
    "REGISTRY_TABLE",
    "build_cohort_eras",
    "build_era_cache",
    "cache_key",
    "era_feature_key",
    "feature_membership",
    "feature_values",
    "load_cohort",
    "prevalence",
]
