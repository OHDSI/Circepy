"""
Feature-aware domain table accessors for the Feature Extraction Framework.

Unlike the cohort-oriented Ibis builders in ``circe.execution.builders`` (which
call ``standardize_output()`` and strip domain-specific columns), these
accessors retain all clinically relevant columns needed for feature extraction:
concept IDs, dates, values, quantities, etc.

Domain metadata is **derived automatically** from the Pydantic ``Criteria``
models and the ``criteria_compat`` column-resolution methods, so extensions
that register a ``Criteria`` subclass get feature extraction support for free.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import ibis.expr.types as ir
    from ..execution.build_context import BuildContext
    from ..cohortdefinition.criteria import Criteria


# ------------------------------------------------------------------
# DomainSpec — lightweight value object
# ------------------------------------------------------------------


@dataclass(frozen=True)
class DomainSpec:
    """Metadata describing an OMOP CDM domain table for feature extraction.

    Instances are derived from ``Criteria`` model introspection via
    ``domain_spec_from_criteria()``.
    """

    table_name: str
    concept_id_column: str
    start_date_column: str
    end_date_column: str
    primary_key_column: str
    value_columns: List[str] = field(default_factory=list)

    @property
    def effective_end_date_column(self) -> str:
        return self.end_date_column or self.start_date_column


# ------------------------------------------------------------------
# Introspection: build DomainSpec from a Criteria instance
# ------------------------------------------------------------------

# Fields on Criteria classes whose *names* correspond directly to CDM table
# columns containing extractable numeric values.
_KNOWN_VALUE_FIELDS = frozenset({
    "value_as_number",
    "value_as_concept",     # value_as_concept_id on the table
    "quantity",
    "days_supply",
    "refills",
    "dose_value",
    "range_low",
    "range_high",
    "drug_exposure_count",
    "condition_occurrence_count",
})


def _infer_value_columns(criteria: "Criteria") -> List[str]:
    """Inspect a Criteria model's Pydantic fields to discover extractable
    value columns on the underlying CDM table.

    Convention: a field typed ``Optional[NumericRange]`` whose snake_case name
    matches a known CDM column is treated as a value column.
    """
    from ..cohortdefinition.core import NumericRange

    value_cols: List[str] = []
    for field_name, field_info in type(criteria).model_fields.items():
        # Check if the field annotation resolves to NumericRange
        annotation = field_info.annotation
        is_numeric = False
        # Handle Optional[NumericRange] → check inner type
        if hasattr(annotation, "__args__"):
            is_numeric = any(
                arg is NumericRange for arg in annotation.__args__
                if arg is not type(None)
            )
        elif annotation is NumericRange:
            is_numeric = True

        if is_numeric and field_name in _KNOWN_VALUE_FIELDS:
            value_cols.append(field_name)

    return value_cols


def domain_spec_from_criteria(criteria: "Criteria") -> DomainSpec:
    """Derive a ``DomainSpec`` from a Criteria model instance.

    Uses the ``criteria_compat`` methods already patched onto every
    ``Criteria`` subclass (``get_concept_id_column``, etc.) plus Pydantic
    field introspection for value columns.
    """
    return DomainSpec(
        table_name=criteria.snake_case_class_name(),
        concept_id_column=criteria.get_concept_id_column(),
        start_date_column=criteria.get_start_date_column(),
        end_date_column=criteria.get_end_date_column(),
        primary_key_column=criteria.get_primary_key_column(),
        value_columns=_infer_value_columns(criteria),
    )


# ------------------------------------------------------------------
# Domain resolution (core + extensions)
# ------------------------------------------------------------------

def _get_criteria_instance(domain: str) -> "Criteria":
    """Resolve a PascalCase domain name to an empty Criteria instance.

    Checks the core ``CRITERIA_TYPE_MAP`` first, then falls back to the
    ``ExtensionRegistry`` for extension domains.
    """
    # Ensure compat methods are patched
    from ..execution.criteria_compat import CRITERIA_TYPE_MAP

    cls = CRITERIA_TYPE_MAP.get(domain)
    if cls is None:
        from ..extensions import get_registry
        cls = get_registry().get_criteria_class(domain)
    if cls is None:
        from ..execution.criteria_compat import CRITERIA_TYPE_MAP
        raise ValueError(
            f"Unknown domain: {domain!r}. "
            f"Available: {sorted(CRITERIA_TYPE_MAP.keys())}"
        )
    return cls()


def get_domain_spec(domain: str) -> DomainSpec:
    """Look up a ``DomainSpec`` by PascalCase domain name.

    Works for both core OMOP CDM domains *and* extension domains that
    have registered a ``Criteria`` subclass.
    """
    criteria = _get_criteria_instance(domain)
    return domain_spec_from_criteria(criteria)


def list_domains() -> List[str]:
    """Return all available domain names (core + extensions)."""
    from ..execution.criteria_compat import CRITERIA_TYPE_MAP
    from ..extensions import get_registry

    core = set(CRITERIA_TYPE_MAP.keys())
    extension = set(get_registry()._criteria_classes.keys())
    return sorted(core | extension)


# ------------------------------------------------------------------
# Feature-aware table accessors
# ------------------------------------------------------------------


def get_domain_events(
    domain: str,
    ctx: "BuildContext",
    *,
    codeset_id: Optional[int] = None,
    columns: Optional[List[str]] = None,
) -> "ir.Table":
    """Return raw domain events as an Ibis table with clinical columns retained.

    Unlike the cohort builders (which call ``standardize_output()``), this
    accessor keeps ``concept_id``, ``value_as_number``, dates, and other
    clinically relevant columns so they can be used in feature aggregations.

    Works automatically for **any** domain that has a registered ``Criteria``
    class (including extensions).

    Parameters
    ----------
    domain : str
        PascalCase OMOP domain name (e.g. ``"ConditionOccurrence"``).
    ctx : BuildContext
        The Ibis build context (connection, schemas, compiled codesets).
    codeset_id : int, optional
        If provided, filter to rows matching this concept set.
    columns : list[str], optional
        Explicit list of columns to select. If ``None``, a sensible default
        set is chosen (person_id, concept_id, dates, value columns).

    Returns
    -------
    ir.Table
        An Ibis table expression with the requested columns.
    """
    from ..execution.builders.common import apply_codeset_filter

    spec = get_domain_spec(domain)
    table = ctx.table(spec.table_name)

    if codeset_id is not None:
        table = apply_codeset_filter(
            table, spec.concept_id_column, codeset_id, ctx
        )

    if columns is not None:
        available = [c for c in columns if c in table.columns]
        return table.select(available)

    return _select_default_columns(table, spec)


def _select_default_columns(table: "ir.Table", spec: DomainSpec) -> "ir.Table":
    """Select a sensible default set of columns for feature extraction."""
    keep = ["person_id", spec.concept_id_column, spec.start_date_column]

    if spec.end_date_column and spec.end_date_column != spec.start_date_column:
        keep.append(spec.end_date_column)

    if spec.primary_key_column and spec.primary_key_column != "person_id":
        keep.append(spec.primary_key_column)

    if "visit_occurrence_id" not in keep:
        keep.append("visit_occurrence_id")

    keep.extend(spec.value_columns)

    # Deduplicate while preserving order, then filter to columns that exist
    available = [c for c in dict.fromkeys(keep) if c in table.columns]
    return table.select(available)


# ------------------------------------------------------------------
# Temporal window filtering
# ------------------------------------------------------------------


def apply_temporal_window(
    events: "ir.Table",
    cohort: "ir.Table",
    spec: DomainSpec,
    window: tuple[int, int],
    *,
    cohort_person_col: str = "subject_id",
    cohort_date_col: str = "cohort_start_date",
) -> "ir.Table":
    """Join domain events to a cohort table and filter by temporal window.

    Parameters
    ----------
    events : ir.Table
        Domain events (from ``get_domain_events``).
    cohort : ir.Table
        Cohort table with at least ``(subject_id, cohort_start_date)``.
    spec : DomainSpec
        The domain specification for column name resolution.
    window : tuple[int, int]
        ``(days_before, days_after)`` relative to the cohort index date.
        ``days_before`` should be negative (e.g. ``-365``).
    cohort_person_col : str
        Person ID column in the cohort table.
    cohort_date_col : str
        Index date column in the cohort table.

    Returns
    -------
    ir.Table
        Joined and filtered table with an added ``time_delta_days`` column.
    """
    import ibis

    days_before, days_after = window
    event_date_col = spec.start_date_column

    joined = events.join(
        cohort,
        events.person_id == cohort[cohort_person_col],
    )

    event_date = joined[event_date_col].cast("timestamp")
    index_date = joined[cohort_date_col].cast("timestamp")

    delta_seconds = event_date.epoch_seconds() - index_date.epoch_seconds()
    delta_days = (delta_seconds / 86400).cast("int64")

    joined = joined.mutate(time_delta_days=delta_days)

    joined = joined.filter(
        (joined.time_delta_days >= ibis.literal(days_before))
        & (joined.time_delta_days <= ibis.literal(days_after))
    )

    return joined
