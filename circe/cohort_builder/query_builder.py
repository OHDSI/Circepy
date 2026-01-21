"""
Query builder classes for the fluent API.

These classes provide chainable methods for building domain-specific queries
with time windows, occurrence counts, and filters.
"""

from typing import Optional, List, Union, Any, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from circe.cohort_builder.builder import CohortWithCriteria


@dataclass
class TimeWindow:
    """Represents a time window relative to the index event."""
    days_before: int = 0
    days_after: int = 0
    use_index_end: bool = False
    use_event_end: bool = False


@dataclass
class QueryConfig:
    """Configuration for a domain query."""
    domain: str
    concept_set_id: Optional[int] = None
    first_occurrence: bool = False
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    gender_concepts: List[int] = field(default_factory=list)
    occurrence_count: int = 1
    occurrence_type: str = "atLeast"  # atLeast, atMost, exactly
    time_window: Optional[TimeWindow] = None
    is_distinct: bool = False
    restrict_visit: bool = False
    ignore_observation_period: bool = False
    
    # Domain specific filters
    value_min: Optional[float] = None
    value_max: Optional[float] = None
    extent_min: Optional[float] = None
    extent_max: Optional[float] = None
    op: Optional[str] = None
    unit_concept_id: Optional[int] = None
    status_concepts: List[int] = field(default_factory=list)
    visit_type_concepts: List[int] = field(default_factory=list)
    provider_specialty_concepts: List[int] = field(default_factory=list)
    source_concept_set_id: Optional[int] = None
    days_supply_min: Optional[int] = None
    days_supply_max: Optional[int] = None
    quantity_min: Optional[float] = None
    quantity_max: Optional[float] = None
    era_length_min: Optional[int] = None
    era_length_max: Optional[int] = None
    dose_min: Optional[float] = None
    dose_max: Optional[float] = None
    correlated_criteria: Optional['GroupConfig'] = None


@dataclass
class CriteriaConfig:
    """Stores a configured criteria for the cohort."""
    query_config: QueryConfig
    is_exclusion: bool = False
    rule_name: Optional[str] = None


@dataclass
class GroupConfig:
    """Configuration for a group of criteria."""
    type: str = "ALL"  # ALL, ANY, AT_LEAST, AT_MOST
    count: Optional[int] = None
    criteria: List[Union[CriteriaConfig, 'GroupConfig']] = field(default_factory=list)


