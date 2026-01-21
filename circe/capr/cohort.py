"""
Main cohort construction functions for CohortComposer.

This module provides the primary API for building complete cohort definitions.
Modeled after OHDSI/Capr's cohort() function and related components.
"""

from typing import Optional, List, Union, Any, TYPE_CHECKING
from dataclasses import dataclass, field

from circe.capr.query import Query
from circe.capr.window import ObservationWindow, continuous_observation
from circe.capr.criteria import CriteriaGroup, Criteria
from circe.capr.attrition import AttritionRules, AttritionRule

# Import circe models for conversion
from circe.cohortdefinition import (
    CohortExpression, PrimaryCriteria, InclusionRule,
    CorelatedCriteria, Occurrence, ConditionOccurrence, DrugExposure,
    ProcedureOccurrence, Measurement, Observation, VisitOccurrence,
    VisitDetail, DeviceExposure, Specimen, Death, ObservationPeriod,
    PayerPlanPeriod, LocationRegion, ConditionEra, DrugEra, DoseEra
)
from circe.cohortdefinition.core import (
    ObservationFilter, ResultLimit, Window, WindowBound,
    NumericRange, DateOffsetStrategy, CustomEraStrategy, CollapseSettings
)
from circe.vocabulary import ConceptSet


@dataclass
class EntryEvent:
    """
    Represents the entry event (index event) for a cohort.
    
    Attributes:
        query: Domain query defining the entry event
        observation_window: Continuous observation requirements
        primary_criteria_limit: How to limit primary criteria ('First', 'All', 'Last')
        additional_criteria: Optional additional criteria to apply
    """
    query: Query
    observation_window: ObservationWindow = field(default_factory=lambda: ObservationWindow(0, 0))
    primary_criteria_limit: str = "All"
    additional_criteria: Optional[CriteriaGroup] = None


@dataclass
class ExitStrategy:
    """
    Represents the exit strategy for a cohort.
    
    Attributes:
        strategy_type: 'observation', 'date_offset', or 'custom_era'
        offset_days: Days to offset from index (for date_offset)
        offset_field: Which date to offset from ('startDate' or 'endDate')
        custom_era_gap_days: Gap days for custom era strategy
        drug_codeset_id: Concept set ID for custom drug era
        censor_events: List of queries for censoring events
    """
    strategy_type: str = "observation"  # 'observation', 'date_offset', 'custom_era'
    offset_days: int = 0
    offset_field: str = "startDate"
    custom_era_gap_days: int = 0
    drug_codeset_id: Optional[int] = None
    censor_events: List[Query] = field(default_factory=list)


@dataclass
class CohortEra:
    """
    Represents era settings for the cohort.
    
    Attributes:
        era_days: Days to collapse era (gap days)
        study_start_date: Optional study start date
        study_end_date: Optional study end date
    """
    era_days: int = 0
    study_start_date: Optional[str] = None
    study_end_date: Optional[str] = None


@dataclass
class ComposedCohort:
    """
    Intermediate representation of a composed cohort before conversion to CohortExpression.
    
    Attributes:
        title: Cohort title
        entry_event: Entry event definition
        attrition: Attrition rules
        exit: Exit strategy
        era: Era settings
        concept_sets: List of concept sets
    """
    title: Optional[str] = None
    entry_event: Optional[EntryEvent] = None
    attrition: Optional[AttritionRules] = None
    exit: Optional[ExitStrategy] = None
    era: Optional[CohortEra] = None
    concept_sets: List[ConceptSet] = field(default_factory=list)
    
    def build(self) -> CohortExpression:
        """Convert to a CohortExpression that can generate SQL."""
        return _convert_to_cohort_expression(self)


def entry(
    query: Query,
    observation_window: Union[ObservationWindow, tuple, None] = None,
    primary_criteria_limit: str = "All",
    additional_criteria: Optional[CriteriaGroup] = None
) -> EntryEvent:
    """
    Define the entry event (index event) for the cohort.
    
    Args:
        query: Domain query defining the entry event
        observation_window: Observation requirements as ObservationWindow or (prior_days, post_days)
        primary_criteria_limit: 'First', 'All', or 'Last'
        additional_criteria: Optional additional criteria to apply at entry
        
    Returns:
        EntryEvent object
        
    Example:
        >>> entry(
        ...     condition_occurrence(concept_set_id=1, first_occurrence=True),
        ...     observation_window=(365, 0),
        ...     primary_criteria_limit="First"
        ... )
    """
    # Convert tuple to ObservationWindow
    if isinstance(observation_window, tuple):
        observation_window = continuous_observation(
            prior_days=observation_window[0],
            post_days=observation_window[1] if len(observation_window) > 1 else 0
        )
    elif observation_window is None:
        observation_window = continuous_observation(0, 0)
    
    return EntryEvent(
        query=query,
        observation_window=observation_window,
        primary_criteria_limit=primary_criteria_limit,
        additional_criteria=additional_criteria
    )


