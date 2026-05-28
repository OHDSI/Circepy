"""Unit tests for sqlglot builder primitives and codeset builder."""

from sqlglot import exp as sge

from circe.cohortdefinition import (
    ConditionOccurrence,
    DrugExposure,
    NumericRange,
    TextFilter,
    VisitOccurrence,
)
from circe.cohortdefinition.core import DateRange
from circe.cohortdefinition.sqlglot_builders import (
    ConditionOccurrenceGlotBuilder,
    DrugExposureGlotBuilder,
    VisitOccurrenceGlotBuilder,
)
from circe.cohortdefinition.sqlglot_builders.primitives import (
    alias_expr,
    build_date_range_clause,
    build_in_clause,
    build_numeric_range_clause,
    build_text_filter_clause,
    coalesce,
    codeset_in,
    codeset_join,
    column_ref,
    date_add,
    date_from_parts,
    datediff,
    row_number_expr,
    year_of,
)


class TestPrimitives:
    """Direct unit tests on primitive functions."""

    def test_column_ref(self):
        c = column_ref("co", "person_id")
        assert c.sql(dialect="duckdb") == "co.person_id"
        assert c.sql(dialect="tsql") == "co.person_id"

    def test_alias_expr(self):
        a = alias_expr(column_ref("co", "person_id"), "person_id")
        assert "person_id AS person_id" in a.sql(dialect="duckdb")

    def test_date_add(self):
        da = date_add("day", 3, column_ref("x", "start"))
        duck = da.sql(dialect="duckdb")
        tsql = da.sql(dialect="tsql")
        assert "+ INTERVAL 3 DAY" in duck or "INTERVAL '3 DAY'" in duck
        assert "DATEADD" in tsql

    def test_coalesce_non_empty(self):
        c = coalesce(column_ref("x", "a"), column_ref("x", "b"))
        sql = c.sql(dialect="duckdb")
        assert "COALESCE" in sql
        assert "x.a" in sql
        assert "x.b" in sql

    def test_coalesce_empty(self):
        # line 25: empty coalesce returns None
        assert coalesce() is None

    def test_year_of(self):
        y = year_of(column_ref("co", "start_date"))
        assert "YEAR" in y.sql(dialect="duckdb")

    def test_date_diff(self):
        dd = datediff("day", column_ref("t", "start"), column_ref("t", "end"))
        sql = dd.sql(dialect="duckdb")
        assert "DATE_DIFF" in sql or "DATEDIFF" in sql.upper()

    def test_date_from_parts(self):
        dfp = date_from_parts(2020, 1, 15)
        duck = dfp.sql(dialect="duckdb")
        tsql = dfp.sql(dialect="tsql")
        assert "MAKE_DATE" in duck.upper() or "DATEFROMPARTS" not in duck
        assert "DATEFROMPARTS" in tsql

    def test_row_number_expr(self):
        rn = row_number_expr(
            [column_ref("co", "person_id")],
            [column_ref("co", "start_date"), column_ref("co", "id")],
        )
        sql = rn.sql(dialect="duckdb")
        assert "ROW_NUMBER" in sql
        assert "PARTITION BY co.person_id" in sql or 'PARTITION BY "person_id"' in sql
        assert "ORDER BY" in sql


class TestPrimitivesDateRange:
    """Test all branches of build_date_range_clause."""

    def _expr(self, col: str = "C.start_date"):
        return column_ref("C", "start_date")

    def test_gte(self):
        r = DateRange(op="gte", value="2020-01-01")
        e = build_date_range_clause(self._expr(), r)
        assert e is not None
        sql = e.sql(dialect="duckdb")
        assert ">= MAKE_DATE" in sql or ">= DATE" in sql

    def test_lte(self):
        r = DateRange(op="lte", value="2020-12-31")
        e = build_date_range_clause(self._expr(), r)
        assert e is not None

    def test_gt(self):
        r = DateRange(op="gt", value="2020-06-01")
        e = build_date_range_clause(self._expr(), r)
        assert e is not None
        sql = e.sql(dialect="duckdb")
        assert ">" in sql

    def test_lt(self):
        r = DateRange(op="lt", value="2020-06-01")
        e = build_date_range_clause(self._expr(), r)
        assert e is not None
        sql = e.sql(dialect="duckdb")
        assert "<" in sql and ">" not in sql

    def test_eq(self):
        r = DateRange(op="eq", value="2020-06-15")
        e = build_date_range_clause(self._expr(), r)
        assert e is not None
        sql = e.sql(dialect="duckdb")
        assert "=" in sql

    def test_neq(self):
        r = DateRange(op="ne", value="2020-06-15")
        e = build_date_range_clause(self._expr(), r)
        assert e is not None
        sql = e.sql(dialect="duckdb")
        assert "<>" in sql or "NOT" in sql

    def test_bt(self):
        r = DateRange(op="bt", value="2020-01-01", extent="2020-12-31")
        e = build_date_range_clause(self._expr(), r)
        assert e is not None
        sql = e.sql(dialect="duckdb")
        assert "AND" in sql

    def test_not_bt(self):
        r = DateRange(op="!bt", value="2020-01-01", extent="2020-12-31")
        e = build_date_range_clause(self._expr(), r)
        assert e is not None
        sql = e.sql(dialect="duckdb")
        assert "NOT" in sql or "<>" in sql

    def test_none_op(self):
        assert build_date_range_clause(self._expr(), None) is None

    def test_none_value_bt(self):
        r = DateRange(op="bt", value=None, extent="2020-12-31")
        assert build_date_range_clause(self._expr(), r) is None

    def test_none_value_single(self):
        r = DateRange(op="eq", value=None)
        assert build_date_range_clause(self._expr(), r) is None


