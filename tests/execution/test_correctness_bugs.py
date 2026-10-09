"""Tests for known correctness bugs identified in benchmark comparison.

Bug 2: End strategy re-joins observation_period, creating duplicates when a person
       has overlapping observation periods → overcounting after ERA collapse.

Bug 3: AdditionalCriteria with VisitOccurrence using EndWindow + UseEventEnd causes
       undercounting when visit_end_date is NULL (comparison evaluates to NULL → row dropped).

Bug 5: Severe undercounting in cohorts with nested CorrelatedCriteria inside
       PrimaryCriteria or complex multi-rule inclusion logic.
"""

from __future__ import annotations

import pytest

from circe.api import build_cohort
from circe.cohortdefinition import (
    CohortExpression,
    ConditionOccurrence,
    CorelatedCriteria,
    CriteriaGroup,
    Occurrence,
    PrimaryCriteria,
    ProcedureOccurrence,
    VisitOccurrence,
    Window,
    WindowBound,
)
from circe.cohortdefinition.core import CollapseSettings, DateOffsetStrategy, ResultLimit
from circe.cohortdefinition.criteria import InclusionRule
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


def _make_concept_set(set_id: int, concept_id: int) -> ConceptSet:
    return ConceptSet(
        id=set_id,
        expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(conceptId=concept_id))]),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Bug 2: Overlapping observation periods cause duplicate rows in end strategy
# ──────────────────────────────────────────────────────────────────────────────


