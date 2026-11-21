"""Feature specifications for the era cache.

An era cache stores the *events* that a feature selects, not the value a feature
takes in a particular cohort.  Three storage classes exist:

``presence``
    The event occurred (diagnosis, procedure, drug, visit, ...).

``categorical``
    The event carries an observed OMOP concept as its result
    (``value_as_concept_id``), for example ``Measurement.value_as_concept_id``.

``continuous``
    The event carries an observed number as its result (``value_as_number``),
    optionally filtered against a numeric predicate such as
    ``value > range_high`` ("above normal range").

A numeric predicate is derived at read time; it is never stored.  The cache
stores the raw value, unit and reference range so different value conditions can
be answered from the same rows.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from ..vocabulary.concept import ConceptSetExpression

__all__ = [
    "ContinuousPredicate",
    "EraFeatureSpec",
    "FeatureClass",
    "SourceTable",
]

FeatureClass = Literal["presence", "categorical", "continuous"]

SourceTable = Literal[
    "condition_occurrence",
    "condition_era",
    "drug_exposure",
    "drug_era",
    "dose_era",
    "procedure_occurrence",
    "device_exposure",
    "measurement",
    "observation",
    "visit_occurrence",
    "visit_detail",
    "specimen",
    "death",
]

# Columns that identify the event and its subject, per source table.
_TABLE_KEYS: dict[str, tuple[str, str]] = {
    "condition_occurrence": ("condition_occurrence_id", "condition_start_date"),
    "condition_era": ("condition_era_id", "condition_era_start_date"),
    "drug_exposure": ("drug_exposure_id", "drug_exposure_start_date"),
    "drug_era": ("drug_era_id", "drug_era_start_date"),
    "dose_era": ("dose_era_id", "dose_era_start_date"),
    "procedure_occurrence": ("procedure_occurrence_id", "procedure_date"),
    "device_exposure": ("device_exposure_id", "device_exposure_start_date"),
    "measurement": ("measurement_id", "measurement_date"),
    "observation": ("observation_id", "observation_date"),
    "visit_occurrence": ("visit_occurrence_id", "visit_start_date"),
    "visit_detail": ("visit_detail_id", "visit_detail_start_date"),
    "specimen": ("specimen_id", "specimen_date"),
    "death": ("person_id", "death_date"),
}

# Tables whose concept column is not the table name + "_concept_id".
_CONCEPT_COLUMNS: dict[str, str] = {
    "condition_occurrence": "condition_concept_id",
    "condition_era": "condition_concept_id",
    "drug_exposure": "drug_concept_id",
    "drug_era": "drug_concept_id",
    "dose_era": "drug_concept_id",
    "procedure_occurrence": "procedure_concept_id",
    "device_exposure": "device_concept_id",
    "measurement": "measurement_concept_id",
    "observation": "observation_concept_id",
    "visit_occurrence": "visit_concept_id",
    "visit_detail": "visit_detail_concept_id",
    "specimen": "specimen_concept_id",
    "death": "cause_concept_id",
}

_SOURCE_CONCEPT_COLUMNS: dict[str, str] = {
    "condition_occurrence": "condition_source_concept_id",
    "condition_era": "condition_concept_id",
    "drug_exposure": "drug_source_concept_id",
    "drug_era": "drug_concept_id",
    "dose_era": "drug_concept_id",
    "procedure_occurrence": "procedure_source_concept_id",
    "device_exposure": "device_source_concept_id",
    "measurement": "measurement_source_concept_id",
    "observation": "observation_source_concept_id",
    "visit_occurrence": "visit_source_concept_id",
    "visit_detail": "visit_detail_source_concept_id",
    "specimen": "specimen_source_concept_id",
    "death": "",
}

# Which tables have a real end date column to use as the era end.
_END_COLUMNS: dict[str, str | None] = {
    "condition_occurrence": "condition_end_date",
    "condition_era": "condition_era_end_date",
    "drug_exposure": "drug_exposure_end_date",
    "drug_era": "drug_era_end_date",
    "dose_era": "dose_era_end_date",
    "procedure_occurrence": None,
    "device_exposure": "device_exposure_end_date",
    "measurement": None,
    "observation": None,
    "visit_occurrence": "visit_end_date",
    "visit_detail": "visit_detail_end_date",
    "specimen": None,
    "death": None,
}


class ContinuousPredicate(BaseModel):
    """A numeric predicate over an observed value.

    The predicate is evaluated at read time; only the raw values are cached.
    ``reference="range"`` compares ``value`` against ``range_low``/``range_high``;
    ``reference="value"`` compares against an explicit ``threshold``.
    """

    model_config = ConfigDict(frozen=True)

    op: Literal["lt", "lte", "gt", "gte", "between", "equals", "neq"]
    reference: Literal["range", "value"] = "value"
    threshold: float | None = None
    upper: float | None = None

    @model_validator(mode="after")
    def _validate(self) -> ContinuousPredicate:
        if self.reference == "value" and self.threshold is None:
            raise ValueError("A value-referenced predicate requires a threshold.")
        if self.op == "between":
            if self.reference != "value":
                raise ValueError("A 'between' predicate must use reference='value'.")
            if self.threshold is None or self.upper is None:
                raise ValueError("A 'between' predicate requires threshold and upper.")
            if self.threshold > self.upper:
                raise ValueError("between: threshold must be <= upper.")
        return self

    def canonical_payload(self) -> dict[str, object]:
        return {
            "op": self.op,
            "reference": self.reference,
            "threshold": self.threshold,
            "upper": self.upper,
        }

    def describe(self) -> str:
        if self.reference == "range":
            return f"normal_range:{self.op}"
        if self.op == "between":
            return f"value:{self.threshold}..{self.upper}"
        return f"value:{self.op}:{self.threshold}"


class EraFeatureSpec(BaseModel):
    """One cached feature family and the events it selects."""

    model_config = ConfigDict(frozen=True)

    name: str
    source_table: SourceTable
    concept_set: ConceptSetExpression | None = None
    concept_ids: tuple[int, ...] = ()
    include_descendants: bool = False
    include_source_concepts: bool = False
    feature_class: FeatureClass = "presence"

    # categorical: restrict to (or derive from) an observed value concept
    value_concept_ids: tuple[int, ...] = ()
    # continuous: never stored, only used to describe/validate the read predicate
    predicates: tuple[ContinuousPredicate, ...] = ()
    unit_concept_ids: tuple[int, ...] = ()

    # record-level filters
    type_concept_ids: tuple[int, ...] = ()
    status_concept_ids: tuple[int, ...] = ()

    tags: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _validate(self) -> EraFeatureSpec:
        if not self.concept_set and not self.concept_ids:
            raise ValueError(f"Feature {self.name!r} needs a concept_set or concept_ids.")
        has_value_columns = self.source_table in {"measurement", "observation"}
        if self.feature_class in {"categorical", "continuous"} and not has_value_columns:
            raise ValueError(
                f"Feature {self.name!r}: {self.feature_class} features need a source "
                "table with value columns (measurement or observation)."
            )
        if self.feature_class == "categorical" and not self.value_concept_ids:
            raise ValueError(f"Feature {self.name!r}: categorical features need value_concept_ids.")
        if self.feature_class == "continuous" and self.value_concept_ids:
            raise ValueError(f"Feature {self.name!r}: continuous features cannot restrict value concepts.")
        if self.feature_class == "presence" and self.predicates:
            raise ValueError(f"Feature {self.name!r}: presence features cannot carry numeric predicates.")
        return self

    # -- source mapping ----------------------------------------------------
    @property
    def event_id_column(self) -> str:
        return _TABLE_KEYS[self.source_table][0]

    @property
    def start_date_column(self) -> str:
        return _TABLE_KEYS[self.source_table][1]

    @property
    def end_date_column(self) -> str | None:
        return _END_COLUMNS[self.source_table]

    @property
    def concept_column(self) -> str:
        return _CONCEPT_COLUMNS[self.source_table]

    @property
    def source_concept_column(self) -> str | None:
        if self.source_table == "death":
            return None
        return _SOURCE_CONCEPT_COLUMNS[self.source_table]

    # -- identity ----------------------------------------------------------
    def canonical_payload(self) -> dict[str, object]:
        """The event selection.  Deliberately excludes name, tags and predicates."""
        return {
            "source_table": self.source_table,
            "concept_set": self._concept_set_payload(),
            "include_descendants": self.include_descendants,
            "include_source_concepts": self.include_source_concepts,
            "feature_class": self.feature_class,
            "value_concept_ids": sorted(int(item) for item in self.value_concept_ids),
            "unit_concept_ids": sorted(int(item) for item in self.unit_concept_ids),
            "type_concept_ids": sorted(int(item) for item in self.type_concept_ids),
            "status_concept_ids": sorted(int(item) for item in self.status_concept_ids),
        }

    def _concept_set_payload(self) -> list[dict[str, object]]:
        if self.concept_set is not None:
            items: list[dict[str, object]] = []
            if self.concept_set.concept is not None and self.concept_set.concept.concept_id is not None:
                items.append(
                    {
                        "concept_id": int(self.concept_set.concept.concept_id),
                        "excluded": bool(self.concept_set.is_excluded),
                        "descendants": bool(self.concept_set.include_descendants),
                        "mapped": bool(self.concept_set.include_mapped),
                    }
                )
            for item in self.concept_set.items or []:
                if item is None or item.concept is None or item.concept.concept_id is None:
                    continue
                items.append(
                    {
                        "concept_id": int(item.concept.concept_id),
                        "excluded": bool(item.is_excluded),
                        "descendants": bool(item.include_descendants),
                        "mapped": bool(item.include_mapped),
                    }
                )
            return sorted(
                items,
                key=lambda entry: (
                    entry["concept_id"],
                    entry["excluded"],
                    entry["descendants"],
                    entry["mapped"],
                ),
            )
        return [
            {
                "concept_id": int(concept_id),
                "excluded": False,
                "descendants": bool(self.include_descendants),
                "mapped": False,
            }
            for concept_id in sorted({int(item) for item in self.concept_ids})
        ]
