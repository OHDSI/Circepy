"""Tests for execution group builders (CriteriaGroup, Demographics, CorrelatedCriteria)."""

from __future__ import annotations

import ibis
import pytest

from circe import CohortExpression
from circe.cohortdefinition import (
    ConditionOccurrence,
    CriteriaGroup,
    DateRange,
    DemographicCriteria,
    NumericRange,
    Occurrence,
    PrimaryCriteria,
    Window,
    WindowBound,
)
from circe.cohortdefinition import (
    CorelatedCriteria as CorrelatedCriteria,
)
from circe.execution.api import build_cohort
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


@pytest.fixture
def mem_db(target_schema="main"):
    pytest.importorskip("duckdb")
    conn = ibis.duckdb.connect()

    # Create required domain tables
    conn.create_table(
        "concept",
        obj=ibis.memtable(
            {
                "concept_id": [111, 222, 8507, 8532],
                "invalid_reason": ["", "", "", ""],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "concept_ancestor",
        obj=ibis.memtable(
            {
                "ancestor_concept_id": [111, 222],
                "descendant_concept_id": [111, 222],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "concept_relationship",
        obj=ibis.memtable(
            {
                "concept_id_1": [111, 222],
                "concept_id_2": [111, 222],
                "relationship_id": ["Maps to", "Maps to"],
                "invalid_reason": ["", ""],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "person",
        obj=ibis.memtable(
            {
                "person_id": [1, 2, 3],
                "gender_concept_id": [8507, 8532, 8507],  # 8507 Male, 8532 Female
                "year_of_birth": [1980, 1990, 2000],
                "month_of_birth": [1, 1, 1],
                "day_of_birth": [1, 1, 1],
                "race_concept_id": [0, 0, 0],
                "ethnicity_concept_id": [0, 0, 0],
            }
        ),
        overwrite=True,
    )
    import datetime

    conn.create_table(
        "observation_period",
        obj=ibis.memtable(
            {
                "person_id": [1, 2, 3],
                "observation_period_start_date": [
                    datetime.datetime(2010, 1, 1),
                    datetime.datetime(2010, 1, 1),
                    datetime.datetime(2010, 1, 1),
                ],
                "observation_period_end_date": [
                    datetime.datetime(2030, 1, 1),
                    datetime.datetime(2030, 1, 1),
                    datetime.datetime(2030, 1, 1),
                ],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 2, 3, 1, 2],
                "condition_occurrence_id": [101, 102, 103, 104, 105],
                "condition_concept_id": [111, 111, 111, 222, 222],
                "condition_start_date": [
                    datetime.datetime(2020, 1, 1),
                    datetime.datetime(2020, 1, 1),
                    datetime.datetime(2022, 1, 1),
                    datetime.datetime(2020, 1, 5),
                    datetime.datetime(2020, 10, 1),
                ],
                "condition_end_date": [
                    datetime.datetime(2020, 1, 2),
                    datetime.datetime(2020, 1, 2),
                    datetime.datetime(2022, 1, 2),
                    datetime.datetime(2020, 1, 6),
                    datetime.datetime(2020, 10, 2),
                ],
            }
        ),
        overwrite=True,
    )
    return conn


def test_demographic_criteria(mem_db):
    """Test DemographicCriteria age and gender filtering in CriteriaGroup."""
    cohort = CohortExpression(
        concept_sets=[
            ConceptSet(
                id=1, expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(conceptId=111))])
            )
        ],
        primary_criteria=PrimaryCriteria(
            criteria_list=[ConditionOccurrence(codeset_id=1)],
        ),
        additional_criteria=CriteriaGroup(
            type="ALL",
            demographic_criteria_list=[
                DemographicCriteria(
                    age=NumericRange(
                        op="gt", value=35
                    ),  # Person 1 (born 1980 is 40 at 2020), Person 2 (1990) is 30, Person 3 (2000) is 20
                )
            ],
        ),
    )

    events = build_cohort(cohort, backend=mem_db, cdm_schema="main")
    events = events.execute()
    assert len(events) == 1
    assert events.iloc[0]["person_id"] == 1


def test_demographic_criteria_gender_and_date(mem_db):
    cohort = CohortExpression(
        concept_sets=[
            ConceptSet(
                id=1, expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(conceptId=111))])
            )
        ],
        primary_criteria=PrimaryCriteria(
            criteria_list=[ConditionOccurrence(codeset_id=1)],
        ),
        additional_criteria=CriteriaGroup(
            type="ALL",
            demographic_criteria_list=[
                DemographicCriteria(
                    gender=[Concept(concept_id=8532)],  # Person 2
                    occurrence_start_date=DateRange(op="lt", value="2021-01-01"),
                )
            ],
        ),
    )

    events = build_cohort(cohort, backend=mem_db, cdm_schema="main")
    events = events.execute()
    assert len(events) == 1
    assert list(events["person_id"]) == [2]


def test_correlated_criteria(mem_db):
    """Test CorrelatedCriteria with window."""
    cohort = CohortExpression(
        concept_sets=[
            ConceptSet(
                id=1, expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(conceptId=111))])
            ),
            ConceptSet(
                id=2, expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(conceptId=222))])
            ),
        ],
        primary_criteria=PrimaryCriteria(
            criteria_list=[ConditionOccurrence(codeset_id=1)],
        ),
        additional_criteria=CriteriaGroup(
            type="ALL",
            criteria_list=[
                # Look for concept 222 (events at 2020-01-05 for P1, 2020-10-01 for P2)
                # within [0, 100] days after index start
                CorrelatedCriteria(
                    criteria=ConditionOccurrence(codeset_id=2),
                    start_window=Window(
                        start=WindowBound(days=0, coeff=1),
                        end=WindowBound(days=100, coeff=1),
                        use_index_end=False,
                        use_event_end=False,
                    ),
                    occurrence=Occurrence(type=2, count=1, is_distinct=False),  # AT_LEAST 1
                )
            ],
        ),
    )

    events = build_cohort(cohort, backend=mem_db, cdm_schema="main")
    events = events.execute()
    # Person 1 has 222 at 2020-01-05, within 0-100 days of 2020-01-01
    # Person 2 has 222 at 2020-10-01, > 100 days after 2020-01-01
    # Person 3 has no 222
    assert len(events) == 1
    assert events.iloc[0]["person_id"] == 1


def test_combine_any_and_threshold(mem_db):
    """Test groups with ANY and AT_LEAST types."""
    cohort = CohortExpression(
        concept_sets=[
            ConceptSet(
                id=1, expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(conceptId=111))])
            )
        ],
        primary_criteria=PrimaryCriteria(
            criteria_list=[ConditionOccurrence(codeset_id=1)],
        ),
        additional_criteria=CriteriaGroup(
            type="AT_LEAST",
            count=1,
            groups=[
                CriteriaGroup(
                    type="ALL",
                    demographic_criteria_list=[
                        DemographicCriteria(age=NumericRange(op="lt", value=25))
                    ],  # P3
                ),
                CriteriaGroup(
                    type="ANY",
                    demographic_criteria_list=[DemographicCriteria(gender=[Concept(concept_id=8532)])],  # P2
                ),
            ],
        ),
    )

    events = build_cohort(cohort, backend=mem_db, cdm_schema="main")
    events = events.execute()
    # Should match Person 2 (from ANY group gender filter) and Person 3 (from ALL group age filter)
    assert set(events["person_id"]) == {2, 3}
