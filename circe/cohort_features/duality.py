"""The cohort/feature duality in one place.

Cohorts and features are two views of the same definition:

``cohort_to_feature``
    Wrap any cohort expression as a feature.  This is the "any cohort can be a
    feature" direction.

``feature_to_cohort``
    Return the cohort expression behind a feature.  This is the "all features
    could be turned into cohorts" direction.

``feature_to_criteria_group``
    Project a feature back to a CIRCE criteria group when the feature is a pure
    primary-criteria cohort.  This is what makes a feature reusable *inside*
    another cohort definition.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..cohort_definition_set._core import CohortDefinitionSet
from ..cohortdefinition.cohort import CohortExpression
from ..cohortdefinition.core import ObservationFilter
from ..cohortdefinition.criteria import Criteria, CriteriaGroup
from ..vocabulary.concept import ConceptSet
from .model import (
    _UNSET,
    CohortFeature,
    CriteriaFeature,
    Feature,
    FeatureAggregation,
    FeatureSet,
    FeatureWindow,
    NotExpressibleAsCriteriaError,
)

__all__ = [
    "cohort_set_from_features",
    "cohort_to_feature",
    "criteria_feature",
    "feature_from_cohort",
    "feature_to_cohort",
    "feature_to_criteria_group",
    "features_from_cohort_set",
]


def cohort_to_feature(
    expression: CohortExpression,
    *,
    feature_id: int,
    name: str | None = None,
    aggregation: FeatureAggregation = "exists",
    window: FeatureWindow | None | object = _UNSET,
    tags: tuple[str, ...] = (),
) -> CohortFeature:
    """Wrap any cohort expression as a feature."""
    return CohortFeature(
        feature_id=feature_id,
        name=name or expression.title or f"feature_{feature_id}",
        cohort=expression,
        aggregation=aggregation,
        window=FeatureWindow() if window is _UNSET else window,
        tags=tags,
    )


feature_from_cohort = cohort_to_feature


def feature_to_cohort(feature: Feature) -> CohortExpression:
    """Return the cohort expression behind *feature*."""
    return feature.to_cohort()


def feature_to_criteria_group(feature: Feature) -> CriteriaGroup:
    """Project *feature* to a criteria group.

    Raises :class:`NotExpressibleAsCriteriaError` when the feature carries
    additional criteria or inclusion rules.
    """
    try:
        return feature.to_criteria_group()
    except NotExpressibleAsCriteriaError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise NotExpressibleAsCriteriaError(str(exc)) from exc


def criteria_feature(
    criterion: Criteria,
    *,
    feature_id: int,
    name: str | None = None,
    concept_sets: Iterable[ConceptSet] = (),
    observation_window: ObservationFilter | None = None,
    aggregation: FeatureAggregation = "exists",
    window: FeatureWindow | None = None,
    tags: tuple[str, ...] = (),
) -> CriteriaFeature:
    """Build a feature from one criterion and its concept sets."""
    return CriteriaFeature(
        feature_id=feature_id,
        name=name or f"feature_{feature_id}",
        criterion=criterion,
        concept_sets=tuple(concept_sets),
        observation_window=observation_window or ObservationFilter(prior_days=0, post_days=0),
        aggregation=aggregation,
        window=window if window is not None else FeatureWindow(),
        tags=tags,
    )


def features_from_cohort_set(
    cohort_set: CohortDefinitionSet,
    *,
    aggregation: FeatureAggregation = "exists",
    window: FeatureWindow | None = None,
    tags: tuple[str, ...] = (),
) -> FeatureSet:
    """Turn every cohort in a definition set into a feature."""
    return FeatureSet.from_cohort_definition_set(
        cohort_set,
        aggregation=aggregation,
        window=window,
        tags=tags,
    )


def cohort_set_from_features(feature_set: FeatureSet):
    """Turn every feature into a cohort definition."""
    return feature_set.to_cohort_definition_set()
