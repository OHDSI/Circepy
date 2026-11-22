"""Circe cohort JSON -> circe.capr Python source.

A port of Capr's ``jsonToCapr()``. Where the R version emits R code, this emits
Python that builds the same definition with :mod:`circe.capr`, so a definition
exported from Atlas can be brought back into version control and re-run without
an R session.

Unsupported JSON fails in ``mode="strict"`` (the default) or is omitted with a
``# SKIPPED:`` comment in ``mode="skip"``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

__all__ = ["JsonToCaprError", "json_to_capr", "json_to_capr_file", "DecompiledCohort"]

_MISSING = object()


class JsonToCaprError(ValueError):
    """Raised when JSON cannot be decompiled (``mode="strict"``)."""


class _Emitter:
    """Collects skips/warnings or raises, mirroring Capr's emitter."""

    def __init__(self, mode: str) -> None:
        if mode not in ("strict", "skip"):
            raise ValueError("mode must be 'strict' or 'skip'")
        self.mode = mode
        self.skipped: list[str] = []
        self.empty_group_warnings: list[str] = []

    def skip_or_stop(self, message: str) -> None:
        if self.mode == "strict":
            raise JsonToCaprError(message)
        self.skipped.append(message)

    def warn_empty_group(self, context: str) -> None:
        if self.mode == "skip":
            self.empty_group_warnings.append(context)

    def header_lines(self) -> list[str]:
        lines: list[str] = []
        if self.skipped or self.empty_group_warnings:
            lines.append("# --- SKIPPED / WARNINGS (mode='skip' is UNSAFE) ---")
            lines.extend(f"# SKIPPED: {s}" for s in self.skipped)
            lines.extend(f"# WARNING: group became empty after skips: {w}" for w in self.empty_group_warnings)
            lines.append("")
        return lines


def _get(node: Any, *keys: str, default: Any = None) -> Any:
    """Fetch the first present key (JSON uses mixed casing)."""
    if not isinstance(node, dict):
        return default
    for key in keys:
        if key in node and node[key] is not None:
            return node[key]
    return default


# --- naming -------------------------------------------------------------------


def to_camel_case(text: Any) -> str:
    """Capr's ``toCamelCase``: 'Type 2 Diabetes' -> 'type2Diabetes'."""
    if not text:
        return "x"
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", str(text))
    parts = [p for p in cleaned.strip().split(" ") if p]
    if not parts:
        return "x"
    head = parts[0].lower()
    tail = "".join(p[:1].upper() + p[1:].lower() for p in parts[1:])
    return head + tail


def concept_set_var_name(name: Any, concept_set_id: Any) -> str:
    """Capr's ``makeConceptSetVarName``: cs + Capitalised(camel) + id."""
    # The unnamed fallback is used verbatim, matching Capr: "conceptSet", not
    # the camel-cased "conceptset".
    base = "conceptSet" if not name else to_camel_case(name)
    return f"cs{base[:1].upper()}{base[1:]}{concept_set_id}"


# --- scalars ------------------------------------------------------------------


def format_scalar(value: Any, *, integers_as_numeric: bool = False) -> str:
    """Render a literal as Python source."""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, (int, float)):
        if not integers_as_numeric and float(value).is_integer():
            return str(int(value))
        return repr(value)
    return repr(value)


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_date(value: Any) -> Any:
    """Capr returns a Date when the string looks like YYYY-MM-DD."""
    return value


def _concept_id(item: Any) -> int | None:
    if isinstance(item, int):
        return item
    if not isinstance(item, dict):
        return None
    inner = item.get("concept")
    if isinstance(inner, dict):
        return _get(inner, "CONCEPT_ID", "concept_id")
    return _get(item, "CONCEPT_ID", "concept_id")


def concept_list_to_ids(concepts: Any) -> list[int]:
    if not concepts:
        return []
    if isinstance(concepts, list) and all(isinstance(c, int) for c in concepts):
        return list(concepts)
    return [cid for cid in (_concept_id(c) for c in concepts) if cid is not None]


def concept_list_to_inline_cs(concepts: Any, name: str = "sourceConcepts") -> str | None:
    ids = concept_list_to_ids(concepts)
    if not ids:
        return None
    return f"capr.cs({', '.join(str(i) for i in ids)}, name={name!r})"


def _date_literal(value: Any) -> str:
    if isinstance(value, str) and _DATE_RE.match(value):
        return f'"{value}"'
    return repr(value)


# --- concept sets -------------------------------------------------------------


