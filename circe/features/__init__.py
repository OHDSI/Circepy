"""
Feature Extraction Framework for OMOP CDM.

This module provides models, builders, and extractors for defining and computing
patient-level features from OMOP CDM data using Apache Ibis.
"""

from circe.features.models import (
    Aggregation,
    AncestorBinaryFeature,
    BinaryFeature,
    BulkDomainFeature,
    CompositeFeature,
    DemographicsFeature,
    EraOverlapFeature,
    FeatureDefinition,
    FeatureSet,
    FeatureType,
    TemporalConfig,
    ValueFeature,
    VisitCountFeature,
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

from circe.features.presets import (
    CHARLSON_COMPONENTS,
    charlson_index,
    default_covariates,
    large_scale_covariates,
)

__all__ = [
    "Aggregation",
    "AncestorBinaryFeature",
    "BinaryFeature",
    "BulkDomainFeature",
    "CHARLSON_COMPONENTS",
    "CompositeFeature",
    "DemographicsFeature",
    "DomainSpec",
    "EraOverlapFeature",
    "FeatureDefinition",
    "FeatureExtractor",
    "FeatureResult",
    "FeatureSet",
    "FeatureSetBuilder",
    "FeatureType",
    "TemporalConfig",
    "ValueFeature",
    "VisitCountFeature",
    "apply_temporal_window",
    "charlson_index",
    "default_covariates",
    "domain_spec_from_criteria",
    "get_domain_events",
    "get_domain_spec",
    "large_scale_covariates",
    "list_domains",
    "table_one",
]
