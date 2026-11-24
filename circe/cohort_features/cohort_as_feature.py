"""Cohorts as features: the overlap matrix.

FeatureExtraction exposes cohort membership as a covariate through
``createCohortBasedCovariateSettings``. Each (target, feature) cohort pair
becomes one binary covariate: did the subject also enter cohort X inside the
window?  That is the mechanism behind cohort overlap and cohort relationship
diagnostics.

This module builds those pairs declaratively:

* :func:`cohort_overlap_pairs` — every ordered (target, feature) pair, self-pairs
  excluded by default.
* :func:`cohort_overlap_features` — one :class:`FeatureSet` holding a feature per
  pair, ready for :func:`circe.cohort_features.extract_feature_matrix`.
* :func:`cohort_overlap_from_set` — convenience wrapper that returns both.

The features are ordinary :class:`CohortFeature` objects, so everything the
rest of the package does with features (extraction, matrix assembly, export)
works unchanged.  Nothing here needs a separate code path.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from ..cohort_definition_set._core import CohortDefinition, CohortDefinitionSet
from .model import CohortFeature, FeatureSet, FeatureWindow

__all__ = [
    "CohortPair",
    "cohort_overlap_features",
    "cohort_overlap_from_set",
    "cohort_overlap_pairs",
    "feature_id_for_pair",
]


@dataclass(frozen=True)
class CohortPair:
    """One (target, feature) cohort pair.

    ``feature_id`` is derived from the pair so a matrix built twice from the
    same definition set assigns the same ids.
    """

    target_cohort_id: int
    target_cohort_name: str
    feature_cohort_id: int
    feature_cohort_name: str
    feature_id: int


def feature_id_for_pair(
    target_cohort_id: int,
    feature_cohort_id: int,
    *,
    base: int = 1,
) -> int:
    """Return a stable, unique feature id for a cohort pair.

    Ids are dense and assigned by :func:`cohort_overlap_pairs`; this helper is
    exposed so callers can reason about a pair's id without rebuilding the
    matrix.
    """
    if base < 1:
        raise ValueError("base must be >= 1")
    return base + (int(target_cohort_id) * 1_000_000) + int(feature_cohort_id)


def cohort_overlap_pairs(
    cohort_set: CohortDefinitionSet,
    *,
    include_self: bool = False,
    max_features_per_target: int | None = None,
) -> Iterator[CohortPair]:
    """Yield every ordered (target, feature) cohort pair.

    Args:
        cohort_set: Definitions to pair up.
        include_self: Keep pairs where target and feature are the same cohort.
            Off by default, since a cohort trivially contains its own entries.
        max_features_per_target: Optional cap per target cohort, useful for very
            wide matrices. Pairs keep definition-set order when capped.
    """
    definitions = list(cohort_set)
    if max_features_per_target is not None and max_features_per_target < 1:
        raise ValueError("max_features_per_target must be >= 1")

    next_id = 1
    seen: dict[tuple[int, int], int] = {}
    for target in definitions:
        emitted = 0
        for feature in definitions:
            if not include_self and feature.cohort_id == target.cohort_id:
                continue
            if max_features_per_target is not None and emitted >= max_features_per_target:
                break
            key = (target.cohort_id, feature.cohort_id)
            feature_id = seen.setdefault(key, next_id)
            if feature_id == next_id:
                next_id += 1
            emitted += 1
            yield CohortPair(
                target_cohort_id=target.cohort_id,
                target_cohort_name=target.cohort_name,
                feature_cohort_id=feature.cohort_id,
                feature_cohort_name=feature.cohort_name,
                feature_id=feature_id,
            )


def _windows_for(
    pairs: list[CohortPair],
    definitions: dict[int, CohortDefinition],
    *,
    window: FeatureWindow | None,
) -> list[CohortFeature]:
    resolved = window or FeatureWindow()
    features: list[CohortFeature] = []
    for pair in pairs:
        definition = definitions[pair.feature_cohort_id]
        features.append(
            CohortFeature(
                feature_id=pair.feature_id,
                name=f"also in {pair.feature_cohort_name}",
                cohort=definition.expression,
                aggregation="exists",
                window=resolved,
                source_cohort_id=pair.feature_cohort_id,
                tags=("cohort_overlap",),
            )
        )
    return features


def cohort_overlap_features(
    cohort_set: CohortDefinitionSet,
    *,
    window: FeatureWindow | None = None,
    include_self: bool = False,
    max_features_per_target: int | None = None,
    name: str | None = None,
) -> FeatureSet:
    """Return a :class:`FeatureSet` with one feature per cohort-overlap pair.

    The returned set is keyed by ``feature_id`` only; which target cohort each
    feature belongs to is recovered with :func:`cohort_overlap_pairs`, which
    yields the pairs in the same order.
    """
    pairs = list(
        cohort_overlap_pairs(
            cohort_set,
            include_self=include_self,
            max_features_per_target=max_features_per_target,
        )
    )
    if not pairs:
        raise ValueError("cohort set produced no overlap pairs; need at least one cohort")
    definitions = {definition.cohort_id: definition for definition in cohort_set}
    return FeatureSet(
        features=_windows_for(pairs, definitions, window=window),
        name=name or "cohort_overlap",
    )


def cohort_overlap_from_set(
    cohort_set: CohortDefinitionSet,
    *,
    window: FeatureWindow | None = None,
    include_self: bool = False,
    max_features_per_target: int | None = None,
) -> tuple[FeatureSet, list[CohortPair]]:
    """Return the overlap :class:`FeatureSet` together with its pairs.

    The pairs are ordered to match the feature order, so
    ``zip(pairs, feature_set.features)`` pairs each feature with its target.
    """
    pairs = list(
        cohort_overlap_pairs(
            cohort_set,
            include_self=include_self,
            max_features_per_target=max_features_per_target,
        )
    )
    if not pairs:
        raise ValueError("cohort set produced no overlap pairs; need at least one cohort")
    definitions = {definition.cohort_id: definition for definition in cohort_set}
    feature_set = FeatureSet(
        features=_windows_for(pairs, definitions, window=window),
        name="cohort_overlap",
    )
    return feature_set, pairs


def pairs_by_target(pairs: list[CohortPair]) -> dict[int, list[CohortPair]]:
    """Group pairs by target cohort id, preserving order."""
    grouped: dict[int, list[CohortPair]] = {}
    for pair in pairs:
        grouped.setdefault(pair.target_cohort_id, []).append(pair)
    return grouped
