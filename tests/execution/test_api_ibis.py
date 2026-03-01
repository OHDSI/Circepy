from __future__ import annotations

import pytest

from circe.api import build_cohort_ibis
from circe.cohortdefinition import (
    BuildExpressionQueryOptions,
    ConditionEra,
    CohortExpression,
    ConditionOccurrence,
    Death,
    DeviceExposure,
    DoseEra,
    DrugExposure,
    DrugEra,
    LocationRegion,
    Measurement,
    Observation,
    ObservationPeriod,
    PayerPlanPeriod,
    PrimaryCriteria,
    ProcedureOccurrence,
    Specimen,
    VisitDetail,
    VisitOccurrence,
)
from circe.cohortdefinition.core import CustomEraStrategy, NumericRange
from circe.execution.errors import UnsupportedFeatureError
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


def _make_concept_set(set_id: int, concept_id: int) -> ConceptSet:
    return ConceptSet(
        id=set_id,
        expression=ConceptSetExpression(
            items=[ConceptSetItem(concept=Concept(conceptId=concept_id))]
        ),
    )


def _seed_common_tables(conn, ibis):
    conn.create_table(
        "person",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "year_of_birth": [1980, 2015],
                "gender_concept_id": [8507, 8507],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "observation_period",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "observation_period_id": [10, 11],
                "observation_period_start_date": ["2019-01-01", "2019-01-01"],
                "observation_period_end_date": ["2021-12-31", "2021-12-31"],
            }
        ),
        overwrite=True,
    )


def _seed_vocabulary_tables(conn, ibis):
    conn.create_table(
        "concept",
        obj=ibis.memtable(
            {
                "concept_id": [100, 101, 102, 200, 201],
                "invalid_reason": [None, None, "D", None, None],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "concept_ancestor",
        obj=ibis.memtable(
            {
                "ancestor_concept_id": [100, 100],
                "descendant_concept_id": [101, 102],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "concept_relationship",
        obj=ibis.memtable(
            {
                "concept_id_1": [200, 201],
                "concept_id_2": [100, 101],
                "relationship_id": ["Maps to", "Maps to"],
                "invalid_reason": [None, "D"],
            }
        ),
        overwrite=True,
    )


def test_build_cohort_ibis_condition_occurrence_mvp():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 1, 2],
                "condition_occurrence_id": [100, 101, 102],
                "condition_concept_id": [111, 111, 999],
                "condition_start_date": ["2020-01-01", "2020-02-01", "2020-01-05"],
                "condition_end_date": ["2020-01-02", "2020-02-02", "2020-01-06"],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(1, 111)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[
                ConditionOccurrence(
                    codeset_id=1,
                    first=True,
                    age=NumericRange(op="gte", value=18),
                )
            ]
        ),
    )

    table = build_cohort_ibis(expression, backend=conn, cdm_schema="main")
    result = table.execute()

    assert set(result.columns) >= {
        "person_id",
        "event_id",
        "start_date",
        "end_date",
        "domain",
        "criterion_type",
    }
    assert set(result.person_id) == {1}
    assert len(result) == 1


def test_build_cohort_ibis_concept_set_resolves_descendants_and_mapped():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    _seed_vocabulary_tables(conn, ibis)
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 1, 1, 1, 1, 2],
                "condition_occurrence_id": [1000, 1001, 1002, 1003, 1004, 1005],
                "condition_concept_id": [100, 101, 102, 200, 201, 999],
                "condition_start_date": [
                    "2020-01-01",
                    "2020-01-02",
                    "2020-01-03",
                    "2020-01-04",
                    "2020-01-05",
                    "2020-01-01",
                ],
                "condition_end_date": [
                    "2020-01-01",
                    "2020-01-02",
                    "2020-01-03",
                    "2020-01-04",
                    "2020-01-05",
                    "2020-01-01",
                ],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[
            ConceptSet(
                id=1,
                expression=ConceptSetExpression(
                    items=[
                        ConceptSetItem(
                            concept=Concept(conceptId=100),
                            includeDescendants=True,
                            includeMapped=True,
                        ),
                        ConceptSetItem(
                            concept=Concept(conceptId=101),
                            isExcluded=True,
                            includeMapped=True,
                        ),
                    ]
                ),
            )
        ],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
    )

    result = build_cohort_ibis(expression, backend=conn, cdm_schema="main").execute()
    assert set(result.person_id) == {1}
    assert set(result.concept_id) == {100, 200}


