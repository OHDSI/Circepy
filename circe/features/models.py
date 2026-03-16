"""
Pydantic models for the Feature Extraction Framework.

Defines the hierarchy of feature definitions, deterministic hashing for
caching/deduplication, and container types for feature sets.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

from pydantic import ConfigDict, Field, model_validator


class FeatureType(str, Enum):
    """Classification of feature extraction strategies."""

    BINARY = "binary"
    """Presence/absence of events matching criteria in a window."""

    COUNT = "count"
    """Number of matching events in a window."""

    VALUE = "value"
    """Numeric value extracted from a domain column (e.g. value_as_number)."""

    COMPOSITE = "composite"
    """Weighted sum of multiple component features (e.g. Charlson index)."""

    BULK_DOMAIN = "bulk_domain"
    """All concepts within a domain, one feature per concept_id."""

    DEMOGRAPHICS = "demographics"
    """Patient-level attributes from the person table (age, gender, race, etc.)."""

    VISIT_COUNT = "visit_count"
    """Count of visits in a time window, optionally filtered by visit type."""

    ERA_OVERLAP = "era_overlap"
    """Condition/drug eras overlapping the index window (one per concept)."""


class Aggregation(str, Enum):
    """Aggregation functions for continuous features."""

    LATEST = "latest"
    """Most recent value by event date."""

    FIRST = "first"
    """Earliest value by event date."""

    MIN = "min"
    MAX = "max"
    AVG = "avg"
    SUM = "sum"
    COUNT = "count"
    MEDIAN = "median"


class FeatureDefinition:
    """Base class for all feature definitions.

    Every feature has a deterministic hash derived from its semantic properties.
    Two features with identical definitions will produce the same hash, enabling
    cache lookups to skip redundant computation.

    This is intentionally *not* a Pydantic model — feature definitions are
    lightweight Python objects used to drive the extraction engine, not CIRCE
    JSON entities.
    """

    def __init__(
        self,
        name: str,
        feature_type: FeatureType,
        *,
        description: str = "",
        tags: Optional[Dict[str, str]] = None,
    ):
        self.name = name
        self.feature_type = feature_type
        self.description = description
        self.tags = tags or {}

    # ------------------------------------------------------------------
    # Deterministic hashing
    # ------------------------------------------------------------------

    def _hash_payload(self) -> dict:
        """Return the dictionary of properties that determine this feature's
        identity. Subclasses must override this to include their specific
        fields.
        """
        return {
            "type": self.feature_type.value,
            "name": self.name,
        }

    @property
    def feature_hash(self) -> str:
        """Deterministic SHA-256 hex digest of the feature definition.

        The hash is computed from a canonical JSON serialization (sorted keys,
        no whitespace) of ``_hash_payload()``.  This means two independently
        constructed ``FeatureDefinition`` objects with the same semantic
        content will always produce the same hash.
        """
        payload = self._hash_payload()
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} hash={self.feature_hash[:12]}>"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FeatureDefinition):
            return NotImplemented
        return self.feature_hash == other.feature_hash

    def __hash__(self) -> int:
        return hash(self.feature_hash)

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary (for storage in feature_definition table)."""
        return {
            "feature_hash": self.feature_hash,
            "feature_name": self.name,
            "feature_type": self.feature_type.value,
            "description": self.description,
            "tags": self.tags,
            "definition": self._hash_payload(),
        }


# ----------------------------------------------------------------------
# Concrete feature types
# ----------------------------------------------------------------------


class BinaryFeature(FeatureDefinition):
    """Presence/absence of events matching a CIRCE criteria group.

    Parameters
    ----------
    name : str
        Human-readable feature name.
    codeset_id : int
        Concept set ID to match against.
    domain : str
        OMOP domain name (e.g. ``"ConditionOccurrence"``).
    window : tuple[int, int]
        ``(days_before, days_after)`` relative to the index date.
        Negative ``days_before`` means *before* the index date.
        Example: ``(-365, 0)`` = 1 year prior through index date.
    criteria_json : dict | None
        Optional raw CIRCE ``CriteriaGroup`` JSON for complex logic.
    """

    def __init__(
        self,
        name: str,
        codeset_id: int,
        domain: str,
        window: Tuple[int, int] = (-99999, 0),
        *,
        criteria_json: Optional[dict] = None,
        description: str = "",
        tags: Optional[Dict[str, str]] = None,
    ):
        super().__init__(name, FeatureType.BINARY, description=description, tags=tags)
        self.codeset_id = codeset_id
        self.domain = domain
        self.window = window
        self.criteria_json = criteria_json

    def _hash_payload(self) -> dict:
        payload = {
            "type": self.feature_type.value,
            "domain": self.domain,
            "codeset_id": self.codeset_id,
            "window": list(self.window),
        }
        if self.criteria_json:
            payload["criteria"] = self.criteria_json
        return payload


