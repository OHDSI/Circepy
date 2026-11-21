"""Decomposable cohort templates for feature construction.

A template is a base cohort plus an ordered list of v1-placed refinements from
:mod:`circe.decomposition.operators`.  Flattening applies the refinements to a
copy of the base, producing a normal ``CohortExpression``.  That is what lets a
family of features share an expensive entry population when they are generated
with ``generate_cohort_set(..., shared=True)``.

``CohortTemplate`` builds cohorts; ``FeatureTemplate`` builds features.  Both
are immutable, so variants do not mutate their parent template.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ..cohortdefinition.cohort import CohortExpression
from ..decomposition.operators import Refinement
from .model import (
    _UNSET,
    CohortFeature,
    FeatureAggregation,
    FeatureSet,
    FeatureWindow,
)

__all__ = [
    "CohortTemplate",
    "FeatureTemplate",
    "expand_templates",
    "template_feature_set",
]


@dataclass(frozen=True)
class CohortTemplate:
    """A base cohort plus refinements that can be flattened or decomposed."""

    name: str
    base: CohortExpression
    refinements: tuple[Refinement, ...] = ()

    def flatten(self, *, title: str | None = None) -> CohortExpression:
        expression = self.base.model_copy(deep=True)
        for refinement in self.refinements:
            refinement.apply(expression)
        if title is not None:
            expression.title = title
        return expression

    def decompose(self) -> tuple[CohortExpression, tuple[Refinement, ...]]:
        return self.base, self.refinements

    def variant(self, name: str, *refinements: Refinement) -> CohortTemplate:
        return CohortTemplate(
            name=name,
            base=self.base,
            refinements=(*self.refinements, *refinements),
        )

    def to_feature(
        self,
        *,
        feature_id: int,
        name: str | None = None,
        aggregation: FeatureAggregation = "exists",
        window: FeatureWindow | None | object = _UNSET,
        tags: tuple[str, ...] = (),
    ) -> CohortFeature:
        return CohortFeature(
            feature_id=feature_id,
            name=name or self.name,
            cohort=self.flatten(title=name or self.name),
            aggregation=aggregation,
            window=FeatureWindow() if window is _UNSET else window,
            tags=tags,
        )

    def describe(self) -> str:
        suffix = "".join(f" + {refinement.describe()}" for refinement in self.refinements)
        return f"{self.name}{suffix}"


@dataclass(frozen=True)
class FeatureTemplate:
    """A base feature plus refinements applied to its cohort expression."""

    name: str
    base: CohortFeature
    refinements: tuple[Refinement, ...] = ()

    def build(
        self,
        *,
        feature_id: int | None = None,
        name: str | None = None,
        aggregation: FeatureAggregation | None = None,
        window: FeatureWindow | None | object = _UNSET,
        tags: tuple[str, ...] = (),
    ) -> CohortFeature:
        expression = self.base.to_cohort()
        for refinement in self.refinements:
            refinement.apply(expression)
        feature_name = name or self.name
        expression.title = feature_name
        return CohortFeature(
            feature_id=feature_id or self.base.feature_id,
            name=feature_name,
            cohort=expression,
            aggregation=aggregation or self.base.aggregation,
            window=self.base.window if window is _UNSET else window,
            tags=tags or self.base.tags,
        )

    def variant(self, name: str, *refinements: Refinement) -> FeatureTemplate:
        return FeatureTemplate(
            name=name,
            base=self.base,
            refinements=(*self.refinements, *refinements),
        )


def expand_templates(
    templates: Iterable[CohortTemplate],
    *,
    start_id: int = 1,
    aggregation: FeatureAggregation = "exists",
    window: FeatureWindow | None | object = _UNSET,
) -> FeatureSet:
    """Flatten templates into a feature set, assigning sequential ids."""
    features = []
    for index, template in enumerate(templates, start=start_id):
        features.append(
            template.to_feature(
                feature_id=index,
                aggregation=aggregation,
                window=window,
            )
        )
    return FeatureSet(features=features)


def template_feature_set(
    templates: Iterable[FeatureTemplate],
    *,
    start_id: int = 1,
) -> FeatureSet:
    features = []
    for index, template in enumerate(templates, start=start_id):
        features.append(template.build(feature_id=index))
    return FeatureSet(features=features)
