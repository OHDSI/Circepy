from __future__ import annotations

import pytest

from circe.execution.ibis.codesets import build_single_codeset_table
from circe.execution.normalize.cohort import NormalizedConceptSet, NormalizedConceptSetItem


def _make_item(cid: int, *, excluded: bool = False) -> NormalizedConceptSetItem:
    return NormalizedConceptSetItem(
        concept_id=cid,
        is_excluded=excluded,
        include_descendants=False,
        include_mapped=False,
    )


def test_multiple_excludes_no_collision():
    """Multiple excluded items trigger sequential anti-joins in
    _build_codeset_expression.  Without the per-iteration reselect, the
    second anti-join would hit a concept_id_right collision.
    """
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()

    concept_sets = {
        1: NormalizedConceptSet(
            set_id=1,
            items=(
                _make_item(111),          # include
                _make_item(222),          # include
                _make_item(333, excluded=True),  # exclude 1
                _make_item(444, excluded=True),  # exclude 2
                _make_item(555, excluded=True),  # exclude 3 → triggers collision without fix
            ),
        ),
    }

    tbl = build_single_codeset_table(
        backend=conn,
        concept_sets=concept_sets,
        batch_table_name="__test_exclude_codesets",
    )
    rows = tbl.execute()

    included_ids = set(rows["concept_id"].tolist())
    assert included_ids == {111, 222}, f"Expected {{111, 222}} got {included_ids}"

    conn.drop_table("__test_exclude_codesets", force=True)


def test_single_exclude_works():
    """Single exclude should also work correctly."""
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()

    concept_sets = {
        1: NormalizedConceptSet(
            set_id=1,
            items=(
                _make_item(111),
                _make_item(222),
                _make_item(333, excluded=True),
            ),
        ),
    }

    tbl = build_single_codeset_table(
        backend=conn,
        concept_sets=concept_sets,
        batch_table_name="__test_exclude_codesets2",
    )
    rows = tbl.execute()

    included_ids = set(rows["concept_id"].tolist())
    assert included_ids == {111, 222}, f"Expected {{111, 222}} got {included_ids}"

    conn.drop_table("__test_exclude_codesets2", force=True)


def test_all_excluded_returns_empty():
    """All items excluded should return empty codeset table."""
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()

    concept_sets = {
        1: NormalizedConceptSet(
            set_id=1,
            items=(
                _make_item(111, excluded=True),
                _make_item(222, excluded=True),
                _make_item(333, excluded=True),
            ),
        ),
    }

    tbl = build_single_codeset_table(
        backend=conn,
        concept_sets=concept_sets,
        batch_table_name="__test_exclude_codesets3",
    )
    rows = tbl.execute()

    assert len(rows) == 0, f"Expected empty, got {rows}"

    conn.drop_table("__test_exclude_codesets3", force=True)
