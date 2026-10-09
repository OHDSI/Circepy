from __future__ import annotations

import pytest

from circe.api import build_cohort
from circe.cohortdefinition import (
    CohortExpression,
    ConditionOccurrence,
    Death,
    DeviceExposure,
    DrugExposure,
    Measurement,
    PrimaryCriteria,
    Specimen,
    VisitDetail,
    VisitOccurrence,
)
from circe.cohortdefinition.core import ConceptSetSelection, DateAdjustment, NumericRange
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem
from tests.execution.test_api_ibis import _seed_common_tables


def _make_concept_set(set_id: int, concept_id: int) -> ConceptSet:
    return ConceptSet(
        id=set_id,
        expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(conceptId=concept_id))]),
    )


def test_condition_occurrence_applies_related_filters_and_date_adjustment():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "provider",
        obj=ibis.memtable(
            {
                "provider_id": [1, 2],
                "specialty_concept_id": [8001, 8002],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "visit_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "visit_occurrence_id": [10, 11],
                "visit_concept_id": [7001, 7002],
                "visit_start_date": ["2020-01-01", "2020-01-01"],
                "visit_end_date": ["2020-01-03", "2020-01-03"],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "condition_occurrence_id": [100, 101],
                "condition_concept_id": [111, 111],
                "condition_start_date": ["2020-01-01", "2020-01-01"],
                "condition_end_date": [None, "2020-01-03"],
                "visit_occurrence_id": [10, 11],
                "provider_id": [1, 2],
                "condition_type_concept_id": [9001, 9002],
                "condition_status_concept_id": [9101, 9102],
                "stop_reason": ["keep me", "drop me"],
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
                    condition_type=[Concept(conceptId=9001)],
                    condition_status=[Concept(conceptId=9101)],
                    stop_reason={"op": "contains", "text": "keep"},
                    provider_specialty=[Concept(conceptId=8001)],
                    visit_type=[Concept(conceptId=7001)],
                    occurrence_start_date={"op": "gte", "value": "2020-01-02"},
                    occurrence_end_date={"op": "gte", "value": "2020-01-04"},
                    date_adjustment=DateAdjustment(start_offset=1, end_offset=2),
                )
            ]
        ),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    assert list(result.person_id) == [1]
    assert result.iloc[0].start_date.date().isoformat() == "2020-01-02"


def test_drug_exposure_applies_domain_filters_and_end_date_fallback():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "provider",
        obj=ibis.memtable({"provider_id": [1, 2], "specialty_concept_id": [8001, 8002]}),
        overwrite=True,
    )
    conn.create_table(
        "visit_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "visit_occurrence_id": [10, 11],
                "visit_concept_id": [7001, 7002],
                "visit_start_date": ["2020-03-01", "2020-03-01"],
                "visit_end_date": ["2020-03-02", "2020-03-02"],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "drug_exposure",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "drug_exposure_id": [200, 201],
                "drug_concept_id": [222, 222],
                "drug_exposure_start_date": ["2020-03-01", "2020-03-01"],
                "drug_exposure_end_date": [None, "2020-03-02"],
                "visit_occurrence_id": [10, 11],
                "provider_id": [1, 2],
                "drug_type_concept_id": [3001, 3002],
                "route_concept_id": [4001, 4002],
                "dose_unit_concept_id": [5001, 5002],
                "lot_number": ["A-LOT", "B-LOT"],
                "quantity": [10.0, 1.0],
                "days_supply": [5, 1],
                "refills": [2, 0],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(2, 222)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[
                DrugExposure(
                    codeset_id=2,
                    drug_type=[Concept(conceptId=3001)],
                    route_concept=[Concept(conceptId=4001)],
                    dose_unit=[Concept(conceptId=5001)],
                    lot_number={"op": "contains", "text": "A-"},
                    quantity=NumericRange(op="gte", value=10),
                    days_supply=NumericRange(op="gte", value=5),
                    refills=NumericRange(op="gte", value=2),
                    provider_specialty=[Concept(conceptId=8001)],
                    visit_type=[Concept(conceptId=7001)],
                    occurrence_end_date={"op": "gte", "value": "2020-03-06"},
                )
            ]
        ),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    assert list(result.person_id) == [1]