def test_build_cohort_ibis_uses_vocabulary_schema_option_for_expansion():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    conn.raw_sql("CREATE SCHEMA vocab")
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 1],
                "condition_occurrence_id": [2000, 2001],
                "condition_concept_id": [100, 101],
                "condition_start_date": ["2020-01-01", "2020-01-02"],
                "condition_end_date": ["2020-01-01", "2020-01-02"],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "concept",
        obj=ibis.memtable(
            {"concept_id": [100, 101, 102], "invalid_reason": [None, None, "D"]}
        ),
        database="vocab",
        overwrite=True,
    )
    conn.create_table(
        "concept_ancestor",
        obj=ibis.memtable(
            {"ancestor_concept_id": [100], "descendant_concept_id": [101]}
        ),
        database="vocab",
        overwrite=True,
    )
    conn.create_table(
        "concept_relationship",
        obj=ibis.memtable(
            {
                "concept_id_1": [9999, 9998],
                "concept_id_2": [100, 101],
                "relationship_id": ["Maps to", "Maps to"],
                "invalid_reason": [None, "D"],
            }
        ),
        database="vocab",
        overwrite=True,
    )

    options = BuildExpressionQueryOptions()
    options.vocabulary_schema = "vocab"

    expression = CohortExpression(
        concept_sets=[
            ConceptSet(
                id=1,
                expression=ConceptSetExpression(
                    items=[
                        ConceptSetItem(
                            concept=Concept(conceptId=100),
                            includeDescendants=True,
                        )
                    ]
                ),
            )
        ],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
    )

    result = build_cohort_ibis(
        expression,
        backend=conn,
        cdm_schema="main",
        options=options,
    ).execute()
    assert set(result.concept_id) == {100, 101}


def test_build_cohort_ibis_drug_exposure_mvp():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "drug_exposure",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "drug_exposure_id": [200, 201],
                "drug_concept_id": [222, 999],
                "drug_exposure_start_date": ["2020-03-01", "2020-03-01"],
                "drug_exposure_end_date": ["2020-03-02", "2020-03-02"],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(2, 222)],
        primary_criteria=PrimaryCriteria(criteria_list=[DrugExposure(codeset_id=2)]),
    )

    table = build_cohort_ibis(expression, backend=conn, cdm_schema="main")
    result = table.execute()

    assert set(result.person_id) == {1}
    assert all(result.domain == "drug_exposure")


def test_build_cohort_ibis_visit_occurrence_mvp():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "visit_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "visit_occurrence_id": [300, 301],
                "visit_concept_id": [333, 999],
                "visit_start_date": ["2020-05-01", "2020-05-01"],
                "visit_end_date": ["2020-05-02", "2020-05-02"],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(3, 333)],
        primary_criteria=PrimaryCriteria(criteria_list=[VisitOccurrence(codeset_id=3)]),
    )

    table = build_cohort_ibis(expression, backend=conn, cdm_schema="main")
    result = table.execute()

    assert set(result.person_id) == {1}
    assert all(result.domain == "visit_occurrence")


def test_build_cohort_ibis_measurement():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "measurement",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "measurement_id": [400, 401],
                "measurement_concept_id": [444, 999],
                "measurement_date": ["2020-06-01", "2020-06-01"],
                "visit_occurrence_id": [10, 11],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(4, 444)],
        primary_criteria=PrimaryCriteria(criteria_list=[Measurement(codeset_id=4)]),
    )

    table = build_cohort_ibis(expression, backend=conn, cdm_schema="main")
    result = table.execute()

    assert set(result.person_id) == {1}
    assert all(result.domain == "measurement")


