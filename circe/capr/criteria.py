"""
Criteria functions for CohortComposer.

These functions define occurrence counting and grouping logic for cohort criteria.
Modeled after OHDSI/Capr's atLeast, atMost, exactly, and group functions.
"""

from typing import Optional, List, Union
from dataclasses import dataclass, field
from circe.capr.query import Query
from circe.capr.window import TimeWindow


@dataclass
class Criteria:
    """
    Represents a criteria object that counts occurrences of a query within a time window.
    
    Attributes:
        occurrence_type: 'atLeast', 'atMost', or 'exactly'
        count: Number of occurrences required
        query: The domain query to count
        aperture: Time window for the search
        is_distinct: Whether to count distinct occurrences
    """
    occurrence_type: str  # 'atLeast', 'atMost', 'exactly'
    count: int
    query: Query
    aperture: Optional[TimeWindow] = None
    is_distinct: bool = False


@dataclass
class CriteriaGroup:
    """
    Represents a group of criteria combined with AND/OR logic.
    
    Attributes:
        group_type: 'ALL' (AND) or 'ANY' (OR)
        criteria_list: List of Criteria or nested CriteriaGroup objects
        demographic_criteria: Optional demographic restrictions
    """
    group_type: str  # 'ALL' or 'ANY'
    criteria_list: List[Union[Criteria, 'CriteriaGroup']] = field(default_factory=list)
    demographic_criteria: Optional[dict] = None


def at_least(
    count: int,
    query: Query,
    aperture: Optional[TimeWindow] = None,
    is_distinct: bool = False
) -> Criteria:
    """
    Create a criteria requiring at least N occurrences.
    
    Args:
        count: Minimum number of occurrences required (>=)
        query: Domain query to search for
        aperture: Time window for the search
        is_distinct: If True, count distinct occurrences
        
    Returns:
        Criteria object
        
    Example:
        >>> # At least 2 drug exposures within 365 days before index
        >>> at_least(
        ...     count=2,
        ...     query=drug_exposure(concept_set_id=1),
        ...     aperture=during_interval(event_starts(before=365, after=0))
        ... )
    """
    return Criteria(
        occurrence_type='atLeast',
        count=count,
        query=query,
        aperture=aperture,
        is_distinct=is_distinct
    )


def at_most(
    count: int,
    query: Query,
    aperture: Optional[TimeWindow] = None,
    is_distinct: bool = False
) -> Criteria:
    """
    Create a criteria requiring at most N occurrences.
    
    Args:
        count: Maximum number of occurrences allowed (<=)
        query: Domain query to search for
        aperture: Time window for the search
        is_distinct: If True, count distinct occurrences
        
    Returns:
        Criteria object
        
    Example:
        >>> # At most 1 prior condition
        >>> at_most(
        ...     count=1,
        ...     query=condition_occurrence(concept_set_id=2),
        ...     aperture=during_interval(event_starts(before=365, after=0))
        ... )
    """
    return Criteria(
        occurrence_type='atMost',
        count=count,
        query=query,
        aperture=aperture,
        is_distinct=is_distinct
    )


def exactly(
    count: int,
    query: Query,
    aperture: Optional[TimeWindow] = None,
    is_distinct: bool = False
) -> Criteria:
    """
    Create a criteria requiring exactly N occurrences.
    
    Args:
        count: Exact number of occurrences required (==)
        query: Domain query to search for
        aperture: Time window for the search
        is_distinct: If True, count distinct occurrences
        
    Returns:
        Criteria object
        
    Example:
        >>> # Exactly 0 prior drug exposures (exclusion)
        >>> exactly(
        ...     count=0,
        ...     query=drug_exposure(concept_set_id=3),
        ...     aperture=during_interval(event_starts(before=365, after=1))
        ... )
    """
    return Criteria(
        occurrence_type='exactly',
        count=count,
        query=query,
        aperture=aperture,
        is_distinct=is_distinct
    )


def with_all(*criteria: Union[Criteria, 'CriteriaGroup']) -> CriteriaGroup:
    """
    Combine criteria with AND logic - all must be satisfied.
    
    Args:
        *criteria: Variable number of Criteria or CriteriaGroup objects
        
    Returns:
        CriteriaGroup with ALL (AND) logic
        
    Example:
        >>> # Must have both conditions
        >>> with_all(
        ...     at_least(1, condition_occurrence(1), aperture),
        ...     at_least(1, drug_exposure(2), aperture)
        ... )
    """
    return CriteriaGroup(
        group_type='ALL',
        criteria_list=list(criteria)
    )


def with_any(*criteria: Union[Criteria, 'CriteriaGroup']) -> CriteriaGroup:
    """
    Combine criteria with OR logic - at least one must be satisfied.
    
    Args:
        *criteria: Variable number of Criteria or CriteriaGroup objects
        
    Returns:
        CriteriaGroup with ANY (OR) logic
        
    Example:
        >>> # Must have at least one of these conditions
        >>> with_any(
        ...     at_least(1, condition_occurrence(1), aperture),
        ...     at_least(1, condition_occurrence(2), aperture)
        ... )
    """
    return CriteriaGroup(
        group_type='ANY',
        criteria_list=list(criteria)
    )


# Convenience function for exclusions
def none_of(
    query: Query,
    aperture: Optional[TimeWindow] = None
) -> Criteria:
    """
    Convenience function for excluding patients with any occurrence.
    Equivalent to exactly(0, query, aperture).
    
    Args:
        query: Domain query that should have zero occurrences
        aperture: Time window for the search
        
    Returns:
        Criteria requiring exactly 0 occurrences
        
    Example:
        >>> # Exclude patients with prior insulin
        >>> none_of(
        ...     drug_exposure(concept_set_id=3),
        ...     aperture=during_interval(event_starts(before=365, after=1))
        ... )
    """
    return exactly(count=0, query=query, aperture=aperture)


def any_of(
    query: Query,
    aperture: Optional[TimeWindow] = None
) -> Criteria:
    """
    Convenience function for requiring at least one occurrence.
    Equivalent to at_least(1, query, aperture).
    
    Args:
        query: Domain query that should have at least one occurrence
        aperture: Time window for the search
        
    Returns:
        Criteria requiring at least 1 occurrence
        
    Example:
        >>> # Require at least one prior diagnosis
        >>> any_of(
        ...     condition_occurrence(concept_set_id=1),
        ...     aperture=during_interval(event_starts(before=365, after=0))
        ... )
    """
    return at_least(count=1, query=query, aperture=aperture)
