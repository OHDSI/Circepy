from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import ibis
import pytest

from circe.execution.engine.group_windows import apply_window_constraints, window_bound_expression
from circe.execution.errors import CompilationError, UnsupportedFeatureError
from circe.execution.ibis.compile_steps import (
    _apply_date_predicate,
    _apply_numeric_predicate,
    _resolve_concept_ids,
    apply_step,
)
from circe.execution.normalize.windows import NormalizedWindow, NormalizedWindowBound
from circe.execution.plan.events import (
    ApplyDateAdjustment,
    FilterByCareSiteLocationRegion,
    FilterByCodeset,
    FilterByConceptSet,
    FilterByPersonGender,
    FilterByText,
    KeepFirstPerPerson,
    RestrictToCorrelatedWindow,
)
from circe.execution.plan.predicates import DateRangePredicate, NumericRangePredicate
from circe.execution.plan.schema import END_DATE, EVENT_ID, PERSON_ID, START_DATE, VISIT_OCCURRENCE_ID


class _Context:
    def __init__(self, conn=None, *, codesets: dict[int, tuple[int, ...]] | None = None):
        self.conn = conn
        self.codesets = codesets or {}

    def concept_ids_for_codeset(self, codeset_id: int) -> tuple[int, ...]:
        return self.codesets.get(codeset_id, ())

    def table(self, name: str):
        if self.conn is None:
            raise KeyError(name)
        return self.conn.table(name)


def _events_table(conn):
    conn.create_table(
        "events",
        obj=ibis.memtable(
            {
                PERSON_ID: [1, 1, 2],
                EVENT_ID: [10, 11, 20],
                START_DATE: [
                    date(2020, 1, 1),
                    date(2020, 1, 2),
                    date(2020, 1, 3),
                ],
                END_DATE: [
                    date(2020, 1, 5),
                    date(2020, 1, 4),
                    date(2020, 1, 6),
                ],
                VISIT_OCCURRENCE_ID: [100, 101, 200],
                "concept_id": [1, 2, 3],
                "text_value": ["alpha", "beta", "gamma"],
            }
        ),
        overwrite=True,
    )
    return conn.table("events")


@pytest.mark.parametrize(
    ("predicate", "expected"),
    [
        (NumericRangePredicate(op=None, value=None, extent=None), [True, True, True]),
        (NumericRangePredicate(op="eq", value=2, extent=None), [False, True, False]),
        (NumericRangePredicate(op="neq", value=2, extent=None), [True, False, True]),
        (NumericRangePredicate(op="gt", value=1, extent=None), [False, True, True]),
        (NumericRangePredicate(op="gte", value=2, extent=None), [False, True, True]),
        (NumericRangePredicate(op="lt", value=3, extent=None), [True, True, False]),
        (NumericRangePredicate(op="lte", value=2, extent=None), [True, True, False]),
        (NumericRangePredicate(op="between", value=2, extent=3), [False, True, True]),
    ],
)
def test_apply_numeric_predicate_covers_supported_ops(predicate, expected):
    table = ibis.memtable({"value": [1, 2, 3]})
    result = table.select(_apply_numeric_predicate(table.value, predicate).name("matched")).execute()
    assert list(result.matched) == expected


def test_apply_numeric_predicate_rejects_invalid_ranges():
    expr = ibis.memtable({"value": [1]}).value

    with pytest.raises(CompilationError, match="numeric range 'between' requires an extent value"):
        _apply_numeric_predicate(expr, NumericRangePredicate(op="between", value=1, extent=None))

    with pytest.raises(CompilationError, match="unsupported numeric range op"):
        _apply_numeric_predicate(expr, NumericRangePredicate(op="weird", value=1, extent=None))


