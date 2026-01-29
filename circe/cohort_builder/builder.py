"""
State-Based Fluent Builder for OHDSI Cohort Definitions.

This module implements a guided API where each method returns an object
with only valid next methods, making it ideal for LLM agents.

The state progression is:
    Cohort -> CohortWithEntry -> CohortWithCriteria -> CohortExpression
"""

from typing import Optional, List, Union, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass, field

from circe.cohort_builder.query_builder import (
    QueryConfig, TimeWindow, BaseQuery,
    ConditionQuery, DrugQuery, DrugEraQuery, MeasurementQuery, 
    ProcedureQuery, VisitQuery, ObservationQuery, DeathQuery,
    ConditionEraQuery, DeviceExposureQuery, SpecimenQuery,
    ObservationPeriodQuery, PayerPlanPeriodQuery, LocationRegionQuery,
    VisitDetailQuery, DoseEraQuery, CriteriaConfig, GroupConfig, CriteriaGroupBuilder
)

# Import circe models for conversion
from circe.cohortdefinition import (
    CohortExpression, PrimaryCriteria, InclusionRule,
    CorelatedCriteria, Occurrence, ConditionOccurrence, ConditionEra, DrugExposure,
    ProcedureOccurrence, Measurement, Observation, VisitOccurrence, VisitDetail,
    DeviceExposure, Death, DrugEra, DoseEra, Specimen, ObservationPeriod,
    PayerPlanPeriod, LocationRegion, DemographicCriteria
)
from circe.cohortdefinition.core import (
    ObservationFilter, ResultLimit, Window, WindowBound,
    NumericRange, DateAdjustment
)
from circe.cohortdefinition.criteria import CriteriaGroup as CirceCriteriaGroup
from circe.vocabulary import ConceptSet, Concept


@dataclass
class CohortSettings:
    """Stores cohort-wide settings like exit strategy and era logic."""
    exit_strategy_type: str = "observation"  # observation, date_offset
    exit_offset_days: int = 0
    exit_offset_field: str = "startDate"
    era_days: int = 0
    censor_queries: List[QueryConfig] = field(default_factory=list)
    
    # Custom Era Strategy
    custom_era_drug_codeset_id: Optional[int] = None
    custom_era_gap_days: int = 30
    custom_era_offset: int = 0
    custom_era_days_supply_override: Optional[int] = None
    
    # Demographics
    gender_concepts: List[int] = field(default_factory=list)
    race_concepts: List[int] = field(default_factory=list)
    ethnicity_concepts: List[int] = field(default_factory=list)
    age_min: Optional[int] = None
    age_max: Optional[int] = None