def test_build_cohort_ibis_measurement_with_value_and_unit_filters():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "measurement",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "measurement_id": [410, 411],
                "measurement_concept_id": [444, 444],
                "measurement_date": ["2020-06-01", "2020-06-01"],
                "visit_occurrence_id": [10, 11],
                "value_as_number": [5.0, 15.0],
                "unit_concept_id": [9001, 9002],
                "value_as_concept_id": [7001, 7002],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(4, 444)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[
                Measurement(
                    codeset_id=4,
                    value_as_number=NumericRange(op="gte", value=10),
                    unit=[Concept(conceptId=9002)],
                    value_as_concept=[Concept(conceptId=7002)],
                )
            ]
        ),
    )

    table = build_cohort_ibis(expression, backend=conn, cdm_schema="main")
    result = table.execute()

    assert set(result.person_id) == {2}
    assert all(result.domain == "measurement")


def test_build_cohort_ibis_procedure_occurrence():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "procedure_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "procedure_occurrence_id": [500, 501],
                "procedure_concept_id": [555, 999],
                "procedure_date": ["2020-07-01", "2020-07-01"],
                "visit_occurrence_id": [10, 11],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(5, 555)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[ProcedureOccurrence(codeset_id=5)]
        ),
    )

    table = build_cohort_ibis(expression, backend=conn, cdm_schema="main")
    result = table.execute()

    assert set(result.person_id) == {1}
    assert all(result.domain == "procedure_occurrence")


def test_build_cohort_ibis_procedure_occurrence_with_domain_filters():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "procedure_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "procedure_occurrence_id": [510, 511],
                "procedure_concept_id": [555, 555],
                "procedure_date": ["2020-07-01", "2020-07-01"],
                "visit_occurrence_id": [10, 11],
                "procedure_type_concept_id": [901, 902],
                "modifier_concept_id": [1001, 1002],
                "quantity": [1, 5],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(5, 555)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[
                ProcedureOccurrence(
                    codeset_id=5,
                    procedure_type=[Concept(conceptId=902)],
                    quantity=NumericRange(op="gte", value=5),
                )
            ]
        ),
    )

    table = build_cohort_ibis(expression, backend=conn, cdm_schema="main")
    result = table.execute()

    assert set(result.person_id) == {2}
    assert all(result.domain == "procedure_occurrence")


def test_build_cohort_ibis_observation():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "observation",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "observation_id": [600, 601],
                "observation_concept_id": [666, 999],
                "observation_date": ["2020-08-01", "2020-08-01"],
                "visit_occurrence_id": [10, 11],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(6, 666)],
        primary_criteria=PrimaryCriteria(criteria_list=[Observation(codeset_id=6)]),
    )

    table = build_cohort_ibis(expression, backend=conn, cdm_schema="main")
    result = table.execute()

    assert set(result.person_id) == {1}
    assert all(result.domain == "observation")


def test_build_cohort_ibis_observation_with_domain_filters():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "observation",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "observation_id": [610, 611],
                "observation_concept_id": [666, 666],
                "observation_date": ["2020-08-01", "2020-08-01"],
                "visit_occurrence_id": [10, 11],
                "observation_type_concept_id": [2001, 2002],
                "value_as_number": [1.0, 20.0],
                "value_as_string": ["low", "high"],
                "value_as_concept_id": [3001, 3002],
                "unit_concept_id": [4001, 4002],
                "qualifier_concept_id": [5001, 5002],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(6, 666)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[
                Observation(
                    codeset_id=6,
                    observation_type=[Concept(conceptId=2002)],
                    value_as_number=NumericRange(op="gte", value=10),
                    value_as_concept=[Concept(conceptId=3002)],
                    unit=[Concept(conceptId=4002)],
                )
            ]
        ),
    )

    table = build_cohort_ibis(expression, backend=conn, cdm_schema="main")
    result = table.execute()

    assert set(result.person_id) == {2}
    assert all(result.domain == "observation")


