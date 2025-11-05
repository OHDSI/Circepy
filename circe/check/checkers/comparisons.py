"""
Comparisons utility class.

This module provides utility functions for comparing values in validation checks.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from datetime import datetime
from typing import Optional, List, Callable, TYPE_CHECKING
from ...cohortdefinition.core import NumericRange, DateRange, Period
from ...vocabulary.concept import ConceptSet, Concept

if TYPE_CHECKING:
    from ...cohortdefinition.criteria import Criteria
    from ...cohortdefinition.core import ObservationFilter, Window
else:
    # Import at runtime to avoid circular dependencies
    try:
        from ...cohortdefinition.criteria import Criteria
        from ...cohortdefinition.core import ObservationFilter, Window
    except ImportError:
        pass


class Comparisons:
    """Utility class for comparing values in validation checks.
    
    Java equivalent: org.ohdsi.circe.check.checkers.Comparisons
    
    This class provides static methods for comparing ranges, dates,
    and other values.
    """
    
    @staticmethod
    def start_is_greater_than_end(range_val) -> bool:
        """Check if start value is greater than end value (supports NumericRange, DateRange, and Period).
        
        Args:
            range_val: The range or period to check (NumericRange, DateRange, or Period)
            
        Returns:
            True if start > end, False otherwise
        """
        if range_val is None:
            return False
        
        # Import here to avoid circular dependencies
        from ...cohortdefinition.core import NumericRange, DateRange, Period
        
        if isinstance(range_val, NumericRange):
            if range_val.value is None or range_val.extent is None:
                return False
            return int(range_val.value) > int(range_val.extent)
        elif isinstance(range_val, DateRange):
            if range_val.value is None or range_val.extent is None:
                return False
            try:
                start_date = datetime.strptime(range_val.value, "%Y-%m-%d").date()
                end_date = datetime.strptime(range_val.extent, "%Y-%m-%d").date()
                return start_date > end_date
            except (ValueError, TypeError):
                return False
        elif isinstance(range_val, Period):
            if range_val.start_date is None or range_val.end_date is None:
                return False
            try:
                start_date = datetime.strptime(range_val.start_date, "%Y-%m-%d").date()
                end_date = datetime.strptime(range_val.end_date, "%Y-%m-%d").date()
                return start_date > end_date
            except (ValueError, TypeError):
                return False
        return False
    
    @staticmethod
    def is_date_valid(date: Optional[str]) -> bool:
        """Check if a date string is valid.
        
        Args:
            date: The date string to validate
            
        Returns:
            True if the date is valid, False otherwise
        """
        if date is None:
            return False
        try:
            datetime.strptime(date, "%Y-%m-%d")
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def is_start_negative(range_val: NumericRange) -> bool:
        """Check if the start value is negative.
        
        Args:
            range_val: The numeric range to check
            
        Returns:
            True if start value is negative, False otherwise
        """
        if range_val is None or range_val.value is None:
            return False
        return int(range_val.value) < 0
    
    @staticmethod
    def compare_to(filter_val: 'ObservationFilter', window: 'Window') -> int:
        """Compare an observation filter to a window.
        
        Args:
            filter_val: The observation filter
            window: The window to compare against
            
        Returns:
            An integer representing the comparison result
        """
        if filter_val is None or window is None:
            return 0
        
        range1 = filter_val.post_days + filter_val.prior_days
        range2_start = 0
        range2_end = 0
        
        if window.start and window.start.days is not None:
            range2_start = window.start.coeff * window.start.days
        
        if window.end and window.end.days is not None:
            range2_end = window.end.coeff * window.end.days
        
        return range1 - (range2_end - range2_start)
    
    @staticmethod
    def is_before(window: 'Window') -> bool:
        """Check if a window is before the reference point.
        
        Args:
            window: The window to check
            
        Returns:
            True if the window is before, False otherwise
        """
        if window is None:
            return False
        return Comparisons.is_before_endpoint(window.start) and not Comparisons.is_after_endpoint(window.end)
    
    @staticmethod
    def is_before_endpoint(endpoint: Optional['Window.Endpoint']) -> bool:
        """Check if an endpoint is before the reference point.
        
        Args:
            endpoint: The endpoint to check
            
        Returns:
            True if before, False otherwise
        """
        if endpoint is None:
            return False
        return endpoint.coeff < 0
    
    @staticmethod
    def is_after_endpoint(endpoint: Optional['Window.Endpoint']) -> bool:
        """Check if an endpoint is after the reference point.
        
        Args:
            endpoint: The endpoint to check
            
        Returns:
            True if after, False otherwise
        """
        if endpoint is None:
            return False
        return endpoint.coeff > 0
    
    @staticmethod
    def compare_concept_set(source: 'ConceptSet'):
        """Create a predicate function to compare concept sets.
        
        Args:
            source: The source concept set to compare against
            
        Returns:
            A function that takes a ConceptSet and returns True if it matches
        """
        def compare_func(concept_set: 'ConceptSet') -> bool:
            if concept_set.expression == source.expression:
                return True
            if concept_set.expression and source.expression:
                if len(concept_set.expression.items) == len(source.expression.items):
                    source_concepts = [item.concept for item in source.expression.items]
                    return all(
                        any(Comparisons.compare_concept(concept)(source_concept) 
                            for source_concept in source_concepts)
                        for concept in [item.concept for item in concept_set.expression.items]
                    )
            return False
        return compare_func
    
    @staticmethod
    def compare_concept(source: 'Concept'):
        """Create a predicate function to compare concepts.
        
        Args:
            source: The source concept to compare against
            
        Returns:
            A function that takes a Concept and returns True if it matches
        """
        def compare_func(concept: 'Concept') -> bool:
            return (concept.concept_code == source.concept_code and
                   concept.domain_id == source.domain_id and
                   concept.vocabulary_id == source.vocabulary_id)
        return compare_func
    
    @staticmethod
    def compare_criteria(c1: 'Criteria', c2: 'Criteria') -> bool:
        """Compare two criteria to see if they are the same type and have the same codeset ID.
        
        Args:
            c1: The first criteria
            c2: The second criteria
            
        Returns:
            True if the criteria are the same type and have the same codeset ID
        """
        if type(c1) != type(c2):
            return False
        
        # Import here to avoid circular dependencies
        from ...cohortdefinition.criteria import (
            ConditionEra, ConditionOccurrence, Death, DeviceExposure,
            DoseEra, DrugEra, DrugExposure, Measurement, Observation,
            ProcedureOccurrence, Specimen, VisitOccurrence, VisitDetail
        )
        
        if isinstance(c1, ConditionEra):
            return c1.codeset_id == c2.codeset_id
        elif isinstance(c1, ConditionOccurrence):
            return c1.codeset_id == c2.codeset_id
        elif isinstance(c1, Death):
            return c1.codeset_id == c2.codeset_id
        elif isinstance(c1, DeviceExposure):
            return c1.codeset_id == c2.codeset_id
        elif isinstance(c1, DoseEra):
            return c1.codeset_id == c2.codeset_id
        elif isinstance(c1, DrugEra):
            return c1.codeset_id == c2.codeset_id
        elif isinstance(c1, DrugExposure):
            return c1.codeset_id == c2.codeset_id
        elif isinstance(c1, Measurement):
            return c1.codeset_id == c2.codeset_id
        elif isinstance(c1, Observation):
            return c1.codeset_id == c2.codeset_id
        elif isinstance(c1, ProcedureOccurrence):
            return c1.codeset_id == c2.codeset_id
        elif isinstance(c1, Specimen):
            return c1.codeset_id == c2.codeset_id
        elif isinstance(c1, VisitOccurrence):
            return c1.codeset_id == c2.codeset_id
        elif isinstance(c1, VisitDetail):
            return c1.codeset_id == c2.codeset_id
        
        return False

