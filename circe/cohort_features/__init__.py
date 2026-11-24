"""Cohort-first feature extraction.

This package treats cohorts and features as two views of the same definition:

* any cohort can be a feature (:func:`cohort_to_feature`);
* any feature can be turned into a cohort (:func:`feature_to_cohort`);
* a feature that is a pure primary-criteria selection can be projected back to
  a CIRCE criteria group and reused inside another cohort definition.

The extractor generates feature cohorts through the decomposable cohort engine
and assembles a basic ``(row_id, feature_id, value)`` matrix for a target
population.
"""

from .cohort_as_feature import (
    CohortPair,
    cohort_overlap_features,
    cohort_overlap_from_set,
    cohort_overlap_pairs,
    pairs_by_target,
)
from .duality import (
    cohort_set_from_features,
    cohort_to_feature,
    criteria_feature,
    feature_from_cohort,
    feature_to_cohort,
    feature_to_criteria_group,
    features_from_cohort_set,
)
from .extract import FeatureMatrix, extract_feature_matrix, write_feature_matrix
from .model import (
    CohortFeature,
    CriteriaFeature,
    Feature,
    FeatureAggregation,
    FeatureSet,
    FeatureWindow,
    NotExpressibleAsCriteriaError,
)
from .templates import (
    CohortTemplate,
    FeatureTemplate,
    expand_templates,
    template_feature_set,
)

__all__ = [
    "CohortFeature",
    "CohortPair",
    "CohortTemplate",
    "CriteriaFeature",
    "Feature",
    "FeatureAggregation",
    "FeatureMatrix",
    "FeatureSet",
    "FeatureTemplate",
    "FeatureWindow",
    "NotExpressibleAsCriteriaError",
    "cohort_overlap_features",
    "cohort_overlap_from_set",
    "cohort_overlap_pairs",
    "cohort_set_from_features",
    "pairs_by_target",
    "cohort_to_feature",
    "criteria_feature",
    "expand_templates",
    "extract_feature_matrix",
    "feature_from_cohort",
    "feature_to_cohort",
    "feature_to_criteria_group",
    "features_from_cohort_set",
    "template_feature_set",
    "write_feature_matrix",
]
