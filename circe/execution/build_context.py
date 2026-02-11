from __future__ import annotations

import uuid
import weakref
from dataclasses import dataclass
from functools import reduce
from pathlib import Path
from typing import Callable, Iterable, Optional, Tuple, Union

import ibis
import ibis.common.exceptions as ibis_exc
import ibis.expr.types as ir

from ..vocabulary.concept import ConceptSet
from .ibis_compat import table_from_literal_list

Database = Union[str, Tuple[str, str]]


def _qualify(database: Database | None, name: str) -> str:
    """Only for statements were constructing outside of Ibis."""
    if database is None:
        return name
    if isinstance(database, tuple):
        return ".".join(database + (name,))
    return f"{database}.{name}"


def _table(conn: ibis.BaseBackend, database: Database | None, name: str) -> ir.Table:
    return conn.table(name, database=database)


def _warn(message: str) -> None:
    print(f"Warning: {message}")


def _analyze_table(
    conn: ibis.BaseBackend, *, backend: str | None, qualified_name: str
) -> None:
    if not backend:
        return
    if backend in ("postgres", "duckdb"):
        conn.raw_sql(f"ANALYZE {qualified_name}")
        return
    if backend == "databricks":
        conn.raw_sql(f"ANALYZE TABLE {qualified_name} COMPUTE STATISTICS")


def _drop_table_safely(
    conn: ibis.BaseBackend,
    *,
    name: str,
    database: Database | None = None,
    warning_label: str,
) -> None:
    try:
        conn.drop_table(name, database=database, force=True)
    except Exception as exc:
        _warn(f"could not drop {warning_label}: {exc}")


@dataclass(frozen=True)
class CohortBuildOptions:
    cdm_schema: Optional[str] = None
    vocabulary_schema: Optional[str] = None
    result_schema: Optional[str] = None
    target_table: Optional[str] = None
    cohort_id: Optional[int] = None
    generate_stats: bool = False
    temp_emulation_schema: Optional[str] = None
    profile_dir: Optional[str] = None
    capture_sql: bool = False
    backend: Optional[str] = None
    materialize_stages: bool = True
    materialize_codesets: bool = True


@dataclass
class CodesetResource:
    table: ir.Table
    _dropper: Optional[Callable[[], None]] = None

    def cleanup(self):
        if self._dropper:
            try:
                self._dropper()
            finally:
                self._dropper = None


