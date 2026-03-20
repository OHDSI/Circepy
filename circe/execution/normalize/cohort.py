from __future__ import annotations

from ...cohortdefinition import CohortExpression
from ...vocabulary.concept import ConceptSet
from .._dataclass import frozen_slots_dataclass
from ..errors import ExecutionNormalizationError, UnsupportedFeatureError
from .collapse import NormalizedCollapseSettings, normalize_collapse_settings
from .criteria import NormalizedCriterion, normalize_criterion
from .end_strategy import NormalizedEndStrategy, normalize_end_strategy
from .groups import (
    NormalizedCriteriaGroup,
    NormalizedInclusionRule,
    normalize_criteria_group,
    normalize_inclusion_rule,
)
from .windows import (
    NormalizedObservationWindow,
    NormalizedPeriod,
    normalize_observation_window,
    normalize_period,
)


@frozen_slots_dataclass
class NormalizedPrimaryCriteria:
    criteria: tuple[NormalizedCriterion, ...]
    observation_window: NormalizedObservationWindow | None
    primary_limit_type: str


@frozen_slots_dataclass
class NormalizedResultLimits:
    qualified_limit_type: str
    expression_limit_type: str


@frozen_slots_dataclass
class NormalizedConceptSetItem:
    concept_id: int
    is_excluded: bool
    include_descendants: bool
    include_mapped: bool


@frozen_slots_dataclass
class NormalizedConceptSet:
    set_id: int
    items: tuple[NormalizedConceptSetItem, ...]


@frozen_slots_dataclass
class NormalizedCohort:
    title: str | None
    concept_sets: dict[int, NormalizedConceptSet]
    primary: NormalizedPrimaryCriteria
    result_limits: NormalizedResultLimits
    additional_criteria: NormalizedCriteriaGroup | None
    inclusion_rules: tuple[NormalizedInclusionRule, ...]
    censoring_criteria: tuple[NormalizedCriterion, ...]
    censor_window: NormalizedPeriod | None
    collapse_settings: NormalizedCollapseSettings | None
    end_strategy: NormalizedEndStrategy | None


def _normalized_item(
    *,
    concept_id: int,
    is_excluded: bool,
    include_descendants: bool,
    include_mapped: bool,
) -> NormalizedConceptSetItem:
    return NormalizedConceptSetItem(
        concept_id=int(concept_id),
        is_excluded=bool(is_excluded),
        include_descendants=bool(include_descendants),
        include_mapped=bool(include_mapped),
    )


def _extract_codesets(concept_sets: list[ConceptSet]) -> dict[int, NormalizedConceptSet]:
    output: dict[int, NormalizedConceptSet] = {}

    for concept_set in concept_sets or []:
        if concept_set is None or concept_set.id is None:
            continue
        set_id = int(concept_set.id)
        expression = concept_set.expression
        if not expression:
            continue

        items: list[NormalizedConceptSetItem] = []

        if expression.concept is not None and expression.concept.concept_id is not None:
            items.append(
                _normalized_item(
                    concept_id=int(expression.concept.concept_id),
                    is_excluded=bool(expression.is_excluded),
                    include_descendants=bool(expression.include_descendants),
                    include_mapped=bool(expression.include_mapped),
                )
            )

        for item in expression.items or []:
            if item is None:
                continue
            if item.concept is None or item.concept.concept_id is None:
                continue
            items.append(
                _normalized_item(
                    concept_id=int(item.concept.concept_id),
                    is_excluded=bool(item.is_excluded),
                    include_descendants=bool(item.include_descendants),
                    include_mapped=bool(item.include_mapped),
                )
            )

        output[set_id] = NormalizedConceptSet(
            set_id=set_id,
            items=tuple(items),
        )

    return output


def normalize_cohort(
    expression: CohortExpression,
) -> NormalizedCohort:
    primary = expression.primary_criteria
    if primary is None or not primary.criteria_list:
        raise ExecutionNormalizationError(
            "Ibis executor normalization error: CohortExpression must contain at least one primary criterion."
        )

    normalized_criteria = tuple(normalize_criterion(criteria) for criteria in primary.criteria_list)
    normalized_primary = NormalizedPrimaryCriteria(
        criteria=normalized_criteria,
        observation_window=normalize_observation_window(primary.observation_window),
        primary_limit_type=(
            (primary.primary_limit.type if primary.primary_limit else "all") or "all"
        ).lower(),
    )
    normalized_limits = NormalizedResultLimits(
        qualified_limit_type=(
            (expression.qualified_limit.type if expression.qualified_limit else "all") or "all"
        ).lower(),
        expression_limit_type=(
            (expression.expression_limit.type if expression.expression_limit else "all") or "all"
        ).lower(),
    )

    normalized_end_strategy = normalize_end_strategy(expression.end_strategy)
    if normalized_end_strategy is not None and normalized_end_strategy.kind == "custom_era":
        raise UnsupportedFeatureError(
            "Ibis executor normalization error: custom_era end strategy is not supported."
        )

    return NormalizedCohort(
        title=expression.title,
        concept_sets=_extract_codesets(expression.concept_sets),
        primary=normalized_primary,
        result_limits=normalized_limits,
        additional_criteria=normalize_criteria_group(expression.additional_criteria),
        inclusion_rules=tuple(normalize_inclusion_rule(rule) for rule in expression.inclusion_rules),
        censoring_criteria=tuple(normalize_criterion(criteria) for criteria in expression.censoring_criteria),
        censor_window=normalize_period(expression.censor_window),
        collapse_settings=normalize_collapse_settings(expression.collapse_settings),
        end_strategy=normalized_end_strategy,
    )
