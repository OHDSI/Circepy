from __future__ import annotations

from ...execution.typing import IbisBackendLike, Table
from ..config import GenerationConfig
from ..tables import COHORT_RESULT_SCHEMA
from .cohort import apply_cohort_subset_operator
from .definitions import (
    CohortSubsetOperator,
    DemographicSubsetOperator,
    LimitSubsetOperator,
    SubsetDefinition,
)
from .demographic import apply_demographic_operator
from .limit import apply_limit_operator


def _assert_cohort_relation_columns(relation: Table) -> None:
    required = set(COHORT_RESULT_SCHEMA.keys())
    missing = required.difference(relation.columns)
    if missing:
        missing_columns = ", ".join(sorted(missing))
        raise ValueError(
            "Subset operations require canonical cohort columns; missing "
            f"{missing_columns}."
        )


def apply_subset(
    relation: Table,
    *,
    backend: IbisBackendLike,
    config: GenerationConfig,
    definition: SubsetDefinition,
) -> Table:
    _assert_cohort_relation_columns(relation)

    current = relation
    person = None
    observation_period = None

    for operator in definition.operators:
        if isinstance(operator, DemographicSubsetOperator):
            if person is None:
                person = backend.table("person", database=config.cdm_schema)
            current = apply_demographic_operator(
                current,
                person=person,
                operator=operator,
            )
            continue

        if isinstance(operator, LimitSubsetOperator):
            if observation_period is None:
                observation_period = backend.table(
                    "observation_period",
                    database=config.cdm_schema,
                )
            current = apply_limit_operator(
                current,
                observation_period=observation_period,
                operator=operator,
            )
            continue

        if isinstance(operator, CohortSubsetOperator):
            cohorts = backend.table(config.cohort_table, database=config.results_schema)
            subset_relation = cohorts.filter(
                cohorts.cohort_definition_id == int(operator.subset_cohort_id)
            ).select(
                "subject_id",
                "cohort_start_date",
                "cohort_end_date",
            )
            current = apply_cohort_subset_operator(
                current,
                subset_relation=subset_relation,
                operator=operator,
            )
            continue

        raise ValueError(f"Unsupported subset operator type: {type(operator)!r}")

    return current
