"""Shared-checkpoint execution for cohort definition sets.

A cohort definition set is planned as a small DAG of pipeline checkpoints:

.. code-block:: text

    C2 primary events        (per distinct primary criteria + limits)
      └─ C3 qualified events (per distinct additional criteria + qualified limit)
           ├─ rule match     (per distinct inclusion rule on a C3)
           └─ C4..C8         (per cohort: inclusion rules → expression limit →
                              end strategy → censoring → collapse)

Every checkpoint is materialised once and read by all cohorts that need it, so a
family of cohorts that share an entry population pays for the entry scan,
observation-window join, and correlated-criteria work once instead of N times.
Checkpoints are keyed by content: concept sets are canonicalised first, so two
cohorts that use different local concept-set ids for the same concepts still
share.

The tail stages call exactly the same engine functions a stand-alone build uses
on exactly the same materialised rows, which is what keeps the output identical
to ``generate_cohort_set(..., shared=False)``.
"""

from __future__ import annotations

import contextlib
import logging
import threading
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from ..cohortdefinition import CohortExpression
from ..decomposition.canonical import ConceptSetCanonicalizer, stable_digest
from .api import write_cohort
from .engine.censoring import apply_censoring
from .engine.cohort import cohort_plan_from_normalized
from .engine.collapse import collapse_events
from .engine.end_strategy import apply_end_strategy
from .engine.group_keys import event_keys
from .engine.groups import apply_additional_criteria
from .engine.limits import apply_result_limit
from .engine.primary import build_primary_events
from .ibis.codesets import build_single_codeset_table
from .ibis.context import make_execution_context
from .ibis.materialize import project_to_ohdsi_cohort_table
from .ibis.operations import create_table, read_table
from .normalize.cohort import NormalizedCohort, normalize_cohort
from .session import register_session, unregister_session
from .typing import IbisBackendLike, Table

logger = logging.getLogger(__name__)

__all__ = [
    "CohortExecution",
    "RuleCheckpoint",
    "SharedCohortExecutor",
    "SharedExecutionPlan",
    "build_shared_execution_plan",
]


def _backend_lock() -> threading.Lock:
    """Return the batch-generation lock shared with ``_process_single_cohort``.

    Sharing the lock means the batch cleanup path (which waits on it) cannot drop
    staging tables while a timed-out executor thread is still populating them.
    Imported lazily to avoid a module cycle: ``_generate`` imports this module
    only when shared execution is requested.
    """
    from ..cohort_definition_set._generate import _backend_lock as lock

    return lock


@dataclass(frozen=True)
class RuleCheckpoint:
    """A shared inclusion-rule match table on one qualified-events checkpoint."""

    key: str
    input_key: str
    rule_name: str | None
    expression: Any


@dataclass(frozen=True)
class CohortExecution:
    """Per-cohort execution entry in a shared plan."""

    cohort_id: int
    cohort_name: str
    primary_key: str
    qualified_key: str | None
    rule_keys: tuple[str, ...]
    normalized: NormalizedCohort | None
    error: Exception | None = None

    @property
    def input_key(self) -> str:
        return self.qualified_key or self.primary_key