def exit_strategy(
    end_strategy: str = "observation",
    offset_days: int = 0,
    offset_field: str = "startDate",
    custom_era_gap_days: int = 0,
    drug_codeset_id: Optional[int] = None,
    censor_events: Optional[List[Query]] = None
) -> ExitStrategy:
    """
    Define the exit strategy for the cohort.
    
    Args:
        end_strategy: 'observation' (end of observation), 'date_offset', or 'custom_era'
        offset_days: Days to offset from index (for date_offset strategy)
        offset_field: Which date to use for offset ('startDate' or 'endDate')
        custom_era_gap_days: Gap days for custom drug era strategy
        drug_codeset_id: Concept set ID for custom drug era
        censor_events: List of queries that trigger censoring
        
    Returns:
        ExitStrategy object
        
    Example:
        >>> # End at end of observation
        >>> exit_strategy(end_strategy="observation")
        
        >>> # End 365 days after index
        >>> exit_strategy(end_strategy="date_offset", offset_days=365)
        
        >>> # Custom drug era with 30 day gap
        >>> exit_strategy(
        ...     end_strategy="custom_era",
        ...     drug_codeset_id=2,
        ...     custom_era_gap_days=30
        ... )
    """
    return ExitStrategy(
        strategy_type=end_strategy,
        offset_days=offset_days,
        offset_field=offset_field,
        custom_era_gap_days=custom_era_gap_days,
        drug_codeset_id=drug_codeset_id,
        censor_events=censor_events or []
    )


def observation_exit() -> ExitStrategy:
    """Convenience function for observation-based exit strategy."""
    return exit_strategy(end_strategy="observation")


def date_offset_exit(days: int, from_field: str = "startDate") -> ExitStrategy:
    """Convenience function for date offset exit strategy."""
    return exit_strategy(
        end_strategy="date_offset",
        offset_days=days,
        offset_field=from_field
    )


def era(
    era_days: int = 0,
    study_start_date: Optional[str] = None,
    study_end_date: Optional[str] = None
) -> CohortEra:
    """
    Define era settings for the cohort.
    
    Args:
        era_days: Days to collapse successive cohort entries (gap days)
        study_start_date: Optional study start date (YYYY-MM-DD)
        study_end_date: Optional study end date (YYYY-MM-DD)
        
    Returns:
        CohortEra object
        
    Example:
        >>> era(era_days=0)  # No collapsing
        >>> era(era_days=30)  # Collapse entries within 30 days
    """
    return CohortEra(
        era_days=era_days,
        study_start_date=study_start_date,
        study_end_date=study_end_date
    )


def cohort(
    title: Optional[str] = None,
    entry: Optional[EntryEvent] = None,
    attrition: Optional[AttritionRules] = None,
    exit: Optional[ExitStrategy] = None,
    era: Optional[CohortEra] = None,
    concept_sets: Optional[List[ConceptSet]] = None
) -> ComposedCohort:
    """
    Create a complete cohort definition.
    
    Args:
        title: Cohort title
        entry: Entry event definition
        attrition: Attrition rules (inclusion/exclusion)
        exit: Exit strategy
        era: Era settings
        concept_sets: List of concept sets used in the cohort
        
    Returns:
        ComposedCohort object that can be converted to CohortExpression
        
    Example:
        >>> my_cohort = cohort(
        ...     title="T2DM on Metformin",
        ...     entry=entry(
        ...         drug_exposure(concept_set_id=2, first_occurrence=True),
        ...         observation_window=(365, 0)
        ...     ),
        ...     attrition=attrition(
        ...         has_t2dm=with_all(
        ...             at_least(1, condition_occurrence(1), aperture)
        ...         )
        ...     ),
        ...     concept_sets=[t2dm_cs, metformin_cs]
        ... )
        >>> 
        >>> cohort_expression = my_cohort.build()
    """
    return ComposedCohort(
        title=title,
        entry_event=entry,
        attrition=attrition,
        exit=exit,
        era=era,
        concept_sets=concept_sets or []
    )


# =============================================================================
# CONVERSION FUNCTIONS
# =============================================================================

def _convert_to_cohort_expression(composed: ComposedCohort) -> CohortExpression:
    """Convert a ComposedCohort to a CohortExpression."""
    
    # Build primary criteria
    primary_criteria = None
    if composed.entry_event:
        primary_criteria = _build_primary_criteria(composed.entry_event)
    
    # Build inclusion rules from attrition
    inclusion_rules = None
    if composed.attrition and composed.attrition.rules:
        inclusion_rules = [
            _build_inclusion_rule(rule)
            for rule in composed.attrition.rules
        ]
    
    # Build end strategy
    end_strategy = None
    censoring_criteria = None
    if composed.exit:
        end_strategy = _build_end_strategy(composed.exit)
        if composed.exit.censor_events:
            censoring_criteria = [
                _query_to_criteria(q) for q in composed.exit.censor_events
            ]
    
    # Build collapse settings from era
    collapse_settings = None
    if composed.era:
        collapse_settings = CollapseSettings(
            era_pad=composed.era.era_days
        )
    
    return CohortExpression(
        title=composed.title,
        concept_sets=composed.concept_sets,
        primary_criteria=primary_criteria,
        inclusion_rules=inclusion_rules,
        end_strategy=end_strategy,
        censoring_criteria=censoring_criteria,
        collapse_settings=collapse_settings
    )