class CohortBuilder:
    """
    Starting point for building a cohort definition.
    
    Supports both context manager and fluent API patterns.
    
    Context Manager Example (Recommended):
        >>> with CohortBuilder("My Cohort") as cohort:
        ...     cohort.with_condition(1)
        ...     cohort.require_drug(2, within_days_before=30)
        >>> expression = cohort.expression  # Built CohortExpression
    
    Fluent API Example:
        >>> expression = (CohortBuilder("My Cohort")
        ...     .with_condition(1)
        ...     .require_drug(2, within_days_before=30)
        ...     .build())
    """
    
    def __init__(self, title: str = "Untitled Cohort"):
        """
        Create a new cohort builder.
        
        Args:
            title: Human-readable title for the cohort
        """
        self._title = title
        self._concept_sets: List[ConceptSet] = []
        # Context manager state
        self._state: Optional['CohortWithEntry'] = None
        self._expression: Optional[CohortExpression] = None
        self._in_context: bool = False
    
    # =========================================================================
    # CONTEXT MANAGER PROTOCOL
    # =========================================================================
    
    def __enter__(self) -> 'CohortBuilder':
        """Enter context manager mode."""
        self._in_context = True
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit context manager and auto-build the cohort."""
        self._in_context = False
        if self._state is not None:
            self._expression = self._state.build()
        return False  # Don't suppress exceptions
    
    @property
    def expression(self) -> CohortExpression:
        """
        Get the built CohortExpression.
        
        Only available after exiting the context manager.
        
        Raises:
            RuntimeError: If accessed before context exit or if no entry event defined
        """
        if self._expression is None:
            if self._in_context:
                raise RuntimeError(
                    "Cannot access 'expression' while inside the context manager. "
                    "Exit the 'with' block first."
                )
            raise RuntimeError(
                "No cohort has been built. Define at least one entry event "
                "(e.g., with_condition, with_drug) inside the context manager."
            )
        return self._expression
    
    def _ensure_state(self) -> Union['CohortWithEntry', 'CohortWithCriteria']:
        """Get or create the current state for method chaining within context."""
        if self._state is None:
            raise RuntimeError(
                "No entry event defined. Call with_condition(), with_drug(), etc. first."
            )
        return self._state
    
    def _update_state(self, new_state: Union['CohortWithEntry', 'CohortWithCriteria', None]) -> None:
        """Update internal state after a method that may change state."""
        if new_state is not None:
            self._state = new_state
    
    # =========================================================================
    # CONTEXT MANAGER DELEGATION METHODS
    # =========================================================================
    
    def first_occurrence(self) -> 'CohortBuilder':
        """Only use the first occurrence per person for entry events."""
        self._ensure_state().first_occurrence()
        return self
    
    def all_occurrences(self) -> 'CohortBuilder':
        """Use all occurrences per person."""
        self._ensure_state().all_occurrences()
        return self
    
    def with_observation_window(self, prior_days: int = 0, post_days: int = 0) -> 'CohortBuilder':
        """Set continuous observation requirements."""
        self._ensure_state().with_observation(prior_days=prior_days, post_days=post_days)
        return self
    
    def min_age(self, age: int) -> 'CohortBuilder':
        """Require minimum age at entry."""
        self._ensure_state().min_age(age)
        return self
    
    def max_age(self, age: int) -> 'CohortBuilder':
        """Require maximum age at entry."""
        self._ensure_state().max_age(age)
        return self
    
    def require_gender(self, *concept_ids: int) -> 'CohortBuilder':
        """Require specific gender concept IDs."""
        self._ensure_state().require_gender(*concept_ids)
        return self
    
    def require_race(self, *concept_ids: int) -> 'CohortBuilder':
        """Require specific race concept IDs."""
        self._ensure_state().require_race(*concept_ids)
        return self
    
    def require_ethnicity(self, *concept_ids: int) -> 'CohortBuilder':
        """Require specific ethnicity concept IDs."""
        self._ensure_state().require_ethnicity(*concept_ids)
        return self
    
    def require_age(self, min_age: Optional[int] = None, max_age: Optional[int] = None) -> 'CohortBuilder':
        """Require specific age range."""
        self._ensure_state().require_age(min_age, max_age)
        return self
    
    def require_condition(self, concept_set_id: int, **kwargs) -> 'CohortBuilder':
        """Add a required condition occurrence."""
        result = self._ensure_state().require_condition(concept_set_id, **kwargs)
        self._update_state(result)
        return self
    
    def require_drug(self, concept_set_id: int, **kwargs) -> 'CohortBuilder':
        """Add a required drug exposure."""
        result = self._ensure_state().require_drug(concept_set_id, **kwargs)
        self._update_state(result)
        return self
    
    def require_procedure(self, concept_set_id: int, **kwargs) -> 'CohortBuilder':
        """Add a required procedure occurrence."""
        result = self._ensure_state().require_procedure(concept_set_id, **kwargs)
        self._update_state(result)
        return self
    
    def require_measurement(self, concept_set_id: int, **kwargs) -> 'CohortBuilder':
        """Add a required measurement."""
        result = self._ensure_state().require_measurement(concept_set_id, **kwargs)
        self._update_state(result)
        return self
    
    def require_observation(self, concept_set_id: int, **kwargs) -> 'CohortBuilder':
        """Add a required observation."""
        result = self._ensure_state().require_observation(concept_set_id, **kwargs)
        self._update_state(result)
        return self
    
    def require_visit(self, concept_set_id: int, **kwargs) -> 'CohortBuilder':
        """Add a required visit occurrence."""
        result = self._ensure_state().require_visit(concept_set_id, **kwargs)
        self._update_state(result)
        return self
    
    def exclude_condition(self, concept_set_id: int, **kwargs) -> 'CohortBuilder':
        """Exclude patients with a condition occurrence."""
        result = self._ensure_state().exclude_condition(concept_set_id, **kwargs)
        self._update_state(result)
        return self
    
    def exclude_drug(self, concept_set_id: int, **kwargs) -> 'CohortBuilder':
        """Exclude patients with a drug exposure."""
        result = self._ensure_state().exclude_drug(concept_set_id, **kwargs)
        self._update_state(result)
        return self
    
    def exclude_procedure(self, concept_set_id: int, **kwargs) -> 'CohortBuilder':
        """Exclude patients with a procedure occurrence."""
        result = self._ensure_state().exclude_procedure(concept_set_id, **kwargs)
        self._update_state(result)
        return self
    
    def exclude_measurement(self, concept_set_id: int, **kwargs) -> 'CohortBuilder':
        """Exclude patients with a measurement."""
        result = self._ensure_state().exclude_measurement(concept_set_id, **kwargs)
        self._update_state(result)
        return self
    
    def include_rule(self, name: str) -> 'InclusionRuleContext':
        """
        Create a named inclusion rule context.
        
        Use with a nested 'with' block to group criteria:
        
            with CohortBuilder("My Cohort") as cohort:
                cohort.with_condition(1)
                
                with cohort.include_rule("Prior Treatment") as rule:
                    rule.require_drug(2, anytime_before=True)
        """
        return InclusionRuleContext(self, name)
    
    def exit_at_observation_end(self) -> 'CohortBuilder':
        """Exit cohort at the end of the observation period."""
        self._ensure_state().exit_at_observation_end()
        return self
    
    def exit_after_days(self, days: int, from_field: str = "startDate") -> 'CohortBuilder':
        """Exit cohort N days after index start/end."""
        self._ensure_state().exit_after_days(days, from_field)
        return self
    
    def collapse_era(self, days: int) -> 'CohortBuilder':
        """Set the number of gap days to collapse successive cohort entries."""
        self._ensure_state()._to_criteria().collapse_era(days)
        return self
    
    # =========================================================================
    # CONCEPT SET MANAGEMENT
    # =========================================================================
    
    def with_concept_sets(self, *concept_sets: ConceptSet) -> 'CohortBuilder':
        """Add concept sets to the cohort."""
        self._concept_sets.extend(concept_sets)
        return self
    
    # =========================================================================
    # ENTRY EVENT METHODS
    # =========================================================================
    
    def with_condition(self, concept_set_id: int, **kwargs) -> Union['CohortBuilder', 'CohortWithEntry']:
        """Set entry event to a condition occurrence."""
        query = ConditionQuery(concept_set_id, is_entry=True)
        query.apply_params(**kwargs)
        cohort = CohortWithEntry(self, query)
        query._parent = cohort
        if self._in_context:
            self._state = cohort
            return self
        return cohort

    def with_drug(self, concept_set_id: int, **kwargs) -> Union['CohortBuilder', 'CohortWithEntry']:
        """Set entry event to a drug exposure."""
        query = DrugQuery(concept_set_id, is_entry=True)
        query.apply_params(**kwargs)
        cohort = CohortWithEntry(self, query)
        query._parent = cohort
        if self._in_context:
            self._state = cohort
            return self
        return cohort

    def with_drug_era(self, concept_set_id: int, **kwargs) -> Union['CohortBuilder', 'CohortWithEntry']:
        """Set entry event to a drug era."""
        query = DrugEraQuery(concept_set_id, is_entry=True)
        query.apply_params(**kwargs)
        cohort = CohortWithEntry(self, query)
        query._parent = cohort
        if self._in_context:
            self._state = cohort
            return self
        return cohort

    def with_procedure(self, concept_set_id: int, **kwargs) -> Union['CohortBuilder', 'CohortWithEntry']:
        """Set entry event to a procedure occurrence."""
        query = ProcedureQuery(concept_set_id, is_entry=True)
        query.apply_params(**kwargs)
        cohort = CohortWithEntry(self, query)
        query._parent = cohort
        if self._in_context:
            self._state = cohort
            return self
        return cohort

    def with_measurement(self, concept_set_id: int, **kwargs) -> Union['CohortBuilder', 'CohortWithEntry']:
        """Set entry event to a measurement."""
        query = MeasurementQuery(concept_set_id, is_entry=True)
        query.apply_params(**kwargs)
        cohort = CohortWithEntry(self, query)
        query._parent = cohort
        if self._in_context:
            self._state = cohort
            return self
        return cohort

    def with_visit(self, concept_set_id: int, **kwargs) -> Union['CohortBuilder', 'CohortWithEntry']:
        """Set entry event to a visit occurrence."""
        query = VisitQuery(concept_set_id, is_entry=True)
        query.apply_params(**kwargs)
        cohort = CohortWithEntry(self, query)
        query._parent = cohort
        if self._in_context:
            self._state = cohort
            return self
        return cohort

    def with_observation(self, concept_set_id: int, **kwargs) -> Union['CohortBuilder', 'CohortWithEntry']:
        """Set entry event to an observation (with concept set)."""
        query = ObservationQuery(concept_set_id, is_entry=True)
        query.apply_params(**kwargs)
        cohort = CohortWithEntry(self, query)
        query._parent = cohort
        if self._in_context:
            self._state = cohort
            return self
        return cohort

    def with_condition_era(self, concept_set_id: int, **kwargs) -> Union['CohortBuilder', 'CohortWithEntry']:
        """Set entry event to a condition era."""
        query = ConditionEraQuery(concept_set_id, is_entry=True)
        query.apply_params(**kwargs)
        cohort = CohortWithEntry(self, query)
        query._parent = cohort
        if self._in_context:
            self._state = cohort
            return self
        return cohort

    def with_device_exposure(self, concept_set_id: int, **kwargs) -> Union['CohortBuilder', 'CohortWithEntry']:
        """Set entry event to a device exposure."""
        query = DeviceExposureQuery(concept_set_id, is_entry=True)
        query.apply_params(**kwargs)
        cohort = CohortWithEntry(self, query)
        query._parent = cohort
        if self._in_context:
            self._state = cohort
            return self
        return cohort

    def with_specimen(self, concept_set_id: int, **kwargs) -> Union['CohortBuilder', 'CohortWithEntry']:
        """Set entry event to a specimen."""
        query = SpecimenQuery(concept_set_id, is_entry=True)
        query.apply_params(**kwargs)
        cohort = CohortWithEntry(self, query)
        query._parent = cohort
        if self._in_context:
            self._state = cohort
            return self
        return cohort

    def with_death(self) -> Union['CohortBuilder', 'CohortWithEntry']:
        """Set entry event to death."""
        query = DeathQuery(is_entry=True)
        cohort = CohortWithEntry(self, query)
        if self._in_context:
            self._state = cohort
            return self
        return cohort
    
    def with_observation_period(self) -> Union['CohortBuilder', 'CohortWithEntry']:
        """Set entry event to an observation period."""
        query = ObservationPeriodQuery(is_entry=True)
        cohort = CohortWithEntry(self, query)
        if self._in_context:
            self._state = cohort
            return self
        return cohort
    
    def with_payer_plan_period(self, concept_set_id: int, **kwargs) -> Union['CohortBuilder', 'CohortWithEntry']:
        """Set entry event to a payer plan period."""
        query = PayerPlanPeriodQuery(concept_set_id, is_entry=True)
        query.apply_params(**kwargs)
        cohort = CohortWithEntry(self, query)
        query._parent = cohort
        if self._in_context:
            self._state = cohort
            return self
        return cohort

    def with_location_region(self, concept_set_id: int) -> Union['CohortBuilder', 'CohortWithEntry']:
        """Set entry event to a location/region."""
        query = LocationRegionQuery(concept_set_id, is_entry=True)
        cohort = CohortWithEntry(self, query)
        if self._in_context:
            self._state = cohort
            return self
        return cohort
    
    def with_visit_detail(self, concept_set_id: int) -> Union['CohortBuilder', 'CohortWithEntry']:
        """Set entry event to a visit detail."""
        query = VisitDetailQuery(concept_set_id, is_entry=True)
        cohort = CohortWithEntry(self, query)
        if self._in_context:
            self._state = cohort
            return self
        return cohort
    
    def with_dose_era(self, concept_set_id: int) -> Union['CohortBuilder', 'CohortWithEntry']:
        """Set entry event to a dose era."""
        query = DoseEraQuery(concept_set_id, is_entry=True)
        cohort = CohortWithEntry(self, query)
        if self._in_context:
            self._state = cohort
            return self
        return cohort


class InclusionRuleContext:
    """
    Context manager for named inclusion rules.
    
    Provides a clean way to group criteria under a named rule for attrition tracking.
    """
    
    def __init__(self, builder: CohortBuilder, name: str):
        self._builder = builder
        self._name = name
    
    def __enter__(self) -> 'InclusionRuleContext':
        """Enter the inclusion rule context."""
        state = self._builder._ensure_state()
        new_state = state.begin_rule(self._name)
        self._builder._update_state(new_state)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit the inclusion rule context."""
        state = self._builder._ensure_state()
        new_state = state.end_rule()
        self._builder._update_state(new_state)
        return False
    
    def require_condition(self, concept_set_id: int, **kwargs) -> 'InclusionRuleContext':
        """Add a required condition occurrence to this rule."""
        result = self._builder._ensure_state().require_condition(concept_set_id, **kwargs)
        self._builder._update_state(result)
        return self
    
    def require_drug(self, concept_set_id: int, **kwargs) -> 'InclusionRuleContext':
        """Add a required drug exposure to this rule."""
        result = self._builder._ensure_state().require_drug(concept_set_id, **kwargs)
        self._builder._update_state(result)
        return self
    
    def require_procedure(self, concept_set_id: int, **kwargs) -> 'InclusionRuleContext':
        """Add a required procedure occurrence to this rule."""
        result = self._builder._ensure_state().require_procedure(concept_set_id, **kwargs)
        self._builder._update_state(result)
        return self
    
    def require_measurement(self, concept_set_id: int, **kwargs) -> 'InclusionRuleContext':
        """Add a required measurement to this rule."""
        result = self._builder._ensure_state().require_measurement(concept_set_id, **kwargs)
        self._builder._update_state(result)
        return self
    
    def require_observation(self, concept_set_id: int, **kwargs) -> 'InclusionRuleContext':
        """Add a required observation to this rule."""
        result = self._builder._ensure_state().require_observation(concept_set_id, **kwargs)
        self._builder._update_state(result)
        return self
    
    def require_visit(self, concept_set_id: int, **kwargs) -> 'InclusionRuleContext':
        """Add a required visit occurrence to this rule."""
        result = self._builder._ensure_state().require_visit(concept_set_id, **kwargs)
        self._builder._update_state(result)
        return self
    
    def exclude_condition(self, concept_set_id: int, **kwargs) -> 'InclusionRuleContext':
        """Exclude patients with a condition occurrence."""
        result = self._builder._ensure_state().exclude_condition(concept_set_id, **kwargs)
        self._builder._update_state(result)
        return self
    
    def exclude_drug(self, concept_set_id: int, **kwargs) -> 'InclusionRuleContext':
        """Exclude patients with a drug exposure."""
        result = self._builder._ensure_state().exclude_drug(concept_set_id, **kwargs)
        self._builder._update_state(result)
        return self
    
    def exclude_procedure(self, concept_set_id: int, **kwargs) -> 'InclusionRuleContext':
        """Exclude patients with a procedure occurrence."""
        result = self._builder._ensure_state().exclude_procedure(concept_set_id, **kwargs)
        self._builder._update_state(result)
        return self
    
    def exclude_measurement(self, concept_set_id: int, **kwargs) -> 'InclusionRuleContext':
        """Exclude patients with a measurement."""
        result = self._builder._ensure_state().exclude_measurement(concept_set_id, **kwargs)
        self._builder._update_state(result)
        return self


