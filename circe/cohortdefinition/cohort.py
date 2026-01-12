"""
Main cohort definition classes.

This module contains the main CohortExpression class and related components.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List, Optional, Any, Union, TYPE_CHECKING
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator, AliasChoices
from .core import (
    ResultLimit, Period, CollapseSettings, EndStrategy, DateOffsetStrategy, CustomEraStrategy,
    PrimaryCriteria, CriteriaGroup, ObservationFilter, CriteriaGroup, Period, CollapseSettings
)
from .criteria import Criteria

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


class CohortExpression(BaseModel):
    """Main cohort expression class containing all cohort definition components.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.CohortExpression
    """

    concept_sets: Optional[List[ConceptSet]] = Field(
        default=None,
        validation_alias=AliasChoices("ConceptSets", "conceptSets"),
        serialization_alias="ConceptSets"
    )
    qualified_limit: Optional[ResultLimit] = Field(
        default=None,
        validation_alias=AliasChoices("QualifiedLimit", "qualifiedLimit"),
        serialization_alias="QualifiedLimit"
    )
    additional_criteria: Optional[CriteriaGroup] = Field(
        default=None,
        validation_alias=AliasChoices("AdditionalCriteria", "additionalCriteria"),
        serialization_alias="AdditionalCriteria"
    )
    end_strategy: Optional[Union[EndStrategy, DateOffsetStrategy, CustomEraStrategy]] = Field(
        default=None,
        validation_alias=AliasChoices("EndStrategy", "endStrategy"),
        serialization_alias="EndStrategy"
    )
    cdm_version_range: Optional[Period] = Field(
        default=None,
        validation_alias=AliasChoices("CdmVersionRange", "cdmVersionRange"),
        serialization_alias="CdmVersionRange"
    )
    primary_criteria: Optional[PrimaryCriteria] = Field(
        default=None,
        validation_alias=AliasChoices("PrimaryCriteria", "primaryCriteria"),
        serialization_alias="PrimaryCriteria"
    )
    expression_limit: Optional[ResultLimit] = Field(
        default=None,
        validation_alias=AliasChoices("ExpressionLimit", "expressionLimit"),
        serialization_alias="ExpressionLimit"
    )
    collapse_settings: Optional[CollapseSettings] = Field(
        default=None,
        validation_alias=AliasChoices("CollapseSettings", "collapseSettings"),
        serialization_alias="CollapseSettings"
    )
    title: Optional[str] = None
    inclusion_rules: Optional[List[InclusionRule]] = Field(
        default=None,
        validation_alias=AliasChoices("InclusionRules", "inclusionRules"),
        serialization_alias="InclusionRules"
    )
    censor_window: Optional[Period] = Field(
        default=None,
        validation_alias=AliasChoices("CensorWindow", "censorWindow"),
        serialization_alias="CensorWindow"
    )
    censoring_criteria: Optional[List[Criteria]] = Field(
        default=None,
        validation_alias=AliasChoices("CensoringCriteria", "censoringCriteria"),
        serialization_alias="CensoringCriteria"
    )

    model_config = ConfigDict(populate_by_name=True)
    
    @field_validator('end_strategy', mode='before')
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
        if 'DateOffset' in v:
            date_offset_data = v['DateOffset']
            return DateOffsetStrategy.model_validate(date_offset_data, strict=False)
        
        # Check if it has CustomEra key
        if 'CustomEra' in v:
            custom_era_data = v['CustomEra']
            return CustomEraStrategy.model_validate(custom_era_data, strict=False)
        
        # Otherwise, try to parse as base EndStrategy
        return EndStrategy.model_validate(v, strict=False)
    
    @field_validator('censoring_criteria', mode='before')
    @classmethod
    def deserialize_censoring_criteria(cls, v: Any) -> Any:
        """Deserialize censoring criteria from polymorphic JSON format.
        
        Censoring criteria come as [{"ConditionOccurrence": {...}}, ...] 
        and need to be unwrapped and deserialized to Criteria objects.
        """
        if not v or not isinstance(v, list):
            return v
        
        from .criteria import (
            ConditionOccurrence, DrugExposure, ProcedureOccurrence, VisitOccurrence,
            Observation, Measurement, DeviceExposure, Specimen, Death, VisitDetail,
            ObservationPeriod, PayerPlanPeriod, LocationRegion, ConditionEra, 
            DrugEra, DoseEra
        )
        
        criteria_class_map = {
            'ConditionOccurrence': ConditionOccurrence,
            'DrugExposure': DrugExposure,
            'ProcedureOccurrence': ProcedureOccurrence,
            'VisitOccurrence': VisitOccurrence,
            'Observation': Observation,
            'Measurement': Measurement,
            'DeviceExposure': DeviceExposure,
            'Specimen': Specimen,
            'Death': Death,
            'VisitDetail': VisitDetail,
            'ObservationPeriod': ObservationPeriod,
            'PayerPlanPeriod': PayerPlanPeriod,
            'LocationRegion': LocationRegion,
            'ConditionEra': ConditionEra,
            'DrugEra': DrugEra,
            'DoseEra': DoseEra,
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
                if 'First' not in data_copy and 'first' not in data_copy:
                    data_copy['First'] = False
                if criteria_type == 'Measurement' and 'MeasurementTypeExclude' not in data_copy and 'measurementTypeExclude' not in data_copy:
                    data_copy['MeasurementTypeExclude'] = False
                if criteria_type == 'Observation' and 'ObservationTypeExclude' not in data_copy and 'observationTypeExclude' not in data_copy:
                    data_copy['ObservationTypeExclude'] = False
                if criteria_type == 'ConditionOccurrence' and 'ConditionTypeExclude' not in data_copy and 'conditionTypeExclude' not in data_copy:
                    data_copy['ConditionTypeExclude'] = False

                criteria_obj = criteria_class_map[criteria_type].model_validate(data_copy, strict=False)
                deserialized.append(criteria_obj)
            else:
                deserialized.append(item)

        return deserialized

    @model_validator(mode='before')
    @classmethod
    def normalize_before_validation(cls, data: Any) -> Any:
        """Normalize data before validation.
        
        Handles cdmVersionRange as string by removing it if it's empty or invalid for Period.
        """
        if isinstance(data, dict):
            # If cdmVersionRange is a string, and we now expect a Period, 
            # we should only keep it if it can be represented as a Period or if it's not a string.
            # Java CIRCE sometimes has cdmVersionRange as a string in older versions or specific exports.
            cdm_v = data.get('CdmVersionRange') or data.get('cdmVersionRange')
            if isinstance(cdm_v, str):
                data = dict(data)
                # If it's a string, we might just want to drop it to avoid validation error,
                # or try to parse it. For now, dropping it matches the previous logic but safely.
                data.pop('CdmVersionRange', None)
                data.pop('cdmVersionRange', None)

            if 'censorWindow' in data and data['censorWindow'] == {}:
                data = dict(data)
                data.pop('censorWindow')

        return data

    def add_concept_set(self, concept_set: ConceptSet) -> None:
        """
        Adds a concept set
        """
        if not isinstance(concept_set, ConceptSet):
            raise TypeError("Expected ConceptSet instance")
        if self.concept_sets is None:
            self.concept_sets = []
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
        if self.inclusion_rules is None:
            self.inclusion_rules = []
        self.inclusion_rules.append(rule)

    def remove_inclusion_rule_by_name(self, name: str) -> None:
        """
        Removes an inclusion rule by its name
        """
        if self.inclusion_rules:
            self.inclusion_rules = [r for r in self.inclusion_rules if getattr(r, 'name', None) != name]

    def add_censoring_criteria(self, criteria: Criteria) -> None:
        """
        Adds a censoring criteria
        """
        if not isinstance(criteria, Criteria):
            raise TypeError("Expected Criteria instance")
        if self.censoring_criteria is None:
            self.censoring_criteria = []
        self.censoring_criteria.append(criteria)

    def remove_censoring_criteria_by_type(self, criteria_type: str) -> None:
        """
        Removes a censoring criteria by its type
        """
        if self.censoring_criteria:
            self.censoring_criteria = [c for c in self.censoring_criteria if c.__class__.__name__ != criteria_type]

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
    
    def check(self) -> List['Warning']:
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
