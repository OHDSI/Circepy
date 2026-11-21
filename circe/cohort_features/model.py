"""Cohort-first feature definitions.

The central idea is symmetry:

* any cohort can be used as a feature (does the subject enter this cohort in the
  feature window?);
* any feature can be turned into a cohort (a feature *is* a cohort with a
  window and an aggregation attached).

``CohortFeature`` wraps an arbitrary :class:`CohortExpression`, so existing
cohort definitions can be reused without rewriting them.  ``CriteriaFeature``
is the lower-level form for a single criterion plus concept sets and is the
bridge used when a feature is constructed from scratch.

Both forms expose ``to_cohort()``.  ``CohortFeature.to_criteria_group()`` is the
reverse projection for the subset of cohorts that are a pure primary-criteria
selection (no additional criteria or inclusion rules), which is what makes a
cohort reusable inside another cohort definition.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from ..cohort_definition_set._core import CohortDefinition, CohortDefinitionSet
from ..cohortdefinition.cohort import CohortExpression
from ..cohortdefinition.core import ObservationFilter, ResultLimit
from ..cohortdefinition.criteria import (
    CorelatedCriteria,
    Criteria,
    CriteriaGroup,
    Occurrence,
    PrimaryCriteria,
)
from ..vocabulary.concept import ConceptSet

if TYPE_CHECKING:
    pass

__all__ = [
    "CohortFeature",
    "CriteriaFeature",
    "Feature",
    "FeatureAggregation",
    "FeatureSet",
    "FeatureWindow",
    "NotExpressibleAsCriteriaError",
]

FeatureAggregation = Literal["exists", "count"]

_UNSET = object()


class NotExpressibleAsCriteriaError(ValueError):
    """Raised when a cohort cannot be reduced to one criteria group."""


@dataclass(frozen=True)
class FeatureWindow:
    """Window relative to the target population's index date.

    ``start_days=None`` means unbounded prior history.  ``basis`` selects
    whether the feature cohort's start or end date is compared with the window.
    ``overlap=True`` matches when the feature cohort interval intersects the
    window.
    """

    start_days: int | None = -365
    end_days: int = 0
    basis: Literal["start", "end"] = "start"
    overlap: bool = False

    def __post_init__(self) -> None:
        if self.start_days is not None and self.start_days > self.end_days:
            raise ValueError(
                f"FeatureWindow start_days ({self.start_days}) must not exceed end_days ({self.end_days})."
            )

    def canonical(self) -> dict[str, Any]:
        return {
            "start_days": self.start_days,
            "end_days": self.end_days,
            "basis": self.basis,
            "overlap": self.overlap,
        }


@dataclass
class CohortFeature:
    """A cohort definition used as a feature."""

    feature_id: int
    name: str
    cohort: CohortExpression
    aggregation: FeatureAggregation = "exists"
    window: FeatureWindow | None = field(default_factory=FeatureWindow)
    source_cohort_id: int | None = None
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.feature_id < 1:
            raise ValueError("feature_id must be >= 1.")
        if self.aggregation not in {"exists", "count"}:
            raise ValueError(f"Unsupported aggregation {self.aggregation!r}.")

    def to_cohort(self) -> CohortExpression:
        """Return the feature as a standalone cohort expression."""
        return self.cohort.model_copy(deep=True)

    def checksum(self) -> str:
        return self.cohort.checksum()

    def to_criteria_group(self) -> CriteriaGroup:
        """Project a pure primary-criteria cohort back to a criteria group."""
        expression = self.cohort
        if expression.additional_criteria is not None and not expression.additional_criteria.is_empty():
            raise NotExpressibleAsCriteriaError(
                "Cohort has additional criteria; project the primary criteria explicitly."
            )
        if expression.inclusion_rules:
            raise NotExpressibleAsCriteriaError(
                "Cohort has inclusion rules; it cannot be represented as a single criteria group."
            )
        primary = expression.primary_criteria
        if primary is None or not primary.criteria_list:
            raise NotExpressibleAsCriteriaError("Cohort has no primary criteria.")

        correlated = [
            CorelatedCriteria(
                criteria=criterion,
                occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
            )
            for criterion in primary.criteria_list
        ]
        group_type = "ANY" if len(correlated) > 1 else "ALL"
        return CriteriaGroup(criteria_list=correlated, type=group_type)

    def with_window(self, window: FeatureWindow | None) -> CohortFeature:
        return CohortFeature(
            feature_id=self.feature_id,
            name=self.name,
            cohort=self.cohort,
            aggregation=self.aggregation,
            window=window,
            source_cohort_id=self.source_cohort_id,
            tags=self.tags,
        )

    def with_aggregation(self, aggregation: FeatureAggregation) -> CohortFeature:
        return CohortFeature(
            feature_id=self.feature_id,
            name=self.name,
            cohort=self.cohort,
            aggregation=aggregation,
            window=self.window,
            source_cohort_id=self.source_cohort_id,
            tags=self.tags,
        )

    @classmethod
    def from_cohort_definition(
        cls,
        definition: CohortDefinition,
        *,
        aggregation: FeatureAggregation = "exists",
        window: FeatureWindow | None | object = _UNSET,
        tags: tuple[str, ...] = (),
    ) -> CohortFeature:
        return cls(
            feature_id=definition.cohort_id,
            name=definition.cohort_name,
            cohort=definition.expression,
            aggregation=aggregation,
            window=FeatureWindow() if window is _UNSET else window,
            source_cohort_id=definition.cohort_id,
            tags=tags,
        )


@dataclass
class CriteriaFeature:
    """A feature built from one CIRCE criterion and its concept sets."""

    feature_id: int
    name: str
    criterion: Criteria
    concept_sets: tuple[ConceptSet, ...] = ()
    observation_window: ObservationFilter = field(
        default_factory=lambda: ObservationFilter(prior_days=0, post_days=0)
    )
    aggregation: FeatureAggregation = "exists"
    window: FeatureWindow | None = field(default_factory=FeatureWindow)
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.feature_id < 1:
            raise ValueError("feature_id must be >= 1.")
        if self.aggregation not in {"exists", "count"}:
            raise ValueError(f"Unsupported aggregation {self.aggregation!r}.")

    def to_cohort(self) -> CohortExpression:
        return CohortExpression(
            concept_sets=[concept_set.model_copy(deep=True) for concept_set in self.concept_sets],
            primary_criteria=PrimaryCriteria(
                criteria_list=[self.criterion.model_copy(deep=True)],
                observation_window=self.observation_window.model_copy(deep=True),
                primary_limit=ResultLimit(type="All"),
            ),
            title=self.name,
        )

    def checksum(self) -> str:
        return self.to_cohort().checksum()

    def to_criteria_group(self) -> CriteriaGroup:
        return CriteriaGroup(
            criteria_list=[
                CorelatedCriteria(
                    criteria=self.criterion.model_copy(deep=True),
                    occurrence=Occurrence(type=Occurrence._AT_LEAST, count=1),
                )
            ],
            type="ALL",
        )


Feature = CohortFeature | CriteriaFeature


@dataclass
class FeatureSet:
    """An ordered collection of cohort-first features."""

    features: list[Feature]
    name: str | None = None

    def __post_init__(self) -> None:
        ids = [feature.feature_id for feature in self.features]
        if len(ids) != len(set(ids)):
            raise ValueError("FeatureSet feature_ids must be unique.")
        if not self.features:
            raise ValueError("FeatureSet requires at least one feature.")

    def __len__(self) -> int:
        return len(self.features)

    def __iter__(self):
        return iter(self.features)

    def __getitem__(self, feature_id: int) -> Feature:
        for feature in self.features:
            if feature.feature_id == feature_id:
                return feature
        raise KeyError(f"No feature with feature_id={feature_id}.")

    def to_cohort_definition_set(self, *, start_id: int | None = None) -> CohortDefinitionSet:
        """Turn every feature into a cohort definition.

        Feature ids are preserved.  *start_id* is only used when a feature does
        not have a positive id (not currently possible, kept for API clarity).
        """
        cds = CohortDefinitionSet()
        next_id = start_id or 1
        for feature in self.features:
            cohort_id = feature.feature_id if feature.feature_id > 0 else next_id
            next_id = max(next_id, cohort_id + 1)
            cds.add(
                cohort_id=cohort_id,
                cohort_name=feature.name,
                expression=feature.to_cohort(),
            )
        return cds

    @classmethod
    def from_cohort_definition_set(
        cls,
        cohort_set: CohortDefinitionSet,
        *,
        aggregation: FeatureAggregation = "exists",
        window: FeatureWindow | None | object = _UNSET,
        tags: tuple[str, ...] = (),
    ) -> FeatureSet:
        return cls(
            features=[
                CohortFeature.from_cohort_definition(
                    definition,
                    aggregation=aggregation,
                    window=window,
                    tags=tags,
                )
                for definition in cohort_set
            ],
            name=None,
        )

    @classmethod
    def from_cohorts(
        cls,
        cohorts: Iterable[CohortExpression],
        *,
        names: Iterable[str] | None = None,
        aggregation: FeatureAggregation = "exists",
        window: FeatureWindow | None | object = _UNSET,
        tags: tuple[str, ...] = (),
    ) -> FeatureSet:
        names_list = list(names) if names is not None else None
        features = []
        for index, cohort in enumerate(cohorts, start=1):
            name = names_list[index - 1] if names_list is not None else f"feature_{index}"
            features.append(
                CohortFeature(
                    feature_id=index,
                    name=name,
                    cohort=cohort,
                    aggregation=aggregation,
                    window=FeatureWindow() if window is _UNSET else window,
                    tags=tags,
                )
            )
        return cls(features=features)

    def with_window(self, window: FeatureWindow | None) -> FeatureSet:
        updated: list[Feature] = []
        for feature in self.features:
            if isinstance(feature, CohortFeature):
                updated.append(feature.with_window(window))
            else:
                updated.append(
                    CriteriaFeature(
                        feature_id=feature.feature_id,
                        name=feature.name,
                        criterion=feature.criterion,
                        concept_sets=feature.concept_sets,
                        observation_window=feature.observation_window,
                        aggregation=feature.aggregation,
                        window=window,
                        tags=feature.tags,
                    )
                )
        return FeatureSet(features=updated, name=self.name)
