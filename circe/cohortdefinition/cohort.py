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
    PrimaryCriteria, CriteriaGroup, ObservationFilter
)

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
    concept_sets: Optional[List['ConceptSet']] = Field(
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
    end_strategy: Optional[EndStrategy] = Field(
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
    inclusion_rules: Optional[List['InclusionRule']] = Field(
        default=None,
        validation_alias=AliasChoices("InclusionRules", "inclusionRules"),
        serialization_alias="InclusionRules"
    )
    censor_window: Optional[Period] = Field(
        default=None,
        validation_alias=AliasChoices("CensorWindow", "censorWindow"),
        serialization_alias="CensorWindow"
    )
    censoring_criteria: Optional[List['Criteria']] = Field(
        default=None,
        validation_alias=AliasChoices("CensoringCriteria", "censoringCriteria"),
        serialization_alias="CensoringCriteria"
    )

    model_config = ConfigDict(populate_by_name=True)
    
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
                # Make a copy to avoid modifying the original
                criteria_data_copy = dict(criteria_data)
                # Set default values for commonly missing required fields
                if 'First' not in criteria_data_copy and 'first' not in criteria_data_copy:
                    criteria_data_copy['First'] = False
                if criteria_type == 'Measurement' and 'MeasurementTypeExclude' not in criteria_data_copy and 'measurementTypeExclude' not in criteria_data_copy:
                    criteria_data_copy['MeasurementTypeExclude'] = False
                if criteria_type == 'Observation' and 'ObservationTypeExclude' not in criteria_data_copy and 'observationTypeExclude' not in criteria_data_copy:
                    criteria_data_copy['ObservationTypeExclude'] = False
                if criteria_type == 'ConditionOccurrence' and 'ConditionTypeExclude' not in criteria_data_copy and 'conditionTypeExclude' not in criteria_data_copy:
                    criteria_data_copy['ConditionTypeExclude'] = False

                criteria_obj = criteria_class_map[criteria_type].model_validate(criteria_data_copy, strict=False)
                deserialized.append(criteria_obj)
            else:
                # Not a recognized criteria type, keep as-is
                deserialized.append(item)
        
        return deserialized
    
    @model_validator(mode='before')
    @classmethod
    def normalize_before_validation(cls, data: Any) -> Any:
        """Normalize data before validation.
        
        Handles cdmVersionRange as string by removing it.
        """
        if isinstance(data, dict):
            # Handle cdmVersionRange as string - remove it
            if 'cdmVersionRange' in data and isinstance(data['cdmVersionRange'], str):
                data = dict(data)  # Create copy
                data.pop('cdmVersionRange')
            
            # Handle empty censorWindow
            if 'censorWindow' in data and data['censorWindow'] == {}:
                data = dict(data) if 'cdmVersionRange' not in locals() else data
                data.pop('censorWindow')
        
        return data

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
