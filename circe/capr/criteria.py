"""Capr-style builders that construct real Circepy cohort models.

Mirrors R's Capr 3.0.0 API, but produces
:class:`~circe.cohortdefinition.cohort.CohortExpression` instances so a cohort
built here flows straight into the existing SQL builders and execution pipeline.

Deliberate differences from R Capr are documented in ``circe/capr/README.md``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from ..cohortdefinition.cohort import CohortExpression
from ..cohortdefinition.core import (
    CollapseSettings,
    CustomEraStrategy,
    DateAdjustment,
    DateOffsetStrategy,
    DateType,
    NumericRange,
    Period,
    ResultLimit,
    TextFilter,
)
from ..cohortdefinition.criteria import (
    ConditionEra,
    ConditionOccurrence,
    CriteriaGroup,
    Death,
    DeviceExposure,
    DoseEra,
    DrugEra,
    DrugExposure,
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
from ..vocabulary.concept import Concept
from .concept_set import CaprConceptSet

__all__ = [
    # operators
    "lt",
    "lte",
    "gt",
    "gte",
    "eq",
    "bt",
    "nbt",
    # windows
    "event_starts",
    "event_ends",
    "during_interval",
    "continuous_observation",
    # criteria
    "exactly",
    "at_least",
    "at_most",
    # groups
    "with_all",
    "with_any",
    "with_at_least",
    "with_at_most",
    "nested_with_all",
    "nested_with_any",
    "nested_with_at_least",
    "nested_with_at_most",
    # attributes
    "age",
    "male",
    "female",
    "gender_concepts",
    "first_occurrence",
    "start_date",
    "end_date",
    "date_adjustment",
    "value_as_number",
    "value_as_string",
    "measurement_unit",
    "days_of_supply",
    "drug_refills",
    "drug_quantity",
    "range_low",
    "range_high",
    "condition_type",
    "condition_type_exclude",
    "condition_source_concept",
    "visit_type",
    "provider_specialty_concepts",
    # exit and era
    "observation_exit",
    "fixed_exit",
    "drug_exit",
    "censoring_events",
    "era",
    # assembly
    "entry",
    "attrition",
    "exit",
    "cohort",
    "to_cohort_expression",
    "to_cohort_json",
    "validate",
    "CaprError",
    "INF",
    # public model classes
    "Cohort",
    "CohortEntry",
    "CohortAttrition",
    "CohortExit",
    "CohortEra",
    "InclusionRule",
    "Group",
    "Criterion",
    "EventAperture",
    "ObservationWindow",
    "ObservationExit",
    "FixedDurationExit",
    "DrugExposureExit",
    "CensoringCriteria",
]

INF = math.inf

_MALE_ID = 8507
_FEMALE_ID = 8532


class CaprError(ValueError):
    """Raised for invalid cohort definitions."""


# ---------------------------------------------------------------------------
# Comparison operators
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Op:
    op: str
    value: Any
    extent: Any = None


def lt(x: Any) -> _Op:
    """Less than."""
    return _Op("lt", x)


def lte(x: Any) -> _Op:
    """Less than or equal to."""
    return _Op("lte", x)


def gt(x: Any) -> _Op:
    """Greater than."""
    return _Op("gt", x)


def gte(x: Any) -> _Op:
    """Greater than or equal to."""
    return _Op("gte", x)


def eq(x: Any) -> _Op:
    """Equal to."""
    return _Op("eq", x)


def bt(x: Any, y: Any) -> _Op:
    """Between, inclusive."""
    return _Op("bt", x, y)


def nbt(x: Any, y: Any) -> _Op:
    """Not between."""
    return _Op("nbt", x, y)


def _numeric_range(op: _Op) -> NumericRange:
    if not isinstance(op, _Op):
        raise CaprError("expected a comparison operator such as gte(18)")
    kwargs: dict[str, Any] = {"Op": op.op, "Value": op.value}
    if op.op in ("bt", "nbt"):
        kwargs["Extent"] = op.extent
    return NumericRange(**kwargs)


def _date_range(op: _Op) -> Any:
    from ..cohortdefinition.core import DateRange

    if not isinstance(op, _Op):
        raise CaprError("expected a comparison operator such as gt(date(...))")
    kwargs: dict[str, Any] = {"Op": op.op, "Value": _iso(op.value)}
    if op.op in ("bt", "nbt"):
        kwargs["Extent"] = _iso(op.extent)
    return DateRange(**kwargs)


def _iso(value: Any) -> Any:
    if value is None:
        return None
    isoformat = getattr(value, "isoformat", None)
    return isoformat()[:10] if isoformat is not None else str(value)[:10]


# ---------------------------------------------------------------------------
# Attributes
# ---------------------------------------------------------------------------


class _Attribute:
    """Base for anything accepted in a query's attribute position."""

    def as_criteria_kwargs(self) -> dict[str, Any]:
        raise NotImplementedError