def _items_to_parts(items: list[dict[str, Any]]) -> list[str]:
    """Group consecutive items by their flag signature, preserving order."""
    runs: list[dict[str, Any]] = []
    for item in items:
        cid = _concept_id(item.get("concept"))
        if cid is None:
            raise JsonToCaprError("concept set item is missing a concept id")
        excluded = bool(item.get("isExcluded"))
        desc = bool(item.get("includeDescendants"))
        mapped_ = bool(item.get("includeMapped"))
        sig = (excluded, desc, mapped_)
        if runs and runs[-1]["sig"] == sig:
            runs[-1]["ids"].append(cid)
        else:
            runs.append({"sig": sig, "ids": [cid]})

    parts: list[str] = []
    for run in runs:
        ids = ", ".join(str(i) for i in run["ids"])
        excluded, desc, mapped_ = run["sig"]
        if excluded:
            if desc and mapped_:
                parts.append(f"capr.exclude(capr.descendants(capr.mapped({ids})))")
            elif desc:
                parts.append(f"capr.exclude(capr.descendants({ids}))")
            elif mapped_:
                parts.append(f"capr.exclude(capr.mapped({ids}))")
            else:
                parts.append(f"capr.exclude({ids})")
        elif desc and mapped_:
            parts.append(f"capr.descendants(capr.mapped({ids}))")
        elif desc:
            parts.append(f"capr.descendants({ids})")
        elif mapped_:
            parts.append(f"capr.mapped({ids})")
        else:
            parts.append(ids)
    return parts


def _concept_set_lines(concept_set: dict[str, Any]) -> list[str]:
    var = concept_set_var_name(concept_set.get("name"), concept_set.get("id"))
    items = _get(concept_set.get("expression") or {}, "items", default=[]) or []
    if not items:
        return [f"{var} = capr.cs(name={concept_set.get('name')!r})"]
    parts = _items_to_parts(items)
    return [f"{var} = capr.cs({', '.join(parts)}, name={concept_set.get('name')!r})"]


# --- operators and windows ----------------------------------------------------


def _op_attr_to_code(op_obj: dict[str, Any], *, integers_as_numeric: bool = False) -> str | None:
    if not op_obj or "Op" not in op_obj:
        return None
    op = op_obj["Op"]
    value = _parse_date(op_obj.get("Value"))
    extent = _parse_date(op_obj.get("Extent")) if "Extent" in op_obj else None

    if value is None:
        raise JsonToCaprError("op attribute is missing Value")

    def fmt(z: Any) -> str:
        if isinstance(z, str) and _DATE_RE.match(z):
            return _date_literal(z)
        return format_scalar(z, integers_as_numeric=integers_as_numeric)

    if op in ("bt", "BT"):
        if extent is None:
            raise JsonToCaprError("bt op is missing Extent")
        return f"capr.bt({fmt(value)}, {fmt(extent)})"
    if op in ("!bt", "nbt", "NBT"):
        if extent is None:
            raise JsonToCaprError("nbt op is missing Extent")
        return f"capr.nbt({fmt(value)}, {fmt(extent)})"
    if op in ("gt", "gte", "lt", "lte", "eq"):
        return f"capr.{op}({fmt(value)})"
    if op in ("contains", "startsWith", "endsWith", "exact"):
        return f"capr.{op}({fmt(value)})"
    raise JsonToCaprError(f"Unsupported op: {op}")


def _window_to_code(window: dict[str, Any]) -> str:
    def side(part: Any) -> str:
        coeff = _get(part, "Coeff", default=1)
        days = _get(part, "Days")
        if days is None:
            return "-capr.INF" if int(coeff) < 0 else "capr.INF"
        return str(int(days) * int(coeff))

    start = side(_get(window, "Start", default={"Coeff": -1}))
    end = side(_get(window, "End", default={"Coeff": 1, "Days": 0}))
    return start, end


def _event_window_to_code(window: dict[str, Any]) -> str:
    start, end = _window_to_code(window)
    index = "endDate" if window.get("UseIndexEnd") else "startDate"
    fn = "event_ends" if window.get("UseEventEnd") else "event_starts"
    return f"capr.{fn}({start}, {end}, index={index!r})"


def _aperture_to_code(
    start_window: dict[str, Any] | None,
    end_window: dict[str, Any] | None,
    restrict_visit: bool = False,
    ignore_observation_period: bool = False,
) -> str:
    start_code = _event_window_to_code(start_window or {})
    args = [f"start_window={start_code}"]
    if end_window is not None:
        args.append(f"end_window={_event_window_to_code(end_window)}")
    if restrict_visit:
        args.append("restrict_visit=True")
    if ignore_observation_period:
        args.append("ignore_observation_period=True")
    return f"capr.during_interval({', '.join(args)})"


def _occurrence_wrap(occurrence: dict[str, Any], inner: str) -> str:
    occ_type = _get(occurrence, "Type", default=2)
    count = int(_get(occurrence, "Count", default=1))
    wrapper = {0: "exactly", 1: "at_most", 2: "at_least"}.get(int(occ_type))
    if wrapper is None:
        raise JsonToCaprError(f"Unsupported Occurrence.Type: {occ_type}")
    args = [str(count), inner]
    if occurrence.get("IsDistinct"):
        args.append("distinct=True")
    column = _get(occurrence, "CountColumn", default="")
    if column:
        args.append(f"count_column={column!r}")
    return f"capr.{wrapper}({', '.join(args)})"