class AncestorBinaryFeature(BinaryFeature):
    """Binary feature that matches via concept_ancestor rollup.

    Instead of requiring a pre-compiled codeset, this feature type joins
    the domain table to ``concept_ancestor`` at extraction time to find
    all descendant concepts of the given ancestor concept IDs.

    Used by the Charlson Index preset to avoid requiring users to register
    codesets for standard comorbidity concepts.

    Parameters
    ----------
    name : str
        Human-readable feature name.
    ancestor_concept_ids : list[int]
        OMOP ancestor concept IDs to expand via ``concept_ancestor``.
    domain : str
        OMOP domain name (e.g. ``"ConditionEra"``).
    window : tuple[int, int]
        ``(days_before, days_after)`` relative to the index date.
    """

    def __init__(
        self,
        name: str,
        ancestor_concept_ids: List[int],
        domain: str = "ConditionOccurrence",
        window: Tuple[int, int] = (-99999, 0),
        *,
        description: str = "",
        tags: Optional[Dict[str, str]] = None,
    ):
        # codeset_id=-1 signals that ancestor rollup is used instead
        super().__init__(
            name, codeset_id=-1, domain=domain, window=window,
            description=description, tags=tags,
        )
        self.ancestor_concept_ids = sorted(ancestor_concept_ids)

    def _hash_payload(self) -> dict:
        return {
            "type": "ancestor_binary",
            "domain": self.domain,
            "ancestor_concept_ids": self.ancestor_concept_ids,
            "window": list(self.window),
        }


class ValueFeature(FeatureDefinition):
    """Extract a numeric value from a domain column.

    Parameters
    ----------
    name : str
        Human-readable feature name.
    codeset_id : int
        Concept set ID to match against.
    domain : str
        OMOP domain name (e.g. ``"Measurement"``).
    value_column : str
        Column to extract (e.g. ``"value_as_number"``).
    aggregation : Aggregation
        How to reduce multiple values to a single scalar.
    window : tuple[int, int]
        ``(days_before, days_after)`` relative to index date.
    """

    def __init__(
        self,
        name: str,
        codeset_id: int,
        domain: str,
        value_column: str = "value_as_number",
        aggregation: Aggregation = Aggregation.LATEST,
        window: Tuple[int, int] = (-99999, 0),
        *,
        description: str = "",
        tags: Optional[Dict[str, str]] = None,
    ):
        super().__init__(name, FeatureType.VALUE, description=description, tags=tags)
        self.codeset_id = codeset_id
        self.domain = domain
        self.value_column = value_column
        self.aggregation = aggregation
        self.window = window

    def _hash_payload(self) -> dict:
        return {
            "type": self.feature_type.value,
            "domain": self.domain,
            "codeset_id": self.codeset_id,
            "value_column": self.value_column,
            "aggregation": self.aggregation.value,
            "window": list(self.window),
        }


class CompositeFeature(FeatureDefinition):
    """Weighted sum of multiple component features (e.g. Charlson Index).

    Parameters
    ----------
    name : str
        Human-readable name (e.g. "Charlson Comorbidity Index").
    components : list[tuple[FeatureDefinition, float]]
        List of ``(feature, weight)`` pairs.  The composite score is
        ``sum(weight * feature_value for feature, weight in components)``.
    """

    def __init__(
        self,
        name: str,
        components: List[Tuple[FeatureDefinition, float]],
        *,
        description: str = "",
        tags: Optional[Dict[str, str]] = None,
    ):
        super().__init__(name, FeatureType.COMPOSITE, description=description, tags=tags)
        self.components = components

    @property
    def component_hashes(self) -> List[Tuple[str, float]]:
        """Return ``(feature_hash, weight)`` pairs for all components."""
        return [(f.feature_hash, w) for f, w in self.components]

    def _hash_payload(self) -> dict:
        return {
            "type": self.feature_type.value,
            "components": [
                {"hash": f.feature_hash, "weight": w}
                for f, w in self.components
            ],
        }


