"""
Main cohort definition classes.

This module contains the main CohortExpression class and related components.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List, Optional, Any, Union, TYPE_CHECKING
from pydantic import BaseModel, Field, ConfigDict
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
    concept_sets: Optional[List['ConceptSet']] = Field(default=None, alias="conceptSets")
    qualified_limit: Optional[ResultLimit] = Field(default=None, alias="qualifiedLimit")
    additional_criteria: Optional[CriteriaGroup] = Field(default=None, alias="additionalCriteria")
    end_strategy: Optional[EndStrategy] = Field(default=None, alias="endStrategy")
    cdm_version_range: Optional[Period] = Field(default=None, alias="cdmVersionRange")
    primary_criteria: Optional[PrimaryCriteria] = Field(default=None, alias="primaryCriteria")
    expression_limit: Optional[ResultLimit] = Field(default=None, alias="expressionLimit")
    collapse_settings: Optional[CollapseSettings] = Field(default=None, alias="collapseSettings")
    title: Optional[str] = None
    inclusion_rules: Optional[List['InclusionRule']] = Field(default=None, alias="inclusionRules")
    censor_window: Optional[Period] = Field(default=None, alias="censorWindow")
    censoring_criteria: Optional[List[Any]] = Field(default=None, alias="censoringCriteria")

    model_config = ConfigDict(populate_by_name=True)

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