@dataclass(frozen=True)
class _NumericAttribute(_Attribute):
    key: str
    op: _Op

    def as_criteria_kwargs(self) -> dict[str, Any]:
        return {self.key: _numeric_range(self.op)}


@dataclass(frozen=True)
class _DateAttribute(_Attribute):
    key: str
    op: _Op

    def as_criteria_kwargs(self) -> dict[str, Any]:
        return {self.key: _date_range(self.op)}


@dataclass(frozen=True)
class _ConceptAttribute(_Attribute):
    key: str
    ids: tuple[int, ...]
    # Populated for the gender helpers, which carry the full vocabulary record
    # so Atlas can render the criterion.
    concepts: tuple[Concept, ...] = ()

    def as_criteria_kwargs(self) -> dict[str, Any]:
        if self.concepts:
            return {self.key: list(self.concepts)}
        return {self.key: [_concept(i) for i in self.ids]}


@dataclass(frozen=True)
class _FlagAttribute(_Attribute):
    key: str
    value: bool = True

    def as_criteria_kwargs(self) -> dict[str, Any]:
        return {self.key: self.value}


@dataclass(frozen=True)
class _ConceptSetRefAttribute(_Attribute):
    """Attributes serialized as an inline concept list (not a CodesetId)."""

    key: str
    concept_set: CaprConceptSet

    def as_criteria_kwargs(self) -> dict[str, Any]:
        return {self.key: [item.concept for item in self.concept_set.items]}


@dataclass(frozen=True)
class _TextAttribute(_Attribute):
    key: str
    text: str
    op: str = "contains"

    def as_criteria_kwargs(self) -> dict[str, Any]:
        return {self.key: TextFilter(Text=self.text, Op=self.op)}


@dataclass(frozen=True)
class _DateAdjustmentAttribute(_Attribute):
    start_with: str = "START_DATE"
    start_offset: int = 0
    end_with: str = "END_DATE"
    end_offset: int = 0

    def as_criteria_kwargs(self) -> dict[str, Any]:
        return {
            "DateAdjustment": DateAdjustment(
                startWith=_date_type(self.start_with),
                startOffset=int(self.start_offset),
                endWith=_date_type(self.end_with),
                endOffset=int(self.end_offset),
            )
        }


@dataclass(frozen=True)
class _NestedAttribute(_Attribute):
    group: Group

    def as_criteria_kwargs(self) -> dict[str, Any]:
        # Deferred: the concept-set ids are only known during compilation, so
        # return a placeholder the query builder resolves.
        return {"CorrelatedCriteria": _DeferredGroup(self.group)}


def _concept(concept_id: int, **kwargs: Any) -> Concept:
    return Concept(CONCEPT_ID=int(concept_id), **kwargs)


def _date_type(value: str) -> DateType:
    return DateType.END_DATE if value.upper().startswith("END") else DateType.START_DATE


def age(op: _Op) -> _NumericAttribute:
    """Age at the event date."""
    return _NumericAttribute("Age", op)


_MALE_CONCEPT = Concept(
    CONCEPT_ID=_MALE_ID,
    CONCEPT_NAME="MALE",
    CONCEPT_CODE="M",
    DOMAIN_ID="Gender",
    VOCABULARY_ID="Gender",
    CONCEPT_CLASS_ID="Gender",
)
_FEMALE_CONCEPT = Concept(
    CONCEPT_ID=_FEMALE_ID,
    CONCEPT_NAME="FEMALE",
    CONCEPT_CODE="F",
    DOMAIN_ID="Gender",
    VOCABULARY_ID="Gender",
    CONCEPT_CLASS_ID="Gender",
)


def male() -> _ConceptAttribute:
    """Male patients (gender concept 8507)."""
    return _ConceptAttribute("Gender", (_MALE_ID,), (_MALE_CONCEPT,))


def female() -> _ConceptAttribute:
    """Female patients (gender concept 8532)."""
    return _ConceptAttribute("Gender", (_FEMALE_ID,), (_FEMALE_CONCEPT,))


def gender_concepts(*ids: int) -> _ConceptAttribute:
    """Patients whose gender is one of the given concept ids."""
    return _ConceptAttribute("Gender", tuple(int(i) for i in ids))


def first_occurrence() -> _FlagAttribute:
    """Restrict to the first occurrence of the event in the patient's history."""
    return _FlagAttribute("First", True)


def start_date(op: _Op, type: str = "occurrence") -> _DateAttribute:
    """Filter on the event start date (``occurrence`` or ``era``)."""
    key = "EraStartDate" if type == "era" else "OccurrenceStartDate"
    return _DateAttribute(key, op)


def end_date(op: _Op, type: str = "occurrence") -> _DateAttribute:
    """Filter on the event end date (``occurrence`` or ``era``)."""
    key = "EraEndDate" if type == "era" else "OccurrenceEndDate"
    return _DateAttribute(key, op)


