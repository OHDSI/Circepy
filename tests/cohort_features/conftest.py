from __future__ import annotations

import ibis
import pandas as pd
import pytest

T2DM = 201826
CHF = 316139
METFORMIN = 1503297


def _strings(values):
    return pd.Series(values, dtype="string")


def _dates(values):
    return pd.Series(pd.to_datetime(values).date)


def seed_cdm(connection) -> None:
    def create(name, data):
        connection.create_table(name, obj=ibis.memtable(pd.DataFrame(data)), overwrite=True)

    create(
        "person",
        {
            "person_id": [1, 2, 3],
            "year_of_birth": [1980, 1950, 1975],
            "gender_concept_id": [8532, 8507, 8532],
            "race_concept_id": [8527, 8527, 8527],
            "ethnicity_concept_id": [38003564, 38003564, 38003564],
        },
    )
    create(
        "observation_period",
        {
            "observation_period_id": [10, 11, 12],
            "person_id": [1, 2, 3],
            "observation_period_start_date": _dates(["2019-01-01"] * 3),
            "observation_period_end_date": _dates(["2022-12-31"] * 3),
        },
    )
    create(
        "concept",
        {
            "concept_id": [T2DM, CHF, METFORMIN],
            "concept_name": [
                "Type 2 diabetes mellitus",
                "Congestive heart failure",
                "Metformin",
            ],
            "invalid_reason": _strings([None] * 3),
            "standard_concept": _strings(["S"] * 3),
            "domain_id": _strings(["Condition", "Condition", "Drug"]),
            "vocabulary_id": _strings(["SNOMED", "SNOMED", "RxNorm"]),
            "concept_class_id": _strings(["Clinical Finding", "Clinical Finding", "Ingredient"]),
            "concept_code": _strings(["44054006", "42343007", "860975"]),
        },
    )
    create(
        "concept_ancestor",
        {
            "ancestor_concept_id": [T2DM, CHF, METFORMIN],
            "descendant_concept_id": [T2DM, CHF, METFORMIN],
            "min_levels_of_separation": [0, 0, 0],
            "max_levels_of_separation": [0, 0, 0],
        },
    )
    create(
        "concept_relationship",
        {
            "concept_id_1": [T2DM, CHF, METFORMIN],
            "concept_id_2": [T2DM, CHF, METFORMIN],
            "relationship_id": ["Maps to"] * 3,
            "invalid_reason": _strings([None] * 3),
        },
    )
    create(
        "condition_occurrence",
        {
            "condition_occurrence_id": [100, 101, 102, 103, 104],
            "person_id": [1, 1, 2, 3, 1],
            "condition_concept_id": [T2DM, CHF, CHF, T2DM, T2DM],
            "condition_start_date": _dates(
                ["2020-01-15", "2020-02-01", "2020-03-01", "2020-01-10", "2020-06-01"]
            ),
            "condition_end_date": _dates(
                ["2020-01-20", "2020-02-05", "2020-03-10", "2020-01-12", "2020-06-05"]
            ),
        },
    )
    create(
        "drug_exposure",
        {
            "drug_exposure_id": [200, 201],
            "person_id": [1, 2],
            "drug_concept_id": [METFORMIN, METFORMIN],
            "drug_exposure_start_date": _dates(["2020-01-05", "2020-02-10"]),
            "drug_exposure_end_date": _dates(["2020-06-01", "2020-05-01"]),
            "days_supply": [150, 80],
            "quantity": [150.0, 80.0],
            "refills": [0, 0],
        },
    )
    create(
        "cohort",
        {
            "cohort_definition_id": [1, 1, 1],
            "subject_id": [1, 2, 3],
            "cohort_start_date": _dates(["2021-01-01"] * 3),
            "cohort_end_date": _dates(["2021-12-31"] * 3),
        },
    )


@pytest.fixture()
def backend():
    connection = ibis.duckdb.connect()
    seed_cdm(connection)
    yield connection
    connection.disconnect()