class CohortWithEntry:
    """
    Cohort state after entry event is defined.
    
    Available methods:
    - first_occurrence(): Only use first occurrence per person
    - with_observation(): Set observation window
    - require_*(): Add inclusion criteria
    - exclude_*(): Add exclusion criteria  
    - build(): Finalize and create CohortExpression
    """
    
    def __init__(self, parent: CohortBuilder, entry_query: BaseQuery):
        self._parent = parent
        self._entry_queries = [entry_query]
        self._prior_observation_days = 0
        self._post_observation_days = 0
        self._limit = "All"
        self._qualified_limit = "First"
        self._expression_limit = "All"
        self._settings = CohortSettings()

    def _add_query(self, config: QueryConfig, is_exclusion: bool = False) -> 'CohortWithCriteria':
        """Delegate query addition to the criteria state."""
        return self._to_criteria()._add_query(config, is_exclusion)

    def _add_censor_query(self, config: QueryConfig) -> 'CohortWithCriteria':
        """Delegate censor query addition to the criteria state."""
        return self._to_criteria()._add_censor_query(config)
    
    def or_with_condition(self, concept_set_id: int, **kwargs) -> 'CohortWithEntry':
        query = ConditionQuery(concept_set_id, is_entry=True, parent=self)
        query.apply_params(**kwargs)
        self._entry_queries.append(query)
        return self


    def or_with_drug(self, concept_set_id: int, **kwargs) -> 'CohortWithEntry':
        query = DrugQuery(concept_set_id, is_entry=True, parent=self)
        query.apply_params(**kwargs)
        self._entry_queries.append(query)
        return self


    def or_with_procedure(self, concept_set_id: int, **kwargs) -> 'CohortWithEntry':
        query = ProcedureQuery(concept_set_id, is_entry=True, parent=self)
        query.apply_params(**kwargs)
        self._entry_queries.append(query)
        return self


    def or_with_measurement(self, concept_set_id: int, **kwargs) -> 'CohortWithEntry':
        query = MeasurementQuery(concept_set_id, is_entry=True, parent=self)
        query.apply_params(**kwargs)
        self._entry_queries.append(query)
        return self


    def or_with_visit(self, concept_set_id: int, **kwargs) -> 'CohortWithEntry':
        query = VisitQuery(concept_set_id, is_entry=True, parent=self)
        query.apply_params(**kwargs)
        self._entry_queries.append(query)
        return self


    def with_qualified_limit(self, limit: str) -> 'CohortWithEntry':
        """Set the qualified limit (First, Last, All)."""
        self._qualified_limit = limit
        return self

    def with_expression_limit(self, limit: str) -> 'CohortWithEntry':
        """Set the expression limit (First, Last, All)."""
        self._expression_limit = limit
        return self

    # Entry query filters (delegate to the last added query)







    def with_all(self) -> 'CriteriaGroupBuilder':
        """Start a correlated criteria group for the last added entry."""
        return self._entry_queries[-1].with_all()

    def with_any(self) -> 'CriteriaGroupBuilder':
        """Start a correlated criteria group for the last added entry."""
        return self._entry_queries[-1].with_any()



    def first_occurrence(self) -> 'CohortWithEntry':
        """Only use the first occurrence per person for entry events."""
        for q in self._entry_queries:
            q._get_config().first_occurrence = True
        self._limit = "First"
        return self
    
    def all_occurrences(self) -> 'CohortWithEntry':
        """Use all occurrences per person."""
        self._limit = "All"
        for q in self._entry_queries:
            q._get_config().first_occurrence = False
        return self
    
    def with_observation(
        self, 
        prior_days: int = 0, 
        post_days: int = 0
    ) -> 'CohortWithEntry':
        """
        Set continuous observation requirements.
        
        Args:
            prior_days: Days of observation required before index
            post_days: Days of observation required after index
            
        Returns:
            Self for chaining
        """
        self._prior_observation_days = prior_days
        self._post_observation_days = post_days
        return self
    
    def min_age(self, age: int) -> 'CohortWithEntry':
        """Require minimum age at entry for all entry events."""
        for q in self._entry_queries:
            q._get_config().age_min = age
        return self
    
    def max_age(self, age: int) -> 'CohortWithEntry':
        """Require maximum age at entry for all entry events."""
        for q in self._entry_queries:
            q._get_config().age_max = age
        return self
    
    def require_gender(self, *concept_ids: int) -> 'CohortWithEntry':
        """Require specific gender concept IDs."""
        self._settings.gender_concepts.extend(concept_ids)
        return self
    
    def require_race(self, *concept_ids: int) -> 'CohortWithEntry':
        """Require specific race concept IDs."""
        self._settings.race_concepts.extend(concept_ids)
        return self
    
    def require_ethnicity(self, *concept_ids: int) -> 'CohortWithEntry':
        """Require specific ethnicity concept IDs."""
        self._settings.ethnicity_concepts.extend(concept_ids)
        return self
    
    def require_age(self, min_age: Optional[int] = None, max_age: Optional[int] = None) -> 'CohortWithEntry':
        """Require specific age range."""
        self._settings.age_min = min_age
        self._settings.age_max = max_age
        return self
    
    def begin_rule(self, name: str) -> 'CohortWithCriteria':
        """Start a new named inclusion rule."""
        return self._to_criteria().begin_rule(name)

    def end_rule(self) -> 'CohortWithCriteria':
        """Finish the current inclusion rule."""
        return self._to_criteria().end_rule()
    
    # Transition to CohortWithCriteria
    def require_condition(self, concept_set_id: int, **kwargs) -> Union['ConditionQuery', 'CohortWithCriteria']:
        """require_condition (Supports both chaining and parameter-based API)"""
        query = ConditionQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def require_drug(self, concept_set_id: int, **kwargs) -> Union['DrugQuery', 'CohortWithCriteria']:
        """require_drug (Supports both chaining and parameter-based API)"""
        query = DrugQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query



    def censor_on_condition(self, concept_set_id: int, **kwargs) -> Union['ConditionQuery', 'CohortWithCriteria']:
        """censor_on_condition (Supports both chaining and parameter-based API)"""
        query = ConditionQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=True)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query



    def censor_on_drug(self, concept_set_id: int, **kwargs) -> Union['DrugQuery', 'CohortWithCriteria']:
        """censor_on_drug (Supports both chaining and parameter-based API)"""
        query = DrugQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=True)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query



    def censor_on_procedure(self, concept_set_id: int, **kwargs) -> Union['ProcedureQuery', 'CohortWithCriteria']:
        """censor_on_procedure (Supports both chaining and parameter-based API)"""
        query = ProcedureQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=True)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query



    def censor_on_measurement(self, concept_set_id: int, **kwargs) -> Union['MeasurementQuery', 'CohortWithCriteria']:
        """censor_on_measurement (Supports both chaining and parameter-based API)"""
        query = MeasurementQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=True)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query



    def censor_on_observation(self, concept_set_id: int) -> ObservationQuery:
        """Censor if an observation occurs."""
        return self._to_criteria().censor_on_observation(concept_set_id)

    def censor_on_visit(self, concept_set_id: int) -> VisitQuery:
        """Censor if a visit occurs."""
        return self._to_criteria().censor_on_visit(concept_set_id)

    def censor_on_death(self, concept_set_id: Optional[int] = None) -> DeathQuery:
        """Censor on death."""
        return self._to_criteria().censor_on_death(concept_set_id)
    
    def require_measurement(self, concept_set_id: int, **kwargs) -> Union['MeasurementQuery', 'CohortWithCriteria']:
        """require_measurement (Supports both chaining and parameter-based API)"""
        query = MeasurementQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def exclude_condition(self, concept_set_id: int, **kwargs) -> Union['ConditionQuery', 'CohortWithCriteria']:
        """exclude_condition (Supports both chaining and parameter-based API)"""
        query = ConditionQuery(concept_set_id, parent=self, is_exclusion=True, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def exclude_drug(self, concept_set_id: int, **kwargs) -> Union['DrugQuery', 'CohortWithCriteria']:
        """exclude_drug (Supports both chaining and parameter-based API)"""
        query = DrugQuery(concept_set_id, parent=self, is_exclusion=True, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def require_condition_era(self, concept_set_id: int, **kwargs) -> Union['ConditionEraQuery', 'CohortWithCriteria']:
        """require_condition_era (Supports both chaining and parameter-based API)"""
        query = ConditionEraQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def require_device_exposure(self, concept_set_id: int, **kwargs) -> Union['DeviceExposureQuery', 'CohortWithCriteria']:
        """require_device_exposure (Supports both chaining and parameter-based API)"""
        query = DeviceExposureQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def require_specimen(self, concept_set_id: int, **kwargs) -> Union['SpecimenQuery', 'CohortWithCriteria']:
        """require_specimen (Supports both chaining and parameter-based API)"""
        query = SpecimenQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def require_visit_detail(self, concept_set_id: int, **kwargs) -> Union['VisitDetailQuery', 'CohortWithCriteria']:
        """require_visit_detail (Supports both chaining and parameter-based API)"""
        query = VisitDetailQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def require_dose_era(self, concept_set_id: int, **kwargs) -> Union['DoseEraQuery', 'CohortWithCriteria']:
        """require_dose_era (Supports both chaining and parameter-based API)"""
        query = DoseEraQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def require_payer_plan_period(self, concept_set_id: int, **kwargs) -> Union['PayerPlanPeriodQuery', 'CohortWithCriteria']:
        """require_payer_plan_period (Supports both chaining and parameter-based API)"""
        query = PayerPlanPeriodQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def exclude_condition_era(self, concept_set_id: int, **kwargs) -> Union['ConditionEraQuery', 'CohortWithCriteria']:
        """exclude_condition_era (Supports both chaining and parameter-based API)"""
        query = ConditionEraQuery(concept_set_id, parent=self, is_exclusion=True, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def exclude_device_exposure(self, concept_set_id: int, **kwargs) -> Union['DeviceExposureQuery', 'CohortWithCriteria']:
        """exclude_device_exposure (Supports both chaining and parameter-based API)"""
        query = DeviceExposureQuery(concept_set_id, parent=self, is_exclusion=True, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def exclude_specimen(self, concept_set_id: int, **kwargs) -> Union['SpecimenQuery', 'CohortWithCriteria']:
        """exclude_specimen (Supports both chaining and parameter-based API)"""
        query = SpecimenQuery(concept_set_id, parent=self, is_exclusion=True, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def exclude_visit_detail(self, concept_set_id: int, **kwargs) -> Union['VisitDetailQuery', 'CohortWithCriteria']:
        """exclude_visit_detail (Supports both chaining and parameter-based API)"""
        query = VisitDetailQuery(concept_set_id, parent=self, is_exclusion=True, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def exclude_dose_era(self, concept_set_id: int, **kwargs) -> Union['DoseEraQuery', 'CohortWithCriteria']:
        """exclude_dose_era (Supports both chaining and parameter-based API)"""
        query = DoseEraQuery(concept_set_id, parent=self, is_exclusion=True, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def exclude_payer_plan_period(self, concept_set_id: int, **kwargs) -> Union['PayerPlanPeriodQuery', 'CohortWithCriteria']:
        """exclude_payer_plan_period (Supports both chaining and parameter-based API)"""
        query = PayerPlanPeriodQuery(concept_set_id, parent=self, is_exclusion=True, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query



    # Exit strategies
    def exit_at_observation_end(self) -> 'CohortWithCriteria':
        """Exit cohort at the end of the observation period."""
        return self._to_criteria().exit_at_observation_end()

    def exit_after_days(self, days: int, from_field: str = "startDate") -> 'CohortWithCriteria':
        """Exit cohort N days after index start/end."""
        return self._to_criteria().exit_after_days(days, from_field)

    def exit_at_era_end(self, concept_set_id: int, gap_days: int = 30, offset: int = 0, supply_override: Optional[int] = None) -> 'CohortWithCriteria':
        """Exit cohort at the end of a drug era."""
        return self._to_criteria().exit_at_era_end(concept_set_id, gap_days, offset, supply_override)

    def any_of(self) -> 'CriteriaGroupBuilder':
        """Start an 'Any Of' group in the current rule."""
        return self._to_criteria().any_of()

    def all_of(self) -> 'CriteriaGroupBuilder':
        """Start an 'All Of' group in the current rule."""
        return self._to_criteria().all_of()

    def at_least_of(self, count: int) -> 'CriteriaGroupBuilder':
        """Start an 'At Least N Of' group in the current rule."""
        return self._to_criteria().at_least_of(count)
    
    # Collection method delegates
    def require_any_of(self, **kwargs) -> 'CohortWithCriteria':
        """Delegate to CohortWithCriteria. See CohortWithCriteria.require_any_of for documentation."""
        return self._to_criteria().require_any_of(**kwargs)
    
    def require_all_of(self, **kwargs) -> 'CohortWithCriteria':
        """Delegate to CohortWithCriteria. See CohortWithCriteria.require_all_of for documentation."""
        return self._to_criteria().require_all_of(**kwargs)
    
    def require_at_least_of(self, count: int, **kwargs) -> 'CohortWithCriteria':
        """Delegate to CohortWithCriteria. See CohortWithCriteria.require_at_least_of for documentation."""
        return self._to_criteria().require_at_least_of(count, **kwargs)
    
    def exclude_any_of(self, **kwargs) -> 'CohortWithCriteria':
        """Delegate to CohortWithCriteria. See CohortWithCriteria.exclude_any_of for documentation."""
        return self._to_criteria().exclude_any_of(**kwargs)
    
    def _to_criteria(self) -> 'CohortWithCriteria':
        """Transition to criteria state."""
        return CohortWithCriteria(
            parent=self._parent,
            entry_configs=[q._get_config() for q in self._entry_queries],
            prior_observation=self._prior_observation_days,
            post_observation=self._post_observation_days,
            limit=self._limit,
            qualified_limit=self._qualified_limit,
            expression_limit=self._expression_limit,
            settings=self._settings
        )
    
    def build(self) -> CohortExpression:
        """Build the final CohortExpression."""
        return self._to_criteria().build()


class CohortWithCriteria:
    """
    Cohort state after criteria have been added.
    
    Available methods:
    - require_*(): Add more inclusion criteria  
    - exclude_*(): Add more exclusion criteria
    - exit_at_*(): Set cohort exit strategy
    - collapse_era(): Set era gap days
    - censor_with_*(): Add censoring events
    - build(): Finalize and create CohortExpression
    """
    
    def __init__(
        self,
        parent: CohortBuilder,
        entry_configs: List[QueryConfig],
        prior_observation: int = 0,
        post_observation: int = 0,
        limit: str = "All",
        qualified_limit: str = "First",
        expression_limit: str = "All",
        settings: Optional[CohortSettings] = None
    ):
        self._parent = parent
        self._entry_configs = entry_configs
        self._prior_observation = prior_observation
        self._post_observation = post_observation
        self._limit = limit
        self._qualified_limit = qualified_limit
        self._expression_limit = expression_limit
        self._rules = [{"name": "Inclusion Criteria", "group": GroupConfig(type="ALL")}]
        self._settings = settings or CohortSettings()
    
    def begin_rule(self, name: str) -> 'CohortWithCriteria':
        """
        Start a new named inclusion rule.
        
        Subsequent criteria will be added to this rule until build() or 
        another begin_rule() is called. This is useful for attrition tracking.
        """
        self._rules.append({"name": name, "group": GroupConfig(type="ALL")})
        return self

    def end_rule(self) -> 'CohortWithCriteria':
        """
        Finish the current inclusion rule.
        
        This method is provided to balance .begin_rule() and make blocks more explicit.
        """
        return self

    def _add_query(self, config: QueryConfig, is_exclusion: bool = False) -> 'CohortWithCriteria':
        """Add a configured query to the current rule's criteria list."""
        self._rules[-1]["group"].criteria.append(CriteriaConfig(
            query_config=config,
            is_exclusion=is_exclusion
        ))
        return self

    def _add_censor_query(self, config: QueryConfig) -> 'CohortWithCriteria':
        """Add a configured query to the censoring criteria list."""
        self._settings.censor_queries.append(config)
        return self

    def any_of(self) -> 'CriteriaGroupBuilder':
        """Start an 'Any Of' group in the current rule."""
        group = GroupConfig(type="ANY")
        self._rules[-1]["group"].criteria.append(group)
        return CriteriaGroupBuilder(self, group)

    def all_of(self) -> 'CriteriaGroupBuilder':
        """Start an 'All Of' group in the current rule."""
        group = GroupConfig(type="ALL")
        self._rules[-1]["group"].criteria.append(group)
        return CriteriaGroupBuilder(self, group)

    def at_least_of(self, count: int) -> 'CriteriaGroupBuilder':
        """Start an 'At Least N Of' group in the current rule."""
        group = GroupConfig(type="AT_LEAST", count=count)
        self._rules[-1]["group"].criteria.append(group)
        return CriteriaGroupBuilder(self, group)
    
    # Collection methods for simplified group creation
    def require_any_of(
        self,
        condition_ids: Optional[List[int]] = None,
        drug_ids: Optional[List[int]] = None,
        drug_era_ids: Optional[List[int]] = None,
        procedure_ids: Optional[List[int]] = None,
        measurement_ids: Optional[List[int]] = None,
        observation_ids: Optional[List[int]] = None,
        visit_ids: Optional[List[int]] = None
    ) -> 'CohortWithCriteria':
        """
        Require ANY of the specified criteria (OR logic).
        
        This is a shortcut for creating an ANY group with multiple criteria
        without manually chaining .any_of()...end_group().
        
        Args:
            condition_ids: List of condition concept set IDs
            drug_ids: List of drug concept set IDs
            drug_era_ids: List of drug era concept set IDs
            procedure_ids: List of procedure concept set IDs
            measurement_ids: List of measurement concept set IDs
            observation_ids: List of observation concept set IDs
            visit_ids: List of visit concept set IDs
        
        Returns:
            Self for continued chaining
        
        Example:
            >>> cohort.require_any_of(drug_ids=[1, 2, 3])
            # Patient must have at least one of Drug 1, 2, or 3
        """
        group = GroupConfig(type="ANY")
        
        if condition_ids:
            for cid in condition_ids:
                config = QueryConfig(domain="ConditionOccurrence", concept_set_id=cid)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)  # Default: all time
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=False))
        
        if drug_ids:
            for did in drug_ids:
                config = QueryConfig(domain="DrugExposure", concept_set_id=did)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=False))
        
        if drug_era_ids:
            for deid in drug_era_ids:
                config = QueryConfig(domain="DrugEra", concept_set_id=deid)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=False))
        
        if procedure_ids:
            for pid in procedure_ids:
                config = QueryConfig(domain="ProcedureOccurrence", concept_set_id=pid)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=False))
        
        if measurement_ids:
            for mid in measurement_ids:
                config = QueryConfig(domain="Measurement", concept_set_id=mid)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=False))
        
        if observation_ids:
            for oid in observation_ids:
                config = QueryConfig(domain="Observation", concept_set_id=oid)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=False))
        
        if visit_ids:
            for vid in visit_ids:
                config = QueryConfig(domain="VisitOccurrence", concept_set_id=vid)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=False))
        
        if group.criteria:  # Only add if we have at least one criterion
            self._rules[-1]["group"].criteria.append(group)
        
        return self
    
    def require_all_of(
        self,
        condition_ids: Optional[List[int]] = None,
        drug_ids: Optional[List[int]] = None,
        drug_era_ids: Optional[List[int]] = None,
        procedure_ids: Optional[List[int]] = None,
        measurement_ids: Optional[List[int]] = None,
        observation_ids: Optional[List[int]] = None,
        visit_ids: Optional[List[int]] = None
    ) -> 'CohortWithCriteria':
        """
        Require ALL of the specified criteria (AND logic).
        
        This is a shortcut for creating an ALL group with multiple criteria.
        
        Args:
            condition_ids: List of condition concept set IDs
            drug_ids: List of drug concept set IDs
            drug_era_ids: List of drug era concept set IDs
            procedure_ids: List of procedure concept set IDs
            measurement_ids: List of measurement concept set IDs
            observation_ids: List of observation concept set IDs
            visit_ids: List of visit concept set IDs
        
        Returns:
            Self for continued chaining
        
        Example:
            >>> cohort.require_all_of(drug_ids=[1, 2], procedure_ids=[10])
            # Patient must have Drug 1 AND Drug 2 AND Procedure 10
        """
        group = GroupConfig(type="ALL")
        
        if condition_ids:
            for cid in condition_ids:
                config = QueryConfig(domain="ConditionOccurrence", concept_set_id=cid)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=False))
        
        if drug_ids:
            for did in drug_ids:
                config = QueryConfig(domain="DrugExposure", concept_set_id=did)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=False))
        
        if drug_era_ids:
            for deid in drug_era_ids:
                config = QueryConfig(domain="DrugEra", concept_set_id=deid)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=False))
        
        if procedure_ids:
            for pid in procedure_ids:
                config = QueryConfig(domain="ProcedureOccurrence", concept_set_id=pid)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=False))
        
        if measurement_ids:
            for mid in measurement_ids:
                config = QueryConfig(domain="Measurement", concept_set_id=mid)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=False))
        
        if observation_ids:
            for oid in observation_ids:
                config = QueryConfig(domain="Observation", concept_set_id=oid)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=False))
        
        if visit_ids:
            for vid in visit_ids:
                config = QueryConfig(domain="VisitOccurrence", concept_set_id=vid)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=False))
        
        if group.criteria:
            self._rules[-1]["group"].criteria.append(group)
        
        return self
    
    def require_at_least_of(
        self,
        count: int,
        condition_ids: Optional[List[int]] = None,
        drug_ids: Optional[List[int]] = None,
        drug_era_ids: Optional[List[int]] = None,
        procedure_ids: Optional[List[int]] = None,
        measurement_ids: Optional[List[int]] = None,
        observation_ids: Optional[List[int]] = None,
        visit_ids: Optional[List[int]] = None
    ) -> 'CohortWithCriteria':
        """
        Require at least N of the specified criteria.
        
        This is a shortcut for creating an AT_LEAST group.
        
        Args:
            count: Minimum number of criteria that must be met
            condition_ids: List of condition concept set IDs
            drug_ids: List of drug concept set IDs
            drug_era_ids: List of drug era concept set IDs
            procedure_ids: List of procedure concept set IDs
            measurement_ids: List of measurement concept set IDs
            observation_ids: List of observation concept set IDs
            visit_ids: List of visit concept set IDs
        
        Returns:
            Self for continued chaining
        
        Example:
            >>> cohort.require_at_least_of(2, procedure_ids=[10, 11, 12])
            # Patient must have at least 2 of the 3 procedures
        """
        group = GroupConfig(type="AT_LEAST", count=count)
        
        if condition_ids:
            for cid in condition_ids:
                config = QueryConfig(domain="ConditionOccurrence", concept_set_id=cid)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=False))
        
        if drug_ids:
            for did in drug_ids:
                config = QueryConfig(domain="DrugExposure", concept_set_id=did)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=False))
        
        if drug_era_ids:
            for deid in drug_era_ids:
                config = QueryConfig(domain="DrugEra", concept_set_id=deid)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=False))
        
        if procedure_ids:
            for pid in procedure_ids:
                config = QueryConfig(domain="ProcedureOccurrence", concept_set_id=pid)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=False))
        
        if measurement_ids:
            for mid in measurement_ids:
                config = QueryConfig(domain="Measurement", concept_set_id=mid)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=False))
        
        if observation_ids:
            for oid in observation_ids:
                config = QueryConfig(domain="Observation", concept_set_id=oid)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=False))
        
        if visit_ids:
            for vid in visit_ids:
                config = QueryConfig(domain="VisitOccurrence", concept_set_id=vid)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=False))
        
        if group.criteria:
            self._rules[-1]["group"].criteria.append(group)
        
        return self
    
    def exclude_any_of(
        self,
        condition_ids: Optional[List[int]] = None,
        drug_ids: Optional[List[int]] = None,
        drug_era_ids: Optional[List[int]] = None,
        procedure_ids: Optional[List[int]] = None,
        measurement_ids: Optional[List[int]] = None,
        observation_ids: Optional[List[int]] = None,
        visit_ids: Optional[List[int]] = None
    ) -> 'CohortWithCriteria':
        """
        Exclude if ANY of the specified criteria are present.
        
        This creates exclusion criteria with OR logic.
        
        Args:
            condition_ids: List of condition concept set IDs to exclude
            drug_ids: List of drug concept set IDs to exclude
            drug_era_ids: List of drug era concept set IDs to exclude
            procedure_ids: List of procedure concept set IDs to exclude
            measurement_ids: List of measurement concept set IDs to exclude
            observation_ids: List of observation concept set IDs to exclude
            visit_ids: List of visit concept set IDs to exclude
        
        Returns:
            Self for continued chaining
        
        Example:
            >>> cohort.exclude_any_of(drug_ids=[3, 4])
            # Exclude patients who have Drug 3 OR Drug 4
        """
        group = GroupConfig(type="ANY")
        
        if condition_ids:
            for cid in condition_ids:
                config = QueryConfig(domain="ConditionOccurrence", concept_set_id=cid)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=True))
        
        if drug_ids:
            for did in drug_ids:
                config = QueryConfig(domain="DrugExposure", concept_set_id=did)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=True))
        
        if drug_era_ids:
            for deid in drug_era_ids:
                config = QueryConfig(domain="DrugEra", concept_set_id=deid)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=True))
        
        if procedure_ids:
            for pid in procedure_ids:
                config = QueryConfig(domain="ProcedureOccurrence", concept_set_id=pid)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=True))
        
        if measurement_ids:
            for mid in measurement_ids:
                config = QueryConfig(domain="Measurement", concept_set_id=mid)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=True))
        
        if observation_ids:
            for oid in observation_ids:
                config = QueryConfig(domain="Observation", concept_set_id=oid)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=True))
        
        if visit_ids:
            for vid in visit_ids:
                config = QueryConfig(domain="VisitOccurrence", concept_set_id=vid)
                config.time_window = TimeWindow(days_before=99999, days_after=99999)
                group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=True))
        
        if group.criteria:
            self._rules[-1]["group"].criteria.append(group)
        
        return self
    
    # Inclusion methods - return query builders with self as parent
    def require_condition(self, concept_set_id: int, **kwargs) -> Union['ConditionQuery', 'CohortWithCriteria']:
        """require_condition (Supports both chaining and parameter-based API)"""
        query = ConditionQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def require_drug(self, concept_set_id: int, **kwargs) -> Union['DrugQuery', 'CohortWithCriteria']:
        """require_drug (Supports both chaining and parameter-based API)"""
        query = DrugQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def require_drug_era(self, concept_set_id: int, **kwargs) -> Union['DrugEraQuery', 'CohortWithCriteria']:
        """require_drug_era (Supports both chaining and parameter-based API)"""
        query = DrugEraQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def require_measurement(self, concept_set_id: int, **kwargs) -> Union['MeasurementQuery', 'CohortWithCriteria']:
        """require_measurement (Supports both chaining and parameter-based API)"""
        query = MeasurementQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def require_procedure(self, concept_set_id: int, **kwargs) -> Union['ProcedureQuery', 'CohortWithCriteria']:
        """require_procedure (Supports both chaining and parameter-based API)"""
        query = ProcedureQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def require_visit(self, concept_set_id: int, **kwargs) -> Union['VisitQuery', 'CohortWithCriteria']:
        """require_visit (Supports both chaining and parameter-based API)"""
        query = VisitQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def require_observation(self, concept_set_id: int, **kwargs) -> Union['ObservationQuery', 'CohortWithCriteria']:
        """require_observation (Supports both chaining and parameter-based API)"""
        query = ObservationQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query



    def require_visit_detail(self, concept_set_id: int, **kwargs) -> Union['VisitDetailQuery', 'CohortWithCriteria']:
        """require_visit_detail (Supports both chaining and parameter-based API)"""
        query = VisitDetailQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def require_death(self, **kwargs) -> Union['DeathQuery', 'CohortWithCriteria']:
        """require_death (Supports both chaining and parameter-based API)"""
        query = DeathQuery(parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def require_device(self, concept_set_id: int, **kwargs) -> Union['DeviceExposureQuery', 'CohortWithCriteria']:



        """require_device (Supports both chaining and parameter-based API)"""



        query = DeviceExposureQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)



        if kwargs:



            query.apply_params(**kwargs)



            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):



                return query._finalize()



        return query



    def require_specimen(self, concept_set_id: int, **kwargs) -> Union['SpecimenQuery', 'CohortWithCriteria']:
        """require_specimen (Supports both chaining and parameter-based API)"""
        query = SpecimenQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query



    def require_drug_era(self, concept_set_id: int, **kwargs) -> Union['DrugEraQuery', 'CohortWithCriteria']:
        """require_drug_era (Supports both chaining and parameter-based API)"""
        query = DrugEraQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query



    def require_condition_era(self, concept_set_id: int, **kwargs) -> Union['ConditionEraQuery', 'CohortWithCriteria']:
        """require_condition_era (Supports both chaining and parameter-based API)"""
        query = ConditionEraQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query



    def require_dose_era(self, concept_set_id: int, **kwargs) -> Union['DoseEraQuery', 'CohortWithCriteria']:
        """require_dose_era (Supports both chaining and parameter-based API)"""
        query = DoseEraQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def exclude_condition(self, concept_set_id: int, **kwargs) -> Union['ConditionQuery', 'CohortWithCriteria']:
        """exclude_condition (Supports both chaining and parameter-based API)"""
        query = ConditionQuery(concept_set_id, parent=self, is_exclusion=True, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def exclude_drug(self, concept_set_id: int, **kwargs) -> Union['DrugQuery', 'CohortWithCriteria']:
        """exclude_drug (Supports both chaining and parameter-based API)"""
        query = DrugQuery(concept_set_id, parent=self, is_exclusion=True, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def exclude_drug_era(self, concept_set_id: int, **kwargs) -> Union['DrugEraQuery', 'CohortWithCriteria']:



        """exclude_drug_era (Supports both chaining and parameter-based API)"""



        query = DrugEraQuery(concept_set_id, parent=self, is_exclusion=True, is_censor=False)



        if kwargs:



            query.apply_params(**kwargs)



            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):



                return query._finalize()



        return query


    def exclude_measurement(self, concept_set_id: int, **kwargs) -> Union['MeasurementQuery', 'CohortWithCriteria']:



        """exclude_measurement (Supports both chaining and parameter-based API)"""



        query = MeasurementQuery(concept_set_id, parent=self, is_exclusion=True, is_censor=False)



        if kwargs:



            query.apply_params(**kwargs)



            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):



                return query._finalize()



        return query


    def exclude_procedure(self, concept_set_id: int, **kwargs) -> Union['ProcedureQuery', 'CohortWithCriteria']:



        """exclude_procedure (Supports both chaining and parameter-based API)"""



        query = ProcedureQuery(concept_set_id, parent=self, is_exclusion=True, is_censor=False)



        if kwargs:



            query.apply_params(**kwargs)



            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):



                return query._finalize()



        return query


    def require_condition_era(self, concept_set_id: int, **kwargs) -> Union['ConditionEraQuery', 'CohortWithCriteria']:
        """require_condition_era (Supports both chaining and parameter-based API)"""
        query = ConditionEraQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def exclude_condition_era(self, concept_set_id: int, **kwargs) -> Union['ConditionEraQuery', 'CohortWithCriteria']:
        """exclude_condition_era (Supports both chaining and parameter-based API)"""
        query = ConditionEraQuery(concept_set_id, parent=self, is_exclusion=True, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def require_device_exposure(self, concept_set_id: int, **kwargs) -> Union['DeviceExposureQuery', 'CohortWithCriteria']:
        """require_device_exposure (Supports both chaining and parameter-based API)"""
        query = DeviceExposureQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def exclude_device_exposure(self, concept_set_id: int, **kwargs) -> Union['DeviceExposureQuery', 'CohortWithCriteria']:
        """exclude_device_exposure (Supports both chaining and parameter-based API)"""
        query = DeviceExposureQuery(concept_set_id, parent=self, is_exclusion=True, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def require_specimen(self, concept_set_id: int, **kwargs) -> Union['SpecimenQuery', 'CohortWithCriteria']:
        """require_specimen (Supports both chaining and parameter-based API)"""
        query = SpecimenQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def exclude_specimen(self, concept_set_id: int, **kwargs) -> Union['SpecimenQuery', 'CohortWithCriteria']:
        """exclude_specimen (Supports both chaining and parameter-based API)"""
        query = SpecimenQuery(concept_set_id, parent=self, is_exclusion=True, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def require_observation_period(self, **kwargs) -> Union['ObservationPeriodQuery', 'CohortWithCriteria']:
        """require_observation_period (Supports both chaining and parameter-based API)"""
        query = ObservationPeriodQuery(parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query

    def exclude_observation_period(self, **kwargs) -> Union['ObservationPeriodQuery', 'CohortWithCriteria']:


        """exclude_observation_period (Supports both chaining and parameter-based API)"""


        query = ObservationPeriodQuery(parent=self, is_exclusion=True, is_censor=False)


        if kwargs:


            query.apply_params(**kwargs)


            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):


                return query._finalize()


        return query

    def require_payer_plan_period(self, concept_set_id: int, **kwargs) -> Union['PayerPlanPeriodQuery', 'CohortWithCriteria']:
        """require_payer_plan_period (Supports both chaining and parameter-based API)"""
        query = PayerPlanPeriodQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def exclude_payer_plan_period(self, concept_set_id: int, **kwargs) -> Union['PayerPlanPeriodQuery', 'CohortWithCriteria']:
        """exclude_payer_plan_period (Supports both chaining and parameter-based API)"""
        query = PayerPlanPeriodQuery(concept_set_id, parent=self, is_exclusion=True, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def require_visit_detail(self, concept_set_id: int, **kwargs) -> Union['VisitDetailQuery', 'CohortWithCriteria']:
        """require_visit_detail (Supports both chaining and parameter-based API)"""
        query = VisitDetailQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query



    def require_death(self, **kwargs) -> Union['DeathQuery', 'CohortWithCriteria']:
        """require_death (Supports both chaining and parameter-based API)"""
        query = DeathQuery(parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def require_device(self, concept_set_id: int, **kwargs) -> Union['DeviceExposureQuery', 'CohortWithCriteria']:



        """require_device (Supports both chaining and parameter-based API)"""



        query = DeviceExposureQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)



        if kwargs:



            query.apply_params(**kwargs)



            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):



                return query._finalize()



        return query



    def require_specimen(self, concept_set_id: int, **kwargs) -> Union['SpecimenQuery', 'CohortWithCriteria']:
        """require_specimen (Supports both chaining and parameter-based API)"""
        query = SpecimenQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query



    def require_drug_era(self, concept_set_id: int, **kwargs) -> Union['DrugEraQuery', 'CohortWithCriteria']:
        """require_drug_era (Supports both chaining and parameter-based API)"""
        query = DrugEraQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query



    def require_condition_era(self, concept_set_id: int, **kwargs) -> Union['ConditionEraQuery', 'CohortWithCriteria']:
        """require_condition_era (Supports both chaining and parameter-based API)"""
        query = ConditionEraQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query



    def require_dose_era(self, concept_set_id: int, **kwargs) -> Union['DoseEraQuery', 'CohortWithCriteria']:
        """require_dose_era (Supports both chaining and parameter-based API)"""
        query = DoseEraQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def exclude_visit_detail(self, concept_set_id: int, **kwargs) -> Union['VisitDetailQuery', 'CohortWithCriteria']:
        """exclude_visit_detail (Supports both chaining and parameter-based API)"""
        query = VisitDetailQuery(concept_set_id, parent=self, is_exclusion=True, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def require_dose_era(self, concept_set_id: int, **kwargs) -> Union['DoseEraQuery', 'CohortWithCriteria']:
        """require_dose_era (Supports both chaining and parameter-based API)"""
        query = DoseEraQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def exclude_dose_era(self, concept_set_id: int, **kwargs) -> Union['DoseEraQuery', 'CohortWithCriteria']:
        """exclude_dose_era (Supports both chaining and parameter-based API)"""
        query = DoseEraQuery(concept_set_id, parent=self, is_exclusion=True, is_censor=False)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query


    def exit_at_observation_end(self) -> 'CohortWithCriteria':
        """Exit cohort at the end of the observation period."""
        self._settings.exit_strategy_type = "observation"
        return self
    
    def exit_after_days(self, days: int, from_field: str = "startDate") -> 'CohortWithCriteria':
        """Exit cohort N days after index start/end."""
        self._settings.exit_strategy_type = "date_offset"
        self._settings.exit_offset_days = days
        self._settings.exit_offset_field = from_field
        return self

    def exit_at_era_end(self, concept_set_id: int, gap_days: int = 30, offset: int = 0, supply_override: Optional[int] = None) -> 'CohortWithCriteria':
        """Exit cohort at the end of a drug era."""
        self._settings.exit_strategy_type = "custom_era"
        self._settings.custom_era_drug_codeset_id = concept_set_id
        self._settings.custom_era_gap_days = gap_days
        self._settings.custom_era_offset = offset
        self._settings.custom_era_days_supply_override = supply_override
        return self

    # Censoring methods
    def censor_on_condition(self, concept_set_id: int, **kwargs) -> Union['ConditionQuery', 'CohortWithCriteria']:
        """censor_on_condition (Supports both chaining and parameter-based API)"""
        query = ConditionQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=True)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query



    def censor_on_drug(self, concept_set_id: int, **kwargs) -> Union['DrugQuery', 'CohortWithCriteria']:
        """censor_on_drug (Supports both chaining and parameter-based API)"""
        query = DrugQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=True)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query



    def censor_on_procedure(self, concept_set_id: int, **kwargs) -> Union['ProcedureQuery', 'CohortWithCriteria']:
        """censor_on_procedure (Supports both chaining and parameter-based API)"""
        query = ProcedureQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=True)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query



    def censor_on_measurement(self, concept_set_id: int, **kwargs) -> Union['MeasurementQuery', 'CohortWithCriteria']:
        """censor_on_measurement (Supports both chaining and parameter-based API)"""
        query = MeasurementQuery(concept_set_id, parent=self, is_exclusion=False, is_censor=True)
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']):
                return query._finalize()
        return query



    def censor_on_observation(self, concept_set_id: int) -> ObservationQuery:
        """Censor if an observation occurs."""
        return ObservationQuery(concept_set_id, parent=self, is_censor=True)

    def censor_on_visit(self, concept_set_id: int) -> VisitQuery:
        """Censor if a visit occurs."""
        return VisitQuery(concept_set_id, parent=self, is_censor=True)

    def censor_on_death(self, concept_set_id: Optional[int] = None) -> DeathQuery:
        """Censor on death."""
        return DeathQuery(concept_set_id, parent=self, is_censor=True)

    def censor_on_device_exposure(self, concept_set_id: int) -> DeviceExposureQuery:
        """Censor if a device exposure occurs."""
        return DeviceExposureQuery(concept_set_id, parent=self, is_censor=True)
    
    def collapse_era(self, days: int) -> 'CohortWithCriteria':
        """Set the number of gap days to collapse successive cohort entries."""
        self._settings.era_days = days
        return self

    def require_gender(self, *concept_ids: int) -> 'CohortWithCriteria':
        """Require specific gender concept IDs."""
        self._settings.gender_concepts.extend(concept_ids)
        return self
    
    def require_race(self, *concept_ids: int) -> 'CohortWithCriteria':
        """Require specific race concept IDs."""
        self._settings.race_concepts.extend(concept_ids)
        return self
    
    def require_ethnicity(self, *concept_ids: int) -> 'CohortWithCriteria':
        """Require specific ethnicity concept IDs."""
        self._settings.ethnicity_concepts.extend(concept_ids)
        return self
    
    def require_age(self, min_age: Optional[int] = None, max_age: Optional[int] = None) -> 'CohortWithCriteria':
        """Require specific age range."""
        self._settings.age_min = min_age
        self._settings.age_max = max_age
        return self
    
    def build(self) -> CohortExpression:
        """
        Build the final CohortExpression.
        
        Returns:
            CohortExpression ready for SQL generation
        """
        return _build_cohort_expression(
            title=self._parent._title,
            concept_sets=self._parent._concept_sets,
            entry_configs=self._entry_configs,
            prior_observation=self._prior_observation,
            post_observation=self._post_observation,
            limit=self._limit,
            qualified_limit=self._qualified_limit,
            expression_limit=self._expression_limit,
            rules=self._rules,
            settings=self._settings
        )


# =============================================================================
# CONVERSION FUNCTIONS
# =============================================================================

def _build_cohort_expression(
    title: str,
    concept_sets: List[ConceptSet],
    entry_configs: List[QueryConfig],
    prior_observation: int,
    post_observation: int,
    limit: str,
    qualified_limit: str,
    expression_limit: str,
    rules: List[Dict[str, Any]],
    settings: CohortSettings
) -> CohortExpression:
    """Build a CohortExpression from the builder state."""
    
    # Build primary criteria
    entry_criteria_list = [_config_to_criteria(cfg) for cfg in entry_configs]
    primary_criteria = PrimaryCriteria(
        criteria_list=entry_criteria_list,
        observation_window=ObservationFilter(
            prior_days=prior_observation,
            post_days=post_observation
        ),
        primary_criteria_limit=ResultLimit(type=limit)
    )
    
    # Build inclusion rules from rules
    inclusion_rules = []
    
    # Build demographic rule FIRST if needed
    if settings.gender_concepts or settings.race_concepts or settings.ethnicity_concepts or settings.age_min is not None or settings.age_max is not None:
        demographic = DemographicCriteria()
        if settings.gender_concepts:
            demographic.gender = [Concept(concept_id=c, concept_name="Gender") for c in settings.gender_concepts]
        if settings.race_concepts:
            demographic.race = [Concept(concept_id=c, concept_name="Race") for c in settings.race_concepts]
        if settings.ethnicity_concepts:
            demographic.ethnicity = [Concept(concept_id=c, concept_name="Ethnicity") for c in settings.ethnicity_concepts]
        
        if settings.age_min is not None or settings.age_max is not None:
            op = 'bt' if (settings.age_min is not None and settings.age_max is not None) else ('gte' if settings.age_min is not None else 'lte')
            demographic.age = NumericRange(value=settings.age_min, extent=settings.age_max, op=op)

        inclusion_rules.append(InclusionRule(
            name="Demographic Criteria",
            expression=CirceCriteriaGroup(
                type="ALL",
                demographic_criteria_list=[demographic]
            )
        ))
    
    # Then add named rules from builder
    for rule_data in rules:
        rule_name = rule_data["name"]
        root_group = rule_data["group"]
        
        if not root_group.criteria:
            continue
        
        # If the root group has exactly ONE child and that child is a group (not a criteria),
        # unwrap it and use it directly as the expression
        if (len(root_group.criteria) == 1 and 
            isinstance(root_group.criteria[0], GroupConfig)):
            # Use the nested group directly
            expression = _build_criteria_group(root_group.criteria[0])
        else:
            # Use the root group as-is
            expression = _build_criteria_group(root_group)
            
        inclusion_rules.append(InclusionRule(
            name=rule_name,
            expression=expression
        ))
    
    # Build end strategy
    end_strategy = None
    if settings.exit_strategy_type == "date_offset":
        from circe.cohortdefinition.core import DateOffsetStrategy
        end_strategy = DateOffsetStrategy(
            date_field=settings.exit_offset_field,
            offset=settings.exit_offset_days
        )
    elif settings.exit_strategy_type == "custom_era":
        from circe.cohortdefinition.core import CustomEraStrategy
        end_strategy = CustomEraStrategy(
            drug_codeset_id=settings.custom_era_drug_codeset_id,
            gap_days=settings.custom_era_gap_days,
            offset=settings.custom_era_offset,
            days_supply_override=settings.custom_era_days_supply_override
        )
    
    # Build collapse settings
    from circe.cohortdefinition.core import CollapseSettings
    collapse_settings = CollapseSettings(era_pad=settings.era_days)
    
    # Build censoring criteria
    censoring_criteria = []
    for cq in settings.censor_queries:
        censoring_criteria.append(_config_to_criteria(cq))

    return CohortExpression(
        title=title,
        concept_sets=concept_sets,
        primary_criteria=primary_criteria,
        inclusion_rules=inclusion_rules,
        end_strategy=end_strategy,
        collapse_settings=collapse_settings,
        censoring_criteria=censoring_criteria,
        qualified_limit=ResultLimit(type=qualified_limit),
        expression_limit=ResultLimit(type=expression_limit)
    )


def _config_to_criteria(config: QueryConfig):
    """Convert a QueryConfig to a domain criteria object."""
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
        'ObservationPeriod': ObservationPeriod,
        'PayerPlanPeriod': PayerPlanPeriod,
        'LocationRegion': LocationRegion,
        'Death': Death
    }
    
    criteria_class = domain_map.get(config.domain)
    if not criteria_class:
        raise ValueError(f"Unknown domain: {config.domain}")
    
    kwargs = {
        'codeset_id': config.concept_set_id,
        'first': config.first_occurrence if config.first_occurrence else None
    }
    
    if config.age_min is not None or config.age_max is not None:
        op = 'bt' if (config.age_min is not None and config.age_max is not None) else ('gte' if config.age_min is not None else 'lte')
        kwargs['age'] = NumericRange(value=config.age_min, extent=config.age_max, op=op)

    # Map domain-specific filters
    if config.domain == 'Measurement':
        if config.value_min is not None or config.value_max is not None:
            op = 'bt' if (config.value_min is not None and config.value_max is not None) else ('gte' if config.value_min is not None else 'lte')
            kwargs['value_as_number'] = NumericRange(value=config.value_min, extent=config.value_max, op=op)
        # Phase 2: Measurement-specific modifiers
        if config.measurement_operator_concepts:
            kwargs['operator'] = [Concept(concept_id=c, concept_name="Operator") for c in config.measurement_operator_concepts]
        if config.range_low_ratio_min is not None or config.range_low_ratio_max is not None:
            op = 'bt' if (config.range_low_ratio_min and config.range_low_ratio_max) else ('gte' if config.range_low_ratio_min else 'lte')
            kwargs['range_low_ratio'] = NumericRange(value=config.range_low_ratio_min, extent=config.range_low_ratio_max, op=op)
        if config.range_high_ratio_min is not None or config.range_high_ratio_max is not None:
            op = 'bt' if (config.range_high_ratio_min and config.range_high_ratio_max) else ('gte' if config.range_high_ratio_min else 'lte')
            kwargs['range_high_ratio'] = NumericRange(value=config.range_high_ratio_min, extent=config.range_high_ratio_max, op=op)
    
    if config.domain == 'DrugExposure':
        if config.days_supply_min is not None or config.days_supply_max is not None:
            op = 'bt' if (config.days_supply_min is not None and config.days_supply_max is not None) else ('gte' if config.days_supply_min is not None else 'lte')
            kwargs['days_supply'] = NumericRange(value=config.days_supply_min, extent=config.days_supply_max, op=op)
        if config.quantity_min is not None or config.quantity_max is not None:
            op = 'bt' if (config.quantity_min is not None and config.quantity_max is not None) else ('gte' if config.quantity_min is not None else 'lte')
            kwargs['quantity'] = NumericRange(value=config.quantity_min, extent=config.quantity_max, op=op)
        # Phase 2: Drug-specific modifiers
        if config.drug_route_concepts:
            kwargs['route_concept'] = [Concept(concept_id=c, concept_name="Route") for c in config.drug_route_concepts]
        if config.refills_min is not None or config.refills_max is not None:
            op = 'bt' if (config.refills_min and config.refills_max) else ('gte' if config.refills_min else 'lte')
            kwargs['refills'] = NumericRange(value=config.refills_min, extent=config.refills_max, op=op)
        if config.dose_min is not None or config.dose_max is not None:
            op = 'bt' if (config.dose_min and config.dose_max) else ('gte' if config.dose_min else 'lte')
            kwargs['effective_drug_dose'] = NumericRange(value=config.dose_min, extent=config.dose_max, op=op)
            
    if config.domain == 'Measurement':
        if config.unit_concepts:
            kwargs['unit'] = [Concept(concept_id=c, concept_name="Unit") for c in config.unit_concepts]
        if config.abnormal is not None:
            kwargs['abnormal'] = config.abnormal
        if config.range_low_min is not None or config.range_low_max is not None:
            op = 'bt' if (config.range_low_min is not None and config.range_low_max is not None) else ('gte' if config.range_low_min is not None else 'lte')
            kwargs['range_low'] = NumericRange(value=config.range_low_min, extent=config.range_low_max, op=op)
        if config.range_high_min is not None or config.range_high_max is not None:
            op = 'bt' if (config.range_high_min is not None and config.range_high_max is not None) else ('gte' if config.range_high_min is not None else 'lte')
            kwargs['range_high'] = NumericRange(value=config.range_high_min, extent=config.range_high_max, op=op)
        if config.value_as_concept_concepts:
            kwargs['value_as_concept'] = [Concept(concept_id=c, concept_name="Value") for c in config.value_as_concept_concepts]

    if config.domain in ['DrugEra', 'ConditionEra']:
        if config.era_length_min is not None or config.era_length_max is not None:
            op = 'bt' if (config.era_length_min is not None and config.era_length_max is not None) else ('gte' if config.era_length_min is not None else 'lte')
            kwargs['era_length'] = NumericRange(value=config.era_length_min, extent=config.era_length_max, op=op)
        if config.value_min is not None or config.value_max is not None:
            op = 'bt' if (config.value_min is not None and config.value_max is not None) else ('gte' if config.value_min is not None else 'lte')
            kwargs['occurrence_count'] = NumericRange(value=config.value_min, extent=config.value_max, op=op)
        if config.domain == 'DrugEra' and (config.extent_min is not None or config.extent_max is not None):
            op = 'bt' if (config.extent_min is not None and config.extent_max is not None) else ('gte' if config.extent_min is not None else 'lte')
            kwargs['gap_days'] = NumericRange(value=config.extent_min, extent=config.extent_max, op=op)

    if config.domain == 'DoseEra':
        if config.dose_min is not None or config.dose_max is not None:
            op = 'bt' if (config.dose_min is not None and config.dose_max is not None) else ('gte' if config.dose_min is not None else 'lte')
            kwargs['dose_value'] = NumericRange(value=config.dose_min, extent=config.dose_max, op=op)
        if config.era_length_min is not None or config.era_length_max is not None:
            op = 'bt' if (config.era_length_min is not None and config.era_length_max is not None) else ('gte' if config.era_length_min is not None else 'lte')
            kwargs['era_length'] = NumericRange(value=config.era_length_min, extent=config.era_length_max, op=op)

    # Phase 2: Procedure-specific modifiers
    if config.domain == 'ProcedureOccurrence':
        if config.procedure_modifier_concepts:
            kwargs['modifier'] = [Concept(concept_id=c, concept_name="Modifier") for c in config.procedure_modifier_concepts]
        if config.quantity_min is not None or config.quantity_max is not None:
            op = 'bt' if (config.quantity_min and config.quantity_max) else ('gte' if config.quantity_min else 'lte')
            kwargs['quantity'] = NumericRange(value=config.quantity_min, extent=config.quantity_max, op=op)
    
    if config.domain in ['VisitOccurrence', 'VisitDetail', 'ObservationPeriod']:
        if config.value_min is not None or config.value_max is not None:
            op = 'bt' if (config.value_min is not None and config.value_max is not None) else ('gte' if config.value_min is not None else 'lte')
            if config.domain == 'VisitOccurrence':
                kwargs['visit_length'] = NumericRange(value=config.value_min, extent=config.value_max, op=op)
            elif config.domain == 'VisitDetail':
                kwargs['visit_detail_length'] = NumericRange(value=config.value_min, extent=config.value_max, op=op)
            elif config.domain == 'ObservationPeriod':
                kwargs['period_length'] = NumericRange(value=config.value_min, extent=config.value_max, op=op)
        
        # Phase 2: Visit-specific modifiers (outside value range check)
        if config.domain == 'VisitOccurrence':
            if config.place_of_service_concepts:
                kwargs['place_of_service'] = [Concept(concept_id=c, concept_name="Place of Service") for c in config.place_of_service_concepts]

    # Phase 2: Observation-specific modifiers
    if config.domain == 'Observation':
        if config.qualifier_concepts:
            kwargs['qualifier'] = [Concept(concept_id=c, concept_name="Qualifier") for c in config.qualifier_concepts]
        if config.value_as_string:
            kwargs['value_as_string'] = config.value_as_string

    # Map common filters
    if config.gender_concepts:
        kwargs['gender'] = [Concept(concept_id=c, concept_name="Gender") for c in config.gender_concepts]
    
    if config.visit_type_concepts:
        kwargs['visit_type'] = [Concept(concept_id=c, concept_name="Visit Type") for c in config.visit_type_concepts]

    if config.condition_type_concepts:
        kwargs['condition_type'] = [Concept(concept_id=c, concept_name="Condition Type") for c in config.condition_type_concepts]

    if config.drug_type_concepts:
        kwargs['drug_type'] = [Concept(concept_id=c, concept_name="Drug Type") for c in config.drug_type_concepts]

    if config.procedure_type_concepts:
        kwargs['procedure_type'] = [Concept(concept_id=c, concept_name="Procedure Type") for c in config.procedure_type_concepts]

    if config.measurement_type_concepts:
        kwargs['measurement_type'] = [Concept(concept_id=c, concept_name="Measurement Type") for c in config.measurement_type_concepts]

    if config.observation_type_concepts:
        kwargs['observation_type'] = [Concept(concept_id=c, concept_name="Observation Type") for c in config.observation_type_concepts]

    if config.device_type_concepts:
        kwargs['device_type'] = [Concept(concept_id=c, concept_name="Device Type") for c in config.device_type_concepts]

    if config.provider_specialty_concepts:
        kwargs['provider_specialty'] = [Concept(concept_id=c, concept_name="Provider Specialty") for c in config.provider_specialty_concepts]

    if config.source_concept_set_id is not None:
        source_field_map = {
            'ConditionOccurrence': 'condition_source_concept',
            'DrugExposure': 'drug_source_concept',
            'ProcedureOccurrence': 'procedure_source_concept',
            'Measurement': 'measurement_source_concept',
            'Observation': 'observation_source_concept',
            'DeviceExposure': 'device_source_concept',
            'Specimen': 'specimen_source_concept',
            'Death': 'death_source_concept',
            'VisitOccurrence': 'visit_source_concept',
            'VisitDetail': 'visit_detail_source_concept'
        }
        source_field = source_field_map.get(config.domain)
        if source_field:
            kwargs[source_field] = config.source_concept_set_id
    
    # Filter out None values
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    
    criteria_obj = criteria_class(**kwargs)
    
    # Add correlated criteria if present
    if config.correlated_criteria:
        criteria_obj.correlated_criteria = _build_criteria_group(config.correlated_criteria)
        
    # Add date adjustment if present
    if config.start_date_offset != 0 or config.end_date_offset != 0:
        criteria_obj.date_adjustment = DateAdjustment(
            start_offset=config.start_date_offset,
            end_offset=config.end_date_offset,
            start_with=config.start_date_with,
            end_with=config.end_date_with
        )
        
    return criteria_obj