class BaseQuery:
    """
    Base class for domain-specific query builders.
    
    Provides common methods for all query types.
    """
    
    def __init__(
        self, 
        domain: str,
        concept_set_id: Optional[int] = None,
        parent: Optional['CohortWithCriteria'] = None,
        is_entry: bool = False,
        is_exclusion: bool = False,
        is_censor: bool = False
    ):
        self._config = QueryConfig(
            domain=domain,
            concept_set_id=concept_set_id
        )
        self._parent = parent
        self._is_entry = is_entry
        self._is_exclusion = is_exclusion
        self._is_censor = is_censor
    
    def first_occurrence(self) -> 'BaseQuery':
        """Only use the first occurrence per person."""
        self._config.first_occurrence = True
        return self
    
    def with_age(self, min_age: Optional[int] = None, max_age: Optional[int] = None) -> 'BaseQuery':
        """Filter by age at event."""
        self._config.age_min = min_age
        self._config.age_max = max_age
        return self
    
    def min_age(self, age: int) -> 'BaseQuery':
        """Require minimum age at event."""
        self._config.age_min = age
        return self
    
    def max_age(self, age: int) -> 'BaseQuery':
        """Require maximum age at event."""
        self._config.age_max = age
        return self
    
    def at_least(self, count: int) -> 'BaseQuery':
        """Require at least N occurrences."""
        self._config.occurrence_count = count
        self._config.occurrence_type = "atLeast"
        return self
    
    def at_most(self, count: int) -> 'BaseQuery':
        """Require at most N occurrences."""
        self._config.occurrence_count = count
        self._config.occurrence_type = "atMost"
        return self
    
    def exactly(self, count: int) -> 'BaseQuery':
        """Require exactly N occurrences."""
        self._config.occurrence_count = count
        self._config.occurrence_type = "exactly"
        return self
    
    def with_gender(self, *concept_ids: int) -> 'BaseQuery':
        """Filter by gender concept IDs."""
        self._config.gender_concepts.extend(concept_ids)
        return self

    def with_visit_type(self, *concept_ids: int) -> 'BaseQuery':
        """Filter by visit type concept IDs."""
        self._config.visit_type_concepts.extend(concept_ids)
        return self

    def with_provider_specialty(self, *concept_ids: int) -> 'BaseQuery':
        """Filter by provider specialty concept IDs."""
        self._config.provider_specialty_concepts.extend(concept_ids)
        return self

    def with_source_concept(self, concept_set_id: int) -> 'BaseQuery':
        """Filter by source concept set ID."""
        self._config.source_concept_set_id = concept_set_id
        return self

    def restrict_to_visit(self) -> 'BaseQuery':
        """Restrict criteria to the same visit as the index event."""
        self._config.restrict_visit = True
        return self

    def ignore_observation_period(self) -> 'BaseQuery':
        """Ignore observation period for this criteria."""
        self._config.ignore_observation_period = True
        return self

    def with_all(self) -> 'CriteriaGroupBuilder':
        """Start a correlated criteria group where ALL must match."""
        if self._config.correlated_criteria is None:
            self._config.correlated_criteria = GroupConfig(type="ALL")
        return CriteriaGroupBuilder(self, self._config.correlated_criteria)

    def with_any(self) -> 'CriteriaGroupBuilder':
        """Start a correlated criteria group where ANY must match."""
        if self._config.correlated_criteria is None:
            self._config.correlated_criteria = GroupConfig(type="ANY")
        return CriteriaGroupBuilder(self, self._config.correlated_criteria)

    def with_at_least(self, count: int) -> 'CriteriaGroupBuilder':
        """Start a correlated criteria group where at least N must match."""
        if self._config.correlated_criteria is None:
            self._config.correlated_criteria = GroupConfig(type="AT_LEAST", count=count)
        return CriteriaGroupBuilder(self, self._config.correlated_criteria)
    
    # Time window methods - return to parent after setting
    def within_days_before(self, days: int) -> 'CohortWithCriteria':
        """Events within N days before the index (excluding index day)."""
        self._config.time_window = TimeWindow(days_before=days, days_after=0)
        return self._finalize()
    
    def within_days_after(self, days: int) -> 'CohortWithCriteria':
        """Events within N days after the index (excluding index day)."""
        self._config.time_window = TimeWindow(days_before=0, days_after=days)
        return self._finalize()
    
    def within_days(self, before: int = 0, after: int = 0) -> 'CohortWithCriteria':
        """Events within a window around the index."""
        self._config.time_window = TimeWindow(days_before=before, days_after=after)
        return self._finalize()
    
    def anytime_before(self) -> 'CohortWithCriteria':
        """Events any time before the index."""
        self._config.time_window = TimeWindow(days_before=99999, days_after=0)
        return self._finalize()
    
    def anytime_after(self) -> 'CohortWithCriteria':
        """Events any time after the index."""
        self._config.time_window = TimeWindow(days_before=0, days_after=99999)
        return self._finalize()
    
    def same_day(self) -> 'CohortWithCriteria':
        """Events on the same day as the index."""
        self._config.time_window = TimeWindow(days_before=0, days_after=0)
        return self._finalize()

    def relative_to_index_end(self) -> 'BaseQuery':
        """Make the time window relative to the index event's end date."""
        if self._config.time_window:
            self._config.time_window.use_index_end = True
        else:
            self._config.time_window = TimeWindow(use_index_end=True)
        return self

    def relative_to_event_end(self) -> 'BaseQuery':
        """Make the time window relative to the criteria event's end date."""
        if self._config.time_window:
            self._config.time_window.use_event_end = True
        else:
            self._config.time_window = TimeWindow(use_event_end=True)
        return self
    
    def _finalize(self) -> 'CohortWithCriteria':
        """Add this query to the parent and return for chaining."""
        if self._parent is None:
            raise ValueError("Cannot finalize query without parent cohort")
        
        if self._is_censor:
            return self._parent._add_censor_query(self._config)
            
        return self._parent._add_query(self._config, self._is_exclusion)
    
    def _get_config(self) -> QueryConfig:
        """Get the query configuration."""
        return self._config