def _build_primary_criteria(entry_event: EntryEvent) -> PrimaryCriteria:
    """Convert EntryEvent to PrimaryCriteria."""
    criteria = _query_to_criteria(entry_event.query)
    
    return PrimaryCriteria(
        criteria_list=[criteria],
        observation_window=ObservationFilter(
            prior_days=entry_event.observation_window.prior_days,
            post_days=entry_event.observation_window.post_days
        ),
        primary_limit=ResultLimit(type=entry_event.primary_criteria_limit)
    )


def _build_inclusion_rule(rule: AttritionRule) -> InclusionRule:
    """Convert AttritionRule to InclusionRule."""
    from circe.cohortdefinition.criteria import CriteriaGroup as CirceCriteriaGroup
    
    expression = None
    if rule.expression:
        expression = _build_criteria_group(rule.expression)
    
    return InclusionRule(
        name=rule.name,
        description=rule.description,
        expression=expression
    )


def _build_criteria_group(group: CriteriaGroup):
    """Convert composer CriteriaGroup to circe CriteriaGroup."""
    from circe.cohortdefinition.criteria import CriteriaGroup as CirceCriteriaGroup
    
    criteria_list = []
    for item in group.criteria_list:
        if isinstance(item, Criteria):
            criteria_list.append(_build_correlated_criteria(item))
        elif isinstance(item, CriteriaGroup):
            # Nested group - not directly supported, flatten or nest
            pass
    
    return CirceCriteriaGroup(
        type=group.group_type,
        criteria_list=criteria_list if criteria_list else None
    )


def _build_correlated_criteria(criteria: Criteria) -> CorelatedCriteria:
    """Convert composer Criteria to CorelatedCriteria."""
    from circe.cohortdefinition.core import Window, WindowBound
    
    query_criteria = _query_to_criteria(criteria.query)
    
    # Build occurrence
    occurrence_type_map = {
        'atLeast': 2,   # AT_LEAST
        'atMost': 1,    # AT_MOST
        'exactly': 0    # EXACTLY
    }
    occurrence = Occurrence(
        type=occurrence_type_map.get(criteria.occurrence_type, 2),
        count=criteria.count,
        is_distinct=criteria.is_distinct
    )
    
    # Build window from aperture
    start_window = None
    if criteria.aperture and criteria.aperture.start_window:
        interval = criteria.aperture.start_window
        start_window = Window(
            use_event_end=criteria.aperture.use_event_end,
            start=WindowBound(
                coeff=-1,
                days=interval.start
            ),
            end=WindowBound(
                coeff=1,
                days=interval.end
            )
        )
    
    return CorelatedCriteria(
        criteria=query_criteria,
        start_window=start_window,
        occurrence=occurrence,
        restrict_visit=criteria.aperture.restrict_visit if criteria.aperture else False,
        ignore_observation_period=criteria.aperture.ignore_observation_period if criteria.aperture else False
    )


def _build_end_strategy(exit_strat: ExitStrategy):
    """Convert ExitStrategy to circe end strategy."""
    if exit_strat.strategy_type == "date_offset":
        return DateOffsetStrategy(
            date_field=exit_strat.offset_field,
            offset=exit_strat.offset_days
        )
    elif exit_strat.strategy_type == "custom_era":
        return CustomEraStrategy(
            drug_codeset_id=exit_strat.drug_codeset_id,
            gap_days=exit_strat.custom_era_gap_days,
            offset=0
        )
    # Observation exit returns None (default behavior)
    return None


def _query_to_criteria(query: Query):
    """Convert a Query to the appropriate domain Criteria object."""
    
    domain_map = {
        'ConditionOccurrence': ConditionOccurrence,
        'ConditionEra': ConditionEra,
        'DrugExposure': DrugExposure,
        'DrugEra': DrugEra,
        'DoseEra': DoseEra,
        'ProcedureOccurrence': ProcedureOccurrence,
        'Measurement': Measurement,
        'Observation': Observation,
        'VisitOccurrence': VisitOccurrence,
        'VisitDetail': VisitDetail,
        'DeviceExposure': DeviceExposure,
        'Specimen': Specimen,
        'Death': Death,
        'ObservationPeriod': ObservationPeriod,
        'PayerPlanPeriod': PayerPlanPeriod,
        'LocationRegion': LocationRegion
    }
    
    criteria_class = domain_map.get(query.domain)
    if not criteria_class:
        raise ValueError(f"Unknown domain: {query.domain}")
    
    # Build kwargs from query
    kwargs = {
        'codeset_id': query.concept_set_id,
        'first': query.first_occurrence if query.first_occurrence else None
    }
    
    # Add domain-specific options
    options = query.criteria_options
    if 'age' in options:
        age = options['age']
        if isinstance(age, tuple):
            kwargs['age'] = NumericRange(value=age[0], op='gte')
        else:
            kwargs['age'] = NumericRange(value=age, op='gte')
    
    # Filter out None values
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    
    return criteria_class(**kwargs)
