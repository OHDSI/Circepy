"""
Fluent Builder for Phenotype Evaluation Rubrics.
"""

from typing import Optional, Union

from circe.cohort_builder.query_builder import (
    ConditionEraQuery,
    ConditionQuery,
    CriteriaConfig,
    CriteriaGroupBuilder,
    DeathQuery,
    DeviceExposureQuery,
    DoseEraQuery,
    DrugEraQuery,
    DrugQuery,
    GroupConfig,
    LocationRegionQuery,
    MeasurementQuery,
    ObservationPeriodQuery,
    ObservationQuery,
    PayerPlanPeriodQuery,
    ProcedureQuery,
    QueryConfig,
    SpecimenQuery,
    TimeWindow,
    VisitDetailQuery,
    VisitQuery,
)
from circe.cohortdefinition import (
    ConditionEra,
    ConditionOccurrence,
    CorelatedCriteria,
    Death,
    DeviceExposure,
    DoseEra,
    DrugEra,
    DrugExposure,
    LocationRegion,
    Measurement,
    Observation,
    ObservationPeriod,
    Occurrence,
    PayerPlanPeriod,
    ProcedureOccurrence,
    Specimen,
    VisitDetail,
    VisitOccurrence,
)
from circe.cohortdefinition.core import NumericRange, Window, WindowBound
from circe.cohortdefinition.criteria import CriteriaGroup as CirceCriteriaGroup
from circe.evaluation.models import EvaluationRubric, EvaluationRule
from circe.vocabulary import Concept, ConceptReference, ConceptSet, concept_set, descendants


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

    def __init__(self, title: str = "Untitled Rubric", description: str = ""):
        self._title = title
        self._description = description
        self._concept_sets: list[ConceptSet] = []
        self._rules: list[RuleBuilder] = []
        self._rubric: Optional[EvaluationRubric] = None
        self._in_context: bool = False

    def __enter__(self) -> "EvaluationBuilder":
        self._in_context = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self._in_context = False
        self._rubric = self.build()
        return False

    def concept_set(self, name: str, *concepts: Union[int, "ConceptReference"], **kwargs) -> int:
        """
        Create and register a concept set, returning its ID.

        Args:
            name: Human-readable name
            *concepts: Variadic list of concept IDs (int) or ConceptReference objects.
                      If an int is provided, it defaults to including descendants.
            **kwargs: Additional parameters for concept set (reserved for future use)

        Returns:
            The ID assigned to the new concept set.
        """
        cs_id = len(self._concept_sets) + 1

        # Process concepts: default int to descendants() for evaluation convenience
        refs = []
        for c in concepts:
            if isinstance(c, int):
                refs.append(descendants(c))
            else:
                refs.append(c)

        cs = concept_set(*refs, id=cs_id, name=name)
        self._concept_sets.append(cs)
        return cs_id

    def with_concept_sets(self, *concept_sets: ConceptSet) -> "EvaluationBuilder":
        """
        Register pre-built concept sets.

        Args:
            *concept_sets: ConceptSet objects to add to the rubric.

        Returns:
            Self for chaining.
        """
        for cs in concept_sets:
            # Ensure ID is set (use 1-based index if not set)
            if cs.id == 0:
                cs.id = len(self._concept_sets) + 1
            self._concept_sets.append(cs)
        return self

    def add_rule(
        self,
        name: str,
        weight: float,
        category: Optional[str] = None,
        description: str = "",
    ) -> "RuleBuilder":
        """Add a simple one-line rule. The sign of `weight` determines whether this is
        evidence (positive) or an exclusion (negative)."""
        rule_id = len(self._rules) + 1
        builder = RuleBuilder(self, rule_id, name, weight, category, description)
        self._rules.append(builder)
        return builder

    def rule(
        self,
        name: str,
        weight: float,
        category: Optional[str] = None,
        description: str = "",
    ) -> "RuleBuilder":
        """Alias for add_rule, ideal for 'with' blocks."""
        return self.add_rule(name, weight, category, description)

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
        return EvaluationRubric(description=self._description, concept_sets=self._concept_sets, rules=rules)


