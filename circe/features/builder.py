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
    DemographicsFeature,
    EraOverlapFeature,
    FeatureDefinition,
    FeatureSet,
    TemporalConfig,
    ValueFeature,
    VisitCountFeature,
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
        builder.demographics(include_age=True, include_gender=True)
        builder.visit_count(window=(-365, 0))
        builder.era_overlap("ConditionEra", window=(-365, 0))
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

    def demographics(
        self,
        *,
        include_age: bool = True,
        include_gender: bool = True,
        include_race: bool = False,
        include_ethnicity: bool = False,
        include_index_year: bool = False,
        include_index_month: bool = False,
        name: str = "Demographics",
    ) -> FeatureSetBuilder:
        """Add demographic features extracted from the person table."""
        self._feature_set.add(
            DemographicsFeature(
                name=name,
                include_age=include_age,
                include_gender=include_gender,
                include_race=include_race,
                include_ethnicity=include_ethnicity,
                include_index_year=include_index_year,
                include_index_month=include_index_month,
            )
        )
        return self

    def visit_count(
        self,
        window: Tuple[int, int] = (-365, 0),
        *,
        visit_concept_ids: Optional[List[int]] = None,
        name: Optional[str] = None,
    ) -> FeatureSetBuilder:
        """Add a visit count feature (count of visits in the window)."""
        self._feature_set.add(
            VisitCountFeature(
                name=name or "Visit Count",
                window=window,
                visit_concept_ids=visit_concept_ids,
            )
        )
        return self

    def era_overlap(
        self,
        domain: str = "ConditionEra",
        window: Tuple[int, int] = (-365, 0),
        *,
        name: Optional[str] = None,
    ) -> FeatureSetBuilder:
        """Add era overlap features (one per concept with an active era)."""
        self._feature_set.add(
            EraOverlapFeature(
                name=name or f"{domain} Overlap",
                domain=domain,
                window=window,
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