class TestBug2OverlappingObservationPeriods:
    """When a person has overlapping observation periods and end strategy uses
    DateOffset with EndDate, the re-join to observation_period creates duplicate
    rows (one per matching OP) with different op_end_date values, resulting in
    different capped end dates. After ERA collapse, this produces more eras than
    expected.

    In simple cases, ERA collapse merges the duplicates back (same start_date →
    always overlap). However, `attach_observation_bounds` still creates structural
    duplication that can cause overcounting in complex pipelines or on backends
    with different NULL/tie-breaking semantics.

    Expected behavior: Each event should produce exactly one cohort era regardless
    of how many observation periods overlap the event's start_date.
    """

    @pytest.fixture
    def conn(self):
        ibis = pytest.importorskip("ibis")
        _ = pytest.importorskip("duckdb")
        conn = ibis.duckdb.connect()

        # Person 1 has TWO overlapping observation periods with DIFFERENT end dates.
        # The shorter OP ends BEFORE the event's end_date + offset, so it caps the
        # end date to a different value than the longer OP.
        conn.create_table(
            "person",
            obj=ibis.memtable({"person_id": [1], "year_of_birth": [1980], "gender_concept_id": [8507]}),
            overwrite=True,
        )
        conn.create_table(
            "observation_period",
            obj=ibis.memtable(
                {
                    "person_id": [1, 1],
                    "observation_period_id": [10, 11],
                    # OP 10: 2019-01-01 to 2020-04-15 (shorter — will cap the end date)
                    # OP 11: 2020-01-01 to 2021-12-31 (longer — won't cap)
                    "observation_period_start_date": ["2019-01-01", "2020-01-01"],
                    "observation_period_end_date": ["2020-04-15", "2021-12-31"],
                }
            ),
            overwrite=True,
        )
        # Condition event: start=2020-03-01, end=2020-03-25
        # DateOffset(EndDate, 30): target end_date = 2020-03-25 + 30 = 2020-04-24
        # Via OP 10 (end=2020-04-15): LEAST(2020-04-24, 2020-04-15) = 2020-04-15
        # Via OP 11 (end=2021-12-31): LEAST(2020-04-24, 2021-12-31) = 2020-04-24
        # → Two different end dates for the SAME event → duplicate row
        conn.create_table(
            "condition_occurrence",
            obj=ibis.memtable(
                {
                    "person_id": [1],
                    "condition_occurrence_id": [100],
                    "condition_concept_id": [111],
                    "condition_start_date": ["2020-03-01"],
                    "condition_end_date": ["2020-03-25"],
                    "visit_occurrence_id": [10],
                }
            ),
            overwrite=True,
        )
        return conn

    def test_attach_observation_bounds_skips_rejoin_when_op_columns_present(self, conn):
        """When events already carry op_start_date/op_end_date from primary events,
        attach_observation_bounds returns them directly without re-joining.

        This is the fix for Bug 2: the primary events stage now always attaches
        OP bounds, so end_strategy and correlated criteria use those instead of
        re-joining (which would create duplicates for overlapping OPs).
        """
        ibis = pytest.importorskip("ibis")
        from circe.execution.engine.end_strategy import attach_observation_bounds
        from circe.execution.ibis.context import make_execution_context

        ctx = make_execution_context(backend=conn, cdm_schema="main")

        # Build events WITH op_start_date/op_end_date (as they come from build_primary_events)
        events = conn.create_table(
            "__test_events_with_op",
            obj=ibis.memtable(
                {
                    "person_id": [1],
                    "event_id": [1],
                    "start_date": ["2020-03-01"],
                    "end_date": ["2020-03-25"],
                    "op_start_date": ["2020-01-01"],
                    "op_end_date": ["2021-12-31"],
                }
            ),
            overwrite=True,
        )
        events = events.mutate(
            person_id=events.person_id.cast("int64"),
            event_id=events.event_id.cast("int64"),
            start_date=events.start_date.cast("date"),
            end_date=events.end_date.cast("date"),
            op_start_date=events.op_start_date.cast("date"),
            op_end_date=events.op_end_date.cast("date"),
        )

        with_bounds = attach_observation_bounds(events, ctx)
        result = with_bounds.execute()

        # With OP columns already present, no re-join happens → exactly 1 row
        assert len(result) == 1, (
            f"attach_observation_bounds produced {len(result)} rows when OP columns "
            "were already present. Should return events directly without re-joining."
        )

    def test_fallback_rejoin_produces_duplicates_for_overlapping_ops(self, conn):
        """The fallback re-join path (for events WITHOUT OP columns) still creates
        duplicates when overlapping OPs exist. This documents the limitation of the
        fallback path, which is NOT used in the normal pipeline (build_primary_events
        always attaches OP columns).
        """
        ibis = pytest.importorskip("ibis")
        from circe.execution.engine.end_strategy import attach_observation_bounds
        from circe.execution.ibis.context import make_execution_context

        ctx = make_execution_context(backend=conn, cdm_schema="main")

        # Build events WITHOUT op columns (triggering the fallback re-join)
        events = conn.create_table(
            "__test_events_no_op",
            obj=ibis.memtable(
                {
                    "person_id": [1],
                    "event_id": [1],
                    "start_date": ["2020-03-01"],
                    "end_date": ["2020-03-25"],
                }
            ),
            overwrite=True,
        )
        events = events.mutate(
            person_id=events.person_id.cast("int64"),
            event_id=events.event_id.cast("int64"),
            start_date=events.start_date.cast("date"),
            end_date=events.end_date.cast("date"),
        )

        with_bounds = attach_observation_bounds(events, ctx)
        result = with_bounds.execute()

        # Fallback path: re-join produces 2 rows (one per matching OP)
        # This is the known limitation that Bug 2 fix avoids by carrying OP from primary events
        assert len(result) == 2, (
            f"Expected fallback re-join to produce 2 rows for overlapping OPs, got {len(result)}."
        )

    def test_single_event_produces_single_era(self, conn):
        """One event in overlapping OPs should still produce exactly one cohort era.

        This test passes because ERA collapse merges the duplicate rows back
        together (they share the same start_date). But the duplication is still
        wasteful and can cause issues on backends with different tie-breaking.
        """
        expression = CohortExpression(
            concept_sets=[_make_concept_set(1, 111)],
            primary_criteria=PrimaryCriteria(
                criteria_list=[ConditionOccurrence(codeset_id=1)],
                primary_limit=ResultLimit(type="All"),
            ),
            end_strategy=DateOffsetStrategy(offset=30, date_field="EndDate"),
            collapse_settings=CollapseSettings(collapse_type="ERA", era_pad=0),
            expression_limit=ResultLimit(type="All"),
        )

        result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
        assert len(result) == 1
        # End date should use the LONGEST OP (not capped by shorter OP)
        assert str(result.iloc[0]["end_date"])[:10] == "2020-04-24"

    def test_two_events_in_overlapping_ops_collapse_correctly(self, conn):
        """Two close events that should merge into one era must not be split by OP duplication."""
        ibis = pytest.importorskip("ibis")
        # Two events: both fall in both OPs, both get duplicated end dates
        # Event 1: start=2020-03-01, end=2020-03-25 → target 2020-04-24 (capped to 2020-04-15 via OP10)
        # Event 2: start=2020-03-10, end=2020-03-28 → target 2020-04-27 (capped to 2020-04-15 via OP10)
        # These events overlap — should collapse to a single era
        conn.create_table(
            "condition_occurrence",
            obj=ibis.memtable(
                {
                    "person_id": [1, 1],
                    "condition_occurrence_id": [100, 101],
                    "condition_concept_id": [111, 111],
                    "condition_start_date": ["2020-03-01", "2020-03-10"],
                    "condition_end_date": ["2020-03-25", "2020-03-28"],
                    "visit_occurrence_id": [10, 10],
                }
            ),
            overwrite=True,
        )

        expression = CohortExpression(
            concept_sets=[_make_concept_set(1, 111)],
            primary_criteria=PrimaryCriteria(
                criteria_list=[ConditionOccurrence(codeset_id=1)],
                primary_limit=ResultLimit(type="All"),
            ),
            end_strategy=DateOffsetStrategy(offset=30, date_field="EndDate"),
            collapse_settings=CollapseSettings(collapse_type="ERA", era_pad=0),
            expression_limit=ResultLimit(type="All"),
        )

        result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
        # Both events overlap (event 2 starts before event 1's end+30) → single merged era
        # Correct: 1 era from 2020-03-01 to 2020-04-27
        # Bug: OP duplication creates extra rows with different end dates, potentially
        # splitting what should be a single era into multiple fragments
        assert len(result) == 1, (
            f"Expected 1 merged era but got {len(result)}. "
            "Overlapping OPs may have created duplicate rows preventing proper ERA merge."
        )


