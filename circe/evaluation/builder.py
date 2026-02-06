"""
Fluent Builder for Phenotype Evaluation Rubrics.
"""

from typing import Optional, List, Union, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass, field
import copy

from circe.cohort_builder.query_builder import (
    QueryConfig, TimeWindow, BaseQuery,
    ConditionQuery, DrugQuery, DrugEraQuery, MeasurementQuery, 
    ProcedureQuery, VisitQuery, ObservationQuery, DeathQuery,
    ConditionEraQuery, DeviceExposureQuery, SpecimenQuery,
    ObservationPeriodQuery, PayerPlanPeriodQuery, LocationRegionQuery,
    VisitDetailQuery, DoseEraQuery, CriteriaConfig, GroupConfig, CriteriaGroupBuilder
)
from circe.cohortdefinition import (
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
from circe.evaluation.models import EvaluationRubric, EvaluationRule
from circe.vocabulary import ConceptSet, Concept

class EvaluationBuilder:
    """
    Main entry point for building an EvaluationRubric.
    
    Example:
        >>> with EvaluationBuilder("GI Bleed Evaluation") as ev:
        ...     bleed = ev.concept_set("GI Bleed", 192671)
        ...     ev.add_rule("Primary Diagnosis", weight=10).condition(bleed).at_least(1)
        ...     with ev.rule("Prior Aspirin", weight=5) as rule:
        ...         rule.drug(1112807).at_least(1).within_days_before(30)
        >>> rubric = ev.rubric
    """
    
    def __init__(self, title: str = "Untitled Rubric"):
        self._title = title
        self._concept_sets: List[ConceptSet] = []
        self._rules: List[RuleBuilder] = []
        self._rubric: Optional[EvaluationRubric] = None
        self._in_context: bool = False

    def __enter__(self) -> 'EvaluationBuilder':
        self._in_context = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self._in_context = False
        self._rubric = self.build()
        return False

    def concept_set(self, name: str, *concept_ids: int, **kwargs) -> int:
        """Create and register a concept set, returning its ID."""
        cs_id = len(self._concept_sets) + 1
        from circe.vocabulary import concept_set, descendants
        cs = concept_set(*[descendants(cid) for cid in concept_ids], id=cs_id, name=name)
        self._concept_sets.append(cs)
        return cs_id

    def add_rule(self, name: str, weight: float, polarity: int = 1, category: Optional[str] = None) -> 'RuleBuilder':
        """Add a simple one-line rule."""
        rule_id = len(self._rules) + 1
        builder = RuleBuilder(self, rule_id, name, weight, polarity, category)
        self._rules.append(builder)
        return builder

    def rule(self, name: str, weight: float, polarity: int = 1, category: Optional[str] = None) -> 'RuleBuilder':
        """Alias for add_rule, ideal for 'with' blocks."""
        return self.add_rule(name, weight, polarity, category)

    @property
    def rubric(self) -> EvaluationRubric:
        if self._rubric is None:
            if self._in_context:
                raise RuntimeError("Cannot access 'rubric' while inside the context manager.")
            self._rubric = self.build()
        return self._rubric

    def build(self) -> EvaluationRubric:
        """Construct the final EvaluationRubric."""
        rules = [rb._build_rule() for rb in self._rules]
        return EvaluationRubric(
            concept_sets=self._concept_sets,
            rules=rules
        )

class RuleBuilder:
    """Builder for an individual EvaluationRule."""
    
    def __init__(self, parent_eval: EvaluationBuilder, rule_id: int, name: str, weight: float, polarity: int, category: Optional[str]):
        self._parent_eval = parent_eval
        self._rule_id = rule_id
        self._name = name
        self._weight = weight
        self._polarity = polarity
        self._category = category
        self._group = GroupConfig(type="ALL")
        self._in_context: bool = False

    def __enter__(self) -> 'RuleBuilder':
        self._in_context = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self._in_context = False
        return False

    def _add_query(self, config: QueryConfig, is_exclusion: bool = False) -> 'RuleBuilder':
        self._group.criteria.append(CriteriaConfig(
            query_config=config,
            is_exclusion=is_exclusion
        ))
        return self

    # --- Domain Methods ---
    def condition(self, concept_set_id: int, **kwargs) -> 'RuleBuilder':
        ConditionQuery(concept_set_id, parent=self).apply_params(**kwargs)._finalize()
        return self

    def drug(self, concept_set_id: int, **kwargs) -> 'RuleBuilder':
        DrugQuery(concept_set_id, parent=self).apply_params(**kwargs)._finalize()
        return self

    def measurement(self, concept_set_id: int, **kwargs) -> 'RuleBuilder':
        MeasurementQuery(concept_set_id, parent=self).apply_params(**kwargs)._finalize()
        return self

    def procedure(self, concept_set_id: int, **kwargs) -> 'RuleBuilder':
        ProcedureQuery(concept_set_id, parent=self).apply_params(**kwargs)._finalize()
        return self

    def visit(self, concept_set_id: int, **kwargs) -> 'RuleBuilder':
        VisitQuery(concept_set_id, parent=self).apply_params(**kwargs)._finalize()
        return self

    def observation(self, concept_set_id: int, **kwargs) -> 'RuleBuilder':
        ObservationQuery(concept_set_id, parent=self).apply_params(**kwargs)._finalize()
        return self

    # Fluent modifiers for simple one-line rules
    def at_least(self, count: int) -> 'RuleBuilder':
        if not self._group.criteria:
            raise RuntimeError("Call a criteria method (e.g. .condition()) before .at_least()")
        last = self._group.criteria[-1]
        if isinstance(last, CriteriaConfig):
            last.query_config.occurrence_count = count
            last.query_config.occurrence_type = "atLeast"
        return self

    def within_days_before(self, days: int) -> 'RuleBuilder':
        if not self._group.criteria:
             raise RuntimeError("Call a criteria method before temporal modifiers")
        last = self._group.criteria[-1]
        if isinstance(last, CriteriaConfig):
            last.query_config.time_window = TimeWindow(days_before=days, days_after=0)
        return self

    def anytime_before(self) -> 'RuleBuilder':
        if not self._group.criteria:
             raise RuntimeError("Call a criteria method before temporal modifiers")
        last = self._group.criteria[-1]
        if isinstance(last, CriteriaConfig):
            last.query_config.time_window = TimeWindow(days_before=99999, days_after=0)
        return self

    def anytime_after(self) -> 'RuleBuilder':
        if not self._group.criteria:
             raise RuntimeError("Call a criteria method before temporal modifiers")
        last = self._group.criteria[-1]
        if isinstance(last, CriteriaConfig):
            last.query_config.time_window = TimeWindow(days_before=0, days_after=99999)
        return self

    def with_value(self, gt: Optional[float] = None, lt: Optional[float] = None, between: Optional[tuple] = None) -> 'RuleBuilder':
        """Set measurement value constraints."""
        if not self._group.criteria:
             raise RuntimeError("Call a criteria method before .with_value()")
        last = self._group.criteria[-1]
        if isinstance(last, CriteriaConfig):
            cfg = last.query_config
            if between:
                cfg.value_min, cfg.value_max = between
            else:
                cfg.value_min = gt
                cfg.value_max = lt
        return self

    def any_of(self) -> CriteriaGroupBuilder:
        new_group = GroupConfig(type="ANY")
        self._group.criteria.append(new_group)
        return CriteriaGroupBuilder(self, new_group)

    def all_of(self) -> CriteriaGroupBuilder:
        new_group = GroupConfig(type="ALL")
        self._group.criteria.append(new_group)
        return CriteriaGroupBuilder(self, new_group)

    def _build_rule(self) -> EvaluationRule:
        """Convert builder state to EvaluationRule model."""
        return EvaluationRule(
            rule_id=self._rule_id,
            name=self._name,
            weight=self._weight,
            polarity=self._polarity,
            category=self._category,
            expression=_build_criteria_group(self._group)
        )

# --- Helper Conversion Functions (Adapted from CohortBuilder) ---

def _build_criteria_group(group_cfg: GroupConfig) -> CirceCriteriaGroup:
    criteria_list = []
    groups = []
    for item in group_cfg.criteria:
        if isinstance(item, CriteriaConfig):
            criteria_list.append(_build_correlated_criteria(item))
        elif isinstance(item, GroupConfig):
            groups.append(_build_criteria_group(item))
    return CirceCriteriaGroup(
        type=group_cfg.type,
        count=group_cfg.count,
        criteria_list=criteria_list,
        groups=groups
    )

def _build_correlated_criteria(criteria_cfg: CriteriaConfig) -> CorelatedCriteria:
    config = criteria_cfg.query_config
    query_criteria = _config_to_criteria(config)
    
    # Occurrence
    type_map = {"exactly": 0, "atMost": 1, "atLeast": 2}
    occ_type = type_map.get(config.occurrence_type, 2)
    occurrence = Occurrence(
        type=occ_type, 
        count=config.occurrence_count or 1,
        is_distinct=config.is_distinct
    )
    
    # Window
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
        occurrence=occurrence
    )

