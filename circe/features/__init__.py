"""
Feature Extraction Framework for OMOP CDM.

This module provides models, builders, and extractors for defining and computing
patient-level features from OMOP CDM data using Apache Ibis.
"""

from circe.features.models import (
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

from circe.features.domain_tables import (
    DomainSpec,
    apply_temporal_window,
    domain_spec_from_criteria,
    get_domain_events,
    get_domain_spec,
    list_domains,
)

from circe.features.extractor import (
    FeatureExtractor,
    FeatureResult,
)

from circe.features.builder import (
    FeatureSetBuilder,
)

from circe.features.aggregation import (
    table_one,
)

__all__ = [
    "Aggregation",
    "BinaryFeature",
    "BulkDomainFeature",
    "CompositeFeature",
    "DomainSpec",
    "FeatureDefinition",
    "FeatureExtractor",
    "FeatureResult",
    "FeatureSet",
    "FeatureSetBuilder",
    "FeatureType",
    "TemporalConfig",
    "ValueFeature",
    "apply_temporal_window",
    "domain_spec_from_criteria",
    "get_domain_events",
    "get_domain_spec",
    "list_domains",
    "table_one",
]