# ──────────────────────────────────────────────────────────────────────────────
# Bug 3: AdditionalCriteria with VisitOccurrence + EndWindow + UseEventEnd
#         undercounts when visit_end_date is NULL
# ──────────────────────────────────────────────────────────────────────────────


class TestBug3VisitEndWindowUndercounting:
    """When AdditionalCriteria requires a VisitOccurrence with EndWindow using
    UseEventEnd=true, visits with NULL visit_end_date fail the comparison
    (NULL >= date evaluates to NULL/false) and the event is excluded.

    The Java/R reference implementation handles this case (likely via COALESCE
    or different NULL semantics), keeping these events in the cohort.

    Pattern from affected cohorts (71, 74, 260-263, 881, 898, 965, 967):
    - StartWindow: visit starts on or before the index event
    - EndWindow with UseEventEnd=true: visit ends on or after the index event
    - This checks "the event occurred during a visit"
    """

    @pytest.fixture
    def conn(self):
        ibis = pytest.importorskip("ibis")
        _ = pytest.importorskip("duckdb")
        conn = ibis.duckdb.connect()

        conn.create_table(
            "person",
            obj=ibis.memtable(
                {"person_id": [1, 2], "year_of_birth": [1980, 1975], "gender_concept_id": [8507, 8532]}
            ),
            overwrite=True,
        )
        conn.create_table(
            "observation_period",
            obj=ibis.memtable(
                {
                    "person_id": [1, 2],
                    "observation_period_id": [10, 20],
                    "observation_period_start_date": ["2019-01-01", "2019-01-01"],
                    "observation_period_end_date": ["2022-12-31", "2022-12-31"],
                }
            ),
            overwrite=True,
        )
        # Two condition events — one for each person
        conn.create_table(
            "condition_occurrence",
            obj=ibis.memtable(
                {
                    "person_id": [1, 2],
                    "condition_occurrence_id": [100, 200],
                    "condition_concept_id": [111, 111],
                    "condition_start_date": ["2020-06-15", "2020-06-15"],
                    "condition_end_date": ["2020-06-20", "2020-06-20"],
                    "visit_occurrence_id": [1000, 2000],
                }
            ),
            overwrite=True,
        )
        # Two visits:
        #   Person 1: visit with a proper end_date (2020-06-20) — should match
        #   Person 2: visit with NULL end_date (ongoing visit) — should ALSO match
        conn.create_table(
            "visit_occurrence",
            obj=ibis.memtable(
                {
                    "person_id": [1, 2],
                    "visit_occurrence_id": [1000, 2000],
                    "visit_concept_id": [9201, 9201],  # Inpatient
                    "visit_start_date": ["2020-06-10", "2020-06-10"],
                    "visit_end_date": ["2020-06-20", None],  # Person 2 has NULL end
                    "visit_source_concept_id": [0, 0],
                }
            ),
            overwrite=True,
        )
        return conn

    def test_null_visit_end_date_excludes_from_end_window(self, conn):
        """A visit with NULL end_date is correctly excluded by EndWindow with UseEventEnd=true.

        This matches Java/R behavior: CohortExpressionQueryBuilder.java line 586 uses
        A.END_DATE directly without COALESCE. When visit_end_date is NULL, the comparison
        `A.END_DATE >= ...` evaluates to NULL → row excluded. This is correct behavior
        per OMOP CDM (visit_end_date is a required NOT NULL field).
        """
        expression = CohortExpression(
            concept_sets=[_make_concept_set(1, 111), _make_concept_set(2, 9201)],
            primary_criteria=PrimaryCriteria(
                criteria_list=[ConditionOccurrence(codeset_id=1)],
                primary_limit=ResultLimit(type="All"),
            ),
            additional_criteria=CriteriaGroup(
                type="ANY",
                criteria_list=[
                    CorelatedCriteria(
                        criteria=VisitOccurrence(codeset_id=2),
                        start_window=Window(
                            start=WindowBound(coeff=-1),  # unbounded before
                            end=WindowBound(days=0, coeff=1),  # up to index start
                            use_index_end=False,
                            use_event_end=False,
                        ),
                        end_window=Window(
                            start=WindowBound(days=0, coeff=-1),  # from index start
                            end=WindowBound(coeff=1),  # unbounded after
                            use_index_end=False,
                            use_event_end=True,  # compare visit END date
                        ),
                        occurrence=Occurrence(type=2, count=1),  # at least 1
                    )
                ],
            ),
            end_strategy=DateOffsetStrategy(offset=30, date_field="EndDate"),
            collapse_settings=CollapseSettings(collapse_type="ERA", era_pad=0),
            expression_limit=ResultLimit(type="All"),
        )

        result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
        # Only Person 1 should be in the cohort:
        # Person 1: visit (Jun 10 - Jun 20) encompasses condition (Jun 15) ✓
        # Person 2: visit (Jun 10 - NULL) → EndWindow check: NULL >= Jun 15 → NULL → excluded
        # This matches Java behavior (no COALESCE on A.END_DATE)
        assert len(result) == 1, (
            f"Expected 1 cohort entry (only person with valid visit_end_date) but got {len(result)}."
        )

    def test_visit_not_encompassing_event_excluded(self, conn):
        """Visits that genuinely don't encompass the event should still be excluded."""
        ibis = pytest.importorskip("ibis")
        # Override: Person 2's visit ENDS BEFORE the condition starts
        conn.create_table(
            "visit_occurrence",
            obj=ibis.memtable(
                {
                    "person_id": [1, 2],
                    "visit_occurrence_id": [1000, 2000],
                    "visit_concept_id": [9201, 9201],
                    "visit_start_date": ["2020-06-10", "2020-06-01"],
                    "visit_end_date": ["2020-06-20", "2020-06-10"],  # Person 2 visit ends before condition
                    "visit_source_concept_id": [0, 0],
                }
            ),
            overwrite=True,
        )

        expression = CohortExpression(
            concept_sets=[_make_concept_set(1, 111), _make_concept_set(2, 9201)],
            primary_criteria=PrimaryCriteria(
                criteria_list=[ConditionOccurrence(codeset_id=1)],
                primary_limit=ResultLimit(type="All"),
            ),
            additional_criteria=CriteriaGroup(
                type="ANY",
                criteria_list=[
                    CorelatedCriteria(
                        criteria=VisitOccurrence(codeset_id=2),
                        start_window=Window(
                            start=WindowBound(coeff=-1),
                            end=WindowBound(days=0, coeff=1),
                            use_index_end=False,
                            use_event_end=False,
                        ),
                        end_window=Window(
                            start=WindowBound(days=0, coeff=-1),
                            end=WindowBound(coeff=1),
                            use_index_end=False,
                            use_event_end=True,
                        ),
                        occurrence=Occurrence(type=2, count=1),
                    )
                ],
            ),
            end_strategy=DateOffsetStrategy(offset=30, date_field="EndDate"),
            collapse_settings=CollapseSettings(collapse_type="ERA", era_pad=0),
            expression_limit=ResultLimit(type="All"),
        )

        result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
        # Only person 1 should match — person 2's visit ended before the condition
        assert len(result) == 1, (
            f"Expected 1 cohort entry (person 1 only) but got {len(result)}. "
            "Person 2's visit ends before condition start and should be excluded."
        )
        assert int(result.iloc[0]["person_id"]) == 1


