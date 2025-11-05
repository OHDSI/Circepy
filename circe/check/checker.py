"""
Checker class for running all validation checks.

This module provides the main Checker class that runs all validation
checks against a cohort expression and returns all warnings.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List
from .check import Check
from .warning import Warning

# Import at runtime to avoid circular dependencies
try:
    from ..cohortdefinition.cohort import CohortExpression
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ..cohortdefinition.cohort import CohortExpression


class Checker(Check):
    """Main checker class that runs all validation checks.
    
    Java equivalent: org.ohdsi.circe.check.Checker
    
    This class orchestrates running all validation checks against a
    cohort expression and collects all warnings.
    """
    
    def _get_checks(self) -> List[Check]:
        """Get the list of all checks to run.
        
        Returns:
            A list of Check instances to run against the expression.
        """
        # Import checkers here to avoid circular dependencies
        from .checkers.unused_concepts_check import UnusedConceptsCheck
        from .checkers.exit_criteria_check import ExitCriteriaCheck
        from .checkers.exit_criteria_days_offset_check import ExitCriteriaDaysOffsetCheck
        from .checkers.range_check import RangeCheck
        from .checkers.concept_check import ConceptCheck
        from .checkers.concept_set_selection_check import ConceptSetSelectionCheck
        from .checkers.attribute_check import AttributeCheck
        from .checkers.text_check import TextCheck
        from .checkers.incomplete_rule_check import IncompleteRuleCheck
        from .checkers.initial_event_check import InitialEventCheck
        from .checkers.no_exit_criteria_check import NoExitCriteriaCheck
        from .checkers.concept_set_criteria_check import ConceptSetCriteriaCheck
        from .checkers.drug_era_check import DrugEraCheck
        from .checkers.ocurrence_check import OcurrenceCheck
        from .checkers.duplicates_criteria_check import DuplicatesCriteriaCheck
        from .checkers.duplicates_concept_set_check import DuplicatesConceptSetCheck
        from .checkers.drug_domain_check import DrugDomainCheck
        from .checkers.empty_concept_set_check import EmptyConceptSetCheck
        from .checkers.events_progression_check import EventsProgressionCheck
        from .checkers.time_window_check import TimeWindowCheck
        from .checkers.time_pattern_check import TimePatternCheck
        from .checkers.domain_type_check import DomainTypeCheck
        from .checkers.criteria_contradictions_check import CriteriaContradictionsCheck
        from .checkers.death_time_window_check import DeathTimeWindowCheck
        
        checks: List[Check] = [
            UnusedConceptsCheck(),
            ExitCriteriaCheck(),
            ExitCriteriaDaysOffsetCheck(),
            RangeCheck(),
            ConceptCheck(),
            ConceptSetSelectionCheck(),
            AttributeCheck(),
            TextCheck(),
            IncompleteRuleCheck(),
            InitialEventCheck(),
            NoExitCriteriaCheck(),
            ConceptSetCriteriaCheck(),
            DrugEraCheck(),
            OcurrenceCheck(),
            DuplicatesCriteriaCheck(),
            DuplicatesConceptSetCheck(),
            DrugDomainCheck(),
            EmptyConceptSetCheck(),
            EventsProgressionCheck(),
            TimeWindowCheck(),
            TimePatternCheck(),
            DomainTypeCheck(),
            CriteriaContradictionsCheck(),
            DeathTimeWindowCheck(),
        ]
        
        return checks
    
    def check(self, expression: 'CohortExpression') -> List[Warning]:
        """Run all validation checks against a cohort expression.
        
        Args:
            expression: The cohort expression to validate
            
        Returns:
            A list of all warnings found by all checks.
        """
        result: List[Warning] = []
        for check in self._get_checks():
            result.extend(check.check(expression))
        return result