class ConditionQuery(BaseQuery):
    """Builder for condition occurrence queries."""
    
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("ConditionOccurrence", concept_set_id, **kwargs)
    
    def with_status(self, status_concepts: List[int]) -> 'ConditionQuery':
        """Filter by condition status."""
        self._config.status_concepts = status_concepts
        return self
    
    def inpatient_only(self) -> 'ConditionQuery':
        """Only include conditions during inpatient visits."""
        # This usually requires joining with visit, but in CIRCE it's often a VisitType filter
        return self


class DrugQuery(BaseQuery):
    """Builder for drug exposure queries."""
    
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("DrugExposure", concept_set_id, **kwargs)
    
    def with_days_supply(self, min_days: Optional[int] = None, max_days: Optional[int] = None) -> 'DrugQuery':
        """Filter by days supply."""
        self._config.days_supply_min = min_days
        self._config.days_supply_max = max_days
        return self
    
    def with_quantity(self, min_qty: Optional[float] = None, max_qty: Optional[float] = None) -> 'DrugQuery':
        """Filter by quantity."""
        self._config.quantity_min = min_qty
        self._config.quantity_max = max_qty
        return self


class DrugEraQuery(BaseQuery):
    """Builder for drug era queries."""
    
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("DrugEra", concept_set_id, **kwargs)
    
    def with_era_length(self, min_days: Optional[int] = None, max_days: Optional[int] = None) -> 'DrugEraQuery':
        """Filter by era length."""
        self._config.era_length_min = min_days
        self._config.era_length_max = max_days
        return self


class MeasurementQuery(BaseQuery):
    """Builder for measurement queries."""
    
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("Measurement", concept_set_id, **kwargs)
    
    def with_value(self, min_val: Optional[float] = None, max_val: Optional[float] = None) -> 'MeasurementQuery':
        """Filter by numeric value."""
        self._config.value_min = min_val
        self._config.value_max = max_val
        return self
    
    def above_normal(self) -> 'MeasurementQuery':
        """Only include values above normal range."""
        self._config.op = "above_normal"
        return self
    
    def below_normal(self) -> 'MeasurementQuery':
        """Only include values below normal range."""
        self._config.op = "below_normal"
        return self


class ProcedureQuery(BaseQuery):
    """Builder for procedure occurrence queries."""
    
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("ProcedureOccurrence", concept_set_id, **kwargs)


class VisitQuery(BaseQuery):
    """Builder for visit occurrence queries."""
    
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("VisitOccurrence", concept_set_id, **kwargs)
    
    def with_length(self, min_days: Optional[int] = None, max_days: Optional[int] = None) -> 'VisitQuery':
        """Filter by visit length."""
        self._config.value_min = min_days
        self._config.value_max = max_days
        return self


class ObservationQuery(BaseQuery):
    """Builder for observation queries."""
    
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("Observation", concept_set_id, **kwargs)


class DeathQuery(BaseQuery):
    """Builder for death queries."""
    
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("Death", concept_set_id, **kwargs)


class ConditionEraQuery(BaseQuery):
    """Builder for condition era queries."""
    
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("ConditionEra", concept_set_id, **kwargs)
    
    def with_era_length(self, min_days: Optional[int] = None, max_days: Optional[int] = None) -> 'ConditionEraQuery':
        """Filter by era length in days."""
        self._config.era_length_min = min_days
        self._config.era_length_max = max_days
        return self


class DeviceExposureQuery(BaseQuery):
    """Builder for device exposure queries."""
    
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("DeviceExposure", concept_set_id, **kwargs)


class SpecimenQuery(BaseQuery):
    """Builder for specimen queries."""
    
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("Specimen", concept_set_id, **kwargs)