class BuildContext:
    """Holds shared state (connection, schemas, compiled codesets) used across builders."""

    def __init__(
        self,
        conn: ibis.BaseBackend,
        options: CohortBuildOptions,
        codeset_resource: CodesetResource | ir.Table,
    ):
        self._conn = conn
        self._options = options
        if isinstance(codeset_resource, CodesetResource):
            self._codeset_resource = codeset_resource
        else:
            self._codeset_resource = CodesetResource(table=codeset_resource)
        self._codesets = self._codeset_resource.table
        self._cleanup_callbacks: list[Callable[[], None]] = []
        self._correlated_cache: dict[str, ir.Table] = {}
        self._profile_dir = None
        if options.profile_dir:
            path = Path(options.profile_dir).resolve()
            path.mkdir(parents=True, exist_ok=True)
            self._profile_dir = path
        self._captured_sql: list[tuple[str, str]] = []
        self._slice_cache: dict[str, ir.Table] = {}
        weakref.finalize(self, self.close)

    def _table(self, database: Optional[str], name: str) -> ir.Table:
        try:
            return _table(self._conn, database, name)
        except (
            ibis_exc.IbisError,
            TypeError,
            ValueError,
            AttributeError,
            NotImplementedError,
        ):
            return self._conn.sql(f"SELECT * FROM {_qualify(database, name)}")

    def table(self, name: str) -> ir.Table:
        """Return a CDM table."""
        return self._table(self._options.cdm_schema, name)

    def vocabulary_table(self, name: str) -> ir.Table:
        """Return a vocabulary table (concept, concept_ancestor, etc.)."""
        schema = self._options.vocabulary_schema or self._options.cdm_schema
        return self._table(schema, name)

    def codeset(self, codeset_id: int, *, is_exclusion: bool = False) -> ir.Table:
        """Return concepts for the requested codeset. `is_exclusion` is provided for parity with Circe."""
        _ = is_exclusion  # placeholder for future differentiated handling
        return self._codesets.filter(self._codesets.codeset_id == codeset_id)

    def get_cached_correlated(self, key: str) -> ir.Table | None:
        return self._correlated_cache.get(key)

    def cache_correlated(self, key: str, table: ir.Table) -> None:
        self._correlated_cache[key] = table

    def materialize(
        self,
        expr: ir.Table,
        *,
        label: str,
        temp: bool = True,
        analyze: bool = True,
    ) -> ir.Table:
        """
        Materialize an Ibis expression, capturing a unique DuckDB profiling
        artifact for this step.
        """
        step_id = uuid.uuid4().hex[:8]
        table_name = f"_stage_{label}_{step_id}"
        backend = self._options.backend

        # "temp emulation" means: create a *real* table in a chosen database/schema.
        use_temp_emulation = temp and self._options.temp_emulation_schema is not None
        database: Database | None = (
            self._options.temp_emulation_schema if use_temp_emulation else None
        )
        temp_flag = False if use_temp_emulation else temp

        # duckdb profiling setup for local dev
        profile_filename: Path | None = None
        profiling_enabled = False
        if backend == "duckdb" and self._profile_dir is not None:
            profile_filename = (
                self._profile_dir / f"ibis_profile_{label}_{step_id}.json"
            ).resolve()
            try:
                escaped = str(profile_filename).replace("'", "''")
                self._conn.raw_sql(f"SET profiling_output='{escaped}'")
                self._conn.raw_sql("SET enable_profiling='json'")
                self._conn.raw_sql("SET profiling_coverage='ALL'")
                profiling_enabled = True
            except Exception as exc:
                _warn(f"could not enable DuckDB profiling for {label}: {exc}")

        try:
            self._conn.create_table(
                table_name,
                obj=expr,
                database=database,
                temp=temp_flag,
                overwrite=True,
            )
            if self._options.capture_sql:
                self._captured_sql.append((table_name, self._conn.compile(expr)))
        finally:
            if profiling_enabled:
                try:
                    self._conn.raw_sql("PRAGMA disable_profiling")
                except Exception as exc:
                    _warn(f"could not disable DuckDB profiling for {label}: {exc}")

        if profiling_enabled and profile_filename is not None:
            print(f"[Profile Captured]: {profile_filename} (Table: {table_name})")

        if analyze:
            qualified = _qualify(database, table_name)
            try:
                _analyze_table(self._conn, backend=backend, qualified_name=qualified)
            except Exception as exc:
                _warn(f"could not analyze table {qualified}: {exc}")

        def _drop():
            _drop_table_safely(
                self._conn,
                name=table_name,
                database=database,
                warning_label=f"table {table_name} in {database}",
            )

        self.register_cleanup(_drop)
        return _table(self._conn, database, table_name)

    def should_materialize_stages(self) -> bool:
        return bool(self._options.materialize_stages)

    def maybe_materialize(
        self,
        expr: ir.Table,
        *,
        label: str,
        temp: bool = True,
        analyze: bool = True,
    ) -> ir.Table:
        if not self.should_materialize_stages():
            return expr
        return self.materialize(expr, label=label, temp=temp, analyze=analyze)

    def write_cohort_table(
        self,
        events: ir.Table,
        *,
        table_name: str | None = None,
        database: Database | None = None,
        overwrite: bool = True,
        append: bool = False,
    ) -> ir.Table:
        """
        Persist cohort rows to a results table.

        Output schema matches OHDSI cohort tables:
          (cohort_definition_id, subject_id, cohort_start_date, cohort_end_date)
        """
        target_table = table_name or self._options.target_table
        if not target_table:
            raise ValueError(
                "target_table must be set (argument or CohortBuildOptions.target_table)"
            )
        target_db = database if database is not None else self._options.result_schema
        if target_db is None:
            raise ValueError(
                "result_schema must be set (argument or CohortBuildOptions.result_schema)"
            )

        cohort_id = self._options.cohort_id
        cohort_id_expr = (
            ibis.literal(int(cohort_id), type="int64")
            if cohort_id is not None
            else ibis.null().cast("int64")
        )

        result = events.select(
            cohort_id_expr.name("cohort_definition_id"),
            events.person_id.cast("int64").name("subject_id"),
            events.start_date.cast("date").name("cohort_start_date"),
            events.end_date.cast("date").name("cohort_end_date"),
        )

        obj = result
        if append:
            try:
                existing = _table(self._conn, target_db, target_table)
                obj = existing.union(result, distinct=False)
            except (
                ibis_exc.IbisError,
                TypeError,
                ValueError,
                AttributeError,
                NotImplementedError,
            ):
                obj = result

        self._conn.create_table(
            target_table,
            obj=obj,
            database=target_db,
            temp=False,
            overwrite=overwrite,
        )
        return _table(self._conn, target_db, target_table)

    @property
    def codesets(self) -> ir.Table:
        return self._codesets

    @property
    def conn(self) -> ibis.BaseBackend:
        return self._conn

    def options(self) -> CohortBuildOptions:
        return self._options

    def captured_sql(self) -> list[tuple[str, str]]:
        return list(self._captured_sql)

    def register_cleanup(self, callback: Callable[[], None]):
        self._cleanup_callbacks.append(callback)

    def get_or_materialize_slice(
        self,
        cache_key: str,
        expr: ir.Table,
        *,
        label: str | None = None,
    ) -> ir.Table:
        """Materialize an expression once and reuse the resulting temp table for later lookups."""
        if not self.should_materialize_stages():
            return expr.view()
        cached = self._slice_cache.get(cache_key)
        if cached is not None:
            return cached
        label_hint = label or "slice"
        table = self.materialize(expr, label=label_hint, temp=True, analyze=True)
        self._slice_cache[cache_key] = table
        return table

    def close(self):
        if self._codeset_resource is not None:
            self._codeset_resource.cleanup()
            self._codeset_resource = None  # type: ignore[assignment]
        while self._cleanup_callbacks:
            callback = self._cleanup_callbacks.pop()
            try:
                callback()
            except Exception as exc:
                _warn(f"cleanup callback failed: {exc}")
        self._captured_sql.clear()
        self._slice_cache.clear()