class BulkDomainFeature(FeatureDefinition):
    """Extract one binary feature per concept_id within a domain.

    This produces *many* features (one per distinct concept in the data).
    Used for large-scale propensity score models.

    Parameters
    ----------
    name : str
        Prefix name (e.g. ``"Conditions_365d"``).
    domain : str
        OMOP domain name (e.g. ``"ConditionOccurrence"``).
    window : tuple[int, int]
        ``(days_before, days_after)`` relative to index date.
    use_ancestors : bool
        If True, roll up to ancestor concepts for aggregation.
    min_cell_count : int
        Minimum number of subjects with the concept to include it.
    """

    def __init__(
        self,
        name: str,
        domain: str,
        window: Tuple[int, int] = (-365, 0),
        *,
        use_ancestors: bool = False,
        min_cell_count: int = 0,
        description: str = "",
        tags: Optional[Dict[str, str]] = None,
    ):
        super().__init__(name, FeatureType.BULK_DOMAIN, description=description, tags=tags)
        self.domain = domain
        self.window = window
        self.use_ancestors = use_ancestors
        self.min_cell_count = min_cell_count

    def _hash_payload(self) -> dict:
        return {
            "type": self.feature_type.value,
            "domain": self.domain,
            "window": list(self.window),
            "use_ancestors": self.use_ancestors,
        }


class VisitCountFeature(FeatureDefinition):
    """Count of visits in a time window, optionally filtered by visit type.

    Parameters
    ----------
    name : str
        Human-readable feature name.
    window : tuple[int, int]
        ``(days_before, days_after)`` relative to index date.
    visit_concept_ids : list[int] | None
        If provided, only count visits matching these visit_concept_id values.
        Common values: 9201 (inpatient), 9202 (outpatient), 9203 (ER).
        If ``None``, count all visits.
    """

    def __init__(
        self,
        name: str = "Visit Count",
        window: Tuple[int, int] = (-365, 0),
        *,
        visit_concept_ids: Optional[List[int]] = None,
        description: str = "",
        tags: Optional[Dict[str, str]] = None,
    ):
        super().__init__(name, FeatureType.VISIT_COUNT, description=description, tags=tags)
        self.window = window
        self.visit_concept_ids = sorted(visit_concept_ids) if visit_concept_ids else None

    def _hash_payload(self) -> dict:
        payload = {
            "type": self.feature_type.value,
            "window": list(self.window),
        }
        if self.visit_concept_ids:
            payload["visit_concept_ids"] = self.visit_concept_ids
        return payload


class EraOverlapFeature(FeatureDefinition):
    """One binary feature per concept whose era overlaps the index window.

    Unlike ``BulkDomainFeature`` (which checks event *start dates* within a
    window), this feature checks whether an **era** (condition_era or
    drug_era) is *active* during the window — i.e. the era's start date is
    before the window end AND its end date is after the window start.

    Parameters
    ----------
    name : str
        Prefix name (e.g. ``"ConditionEra_Overlap"``).
    domain : str
        ``"ConditionEra"`` or ``"DrugEra"``.
    window : tuple[int, int]
        ``(days_before, days_after)`` relative to index date.
    """

    def __init__(
        self,
        name: str = "Era Overlap",
        domain: str = "ConditionEra",
        window: Tuple[int, int] = (-365, 0),
        *,
        description: str = "",
        tags: Optional[Dict[str, str]] = None,
    ):
        super().__init__(name, FeatureType.ERA_OVERLAP, description=description, tags=tags)
        self.domain = domain
        self.window = window

    def _hash_payload(self) -> dict:
        return {
            "type": self.feature_type.value,
            "domain": self.domain,
            "window": list(self.window),
        }