@pytest.mark.parametrize(
    ("predicate", "expected"),
    [
        (DateRangePredicate(op=None, value=None, extent=None), [True, True, True]),
        (DateRangePredicate(op="eq", value="2020-01-02", extent=None), [False, True, False]),
        (DateRangePredicate(op="neq", value="2020-01-02", extent=None), [True, False, True]),
        (DateRangePredicate(op="gt", value="2020-01-01", extent=None), [False, True, True]),
        (DateRangePredicate(op="gte", value="2020-01-02", extent=None), [False, True, True]),
        (DateRangePredicate(op="lt", value="2020-01-03", extent=None), [True, True, False]),
        (DateRangePredicate(op="lte", value="2020-01-02", extent=None), [True, True, False]),
        (
            DateRangePredicate(op="between", value="2020-01-02", extent="2020-01-03"),
            [False, True, True],
        ),
    ],
)
def test_apply_date_predicate_covers_supported_ops(predicate, expected):
    table = ibis.memtable({"value": ["2020-01-01", "2020-01-02", "2020-01-03"]})
    result = table.select(_apply_date_predicate(table.value, predicate).name("matched")).execute()
    assert list(result.matched) == expected


def test_apply_date_predicate_rejects_invalid_ranges():
    expr = ibis.memtable({"value": ["2020-01-01"]}).value

    with pytest.raises(CompilationError, match="date range 'between' requires an extent value"):
        _apply_date_predicate(expr, DateRangePredicate(op="between", value="2020-01-01", extent=None))

    with pytest.raises(CompilationError, match="unsupported date range op"):
        _apply_date_predicate(expr, DateRangePredicate(op="weird", value="2020-01-01", extent=None))


def test_resolve_concept_ids_deduplicates_codeset_ids():
    ctx = _Context(codesets={1: (2, 3, 4)})
    assert _resolve_concept_ids(direct_ids=(1, 2), codeset_id=1, ctx=ctx) == (1, 2, 3, 4)


def test_apply_step_covers_text_codeset_concept_and_adjustment_paths():
    ibis_mod = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis_mod.duckdb.connect()
    table = _events_table(conn)
    ctx = _Context(conn, codesets={1: (1, 3), 2: ()})

    codeset_hit = apply_step(
        FilterByCodeset(column="concept_id", codeset_id=1),
        table=table,
        source=None,
        ctx=ctx,
    ).execute()
    assert set(codeset_hit.concept_id) == {1, 3}

    codeset_exclude = apply_step(
        FilterByCodeset(column="concept_id", codeset_id=2, exclude=True),
        table=table,
        source=None,
        ctx=ctx,
    ).execute()
    assert len(codeset_exclude) == 3

    empty_concepts = apply_step(
        FilterByConceptSet(column="concept_id", concept_ids=(), exclude=False),
        table=table,
        source=None,
        ctx=ctx,
    ).execute()
    assert empty_concepts.empty

    text_eq = apply_step(
        FilterByText(column="text_value", op="eq", text="alpha"),
        table=table,
        source=None,
        ctx=ctx,
    ).execute()
    assert list(text_eq.text_value) == ["alpha"]

    text_neq = apply_step(
        FilterByText(column="text_value", op="neq", text="alpha"),
        table=table,
        source=None,
        ctx=ctx,
    ).execute()
    assert set(text_neq.text_value) == {"beta", "gamma"}

    text_none = apply_step(
        FilterByText(column="text_value", op="contains", text=None),
        table=table,
        source=None,
        ctx=ctx,
    )
    assert text_none is table

    text_like = apply_step(
        FilterByText(column="text_value", op="contains", text="a"),
        table=table,
        source=None,
        ctx=ctx,
    ).execute()
    assert set(text_like.text_value) == {"alpha", "beta", "gamma"}

    adjusted = apply_step(
        ApplyDateAdjustment(start_offset_days=2, end_offset_days=1, start_with=END_DATE, end_with=START_DATE),
        table=table,
        source=None,
        ctx=ctx,
    ).execute()
    assert str(adjusted.iloc[0][START_DATE])[:10] == "2020-01-07"
    assert str(adjusted.iloc[0][END_DATE])[:10] == "2020-01-02"