def date_adjustment(
    start_with: str = "START_DATE",
    start_offset: int = 0,
    end_with: str = "END_DATE",
    end_offset: int = 0,
) -> _DateAdjustmentAttribute:
    """Shift the event's effective dates before criteria matching."""
    return _DateAdjustmentAttribute(start_with, int(start_offset), end_with, int(end_offset))


def value_as_number(op: _Op) -> _NumericAttribute:
    """Filter on ``value_as_number``."""
    return _NumericAttribute("ValueAsNumber", op)


def value_as_string(text: str, op: str = "contains") -> _TextAttribute:
    """Filter on ``value_as_string``; ``op`` is contains/starts/ends/equals."""
    return _TextAttribute("ValueAsString", text, op)


def measurement_unit(ids: int | tuple[int, ...]) -> _ConceptAttribute:
    """Filter measurements by unit concept id."""
    if isinstance(ids, int):
        ids = (ids,)
    return _ConceptAttribute("Unit", tuple(int(i) for i in ids))


def days_of_supply(op: _Op) -> _NumericAttribute:
    """Filter on ``days_supply``."""
    return _NumericAttribute("DaysSupply", op)


def drug_refills(op: _Op) -> _NumericAttribute:
    """Filter on ``refills``."""
    return _NumericAttribute("Refills", op)


def drug_quantity(op: _Op) -> _NumericAttribute:
    """Filter on ``quantity``."""
    return _NumericAttribute("Quantity", op)


def range_low(op: _Op) -> _NumericAttribute:
    """Filter on ``range_low``."""
    return _NumericAttribute("RangeLow", op)


def range_high(op: _Op) -> _NumericAttribute:
    """Filter on ``range_high``."""
    return _NumericAttribute("RangeHigh", op)


def condition_type(ids: int | tuple[int, ...]) -> _ConceptAttribute:
    """Filter on ``condition_type_concept_id`` (record provenance)."""
    if isinstance(ids, int):
        ids = (ids,)
    return _ConceptAttribute("ConditionType", tuple(int(i) for i in ids))


def condition_type_exclude(exclude: bool = False) -> _FlagAttribute:
    """Invert the condition type filter."""
    return _FlagAttribute("ConditionTypeExclude", bool(exclude))


def condition_source_concept(concept_set: CaprConceptSet) -> _ConceptSetRefAttribute:
    """Filter on ``condition_source_concept_id`` using an inline concept list."""
    if not isinstance(concept_set, CaprConceptSet):
        raise CaprError("condition_source_concept() expects a concept set from cs()")
    return _ConceptSetRefAttribute("ConditionSourceConcept", concept_set)


def visit_type(ids: int | tuple[int, ...]) -> _ConceptAttribute:
    """Filter on ``visit_type_concept_id`` (provenance, not care setting)."""
    if isinstance(ids, int):
        ids = (ids,)
    return _ConceptAttribute("VisitType", tuple(int(i) for i in ids))


def provider_specialty_concepts(*ids: int) -> _ConceptAttribute:
    """Filter visits by provider specialty concept id."""
    return _ConceptAttribute("ProviderSpecialty", tuple(int(i) for i in ids))


# ---------------------------------------------------------------------------
# Windows and criteria
# ---------------------------------------------------------------------------


def _bound(days: float) -> tuple[int | None, int]:
    """Capr stores the magnitude plus a sign; 0 counts as negative."""
    sign = -1 if days <= 0 else 1
    magnitude = abs(days)
    return (None if math.isinf(magnitude) else int(magnitude)), sign


def _window(a: float, b: float, index: str, event: str) -> WindowedSpec:
    return WindowedSpec(a=a, b=b, index=index, event=event)


@dataclass(frozen=True)
class WindowedSpec:
    """An ``eventStarts``/``eventEnds`` window before it becomes a model."""

    a: float
    b: float
    index: str = "startDate"
    event: str = "start"

    def to_window(self) -> Any:
        from ..cohortdefinition.core import Window, WindowBound

        start_days, start_coeff = _bound(self.a)
        end_days, end_coeff = _bound(self.b)
        return Window(
            Start=WindowBound(Coeff=start_coeff, Days=start_days),
            End=WindowBound(Coeff=end_coeff, Days=end_days),
            UseEventEnd=self.event == "end",
            UseIndexEnd=self.index == "endDate",
        )


def event_starts(a: float, b: float, index: str = "startDate") -> WindowedSpec:
    """Window on where the related event starts, in days relative to index."""
    return _window(a, b, index, "start")


def event_ends(a: float, b: float, index: str = "startDate") -> WindowedSpec:
    """Window on where the related event ends, in days relative to index."""
    return _window(a, b, index, "end")