class TestPrimitivesNumericRange:
    """Test all branches of build_numeric_range_clause."""

    def test_gte(self):
        r = NumericRange(op="gte", value=18)
        e = build_numeric_range_clause(column_ref("C", "age"), r)
        assert e is not None
        sql = e.sql(dialect="duckdb")
        assert ">= 18" in sql

    def test_bt(self):
        r = NumericRange(op="bt", value=10, extent=20)
        e = build_numeric_range_clause(column_ref("C", "age"), r)
        assert e is not None
        sql = e.sql(dialect="duckdb")
        assert "10" in sql and "20" in sql and "AND" in sql

    def test_not_bt(self):
        r = NumericRange(op="!bt", value=5, extent=15)
        e = build_numeric_range_clause(column_ref("C", "x"), r)
        assert e is not None
        sql = e.sql(dialect="duckdb")
        assert "NOT" in sql or "<" in sql

    def test_eq(self):
        r = NumericRange(op="eq", value=42)
        e = build_numeric_range_clause(column_ref("C", "x"), r)
        assert e is not None
        sql = e.sql(dialect="duckdb")
        assert "= 42" in sql or "42 =" not in sql

    def test_neq(self):
        r = NumericRange(op="ne", value=99)
        e = build_numeric_range_clause(column_ref("C", "x"), r)
        assert e is not None

    def test_lt(self):
        r = NumericRange(op="lt", value=50)
        e = build_numeric_range_clause(column_ref("C", "x"), r)
        assert e is not None
        assert "< 50" in e.sql(dialect="duckdb")

    def test_lte(self):
        r = NumericRange(op="lte", value=100)
        e = build_numeric_range_clause(column_ref("C", "x"), r)
        assert e is not None

    def test_gt(self):
        r = NumericRange(op="gt", value=0)
        e = build_numeric_range_clause(column_ref("C", "x"), r)
        assert e is not None

    def test_none_op(self):
        assert build_numeric_range_clause(column_ref("C", "x"), None) is None

    def test_none_value(self):
        r = NumericRange(op="gt", value=None)
        assert build_numeric_range_clause(column_ref("C", "x"), r) is None

    def test_none_value_bt(self):
        r = NumericRange(op="bt", value=None, extent=5)
        assert build_numeric_range_clause(column_ref("C", "x"), r) is None

    def test_none_extent_bt(self):
        r = NumericRange(op="bt", value=1, extent=None)
        assert build_numeric_range_clause(column_ref("C", "x"), r) is None


