"""
Main cohort definition classes.

This module contains the main CohortExpression class and related components.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

import json
from typing import TYPE_CHECKING, Any, List, Optional, Union

from pydantic import (
    AliasChoices,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from .core import (
    CirceBaseModel,
    CollapseSettings,
    CustomEraStrategy,
    DateOffsetStrategy,
    EndStrategy,
    Period,
    ResultLimit,
)
from .criteria import Criteria, CriteriaGroup, CriteriaType, PrimaryCriteria

if TYPE_CHECKING:
    from ..check.warning import Warning
    from ..vocabulary.concept import ConceptSet
    from .criteria import InclusionRule
else:
    # Import at runtime to avoid circular dependencies
    try:
        from ..check.warning import Warning
    except ImportError:
        pass
    # Import ConceptSet at runtime to avoid circular dependencies
    try:
        from ..vocabulary.concept import ConceptSet
    except ImportError:
        ConceptSet = Any
    # Import InclusionRule at runtime to avoid circular dependencies
    try:
        from .criteria import InclusionRule
    except ImportError:
        InclusionRule = Any


class CohortExpression(CirceBaseModel):
    """Main cohort expression class containing all cohort definition components.

    Java equivalent: org.ohdsi.circe.cohortdefinition.CohortExpression
    """

    concept_sets: List[ConceptSet] = Field(
        default_factory=list,
        validation_alias=AliasChoices("ConceptSets", "conceptSets"),
        serialization_alias="ConceptSets",
    )
    qualified_limit: Optional[ResultLimit] = Field(
        default=None,
        validation_alias=AliasChoices("QualifiedLimit", "qualifiedLimit"),
        serialization_alias="QualifiedLimit",
    )
    additional_criteria: Optional[CriteriaGroup] = Field(
        default=None,
        validation_alias=AliasChoices("AdditionalCriteria", "additionalCriteria"),
        serialization_alias="AdditionalCriteria",
    )
    end_strategy: Optional[
        Union[EndStrategy, DateOffsetStrategy, CustomEraStrategy]
    ] = Field(
        default=None,
        validation_alias=AliasChoices("EndStrategy", "endStrategy"),
        serialization_alias="EndStrategy",
    )
    cdm_version_range: Optional[str] = Field(default=None, alias="cdmVersionRange")
    primary_criteria: Optional[PrimaryCriteria] = Field(
        default=None,
        validation_alias=AliasChoices("PrimaryCriteria", "primaryCriteria"),
        serialization_alias="PrimaryCriteria",
    )
    expression_limit: Optional[ResultLimit] = Field(
        default=None,
        validation_alias=AliasChoices("ExpressionLimit", "expressionLimit"),
        serialization_alias="ExpressionLimit",
    )
    collapse_settings: Optional[CollapseSettings] = Field(
        default=None,
        validation_alias=AliasChoices("CollapseSettings", "collapseSettings"),
        serialization_alias="CollapseSettings",
    )
    title: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("Title", "title"),
        serialization_alias="Title",
    )
    inclusion_rules: List[InclusionRule] = Field(
        default_factory=list,
        validation_alias=AliasChoices("InclusionRules", "inclusionRules"),
        serialization_alias="InclusionRules",
    )
    censor_window: Optional[Period] = Field(
        default=None,
        validation_alias=AliasChoices("CensorWindow", "censorWindow"),
        serialization_alias="CensorWindow",
    )
    censoring_criteria: List[CriteriaType] = Field(
        default_factory=list,
        validation_alias=AliasChoices(
            "CensoringCriteria", "censoring_criteria", "censoringCriteria"
        ),
        serialization_alias="CensoringCriteria",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("inclusion_rules", mode="before")
    @classmethod
    def allow_none_inclusion_rules(cls, v: Any) -> Any:
        """Convert None to empty list for inclusion_rules."""
        if v is None:
            return []
        return v

    @field_validator("concept_sets", mode="before")
    @classmethod
    def allow_none_concept_sets(cls, v: Any) -> Any:
        """Convert None to empty list for concept_sets."""
        if v is None:
            return []
        return v

    @field_validator("end_strategy", mode="before")
    @classmethod
    def deserialize_end_strategy(cls, v: Any) -> Any:
        """Deserialize end strategy from polymorphic JSON format.

        End strategy can come as:
        - {"DateOffset": {"DateField": "StartDate", "Offset": 7}}
        - {"CustomEra": {...}}
        - null/None
        """
        if not v or not isinstance(v, dict):
            return v

        # Check if it has DateOffset key
        if "DateOffset" in v:
            date_offset_data = v["DateOffset"]
            return DateOffsetStrategy.model_validate(date_offset_data, strict=False)

        # Check if it has CustomEra key
        if "CustomEra" in v:
            custom_era_data = v["CustomEra"]
            return CustomEraStrategy.model_validate(custom_era_data, strict=False)

        # Otherwise, try to parse as base EndStrategy
        return EndStrategy.model_validate(v, strict=False)

    @field_validator("censoring_criteria", mode="before")
    @classmethod
    def deserialize_censoring_criteria(cls, v: Any) -> Any:
        """Deserialize censoring criteria from polymorphic JSON format.

        Censoring criteria come as [{"ConditionOccurrence": {...}}, ...]
        and need to be unwrapped and deserialized to Criteria objects.
        """
        if v is None:
            return []
        if not v or not isinstance(v, list):
            return v

        from .criteria import (
            ConditionEra,
            ConditionOccurrence,
            Death,
            DeviceExposure,
            DoseEra,
            DrugEra,
            DrugExposure,
            LocationRegion,
            Measurement,
            Observation,
            ObservationPeriod,
            PayerPlanPeriod,
            ProcedureOccurrence,
            Specimen,
            VisitDetail,
            VisitOccurrence,
        )

        criteria_class_map = {
            "ConditionOccurrence": ConditionOccurrence,
            "DrugExposure": DrugExposure,
            "ProcedureOccurrence": ProcedureOccurrence,
            "VisitOccurrence": VisitOccurrence,
            "Observation": Observation,
            "Measurement": Measurement,
            "DeviceExposure": DeviceExposure,
            "Specimen": Specimen,
            "Death": Death,
            "VisitDetail": VisitDetail,
            "ObservationPeriod": ObservationPeriod,
            "PayerPlanPeriod": PayerPlanPeriod,
            "LocationRegion": LocationRegion,
            "ConditionEra": ConditionEra,
            "DrugEra": DrugEra,
            "DoseEra": DoseEra,
        }

        deserialized = []
        for item in v:
            if not isinstance(item, dict):
                deserialized.append(item)
                continue

            # JSON format: {"ConditionOccurrence": {...}} - unwrap and deserialize
            criteria_type = None
            criteria_data = None
            for key in item.keys():
                if key in criteria_class_map:
                    criteria_type = key
                    criteria_data = item[key]
                    break

            if criteria_type and criteria_data is not None:
                data_copy = dict(criteria_data)
                if "First" not in data_copy and "first" not in data_copy:
                    data_copy["First"] = False
                if (
                    criteria_type == "Measurement"
                    and "MeasurementTypeExclude" not in data_copy
                    and "measurementTypeExclude" not in data_copy
                ):
                    data_copy["MeasurementTypeExclude"] = False
                if (
                    criteria_type == "Observation"
                    and "ObservationTypeExclude" not in data_copy
                    and "observationTypeExclude" not in data_copy
                ):
                    data_copy["ObservationTypeExclude"] = False
                if (
                    criteria_type == "ConditionOccurrence"
                    and "ConditionTypeExclude" not in data_copy
                    and "conditionTypeExclude" not in data_copy
                ):
                    data_copy["ConditionTypeExclude"] = False

                criteria_obj = criteria_class_map[criteria_type].model_validate(
                    data_copy, strict=False
                )
                deserialized.append(criteria_obj)
            else:
                deserialized.append(item)

        return deserialized

    @model_validator(mode="before")
    @classmethod
    def normalize_before_validation(cls, data: Any) -> Any:
        """Normalize data before validation.

        Handles empty objects and other normalization needs.
        """
        if isinstance(data, dict):
            # No longer dropping cdmVersionRange string since we now expect Optional[str]
            if "censorWindow" in data and data["censorWindow"] == {}:
                data = dict(data)
                data.pop("censorWindow")

        return data

    def add_concept_set(self, concept_set: ConceptSet) -> None:
        """
        Adds a concept set
        """
        if not isinstance(concept_set, ConceptSet):
            raise TypeError("Expected ConceptSet instance")
        self.concept_sets.append(concept_set)

    def remove_concept_set_by_id(self, id_: int) -> None:
        """
        Removes a concept set by its id
        """
        if self.concept_sets:
            self.concept_sets = [cs for cs in self.concept_sets if cs.id != id_]

    def add_inclusion_rule(self, rule: InclusionRule) -> None:
        """
        Adds an inclusion rule
        """
        if not isinstance(rule, InclusionRule):
            raise TypeError("Expected InclusionRule instance")
        self.inclusion_rules.append(rule)

    def remove_inclusion_rule_by_name(self, name: str) -> None:
        """
        Removes an inclusion rule by its name
        """
        if self.inclusion_rules:
            self.inclusion_rules = [
                r for r in self.inclusion_rules if getattr(r, "name", None) != name
            ]

    def add_censoring_criteria(self, criteria: Criteria) -> None:
        """
        Adds a censoring criteria
        """
        if not isinstance(criteria, Criteria):
            raise TypeError("Expected Criteria instance")
        self.censoring_criteria.append(criteria)

    def remove_censoring_criteria_by_type(self, criteria_type: str) -> None:
        """
        Removes a censoring criteria by its type
        """
        if self.censoring_criteria:
            self.censoring_criteria = [
                c
                for c in self.censoring_criteria
                if c.__class__.__name__ != criteria_type
            ]

    def validate_expression(self) -> bool:
        """Validate the cohort expression."""
        # Basic validation logic
        if not self.primary_criteria:
            return False

        if self.concept_sets:
            for concept_set in self.concept_sets:
                if not concept_set.id:
                    return False

        return True

    def get_concept_set_ids(self) -> List[int]:
        """Get all concept set IDs used in this expression."""
        if not self.concept_sets:
            return []
        return [cs.id for cs in self.concept_sets if cs.id is not None]

    def check(self) -> List["Warning"]:
        """Run validation checks on this cohort expression.

        This method runs all validation checks defined in the check module
        and returns a list of warnings found during validation.

        Returns:
            A list of Warning objects. Empty list if no issues found.

        Example:
            >>> expression = CohortExpression(...)
            >>> warnings = expression.check()
            >>> for warning in warnings:
            ...     print(f"{warning.severity}: {warning.to_message()}")
        """
        # Import here to avoid circular dependencies
        from ..check.checker import Checker

        checker = Checker()
        return checker.check(self)

    def checksum(self, algorithm: str = "sha256") -> str:
        """Calculate a checksum for this cohort expression.

        Args:
            algorithm: Hash algorithm to use (default: sha256)

        Returns:
            Hex digest of the checksum
        """
        import hashlib
        import json

        # 1. Dump with defaults excluded to handle implicit defaults
        data = self.model_dump(exclude_unset=True, exclude_defaults=True, by_alias=True)

        # 2. Normalize: remove metadata, deduplicate concept sets, etc.
        normalized_data = self._normalize_for_checksum(data)

        # 3. Serialize to canonical JSON
        canonical_json = json.dumps(normalized_data, sort_keys=True)

        h = hashlib.new(algorithm)
        h.update(canonical_json.encode("utf-8"))
        return h.hexdigest()

    def _normalize_for_checksum(self, data: Any) -> Any:
        """Recursively normalize data for checksum calculation.

        Removes metadata fields from Concepts, deduplicates ConceptSet items,
        and ensures consistent ordering.
        """
        if isinstance(data, dict):
            # Handle ConceptSet Expression Items
            if "items" in data and isinstance(data["items"], list):
                # Check if these look like ConceptSetItems (have 'concept')
                if (
                    data["items"]
                    and isinstance(data["items"][0], dict)
                    and "concept" in data["items"][0]
                ):
                    normalized_items = []
                    seen_items = set()

                    for item in data["items"]:
                        # Normalize the item first
                        norm_item = self._normalize_for_checksum(item)

                        # Create a sortable/hashable representation for deduplication
                        # We need to sort keys to ensure tuple order is consistent
                        item_json = json.dumps(norm_item, sort_keys=True)

                        if item_json not in seen_items:
                            seen_items.add(item_json)
                            normalized_items.append(norm_item)

                    # Sort items to ensure list order doesn't affect hash
                    # Sort by the JSON string representation
                    normalized_items.sort(key=lambda x: json.dumps(x, sort_keys=True))

                    new_data = data.copy()
                    new_data["items"] = normalized_items
                    return new_data

            # Handle Concept Objects (heuristically by fields)
            if "CONCEPT_ID" in data:
                # Keep ID, remove metadata names/codes/vocab
                # Keep only structural identifier
                return {"CONCEPT_ID": data["CONCEPT_ID"]}

            # Recurse for other dicts
            return {k: self._normalize_for_checksum(v) for k, v in data.items()}

        elif isinstance(data, list):
            return [self._normalize_for_checksum(item) for item in data]

        return data

    # =========================================================================
    # VALIDATION AND PROPERTY CHECKING METHODS
    # =========================================================================

    def is_first_event(self) -> bool:
        """Check if cohort uses first event criteria.

        Returns:
            True if all primary criteria have first=True, False otherwise.
        """
        if not self.primary_criteria or not self.primary_criteria.criteria_list:
            return False

        # Check if all criteria have first=True
        for criteria in self.primary_criteria.criteria_list:
            # Get the first attribute, handling both direct attribute and nested structure
            first_value = getattr(criteria, "first", None)
            if first_value is not True:
                return False

        return True

    def has_exclusion_rules(self) -> bool:
        """Check if cohort has exclusion rules (inclusion rules).

        Note: In CIRCE terminology, "inclusion rules" act as exclusion criteria.

        Returns:
            True if the cohort has any inclusion rules.
        """
        return bool(self.inclusion_rules and len(self.inclusion_rules) > 0)

    def get_exclusion_count(self) -> int:
        """Get the number of exclusion rules (inclusion rules).

        Returns:
            The number of inclusion rules.
        """
        return len(self.inclusion_rules) if self.inclusion_rules else 0

    def has_inclusion_rule_by_name(self, name: str) -> bool:
        """Check if an inclusion rule with the given name exists.

        This is useful for checking if specific rules are shared between cohorts.

        Args:
            name: The name of the inclusion rule to search for.

        Returns:
            True if an inclusion rule with the given name exists.
        """
        if not self.inclusion_rules:
            return False

        for rule in self.inclusion_rules:
            if getattr(rule, "name", None) == name:
                return True

        return False

    def has_censoring_criteria(self) -> bool:
        """Check if cohort has censoring criteria.

        Returns:
            True if censoring criteria are defined.
        """
        return bool(self.censoring_criteria and len(self.censoring_criteria) > 0)

    def get_censoring_criteria_types(self) -> List[str]:
        """Get list of censoring criteria class names.

        Returns:
            List of class names (e.g., ['ConditionOccurrence', 'DrugExposure']).
        """
        if not self.censoring_criteria:
            return []

        return [criteria.__class__.__name__ for criteria in self.censoring_criteria]

    def has_additional_criteria(self) -> bool:
        """Check if cohort has additional criteria defined and not empty.

        Returns:
            True if additional criteria are defined and not empty.
        """
        if not self.additional_criteria:
            return False

        # Check if the criteria group is not empty
        return not self.additional_criteria.is_empty()

    def has_end_strategy(self) -> bool:
        """Check if cohort has an end strategy defined.

        Returns:
            True if an end strategy is defined.
        """
        return self.end_strategy is not None

    def get_end_strategy_type(self) -> Optional[str]:
        """Get the type of end strategy.

        Returns:
            'DateOffset', 'CustomEra', or None if no end strategy is defined.
        """
        if not self.end_strategy:
            return None

        class_name = self.end_strategy.__class__.__name__
        if class_name == "DateOffsetStrategy":
            return "DateOffset"
        elif class_name == "CustomEraStrategy":
            return "CustomEra"
        else:
            return class_name

    def get_primary_criteria_types(self) -> List[str]:
        """Get list of primary criteria class names.

        Returns:
            List of class names (e.g., ['ConditionOccurrence', 'DrugExposure']).
        """
        if not self.primary_criteria or not self.primary_criteria.criteria_list:
            return []

        return [
            criteria.__class__.__name__
            for criteria in self.primary_criteria.criteria_list
        ]

    def has_observation_window(self) -> bool:
        """Check if observation window is defined in primary criteria.

        Returns:
            True if observation window is defined.
        """
        if not self.primary_criteria:
            return False

        return self.primary_criteria.observation_window is not None

    def get_primary_limit_type(self) -> Optional[str]:
        """Get the primary limit type.

        Returns:
            The primary limit type (e.g., 'All', 'First') or None.
        """
        if not self.primary_criteria or not self.primary_criteria.primary_limit:
            return None

        return getattr(self.primary_criteria.primary_limit, "type", None)

    def get_concept_set_count(self) -> int:
        """Get the number of concept sets.

        Returns:
            The number of concept sets.
        """
        return len(self.concept_sets) if self.concept_sets else 0

    def has_concept_sets(self) -> bool:
        """Check if concept sets are defined.

        Returns:
            True if concept sets are defined.
        """
        return bool(self.concept_sets and len(self.concept_sets) > 0)

    def _repr_markdown_(self) -> str:
        """IPython notebook markdown representation.

        Returns:
            Markdown string defining the cohort.
        """
        try:
            # Import locally to avoid circular dependencies
            from .printfriendly.markdown_render import MarkdownRender

            renderer = MarkdownRender()
            return renderer.render_cohort_expression(self)
        except Exception as e:
            return f"Error rendering cohort markdown: {str(e)}"

    def __str__(self) -> str:
        """String representation of the cohort.

        Returns:
            Markdown string defining the cohort.
        """
        return self._repr_markdown_()