@dataclass(frozen=True)
class EventAperture:
    """The assessment window for a criterion."""

    start_window: WindowedSpec
    end_window: WindowedSpec | None = None
    restrict_visit: bool = False
    ignore_observation_period: bool = False

    def to_kwargs(self) -> dict[str, Any]:
        out: dict[str, Any] = {"StartWindow": self.start_window.to_window()}
        if self.end_window is not None:
            out["EndWindow"] = self.end_window.to_window()
        if self.restrict_visit:
            out["RestrictVisit"] = True
        if self.ignore_observation_period:
            out["IgnoreObservationPeriod"] = True
        return out


def during_interval(
    start_window: WindowedSpec,
    end_window: WindowedSpec | None = None,
    restrict_visit: bool = False,
    ignore_observation_period: bool = False,
) -> EventAperture:
    """Define when the related event must occur."""
    return EventAperture(start_window, end_window, restrict_visit, ignore_observation_period)


@dataclass(frozen=True)
class ObservationWindow:
    """Required continuous observation around the index event."""

    prior_days: int = 0
    post_days: int = 0


def continuous_observation(prior_days: int = 0, post_days: int = 0) -> ObservationWindow:
    """Require continuous observation before/after index."""
    return ObservationWindow(int(prior_days), int(post_days))


_OCCURRENCE_CODES = {"exactly": 0, "atMost": 1, "atLeast": 2}


@dataclass(frozen=True)
class Criterion:
    """A query wrapped with a count and an aperture."""

    query: Any
    kind: str
    count: int
    aperture: EventAperture
    distinct: bool | None = None
    count_column: str | None = None

    def to_occurrence(self) -> Occurrence:
        kwargs: dict[str, Any] = {
            "Type": _OCCURRENCE_CODES[self.kind],
            "Count": int(self.count),
        }
        if self.distinct:
            kwargs["IsDistinct"] = True
        if self.count_column:
            kwargs["CountColumn"] = self.count_column
        return Occurrence(**kwargs)

    def to_corelated(self, ids: dict[str, int] | None = None) -> Any:
        from ..cohortdefinition.criteria import CorelatedCriteria

        return CorelatedCriteria(
            Criteria=_build_query(self.query, ids or {}),
            Occurrence=self.to_occurrence(),
            **self.aperture.to_kwargs(),
        )


def _criterion(kind: str, x: int, query: Any, aperture: EventAperture | None, **kwargs: Any) -> Criterion:
    if query is None:
        raise CaprError(f"{kind}() requires a query")
    if aperture is None:
        aperture = EventAperture(event_starts(-INF, INF))
    if kwargs.get("distinct") and not kwargs.get("count_column"):
        raise CaprError("count_column is required when distinct=True")
    return Criterion(query, kind, int(x), aperture, kwargs.get("distinct"), kwargs.get("count_column"))


def exactly(
    x: int,
    query: Any,
    aperture: EventAperture | None = None,
    distinct: bool | None = None,
    count_column: str | None = None,
) -> Criterion:
    """Require exactly ``x`` occurrences of ``query`` within ``aperture``."""
    return _criterion("exactly", x, query, aperture, distinct=distinct, count_column=count_column)


def at_least(
    x: int,
    query: Any,
    aperture: EventAperture | None = None,
    distinct: bool | None = None,
    count_column: str | None = None,
) -> Criterion:
    """Require at least ``x`` occurrences."""
    return _criterion("atLeast", x, query, aperture, distinct=distinct, count_column=count_column)


def at_most(
    x: int,
    query: Any,
    aperture: EventAperture | None = None,
    distinct: bool | None = None,
    count_column: str | None = None,
) -> Criterion:
    """Require at most ``x`` occurrences."""
    return _criterion("atMost", x, query, aperture, distinct=distinct, count_column=count_column)


_GROUP_TYPES = {
    "all": "ALL",
    "any": "ANY",
    "atLeast": "AT_LEAST",
    "atMost": "AT_MOST",
}


@dataclass(frozen=True)
class Group:
    """Criteria, subgroups and demographic attributes combined by a logical operator."""

    type: str
    items: tuple[Any, ...] = ()
    count: int | None = None

    def to_criteria_group(self, ids: dict[str, int] | None = None) -> CriteriaGroup:
        from ..cohortdefinition.criteria import DemographicCriteria

        kwargs: dict[str, Any] = {"Type": _GROUP_TYPES[self.type]}
        if self.count is not None:
            kwargs["Count"] = int(self.count)

        corelated = [i.to_corelated(ids) for i in self.items if isinstance(i, Criterion)]
        subgroups = [i.to_criteria_group(ids) for i in self.items if isinstance(i, Group)]
        demographics = [i for i in self.items if isinstance(i, _Attribute)]

        if corelated:
            kwargs["CriteriaList"] = corelated
        if subgroups:
            kwargs["Groups"] = subgroups
        if demographics:
            demo: dict[str, Any] = {}
            for attr in demographics:
                demo.update(attr.as_criteria_kwargs())
            kwargs["DemographicCriteriaList"] = [DemographicCriteria(**demo)]
        return CriteriaGroup(**kwargs)