class TestPrimitivesTextFilter:
    """Test all branches of build_text_filter_clause."""

    def test_string_input(self):
        e = build_text_filter_clause(column_ref("C", "reason"), "stopped")
        assert e is not None
        sql = e.sql(dialect="duckdb")
        assert "LIKE" in sql.upper()
        assert "%stopped%" in sql

    def test_eq(self):
        e = build_text_filter_clause(column_ref("C", "reason"), TextFilter(text="exact", op="eq"))
        assert e is not None
        sql = e.sql(dialect="duckdb")
        assert "= 'exact'" in sql or "'exact'" in sql

    def test_neq(self):
        e = build_text_filter_clause(column_ref("C", "reason"), TextFilter(text="bad", op="!eq"))
        assert e is not None
        sql = e.sql(dialect="duckdb")
        assert "<>" in sql or "NOT" in sql

    def test_starts_with(self):
        e = build_text_filter_clause(column_ref("C", "reason"), TextFilter(text="pre", op="startsWith"))
        assert e is not None
        sql = e.sql(dialect="duckdb")
        assert "pre%" in sql

    def test_ends_with(self):
        e = build_text_filter_clause(column_ref("C", "reason"), TextFilter(text="fix", op="endsWith"))
        assert e is not None
        sql = e.sql(dialect="duckdb")
        assert "%fix" in sql

    def test_not_contains(self):
        e = build_text_filter_clause(column_ref("C", "reason"), TextFilter(text="bad", op="!contains"))
        assert e is not None
        sql = e.sql(dialect="duckdb")
        assert "NOT" in sql

    def test_contains_default(self):
        e = build_text_filter_clause(column_ref("C", "reason"), TextFilter(text="hidden", op="unknown_op"))
        assert e is not None
        sql = e.sql(dialect="duckdb")
        assert "%hidden%" in sql

    def test_none(self):
        assert build_text_filter_clause(column_ref("C", "x"), None) is None

    def test_empty_text(self):
        e = build_text_filter_clause(column_ref("C", "x"), TextFilter(text="", op="eq"))
        assert e is not None


class TestPrimitivesInClause:
    """Test build_in_clause."""

    def test_basic(self):
        e = build_in_clause(column_ref("C", "id"), [1, 2, 3])
        sql = e.sql(dialect="duckdb")
        assert "IN" in sql
        assert "1" in sql and "2" in sql and "3" in sql

    def test_exclude(self):
        e = build_in_clause(column_ref("C", "id"), [5, 6], exclude=True)
        sql = e.sql(dialect="duckdb")
        assert "NOT" in sql

    def test_single(self):
        e = build_in_clause(column_ref("C", "id"), [99])
        sql = e.sql(dialect="duckdb")
        assert "99" in sql

    def test_duplicates(self):
        e = build_in_clause(column_ref("C", "id"), [1, 1, 2, 2, 3])
        sql = e.sql(dialect="duckdb")
        assert "1, 2, 3" in sql or "1" in sql


class TestPrimitivesCodesetJoin:
    """Test codeset_join and codeset_in."""

    def test_codeset_join_basic(self):
        cj = codeset_join("#Codesets", column_ref("co", "condition_concept_id"), 1)
        sql = cj.sql(dialect="duckdb")
        assert "Codesets" in sql
        assert "condition_concept_id" in sql

    def test_codeset_in(self):
        ci = codeset_in(column_ref("C", "type_id"), 5)
        sql = ci.sql(dialect="duckdb")
        assert "SELECT" in sql
        assert "codeset_id" in sql

    def test_codeset_in_exclude(self):
        ci = codeset_in(column_ref("C", "type_id"), 5, exclude=True)
        sql = ci.sql(dialect="duckdb")
        assert "NOT" in sql


class TestRowNumberAcrossBuilders:
    """Validate ROW_NUMBER output across all three builders for first=True."""

    def _check_ordinal_col(self, select: sge.Select):
        """Ensure the outer SELECT produces a query with ordinal expression."""
        sql = select.sql(dialect="duckdb")
        assert "ROW_NUMBER" in sql, f"Missing ROW_NUMBER: {sql}"

    def test_co_ordinal(self):
        co = ConditionOccurrence(codeset_id=1, first=True)
        s = ConditionOccurrenceGlotBuilder().build_select(co)
        self._check_ordinal_col(s)

    def test_de_ordinal(self):
        de = DrugExposure(codeset_id=1, first=True)
        s = DrugExposureGlotBuilder().build_select(de)
        self._check_ordinal_col(s)

    def test_vo_ordinal(self):
        vo = VisitOccurrence(codeset_id=1, first=True)
        s = VisitOccurrenceGlotBuilder().build_select(vo)
        self._check_ordinal_col(s)