# --- domains ------------------------------------------------------------------

_DOMAIN_TO_QUERY_FUN: dict[str, str] = {
    "ConditionOccurrence": "condition_occurrence",
    "ConditionEra": "condition_era",
    "DrugExposure": "drug_exposure",
    "DrugEra": "drug_era",
    "DoseEra": "dose_era",
    "ProcedureOccurrence": "procedure",
    "Measurement": "measurement",
    "VisitOccurrence": "visit",
    "VisitDetail": "visit_detail",
    "Observation": "observation",
    "Death": "death",
    "DeviceExposure": "device",
    "ObservationPeriod": "observation_period",
    "Specimen": "specimen",
    "PayerPlanPeriod": "payer_plan_period",
}

# Domains whose query constructor takes no concept set.
_NO_CONCEPT_SET_DOMAINS = {"ObservationPeriod"}

_SOURCE_CONCEPT_MAP = {
    "ConditionSourceConcept": "condition_source_concept",
    "DrugSourceConcept": "drug_source_concept",
    "ProcedureSourceConcept": "procedure_source_concept",
    "ObservationSourceConcept": "observation_source_concept",
    "VisitSourceConcept": "visit_source_concept",
    "MeasurementSourceConcept": "measurement_source_concept",
    "VisitDetailSourceConcept": "visit_detail_source_concept",
}

_TYPE_ATTRIBUTE_MAP = {
    "ConditionType": "condition_type",
    "ConditionStatus": "condition_status",
    "DrugType": "drug_type",
    "MeasurementType": "measurement_type",
    "ObservationType": "observation_type",
    "ProcedureType": "procedure_type",
    "DeathType": "death_type",
    "DeviceType": "device_type",
    "SpecimenType": "specimen_type",
    "PeriodType": "observation_period_type",
}

_TYPE_EXCLUDE_MAP = {
    "ConditionTypeExclude": "condition_type_exclude",
    "DrugTypeExclude": "drug_type_exclude",
    "MeasurementTypeExclude": "measurement_type_exclude",
    "DeathTypeExclude": "death_type_exclude",
    "SpecimenTypeExclude": "specimen_type_exclude",
    "ObservationTypeExclude": "observation_type_exclude",
    "ProcedureTypeExclude": "procedure_type_exclude",
    "DeviceTypeExclude": "device_type_exclude",
}


def _ids_call(name: str, ids: list[int]) -> str:
    """``ids=(1, 2)`` style for id-based type filters, or a scalar for one id."""
    if len(ids) == 1:
        return f"capr.{name}({ids[0]})"
    inner = ", ".join(str(i) for i in ids)
    return f"capr.{name}(({inner}))"


def _gender_calls(concepts: Any, emitter: _Emitter) -> list[str]:
    ids = sorted(set(concept_list_to_ids(concepts)))
    if not ids:
        return []
    if ids == [8507]:
        return ["capr.male()"]
    if ids == [8532]:
        return ["capr.female()"]
    if ids == [8507, 8532]:
        return ["capr.gender_concepts(8507, 8532)"]
    emitter.skip_or_stop(f"Unsupported Gender concept ids: {', '.join(map(str, ids))}")
    return []


def _date_adjustment_to_code(date_adjustment: dict[str, Any]) -> str:
    start_with = _get(date_adjustment, "StartWith", default="START_DATE")
    start_offset = int(_get(date_adjustment, "StartOffset", default=0))
    end_with = _get(date_adjustment, "EndWith", default="END_DATE")
    end_offset = int(_get(date_adjustment, "EndOffset", default=0))
    return (
        f"capr.date_adjustment(start_with={start_with!r}, start_offset={start_offset}, "
        f"end_with={end_with!r}, end_offset={end_offset})"
    )


def _user_defined_period_to_code(period: dict[str, Any]) -> str:
    start = _get(period, "StartDate")
    end = _get(period, "EndDate")
    if start is None or end is None:
        raise JsonToCaprError("UserDefinedPeriod is missing StartDate or EndDate")
    op = (
        f"capr.eq({_date_literal(start)})"
        if start == end
        else f"capr.bt({_date_literal(start)}, {_date_literal(end)})"
    )
    return f"capr.start_date({op})"


_SUPPORTED_KEYS_BY_DOMAIN: dict[str, set[str]] = {}