def _build_criteria_group(group_cfg: GroupConfig) -> CirceCriteriaGroup:
    """Recursively build a CirceCriteriaGroup from GroupConfig."""
    criteria_list = []
    groups = []
    
    for item in group_cfg.criteria:
        if isinstance(item, CriteriaConfig):
            cc = _build_correlated_criteria(item)
            criteria_list.append(cc)
        elif isinstance(item, GroupConfig):
            groups.append(_build_criteria_group(item))
            
    return CirceCriteriaGroup(
        type=group_cfg.type,
        count=group_cfg.count,
        criteria_list=criteria_list,
        groups=groups
    )


def _build_correlated_criteria(criteria_cfg: CriteriaConfig) -> CorelatedCriteria:
    """Convert a CriteriaConfig to a CorelatedCriteria."""
    config = criteria_cfg.query_config
    query_criteria = _config_to_criteria(config)
    
    # Build occurrence
    if criteria_cfg.is_exclusion:
        occurrence = Occurrence(type=0, count=0, is_distinct=False)  # exactly 0
    else:
        type_map = {"exactly": 0, "atMost": 1, "atLeast": 2}
        occ_type = type_map.get(config.occurrence_type, 2)
        occurrence = Occurrence(
            type=occ_type, 
            count=config.occurrence_count,
            is_distinct=config.is_distinct
        )
    
    # Build window
    start_window = None
    if config.time_window:
        tw = config.time_window
        start_window = Window(
            use_index_end=tw.use_index_end,
            use_event_end=tw.use_event_end,
            start=WindowBound(coeff=-1, days=tw.days_before),
            end=WindowBound(coeff=1, days=tw.days_after)
        )
    
    return CorelatedCriteria(
        criteria=query_criteria,
        start_window=start_window,
        occurrence=occurrence,
        restrict_visit=config.restrict_visit,
        ignore_observation_period=config.ignore_observation_period
    )
