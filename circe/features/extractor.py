"""
Feature Extraction Engine.

Orchestrates the extraction of scalar features and temporal sequences
from OMOP CDM data using the domain table accessors and feature definitions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union

import ibis
import ibis.expr.types as ir

from .domain_tables import (
    DomainSpec,
    apply_temporal_window,
    get_domain_events,
    get_domain_spec,
)
from .models import (
    Aggregation,
    BinaryFeature,
    BulkDomainFeature,
    CompositeFeature,
    FeatureDefinition,
    FeatureSet,
    FeatureType,
    TemporalConfig,
    ValueFeature,
)

if TYPE_CHECKING:
    from ..execution.build_context import BuildContext


class FeatureExtractor:
    """Extracts features from OMOP CDM data for a cohort.

    Parameters
    ----------
    ctx : BuildContext
        Ibis build context (connection, schemas, compiled codesets).
    cohort : ir.Table
        Cohort table with at least ``(subject_id, cohort_start_date)`` columns.
    cohort_person_col : str
        Person ID column name in the cohort table.
    cohort_date_col : str
        Index date column name in the cohort table.

    Example
    -------
    ::

        extractor = FeatureExtractor(ctx, cohort_table)
        results = extractor.extract(feature_set)
        df = results.to_pandas()
    """

    def __init__(
        self,
        ctx: "BuildContext",
        cohort: ir.Table,
        *,
        cohort_person_col: str = "subject_id",
        cohort_date_col: str = "cohort_start_date",
    ):
        self.ctx = ctx
        self.cohort = cohort
        self.cohort_person_col = cohort_person_col
        self.cohort_date_col = cohort_date_col

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, feature_set: FeatureSet) -> "FeatureResult":
        """Extract all features in a ``FeatureSet`` and return results.

        Scalar features are computed individually and unioned into a single
        long-format table. Temporal sequences (if configured) are extracted
        separately.
        """
        scalar_tables: list[ir.Table] = []

        for feature in feature_set:
            expr = self._extract_single(feature)
            if expr is not None:
                scalar_tables.append(expr)

        scalar = _union_all(scalar_tables) if scalar_tables else None

        temporal = None
        if feature_set.temporal is not None:
            temporal = self.extract_sequences(feature_set.temporal)

        return FeatureResult(scalar=scalar, temporal=temporal)

    def extract_single(self, feature: FeatureDefinition) -> ir.Table:
        """Extract a single feature, returning a table of
        ``(subject_id, index_date, feature_hash, feature_value)``.
        """
        result = self._extract_single(feature)
        if result is None:
            raise ValueError(f"Unsupported feature type: {feature.feature_type}")
        return result

    def extract_sequences(self, config: TemporalConfig) -> ir.Table:
        """Extract temporal event sequences for deep learning.

        Returns a table of
        ``(subject_id, time_delta_days, concept_id, domain, value)``
        sorted by ``(subject_id, time_delta_days)``.
        """
        domain_tables: list[ir.Table] = []

        for domain_name in config.domains:
            spec = get_domain_spec(domain_name)
            events = get_domain_events(domain_name, self.ctx)

            # Normalize to a common schema before union
            windowed = apply_temporal_window(
                events,
                self.cohort,
                spec,
                config.window,
                cohort_person_col=self.cohort_person_col,
                cohort_date_col=self.cohort_date_col,
            )

            # Build the normalized columns
            cols = {
                "subject_id": windowed[self.cohort_person_col],
                "time_delta_days": windowed.time_delta_days,
                "concept_id": windowed[spec.concept_id_column],
                "domain": ibis.literal(domain_name),
            }

            # Add value column if available and requested
            if config.include_values and spec.value_columns:
                first_value_col = spec.value_columns[0]
                if first_value_col in windowed.columns:
                    cols["value"] = windowed[first_value_col].cast("float64")
                else:
                    cols["value"] = ibis.null().cast("float64")
            else:
                cols["value"] = ibis.null().cast("float64")

            normalized = windowed.select(**cols)
            domain_tables.append(normalized)

        if not domain_tables:
            raise ValueError("No domains specified in TemporalConfig")

        result = _union_all(domain_tables)
        return result.order_by(["subject_id", "time_delta_days"])

    # ------------------------------------------------------------------
    # Internal dispatch
    # ------------------------------------------------------------------

    def _extract_single(self, feature: FeatureDefinition) -> Optional[ir.Table]:
        """Dispatch to the appropriate extraction method."""
        if isinstance(feature, BinaryFeature):
            return self._extract_binary(feature)
        elif isinstance(feature, ValueFeature):
            return self._extract_value(feature)
        elif isinstance(feature, CompositeFeature):
            return self._extract_composite(feature)
        elif isinstance(feature, BulkDomainFeature):
            return self._extract_bulk(feature)
        return None

    def _extract_binary(self, feature: BinaryFeature) -> ir.Table:
        """Extract a binary (0/1) feature."""
        spec = get_domain_spec(feature.domain)
        events = get_domain_events(
            feature.domain, self.ctx, codeset_id=feature.codeset_id
        )

        windowed = apply_temporal_window(
            events, self.cohort, spec, feature.window,
            cohort_person_col=self.cohort_person_col,
            cohort_date_col=self.cohort_date_col,
        )

        # Subjects who have at least one matching event → 1
        has_event = (
            windowed
            .select(
                subject_id=windowed[self.cohort_person_col],
                index_date=windowed[self.cohort_date_col],
            )
            .distinct()
            .mutate(feature_value=ibis.literal(1.0))
        )

        # Left join back to full cohort to get 0 for non-matches
        cohort_base = self.cohort.select(
            subject_id=self.cohort[self.cohort_person_col],
            index_date=self.cohort[self.cohort_date_col],
        )

        result = cohort_base.left_join(
            has_event,
            (cohort_base.subject_id == has_event.subject_id)
            & (cohort_base.index_date == has_event.index_date),
        ).select(
            subject_id=cohort_base.subject_id,
            index_date=cohort_base.index_date,
            feature_value=has_event.feature_value.fill_null(0.0),
        )

        return result.mutate(
            feature_hash=ibis.literal(feature.feature_hash),
        )

    def _extract_value(self, feature: ValueFeature) -> ir.Table:
        """Extract a continuous value feature with aggregation."""
        spec = get_domain_spec(feature.domain)
        events = get_domain_events(
            feature.domain, self.ctx, codeset_id=feature.codeset_id
        )

        windowed = apply_temporal_window(
            events, self.cohort, spec, feature.window,
            cohort_person_col=self.cohort_person_col,
            cohort_date_col=self.cohort_date_col,
        )

        # Ensure the value column exists
        value_col = feature.value_column
        if value_col not in windowed.columns:
            raise ValueError(
                f"Column {value_col!r} not found in {feature.domain} table. "
                f"Available: {windowed.columns}"
            )

        subject = windowed[self.cohort_person_col]
        index_date = windowed[self.cohort_date_col]
        value = windowed[value_col].cast("float64")

        agg_expr = self._apply_aggregation(
            windowed, subject, index_date, value, feature.aggregation, spec
        )

        return agg_expr.mutate(
            feature_hash=ibis.literal(feature.feature_hash),
        )

    def _apply_aggregation(
        self,
        table: ir.Table,
        subject_col: ir.Column,
        index_date_col: ir.Column,
        value_col: ir.Column,
        aggregation: Aggregation,
        spec: DomainSpec,
    ) -> ir.Table:
        """Apply an aggregation function to grouped events."""
        grouped = table.group_by(
            subject_id=subject_col,
            index_date=index_date_col,
        )

        if aggregation == Aggregation.COUNT:
            return grouped.agg(feature_value=value_col.count().cast("float64"))
        elif aggregation == Aggregation.AVG:
            return grouped.agg(feature_value=value_col.mean().cast("float64"))
        elif aggregation == Aggregation.MIN:
            return grouped.agg(feature_value=value_col.min().cast("float64"))
        elif aggregation == Aggregation.MAX:
            return grouped.agg(feature_value=value_col.max().cast("float64"))
        elif aggregation == Aggregation.SUM:
            return grouped.agg(feature_value=value_col.sum().cast("float64"))
        elif aggregation == Aggregation.MEDIAN:
            return grouped.agg(feature_value=value_col.median().cast("float64"))
        elif aggregation in (Aggregation.LATEST, Aggregation.FIRST):
            return self._apply_ordinal_aggregation(
                table, subject_col, index_date_col, value_col,
                aggregation, spec,
            )
        else:
            raise ValueError(f"Unsupported aggregation: {aggregation}")

    def _apply_ordinal_aggregation(
        self,
        table: ir.Table,
        subject_col: ir.Column,
        index_date_col: ir.Column,
        value_col: ir.Column,
        aggregation: Aggregation,
        spec: DomainSpec,
    ) -> ir.Table:
        """Handle LATEST/FIRST by ordering by event date."""
        ascending = aggregation == Aggregation.FIRST
        event_date = table[spec.start_date_column]

        ranked = table.mutate(
            _rank=ibis.row_number().over(
                ibis.window(
                    group_by=[subject_col, index_date_col],
                    order_by=event_date.asc() if ascending else event_date.desc(),
                )
            )
        )
        first_row = ranked.filter(ranked._rank == 0)
        return first_row.select(
            subject_id=first_row[self.cohort_person_col],
            index_date=first_row[self.cohort_date_col],
            feature_value=value_col.cast("float64"),
        )

    def _extract_composite(self, feature: CompositeFeature) -> ir.Table:
        """Extract a composite feature (weighted sum of components)."""
        component_tables: list[ir.Table] = []

        for component_feature, weight in feature.components:
            comp_result = self._extract_single(component_feature)
            if comp_result is None:
                continue
            # Multiply each component's value by its weight
            weighted = comp_result.select(
                "subject_id",
                "index_date",
                weighted_value=comp_result.feature_value * ibis.literal(weight),
            )
            component_tables.append(weighted)

        if not component_tables:
            raise ValueError("CompositeFeature has no extractable components")

        # Union all weighted components and sum per subject
        all_components = _union_all(component_tables)
        result = all_components.group_by("subject_id", "index_date").agg(
            feature_value=all_components.weighted_value.sum()
        )

        return result.mutate(
            feature_hash=ibis.literal(feature.feature_hash),
        )

    def _extract_bulk(self, feature: BulkDomainFeature) -> ir.Table:
        """Extract one binary feature per concept_id in a domain.

        Returns long-format rows where ``feature_hash`` encodes
        ``domain + window + concept_id``.
        """
        import hashlib
        import json

        spec = get_domain_spec(feature.domain)
        events = get_domain_events(feature.domain, self.ctx)

        windowed = apply_temporal_window(
            events, self.cohort, spec, feature.window,
            cohort_person_col=self.cohort_person_col,
            cohort_date_col=self.cohort_date_col,
        )

        # One row per (subject, index_date, concept_id)
        result = (
            windowed
            .select(
                subject_id=windowed[self.cohort_person_col],
                index_date=windowed[self.cohort_date_col],
                concept_id=windowed[spec.concept_id_column],
            )
            .distinct()
            .mutate(
                feature_value=ibis.literal(1.0),
                # Use the bulk feature hash as the base — concept_id is in the row
                feature_hash=ibis.literal(feature.feature_hash),
            )
        )

        return result


# ------------------------------------------------------------------
# Result container
# ------------------------------------------------------------------


class FeatureResult:
    """Container for extraction results.

    Attributes
    ----------
    scalar : ir.Table | None
        Long-format scalar features:
        ``(subject_id, index_date, feature_hash, feature_value)``.
    temporal : ir.Table | None
        Temporal sequences:
        ``(subject_id, time_delta_days, concept_id, domain, value)``.
    """

    def __init__(
        self,
        scalar: Optional[ir.Table] = None,
        temporal: Optional[ir.Table] = None,
    ):
        self.scalar = scalar
        self.temporal = temporal

    def to_pandas(self) -> dict:
        """Execute and return results as pandas DataFrames."""
        result = {}
        if self.scalar is not None:
            result["scalar"] = self.scalar.execute()
        if self.temporal is not None:
            result["temporal"] = self.temporal.execute()
        return result

    def to_polars(self) -> dict:
        """Execute and return results as Polars DataFrames."""
        import polars as pl

        result = {}
        if self.scalar is not None:
            result["scalar"] = pl.from_pandas(self.scalar.execute())
        if self.temporal is not None:
            result["temporal"] = pl.from_pandas(self.temporal.execute())
        return result

    def __repr__(self) -> str:
        parts = []
        if self.scalar is not None:
            parts.append("scalar=yes")
        if self.temporal is not None:
            parts.append("temporal=yes")
        return f"<FeatureResult {' '.join(parts)}>"


# ------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------


def _union_all(tables: list[ir.Table]) -> ir.Table:
    """Union a list of Ibis tables together."""
    if not tables:
        raise ValueError("Cannot union empty list of tables")
    result = tables[0]
    for t in tables[1:]:
        result = result.union(t, distinct=False)
    return result
