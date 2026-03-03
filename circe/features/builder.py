"""
Fluent Builder API for creating FeatureSets.
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Union

from .models import (
    Aggregation,
    BinaryFeature,
    BulkDomainFeature,
    CompositeFeature,
    FeatureDefinition,
    FeatureSet,
    TemporalConfig,
    ValueFeature,
)


class FeatureSetBuilder:
    """Fluent API for defining a set of features.

    Example
    -------
    ::

        builder = FeatureSetBuilder("Patient Profile")
        builder.binary("Diabetes", codeset_id=1, window=(-365, 0))
        builder.value("Latest BMI", codeset_id=2, domain="Measurement",
                      value_column="value_as_number", aggregation="latest")
        builder.bulk("ConditionOccurrence", window=(-365, 0))
        builder.temporal(["ConditionOccurrence", "Measurement"], window=(-365, 0))

        feature_set = builder.build()
    """

    def __init__(self, name: str = "Feature Set"):
        self._feature_set = FeatureSet(name=name)

    def binary(
        self,
        name: str,
        codeset_id: int,
        window: Tuple[int, int] = (-365, 0),
        domain: str = "ConditionOccurrence",
    ) -> FeatureSetBuilder:
        """Add a binary (0/1) feature."""
        self._feature_set.add(
            BinaryFeature(
                name=name,
                codeset_id=codeset_id,
                window=window,
                domain=domain,
            )
        )
        return self

    def value(
        self,
        name: str,
        codeset_id: int,
        value_column: str,
        aggregation: Union[Aggregation, str] = Aggregation.LATEST,
        window: Tuple[int, int] = (-365, 0),
        domain: str = "Measurement",
    ) -> FeatureSetBuilder:
        """Add a continuous value feature with aggregation."""
        if isinstance(aggregation, str):
            aggregation = Aggregation(aggregation.lower())

        self._feature_set.add(
            ValueFeature(
                name=name,
                codeset_id=codeset_id,
                domain=domain,
                value_column=value_column,
                aggregation=aggregation,
                window=window,
            )
        )
        return self

    def bulk(
        self,
        domain: str,
        window: Tuple[int, int] = (-365, 0),
        name: Optional[str] = None,
    ) -> FeatureSetBuilder:
        """Add one binary feature per concept_id in a domain."""
        self._feature_set.add(
            BulkDomainFeature(
                name=name or f"Bulk {domain}",
                domain=domain,
                window=window,
            )
        )
        return self

    def composite(
        self,
        name: str,
        components: List[Tuple[FeatureDefinition, float]],
    ) -> FeatureSetBuilder:
        """Add a composite feature (weighted sum of others)."""
        self._feature_set.add(
            CompositeFeature(
                name=name,
                components=components,
            )
        )
        return self

    def temporal(
        self,
        domains: List[str],
        window: Tuple[int, int] = (-365, 0),
        include_values: bool = True,
    ) -> FeatureSetBuilder:
        """Configure temporal sequence extraction."""
        self._feature_set.temporal = TemporalConfig(
            domains=domains,
            window=window,
            include_values=include_values,
        )
        return self

    def build(self) -> FeatureSet:
        """Return the finalized FeatureSet."""
        return self._feature_set