def _group(kind: str, x: int | None, items: tuple[Any, ...]) -> Group:
    for item in items:
        if not isinstance(item, (Criterion, Group, _Attribute)):
            raise CaprError(
                f"group items must be criteria, groups or demographic attributes, got {type(item).__name__}"
            )
    return Group(kind, items, x)


def with_all(*items: Any) -> Group:
    """All items must be satisfied."""
    return _group("all", None, items)


def with_any(*items: Any) -> Group:
    """At least one item must be satisfied."""
    return _group("any", None, items)


def with_at_least(x: int, *items: Any) -> Group:
    """At least ``x`` of the items must be satisfied."""
    return _group("atLeast", int(x), items)


def with_at_most(x: int, *items: Any) -> Group:
    """At most ``x`` of the items must be satisfied."""
    return _group("atMost", int(x), items)


def nested_with_all(*items: Any) -> _NestedAttribute:
    """Correlated criteria evaluated relative to the query's own event."""
    return _NestedAttribute(with_all(*items))


def nested_with_any(*items: Any) -> _NestedAttribute:
    """Correlated criteria where any item must hold."""
    return _NestedAttribute(with_any(*items))


def nested_with_at_least(x: int, *items: Any) -> _NestedAttribute:
    """Correlated criteria where at least ``x`` items must hold."""
    return _NestedAttribute(with_at_least(x, *items))


def nested_with_at_most(x: int, *items: Any) -> _NestedAttribute:
    """Correlated criteria where at most ``x`` items must hold."""
    return _NestedAttribute(with_at_most(x, *items))


# ---------------------------------------------------------------------------
# Domain queries
# ---------------------------------------------------------------------------

_DOMAIN_CLASSES: dict[str, Any] = {
    "condition_occurrence": ConditionOccurrence,
    "condition_era": ConditionEra,
    "drug_exposure": DrugExposure,
    "drug_era": DrugEra,
    "dose_era": DoseEra,
    "measurement": Measurement,
    "observation": Observation,
    "procedure": ProcedureOccurrence,
    "visit": VisitOccurrence,
    "visit_detail": VisitDetail,
    "device": DeviceExposure,
    "specimen": Specimen,
    "death": Death,
    "observation_period": ObservationPeriod,
    "payer_plan_period": PayerPlanPeriod,
}

_OPTIONAL_CONCEPT_SET = {"death", "observation_period"}


@dataclass(frozen=True)
class _Query:
    """A pending domain query: concept set plus attributes, not yet a model."""

    domain: str
    concept_set: CaprConceptSet | None
    attributes: tuple[Any, ...] = field(default_factory=tuple)

    def build(self) -> Any:
        cls = _DOMAIN_CLASSES[self.domain]
        kwargs: dict[str, Any] = {}
        for attr in self.attributes:
            kwargs.update(attr.as_criteria_kwargs())
        if self.concept_set is not None and self.concept_set.items:
            kwargs["CodesetId"] = self.concept_set
        return _DeferredQuery(cls, kwargs, kwargs.get("CodesetId"))


class _DeferredQuery:
    """Wraps a criteria class + kwargs, resolving the concept set to an int on compile."""

    __slots__ = ("cls", "kwargs", "_concept_set")

    def __init__(self, cls: Any, kwargs: dict[str, Any], concept_set: Any) -> None:
        self.cls = cls
        self.kwargs = kwargs
        self._concept_set = concept_set

    @property
    def concept_set(self) -> CaprConceptSet | None:
        value = self._concept_set
        return value if isinstance(value, CaprConceptSet) else None

    def with_codeset_id(self, codeset_id: int | None) -> Any:
        kwargs = dict(self.kwargs)
        kwargs.pop("CodesetId", None)
        if codeset_id is not None:
            kwargs["CodesetId"] = codeset_id
        return self.cls(**kwargs)


def _make_domain(name: str):
    def factory(concept_set: Any = None, *attributes: Any) -> _Query:
        requires_cs = name not in _OPTIONAL_CONCEPT_SET
        if not requires_cs and concept_set is not None and not isinstance(concept_set, CaprConceptSet):
            attributes = (concept_set, *attributes)
            concept_set = None
        if concept_set is not None and not isinstance(concept_set, CaprConceptSet):
            raise CaprError(f"{name}() expects a concept set from cs(), got {type(concept_set).__name__}")
        if concept_set is None and requires_cs:
            raise CaprError(f"{name}() requires a concept set")
        for attr in attributes:
            if not isinstance(attr, _Attribute):
                raise CaprError(f"{name}() attributes must be attribute objects, got {type(attr).__name__}")
        return _Query(name, concept_set, tuple(attributes))

    factory.__name__ = name
    factory.__doc__ = f"Query the {name.replace('_', ' ')} domain."
    return factory


for _domain in _DOMAIN_CLASSES:
    globals()[_domain] = _make_domain(_domain)
    __all__.append(_domain)


