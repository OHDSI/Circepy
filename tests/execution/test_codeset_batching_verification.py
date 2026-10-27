"""Verify that the batched codeset optimization produces identical results.

This test exercises multiple items with include_descendants=True within a single
concept set -- the exact pattern that OPT-1 batches into a single
concept_ancestor JOIN instead of N separate JOINs.
"""

from __future__ import annotations

import pytest

from circe.execution.ibis.codesets import _build_codeset_expression, build_single_codeset_table
from circe.execution.normalize.cohort import NormalizedConceptSet, NormalizedConceptSetItem


@pytest.fixture
def vocab_conn():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    conn.create_table(
        "concept",
        obj=ibis.memtable(
            {
                "concept_id": [10, 11, 12, 20, 21, 22, 30, 31, 32, 40, 41, 50],
                "invalid_reason": [None, None, None, None, None, None, None, None, None, None, None, "D"],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "concept_ancestor",
        obj=ibis.memtable(
            {
                "ancestor_concept_id": [10, 10, 20, 20, 30, 30, 40],
                "descendant_concept_id": [11, 12, 21, 22, 31, 32, 50],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "concept_relationship",
        obj=ibis.memtable(
            {
                "concept_id_1": [40, 41, 99],
                "concept_id_2": [10, 20, 99],
                "relationship_id": ["Maps to", "Maps to", "Maps to"],
                "invalid_reason": [None, None, "D"],
            }
        ),
        overwrite=True,
    )
    return conn


def _table_getter(conn):
    def getter(name, schema):
        return conn.table(name)

    return getter


class TestBatchedDescendantExpansion:
    """Test that batching multiple include_descendants items gives correct results."""

    def test_multiple_descendants_batched(self, vocab_conn):
        """Three items with include_descendants=True should resolve to all their descendants."""
        concept_set = NormalizedConceptSet(
            set_id=1,
            items=(
                NormalizedConceptSetItem(
                    concept_id=10, is_excluded=False, include_descendants=True, include_mapped=False
                ),
                NormalizedConceptSetItem(
                    concept_id=20, is_excluded=False, include_descendants=True, include_mapped=False
                ),
                NormalizedConceptSetItem(
                    concept_id=30, is_excluded=False, include_descendants=True, include_mapped=False
                ),
            ),
        )
        result = _build_codeset_expression(
            concept_set, table_getter=_table_getter(vocab_conn), vocabulary_schema=None
        )
        rows = set(result.execute()["concept_id"].tolist())
        # Direct {10,20,30} + descendants: 10->{11,12}, 20->{21,22}, 30->{31,32}
        # Note: 40->50 but 50 is invalid so not included
        assert rows == {10, 11, 12, 20, 21, 22, 30, 31, 32}

    def test_descendants_with_direct_exclusion(self, vocab_conn):
        """Excluded item (direct, no descendants) removes it from the final set."""
        concept_set = NormalizedConceptSet(
            set_id=2,
            items=(
                NormalizedConceptSetItem(
                    concept_id=10, is_excluded=False, include_descendants=True, include_mapped=False
                ),
                NormalizedConceptSetItem(
                    concept_id=20, is_excluded=False, include_descendants=True, include_mapped=False
                ),
                NormalizedConceptSetItem(
                    concept_id=11, is_excluded=True, include_descendants=False, include_mapped=False
                ),
            ),
        )
        result = _build_codeset_expression(
            concept_set, table_getter=_table_getter(vocab_conn), vocabulary_schema=None
        )
        rows = set(result.execute()["concept_id"].tolist())
        # Include: {10, 11, 12, 20, 21, 22}, Exclude: {11} -> {10, 12, 20, 21, 22}
        assert rows == {10, 12, 20, 21, 22}

    def test_excluded_with_descendants_batched(self, vocab_conn):
        """Excluded items with include_descendants should batch their ancestor lookup too."""
        concept_set = NormalizedConceptSet(
            set_id=3,
            items=(
                NormalizedConceptSetItem(
                    concept_id=10, is_excluded=False, include_descendants=True, include_mapped=False
                ),
                NormalizedConceptSetItem(
                    concept_id=20, is_excluded=False, include_descendants=True, include_mapped=False
                ),
                NormalizedConceptSetItem(
                    concept_id=30, is_excluded=True, include_descendants=True, include_mapped=False
                ),
            ),
        )
        result = _build_codeset_expression(
            concept_set, table_getter=_table_getter(vocab_conn), vocabulary_schema=None
        )
        rows = set(result.execute()["concept_id"].tolist())
        # Include: {10, 11, 12, 20, 21, 22}. Exclude: {30, 31, 32}. No overlap.
        assert rows == {10, 11, 12, 20, 21, 22}

    def test_mapped_batched(self, vocab_conn):
        """Multiple items with include_mapped should batch the relationship lookup."""
        concept_set = NormalizedConceptSet(
            set_id=4,
            items=(
                NormalizedConceptSetItem(
                    concept_id=10, is_excluded=False, include_descendants=False, include_mapped=True
                ),
                NormalizedConceptSetItem(
                    concept_id=20, is_excluded=False, include_descendants=False, include_mapped=True
                ),
            ),
        )
        result = _build_codeset_expression(
            concept_set, table_getter=_table_getter(vocab_conn), vocabulary_schema=None
        )
        rows = set(result.execute()["concept_id"].tolist())
        # Direct: {10, 20}. Mapped: concept_relationship where concept_id_2 IN (10,20)
        # -> concept_id_1=40 (maps to 10), concept_id_1=41 (maps to 20)
        assert rows == {10, 20, 40, 41}

    def test_descendants_and_mapped_combined(self, vocab_conn):
        """Items with both include_descendants and include_mapped batch both lookups."""
        concept_set = NormalizedConceptSet(
            set_id=5,
            items=(
                NormalizedConceptSetItem(
                    concept_id=10, is_excluded=False, include_descendants=True, include_mapped=True
                ),
                NormalizedConceptSetItem(
                    concept_id=20, is_excluded=False, include_descendants=True, include_mapped=True
                ),
            ),
        )
        result = _build_codeset_expression(
            concept_set, table_getter=_table_getter(vocab_conn), vocabulary_schema=None
        )
        rows = set(result.execute()["concept_id"].tolist())
        # Direct: {10, 20}. Desc: {11, 12, 21, 22}. Mapped: {40, 41}
        assert rows == {10, 11, 12, 20, 21, 22, 40, 41}

    def test_build_single_codeset_table_multiple_sets(self, vocab_conn):
        """build_single_codeset_table correctly separates concept sets with batched expansion."""
        concept_sets = {
            1: NormalizedConceptSet(
                set_id=1,
                items=(
                    NormalizedConceptSetItem(
                        concept_id=10, is_excluded=False, include_descendants=True, include_mapped=False
                    ),
                    NormalizedConceptSetItem(
                        concept_id=20, is_excluded=False, include_descendants=True, include_mapped=False
                    ),
                ),
            ),
            2: NormalizedConceptSet(
                set_id=2,
                items=(
                    NormalizedConceptSetItem(
                        concept_id=30, is_excluded=False, include_descendants=True, include_mapped=False
                    ),
                ),
            ),
        }
        tbl = build_single_codeset_table(
            backend=vocab_conn,
            concept_sets=concept_sets,
            batch_table_name="__test_batch_verify",
        )
        df = tbl.execute()
        cs1_ids = set(df[df["codeset_id"] == 1]["concept_id"].tolist())
        cs2_ids = set(df[df["codeset_id"] == 2]["concept_id"].tolist())
        assert cs1_ids == {10, 11, 12, 20, 21, 22}
        assert cs2_ids == {30, 31, 32}
        vocab_conn.drop_table("__test_batch_verify", force=True)


class TestBatchedEndToEnd:
    """End-to-end cohort build with batched codeset resolution."""

    def test_cohort_with_descendants_and_exclusion(self):
        """Reproduce the existing test_build_cohort_concept_set_resolves_descendants_and_mapped."""
        import datetime

        ibis = pytest.importorskip("ibis")
        _ = pytest.importorskip("duckdb")

        from circe.cohortdefinition import (
            CohortExpression,
            ConditionOccurrence,
            PrimaryCriteria,
        )
        from circe.execution.api import build_cohort
        from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem

        conn = ibis.duckdb.connect()
        S = datetime.date(2020, 1, 1)
        E = datetime.date(2020, 12, 31)
        conn.create_table(
            "person",
            obj=ibis.memtable(
                {"person_id": [1, 2], "year_of_birth": [1980, 1980], "gender_concept_id": [0, 0]}
            ),
            overwrite=True,
        )
        conn.create_table(
            "observation_period",
            obj=ibis.memtable(
                {
                    "person_id": [1, 2],
                    "observation_period_id": [1, 2],
                    "observation_period_start_date": [S, S],
                    "observation_period_end_date": [E, E],
                }
            ),
            overwrite=True,
        )
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
            obj=ibis.memtable({"ancestor_concept_id": [100, 100], "descendant_concept_id": [101, 102]}),
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
        conn.create_table(
            "condition_occurrence",
            obj=ibis.memtable(
                {
                    "person_id": [1, 1, 1, 1, 1, 2],
                    "condition_occurrence_id": [1000, 1001, 1002, 1003, 1004, 1005],
                    "condition_concept_id": [100, 101, 102, 200, 201, 999],
                    "condition_start_date": [S, S, S, S, S, S],
                    "condition_end_date": [S, S, S, S, S, S],
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

        cohort_result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
        assert set(cohort_result.person_id) == {1}
        # codeset 1: include 100 (desc=True, mapped=True), exclude 101 (mapped=True)
        # Include side: direct 100 + desc of 100: {101, 102(invalid)} + mapped of 100: {200}
        #   -> valid include = {100, 101, 200}
        # Exclude side: direct 101 + mapped of 101: {201(invalid_reason='D')}
        #   -> valid exclude = {101}
        # Final: {100, 101, 200} - {101} = {100, 200}
        assert set(cohort_result.concept_id) == {100, 200}