def compile_codesets(
    conn: ibis.BaseBackend,
    concept_sets: list[ConceptSet],
    options: CohortBuildOptions,
) -> CodesetResource:
    """Rebuild Circe concept set logic as an ibis expression."""

    vocab_schema = options.vocabulary_schema or options.cdm_schema
    concept = _table(conn, vocab_schema, "concept")
    concept_ancestor = _table(conn, vocab_schema, "concept_ancestor")
    concept_relationship = _table(conn, vocab_schema, "concept_relationship")

    compiled = []
    for concept_set in concept_sets or []:
        compiled_expr = _compile_single_codeset(
            concept, concept_ancestor, concept_relationship, concept_set
        )
        if compiled_expr is not None:
            compiled.append(compiled_expr)

    if not compiled:
        compiled_expr = _empty_codeset_table()
    else:
        compiled_expr = _union_all(compiled).distinct()

    if not options.materialize_codesets:
        return CodesetResource(table=compiled_expr)

    return _materialize_codesets(conn, compiled_expr, options)


def _compile_single_codeset(
    concept: ir.Table,
    concept_ancestor: ir.Table,
    concept_relationship: ir.Table,
    concept_set: ConceptSet,
) -> Optional[ir.Table]:
    expression = concept_set.expression
    if expression is None or not expression.items:
        return None

    include_ids: list[int] = []
    include_descendant_ids: list[int] = []
    include_mapped_ids: list[int] = []
    include_mapped_descendant_ids: list[int] = []

    exclude_ids: list[int] = []
    exclude_descendant_ids: list[int] = []
    exclude_mapped_ids: list[int] = []
    exclude_mapped_descendant_ids: list[int] = []

    for item in expression.items:
        if item.concept is None or item.concept.concept_id is None:
            continue
        target_include = not bool(item.is_excluded)
        include_descendants = bool(item.include_descendants)
        include_mapped = bool(item.include_mapped)
        concept_id = int(item.concept.concept_id)

        if target_include:
            include_ids.append(concept_id)
            if include_descendants:
                include_descendant_ids.append(concept_id)
            if include_mapped:
                include_mapped_ids.append(concept_id)
                if include_descendants:
                    include_mapped_descendant_ids.append(concept_id)
        else:
            exclude_ids.append(concept_id)
            if include_descendants:
                exclude_descendant_ids.append(concept_id)
            if include_mapped:
                exclude_mapped_ids.append(concept_id)
                if include_descendants:
                    exclude_mapped_descendant_ids.append(concept_id)

    include_expr = _union_distinct(
        [
            _ids_memtable(include_ids),
            _descendants(concept, concept_ancestor, include_descendant_ids),
            _mapped_concepts(
                concept,
                concept_ancestor,
                concept_relationship,
                include_mapped_ids,
                include_mapped_descendant_ids,
            ),
        ]
    )

    if include_expr is None:
        return None

    exclude_expr = _union_distinct(
        [
            _ids_memtable(exclude_ids),
            _descendants(concept, concept_ancestor, exclude_descendant_ids),
            _mapped_concepts(
                concept,
                concept_ancestor,
                concept_relationship,
                exclude_mapped_ids,
                exclude_mapped_descendant_ids,
            ),
        ]
    )

    if exclude_expr is not None:
        include_expr = include_expr.anti_join(exclude_expr, ["concept_id"])

    codeset_literal = ibis.literal(int(concept_set.id), type="int64")
    return include_expr.mutate(codeset_id=codeset_literal)[["codeset_id", "concept_id"]]