# ---------------------------------------------------------------------------
# Entry / attrition / exit / era
# ---------------------------------------------------------------------------

_LIMITS = ("First", "All", "Last")


@dataclass(frozen=True)
class CohortEntry:
    """Index events plus the required observation window."""

    events: tuple[_Query, ...]
    observation_window: ObservationWindow = field(default_factory=ObservationWindow)
    primary_criteria_limit: str = "First"
    additional_criteria: Group | None = None
    qualified_limit: str | None = None


def entry(
    *events: _Query,
    observation_window: ObservationWindow | None = None,
    primary_criteria_limit: str = "First",
    additional_criteria: Group | None = None,
    qualified_limit: str | None = None,
) -> CohortEntry:
    """Define the index event(s) and qualifying conditions."""
    if not events:
        raise CaprError("entry() requires at least one query")
    for event in events:
        if not isinstance(event, _Query):
            raise CaprError(
                "entry() only accepts queries, not "
                f"{type(event).__name__}. Pass the query itself, e.g. "
                "condition_occurrence(cs) without wrapping it in at_least()."
            )
    if primary_criteria_limit not in _LIMITS:
        raise CaprError(f"primary_criteria_limit must be one of {_LIMITS}")
    if additional_criteria is not None and qualified_limit is None:
        raise CaprError("qualified_limit must be provided when additional_criteria is used.")
    return CohortEntry(
        events=events,
        observation_window=observation_window or ObservationWindow(),
        primary_criteria_limit=primary_criteria_limit,
        additional_criteria=additional_criteria,
        qualified_limit=qualified_limit or primary_criteria_limit,
    )


@dataclass(frozen=True)
class InclusionRule:
    """A named inclusion/exclusion rule."""

    name: str
    group: Group


@dataclass(frozen=True)
class CohortAttrition:
    """The ordered inclusion rules and the limit applied after them."""

    rules: tuple[InclusionRule, ...] = field(default_factory=tuple)
    expression_limit: str = "First"


def attrition(expression_limit: str = "First", **rules: Group) -> CohortAttrition:
    """Define named inclusion/exclusion rules.

    Each rule must be a group (``with_all``, ``with_any``, ``with_at_least``,
    ``with_at_most``). R's Capr accepts a bare criterion here and silently
    writes an inclusion rule Atlas cannot render; this raises instead.
    """
    if expression_limit not in _LIMITS:
        raise CaprError(f"expression_limit must be one of {_LIMITS}")
    parsed: list[InclusionRule] = []
    for name, group in rules.items():
        if not isinstance(group, Group):
            raise CaprError(
                f"attrition rule {name!r} must be a group "
                f"(with_all/with_any/with_at_least/with_at_most), got {type(group).__name__}"
            )
        parsed.append(InclusionRule(name, group))
    return CohortAttrition(tuple(parsed), expression_limit)


@dataclass(frozen=True)
class ObservationExit:
    """Exit at the end of continuous observation (the default)."""


@dataclass(frozen=True)
class FixedDurationExit:
    """Exit a fixed number of days after the index event."""

    index: str = "startDate"
    offset_days: int = 0


@dataclass(frozen=True)
class DrugExposureExit:
    """Exit at the end of a continuous drug era."""

    concept_set: CaprConceptSet
    persistence_window: int = 0
    surveillance_window: int = 0
    days_supply_override: int | None = None