# ──────────────────────────────────────────────────────────────────────────────
# Bug 5a: Nested CorrelatedCriteria inside PrimaryCriteria severe undercount
# ──────────────────────────────────────────────────────────────────────────────


class TestBug5NestedCorrelatedCriteria:
    """Cohorts with CorrelatedCriteria nested inside PrimaryCriteria (e.g.,
    "ConditionOccurrence where a ProcedureOccurrence exists within X days")
    produce severe undercounting (1-2% of expected results).

    Pattern from cohort 402: PrimaryCriteria has a ConditionOccurrence with
    an inline CorrelatedCriteria requiring a ProcedureOccurrence nearby.
    """

    @pytest.fixture
    def conn(self):
        ibis = pytest.importorskip("ibis")
        _ = pytest.importorskip("duckdb")
        conn = ibis.duckdb.connect()

        conn.create_table(
            "person",
            obj=ibis.memtable(
                {
                    "person_id": [1, 2, 3],
                    "year_of_birth": [1980, 1975, 1990],
                    "gender_concept_id": [8507, 8532, 8507],
                }
            ),
            overwrite=True,
        )
        conn.create_table(
            "observation_period",
            obj=ibis.memtable(
                {
                    "person_id": [1, 2, 3],
                    "observation_period_id": [10, 20, 30],
                    "observation_period_start_date": ["2018-01-01", "2018-01-01", "2018-01-01"],
                    "observation_period_end_date": ["2022-12-31", "2022-12-31", "2022-12-31"],
                }
            ),
            overwrite=True,
        )
        # Three persons with conditions
        conn.create_table(
            "condition_occurrence",
            obj=ibis.memtable(
                {
                    "person_id": [1, 2, 3],
                    "condition_occurrence_id": [100, 200, 300],
                    "condition_concept_id": [111, 111, 111],
                    "condition_start_date": ["2020-06-01", "2020-07-01", "2020-08-01"],
                    "condition_end_date": ["2020-06-05", "2020-07-05", "2020-08-05"],
                    "visit_occurrence_id": [1000, 2000, 3000],
                }
            ),
            overwrite=True,
        )
        # Only persons 1 and 2 have a procedure within 7 days of their condition
        conn.create_table(
            "procedure_occurrence",
            obj=ibis.memtable(
                {
                    "person_id": [1, 2],
                    "procedure_occurrence_id": [500, 600],
                    "procedure_concept_id": [222, 222],
                    "procedure_date": ["2020-06-03", "2020-07-02"],
                    "procedure_source_concept_id": [0, 0],
                    "visit_occurrence_id": [1000, 2000],
                }
            ),
            overwrite=True,
        )
        # Need visit_occurrence table for schema completeness
        conn.create_table(
            "visit_occurrence",
            obj=ibis.memtable(
                {
                    "person_id": [1, 2, 3],
                    "visit_occurrence_id": [1000, 2000, 3000],
                    "visit_concept_id": [9201, 9201, 9201],
                    "visit_start_date": ["2020-06-01", "2020-07-01", "2020-08-01"],
                    "visit_end_date": ["2020-06-10", "2020-07-10", "2020-08-10"],
                    "visit_source_concept_id": [0, 0, 0],
                }
            ),
            overwrite=True,
        )
        return conn

    def test_primary_criteria_with_nested_correlated_criteria(self, conn):
        """PrimaryCriteria with inline CorrelatedCriteria should correctly filter
        primary events to those having a matching correlated event.

        Pattern: "Condition X where Procedure Y occurs within ±7 days"
        Only persons 1 and 2 have procedures within 7 days of their condition.
        """
        expression = CohortExpression(
            concept_sets=[_make_concept_set(1, 111), _make_concept_set(2, 222)],
            primary_criteria=PrimaryCriteria(
                criteria_list=[
                    ConditionOccurrence(
                        codeset_id=1,
                        correlated_criteria=CriteriaGroup(
                            type="ALL",
                            criteria_list=[
                                CorelatedCriteria(
                                    criteria=ProcedureOccurrence(codeset_id=2),
                                    start_window=Window(
                                        start=WindowBound(days=7, coeff=-1),  # 7 days before
                                        end=WindowBound(days=7, coeff=1),  # 7 days after
                                        use_index_end=False,
                                        use_event_end=False,
                                    ),
                                    occurrence=Occurrence(type=2, count=1),  # at least 1
                                )
                            ],
                        ),
                    )
                ],
                primary_limit=ResultLimit(type="First"),
            ),
            qualified_limit=ResultLimit(type="First"),
            expression_limit=ResultLimit(type="All"),
        )

        result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
        # Persons 1 and 2 have procedures within 7 days of condition → match
        # Person 3 has no procedure at all → excluded by correlated criteria
        assert len(result) == 2, (
            f"Expected 2 cohort entries (persons 1 & 2) but got {len(result)}. "
            "Nested CorrelatedCriteria in PrimaryCriteria may not be filtering correctly."
        )
        result_persons = sorted(result["person_id"].tolist())
        assert result_persons == [1, 2]

    def test_nested_correlated_excludes_non_matching(self, conn):
        """Person 3 has no procedure near the condition and should be excluded."""
        pytest.importorskip("ibis")
        # Make the window very tight so only person 1 matches (procedure on same day)
        expression = CohortExpression(
            concept_sets=[_make_concept_set(1, 111), _make_concept_set(2, 222)],
            primary_criteria=PrimaryCriteria(
                criteria_list=[
                    ConditionOccurrence(
                        codeset_id=1,
                        correlated_criteria=CriteriaGroup(
                            type="ALL",
                            criteria_list=[
                                CorelatedCriteria(
                                    criteria=ProcedureOccurrence(codeset_id=2),
                                    start_window=Window(
                                        start=WindowBound(days=0, coeff=-1),  # same day only
                                        end=WindowBound(days=0, coeff=1),
                                        use_index_end=False,
                                        use_event_end=False,
                                    ),
                                    occurrence=Occurrence(type=2, count=1),
                                )
                            ],
                        ),
                    )
                ],
                primary_limit=ResultLimit(type="First"),
            ),
            qualified_limit=ResultLimit(type="First"),
            expression_limit=ResultLimit(type="All"),
        )

        result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
        # Only person 1's procedure (Jun 3) is within 0 days of condition (Jun 1)? No!
        # Person 1: condition=Jun 1, procedure=Jun 3 → 2 days apart → outside ±0 window
        # Person 2: condition=Jul 1, procedure=Jul 2 → 1 day apart → outside ±0 window
        # Neither should match with a 0-day window
        assert len(result) == 0, (
            f"Expected 0 entries with 0-day window but got {len(result)}. "
            "No procedures occur on the exact same day as the conditions."
        )