@dataclass(frozen=True)
class SharedExecutionPlan:
    """Content-addressed checkpoint DAG for a cohort definition set."""

    cohorts: tuple[CohortExecution, ...]
    primary_nodes: Mapping[str, NormalizedCohort]
    qualified_nodes: Mapping[str, NormalizedCohort]
    rule_nodes: Mapping[str, RuleCheckpoint]

    @property
    def standalone_rule_references(self) -> int:
        return sum(len(cohort.rule_keys) for cohort in self.cohorts)

    def explain(self) -> dict[str, Any]:
        """Return checkpoint counts and the estimated work avoided."""
        cohort_count = len(self.cohorts)
        primary_count = len(self.primary_nodes)
        qualified_count = len(self.qualified_nodes)
        rule_count = len(self.rule_nodes)

        standalone_qualified = sum(1 for cohort in self.cohorts if cohort.qualified_key is not None)
        standalone_checkpoints = cohort_count + standalone_qualified + self.standalone_rule_references
        shared_checkpoints = primary_count + qualified_count + rule_count

        return {
            "cohorts": cohort_count,
            "primary_checkpoints": primary_count,
            "qualified_checkpoints": qualified_count,
            "rule_checkpoints": rule_count,
            "standalone_checkpoints": standalone_checkpoints,
            "shared_checkpoints": shared_checkpoints,
            "reuse_factor": (
                round(standalone_checkpoints / shared_checkpoints, 2) if shared_checkpoints else 0.0
            ),
            "primary_scans_saved": cohort_count - primary_count,
            "qualified_recomputations_saved": standalone_qualified - qualified_count,
            "rule_recomputations_saved": self.standalone_rule_references - rule_count,
            "failed_cohorts": sum(1 for cohort in self.cohorts if cohort.error is not None),
        }

    def describe(self) -> str:
        """Return a one-line summary of the plan for logs."""
        summary = self.explain()
        return (
            f"Shared execution plan: {summary['cohorts']} cohort(s), "
            f"{summary['primary_checkpoints']} primary checkpoint(s), "
            f"{summary['qualified_checkpoints']} qualified checkpoint(s), "
            f"{summary['rule_checkpoints']} rule checkpoint(s); "
            f"{summary['reuse_factor']}x checkpoint reuse."
        )


def _primary_key(normalized: NormalizedCohort) -> str:
    return stable_digest({"engine": "ibis-v1", "primary": normalized.primary})[:32]


def _has_additional(normalized: NormalizedCohort) -> bool:
    group = normalized.additional_criteria
    return group is not None and not group.is_empty()


def _qualified_key(normalized: NormalizedCohort, primary_key: str) -> str | None:
    if not _has_additional(normalized):
        # Mirrors the stand-alone engine: QualifiedLimit only applies when
        # AdditionalCriteria is present, so without it C3 *is* C2.
        return None
    return stable_digest(
        {
            "engine": "ibis-v1",
            "primary": primary_key,
            "additional": normalized.additional_criteria,
            "qualified_limit": normalized.result_limits.qualified_limit_type,
        }
    )[:32]


def _rule_key(input_key: str, rule: Any) -> str:
    return stable_digest(
        {
            "engine": "ibis-v1",
            "input": input_key,
            "rule": rule.expression,
        }
    )[:32]


def build_shared_execution_plan(
    cohorts: Iterable[tuple[int, str, CohortExpression]],
    *,
    canonicalizer: ConceptSetCanonicalizer | None = None,
) -> tuple[SharedExecutionPlan, ConceptSetCanonicalizer]:
    """Plan shared checkpoints for ``(cohort_id, cohort_name, expression)`` triples.

    Cohort expressions are canonicalised (concept-set ids rewritten by content)
    before checkpoint keys are computed.  Per-cohort normalisation errors are
    captured in the plan instead of aborting the batch.
    """
    items = [(int(cohort_id), str(name), expression) for cohort_id, name, expression in cohorts]
    canonicalizer = canonicalizer or ConceptSetCanonicalizer()

    for _, _, expression in items:
        canonicalizer.register_expression(expression)

    primary_nodes: dict[str, NormalizedCohort] = {}
    qualified_nodes: dict[str, NormalizedCohort] = {}
    rule_nodes: dict[str, RuleCheckpoint] = {}
    execution: list[CohortExecution] = []

    for cohort_id, cohort_name, expression in items:
        try:
            canonical = canonicalizer.canonicalize(expression)
            normalized = normalize_cohort(canonical)
        except Exception as exc:  # surfaced per cohort when it is executed
            execution.append(
                CohortExecution(
                    cohort_id=cohort_id,
                    cohort_name=cohort_name,
                    primary_key="",
                    qualified_key=None,
                    rule_keys=(),
                    normalized=None,
                    error=exc,
                )
            )
            continue

        primary_key = _primary_key(normalized)
        primary_nodes.setdefault(primary_key, normalized)

        qualified_key = _qualified_key(normalized, primary_key)
        if qualified_key is not None:
            qualified_nodes.setdefault(qualified_key, normalized)

        input_key = qualified_key or primary_key
        rule_keys: list[str] = []
        for rule in normalized.inclusion_rules:
            if rule.expression is None or rule.expression.is_empty():
                continue
            key = _rule_key(input_key, rule)
            rule_nodes.setdefault(
                key,
                RuleCheckpoint(
                    key=key,
                    input_key=input_key,
                    rule_name=rule.name,
                    expression=rule.expression,
                ),
            )
            rule_keys.append(key)

        execution.append(
            CohortExecution(
                cohort_id=cohort_id,
                cohort_name=cohort_name,
                primary_key=primary_key,
                qualified_key=qualified_key,
                rule_keys=tuple(rule_keys),
                normalized=normalized,
            )
        )

    plan = SharedExecutionPlan(
        cohorts=tuple(execution),
        primary_nodes=primary_nodes,
        qualified_nodes=qualified_nodes,
        rule_nodes=rule_nodes,
    )
    return plan, canonicalizer