def test_build_cohort_ibis_visit_detail():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "visit_detail",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "visit_detail_id": [700, 701],
                "visit_detail_concept_id": [777, 999],
                "visit_detail_start_date": ["2020-09-01", "2020-09-01"],
                "visit_detail_end_date": ["2020-09-02", "2020-09-02"],
                "visit_occurrence_id": [10, 11],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(7, 777)],
        primary_criteria=PrimaryCriteria(criteria_list=[VisitDetail(codeset_id=7)]),
    )

    table = build_cohort_ibis(expression, backend=conn, cdm_schema="main")
    result = table.execute()

    assert set(result.person_id) == {1}
    assert all(result.domain == "visit_detail")


def test_build_cohort_ibis_visit_detail_with_domain_filters():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "visit_detail",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "visit_detail_id": [710, 711],
                "visit_detail_concept_id": [777, 777],
                "visit_detail_start_date": ["2020-09-01", "2020-09-01"],
                "visit_detail_end_date": ["2020-09-02", "2020-09-02"],
                "visit_occurrence_id": [10, 11],
                "visit_detail_type_concept_id": [6001, 6002],
                "discharge_to_concept_id": [7001, 7002],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(7, 777)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[
                VisitDetail(
                    codeset_id=7,
                    visit_detail_type=[Concept(conceptId=6002)],
                    discharge_to=[Concept(conceptId=7002)],
                )
            ]
        ),
    )

    table = build_cohort_ibis(expression, backend=conn, cdm_schema="main")
    result = table.execute()

    assert set(result.person_id) == {2}
    assert all(result.domain == "visit_detail")


def test_build_cohort_ibis_device_exposure():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "device_exposure",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "device_exposure_id": [800, 801],
                "device_concept_id": [888, 999],
                "device_exposure_start_date": ["2020-10-01", "2020-10-01"],
                "device_exposure_end_date": ["2020-10-02", "2020-10-02"],
                "visit_occurrence_id": [10, 11],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(8, 888)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[DeviceExposure(codeset_id=8)]
        ),
    )

    table = build_cohort_ibis(expression, backend=conn, cdm_schema="main")
    result = table.execute()

    assert set(result.person_id) == {1}
    assert all(result.domain == "device_exposure")


def test_build_cohort_ibis_specimen():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "specimen",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "specimen_id": [900, 901],
                "specimen_concept_id": [9990, 9991],
                "specimen_date": ["2020-11-01", "2020-11-01"],
                "visit_occurrence_id": [10, 11],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(9, 9990)],
        primary_criteria=PrimaryCriteria(criteria_list=[Specimen(codeset_id=9)]),
    )

    table = build_cohort_ibis(expression, backend=conn, cdm_schema="main")
    result = table.execute()

    assert set(result.person_id) == {1}
    assert all(result.domain == "specimen")


def test_build_cohort_ibis_death():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "death",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "cause_concept_id": [10001, 10002],
                "cause_source_concept_id": [20001, 20002],
                "death_date": ["2020-12-01", "2020-12-01"],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(10, 10001)],
        primary_criteria=PrimaryCriteria(criteria_list=[Death(codeset_id=10)]),
    )

    table = build_cohort_ibis(expression, backend=conn, cdm_schema="main")
    result = table.execute()

    assert set(result.person_id) == {1}
    assert all(result.domain == "death")


def test_build_cohort_ibis_observation_period():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)

    expression = CohortExpression(
        primary_criteria=PrimaryCriteria(criteria_list=[ObservationPeriod()]),
    )

    table = build_cohort_ibis(expression, backend=conn, cdm_schema="main")
    result = table.execute()

    assert set(result.person_id) == {1, 2}
    assert all(result.domain == "observation_period")