def test_visit_occurrence_applies_care_site_provider_location_and_duration_filters():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "provider",
        obj=ibis.memtable({"provider_id": [1, 2], "specialty_concept_id": [8001, 8002]}),
        overwrite=True,
    )
    conn.create_table(
        "care_site",
        obj=ibis.memtable(
            {
                "care_site_id": [100, 101],
                "place_of_service_concept_id": [9001, 9002],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "location_history",
        obj=ibis.memtable(
            {
                "entity_id": [100, 101],
                "domain_id": ["CARE_SITE", "CARE_SITE"],
                "location_id": [500, 501],
                "start_date": ["2020-01-01", "2020-01-01"],
                "end_date": [None, "2020-12-31"],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "location",
        obj=ibis.memtable({"location_id": [500, 501], "region_concept_id": [6001, 6002]}),
        overwrite=True,
    )
    conn.create_table(
        "visit_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "visit_occurrence_id": [300, 301],
                "visit_concept_id": [333, 333],
                "visit_start_date": ["2020-05-01", "2020-05-01"],
                "visit_end_date": ["2020-05-03", "2020-05-02"],
                "visit_type_concept_id": [7001, 7002],
                "provider_id": [1, 2],
                "care_site_id": [100, 101],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(3, 333), _make_concept_set(31, 6001)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[
                VisitOccurrence(
                    codeset_id=3,
                    visit_type=[Concept(conceptId=7001)],
                    visit_length=NumericRange(op="gte", value=2),
                    provider_specialty=[Concept(conceptId=8001)],
                    place_of_service=[Concept(conceptId=9001)],
                    place_of_service_location=31,
                )
            ]
        ),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    assert list(result.person_id) == [1]


def test_device_exposure_applies_domain_filters_and_end_date_fallback():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "provider",
        obj=ibis.memtable({"provider_id": [1, 2], "specialty_concept_id": [8001, 8002]}),
        overwrite=True,
    )
    conn.create_table(
        "visit_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "visit_occurrence_id": [10, 11],
                "visit_concept_id": [7001, 7002],
                "visit_start_date": ["2020-10-01", "2020-10-01"],
                "visit_end_date": ["2020-10-02", "2020-10-02"],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "device_exposure",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "device_exposure_id": [800, 801],
                "device_concept_id": [888, 888],
                "device_exposure_start_date": ["2020-10-01", "2020-10-01"],
                "device_exposure_end_date": [None, "2020-10-02"],
                "visit_occurrence_id": [10, 11],
                "provider_id": [1, 2],
                "device_type_concept_id": [3001, 3002],
                "unique_device_id": ["abc-123", "xyz-999"],
                "quantity": [5, 1],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(8, 888)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[
                DeviceExposure(
                    codeset_id=8,
                    device_type=[Concept(conceptId=3001)],
                    unique_device_id={"op": "contains", "text": "abc"},
                    quantity=NumericRange(op="gte", value=5),
                    provider_specialty=[Concept(conceptId=8001)],
                    visit_type=[Concept(conceptId=7001)],
                    occurrence_end_date={"op": "gte", "value": "2020-10-02"},
                )
            ]
        ),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    assert list(result.person_id) == [1]


def test_specimen_applies_domain_filters():
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
                "specimen_concept_id": [9990, 9990],
                "specimen_date": ["2020-11-01", "2020-11-01"],
                "visit_occurrence_id": [10, 11],
                "specimen_type_concept_id": [1001, 1002],
                "quantity": [5.0, 1.0],
                "unit_concept_id": [2001, 2002],
                "anatomic_site_concept_id": [3001, 3002],
                "disease_status_concept_id": [4001, 4002],
                "specimen_source_id": ["keep-source", "drop-source"],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(9, 9990)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[
                Specimen(
                    codeset_id=9,
                    specimen_type=[Concept(conceptId=1001)],
                    quantity=NumericRange(op="gte", value=5),
                    unit=[Concept(conceptId=2001)],
                    anatomic_site=[Concept(conceptId=3001)],
                    disease_status=[Concept(conceptId=4001)],
                    source_id={"op": "contains", "text": "keep"},
                )
            ]
        ),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    assert list(result.person_id) == [1]


def test_death_applies_death_type_and_derived_end_date():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "death",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "cause_concept_id": [10001, 10001],
                "cause_source_concept_id": [20001, 20002],
                "death_type_concept_id": [3001, 3002],
                "death_date": ["2020-12-01", "2020-12-01"],
            }
        ),
        overwrite=True,
    )

    expression = CohortExpression(
        concept_sets=[_make_concept_set(10, 10001)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[
                Death(
                    codeset_id=10,
                    death_type=[Concept(conceptId=3001)],
                    occurrence_end_date={"op": "gte", "value": "2020-12-02"},
                )
            ]
        ),
    )

    result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
    assert list(result.person_id) == [1]