def _config_to_criteria(config: QueryConfig):
    domain_map = {
        'ConditionOccurrence': ConditionOccurrence,
        'DrugExposure': DrugExposure,
        'Measurement': Measurement,
        'ProcedureOccurrence': ProcedureOccurrence,
        'VisitOccurrence': VisitOccurrence,
        'Observation': Observation,
        'Death': Death
    }
    cls = domain_map.get(config.domain)
    if not cls: raise ValueError(f"Unsupported domain: {config.domain}")
    
    kwargs = {'codeset_id': config.concept_set_id}
    
    # Handle Gender filter if present in config
    if config.gender_concepts:
        if hasattr(cls, 'gender_cs'):
             # We need a dummy codeset_id or we just use gender if it's a simple list
             kwargs['gender'] = [Concept(concept_id=cid) for cid in config.gender_concepts]

    if config.domain == 'Measurement' and (config.value_min is not None or config.value_max is not None):
        if config.value_min is not None and config.value_max is not None:
             kwargs['value_as_number'] = NumericRange(op='bt', value=config.value_min, extent=config.value_max)
        elif config.value_min is not None:
             kwargs['value_as_number'] = NumericRange(op='gte', value=config.value_min)
        else:
             kwargs['value_as_number'] = NumericRange(op='lte', value=config.value_max)
        
    return cls(**{k: v for k, v in kwargs.items() if v is not None})