def test_build_cohort_ibis_payer_plan_period():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "payer_plan_period",
        obj=ibis.memtable(
            {
                "person_id": [1],
                "payer_plan_period_id": [1100],
                "payer_concept_id": [12345],
                "payer_source_concept_id": [54321],
                "payer_plan_period_start_date": ["2020-01-01"],
                "payer_plan_period_end_date": ["2020-12-31"],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        primary_criteria=PrimaryCriteria(criteria_list=[PayerPlanPeriod()]),
    )

    table = build_cohort_ibis(expression, backend=conn, cdm_schema="main")
    result = table.execute()

    assert set(result.person_id) == {1}
    assert all(result.domain == "payer_plan_period")


def test_build_cohort_ibis_condition_era():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "condition_era",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "condition_era_id": [1200, 1201],
                "condition_concept_id": [12121, 99999],
                "condition_era_start_date": ["2020-01-01", "2020-01-01"],
                "condition_era_end_date": ["2020-02-01", "2020-02-01"],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(11, 12121)],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionEra(codeset_id=11)]),
    )

    table = build_cohort_ibis(expression, backend=conn, cdm_schema="main")
    result = table.execute()

    assert set(result.person_id) == {1}
    assert all(result.domain == "condition_era")


def test_build_cohort_ibis_drug_era():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "drug_era",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "drug_era_id": [1300, 1301],
                "drug_concept_id": [13131, 99999],
                "drug_era_start_date": ["2020-03-01", "2020-03-01"],
                "drug_era_end_date": ["2020-04-01", "2020-04-01"],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(12, 13131)],
        primary_criteria=PrimaryCriteria(criteria_list=[DrugEra(codeset_id=12)]),
    )

    table = build_cohort_ibis(expression, backend=conn, cdm_schema="main")
    result = table.execute()

    assert set(result.person_id) == {1}
    assert all(result.domain == "drug_era")


def test_build_cohort_ibis_dose_era():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "dose_era",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "dose_era_id": [1400, 1401],
                "drug_concept_id": [14141, 99999],
                "dose_era_start_date": ["2020-05-01", "2020-05-01"],
                "dose_era_end_date": ["2020-06-01", "2020-06-01"],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(13, 14141)],
        primary_criteria=PrimaryCriteria(criteria_list=[DoseEra(codeset_id=13)]),
    )

    table = build_cohort_ibis(expression, backend=conn, cdm_schema="main")
    result = table.execute()

    assert set(result.person_id) == {1}
    assert all(result.domain == "dose_era")


def test_build_cohort_ibis_location_region():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "location",
        obj=ibis.memtable(
            {
                "location_id": [10, 20],
                "region_concept_id": [15151, 99999],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "location_history",
        obj=ibis.memtable(
            {
                "entity_id": [1, 2],
                "location_id": [10, 20],
                "start_date": ["2020-01-01", "2020-01-01"],
                "end_date": ["2020-12-31", "2020-12-31"],
                "domain_id": ["PERSON", "PERSON"],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(14, 15151)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[LocationRegion(codeset_id=14)]
        ),
    )

    table = build_cohort_ibis(expression, backend=conn, cdm_schema="main")
    result = table.execute()

    assert set(result.person_id) == {1}
    assert all(result.domain == "location_region")


def test_build_cohort_ibis_location_region_keeps_repeated_location_history_rows():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "location",
        obj=ibis.memtable(
            {
                "location_id": [10],
                "region_concept_id": [15151],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "location_history",
        obj=ibis.memtable(
            {
                "entity_id": [1, 1],
                "location_id": [10, 10],
                "start_date": ["2020-01-01", "2020-02-01"],
                "end_date": ["2020-01-31", "2020-02-28"],
                "domain_id": ["PERSON", "PERSON"],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(14, 15151)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[LocationRegion(codeset_id=14)]
        ),
    )

    result = build_cohort_ibis(expression, backend=conn, cdm_schema="main").execute()

    assert len(result) == 2
    assert set(result.person_id) == {1}
    assert sorted(result.start_date.astype(str).tolist()) == ["2020-01-01", "2020-02-01"]


def test_build_cohort_ibis_rejects_non_mvp_features():
    expression = CohortExpression(
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence()]),
        end_strategy=CustomEraStrategy(drug_codeset_id=1, gap_days=30, offset=0),
    )
    with pytest.raises(UnsupportedFeatureError, match="custom_era"):
        _ = build_cohort_ibis(expression, backend=object(), cdm_schema="main")