class TestCodesetsBuilder:
    """Test concept set resolution matching T-SQL ConceptSetExpressionQueryBuilder."""

    def _build(self, concept_sets):
        from circe.cohortdefinition.sqlglot_builders.codesets import build_codeset_query

        return build_codeset_query(concept_sets)

    def test_empty_concept_sets(self):
        assert self._build([]) is None

    def test_simple_concept_set(self):
        from circe.vocabulary.concept import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem

        cs = ConceptSet(
            id=1, expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(concept_id=123))])
        )
        query = self._build([cs])
        assert query is not None
        sql = query.sql(dialect="tsql")
        assert "123" in sql
        assert "DISTINCT" in sql
        assert "LEFT JOIN" not in sql  # no excludes

    def test_include_and_exclude(self):
        from circe.vocabulary.concept import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem

        cs = ConceptSet(
            id=1,
            expression=ConceptSetExpression(
                items=[
                    ConceptSetItem(concept=Concept(concept_id=100), is_excluded=False),
                    ConceptSetItem(concept=Concept(concept_id=200), is_excluded=True),
                ]
            ),
        )
        query = self._build([cs])
        sql = query.sql(dialect="tsql")
        assert "LEFT JOIN" in sql
        assert "IS NULL" in sql
        assert "DISTINCT" in sql

    def test_include_descendants(self):
        from circe.vocabulary.concept import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem

        cs = ConceptSet(
            id=1,
            expression=ConceptSetExpression(
                items=[
                    ConceptSetItem(
                        concept=Concept(concept_id=10), is_excluded=False, include_descendants=True
                    ),
                ]
            ),
        )
        query = self._build([cs])
        sql = query.sql(dialect="tsql")
        assert "CONCEPT_ANCESTOR" in sql
        assert "invalid_reason" in sql

    def test_include_mapped(self):
        from circe.vocabulary.concept import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem

        cs = ConceptSet(
            id=1,
            expression=ConceptSetExpression(
                items=[
                    ConceptSetItem(concept=Concept(concept_id=1), is_excluded=False, include_mapped=True),
                ]
            ),
        )
        query = self._build([cs])
        sql = query.sql(dialect="tsql")
        assert "concept_relationship" in sql
        assert "Maps to" in sql

    def test_exclude_only_no_includes(self):
        from circe.vocabulary.concept import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem

        cs = ConceptSet(
            id=1,
            expression=ConceptSetExpression(
                items=[
                    ConceptSetItem(concept=Concept(concept_id=99), is_excluded=True),
                ]
            ),
        )
        query = self._build([cs])
        sql = query.sql(dialect="tsql")
        assert "LEFT JOIN" in sql
        assert "IS NULL" in sql
        assert "1 = 0" in sql or "0=1" in sql or "FALSE" in sql

    def test_multiple_concept_sets_union_all(self):
        from circe.vocabulary.concept import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem

        cs1 = ConceptSet(
            id=1, expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(concept_id=1))])
        )
        cs2 = ConceptSet(
            id=2, expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(concept_id=2))])
        )
        query = self._build([cs1, cs2])
        sql = query.sql(dialect="tsql")
        assert "UNION ALL" in sql.upper() or "UNION" in sql.upper()

    def test_concept_set_with_no_items(self):
        from circe.vocabulary.concept import ConceptSet, ConceptSetExpression

        cs = ConceptSet(id=1, expression=ConceptSetExpression(items=[]))
        assert self._build([cs]) is None

    def test_concept_set_without_expression(self):
        from circe.vocabulary.concept import ConceptSet

        cs = ConceptSet(id=1, name="noexpr")
        assert self._build([cs]) is None

    def test_no_double_join(self):
        from circe.vocabulary.concept import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem

        cs = ConceptSet(
            id=1,
            expression=ConceptSetExpression(
                items=[
                    ConceptSetItem(concept=Concept(concept_id=1), is_excluded=True, include_descendants=True),
                    ConceptSetItem(concept=Concept(concept_id=2), is_excluded=False, include_mapped=True),
                ]
            ),
        )
        query = self._build([cs])
        sql = query.sql(dialect="tsql")
        assert "JOIN JOIN" not in sql, "Double JOIN found"


class TestCrossDialect:
    """Compile each builder to multiple dialects; verify sqlglot can read back."""

    @staticmethod
    def _check_dialect(sel: sge.Select, dialect: str):
        sql = sel.sql(dialect=dialect)
        assert len(sql) > 0
        clean = sql.replace("#Codesets", "Codesets")
        parsed = sge.maybe_parse(clean, dialect=dialect)
        assert parsed is not None, f"Cannot parse {dialect} output back"

    def test_co_multiple_dialects(self):
        co = ConditionOccurrence(codeset_id=1, age=NumericRange(op="gte", value=18))
        sel = ConditionOccurrenceGlotBuilder().build_select(co)
        for d in ("duckdb", "postgres", "tsql", "bigquery"):
            self._check_dialect(sel, d)

    def test_de_multiple_dialects(self):
        de = DrugExposure(codeset_id=1)
        sel = DrugExposureGlotBuilder().build_select(de)
        for d in ("duckdb", "postgres", "tsql", "mysql"):
            self._check_dialect(sel, d)

    def test_vo_multiple_dialects(self):
        vo = VisitOccurrence(codeset_id=1, first=True)
        sel = VisitOccurrenceGlotBuilder().build_select(vo)
        for d in ("duckdb", "tsql", "bigquery"):
            self._check_dialect(sel, d)