def _supported_keys(domain: str) -> set[str]:
    base = {
        "CodesetId",
        "CodesetID",
        "CorrelatedCriteria",
        "First",
        "DateAdjustment",
        "Age",
        "Gender",
        "OccurrenceStartDate",
        "OccurrenceEndDate",
        "EraStartDate",
        "EraEndDate",
        "UserDefinedPeriod",
        "VisitType",
        *_SOURCE_CONCEPT_MAP,
        *_TYPE_ATTRIBUTE_MAP,
        *_TYPE_EXCLUDE_MAP,
    }
    extra = {
        "ConditionOccurrence": {"ConditionStatus"},
        "VisitOccurrence": {"ProviderSpecialty"},
        "Measurement": {"ValueAsNumber", "RangeLow", "RangeHigh", "RangeHighRatio", "Unit", "ValueAsConcept"},
        "Observation": {"ValueAsNumber", "Unit", "ValueAsConcept", "ValueAsString"},
        "DrugExposure": {"DaysSupply", "Refills", "Quantity", "LotNumber"},
        "DrugEra": {"EraLength"},
        "DoseEra": {"Unit", "DoseValue", "EraLength"},
        "ConditionEra": {"OccurrenceCount"},
        "VisitDetail": {"VisitDetailSourceConcept"},
        "Specimen": {"SpecimenType", "SpecimenTypeExclude"},
        "DeviceExposure": {"DeviceType", "DeviceTypeExclude"},
        "ProcedureOccurrence": {"ProcedureType", "ProcedureTypeExclude"},
        "PayerPlanPeriod": set(),
    }.get(domain, set())
    return base | extra


def _detect_unsupported_keys(domain: str, domain_val: dict[str, Any], emitter: _Emitter, path: str) -> None:
    supported = _supported_keys(domain)
    for key, value in domain_val.items():
        if key in supported:
            continue
        if key.endswith("Type") or key.endswith("TypeExclude"):
            continue  # handled by the type-exclude checks
        if value in (None, [], {}):
            continue
        prefix = f"{path}." if path else ""
        emitter.skip_or_stop(f"Unsupported key: {prefix}{domain}.{key}")


def _stop_if_unsupported_types(domain_val: dict[str, Any], emitter: _Emitter, path: str) -> None:
    prefix = f"{path}." if path else ""
    for key, value in domain_val.items():
        if key.endswith("TypeExclude") and value is True:
            emitter.skip_or_stop(
                f"TypeExclude not supported: {prefix}{key}=TRUE "
                "(strict: stop; skip: omit this constraint only)"
            )
        if (
            key.endswith("Type")
            and key not in ("VisitType", *_TYPE_ATTRIBUTE_MAP)
            and isinstance(value, list)
            and value
        ):
            emitter.skip_or_stop(f"Unsupported type attribute: {prefix}{key}")


