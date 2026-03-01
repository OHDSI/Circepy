from __future__ import annotations

from collections import defaultdict
from typing import Dict, FrozenSet, Optional, Tuple

from ...cohortdefinition import BuildExpressionQueryOptions, CohortExpression
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
    criteria: Tuple[NormalizedCriterion, ...]
    observation_window: NormalizedObservationWindow | None
    primary_limit_type: str


@frozen_slots_dataclass
class NormalizedCohort:
    title: str | None
    options: BuildExpressionQueryOptions | None
    concept_sets: Dict[int, FrozenSet[int]]
    primary: NormalizedPrimaryCriteria
    additional_criteria: NormalizedCriteriaGroup | None
    inclusion_rules: Tuple[NormalizedInclusionRule, ...]
    censoring_criteria: Tuple[NormalizedCriterion, ...]
    censor_window: NormalizedPeriod | None
    collapse_settings: NormalizedCollapseSettings | None
    end_strategy: NormalizedEndStrategy | None


def _extract_codesets(concept_sets: list[ConceptSet]) -> Dict[int, FrozenSet[int]]:
    included: dict[int, set[int]] = defaultdict(set)
    excluded: dict[int, set[int]] = defaultdict(set)

    for concept_set in concept_sets or []:
        if concept_set is None or concept_set.id is None:
            continue
        set_id = int(concept_set.id)
        expression = concept_set.expression
        if not expression:
            continue

        if bool(expression.include_descendants) or bool(expression.include_mapped):
            raise UnsupportedFeatureError(
                "ConceptSet expansion flags includeDescendants/includeMapped are not "
                f"implemented in the Ibis executor (codeset_id={set_id})."
            )

        if expression.concept is not None and expression.concept.concept_id is not None:
            concept_id = int(expression.concept.concept_id)
            if expression.is_excluded:
                excluded[set_id].add(concept_id)
            else:
                included[set_id].add(concept_id)

        for item in expression.items or []:
            if item is None:
                continue
            if bool(item.include_descendants) or bool(item.include_mapped):
                raise UnsupportedFeatureError(
                    "ConceptSet item flags includeDescendants/includeMapped are not "
                    "implemented in the Ibis executor "
                    f"(codeset_id={set_id}, concept_id={getattr(item.concept, 'concept_id', None)})."
                )
            if item.concept is None or item.concept.concept_id is None:
                continue
            concept_id = int(item.concept.concept_id)
            if item.is_excluded:
                excluded[set_id].add(concept_id)
            else:
                included[set_id].add(concept_id)

    output: Dict[int, FrozenSet[int]] = {}
    for set_id, include_values in included.items():
        output[set_id] = frozenset(include_values - excluded.get(set_id, set()))
    return output


def normalize_cohort(
    expression: CohortExpression,
    options: Optional[BuildExpressionQueryOptions] = None,
) -> NormalizedCohort:
    primary = expression.primary_criteria
    if primary is None or not primary.criteria_list:
        raise ExecutionNormalizationError(
            "CohortExpression must contain non-empty primary criteria."
        )

    normalized_criteria = tuple(
        normalize_criterion(criteria) for criteria in primary.criteria_list
    )
    normalized_primary = NormalizedPrimaryCriteria(
        criteria=normalized_criteria,
        observation_window=normalize_observation_window(primary.observation_window),
        primary_limit_type=(
            (primary.primary_limit.type if primary.primary_limit else "all") or "all"
        ).lower(),
    )

    normalized_end_strategy = normalize_end_strategy(expression.end_strategy)
    if normalized_end_strategy is not None and normalized_end_strategy.kind == "custom_era":
        raise UnsupportedFeatureError(
            "custom_era end_strategy is not implemented in the Ibis executor."
        )

    return NormalizedCohort(
        title=expression.title,
        options=options,
        concept_sets=_extract_codesets(expression.concept_sets),
        primary=normalized_primary,
        additional_criteria=normalize_criteria_group(expression.additional_criteria),
        inclusion_rules=tuple(
            normalize_inclusion_rule(rule) for rule in expression.inclusion_rules
        ),
        censoring_criteria=tuple(
            normalize_criterion(criteria) for criteria in expression.censoring_criteria
        ),
        censor_window=normalize_period(expression.censor_window),
        collapse_settings=normalize_collapse_settings(expression.collapse_settings),
        end_strategy=normalized_end_strategy,
    )
