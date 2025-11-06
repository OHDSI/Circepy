"""
Main cohort definition classes.

This module contains the main CohortExpression class and related components.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List, Optional, Any, Union, TYPE_CHECKING
from pydantic import BaseModel, Field, ConfigDict, model_validator, AliasChoices
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
    censoring_criteria: Optional[List[Any]] = Field(
        default=None,
        validation_alias=AliasChoices("CensoringCriteria", "censoringCriteria"),
        serialization_alias="CensoringCriteria"
    )

    model_config = ConfigDict(populate_by_name=True)
    
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