def _domain_attributes_to_capr(
    domain: str,
    domain_val: dict[str, Any],
    emitter: _Emitter,
    concept_set_by_id: dict[str, str],
    path: str = "",
) -> list[str]:
    _stop_if_unsupported_types(domain_val, emitter, path)
    calls: list[str] = []

    # Provider specialty on a visit.
    if domain == "VisitOccurrence":
        ids = concept_list_to_ids(domain_val.get("ProviderSpecialty"))
        if ids:
            inner = ", ".join(str(i) for i in ids)
            calls.append(f"capr.provider_specialty_concepts({inner})")

    if domain == "ConditionEra" and domain_val.get("OccurrenceCount"):
        calls.append(f"capr.occurrence_count({_op_attr_to_code(domain_val['OccurrenceCount'])})")
    if domain == "DrugEra" and domain_val.get("EraLength"):
        calls.append(f"capr.era_length({_op_attr_to_code(domain_val['EraLength'])})")

    if domain == "DoseEra":
        if domain_val.get("Unit") is not None:
            inline = concept_list_to_inline_cs(domain_val["Unit"], name="Unit")
            if inline:
                calls.append(f"capr.measurement_unit({inline})")
        if domain_val.get("DoseValue"):
            calls.append(
                f"capr.dose_value({_op_attr_to_code(domain_val['DoseValue'], integers_as_numeric=True)})"
            )
        if domain_val.get("EraLength"):
            calls.append(f"capr.era_length({_op_attr_to_code(domain_val['EraLength'])})")

    if domain == "Measurement" and domain_val.get("RangeHighRatio"):
        calls.append(
            f"capr.range_high_ratio("
            f"{_op_attr_to_code(domain_val['RangeHighRatio'], integers_as_numeric=True)})"
        )

    if domain_val.get("First") is True:
        calls.append("capr.first_occurrence()")

    for json_key, fun_name in _TYPE_EXCLUDE_MAP.items():
        if domain_val.get(json_key) is False:
            calls.append(f"capr.{fun_name}(False)")

    if domain_val.get("DateAdjustment"):
        calls.append(_date_adjustment_to_code(domain_val["DateAdjustment"]))

    if domain_val.get("Age"):
        calls.append(f"capr.age({_op_attr_to_code(domain_val['Age'])})")

    if domain_val.get("Gender"):
        calls.extend(_gender_calls(domain_val["Gender"], emitter))

    for json_key, fun_name, type_arg in (
        ("OccurrenceStartDate", "start_date", "occurrence"),
        ("OccurrenceEndDate", "end_date", "occurrence"),
        ("EraStartDate", "start_date", "era"),
        ("EraEndDate", "end_date", "era"),
    ):
        if domain_val.get(json_key):
            calls.append(f"capr.{fun_name}({_op_attr_to_code(domain_val[json_key])}, type={type_arg!r})")

    if domain == "ObservationPeriod" and domain_val.get("UserDefinedPeriod"):
        calls.append(_user_defined_period_to_code(domain_val["UserDefinedPeriod"]))

    # Source concepts: a bare integer means "use this concept set".
    for json_key, fun_name in _SOURCE_CONCEPT_MAP.items():
        value = domain_val.get(json_key)
        if value in (None, []):
            continue
        if isinstance(value, int):
            var = concept_set_by_id.get(str(value))
            if var:
                calls.append(f"capr.{fun_name}({var})")
                continue
        inline = concept_list_to_inline_cs(value, name=json_key)
        if inline:
            calls.append(f"capr.{fun_name}({inline})")

    for json_key, fun_name in _TYPE_ATTRIBUTE_MAP.items():
        value = domain_val.get(json_key)
        if isinstance(value, list) and value:
            ids = concept_list_to_ids(value)
            if ids:
                calls.append(_ids_call(fun_name, ids))

    if domain_val.get("VisitType"):
        value = domain_val["VisitType"]
        if isinstance(value, int) and str(value) in concept_set_by_id:
            calls.append(f"capr.visit_type_set({concept_set_by_id[str(value)]})")
        else:
            inline = concept_list_to_inline_cs(value, name="VisitType")
            if inline:
                calls.append(f"capr.visit_type_set({inline})")

    for domain_name, keys in (
        (
            "Measurement",
            (("ValueAsNumber", "value_as_number"), ("RangeLow", "range_low"), ("RangeHigh", "range_high")),
        ),
        ("Observation", (("ValueAsNumber", "value_as_number"),)),
    ):
        if domain == domain_name:
            for json_key, fun_name in keys:
                if domain_val.get(json_key):
                    calls.append(
                        f"capr.{fun_name}({_op_attr_to_code(domain_val[json_key], integers_as_numeric=True)})"
                    )
            unit_ids = concept_list_to_ids(domain_val.get("Unit"))
            if unit_ids:
                calls.append(_ids_call("measurement_unit", unit_ids))
            if domain_val.get("ValueAsConcept") is not None:
                value = domain_val["ValueAsConcept"]
                if isinstance(value, int) and str(value) in concept_set_by_id:
                    calls.append(f"capr.value_as_concept_set({concept_set_by_id[str(value)]})")
                else:
                    inline = concept_list_to_inline_cs(value, name="ValueAsConcept")
                    if inline:
                        calls.append(f"capr.value_as_concept_set({inline})")

    if domain == "Observation" and isinstance(domain_val.get("ValueAsString"), dict):
        vs = domain_val["ValueAsString"]
        text = _get(vs, "Text", "text")
        op = _get(vs, "Op", "op", default="contains")
        if text:
            calls.append(f"capr.value_as_string({text!r}, op={op!r})")

    if domain == "DrugExposure":
        for json_key, fun_name in (
            ("DaysSupply", "days_of_supply"),
            ("Refills", "drug_refills"),
            ("Quantity", "drug_quantity"),
            ("LotNumber", "lot_number"),
        ):
            if domain_val.get(json_key):
                calls.append(f"capr.{fun_name}({_op_attr_to_code(domain_val[json_key])})")

    _detect_unsupported_keys(domain, domain_val, emitter, path)
    return calls


# --- criteria and groups ------------------------------------------------------


def _demographic_to_capr(demo: dict[str, Any], emitter: _Emitter) -> list[str]:
    calls: list[str] = []
    if demo.get("Age"):
        calls.append(f"capr.age({_op_attr_to_code(demo['Age'])})")
    if demo.get("Gender"):
        calls.extend(_gender_calls(demo["Gender"], emitter))
    if demo.get("OccurrenceStartDate"):
        calls.append(f"capr.start_date({_op_attr_to_code(demo['OccurrenceStartDate'])}")
    if demo.get("OccurrenceEndDate"):
        calls.append(f"capr.end_date({_op_attr_to_code(demo['OccurrenceEndDate'])}")

    unsupported = set(demo) - {"Age", "Gender", "OccurrenceStartDate", "OccurrenceEndDate"}
    if unsupported:
        emitter.skip_or_stop(f"Unsupported demographic keys: {', '.join(sorted(unsupported))}")
    return calls


