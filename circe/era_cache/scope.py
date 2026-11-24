"""Scoping an era-cache build to a population.

Two pipelines exist, and they differ only in *which subjects* a build covers:

``cohort`` scope — the default
    Build eras only for the people in a specified cohort (or set of cohort ids).
    This is what almost every study needs: a cohort of a few thousand people has
    a few thousand person-timelines, so the cache stays small enough to rebuild
    freely and to keep beside the study it serves.

``whole-cdm`` scope — explicit opt-in
    Build eras for every person in the CDM.  Useful when one cache must serve
    many unrelated studies, but it is a very large dataset: at 465k people and a
    dozen features it already reaches tens of millions of rows, and it grows with
    the cohort-independent breadth of the feature set.  :func:`whole_cdm` is the
    only way to ask for it, so it can never happen by accident.

The scope is part of the cache identity.  Two builds over the same features but
different subject populations must not share rows, so :meth:`CohortScope.fingerprint`
feeds the ``cache_key``.  Without this, a cohort-scoped build would be silently
reused for a different cohort set and quietly return the wrong denominators.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..execution.typing import IbisBackendLike

__all__ = [
    "CohortScope",
    "cohort_scope",
    "scope_from_cohort_table",
    "whole_cdm",
    "WHOLE_CDM_SCOPE",
]


@dataclass(frozen=True)
class CohortScope:
    """Which subjects an era-cache build covers.

    Exactly one of ``cohort_ids`` / ``subject_relation`` is required for a
    cohort scope; both being ``None`` means the whole CDM, which must be
    requested through :func:`whole_cdm` so it is never accidental.
    """

    kind: Literal["cohort", "whole_cdm"]
    cohort_ids: tuple[int, ...] = ()
    cohort_table: str | None = None
    cohort_column: str = "cohort_definition_id"
    subject_column: str = "subject_id"
    schema: str | None = None
    # True when every cohort in cohort_table is in scope. Distinguishes "all
    # cohorts in this table" from "no cohort specified", which is an error.
    all_cohorts: bool = False
    # Populated by scope_from_cohort_table when a caller wants to pin the exact
    # membership rather than the cohort id (for example a sampled cohort).
    subject_fingerprint: str | None = None

    def __post_init__(self) -> None:
        if self.kind == "whole_cdm":
            if self.cohort_ids or self.cohort_table:
                raise ValueError("whole_cdm scope must not specify cohorts.")
            return
        if self.kind != "cohort":
            raise ValueError(f"Unsupported scope kind {self.kind!r}.")
        if self.cohort_table is None:
            raise ValueError(
                "A cohort scope needs a cohort_table to resolve subjects. Use "
                "whole_cdm() to build the cache for every person in the CDM."
            )
        if not self.cohort_ids and not self.all_cohorts:
            raise ValueError(
                "A cohort scope needs at least one cohort id; pass cohort_ids=... . "
                "Use scope_from_cohort_table(cohort_ids=None) to take every cohort "
                "in a table."
            )
        if self.cohort_table is not None and not self.cohort_column:
            raise ValueError("cohort_column must be set when cohort_table is given.")

    @property
    def is_whole_cdm(self) -> bool:
        return self.kind == "whole_cdm"

    def fingerprint(self) -> str:
        """Return a stable identity for the covered population.

        Two builds share cached rows only when this matches, so it must capture
        everything that changes *who* is included. Definitions of the cohorts
        themselves are the caller's responsibility (a regenerated cohort table
        with the same ids and the same people is the same population).
        """
        if self.is_whole_cdm:
            payload: dict[str, object] = {"kind": "whole_cdm"}
        else:
            payload = {
                "kind": "cohort",
                "cohort_ids": sorted(int(value) for value in self.cohort_ids),
                "all_cohorts": self.all_cohorts,
                "cohort_table": self.cohort_table,
                "cohort_column": self.cohort_column,
                "subject_column": self.subject_column,
                "schema": self.schema,
                "subject_fingerprint": self.subject_fingerprint,
            }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]

    def describe(self) -> dict[str, object]:
        """Return a JSON-safe description for registries and logs."""
        if self.is_whole_cdm:
            return {"kind": "whole_cdm", "fingerprint": self.fingerprint()}
        return {
            "kind": "cohort",
            "cohort_ids": list(self.cohort_ids),
            "all_cohorts": self.all_cohorts,
            "cohort_table": self.cohort_table,
            "cohort_column": self.cohort_column,
            "subject_column": self.subject_column,
            "schema": self.schema,
            "fingerprint": self.fingerprint(),
        }

    def subjects(self, backend: IbisBackendLike):
        """Return a lazy relation of ``subject_id`` covering this scope.

        The relation is never materialised here; callers join it into the
        extraction so the filter happens in the database.
        """
        if self.is_whole_cdm:
            raise ValueError("whole_cdm scope has no subject relation; ask the backend for person.")
        if self.cohort_table is not None:
            table = backend.table(self.cohort_table, database=self.schema)
            relation = (
                table.filter(table[self.cohort_column].isin(list(self.cohort_ids)))
                if self.cohort_ids
                else table
            )
            return relation.select(relation[self.subject_column].cast("int64").name("subject_id")).distinct()
        # cohort ids without a table: the caller must supply one.
        raise ValueError("A cohort scope built from cohort_ids alone needs cohort_table to resolve subjects.")


WHOLE_CDM_SCOPE = CohortScope(kind="whole_cdm")


def whole_cdm() -> CohortScope:
    """Return the explicit whole-CDM scope.

    This is the opt-in pipeline. Prefer :func:`cohort_scope` unless the cache
    genuinely must serve unrelated studies, because the result scales with the
    CDM rather than with the study population.
    """
    return WHOLE_CDM_SCOPE


def cohort_scope(
    cohort_ids: int | tuple[int, ...] | list[int],
    *,
    cohort_table: str | None = None,
    cohort_column: str = "cohort_definition_id",
    subject_column: str = "subject_id",
    schema: str | None = None,
) -> CohortScope:
    """Return a scope covering the people in *cohort_ids*.

    This is the default pipeline. Pass ``cohort_table`` (and optionally
    ``schema``) so subjects can be resolved; ``cohort_ids`` alone is accepted
    for callers that join their own membership relation.
    """
    ids = (int(cohort_ids),) if isinstance(cohort_ids, int) else tuple(int(value) for value in cohort_ids)
    if not ids:
        raise ValueError("cohort_scope requires at least one cohort id.")
    return CohortScope(
        kind="cohort",
        cohort_ids=ids,
        all_cohorts=not ids,
        cohort_table=cohort_table,
        cohort_column=cohort_column,
        subject_column=subject_column,
        schema=schema,
    )


def scope_from_cohort_table(
    cohort_table: str,
    *,
    cohort_ids: int | tuple[int, ...] | list[int] | None = None,
    cohort_column: str = "cohort_definition_id",
    subject_column: str = "subject_id",
    schema: str | None = None,
) -> CohortScope:
    """Return a scope resolved from a cohort table.

    ``cohort_ids=None`` means "everyone in the table" — still a cohort scope,
    because the table is a study cohort rather than the whole CDM.
    """
    if cohort_ids is None:
        ids: tuple[int, ...] = ()
    elif isinstance(cohort_ids, int):
        ids = (int(cohort_ids),)
    else:
        ids = tuple(int(value) for value in cohort_ids)

    if not cohort_table:
        raise ValueError("scope_from_cohort_table requires a table name.")
    return CohortScope(
        kind="cohort",
        cohort_ids=ids,
        all_cohorts=not ids,
        cohort_table=cohort_table,
        cohort_column=cohort_column,
        subject_column=subject_column,
        schema=schema,
    )