def test_measurement_and_visit_detail_apply_shared_related_filters():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    _seed_common_tables(conn, ibis)
    conn.create_table(
        "provider",
        obj=ibis.memtable({"provider_id": [1, 2], "specialty_concept_id": [8001, 8002]}),
        overwrite=True,
    )
    conn.create_table(
        "visit_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "visit_occurrence_id": [10, 11],
                "visit_concept_id": [7001, 7002],
                "visit_start_date": ["2020-06-01", "2020-06-01"],
                "visit_end_date": ["2020-06-02", "2020-06-02"],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "care_site",
        obj=ibis.memtable(
            {
                "care_site_id": [100, 101],
                "place_of_service_concept_id": [9001, 9002],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "location_history",
        obj=ibis.memtable(
            {
                "entity_id": [100, 101],
                "domain_id": ["CARE_SITE", "CARE_SITE"],
                "location_id": [500, 501],
                "start_date": ["2020-01-01", "2020-01-01"],
                "end_date": [None, "2020-12-31"],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "location",
        obj=ibis.memtable({"location_id": [500, 501], "region_concept_id": [6001, 6002]}),
        overwrite=True,
    )
    conn.create_table(
        "measurement",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "measurement_id": [400, 401],
                "measurement_concept_id": [444, 444],
                "measurement_date": ["2020-06-01", "2020-06-01"],
                "visit_occurrence_id": [10, 11],
                "provider_id": [1, 2],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "visit_detail",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "visit_detail_id": [710, 711],
                "visit_detail_concept_id": [777, 777],
                "visit_detail_start_date": ["2020-09-01", "2020-09-01"],
                "visit_detail_end_date": ["2020-09-03", "2020-09-02"],
                "visit_occurrence_id": [10, 11],
                "provider_id": [1, 2],
                "care_site_id": [100, 101],
            }
        ),
        overwrite=True,
    )

    measurement_expression = CohortExpression(
        concept_sets=[_make_concept_set(4, 444)],
        primary_criteria=PrimaryCriteria(
            criteria_list=[
                Measurement(
                    codeset_id=4,
                    provider_specialty=[Concept(conceptId=8001)],
                    visit_type=[Concept(conceptId=7001)],
                )
            ]
        ),
    )
    measurement_result = build_cohort(
        measurement_expression,
        backend=conn,
        cdm_schema="main",
    ).execute()
    assert list(measurement_result.person_id) == [1]

    visit_detail_expression = CohortExpression(
        concept_sets=[
            _make_concept_set(7, 777),
            _make_concept_set(21, 8001),
            _make_concept_set(22, 9001),
            _make_concept_set(23, 6001),
        ],
        primary_criteria=PrimaryCriteria(
            criteria_list=[
                VisitDetail(
                    codeset_id=7,
                    provider_specialty_cs=ConceptSetSelection(codeset_id=21, is_exclusion=False),
                    place_of_service_cs=ConceptSetSelection(codeset_id=22, is_exclusion=False),
                    place_of_service_location=23,
                    visit_detail_length=NumericRange(op="gte", value=2),
                )
            ]
        ),
    )
    visit_detail_result = build_cohort(
        visit_detail_expression,
        backend=conn,
        cdm_schema="main",
    ).execute()
    assert list(visit_detail_result.person_id) == [1]
