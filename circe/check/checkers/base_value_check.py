"""
Base value check class for validation checks.

This module provides the base class for checks that validate values
in criteria and demographic criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Optional
from .base_check import BaseCheck
from .warning_reporter import WarningReporter

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.cohort import CohortExpression
    from ...cohortdefinition.criteria import Criteria, CorelatedCriteria, DemographicCriteria, PrimaryCriteria, CriteriaGroup
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.cohort import CohortExpression
        from ...cohortdefinition.criteria import Criteria, CorelatedCriteria, DemographicCriteria, PrimaryCriteria, CriteriaGroup


class BaseValueCheck(BaseCheck):
    """Base class for checks that validate values in criteria.
    
    Java equivalent: org.ohdsi.circe.check.checkers.BaseValueCheck
    
    This class provides functionality to iterate over criteria in
    primary criteria, additional criteria, inclusion rules, and
    censoring criteria.
    """
    
    INCLUSION_CRITERIA = "Inclusion criteria "
    PRIMARY_CRITERIA = "Primary criteria"
    ADDITIONAL_CRITERIA = "Additional criteria"
    CENSORING_CRITERIA = "Censoring events"
    
    def _check(self, expression: 'CohortExpression', reporter: WarningReporter) -> None:
        """Check implementation that validates all criteria types.
        
        Args:
            expression: The cohort expression to validate
            reporter: The warning reporter to use
        """
        self._check_primary_criteria(expression.primary_criteria, reporter)
        self._check_additional_criteria(expression.additional_criteria, reporter)
        self._check_inclusion_rules(expression, reporter)
        self._check_censoring_criteria(expression, reporter)
    
    def _check_primary_criteria(self, primary_criteria: Optional['PrimaryCriteria'], reporter: WarningReporter) -> None:
        """Check primary criteria.
        
        Args:
            primary_criteria: The primary criteria to check
            reporter: The warning reporter to use
        """
        if primary_criteria and primary_criteria.criteria_list:
            for criteria in primary_criteria.criteria_list:
                self._check_criteria(criteria, reporter, self.PRIMARY_CRITERIA)
    
    def _check_additional_criteria(self, criteria_group: Optional['CriteriaGroup'], reporter: WarningReporter) -> None:
        """Check additional criteria.
        
        Args:
            criteria_group: The additional criteria group to check
            reporter: The warning reporter to use
        """
        if criteria_group:
            if hasattr(criteria_group, 'criteria_list') and criteria_group.criteria_list:
                for criteria in criteria_group.criteria_list:
                    self._check_criteria(criteria, reporter, self.ADDITIONAL_CRITERIA)
            if hasattr(criteria_group, 'demographic_criteria_list') and criteria_group.demographic_criteria_list:
                for criteria in criteria_group.demographic_criteria_list:
                    self._check_criteria(criteria, reporter, self.ADDITIONAL_CRITERIA)
            if hasattr(criteria_group, 'groups') and criteria_group.groups:
                for group in criteria_group.groups:
                    self._check_additional_criteria(group, reporter)
    
    def _check_censoring_criteria(self, expression: 'CohortExpression', reporter: WarningReporter) -> None:
        """Check censoring criteria.
        
        Args:
            expression: The cohort expression containing censoring criteria
            reporter: The warning reporter to use
        """
        if expression.censoring_criteria:
            for criteria in expression.censoring_criteria:
                self._check_criteria(criteria, reporter, self.CENSORING_CRITERIA)
    
    def _check_inclusion_rules(self, expression: 'CohortExpression', reporter: WarningReporter) -> None:
        """Check inclusion rules.
        
        Args:
            expression: The cohort expression containing inclusion rules
            reporter: The warning reporter to use
        """
        if expression.inclusion_rules:
            for rule in expression.inclusion_rules:
                if rule.expression:
                    rule_name = f'{self.INCLUSION_CRITERIA}"{rule.name}"'
                    if hasattr(rule.expression, 'criteria_list') and rule.expression.criteria_list:
                        for criteria in rule.expression.criteria_list:
                            self._check_criteria(criteria, reporter, rule_name)
                    if hasattr(rule.expression, 'demographic_criteria_list') and rule.expression.demographic_criteria_list:
                        for criteria in rule.expression.demographic_criteria_list:
                            self._check_criteria(criteria, reporter, rule_name)
    
    def _check_criteria(self, criteria, reporter: WarningReporter, name: str) -> None:
        """Check a criteria (supports multiple types via runtime checking).
        
        Args:
            criteria: The criteria to check (Criteria, CorelatedCriteria, DemographicCriteria, or CriteriaGroup)
            reporter: The warning reporter to use
            name: The name of the criteria group
        """
        # Import here to avoid circular dependencies
        from ...cohortdefinition.criteria import Criteria, CorelatedCriteria, DemographicCriteria
        from ...cohortdefinition.criteria import CriteriaGroup
        
        # Check CriteriaGroup
        if isinstance(criteria, CriteriaGroup):
            if hasattr(criteria, 'demographic_criteria_list') and criteria.demographic_criteria_list:
                for dem_criteria in criteria.demographic_criteria_list:
                    self._check_criteria(dem_criteria, reporter, name)
            if hasattr(criteria, 'criteria_list') and criteria.criteria_list:
                for corelated_criteria in criteria.criteria_list:
                    self._check_criteria(corelated_criteria, reporter, name)
            if hasattr(criteria, 'groups') and criteria.groups:
                for group in criteria.groups:
                    self._check_criteria(group, reporter, name)
        # Check CorelatedCriteria
        elif isinstance(criteria, CorelatedCriteria):
            if hasattr(criteria, 'criteria') and criteria.criteria:
                self._check_criteria(criteria.criteria, reporter, name)
        # Check DemographicCriteria
        elif isinstance(criteria, DemographicCriteria):
            factory = self._get_factory(reporter, name)
            factory.check(criteria)
        # Check Criteria (must be last as it's the base type)
        elif isinstance(criteria, Criteria):
            if hasattr(criteria, 'correlated_criteria') and criteria.correlated_criteria:
                self._check_criteria(criteria.correlated_criteria, reporter, name)
            # Don't call factory.check for base Criteria - only specific criteria types have ranges to check
            # The factory's check method is for CohortExpression, not Criteria
    
    def _get_factory(self, reporter: WarningReporter, name: str):
        """Get a checker factory (to be implemented by subclasses).
        
        Args:
            reporter: The warning reporter to use
            name: The name of the criteria group
            
        Returns:
            A checker factory instance
        """
        raise NotImplementedError("Subclasses must implement _get_factory")