class SharedCohortExecutor:
    """Execute a cohort definition set while reusing shared checkpoints.

    The executor owns the staging tables it creates.  When *session_prefix* is
    supplied (as by :func:`~circe.cohort_definition_set.generate_cohort_set`),
    the caller is responsible for dropping prefix-owned tables; otherwise the
    executor registers its own session and :meth:`close` cleans up.
    """

    def __init__(
        self,
        *,
        backend: IbisBackendLike,
        cdm_schema: str,
        cohort_table: str,
        results_schema: str | None = None,
        vocabulary_schema: str | None = None,
        session_prefix: str = "",
    ) -> None:
        self._backend = backend
        self._cdm_schema = cdm_schema
        self._results_schema = results_schema
        self._vocabulary_schema = vocabulary_schema or cdm_schema
        self._cohort_table = cohort_table
        self._schema = results_schema or cdm_schema

        self._owns_session = not session_prefix
        if not session_prefix:
            session_prefix = f"__x_{uuid.uuid4().hex[:8]}_"
            register_session(backend, schema=self._schema, session_prefix=session_prefix)
        self._session_prefix = session_prefix

        self._plan: SharedExecutionPlan | None = None
        self._canonicalizer: ConceptSetCanonicalizer | None = None
        self._by_id: dict[int, CohortExecution] = {}
        self._context: Any = None
        self._tables: dict[str, Table] = {}
        self._created_tables: list[str] = []
        self._table_counter = 0

    # -- planning ----------------------------------------------------------
    def plan(self, cohorts: Iterable[tuple[int, str, CohortExpression]]) -> SharedExecutionPlan:
        """Plan shared checkpoints for a cohort set (idempotent)."""
        if self._plan is not None:
            return self._plan
        self._plan, self._canonicalizer = build_shared_execution_plan(cohorts)
        self._by_id = {cohort.cohort_id: cohort for cohort in self._plan.cohorts}
        return self._plan

    @property
    def plan_result(self) -> SharedExecutionPlan:
        if self._plan is None:
            raise RuntimeError("SharedCohortExecutor.plan() must be called before inspection.")
        return self._plan

    def explain(self) -> dict[str, Any]:
        return self.plan_result.explain()

    def describe(self) -> str:
        return self.plan_result.describe()

    # -- internals ---------------------------------------------------------
    def _execution_context(self):
        if self._context is not None:
            return self._context
        assert self._canonicalizer is not None
        codeset_table = build_single_codeset_table(
            backend=self._backend,
            concept_sets=self._canonicalizer.concept_sets,
            batch_table_name="shared_codesets",
            results_schema=self._schema,
            vocabulary_schema=self._vocabulary_schema,
            session_prefix=self._session_prefix,
        )
        self._created_tables.append(f"{self._session_prefix}shared_codesets")
        self._context = make_execution_context(
            backend=self._backend,
            cdm_schema=self._cdm_schema,
            results_schema=self._results_schema,
            vocabulary_schema=self._vocabulary_schema,
            codeset_table=codeset_table,
        )
        return self._context

    def _materialize(self, relation: Table, label: str) -> Table:
        self._table_counter += 1
        name = f"{self._session_prefix}shared_{label}_{self._table_counter}"
        create_table(self._backend, table_name=name, schema=self._schema, obj=relation, overwrite=True)
        self._created_tables.append(name)
        return read_table(self._backend, table_name=name, schema=self._schema)

    def _primary_table(self, key: str) -> Table:
        cached = self._tables.get(key)
        if cached is not None:
            return cached
        normalized = self.plan_result.primary_nodes[key]
        context = self._execution_context()
        relation = build_primary_events(cohort_plan_from_normalized(normalized), context)
        table = self._materialize(relation, "primary")
        self._tables[key] = table
        return table

    def _qualified_table(self, planned: CohortExecution, primary: Table) -> Table:
        if planned.qualified_key is None:
            return primary
        cached = self._tables.get(planned.qualified_key)
        if cached is not None:
            return cached

        normalized = self.plan_result.qualified_nodes[planned.qualified_key]
        context = self._execution_context()
        relation = apply_additional_criteria(primary, normalized.additional_criteria, context)
        relation = apply_result_limit(relation, normalized.result_limits.qualified_limit_type)
        table = self._materialize(relation, "qualified")
        self._tables[planned.qualified_key] = table
        return table

    def _rule_table(self, key: str) -> Table:
        cached = self._tables.get(key)
        if cached is not None:
            return cached
        checkpoint = self.plan_result.rule_nodes[key]
        input_table = self._tables.get(checkpoint.input_key)
        if input_table is None:
            raise RuntimeError(
                f"Rule checkpoint {key} was requested before its input checkpoint "
                f"{checkpoint.input_key} was materialised."
            )
        context = self._execution_context()
        matched = apply_additional_criteria(input_table, checkpoint.expression, context)
        table = self._materialize(event_keys(matched), "rule")
        self._tables[key] = table
        return table

    def _included_relation(self, planned: CohortExecution, qualified: Table) -> Table:
        if not planned.rule_keys:
            return qualified

        relation = qualified
        columns = list(qualified.columns)
        for rule_key in planned.rule_keys:
            rule_table = self._rule_table(rule_key)
            relation = relation.join(
                rule_table,
                predicates=[
                    (relation.person_id == rule_table.person_id) & (relation.event_id == rule_table.event_id)
                ],
            )
            relation = relation.select(*[relation[column] for column in columns])
        return self._materialize(relation, f"included_{planned.cohort_id}")

    # -- execution ---------------------------------------------------------
    def build(self, cohort_id: int) -> Table:
        """Return the final cohort relation for *cohort_id* (rows not projected)."""
        if self._plan is None:
            raise RuntimeError("SharedCohortExecutor.plan() must be called before build().")
        planned = self._by_id.get(int(cohort_id))
        if planned is None:
            raise KeyError(f"cohort_id={cohort_id} is not part of this execution plan.")
        if planned.error is not None:
            raise planned.error
        assert planned.normalized is not None

        context = self._execution_context()
        normalized = planned.normalized

        primary = self._primary_table(planned.primary_key)
        qualified = self._qualified_table(planned, primary)
        included = self._included_relation(planned, qualified)

        limited = apply_result_limit(included, normalized.result_limits.expression_limit_type)
        ended = apply_end_strategy(limited, normalized.end_strategy, context)
        censored = apply_censoring(ended, normalized.censoring_criteria, normalized.censor_window, context)
        return collapse_events(censored, normalized.collapse_settings, normalized.censor_window)

    def write(self, cohort_id: int) -> None:
        """Build *cohort_id* and write its OHDSI cohort-table rows."""
        with _backend_lock():
            relation = self.build(cohort_id)
            projected = project_to_ohdsi_cohort_table(relation, cohort_id=cohort_id)
            write_cohort(
                compiled_relation=projected,
                backend=self._backend,
                cdm_schema=self._cdm_schema,
                cohort_table=self._cohort_table,
                cohort_id=cohort_id,
                results_schema=self._results_schema,
                vocabulary_schema=self._vocabulary_schema,
                if_exists="replace",
            )

    def close(self) -> None:
        """Drop staging tables and unregister the session when it is owned."""
        for name in list(self._created_tables):
            with contextlib.suppress(Exception):
                self._backend.drop_table(name, database=self._schema, force=True)
        self._created_tables.clear()
        self._tables.clear()
        if self._owns_session:
            with contextlib.suppress(Exception):
                unregister_session(
                    self._backend,
                    schema=self._schema,
                    session_prefix=self._session_prefix,
                )

    def __enter__(self) -> SharedCohortExecutor:
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()
