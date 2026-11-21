from __future__ import annotations

import ibis
import pandas as pd
import pytest

T2DM = 201826
CHF = 316139
OBESITY = 433736
ASTHMA = 317009
HBA1C = 3004410
GLUCOSE = 3004411
HIGH = 4328749
NORMAL = 4069590
METFORMIN = 1503297
GLUCOSE_ABOVE = 438557
GLUCOSE_NORMAL = 4069590


def _dates(values):
    return pd.Series(pd.to_datetime(values).date)


def _strings(values):
    return pd.Series(values, dtype="string")


def seed_cdm(connection) -> None:
    def create(name, data):
        connection.create_table(name, obj=ibis.memtable(pd.DataFrame(data)), overwrite=True)

    create(
        "person",
        {
            "person_id": [1, 2, 3, 4],
            "year_of_birth": [1980, 1950, 1975, 1990],
            "gender_concept_id": [8532, 8507, 8532, 8507],
        },
    )
    create(
        "observation_period",
        {
            "observation_period_id": [10, 11, 12, 13],
            "person_id": [1, 2, 3, 4],
            "observation_period_start_date": _dates(["2018-01-01", "2018-01-01", "2018-01-01", "2018-01-01"]),
            "observation_period_end_date": _dates(["2021-12-31", "2021-12-31", "2021-12-31", "2021-12-31"]),
        },
    )
    concepts = [
        (T2DM, "Type 2 diabetes", "Condition", "S"),
        (CHF, "Heart failure", "Condition", "S"),
        (OBESITY, "Obesity", "Condition", "S"),
        (ASTHMA, "Asthma", "Condition", "S"),
        (HBA1C, "HbA1c", "Measurement", "S"),
        (GLUCOSE, "Glucose", "Measurement", "S"),
        (HIGH, "High", "Meas Value", "S"),
        (NORMAL, "Normal", "Meas Value", "S"),
        (METFORMIN, "Metformin", "Drug", "S"),
        (8532, "Female", "Gender", "S"),
        (8507, "Male", "Gender", "S"),
    ]
    create(
        "concept",
        {
            "concept_id": [row[0] for row in concepts],
            "concept_name": _strings([row[1] for row in concepts]),
            "domain_id": _strings([row[2] for row in concepts]),
            "standard_concept": _strings([row[3] for row in concepts]),
            "invalid_reason": _strings([None] * len(concepts)),
            "vocabulary_id": _strings(["SNOMED"] * len(concepts)),
            "concept_class_id": _strings(["Clinical Finding"] * len(concepts)),
            "concept_code": _strings([str(row[0]) for row in concepts]),
        },
    )
    create(
        "concept_ancestor",
        {
            "ancestor_concept_id": [T2DM, CHF, OBESITY, ASTHMA, HBA1C, GLUCOSE],
            "descendant_concept_id": [T2DM, CHF, OBESITY, ASTHMA, HBA1C, GLUCOSE],
            "min_levels_of_separation": [0] * 6,
            "max_levels_of_separation": [0] * 6,
        },
    )
    create(
        "concept_relationship",
        {
            "concept_id_1": [T2DM],
            "concept_id_2": [T2DM],
            "relationship_id": ["Maps to"],
            "invalid_reason": _strings([None]),
        },
    )
    create(
        "condition_occurrence",
        {
            "condition_occurrence_id": [100, 101, 102, 103, 104, 105],
            "person_id": [1, 1, 2, 3, 4, 4],
            "condition_concept_id": [T2DM, CHF, CHF, T2DM, ASTHMA, OBESITY],
            "condition_start_date": _dates(
                ["2017-06-01", "2020-07-15", "2020-03-01", "2020-11-01", "2019-01-05", "2020-08-01"]
            ),
            "condition_end_date": _dates(
                ["2017-06-10", "2020-07-20", "2020-03-10", "2020-11-10", "2019-01-10", "2020-08-10"]
            ),
        },
    )
    create(
        "drug_exposure",
        {
            "drug_exposure_id": [200, 201, 202],
            "person_id": [1, 2, 3],
            "drug_concept_id": [METFORMIN, METFORMIN, 0],
            "drug_exposure_start_date": _dates(["2019-05-01", "2019-02-01", "2020-01-01"]),
            "drug_exposure_end_date": _dates(["2019-08-01", "2019-05-01", "2020-02-01"]),
            "days_supply": [92, 89, 32],
        },
    )
    create(
        "measurement",
        {
            "measurement_id": [300, 301, 302, 303, 304, 305],
            "person_id": [1, 1, 2, 3, 1, 4],
            "measurement_concept_id": [HBA1C, HBA1C, GLUCOSE, GLUCOSE, GLUCOSE, HBA1C],
            "measurement_date": _dates(
                ["2019-07-01", "2020-07-20", "2019-04-01", "2020-12-01", "2020-06-01", "2019-02-01"]
            ),
            "value_as_number": [9.2, 7.1, 120.0, None, 90.0, 6.0],
            "value_as_concept_id": [HIGH, NORMAL, HIGH, 0, NORMAL, NORMAL],
            "unit_concept_id": [8840, 8840, 8753, 8753, 8753, 8840],
            "range_low": [4.0, 4.0, 70.0, 70.0, 70.0, 4.0],
            "range_high": [6.0, 6.0, 100.0, 100.0, 100.0, 6.0],
            "operator_concept_id": [0, 0, 0, 0, 0, 0],
        },
    )
    create(
        "observation",
        {
            "observation_id": [400],
            "person_id": [1],
            "observation_concept_id": [OBESITY],
            "observation_date": _dates(["2019-06-01"]),
            "value_as_number": [30.0],
            "value_as_concept_id": [0],
            "unit_concept_id": [9529],
            "range_low": [18.5],
            "range_high": [25.0],
            "operator_concept_id": [0],
        },
    )
    create(
        "procedure_occurrence",
        {
            "procedure_occurrence_id": [500],
            "person_id": [2],
            "procedure_concept_id": [CHF],
            "procedure_date": _dates(["2019-03-02"]),
        },
    )
    create(
        "cohort",
        {
            "cohort_definition_id": [1, 1, 1, 1],
            "subject_id": [1, 2, 3, 4],
            "cohort_start_date": _dates(["2020-08-01", "2020-08-01", "2020-08-01", "2020-08-01"]),
            "cohort_end_date": _dates(["2021-08-01", "2021-08-01", "2021-08-01", "2021-08-01"]),
        },
    )


@pytest.fixture()
def backend():
    connection = ibis.duckdb.connect()
    seed_cdm(connection)
    yield connection
    connection.disconnect()