def _query_to_capr(
    domain: str,
    domain_val: dict[str, Any],
    concept_set_by_id: dict[str, str],
    emitter: _Emitter,
    path: str,
) -> str | None:
    query_fun = _DOMAIN_TO_QUERY_FUN.get(domain)
    if query_fun is None:
        emitter.skip_or_stop(f"Unsupported domain key: {domain}")
        return None

    codeset_id = _get(domain_val, "CodesetId", "CodesetID")
    if codeset_id is None:
        concept_set_var: str | None = None if domain in _NO_CONCEPT_SET_DOMAINS else "None"
    else:
        concept_set_var = concept_set_by_id.get(str(codeset_id))
        if concept_set_var is None:
            emitter.skip_or_stop(f"{path} CodesetId not found in ConceptSets: {codeset_id}")
            return None
    if domain in _NO_CONCEPT_SET_DOMAINS:
        concept_set_var = None

    args = _domain_attributes_to_capr(domain, domain_val, emitter, concept_set_by_id, path)

    correlated = domain_val.get("CorrelatedCriteria")
    if correlated:
        nested = _correlated_to_capr(correlated, concept_set_by_id, emitter)
        if nested:
            args.append(nested)

    call_args = ([concept_set_var] if concept_set_var else []) + args
    return f"capr.{query_fun}({', '.join(call_args)})"


def _criterion_node_to_capr(
    node: dict[str, Any],
    concept_set_by_id: dict[str, str],
    emitter: _Emitter,
    path: str,
) -> str | None:
    criteria_obj = node.get("Criteria") or {}
    if not criteria_obj:
        return None
    domain = next(iter(criteria_obj))
    domain_val = criteria_obj[domain] or {}

    inner = _query_to_capr(domain, domain_val, concept_set_by_id, emitter, path)
    if inner is None:
        return None

    aperture = _aperture_to_code(
        node.get("StartWindow"),
        node.get("EndWindow"),
        bool(node.get("RestrictVisit")),
        bool(node.get("IgnoreObservationPeriod")),
    )
    wrapped = _occurrence_wrap(node.get("Occurrence") or {}, f"{inner}, {aperture}")
    return wrapped


def _group_fn(group_type: str, engine: str) -> tuple[str, str | None]:
    """Map a Circe group type to the builder function and count argument."""
    pretty = {"ALL": "all", "ANY": "any", "AT_LEAST": "at_least", "AT_MOST": "at_most"}
    key = pretty.get(group_type.upper(), "all")
    prefix = "nested_with" if engine == "nested" else "with"
    return prefix + ("_" if prefix == "with" else "_") + key, None


def _parse_group_type(group: dict[str, Any]) -> str:
    return str(_get(group, "Type", default="ALL")).upper()


def _group_call(
    group: dict[str, Any],
    concept_set_by_id: dict[str, str],
    emitter: _Emitter,
    *,
    nested: bool,
    context: str,
) -> str:
    group_type = _parse_group_type(group)
    count = int(_get(group, "Count", default=1))

    mapping = {
        "ALL": "nested_with_all" if nested else "with_all",
        "ANY": "nested_with_any" if nested else "with_any",
        "AT_LEAST": "nested_with_at_least" if nested else "with_at_least",
        "AT_MOST": "nested_with_at_most" if nested else "with_at_most",
    }
    fun = mapping.get(group_type, "with_all")
    args: list[str] = []
    if group_type in ("AT_LEAST", "AT_MOST"):
        args.append(str(count))

    for index, node in enumerate(group.get("CriteriaList") or []):
        call = _criterion_node_to_capr(node, concept_set_by_id, emitter, f"{context}#{index}")
        if call:
            args.append(call)

    for demo in group.get("DemographicCriteriaList") or []:
        args.extend(_demographic_to_capr(demo, emitter))

    for index, sub in enumerate(group.get("Groups") or []):
        args.append(
            _group_call(sub, concept_set_by_id, emitter, nested=nested, context=f"{context}/subgroup#{index}")
        )

    if not args or (len(args) == 1 and group_type in ("AT_LEAST", "AT_MOST")):
        emitter.warn_empty_group(context)
        return f"capr.{fun}()"
    return f"capr.{fun}({', '.join(args)})"


def _correlated_to_capr(
    correlated: dict[str, Any], concept_set_by_id: dict[str, str], emitter: _Emitter
) -> str | None:
    if not correlated:
        return None
    return _group_call(correlated, concept_set_by_id, emitter, nested=True, context="correlatedCriteria")


# --- exit / era ---------------------------------------------------------------

_END_STRATEGY_KEYS = {"DateOffset", "CustomEra"}