class DemographicsFeature(FeatureDefinition):
    """Patient-level attributes extracted from the ``person`` table.

    Produces multiple sub-features (each with its own hash) for the
    selected demographic attributes.

    Parameters
    ----------
    include_age : bool
        Include age in years at index date.
    include_gender : bool
        Include binary features for each ``gender_concept_id``.
    include_race : bool
        Include binary features for each ``race_concept_id``.
    include_ethnicity : bool
        Include binary features for each ``ethnicity_concept_id``.
    include_index_year : bool
        Include calendar year of index date.
    include_index_month : bool
        Include calendar month of index date.
    """

    def __init__(
        self,
        name: str = "Demographics",
        *,
        include_age: bool = True,
        include_gender: bool = True,
        include_race: bool = False,
        include_ethnicity: bool = False,
        include_index_year: bool = False,
        include_index_month: bool = False,
        description: str = "",
        tags: Optional[Dict[str, str]] = None,
    ):
        super().__init__(name, FeatureType.DEMOGRAPHICS, description=description, tags=tags)
        self.include_age = include_age
        self.include_gender = include_gender
        self.include_race = include_race
        self.include_ethnicity = include_ethnicity
        self.include_index_year = include_index_year
        self.include_index_month = include_index_month

    def _hash_payload(self) -> dict:
        return {
            "type": self.feature_type.value,
            "age": self.include_age,
            "gender": self.include_gender,
            "race": self.include_race,
            "ethnicity": self.include_ethnicity,
            "index_year": self.include_index_year,
            "index_month": self.include_index_month,
        }

    def sub_hash(self, attribute: str) -> str:
        """Deterministic hash for a specific demographic sub-feature."""
        payload = {"parent": self.feature_hash, "attribute": attribute}
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ----------------------------------------------------------------------
# Temporal extraction configuration
# ----------------------------------------------------------------------


class TemporalConfig:
    """Configuration for temporal (sequence) extraction.

    Parameters
    ----------
    domains : list[str]
        OMOP domains to include in the timeline (e.g.
        ``["ConditionOccurrence", "DrugExposure", "Measurement"]``).
    window : tuple[int, int]
        ``(days_before, days_after)`` relative to index date.
    include_values : bool
        If True, include ``value_as_number`` for measurement/observation
        domains.
    """

    def __init__(
        self,
        domains: List[str],
        window: Tuple[int, int] = (-365, 0),
        *,
        include_values: bool = True,
    ):
        self.domains = sorted(domains)
        self.window = window
        self.include_values = include_values

    @property
    def cache_key(self) -> str:
        """Deterministic cache key for this temporal extraction."""
        payload = {
            "domains": self.domains,
            "window": list(self.window),
            "include_values": self.include_values,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        return (
            f"<TemporalConfig domains={self.domains} "
            f"window={self.window} key={self.cache_key[:12]}>"
        )


# ----------------------------------------------------------------------
# Feature set container
# ----------------------------------------------------------------------


class FeatureSet:
    """A named collection of feature definitions to extract together.

    Parameters
    ----------
    name : str
        Human-readable name for this feature set.
    features : list[FeatureDefinition]
        The features to extract.
    temporal : TemporalConfig | None
        Optional temporal sequence extraction config.
    """

    def __init__(
        self,
        name: str,
        features: Optional[List[FeatureDefinition]] = None,
        *,
        temporal: Optional[TemporalConfig] = None,
        description: str = "",
    ):
        self.name = name
        self.features = features or []
        self.temporal = temporal
        self.description = description

    def add(self, feature: FeatureDefinition) -> "FeatureSet":
        """Add a feature definition. Returns self for chaining."""
        self.features.append(feature)
        return self

    @property
    def feature_hashes(self) -> List[str]:
        """All unique feature hashes in this set."""
        return list(dict.fromkeys(f.feature_hash for f in self.features))

    @property
    def features_by_type(self) -> Dict[FeatureType, List[FeatureDefinition]]:
        """Group features by their type for batched extraction."""
        result: Dict[FeatureType, List[FeatureDefinition]] = {}
        for f in self.features:
            result.setdefault(f.feature_type, []).append(f)
        return result

    def __repr__(self) -> str:
        return (
            f"<FeatureSet name={self.name!r} "
            f"features={len(self.features)} "
            f"temporal={'yes' if self.temporal else 'no'}>"
        )

    def __len__(self) -> int:
        return len(self.features)

    def __iter__(self):
        return iter(self.features)