class RuleBuilder:
    """Builder for an individual EvaluationRule."""

    # Define domain query mapping once
    _DOMAIN_QUERIES = {
        "condition": ConditionQuery,
        "drug": DrugQuery,
        "drug_era": DrugEraQuery,
        "measurement": MeasurementQuery,
        "procedure": ProcedureQuery,
        "visit": VisitQuery,
        "observation": ObservationQuery,
        "death": DeathQuery,
        "condition_era": ConditionEraQuery,
        "device_exposure": DeviceExposureQuery,
        "specimen": SpecimenQuery,
        "observation_period": ObservationPeriodQuery,
        "payer_plan_period": PayerPlanPeriodQuery,
        "location_region": LocationRegionQuery,
        "visit_detail": VisitDetailQuery,
        "dose_era": DoseEraQuery,
    }

    def __init__(
        self,
        parent_eval: EvaluationBuilder,
        rule_id: int,
        name: str,
        weight: float,
        category: Optional[str],
        description: str = "",
    ):
        self._parent_eval = parent_eval
        self._rule_id = rule_id
        self._name = name
        self._weight = weight
        self._category = category
        self._description = description
        self._group = GroupConfig(type="ALL")
        self._in_context: bool = False

    def __enter__(self) -> "RuleBuilder":
        self._in_context = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self._in_context = False
        return False

    def _add_query(self, config: QueryConfig, is_exclusion: bool = False) -> "RuleBuilder":
        self._group.criteria.append(CriteriaConfig(query_config=config, is_exclusion=is_exclusion))
        return self

    def _add_domain_criteria(self, domain_name: str, concept_set_id: int, **kwargs) -> "RuleBuilder":
        """Generic method to add domain criteria."""
        query_class = self._DOMAIN_QUERIES.get(domain_name)
        if not query_class:
            raise ValueError(f"Unknown domain: {domain_name}")
        query_class(concept_set_id, parent=self).apply_params(**kwargs)._finalize()
        return self

    # --- Domain Methods ---
    def condition(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        return self._add_domain_criteria("condition", concept_set_id, **kwargs)

    def drug(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        return self._add_domain_criteria("drug", concept_set_id, **kwargs)

    def drug_era(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        return self._add_domain_criteria("drug_era", concept_set_id, **kwargs)

    def measurement(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        return self._add_domain_criteria("measurement", concept_set_id, **kwargs)

    def procedure(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        return self._add_domain_criteria("procedure", concept_set_id, **kwargs)

    def visit(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        return self._add_domain_criteria("visit", concept_set_id, **kwargs)

    def observation(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        return self._add_domain_criteria("observation", concept_set_id, **kwargs)

    def death(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        return self._add_domain_criteria("death", concept_set_id, **kwargs)

    def condition_era(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        return self._add_domain_criteria("condition_era", concept_set_id, **kwargs)

    def device_exposure(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        return self._add_domain_criteria("device_exposure", concept_set_id, **kwargs)

    def specimen(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        return self._add_domain_criteria("specimen", concept_set_id, **kwargs)

    def observation_period(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        return self._add_domain_criteria("observation_period", concept_set_id, **kwargs)

    def payer_plan_period(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        return self._add_domain_criteria("payer_plan_period", concept_set_id, **kwargs)

    def location_region(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        return self._add_domain_criteria("location_region", concept_set_id, **kwargs)

    def visit_detail(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        return self._add_domain_criteria("visit_detail", concept_set_id, **kwargs)

    def dose_era(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        return self._add_domain_criteria("dose_era", concept_set_id, **kwargs)

    # --- Exclude Methods (shorthand for "exactly 0 occurrences") ---

    def _exclude_domain(self, domain_name: str, concept_set_id: int, **kwargs) -> "RuleBuilder":
        """Generic exclude: adds a criteria with exactly 0 occurrences.

        This is shorthand for ``rule.condition(id).at_most(0).within_days_before(N)``
        but expressed as ``rule.exclude_condition(id, within_days_before=N)``.
        """
        query_class = self._DOMAIN_QUERIES.get(domain_name)
        if not query_class:
            raise ValueError(f"Unknown domain: {domain_name}")
        query = query_class(concept_set_id, parent=self, is_exclusion=True)
        # Force exactly 0 occurrences for exclusion semantics
        query._config.occurrence_count = 0
        query._config.occurrence_type = "exactly"
        query.apply_params(**kwargs)
        query._finalize()
        return self

    def exclude_condition(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        """Exclude if a condition is present (exactly 0 occurrences).

        Equivalent to ``rule.condition(id).at_most(0)`` with optional time window.

        Example::

            rule.exclude_condition(cs_id, anytime_before=True)
            rule.exclude_condition(cs_id, within_days_before=365)
        """
        return self._exclude_domain("condition", concept_set_id, **kwargs)

    def exclude_drug(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        """Exclude if a drug exposure is present (exactly 0 occurrences)."""
        return self._exclude_domain("drug", concept_set_id, **kwargs)

    def exclude_drug_era(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        """Exclude if a drug era is present (exactly 0 occurrences)."""
        return self._exclude_domain("drug_era", concept_set_id, **kwargs)

    def exclude_measurement(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        """Exclude if a measurement is present (exactly 0 occurrences)."""
        return self._exclude_domain("measurement", concept_set_id, **kwargs)

    def exclude_procedure(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        """Exclude if a procedure is present (exactly 0 occurrences)."""
        return self._exclude_domain("procedure", concept_set_id, **kwargs)

    def exclude_visit(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        """Exclude if a visit is present (exactly 0 occurrences)."""
        return self._exclude_domain("visit", concept_set_id, **kwargs)

    def exclude_observation(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        """Exclude if an observation is present (exactly 0 occurrences)."""
        return self._exclude_domain("observation", concept_set_id, **kwargs)

    def exclude_device_exposure(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        """Exclude if a device exposure is present (exactly 0 occurrences)."""
        return self._exclude_domain("device_exposure", concept_set_id, **kwargs)

    def exclude_condition_era(self, concept_set_id: int, **kwargs) -> "RuleBuilder":
        """Exclude if a condition era is present (exactly 0 occurrences)."""
        return self._exclude_domain("condition_era", concept_set_id, **kwargs)

    def _modify_last_criteria(self, modifier_fn) -> "RuleBuilder":
        """Generic helper for modifying the last criteria."""
        if not self._group.criteria:
            raise RuntimeError("Call a criteria method before applying modifiers")
        last = self._group.criteria[-1]
        if isinstance(last, CriteriaConfig):
            modifier_fn(last.query_config)
        return self

    # Fluent modifiers for simple one-line rules
    def at_least(self, count: int) -> "RuleBuilder":
        def set_occurrence(cfg):
            cfg.occurrence_count = count
            cfg.occurrence_type = "atLeast"

        return self._modify_last_criteria(set_occurrence)

    def at_most(self, count: int) -> "RuleBuilder":
        def set_occurrence(cfg):
            cfg.occurrence_count = count
            cfg.occurrence_type = "atMost"

        return self._modify_last_criteria(set_occurrence)

    def exactly(self, count: int) -> "RuleBuilder":
        def set_occurrence(cfg):
            cfg.occurrence_count = count
            cfg.occurrence_type = "exactly"

        return self._modify_last_criteria(set_occurrence)

    def _set_time_window(self, days_before: int = 0, days_after: int = 0) -> "RuleBuilder":
        """Generic temporal window setter."""
        return self._modify_last_criteria(
            lambda cfg: setattr(
                cfg, "time_window", TimeWindow(days_before=days_before, days_after=days_after)
            )
        )

    def within_days_before(self, days: int) -> "RuleBuilder":
        return self._set_time_window(days_before=days, days_after=0)

    def within_days_after(self, days: int) -> "RuleBuilder":
        return self._set_time_window(days_before=0, days_after=days)

    def within_days(self, days: Optional[int] = None, before: int = 0, after: int = 0) -> "RuleBuilder":
        """
        Set temporal window.

        Args:
            days: If provided, sets a symmetric window (days before AND days after).
            before: Days before index (used if days is None).
            after: Days after index (used if days is None).
        """
        if days is not None:
            return self._set_time_window(days_before=days, days_after=days)
        return self._set_time_window(days_before=before, days_after=after)

    def anytime_before(self) -> "RuleBuilder":
        return self._set_time_window(days_before=99999, days_after=0)

    def anytime_after(self) -> "RuleBuilder":
        return self._set_time_window(days_before=0, days_after=99999)

    def with_value(
        self, gt: Optional[float] = None, lt: Optional[float] = None, between: Optional[tuple] = None
    ) -> "RuleBuilder":
        """Set measurement/observation value constraints."""

        def set_values(cfg):
            if between:
                cfg.value_min, cfg.value_max = between
            else:
                cfg.value_min = gt
                cfg.value_max = lt

        return self._modify_last_criteria(set_values)

    def any_of(self) -> CriteriaGroupBuilder:
        """Create a nested group where **any** criterion can match (OR logic)."""
        new_group = GroupConfig(type="ANY")
        self._group.criteria.append(new_group)
        return CriteriaGroupBuilder(self, new_group)

    def all_of(self) -> CriteriaGroupBuilder:
        """Create a nested group where **all** criteria must match (AND logic)."""
        new_group = GroupConfig(type="ALL")
        self._group.criteria.append(new_group)
        return CriteriaGroupBuilder(self, new_group)

    def at_least_of(self, count: int) -> CriteriaGroupBuilder:
        """Create a nested group where at least *count* criteria must match.

        Example::

            with ev.rule("Supporting Evidence", weight=5) as rule:
                with rule.at_least_of(2) as group:
                    group.condition(cs_dx)
                    group.drug(cs_drug)
                    group.measurement(cs_lab)
        """
        new_group = GroupConfig(type="AT_LEAST", count=count)
        self._group.criteria.append(new_group)
        return CriteriaGroupBuilder(self, new_group)

    def at_most_of(self, count: int) -> CriteriaGroupBuilder:
        """Create a nested group where at most *count* criteria may match.

        Example::

            with ev.rule("Rare Side Effect", weight=-3) as rule:
                with rule.at_most_of(1) as group:
                    group.condition(cs_side_effect_a)
                    group.condition(cs_side_effect_b)
        """
        new_group = GroupConfig(type="AT_MOST", count=count)
        self._group.criteria.append(new_group)
        return CriteriaGroupBuilder(self, new_group)

    def _build_rule(self) -> EvaluationRule:
        """Convert builder state to EvaluationRule model."""
        return EvaluationRule(
            rule_id=self._rule_id,
            name=self._name,
            description=self._description,
            weight=self._weight,
            category=self._category,
            expression=_build_criteria_group(self._group),
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
        type=group_cfg.type, count=group_cfg.count, criteria_list=criteria_list, groups=groups
    )


def _build_correlated_criteria(criteria_cfg: CriteriaConfig) -> CorelatedCriteria:
    config = criteria_cfg.query_config
    query_criteria = _config_to_criteria(config)

    # Occurrence
    type_map = {"exactly": 0, "atMost": 1, "atLeast": 2}
    occ_type = type_map.get(config.occurrence_type, 2)
    occurrence = Occurrence(
        type=occ_type,
        count=config.occurrence_count if config.occurrence_count is not None else 1,
        is_distinct=config.is_distinct,
    )

    # Window
    start_window = None
    if config.time_window:
        tw = config.time_window
        start_window = Window(
            use_index_end=tw.use_index_end,
            use_event_end=tw.use_event_end,
            start=WindowBound(coeff=-1, days=tw.days_before),
            end=WindowBound(coeff=1, days=tw.days_after),
        )

    return CorelatedCriteria(
        criteria=query_criteria,
        start_window=start_window,
        occurrence=occurrence,
        restrict_visit=config.restrict_visit,
        ignore_observation_period=config.ignore_observation_period,
    )


def _apply_numeric_range(
    config: QueryConfig, kwargs: dict, config_min_field: str, config_max_field: str, criteria_field: str
):
    """Helper to apply numeric range from config to kwargs."""
    min_val = getattr(config, config_min_field, None)
    max_val = getattr(config, config_max_field, None)

    if min_val is not None and max_val is not None:
        kwargs[criteria_field] = NumericRange(op="bt", value=min_val, extent=max_val)
    elif min_val is not None:
        kwargs[criteria_field] = NumericRange(op="gte", value=min_val)
    elif max_val is not None:
        kwargs[criteria_field] = NumericRange(op="lte", value=max_val)


def _config_to_criteria(config: QueryConfig):
    domain_map = {
        "ConditionOccurrence": ConditionOccurrence,
        "DrugExposure": DrugExposure,
        "Measurement": Measurement,
        "ProcedureOccurrence": ProcedureOccurrence,
        "VisitOccurrence": VisitOccurrence,
        "Observation": Observation,
        "Death": Death,
        "ConditionEra": ConditionEra,
        "DrugEra": DrugEra,
        "DoseEra": DoseEra,
        "DeviceExposure": DeviceExposure,
        "Specimen": Specimen,
        "ObservationPeriod": ObservationPeriod,
        "PayerPlanPeriod": PayerPlanPeriod,
        "LocationRegion": LocationRegion,
        "VisitDetail": VisitDetail,
    }
    cls = domain_map.get(config.domain)
    if not cls:
        raise ValueError(f"Unsupported domain: {config.domain}")

    kwargs = {"codeset_id": config.concept_set_id}
    if hasattr(cls, "first") or "first" in cls.model_fields:
        kwargs["first"] = config.first_occurrence

    # Helper for standard concepts
    def get_concepts(concept_ids):
        # Human-readable names for standard genders to help markdown report without DB
        genders = {8507: "MALE", 8532: "FEMALE"}
        return [Concept(concept_id=cid, concept_name=genders.get(cid)) for cid in concept_ids]

    # Map QueryConfig fields to Criteria fields if they exist in the model
    field_map = {
        "gender_concepts": "gender",
        "visit_type_concepts": "visit_type",
        "condition_type_concepts": "condition_type",
        "drug_type_concepts": "drug_type",
        "procedure_type_concepts": "procedure_type",
        "measurement_type_concepts": "measurement_type",
        "observation_type_concepts": "observation_type",
        "device_type_concepts": "device_type",
        "unit_concepts": "unit",
        "value_as_concept_concepts": "value_as_concept",
        "status_concepts": "status",
        "procedure_modifier_concepts": "modifier",
    }

    for config_field, criteria_field in field_map.items():
        val = getattr(config, config_field, None)
        if val and criteria_field in cls.model_fields:
            kwargs[criteria_field] = get_concepts(val)

    # Handle Age using generic helper
    if (config.age_min is not None or config.age_max is not None) and "age" in cls.model_fields:
        _apply_numeric_range(config, kwargs, "age_min", "age_max", "age")

    # Handle value_as_number for both Measurement and Observation using generic helper
    if (
        config.domain in ("Measurement", "Observation")
        and (config.value_min is not None or config.value_max is not None)
        and "value_as_number" in cls.model_fields
    ):
        _apply_numeric_range(config, kwargs, "value_min", "value_max", "value_as_number")

    # Handle Measurement-specific abnormal flag
    if config.domain == "Measurement" and config.abnormal is not None and "abnormal" in cls.model_fields:
        kwargs["abnormal"] = config.abnormal

    return cls(**{k: v for k, v in kwargs.items() if v is not None})