def _end_strategy_to_capr(
    end_strategy: dict[str, Any] | None,
    concept_set_by_id: dict[str, str],
    emitter: _Emitter,
) -> str:
    if not end_strategy:
        return "capr.observation_exit()"

    if end_strategy.get("DateOffset"):
        date_field = _get(end_strategy["DateOffset"], "DateField", default="EndDate")
        offset = int(_get(end_strategy["DateOffset"], "Offset", default=0))
        index = "startDate" if str(date_field).lower().startswith("start") else "endDate"
        return f"capr.fixed_exit(index={index!r}, offset_days={offset})"

    if end_strategy.get("CustomEra"):
        custom = end_strategy["CustomEra"]
        drug_id = _get(custom, "DrugCodesetId", "DrugCodesetID")
        if drug_id is None:
            emitter.skip_or_stop("CustomEra is missing DrugCodesetId")
            return "capr.observation_exit()"
        var = concept_set_by_id.get(str(drug_id))
        if var is None:
            emitter.skip_or_stop(f"CustomEra DrugCodesetId not found in ConceptSets: {drug_id}")
            return "capr.observation_exit()"
        gap = int(_get(custom, "GapDays", default=0))
        offset = int(_get(custom, "Offset", default=0))
        return f"capr.drug_exit({var}, persistence_window={gap}, surveillance_window={offset})"

    keys = ", ".join(sorted(end_strategy))
    emitter.skip_or_stop(f"Unsupported EndStrategy structure: {keys}")
    return "capr.observation_exit()"


def _censoring_to_capr(
    censoring: list[dict[str, Any]],
    concept_set_by_id: dict[str, str],
    emitter: _Emitter,
) -> str | None:
    if not censoring:
        return None

    calls: list[str] = []
    for index, node in enumerate(censoring):
        criteria_obj = node.get("Criteria") or {}
        if not criteria_obj:
            # Atlas may export the domain object directly, without the Criteria wrapper.
            if node and next(iter(node)) in _DOMAIN_TO_QUERY_FUN:
                criteria_obj = node
            else:
                continue
        domain = next(iter(criteria_obj))
        domain_val = criteria_obj[domain] or {}
        call = _query_to_capr(domain, domain_val, concept_set_by_id, emitter, f"CensoringCriteria#{index}")
        if call:
            calls.append(call)

    if not calls:
        emitter.warn_empty_group("censoringCriteria")
        return None
    return f"capr.censoring_events({', '.join(calls)})"


def _era_call(collapse_settings: dict[str, Any] | None, censor_window: dict[str, Any] | None) -> str:
    if not collapse_settings:
        return "capr.era()"
    collapse_type = _get(collapse_settings, "CollapseType", default="ERA")
    if str(collapse_type) != "ERA":
        raise JsonToCaprError(f"Unsupported CollapseType: {collapse_type}")
    pad = int(_get(collapse_settings, "EraPad", default=0))
    args = [f"era_days={pad}"]
    if censor_window:
        start = _get(censor_window, "StartDate")
        end = _get(censor_window, "EndDate")
        if start:
            args.append(f"study_start_date={_date_literal(start)}")
        if end:
            args.append(f"study_end_date={_date_literal(end)}")
    return f"capr.era({', '.join(args)})"


def _limit_code(limit: Any) -> str:
    if limit is None:
        return "'All'"
    if isinstance(limit, str):
        return repr(limit)
    if isinstance(limit, dict) and "Type" in limit:
        return repr(limit["Type"])
    raise JsonToCaprError("Unsupported limit structure.")


# --- assembly -----------------------------------------------------------------


class DecompiledCohort:
    """The generated source plus the diagnostics collected while decompiling."""

    def __init__(self, source: str, skipped: list[str], empty_group_warnings: list[str]) -> None:
        self.source = source
        self.skipped = skipped
        self.empty_group_warnings = empty_group_warnings

    def __str__(self) -> str:
        return self.source

    def __repr__(self) -> str:
        return (
            f"DecompiledCohort({len(self.source.splitlines())} lines, "
            f"skipped={len(self.skipped)}, warnings={len(self.empty_group_warnings)})"
        )

    def write(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.source)
        return target


def _attrition_lines(
    inclusion_rules: list[dict[str, Any]],
    expression_limit: Any,
    concept_set_by_id: dict[str, str],
    emitter: _Emitter,
) -> list[str]:
    """Render ``attrition = capr.attrition(...)`` lines, or nothing if trivial."""
    limit_code = _limit_code(expression_limit)
    limit_type = expression_limit.get("Type") if isinstance(expression_limit, dict) else expression_limit

    if not inclusion_rules:
        if limit_type in (None, "First"):
            return []  # the default; nothing to say
        return [f"  attrition=capr.attrition(expression_limit={limit_code}),"]

    lines = [f"  attrition=capr.attrition(expression_limit={limit_code},"]
    for index, rule in enumerate(inclusion_rules):
        name = _get(rule, "name", "Name", default=f"rule {index + 1}")
        expression = rule.get("expression") or rule.get("Expression") or {"Type": "ALL"}
        call = _group_call(
            expression, concept_set_by_id, emitter, nested=False, context=f"inclusionRule:{name}"
        )
        lines.append(f"    **{{{name!r}: {call}}},")
    lines.append("  ),")
    return lines


