"""
UnusedConceptsCheck class.

This module provides validation for unused concept sets.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List, Optional
from ..warning_severity import WarningSeverity
from ..warnings.concept_set_warning import ConceptSetWarning
from .base_check import BaseCheck
from .warning_reporter import WarningReporter
from .criteria_checker_factory import CriteriaCheckerFactory

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.cohort import CohortExpression
    from ...cohortdefinition.criteria import Criteria, CorelatedCriteria
    from ...cohortdefinition.core import CustomEraStrategy
    from ...cohortdefinition.criteria import CriteriaGroup
    from ...vocabulary.concept import ConceptSet
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.cohort import CohortExpression
        from ...cohortdefinition.criteria import Criteria, CorelatedCriteria
        from ...cohortdefinition.core import CustomEraStrategy
        from ...cohortdefinition.criteria import CriteriaGroup
        from ...vocabulary.concept import ConceptSet


class UnusedConceptsCheck(BaseCheck):
    """Check for unused concept sets in the expression.
    
    Java equivalent: org.ohdsi.circe.check.checkers.UnusedConceptsCheck
    """
    
    def _define_severity(self) -> WarningSeverity:
        """Define the severity level for this check.
        
        Returns:
            WARNING severity level
        """
        return WarningSeverity.WARNING
    
    def _get_reporter(self, severity: WarningSeverity, warnings: List) -> WarningReporter:
        """Get a warning reporter that creates ConceptSetWarning instances.
        
        Args:
            severity: The severity level
            warnings: The list to add warnings to
            
        Returns:
            A WarningReporter that creates ConceptSetWarning instances
        """
        def reporter(template: str, *args) -> None:
            if args and isinstance(args[0], ConceptSet):
                warnings.append(ConceptSetWarning(severity, template, args[0]))
        return reporter
    
    def _check(self, expression: 'CohortExpression', reporter: WarningReporter) -> None:
        """Check for unused concept sets.
        
        Args:
            expression: The cohort expression to check
            reporter: The warning reporter to use
        """
        additional_criteria = self._get_additional_criteria(expression)
        
        if expression.concept_sets:
            for concept_set in expression.concept_sets:
                if not self._is_used(expression, additional_criteria, concept_set):
                    reporter("Concept Set \"%s\" is not used", concept_set)
    
    def _get_additional_criteria(self, expression: 'CohortExpression') -> List['Criteria']:
        """Get all criteria from additional criteria.
        
        Args:
            expression: The cohort expression
            
        Returns:
            A list of all criteria from additional criteria
        """
        additional_criteria: List['Criteria'] = []
        if expression.additional_criteria:
            additional_criteria.extend(self._to_criteria_list(expression.additional_criteria.criteria_list))
            if expression.additional_criteria.groups:
                additional_criteria.extend(self._to_criteria_list_from_groups(expression.additional_criteria.groups))
        return additional_criteria
    
    def _is_used(
        self, 
        expression: 'CohortExpression', 
        additional_criteria: List['Criteria'], 
        concept_set: 'ConceptSet'
    ) -> bool:
        """Check if a concept set is used.
        
        Args:
            expression: The cohort expression
            additional_criteria: Additional criteria to check
            concept_set: The concept set to check
            
        Returns:
            True if the concept set is used, False otherwise
        """
        # Check primary criteria
        if expression.primary_criteria and expression.primary_criteria.criteria_list:
            if self._is_concept_set_used(concept_set, expression.primary_criteria.criteria_list):
                return True
        
        # Check additional criteria
        if self._is_concept_set_used(concept_set, additional_criteria):
            return True
        
        # Check inclusion rules
        if expression.inclusion_rules:
            for rule in expression.inclusion_rules:
                if rule.expression:
                    # Convert rule expression to criteria list
                    rule_criteria_list = []
                    if hasattr(rule.expression, 'criteria_list') and rule.expression.criteria_list:
                        rule_criteria_list.extend([c.criteria for c in rule.expression.criteria_list if hasattr(c, 'criteria') and c.criteria])
                    if rule_criteria_list and self._is_concept_set_used_in_list(concept_set, rule_criteria_list):
                        return True
        
        # Check end strategy (CustomEraStrategy)
        if isinstance(expression.end_strategy, CustomEraStrategy):
            if expression.end_strategy.drug_codeset_id == concept_set.id:
                return True
        
        # Check censoring criteria
        if expression.censoring_criteria:
            if self._is_concept_set_used(concept_set, expression.censoring_criteria):
                return True
        
        return False
    
    def _is_concept_set_used(self, concept_set: 'ConceptSet', target) -> bool:
        """Check if a concept set is used (supports both List[Criteria] and CriteriaGroup).
        
        Args:
            concept_set: The concept set to check
            target: Either a List[Criteria] or CriteriaGroup
            
        Returns:
            True if the concept set is used, False otherwise
        """
        # Import here to avoid circular dependencies
        from ...cohortdefinition.criteria import CriteriaGroup
        
        if isinstance(target, CriteriaGroup):
            criteria_list = self._to_criteria_list(target.criteria_list)
            if self._is_concept_set_used_in_list(concept_set, criteria_list):
                return True
            
            if target.groups:
                return any(self._is_concept_set_used(concept_set, group) for group in target.groups)
            
            return False
        elif isinstance(target, list):
            # Assume it's a list of Criteria
            return self._is_concept_set_used_in_list(concept_set, target)
        else:
            return False
    
    def _is_concept_set_used_in_list(self, concept_set: 'ConceptSet', criteria_list: List['Criteria']) -> bool:
        """Check if a concept set is used in a criteria list.
        
        Args:
            concept_set: The concept set to check
            criteria_list: The criteria list to check
            
        Returns:
            True if the concept set is used, False otherwise
        """
        factory = CriteriaCheckerFactory.get_factory(concept_set)
        main_check = any(factory.get_criteria_checker(criteria)(criteria) for criteria in criteria_list)
        
        if main_check:
            return True
        
        # Check correlated criteria
        for criteria in criteria_list:
            if hasattr(criteria, 'correlated_criteria') and criteria.correlated_criteria:
                # Convert correlated criteria to list and check
                correlated_list = self._correlated_criteria_to_list(criteria.correlated_criteria)
                if self._is_concept_set_used_in_list(concept_set, correlated_list):
                    return True
        
        return False
    
    def _correlated_criteria_to_list(self, correlated_criteria) -> List['Criteria']:
        """Convert correlated criteria to a list of criteria.
        
        Args:
            correlated_criteria: The correlated criteria to convert
            
        Returns:
            A list of Criteria
        """
        criteria_list: List['Criteria'] = []
        if hasattr(correlated_criteria, 'criteria_list') and correlated_criteria.criteria_list:
            criteria_list.extend([c.criteria for c in correlated_criteria.criteria_list if hasattr(c, 'criteria') and c.criteria])
        if hasattr(correlated_criteria, 'groups') and correlated_criteria.groups:
            for group in correlated_criteria.groups:
                if hasattr(group, 'criteria_list') and group.criteria_list:
                    criteria_list.extend([c.criteria for c in group.criteria_list if hasattr(c, 'criteria') and c.criteria])
        return criteria_list
    
    def _to_criteria_list(self, criteria_list: Optional[List['CorelatedCriteria']]) -> List['Criteria']:
        """Convert a list of CorelatedCriteria to a list of Criteria.
        
        Args:
            criteria_list: The list of CorelatedCriteria
            
        Returns:
            A list of Criteria
        """
        if not criteria_list:
            return []
        return [c.criteria for c in criteria_list if hasattr(c, 'criteria') and c.criteria]
    
    def _to_criteria_list_from_groups(self, groups: Optional[List['CriteriaGroup']]) -> List['Criteria']:
        """Convert groups to a list of criteria.
        
        Args:
            groups: The list of groups
            
        Returns:
            A list of Criteria
        """
        criteria: List['Criteria'] = []
        if groups:
            for group in groups:
                if group.criteria_list:
                    criteria.extend(self._to_criteria_list(group.criteria_list))
                if group.groups:
                    criteria.extend(self._to_criteria_list_from_groups(group.groups))
        return criteria