# ──────────────────────────────────────────────────────────────────────────────
# Bug 5b: Complex multi-rule inclusion logic causes excessive filtering
# ──────────────────────────────────────────────────────────────────────────────


class TestBug5ComplexInclusionRules:
    """Cohorts with many inclusion rules (7+) where each rule has complex
    correlated criteria may over-filter due to incorrect rule intersection logic.

    Pattern from cohort 726: Multiple inclusion rules, each requiring different
    correlated criteria. The ALL logic requires ALL rules to pass for an event
    to be included. If any rule's join logic is overly restrictive (e.g., inner
    join instead of semi-join), events get dropped.
    """

    @pytest.fixture
    def conn(self):
        ibis = pytest.importorskip("ibis")
        _ = pytest.importorskip("duckdb")
        conn = ibis.duckdb.connect()

        conn.create_table(
            "person",
            obj=ibis.memtable(
                {"person_id": [1, 2], "year_of_birth": [1980, 1975], "gender_concept_id": [8507, 8532]}
            ),
            overwrite=True,
        )
        conn.create_table(
            "observation_period",
            obj=ibis.memtable(
                {
                    "person_id": [1, 2],
                    "observation_period_id": [10, 20],
                    "observation_period_start_date": ["2018-01-01", "2018-01-01"],
                    "observation_period_end_date": ["2023-12-31", "2023-12-31"],
                }
            ),
            overwrite=True,
        )
        # Both persons have the primary condition
        conn.create_table(
            "condition_occurrence",
            obj=ibis.memtable(
                {
                    "person_id": [1, 2],
                    "condition_occurrence_id": [100, 200],
                    "condition_concept_id": [111, 111],
                    "condition_start_date": ["2020-06-01", "2020-06-01"],
                    "condition_end_date": ["2020-06-05", "2020-06-05"],
                    "visit_occurrence_id": [1000, 2000],
                }
            ),
            overwrite=True,
        )
        # Both persons have visit occurrences matching each inclusion rule
        conn.create_table(
            "visit_occurrence",
            obj=ibis.memtable(
                {
                    "person_id": [1, 1, 2, 2],
                    "visit_occurrence_id": [1000, 1001, 2000, 2001],
                    "visit_concept_id": [9201, 9202, 9201, 9202],  # Inpatient, ER
                    "visit_start_date": ["2020-06-01", "2020-05-01", "2020-06-01", "2020-05-01"],
                    "visit_end_date": ["2020-06-10", "2020-05-02", "2020-06-10", "2020-05-02"],
                    "visit_source_concept_id": [0, 0, 0, 0],
                }
            ),
            overwrite=True,
        )
        # Both persons have procedures (for a second inclusion rule)
        conn.create_table(
            "procedure_occurrence",
            obj=ibis.memtable(
                {
                    "person_id": [1, 2],
                    "procedure_occurrence_id": [500, 600],
                    "procedure_concept_id": [333, 333],
                    "procedure_date": ["2020-06-02", "2020-06-02"],
                    "procedure_source_concept_id": [0, 0],
                    "visit_occurrence_id": [1000, 2000],
                }
            ),
            overwrite=True,
        )
        return conn

    def test_multiple_inclusion_rules_all_satisfied(self, conn):
        """When a person satisfies ALL inclusion rules, they should remain in the cohort.

        Two inclusion rules:
        1. Must have an inpatient visit (9201) within ±30 days
        2. Must have a procedure (333) within ±30 days
        Both persons satisfy both rules.
        """
        expression = CohortExpression(
            concept_sets=[
                _make_concept_set(1, 111),
                _make_concept_set(2, 9201),
                _make_concept_set(3, 333),
            ],
            primary_criteria=PrimaryCriteria(
                criteria_list=[ConditionOccurrence(codeset_id=1)],
                primary_limit=ResultLimit(type="First"),
            ),
            inclusion_rules=[
                InclusionRule(
                    name="Has inpatient visit",
                    expression=CriteriaGroup(
                        type="ALL",
                        criteria_list=[
                            CorelatedCriteria(
                                criteria=VisitOccurrence(codeset_id=2),
                                start_window=Window(
                                    start=WindowBound(days=30, coeff=-1),
                                    end=WindowBound(days=30, coeff=1),
                                    use_index_end=False,
                                    use_event_end=False,
                                ),
                                occurrence=Occurrence(type=2, count=1),
                            )
                        ],
                    ),
                ),
                InclusionRule(
                    name="Has procedure",
                    expression=CriteriaGroup(
                        type="ALL",
                        criteria_list=[
                            CorelatedCriteria(
                                criteria=ProcedureOccurrence(codeset_id=3),
                                start_window=Window(
                                    start=WindowBound(days=30, coeff=-1),
                                    end=WindowBound(days=30, coeff=1),
                                    use_index_end=False,
                                    use_event_end=False,
                                ),
                                occurrence=Occurrence(type=2, count=1),
                            )
                        ],
                    ),
                ),
            ],
            expression_limit=ResultLimit(type="All"),
        )

        result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
        # Both persons have inpatient visit AND procedure within 30 days
        assert len(result) == 2, (
            f"Expected 2 cohort entries but got {len(result)}. "
            "Multiple inclusion rules may be incorrectly intersecting and dropping valid events."
        )

    def test_one_rule_not_satisfied_excludes_person(self, conn):
        """Person failing one inclusion rule should be excluded."""
        ibis = pytest.importorskip("ibis")
        # Override procedures — only person 1 has one
        conn.create_table(
            "procedure_occurrence",
            obj=ibis.memtable(
                {
                    "person_id": [1],
                    "procedure_occurrence_id": [500],
                    "procedure_concept_id": [333],
                    "procedure_date": ["2020-06-02"],
                    "procedure_source_concept_id": [0],
                    "visit_occurrence_id": [1000],
                }
            ),
            overwrite=True,
        )

        expression = CohortExpression(
            concept_sets=[
                _make_concept_set(1, 111),
                _make_concept_set(2, 9201),
                _make_concept_set(3, 333),
            ],
            primary_criteria=PrimaryCriteria(
                criteria_list=[ConditionOccurrence(codeset_id=1)],
                primary_limit=ResultLimit(type="First"),
            ),
            inclusion_rules=[
                InclusionRule(
                    name="Has inpatient visit",
                    expression=CriteriaGroup(
                        type="ALL",
                        criteria_list=[
                            CorelatedCriteria(
                                criteria=VisitOccurrence(codeset_id=2),
                                start_window=Window(
                                    start=WindowBound(days=30, coeff=-1),
                                    end=WindowBound(days=30, coeff=1),
                                    use_index_end=False,
                                    use_event_end=False,
                                ),
                                occurrence=Occurrence(type=2, count=1),
                            )
                        ],
                    ),
                ),
                InclusionRule(
                    name="Has procedure",
                    expression=CriteriaGroup(
                        type="ALL",
                        criteria_list=[
                            CorelatedCriteria(
                                criteria=ProcedureOccurrence(codeset_id=3),
                                start_window=Window(
                                    start=WindowBound(days=30, coeff=-1),
                                    end=WindowBound(days=30, coeff=1),
                                    use_index_end=False,
                                    use_event_end=False,
                                ),
                                occurrence=Occurrence(type=2, count=1),
                            )
                        ],
                    ),
                ),
            ],
            expression_limit=ResultLimit(type="All"),
        )

        result = build_cohort(expression, backend=conn, cdm_schema="main").execute()
        # Person 1: has visit + procedure → passes both rules
        # Person 2: has visit but NO procedure → fails rule 2 → excluded
        assert len(result) == 1, f"Expected 1 cohort entry (person 1 only) but got {len(result)}."
        assert int(result.iloc[0]["person_id"]) == 1