def _build_lines(cohort_json: dict[str, Any], emitter: _Emitter, source_name: str) -> list[str]:
    concept_sets = cohort_json.get("ConceptSets") or []
    concept_set_lines: list[str] = []
    concept_set_by_id: dict[str, str] = {}
    for concept_set in concept_sets:
        concept_set_lines.extend(_concept_set_lines(concept_set))
        concept_set_by_id[str(concept_set.get("id"))] = concept_set_var_name(
            concept_set.get("name"), concept_set.get("id")
        )

    primary = cohort_json.get("PrimaryCriteria")
    if primary is None:
        raise JsonToCaprError("JSON is missing PrimaryCriteria")
    primary_list = primary.get("CriteriaList") or []

    entry_calls: list[str] = []
    for node in primary_list:
        if not node:
            continue
        domain = next(iter(node))
        call = _query_to_capr(domain, node[domain] or {}, concept_set_by_id, emitter, "PrimaryCriteria")
        if call:
            entry_calls.append(call)

    if primary_list and not entry_calls:
        raise JsonToCaprError(
            "PrimaryCriteria produced no supported entry queries (strict) or all were skipped (skip)."
        )

    observation_window = primary.get("ObservationWindow") or {}
    prior = int(_get(observation_window, "PriorDays", default=0))
    post = int(_get(observation_window, "PostDays", default=0))
    primary_limit = _limit_code(primary.get("PrimaryCriteriaLimit") or "First")
    qualified_limit = _limit_code(
        cohort_json.get("QualifiedLimit") or primary.get("PrimaryCriteriaLimit") or "First"
    )

    end_strategy = cohort_json.get("EndStrategy") or {}
    end_strategy_call = _end_strategy_to_capr(end_strategy, concept_set_by_id, emitter)
    censoring_call = _censoring_to_capr(
        cohort_json.get("CensoringCriteria") or [], concept_set_by_id, emitter
    )
    era_call = _era_call(cohort_json.get("CollapseSettings"), cohort_json.get("CensorWindow"))

    lines: list[str] = [
        "from circe import capr",
        "",
        f"# Generated by json_to_capr() from {source_name}",
        "",
        "# --- concept sets ---",
        *concept_set_lines,
        "",
        "# --- cohort ---",
        "cohort_definition = capr.cohort(",
        "  entry=capr.entry(",
        *(f"    {call}," for call in entry_calls),
        f"    observation_window=capr.continuous_observation({prior}, {post}),",
        f"    primary_criteria_limit={primary_limit},",
        f"    qualified_limit={qualified_limit},",
        "  ),",
        *_attrition_lines(
            cohort_json.get("InclusionRules") or [],
            cohort_json.get("ExpressionLimit"),
            concept_set_by_id,
            emitter,
        ),
        "  exit=capr.exit(",
        f"    end_strategy={end_strategy_call},"
        + (f"\n    censor={censoring_call}," if censoring_call else ""),
        "  ),",
        f"  era={era_call},",
        ")",
        "",
    ]
    return lines


def json_to_capr(
    json_path: str | Path,
    *,
    mode: str = "strict",
    return_skipped: bool = False,
) -> str | DecompiledCohort:
    """Decompile Circe cohort JSON into ``circe.capr`` Python source.

    Args:
        json_path: Path to a cohort definition JSON file.
        mode: ``"strict"`` raises :class:`JsonToCaprError` on anything
            unsupported; ``"skip"`` omits it and records a ``# SKIPPED:`` comment.
        return_skipped: Return a :class:`DecompiledCohort` carrying the skipped
            and warning lists alongside the source.

    Returns:
        The generated Python source, or a :class:`DecompiledCohort` when
        ``return_skipped`` is true.
    """
    emitter = _Emitter(mode)
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"No such JSON file: {path}")

    cohort_json = json.loads(path.read_text())

    try:
        body = _build_lines(cohort_json, emitter, path.name)
    except JsonToCaprError:
        raise

    lines = [*emitter.header_lines(), *body]
    source = "\n".join(lines)
    if return_skipped:
        return DecompiledCohort(source, emitter.skipped, emitter.empty_group_warnings)
    return source


def json_to_capr_file(
    json_path: str | Path,
    out_path: str | Path,
    *,
    mode: str = "strict",
) -> Path:
    """Decompile cohort JSON to ``out_path``, returning the written path."""
    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json_to_capr(json_path, mode=mode))
    return target