def test_apply_step_covers_keep_first_person_filter_and_error_paths():
    ibis_mod = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis_mod.duckdb.connect()
    table = _events_table(conn)
    conn.create_table(
        "person",
        obj=ibis_mod.memtable(
            {
                PERSON_ID: [1, 2],
                "gender_concept_id": [8507, 8532],
            }
        ),
        overwrite=True,
    )
    ctx = _Context(conn, codesets={9: ()})

    first = apply_step(
        KeepFirstPerPerson(order_by=(START_DATE,)),
        table=table,
        source=None,
        ctx=ctx,
    ).execute()
    assert set(first[EVENT_ID]) == {10, 20}

    filtered = apply_step(
        FilterByPersonGender(concept_ids=(8507,), codeset_id=None),
        table=table,
        source=None,
        ctx=ctx,
    ).execute()
    assert set(filtered[PERSON_ID]) == {1}

    care_site_empty = apply_step(
        FilterByCareSiteLocationRegion(codeset_id=9),
        table=table,
        source=None,
        ctx=ctx,
    ).execute()
    assert care_site_empty.empty

    with pytest.raises(CompilationError, match="unsupported text filter op"):
        apply_step(FilterByText(column="text_value", op="weird", text="x"), table=table, source=None, ctx=ctx)

    with pytest.raises(UnsupportedFeatureError, match="RestrictToCorrelatedWindow step is not implemented"):
        apply_step(RestrictToCorrelatedWindow(payload={}), table=table, source=None, ctx=ctx)

    with pytest.raises(CompilationError, match="unsupported plan step"):
        apply_step(SimpleNamespace(), table=table, source=None, ctx=ctx)


def test_window_bound_expression_and_end_window_constraints():
    ibis_mod = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    assert (
        window_bound_expression(
            None,
            index_anchor_expr=ibis_mod.literal("2020-01-01").cast("date"),
            use_observation_period=True,
            op_start_expr=ibis_mod.literal("2019-01-01").cast("date"),
            op_end_expr=ibis_mod.literal("2020-12-31").cast("date"),
        )
        is None
    )
    assert (
        window_bound_expression(
            NormalizedWindowBound(coeff=1, days=None),
            index_anchor_expr=ibis_mod.literal("2020-01-01").cast("date"),
            use_observation_period=False,
            op_start_expr=ibis_mod.literal("2019-01-01").cast("date"),
            op_end_expr=ibis_mod.literal("2020-12-31").cast("date"),
        )
        is None
    )

    joined = ibis_mod.memtable(
        {
            "a_person_id": [1, 1],
            "p_person_id": [1, 1],
            "a_start_date": [date(2020, 1, 3), date(2020, 1, 20)],
            "a_end_date": [date(2020, 1, 5), date(2020, 1, 25)],
            "p_start_date": [date(2020, 1, 1), date(2020, 1, 1)],
            "p_end_date": [date(2020, 1, 10), date(2020, 1, 10)],
            "p_op_start_date": [date(2019, 1, 1), date(2019, 1, 1)],
            "p_op_end_date": [date(2020, 12, 31), date(2020, 12, 31)],
            "a_visit_occurrence_id": [100, 101],
            "p_visit_occurrence_id": [100, 100],
        }
    )
    correlated = SimpleNamespace(
        ignore_observation_period=False,
        restrict_visit=True,
        start_window=None,
        end_window=NormalizedWindow(
            start=NormalizedWindowBound(coeff=1, days=0),
            end=NormalizedWindowBound(coeff=1, days=10),
            use_event_end=False,
            use_index_end=False,
        ),
    )

    result = apply_window_constraints(joined, correlated).execute()
    assert len(result) == 1
    assert int(result.iloc[0]["a_visit_occurrence_id"]) == 100
