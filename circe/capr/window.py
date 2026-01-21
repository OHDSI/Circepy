"""
Time window functions for CohortComposer.

These functions define the temporal relationship between events and an index point.
Modeled after OHDSI/Capr's aperture and window functions.
"""

from typing import Optional, Union
from dataclasses import dataclass


@dataclass
class WindowBoundary:
    """
    Represents a boundary point for a time window.
    
    Attributes:
        days: Number of days from the index point
        index: Which date to use as reference ('startDate' or 'endDate')
    """
    days: int
    index: str = "startDate"


@dataclass 
class TimeWindow:
    """
    Represents a time window (aperture) relative to an index event.
    
    Attributes:
        start_window: The start boundary of the window
        end_window: The end boundary of the window (optional)
        use_event_end: Whether to use event end date instead of start date
        restrict_visit: Whether to restrict to same visit
        ignore_observation_period: Whether to ignore observation period bounds
    """
    start_window: Optional['Interval'] = None
    end_window: Optional['Interval'] = None
    use_event_end: bool = False
    restrict_visit: bool = False
    ignore_observation_period: bool = False


@dataclass
class Interval:
    """
    Represents an interval with start and end boundaries.
    
    Attributes:
        start: Start boundary (days before index, positive = before)
        end: End boundary (days after index, positive = after)
        index: Which date to use as reference ('startDate' or 'endDate')
    """
    start: int  # days before (positive = before index)
    end: int    # days after (positive = after index)
    index: str = "startDate"


@dataclass
class ObservationWindow:
    """
    Represents the continuous observation requirement.
    
    Attributes:
        prior_days: Days of observation required before index
        post_days: Days of observation required after index
    """
    prior_days: int = 0
    post_days: int = 0


def event_starts(
    before: int = 0,
    after: int = 0,
    index: str = "startDate"
) -> Interval:
    """
    Create an interval relative to the event start date.
    
    Args:
        before: Days before the index (positive value)
        after: Days after the index (positive value)
        index: Which date to use as reference ('startDate' or 'endDate')
        
    Returns:
        Interval object
        
    Example:
        >>> # 365 days before to 0 days after index start
        >>> event_starts(before=365, after=0)
        
        >>> # 0 to 30 days after index start  
        >>> event_starts(before=0, after=30)
    """
    return Interval(
        start=before,
        end=after,
        index=index
    )


def event_ends(
    before: int = 0,
    after: int = 0,
    index: str = "endDate"
) -> Interval:
    """
    Create an interval relative to the event end date.
    
    Args:
        before: Days before the index end (positive value)
        after: Days after the index end (positive value)
        index: Which date to use as reference (default: 'endDate')
        
    Returns:
        Interval object
        
    Example:
        >>> # 0 to 30 days after index end
        >>> event_ends(before=0, after=30)
    """
    return Interval(
        start=before,
        end=after,
        index=index
    )


def during_interval(
    start_window: Optional[Interval] = None,
    end_window: Optional[Interval] = None,
    use_event_end: bool = False,
    restrict_visit: bool = False,
    ignore_observation_period: bool = False
) -> TimeWindow:
    """
    Create a time window (aperture) for criteria matching.
    
    Args:
        start_window: Interval for the start of the window
        end_window: Interval for the end of the window (optional)
        use_event_end: If True, use event end date for matching
        restrict_visit: If True, require same visit
        ignore_observation_period: If True, ignore observation period bounds
        
    Returns:
        TimeWindow object
        
    Example:
        >>> # Events occurring 365 days before to 0 days after index
        >>> during_interval(
        ...     start_window=event_starts(before=365, after=0)
        ... )
        
        >>> # Events occurring 0 to 30 days after index
        >>> during_interval(
        ...     start_window=event_starts(before=0, after=30)
        ... )
    """
    return TimeWindow(
        start_window=start_window,
        end_window=end_window,
        use_event_end=use_event_end,
        restrict_visit=restrict_visit,
        ignore_observation_period=ignore_observation_period
    )


def continuous_observation(
    prior_days: int = 0,
    post_days: int = 0
) -> ObservationWindow:
    """
    Define continuous observation requirements around the index event.
    
    Args:
        prior_days: Days of continuous observation required before index
        post_days: Days of continuous observation required after index
        
    Returns:
        ObservationWindow object
        
    Example:
        >>> # Require 365 days of observation before index
        >>> continuous_observation(prior_days=365)
        
        >>> # Require 365 days before and 180 days after
        >>> continuous_observation(prior_days=365, post_days=180)
    """
    return ObservationWindow(
        prior_days=prior_days,
        post_days=post_days
    )


# Convenience aliases for common patterns
def anytime_before(index: str = "startDate") -> Interval:
    """Events any time before the index (no lower bound)."""
    return Interval(start=99999, end=1, index=index)


def anytime_after(index: str = "startDate") -> Interval:
    """Events any time after the index (no upper bound)."""
    return Interval(start=0, end=99999, index=index)


def same_day(index: str = "startDate") -> Interval:
    """Events on the same day as the index."""
    return Interval(start=0, end=0, index=index)


def within_days_before(days: int, index: str = "startDate") -> Interval:
    """Events within N days before the index (exclusive of index day)."""
    return Interval(start=days, end=1, index=index)


def within_days_after(days: int, index: str = "startDate") -> Interval:
    """Events within N days after the index (exclusive of index day)."""
    return Interval(start=0, end=days, index=index)