@dataclass(frozen=True)
class CensoringCriteria:
    """Events that end the cohort episode early."""

    queries: tuple[_Query, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CohortExit:
    """The end strategy plus optional censoring events."""

    end_strategy: Any = field(default_factory=ObservationExit)
    censor: CensoringCriteria | None = None


def observation_exit() -> ObservationExit:
    """Exit at the end of continuous observation."""
    return ObservationExit()


def fixed_exit(index: str = "startDate", offset_days: int = 0, **kwargs: Any) -> FixedDurationExit:
    """Exit ``offset_days`` after the index event's start or end date."""
    if "offsetDays" in kwargs:
        offset_days = kwargs.pop("offsetDays")
    if kwargs:
        raise TypeError(f"fixed_exit() got unexpected arguments: {', '.join(kwargs)}")
    return FixedDurationExit(index=index, offset_days=int(offset_days))


def drug_exit(
    concept_set: CaprConceptSet,
    persistence_window: int = 0,
    surveillance_window: int = 0,
    days_supply_override: int | None = None,
) -> DrugExposureExit:
    """Exit at the end of a continuous drug exposure era."""
    if not isinstance(concept_set, CaprConceptSet):
        raise CaprError("drug_exit() expects a concept set from cs()")
    return DrugExposureExit(
        concept_set=concept_set,
        persistence_window=int(persistence_window),
        surveillance_window=int(surveillance_window),
        days_supply_override=days_supply_override,
    )


def censoring_events(*queries: _Query) -> CensoringCriteria:
    """Events that cut a cohort episode short."""
    for query in queries:
        if not isinstance(query, _Query):
            raise CaprError("censoring_events() expects queries")
    return CensoringCriteria(queries)


def exit(end_strategy: Any = None, censor: CensoringCriteria | None = None) -> CohortExit:
    """Wrap an end strategy and optional censoring criteria."""
    return CohortExit(end_strategy or ObservationExit(), censor)


@dataclass(frozen=True)
class CohortEra:
    """Era-collapse padding and an optional study period window."""

    era_days: int = 0
    study_start_date: Any = None
    study_end_date: Any = None


def era(era_days: int = 0, study_start_date: Any = None, study_end_date: Any = None) -> CohortEra:
    """Set the era-collapse gap and optional study date window."""
    return CohortEra(
        int(era_days),
        _iso(study_start_date) if study_start_date else None,
        _iso(study_end_date) if study_end_date else None,
    )


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Cohort:
    """A complete cohort definition."""

    entry: CohortEntry
    attrition: CohortAttrition = field(default_factory=CohortAttrition)
    exit: CohortExit = field(default_factory=CohortExit)
    era: CohortEra = field(default_factory=CohortEra)


def cohort(
    entry: Any,
    attrition: CohortAttrition | None = None,
    exit: CohortExit | None = None,
    era: CohortEra | None = None,
) -> Cohort:
    """Assemble a cohort definition.

    ``entry`` is a :class:`CohortEntry` from :func:`entry`. A bare query is also
    accepted and wrapped, for convenience.
    """
    if isinstance(entry, _Query):
        entry = globals()["entry"](entry)
    if not isinstance(entry, CohortEntry):
        raise CaprError(f"cohort() requires the result of entry(...) or a query, got {type(entry).__name__}")
    return Cohort(
        entry=entry,
        attrition=attrition or CohortAttrition(),
        exit=exit or CohortExit(),
        era=era or CohortEra(),
    )


def _collect_concept_sets(cd: Cohort) -> list[CaprConceptSet]:
    """Walk the tree collecting concept sets in first-encounter order."""
    ordered: list[CaprConceptSet] = []
    seen: set[str] = set()

    def register(concept_set: CaprConceptSet | None) -> None:
        if concept_set is None or not concept_set.items:
            return
        ident = concept_set.id
        if ident not in seen:
            seen.add(ident)
            ordered.append(concept_set)

    def walk_query(query: Any) -> None:
        if not isinstance(query, _Query):
            return
        register(query.concept_set)
        for attr in query.attributes:
            if isinstance(attr, _ConceptSetRefAttribute):
                register(attr.concept_set)
            elif isinstance(attr, _NestedAttribute):
                walk_group(attr.group)

    def walk_group(group: Group | None) -> None:
        if group is None:
            return
        for item in group.items:
            if isinstance(item, Group):
                walk_group(item)
            elif isinstance(item, Criterion):
                walk_query(item.query)

    for event in cd.entry.events:
        walk_query(event)
    walk_group(cd.entry.additional_criteria)
    for rule in cd.attrition.rules:
        walk_group(rule.group)
    if isinstance(cd.exit.end_strategy, DrugExposureExit):
        register(cd.exit.end_strategy.concept_set)
    if cd.exit.censor is not None:
        for query in cd.exit.censor.queries:
            walk_query(query)
    return ordered


def _build_criteria(query: Any, ids: dict[str, int]) -> Any:
    if not isinstance(query, _DeferredQuery):
        return query
    concept_set = query.concept_set
    codeset_id = None
    if concept_set is not None and concept_set.items:
        codeset_id = ids[concept_set.id]
    return query.with_codeset_id(codeset_id)


def _build_group(group: Group, ids: dict[str, int]) -> CriteriaGroup:
    """Compile a :class:`Group` into a :class:`CriteriaGroup` with resolved ids."""
    return group.to_criteria_group(ids)


@dataclass(frozen=True)
class _DeferredGroup:
    """A criteria group whose concept-set ids are resolved at compile time."""

    group: Group


def _resolve_kwargs(kwargs: dict[str, Any], ids: dict[str, int]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in kwargs.items():
        out[key] = _build_group(value.group, ids) if isinstance(value, _DeferredGroup) else value
    return out


def _build_query(query: Any, ids: dict[str, int]) -> Any:
    if isinstance(query, _DeferredQuery):
        kwargs = _resolve_kwargs(query.kwargs, ids)
        kwargs.pop("CodesetId", None)
        if query.concept_set is not None and query.concept_set.items:
            kwargs["CodesetId"] = ids[query.concept_set.id]
        return query.cls(**kwargs)
    if isinstance(query, _Query):
        cls = _DOMAIN_CLASSES[query.domain]
        kwargs = {}
        for attr in query.attributes:
            kwargs.update(attr.as_criteria_kwargs())
        kwargs = _resolve_kwargs(kwargs, ids)
        if query.concept_set is not None and query.concept_set.items:
            kwargs["CodesetId"] = ids[query.concept_set.id]
        return cls(**kwargs)
    return query


def _build_end_strategy(strategy: Any, ids: dict[str, int]) -> Any:
    if isinstance(strategy, FixedDurationExit):
        field = "EndDate" if strategy.index.lower().startswith("end") else "StartDate"
        return DateOffsetStrategy(Offset=int(strategy.offset_days), DateField=field)
    if isinstance(strategy, DrugExposureExit):
        kwargs: dict[str, Any] = {
            "DrugCodesetId": ids[strategy.concept_set.id],
            "GapDays": int(strategy.persistence_window),
            "Offset": int(strategy.surveillance_window),
        }
        if strategy.days_supply_override is not None:
            kwargs["DaysSupplyOverride"] = int(strategy.days_supply_override)
        return CustomEraStrategy(**kwargs)
    return None


def to_cohort_expression(cd: Cohort) -> CohortExpression:
    """Compile a :class:`Cohort` into a :class:`CohortExpression`.

    Concept sets are numbered ``0..n-1`` in first-encounter order, matching the
    order CIRCE expects for ``CodesetId`` references.
    """
    from ..cohortdefinition.criteria import (
        InclusionRule as ModelInclusionRule,
    )
    from ..cohortdefinition.criteria import PrimaryCriteria
    from ..vocabulary.concept import ConceptSet, ConceptSetExpression

    ordered = _collect_concept_sets(cd)
    ids = {cs_.id: index for index, cs_ in enumerate(ordered)}

    concept_sets = [
        ConceptSet(
            id=index,
            name=concept_set.name,
            expression=ConceptSetExpression(items=list(concept_set.items)),
        )
        for index, concept_set in enumerate(ordered)
    ]

    primary = PrimaryCriteria(
        CriteriaList=[_build_query(event, ids) for event in cd.entry.events],
        ObservationWindow=_observation_filter(cd.entry.observation_window),
        PrimaryCriteriaLimit=ResultLimit(Type=cd.entry.primary_criteria_limit),
    )

    inclusion_rules = [
        ModelInclusionRule(Name=rule.name, Expression=_build_group(rule.group, ids))
        for rule in cd.attrition.rules
    ]

    censoring = []
    if cd.exit.censor is not None:
        censoring = [_build_query(query, ids) for query in cd.exit.censor.queries]

    kwargs: dict[str, Any] = {
        "ConceptSets": concept_sets,
        "PrimaryCriteria": primary,
        "QualifiedLimit": ResultLimit(Type=cd.entry.qualified_limit or cd.entry.primary_criteria_limit),
        "ExpressionLimit": ResultLimit(Type=cd.attrition.expression_limit),
        "InclusionRules": inclusion_rules,
        "CensoringCriteria": censoring,
        "CollapseSettings": CollapseSettings(EraPad=cd.era.era_days),
        "cdmVersionRange": ">=5.0.0",
        "CensorWindow": Period(StartDate=cd.era.study_start_date, EndDate=cd.era.study_end_date),
    }

    if cd.entry.additional_criteria is not None:
        kwargs["AdditionalCriteria"] = _build_group(cd.entry.additional_criteria, ids)

    end_strategy = _build_end_strategy(cd.exit.end_strategy, ids)
    if end_strategy is not None:
        kwargs["EndStrategy"] = end_strategy

    return CohortExpression(**kwargs)


def _observation_filter(window: ObservationWindow) -> Any:
    from ..cohortdefinition.core import ObservationFilter

    return ObservationFilter(PriorDays=window.prior_days, PostDays=window.post_days)


def to_cohort_json(cd: Cohort, *, indent: int | None = None) -> str:
    """Compile a cohort to Circe JSON."""
    import json

    expression = to_cohort_expression(cd)
    payload = expression.model_dump()
    if indent is None:
        return json.dumps(payload, separators=(",", ":"))
    return json.dumps(payload, indent=indent)


def validate(cd: Cohort, *, strict: bool = True) -> list[str]:
    """Check for definitions that compile but quietly mean the wrong thing.

    These are the traps R's Capr lets through without error.
    """
    problems: list[str] = []
    if cd.entry.primary_criteria_limit == "All" and cd.attrition.expression_limit == "First":
        problems.append(
            "primary_criteria_limit='All' with expression_limit='First' silently "
            "collapses the cohort to one event per person"
        )
    for rule in cd.attrition.rules:
        if not isinstance(rule.group, Group):
            problems.append(f"inclusion rule {rule.name!r} is not a group")
    if cd.entry.additional_criteria is None and cd.entry.qualified_limit not in (
        None,
        cd.entry.primary_criteria_limit,
    ):
        problems.append("qualified_limit has no effect without additional_criteria")
    if strict and problems:
        raise CaprError("; ".join(problems))
    return problems
