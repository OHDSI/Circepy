from __future__ import annotations

from ..tables import COHORT_RESULT_SCHEMA
from .definitions import DemographicSubsetOperator


def apply_demographic_operator(relation, *, person, operator: DemographicSubsetOperator):
    relation_columns = list(COHORT_RESULT_SCHEMA.keys())
    joined = relation.join(
        person,
        predicates=[relation.subject_id == person.person_id],
        how="inner",
    )

    filtered = joined
    if operator.age_range is not None:
        min_age, max_age = operator.age_range
        age_years = relation.cohort_start_date.year() - person.year_of_birth
        if min_age is not None:
            filtered = filtered.filter(age_years >= int(min_age))
        if max_age is not None:
            filtered = filtered.filter(age_years <= int(max_age))

    if operator.gender_concept_ids:
        filtered = filtered.filter(
            person.gender_concept_id.isin(tuple(int(x) for x in operator.gender_concept_ids))
        )

    if operator.race_concept_ids and "race_concept_id" in person.columns:
        filtered = filtered.filter(
            person.race_concept_id.isin(tuple(int(x) for x in operator.race_concept_ids))
        )

    if operator.ethnicity_concept_ids and "ethnicity_concept_id" in person.columns:
        filtered = filtered.filter(
            person.ethnicity_concept_id.isin(
                tuple(int(x) for x in operator.ethnicity_concept_ids)
            )
        )

    return filtered.select(*[relation[column] for column in relation_columns]).distinct()
