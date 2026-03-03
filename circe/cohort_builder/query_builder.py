"""
Query builder classes for the fluent API.

These classes provide configuration for domain-specific queries
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
    unit_concepts: List[int] = field(default_factory=list)
    abnormal: Optional[bool] = None
    range_low_min: Optional[float] = None
    range_low_max: Optional[float] = None
    range_high_min: Optional[float] = None
    range_high_max: Optional[float] = None
    
    # Date Adjustment
    start_date_offset: int = 0
    end_date_offset: int = 0
    start_date_with: str = "START_DATE"
    end_date_with: str = "END_DATE"
    
    status_concepts: List[int] = field(default_factory=list)
    visit_type_concepts: List[int] = field(default_factory=list)
    condition_type_concepts: List[int] = field(default_factory=list)
    drug_type_concepts: List[int] = field(default_factory=list)
    procedure_type_concepts: List[int] = field(default_factory=list)
    measurement_type_concepts: List[int] = field(default_factory=list)
    observation_type_concepts: List[int] = field(default_factory=list)
    device_type_concepts: List[int] = field(default_factory=list)
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

    # Measurement specific
    value_as_concept_concepts: List[int] = field(default_factory=list)
    measurement_operator_concepts: List[int] = field(default_factory=list)
    range_low_ratio_min: Optional[float] = None
    range_low_ratio_max: Optional[float] = None
    range_high_ratio_min: Optional[float] = None
    range_high_ratio_max: Optional[float] = None
    
    # Procedure specific
    procedure_modifier_concepts: List[int] = field(default_factory=list)
    
    # Drug specific
    drug_route_concepts: List[int] = field(default_factory=list)
    refills_min: Optional[int] = None
    refills_max: Optional[int] = None
    
    # Visit specific
    admitted_from_concepts: List[int] = field(default_factory=list)
    discharged_to_concepts: List[int] = field(default_factory=list)
    place_of_service_concepts: List[int] = field(default_factory=list)
    
    # Observation specific
    qualifier_concepts: List[int] = field(default_factory=list)
    value_as_string: Optional[str] = None
    
    # Extension-specific fields (populated by auto-generated query classes)
    extra_fields: dict = field(default_factory=dict)


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
    """
    
    def __init__(
        self, 
        domain: str,
        concept_set_id: Optional[int] = None,
        parent: Optional[Union['CohortWithCriteria', 'CriteriaGroupBuilder']] = None,
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

    def apply_params(self, **kwargs) -> 'BaseQuery':
        """Batch apply parameters to the query configuration."""
        # Occurrence counting
        if 'at_least' in kwargs:
            self._config.occurrence_count = kwargs['at_least']
            self._config.occurrence_type = "atLeast"
        elif 'at_most' in kwargs:
            self._config.occurrence_count = kwargs['at_most']
            self._config.occurrence_type = "atMost"
        elif 'exactly' in kwargs:
            self._config.occurrence_count = kwargs['exactly']
            self._config.occurrence_type = "exactly"
            
        if 'distinct' in kwargs:
            self._config.is_distinct = kwargs['distinct']
            
        # Age
        if 'age_min' in kwargs:
            self._config.age_min = kwargs['age_min']
        if 'age_max' in kwargs:
            self._config.age_max = kwargs['age_max']
            
        # Time Windows
        if 'anytime_before' in kwargs and kwargs['anytime_before']:
            self._config.time_window = TimeWindow(days_before=99999, days_after=0)
        elif 'anytime_after' in kwargs and kwargs['anytime_after']:
            self._config.time_window = TimeWindow(days_before=0, days_after=99999)
        elif 'within_days_before' in kwargs:
            self._config.time_window = TimeWindow(days_before=kwargs['within_days_before'], days_after=0)
        elif 'within_days_after' in kwargs:
            self._config.time_window = TimeWindow(days_before=0, days_after=kwargs['within_days_after'])
        elif 'within_days' in kwargs:
            if isinstance(kwargs['within_days'], tuple):
                before, after = kwargs['within_days']
                self._config.time_window = TimeWindow(days_before=before, days_after=after)
        elif 'same_day' in kwargs and kwargs['same_day']:
            self._config.time_window = TimeWindow(days_before=0, days_after=0)
        elif 'during_event' in kwargs and kwargs['during_event']:
            self._config.time_window = TimeWindow(days_before=0, days_after=0, use_index_end=True)
        elif 'before_event_end' in kwargs:
            self._config.time_window = TimeWindow(days_before=kwargs['before_event_end'], days_after=0, use_index_end=True)
            
        if 'relative_to_index_end' in kwargs and kwargs['relative_to_index_end']:
            if self._config.time_window:
                self._config.time_window.use_index_end = True
            else:
                self._config.time_window = TimeWindow(use_index_end=True)
                
        if 'relative_to_event_end' in kwargs and kwargs['relative_to_event_end']:
            if self._config.time_window:
                self._config.time_window.use_event_end = True
            else:
                self._config.time_window = TimeWindow(use_event_end=True)

        # Common Modifiers
        if 'restrict_visit' in kwargs:
            self._config.restrict_visit = kwargs['restrict_visit']
        if 'ignore_observation_period' in kwargs:
            self._config.ignore_observation_period = kwargs['ignore_observation_period']
        if 'first_occurrence' in kwargs:
            self._config.first_occurrence = kwargs['first_occurrence']
            
        if 'gender' in kwargs:
            self._config.gender_concepts = kwargs['gender'] if isinstance(kwargs['gender'], list) else [kwargs['gender']]

        return self

    # --- Fluid Chaining Methods (Time Windows & Occurrence) ---

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

    def anytime_before(self) -> Any:
        """Events occurring any time before the index."""
        self._config.time_window = TimeWindow(days_before=99999, days_after=0)
        return self._finalize()

    def anytime_after(self) -> Any:
        """Events occurring any time after the index."""
        self._config.time_window = TimeWindow(days_before=0, days_after=99999)
        return self._finalize()

    def within_days_before(self, days: int) -> Any:
        """Events occurring within N days before the index."""
        self._config.time_window = TimeWindow(days_before=days, days_after=0)
        return self._finalize()

    def within_days_after(self, days: int) -> Any:
        """Events occurring within N days after the index."""
        self._config.time_window = TimeWindow(days_before=0, days_after=days)
        return self._finalize()

    def within_days(self, before: int = 0, after: int = 0) -> Any:
        """Events occurring within a window of [before, after] days."""
        self._config.time_window = TimeWindow(days_before=before, days_after=after)
        return self._finalize()

    def same_day(self) -> Any:
        """Events occurring on the same day as the index."""
        self._config.time_window = TimeWindow(days_before=0, days_after=0)
        return self._finalize()

    def during_event(self) -> Any:
        """Events occurring within the duration of the index event."""
        self._config.time_window = TimeWindow(days_before=0, days_after=0, use_index_end=True)
        return self._finalize()

    def before_event_end(self, days: int = 0) -> Any:
        """Events occurring before the end of the index event."""
        self._config.time_window = TimeWindow(days_before=days, days_after=0, use_index_end=True)
        return self._finalize()

    def restrict_to_visit(self) -> 'BaseQuery':
        """Restrict criteria to the same visit as the index event."""
        self._config.restrict_visit = True
        return self

    def between_visits(self) -> 'BaseQuery':
        """Shortcut for restrict_to_visit()."""
        return self.restrict_to_visit()

    def ignore_observation_period(self) -> 'BaseQuery':
        """Ignore observation period requirements for this criteria."""
        self._config.ignore_observation_period = True
        return self

    def with_distinct(self) -> 'BaseQuery':
        """Count distinct occurrences (e.g., distinct days or distinct status)."""
        self._config.is_distinct = True
        return self

    def _finalize(self) -> Any:
        """Add this query to the parent and return for chaining."""
        if self._parent is None:
            return self
        
        if hasattr(self._parent, "_add_censor_query") and self._is_censor:
            return self._parent._add_censor_query(self._config)
            
        return self._parent._add_query(self._config, self._is_exclusion)

    def _get_config(self) -> "QueryConfig":
        """Get the query configuration."""
        return self._config

    def build(self) -> Any:
        """Finalize the query and build the cohort."""
        return self._finalize().build()


class ConditionQuery(BaseQuery):
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("ConditionOccurrence", concept_set_id, **kwargs)

    def with_status(self, *concept_ids: int) -> 'ConditionQuery':
        """Require specific condition status concept IDs."""
        self._config.status_concepts.extend(concept_ids)
        return self

    def with_condition_type(self, *concept_ids: int) -> 'ConditionQuery':
        """Require specific condition type concept IDs."""
        self._config.condition_type_concepts.extend(concept_ids)
        return self

    def apply_params(self, **kwargs) -> 'ConditionQuery':
        super().apply_params(**kwargs)
        if 'status' in kwargs:
            self._config.status_concepts = kwargs['status'] if isinstance(kwargs['status'], list) else [kwargs['status']]
        if 'type' in kwargs:
            self._config.condition_type_concepts = kwargs['type'] if isinstance(kwargs['type'], list) else [kwargs['type']]
        return self


class DrugQuery(BaseQuery):
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("DrugExposure", concept_set_id, **kwargs)

    def with_days_supply(self, min_days: int, max_days: Optional[int] = None) -> 'DrugQuery':
        """Require specific days supply range."""
        self._config.days_supply_min = min_days
        self._config.days_supply_max = max_days
        return self

    def with_quantity(self, min_qty: float, max_qty: Optional[float] = None) -> 'DrugQuery':
        """Require specific quantity range."""
        self._config.quantity_min = min_qty
        self._config.quantity_max = max_qty
        return self

    def with_drug_type(self, *concept_ids: int) -> 'DrugQuery':
        """Require specific drug type concept IDs."""
        self._config.drug_type_concepts.extend(concept_ids)
        return self

    def with_route(self, *concept_ids: int) -> 'DrugQuery':
        """Require specific drug route concept IDs."""
        self._config.drug_route_concepts.extend(concept_ids)
        return self

    def with_refills(self, min_refills: int, max_refills: Optional[int] = None) -> 'DrugQuery':
        """Require specific refills range."""
        self._config.refills_min = min_refills
        self._config.refills_max = max_refills
        return self

    def with_dose(self, min_dose: float, max_dose: Optional[float] = None) -> 'DrugQuery':
        """Require specific effective drug dose range."""
        self._config.dose_min = min_dose
        self._config.dose_max = max_dose
        return self

    def apply_params(self, **kwargs) -> 'DrugQuery':
        super().apply_params(**kwargs)
        if 'days_supply_min' in kwargs:
            self._config.days_supply_min = kwargs['days_supply_min']
        if 'days_supply_max' in kwargs:
            self._config.days_supply_max = kwargs['days_supply_max']
        if 'type' in kwargs:
            self._config.drug_type_concepts = kwargs['type'] if isinstance(kwargs['type'], list) else [kwargs['type']]
        if 'quantity_min' in kwargs:
            self._config.quantity_min = kwargs['quantity_min']
        if 'quantity_max' in kwargs:
            self._config.quantity_max = kwargs['quantity_max']
        if 'route' in kwargs:
            self._config.drug_route_concepts = kwargs['route'] if isinstance(kwargs['route'], list) else [kwargs['route']]
        if 'refills_min' in kwargs:
            self._config.refills_min = kwargs['refills_min']
        if 'refills_max' in kwargs:
            self._config.refills_max = kwargs['refills_max']
        if 'dose_min' in kwargs:
            self._config.dose_min = kwargs['dose_min']
        if 'dose_max' in kwargs:
            self._config.dose_max = kwargs['dose_max']
        return self


class DrugEraQuery(BaseQuery):
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("DrugEra", concept_set_id, **kwargs)

    def apply_params(self, **kwargs) -> 'DrugEraQuery':
        super().apply_params(**kwargs)
        if 'era_length_min' in kwargs:
            self._config.era_length_min = kwargs['era_length_min']
        if 'era_length_max' in kwargs:
            self._config.era_length_max = kwargs['era_length_max']
        if 'gap_days_min' in kwargs:
            self._config.extent_min = kwargs['gap_days_min']
        if 'gap_days_max' in kwargs:
            self._config.extent_max = kwargs['gap_days_max']
        if 'occurrence_count_min' in kwargs:
            self._config.occurrence_count = kwargs['occurrence_count_min']
            self._config.value_min = kwargs['occurrence_count_min']
        if 'occurrence_count_max' in kwargs:
            self._config.value_max = kwargs['occurrence_count_max']
        return self


class MeasurementQuery(BaseQuery):
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("Measurement", concept_set_id, **kwargs)

    def with_value(self, min_val: float, max_val: Optional[float] = None) -> 'MeasurementQuery':
        """Require specific value range."""
        self._config.value_min = min_val
        self._config.value_max = max_val
        return self

    def with_unit(self, *concept_ids: int) -> 'MeasurementQuery':
        """Require specific unit concept IDs."""
        self._config.unit_concepts.extend(concept_ids)
        return self

    def is_abnormal(self, value: bool = True) -> 'MeasurementQuery':
        """Restrict to abnormal values."""
        self._config.abnormal = value
        return self

    def with_range_low_ratio(self, min_ratio: float, max_ratio: Optional[float] = None) -> 'MeasurementQuery':
        """Require specific range low ratio."""
        self._config.range_low_ratio_min = min_ratio
        self._config.range_low_ratio_max = max_ratio
        return self

    def with_range_high_ratio(self, min_ratio: float, max_ratio: Optional[float] = None) -> 'MeasurementQuery':
        """Require specific range high ratio."""
        self._config.range_high_ratio_min = min_ratio
        self._config.range_high_ratio_max = max_ratio
        return self

    def with_operator(self, *concept_ids: int) -> 'MeasurementQuery':
        """Require specific operator concept IDs."""
        self._config.measurement_operator_concepts.extend(concept_ids)
        return self

    def with_value_as_concept(self, *concept_ids: int) -> 'MeasurementQuery':
        """Require specific value as concept IDs."""
        self._config.value_as_concept_concepts.extend(concept_ids)
        return self

    def apply_params(self, **kwargs) -> 'MeasurementQuery':
        super().apply_params(**kwargs)
        if 'value_min' in kwargs:
            self._config.value_min = kwargs['value_min']
        if 'value_max' in kwargs:
            self._config.value_max = kwargs['value_max']
        if 'unit' in kwargs:
            self._config.unit_concepts = kwargs['unit'] if isinstance(kwargs['unit'], list) else [kwargs['unit']]
        if 'abnormal' in kwargs:
            self._config.abnormal = kwargs['abnormal']
        if 'range_low_min' in kwargs:
            self._config.range_low_min = kwargs['range_low_min']
        if 'range_low_max' in kwargs:
            self._config.range_low_max = kwargs['range_low_max']
        if 'range_high_min' in kwargs:
            self._config.range_high_min = kwargs['range_high_min']
        if 'range_high_max' in kwargs:
            self._config.range_high_max = kwargs['range_high_max']
        if 'value_as_concept' in kwargs:
            self._config.value_as_concept_concepts = kwargs['value_as_concept'] if isinstance(kwargs['value_as_concept'], list) else [kwargs['value_as_concept']]
        if 'operator' in kwargs:
            self._config.measurement_operator_concepts = kwargs['operator'] if isinstance(kwargs['operator'], list) else [kwargs['operator']]
        return self


class ProcedureQuery(BaseQuery):
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("ProcedureOccurrence", concept_set_id, **kwargs)

    def with_procedure_type(self, *concept_ids: int) -> 'ProcedureQuery':
        """Require specific procedure type concept IDs."""
        self._config.procedure_type_concepts.extend(concept_ids)
        return self

    def with_modifier(self, *concept_ids: int) -> 'ProcedureQuery':
        """Require specific procedure modifier concept IDs."""
        self._config.procedure_modifier_concepts.extend(concept_ids)
        return self

    def with_quantity(self, min_qty: float, max_qty: Optional[float] = None) -> 'ProcedureQuery':
        """Require specific quantity range."""
        self._config.quantity_min = min_qty
        self._config.quantity_max = max_qty
        return self

    def apply_params(self, **kwargs) -> 'ProcedureQuery':
        super().apply_params(**kwargs)
        if 'quantity_min' in kwargs:
            self._config.quantity_min = kwargs['quantity_min']
        if 'quantity_max' in kwargs:
            self._config.quantity_max = kwargs['quantity_max']
        if 'modifier' in kwargs:
            self._config.procedure_modifier_concepts = kwargs['modifier'] if isinstance(kwargs['modifier'], list) else [kwargs['modifier']]
        if 'type' in kwargs:
            self._config.procedure_type_concepts = kwargs['type'] if isinstance(kwargs['type'], list) else [kwargs['type']]
        return self


class VisitQuery(BaseQuery):
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("VisitOccurrence", concept_set_id, **kwargs)

    def with_visit_type(self, *concept_ids: int) -> 'VisitQuery':
        """Require specific visit type concept IDs."""
        self._config.visit_type_concepts.extend(concept_ids)
        return self

    def with_place_of_service(self, *concept_ids: int) -> 'VisitQuery':
        """Require specific place of service concept IDs."""
        self._config.place_of_service_concepts.extend(concept_ids)
        return self

    def with_length(self, min_days: int, max_days: Optional[int] = None) -> 'VisitQuery':
        """Require specific visit length range."""
        self._config.value_min = min_days
        self._config.value_max = max_days
        return self

    def apply_params(self, **kwargs) -> 'VisitQuery':
        super().apply_params(**kwargs)
        if 'length_min' in kwargs:
            self._config.value_min = kwargs['length_min']
        if 'length_max' in kwargs:
            self._config.value_max = kwargs['length_max']
        if 'place_of_service' in kwargs:
            self._config.place_of_service_concepts = kwargs['place_of_service'] if isinstance(kwargs['place_of_service'], list) else [kwargs['place_of_service']]
        return self


class ObservationQuery(BaseQuery):
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("Observation", concept_set_id, **kwargs)

    def with_observation_type(self, *concept_ids: int) -> 'ObservationQuery':
        """Require specific observation type concept IDs."""
        self._config.observation_type_concepts.extend(concept_ids)
        return self

    def with_qualifier(self, *concept_ids: int) -> 'ObservationQuery':
        """Require specific qualifier concept IDs."""
        self._config.qualifier_concepts.extend(concept_ids)
        return self

    def with_value_as_string(self, value: str) -> 'ObservationQuery':
        """Require specific value as string."""
        self._config.value_as_string = value
        return self

    def apply_params(self, **kwargs) -> 'ObservationQuery':
        super().apply_params(**kwargs)
        if 'qualifier' in kwargs:
            self._config.qualifier_concepts = kwargs['qualifier'] if isinstance(kwargs['qualifier'], list) else [kwargs['qualifier']]
        if 'value_as_string' in kwargs:
            self._config.value_as_string = kwargs['value_as_string']
        return self


class DeathQuery(BaseQuery):
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("Death", concept_set_id, **kwargs)


class ConditionEraQuery(BaseQuery):
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("ConditionEra", concept_set_id, **kwargs)

    def apply_params(self, **kwargs) -> 'ConditionEraQuery':
        super().apply_params(**kwargs)
        if 'era_length_min' in kwargs:
            self._config.era_length_min = kwargs['era_length_min']
        if 'era_length_max' in kwargs:
            self._config.era_length_max = kwargs['era_length_max']
        if 'occurrence_count_min' in kwargs:
            self._config.value_min = kwargs['occurrence_count_min']
        if 'occurrence_count_max' in kwargs:
            self._config.value_max = kwargs['occurrence_count_max']
        return self


class DeviceExposureQuery(BaseQuery):
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("DeviceExposure", concept_set_id, **kwargs)


class SpecimenQuery(BaseQuery):
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("Specimen", concept_set_id, **kwargs)


class ObservationPeriodQuery(BaseQuery):
    def __init__(self, **kwargs):
        super().__init__("ObservationPeriod", concept_set_id=None, **kwargs)

    def apply_params(self, **kwargs) -> 'ObservationPeriodQuery':
        super().apply_params(**kwargs)
        if 'length_min' in kwargs:
            self._config.value_min = kwargs['length_min']
        if 'length_max' in kwargs:
            self._config.value_max = kwargs['length_max']
        return self


class PayerPlanPeriodQuery(BaseQuery):
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("PayerPlanPeriod", concept_set_id, **kwargs)


class LocationRegionQuery(BaseQuery):
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("LocationRegion", concept_set_id, **kwargs)


class VisitDetailQuery(BaseQuery):
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("VisitDetail", concept_set_id, **kwargs)


class DoseEraQuery(BaseQuery):
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("DoseEra", concept_set_id, **kwargs)


class CriteriaGroupBuilder:
    def __init__(self, parent: Union['CriteriaGroupBuilder', 'CohortWithCriteria', 'BaseQuery'], group: GroupConfig):
        self._parent = parent
        self._group = group

    def __enter__(self) -> 'CriteriaGroupBuilder':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        return False
    
    def _add_query(self, config: QueryConfig, is_exclusion: bool = False) -> 'CriteriaGroupBuilder':
        self._group.criteria.append(CriteriaConfig(
            query_config=config,
            is_exclusion=is_exclusion
        ))
        return self
    
    def end_group(self) -> Any:
        """End this group and return to parent context."""
        return self._parent
    
    def require_condition(self, concept_set_id: int, **kwargs) -> "CriteriaGroupBuilder":
        return ConditionQuery(concept_set_id, parent=self, is_exclusion=False).apply_params(**kwargs)._finalize()

    def require_drug(self, concept_set_id: int, **kwargs) -> "CriteriaGroupBuilder":
        return DrugQuery(concept_set_id, parent=self, is_exclusion=False).apply_params(**kwargs)._finalize()

    def require_drug_era(self, concept_set_id: int, **kwargs) -> "CriteriaGroupBuilder":
        return DrugEraQuery(concept_set_id, parent=self, is_exclusion=False).apply_params(**kwargs)._finalize()

    def require_measurement(self, concept_set_id: int, **kwargs) -> "CriteriaGroupBuilder":
        return MeasurementQuery(concept_set_id, parent=self, is_exclusion=False).apply_params(**kwargs)._finalize()

    def require_procedure(self, concept_set_id: int, **kwargs) -> "CriteriaGroupBuilder":
        return ProcedureQuery(concept_set_id, parent=self, is_exclusion=False).apply_params(**kwargs)._finalize()

    def require_visit(self, concept_set_id: int, **kwargs) -> "CriteriaGroupBuilder":
        return VisitQuery(concept_set_id, parent=self, is_exclusion=False).apply_params(**kwargs)._finalize()

    def require_observation(self, concept_set_id: int, **kwargs) -> "CriteriaGroupBuilder":
        return ObservationQuery(concept_set_id, parent=self, is_exclusion=False).apply_params(**kwargs)._finalize()

    def require_visit_detail(self, concept_set_id: int, **kwargs) -> "CriteriaGroupBuilder":
        return VisitDetailQuery(concept_set_id, parent=self, is_exclusion=False).apply_params(**kwargs)._finalize()

    def require_death(self, **kwargs) -> "CriteriaGroupBuilder":
        return DeathQuery(parent=self, is_exclusion=False).apply_params(**kwargs)._finalize()

    # Aliases for brevity
    def condition(self, concept_set_id: int, **kwargs) -> "CriteriaGroupBuilder":
        return self.require_condition(concept_set_id, **kwargs)

    def drug(self, concept_set_id: int, **kwargs) -> "CriteriaGroupBuilder":
        return self.require_drug(concept_set_id, **kwargs)

    def measurement(self, concept_set_id: int, **kwargs) -> "CriteriaGroupBuilder":
        return self.require_measurement(concept_set_id, **kwargs)

    def procedure(self, concept_set_id: int, **kwargs) -> "CriteriaGroupBuilder":
        return self.require_procedure(concept_set_id, **kwargs)

    def visit(self, concept_set_id: int, **kwargs) -> "CriteriaGroupBuilder":
        return self.require_visit(concept_set_id, **kwargs)

    def observation(self, concept_set_id: int, **kwargs) -> "CriteriaGroupBuilder":
        return self.require_observation(concept_set_id, **kwargs)

    def death(self, **kwargs) -> "CriteriaGroupBuilder":
        return self.require_death(**kwargs)

    def require_device(self, concept_set_id: int, **kwargs) -> "CriteriaGroupBuilder":
        return DeviceExposureQuery(concept_set_id, parent=self, is_exclusion=False).apply_params(**kwargs)._finalize()

    def require_specimen(self, concept_set_id: int, **kwargs) -> "CriteriaGroupBuilder":
        return SpecimenQuery(concept_set_id, parent=self, is_exclusion=False).apply_params(**kwargs)._finalize()

    def require_condition_era(self, concept_set_id: int, **kwargs) -> "CriteriaGroupBuilder":
        return ConditionEraQuery(concept_set_id, parent=self, is_exclusion=False).apply_params(**kwargs)._finalize()

    def require_payer_plan_period(self, concept_set_id: int, **kwargs) -> "CriteriaGroupBuilder":
        return PayerPlanPeriodQuery(concept_set_id, parent=self, is_exclusion=False).apply_params(**kwargs)._finalize()

    def exclude_condition(self, concept_set_id: int, **kwargs) -> "CriteriaGroupBuilder":
        return ConditionQuery(concept_set_id, parent=self, is_exclusion=True).apply_params(**kwargs)._finalize()

    def exclude_drug(self, concept_set_id: int, **kwargs) -> "CriteriaGroupBuilder":
        return DrugQuery(concept_set_id, parent=self, is_exclusion=True).apply_params(**kwargs)._finalize()


    def any_of(self) -> 'CriteriaGroupBuilder':
        new_group = GroupConfig(type="ANY")
        self._group.criteria.append(new_group)
        return CriteriaGroupBuilder(self, new_group)

    def all_of(self) -> 'CriteriaGroupBuilder':
        new_group = GroupConfig(type="ALL")
        self._group.criteria.append(new_group)
        return CriteriaGroupBuilder(self, new_group)

    def at_least_of(self, count: int) -> 'CriteriaGroupBuilder':
        new_group = GroupConfig(type="AT_LEAST", count=count)
        self._group.criteria.append(new_group)
        return CriteriaGroupBuilder(self, new_group)

    def __getattr__(self, name: str):
        """Dynamic dispatch for extension domain methods.
        
        Supports patterns like:
            .require_waveform_feature(cs_id, ...)
            .exclude_waveform_feature(cs_id, ...)
            .waveform_feature(cs_id, ...)  # alias for require_
        """
        from circe.extensions import get_registry, _snake_to_pascal
        registry = get_registry()
        domain_queries = registry.get_domain_query_map()
        
        for prefix in ('require_', 'exclude_', ''):
            if prefix and not name.startswith(prefix):
                continue
            domain_snake = name[len(prefix):] if prefix else name
            pascal_domain = _snake_to_pascal(domain_snake)
            if pascal_domain in domain_queries:
                query_cls = domain_queries[pascal_domain]
                is_exclusion = prefix == 'exclude_'
                def method(concept_set_id, _q=query_cls, _ex=is_exclusion, **kwargs):
                    return _q(concept_set_id, parent=self, is_exclusion=_ex).apply_params(**kwargs)._finalize()
                return method
        
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")