def _ids_memtable(ids: list[int]) -> Optional[ir.Table]:
    if not ids:
        return None
    return table_from_literal_list(
        ids, column_name="concept_id", element_type="int64"
    ).distinct()


def _descendants(
    concept: ir.Table, concept_ancestor: ir.Table, ancestor_ids: list[int]
) -> Optional[ir.Table]:
    if not ancestor_ids:
        return None
    return (
        concept_ancestor.filter(concept_ancestor.ancestor_concept_id.isin(ancestor_ids))
        .join(concept, concept_ancestor.descendant_concept_id == concept.concept_id)
        .filter(concept.invalid_reason.isnull())
        .select(concept.concept_id.cast("int64").name("concept_id"))
        .distinct()
    )


def _mapped_concepts(
    concept: ir.Table,
    concept_ancestor: ir.Table,
    concept_relationship: ir.Table,
    concepts_to_map: list[int],
    concepts_with_descendants_to_map: list[int],
) -> Optional[ir.Table]:
    sources = _union_distinct(
        [
            _ids_memtable(concepts_to_map),
            _descendants(concept, concept_ancestor, concepts_with_descendants_to_map),
        ]
    )

    if sources is None:
        return None

    valid_relationships = concept_relationship.filter(
        [
            concept_relationship.relationship_id == "Maps to",
            concept_relationship.invalid_reason.isnull(),
        ]
    )

    return (
        sources.join(
            valid_relationships, sources.concept_id == valid_relationships.concept_id_2
        )
        .select(valid_relationships.concept_id_1.cast("int64").name("concept_id"))
        .distinct()
    )


def _empty_codeset_table() -> ir.Table:
    empty_concepts = table_from_literal_list(
        [], column_name="concept_id", element_type="int64"
    )
    empty_codesets = empty_concepts.mutate(
        codeset_id=ibis.null().cast("int64"),
    )
    return empty_codesets.select("codeset_id", "concept_id")


def _materialize_codesets(
    conn: ibis.BaseBackend,
    expr: ir.Table,
    options: CohortBuildOptions,
) -> CodesetResource:
    name = f"_codesets_{uuid.uuid4().hex}"
    if options.temp_emulation_schema:
        database: Database = options.temp_emulation_schema
        conn.create_table(
            name,
            obj=expr,
            database=database,
            temp=False,
            overwrite=True,
        )
        table = _table(conn, database, name)
        qualified = _qualify(database, name)

        def _drop():
            _drop_table_safely(
                conn,
                name=name,
                database=database,
                warning_label=f"codeset table {name} in {database}",
            )

    else:
        conn.create_table(
            name,
            obj=expr,
            temp=True,
            overwrite=True,
        )
        table = _table(conn, None, name)
        qualified = _qualify(None, name)

        def _drop():
            _drop_table_safely(
                conn,
                name=name,
                warning_label=f"codeset temp table {name}",
            )

    backend = options.backend
    if backend:
        try:
            _analyze_table(conn, backend=backend, qualified_name=qualified)
        except Exception as exc:
            _warn(f"could not analyze codeset table {qualified}: {exc}")

    resource = CodesetResource(table=table, _dropper=_drop)
    weakref.finalize(resource, resource.cleanup)
    return resource


def _union_distinct(tables: Iterable[Optional[ir.Table]]) -> Optional[ir.Table]:
    valid_tables = [t for t in tables if t is not None]
    if not valid_tables:
        return None

    return reduce(
        lambda left, right: left.union(right, distinct=True),
        valid_tables[1:],
        valid_tables[0],
    )


def _union_all(tables: list[ir.Table]) -> ir.Table:
    return reduce(lambda left, right: left.union(right), tables[1:], tables[0])