class ObservationPeriodQuery(BaseQuery):
    """Builder for observation period queries."""
    
    def __init__(self, **kwargs):
        super().__init__("ObservationPeriod", concept_set_id=None, **kwargs)
    
    def with_length(self, min_days: Optional[int] = None, max_days: Optional[int] = None) -> 'ObservationPeriodQuery':
        """Filter by observation period length."""
        self._config.value_min = min_days
        self._config.value_max = max_days
        return self


class PayerPlanPeriodQuery(BaseQuery):
    """Builder for payer plan period queries."""
    
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("PayerPlanPeriod", concept_set_id, **kwargs)


class LocationRegionQuery(BaseQuery):
    """Builder for location/region queries."""
    
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("LocationRegion", concept_set_id, **kwargs)


class VisitDetailQuery(BaseQuery):
    """Builder for visit detail queries."""
    
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("VisitDetail", concept_set_id, **kwargs)
    
    def with_length(self, min_days: Optional[int] = None, max_days: Optional[int] = None) -> 'VisitDetailQuery':
        """Filter by visit detail length."""
        self._config.value_min = min_days
        self._config.value_max = max_days
        return self


class DoseEraQuery(BaseQuery):
    """Builder for dose era queries."""
    
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("DoseEra", concept_set_id, **kwargs)
    
    def with_dose(self, min_dose: Optional[float] = None, max_dose: Optional[float] = None) -> 'DoseEraQuery':
        """Filter by dose value."""
        self._config.dose_min = min_dose
        self._config.dose_max = max_dose
        return self


class CriteriaGroupBuilder:
    """Builder for a group of criteria (Any of, All of)."""
    
    def __init__(self, parent: Union['CriteriaGroupBuilder', 'CohortWithCriteria', 'BaseQuery'], group: GroupConfig):
        self._parent = parent
        self._group = group
    
    def _add_query(self, config: QueryConfig, is_exclusion: bool = False) -> 'CriteriaGroupBuilder':
        self._group.criteria.append(CriteriaConfig(
            query_config=config,
            is_exclusion=is_exclusion
        ))
        return self
    
    def end_group(self) -> Union['CriteriaGroupBuilder', Any]:
        """Finish adding to this group and return to the parent builder."""
        return self._parent

    def require_condition(self, concept_set_id: int) -> 'ConditionQuery':
        return ConditionQuery(concept_set_id, parent=self, is_exclusion=False)
    
    def require_drug(self, concept_set_id: int) -> 'DrugQuery':
        return DrugQuery(concept_set_id, parent=self, is_exclusion=False)
    
    def require_measurement(self, concept_set_id: int) -> 'MeasurementQuery':
        return MeasurementQuery(concept_set_id, parent=self, is_exclusion=False)
    
    def require_procedure(self, concept_set_id: int) -> 'ProcedureQuery':
        return ProcedureQuery(concept_set_id, parent=self, is_exclusion=False)
    
    def require_visit(self, concept_set_id: int) -> 'VisitQuery':
        return VisitQuery(concept_set_id, parent=self, is_exclusion=False)
    
    def exclude_condition(self, concept_set_id: int) -> 'ConditionQuery':
        return ConditionQuery(concept_set_id, parent=self, is_exclusion=True)
    
    def exclude_drug(self, concept_set_id: int) -> 'DrugQuery':
        return DrugQuery(concept_set_id, parent=self, is_exclusion=True)

    def any_of(self) -> 'CriteriaGroupBuilder':
        """Start a nested 'Any Of' group."""
        new_group = GroupConfig(type="ANY")
        self._group.criteria.append(new_group)
        return CriteriaGroupBuilder(self, new_group)

    def all_of(self) -> 'CriteriaGroupBuilder':
        """Start a nested 'All Of' group."""
        new_group = GroupConfig(type="ALL")
        self._group.criteria.append(new_group)
        return CriteriaGroupBuilder(self, new_group)

    def at_least_of(self, count: int) -> 'CriteriaGroupBuilder':
        """Start a nested 'At Least N Of' group."""
        new_group = GroupConfig(type="AT_LEAST", count=count)
        self._group.criteria.append(new_group)
        return CriteriaGroupBuilder(self, new_group)
