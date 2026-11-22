"""Tests for ``circe.capr.json_to_capr`` (Circe JSON -> circe.capr source).

The round-trip test is the meaningful one: decompile a cohort, execute the
generated source, re-serialize, and confirm nothing was lost.

Fixtures come from ``tests/capr/fixtures``, which are the JSON that R's Capr
produces for the reference cohorts. Two known input quirks are normalised
before comparison, both on the *input* side and neither caused by this module:

- Capr writes inclusion rules with lowercase ``name``/``expression``.
- Circepy's domain criteria serialize gender as ``gender`` (pre-existing bug).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from circe import capr
from circe.capr.json_to_capr import concept_set_var_name, to_camel_case

FIXTURES = Path(__file__).parent / "fixtures"

_DROPPED = {"cdmVersionRange"}
_FALSE_DEFAULTS = {
    "First",
    "ConditionTypeExclude",
    "DeathTypeExclude",
    "DrugTypeExclude",
    "MeasurementTypeExclude",
    "SpecimenTypeExclude",
    "ObservationTypeExclude",
    "ProcedureTypeExclude",
    "DeviceTypeExclude",
    "RestrictVisit",
    "IgnoreObservationPeriod",
    "IsDistinct",
}
_EMPTY_CONCEPT_STRINGS = {
    "CONCEPT_NAME",
    "STANDARD_CONCEPT",
    "STANDARD_CONCEPT_CAPTION",
    "INVALID_REASON",
    "INVALID_REASON_CAPTION",
    "CONCEPT_CODE",
    "DOMAIN_ID",
    "VOCABULARY_ID",
    "CONCEPT_CLASS_ID",
}
_EXPRESSION_DEFAULTS = {"isExcluded", "includeMapped", "includeDescendants"}
_RULE_KEYS = {"name": "Name", "expression": "Expression"}
_KEY_CASE = {"gender": "Gender"}


def _normalise(node, *, in_expression: bool = False):
    if isinstance(node, dict):
        is_expression_parent = isinstance(node.get("expression"), dict) and (
            "items" in (node.get("expression") or {})
        )
        out = {}
        for key, value in node.items():
            if key in _DROPPED:
                continue
            if key in _FALSE_DEFAULTS and value is False:
                continue
            if key in _EMPTY_CONCEPT_STRINGS and value in ("", None):
                continue
            if in_expression and key in _EXPRESSION_DEFAULTS and value is False:
                continue
            out[_KEY_CASE.get(key, key)] = _normalise(value, in_expression=is_expression_parent)
        return out
    if isinstance(node, list):
        return [_normalise(item, in_expression=in_expression) for item in node]
    return node


def _normalise_rule_keys(node):
    if isinstance(node, dict):
        return {
            key: (
                [{_RULE_KEYS.get(k, k): v for k, v in rule.items()} for rule in value]
                if key == "InclusionRules" and isinstance(value, list)
                else _normalise_rule_keys(value)
            )
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [_normalise_rule_keys(item) for item in node]
    return node


def _canonical(payload):
    return _normalise_rule_keys(_normalise(payload))


FIXTURE_NAMES = sorted(p.stem for p in FIXTURES.glob("*.json"))


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_round_trip_preserves_definition(name: str, tmp_path: Path) -> None:
    """decompile -> exec -> re-serialize reproduces the original definition."""
    source_json = FIXTURES / f"{name}.json"
    json_path = tmp_path / "cohort.json"
    json_path.write_text(source_json.read_text())

    source = capr.json_to_capr(json_path)
    namespace: dict[str, object] = {}
    exec(compile(source, f"<{name}>", "exec"), namespace)

    regenerated = json.loads(capr.to_cohort_json(namespace["cohort_definition"]))
    assert _canonical(regenerated) == _canonical(json.loads(source_json.read_text()))


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_generated_source_is_executable_and_namespaced(name: str, tmp_path: Path) -> None:
    json_path = tmp_path / "cohort.json"
    json_path.write_text((FIXTURES / f"{name}.json").read_text())

    source = capr.json_to_capr(json_path)
    assert source.startswith("from circe import capr")
    assert "cohort_definition = capr.cohort(" in source

    namespace: dict[str, object] = {}
    exec(compile(source, f"<{name}>", "exec"), namespace)
    assert isinstance(namespace["cohort_definition"], capr.Cohort)


def test_concept_set_variable_naming() -> None:
    assert concept_set_var_name("Type 2 Diabetes", 0) == "csType2Diabetes0"
    assert concept_set_var_name(None, 3) == "csConceptSet3"
    assert to_camel_case("Mixed CASE name") == "mixedCaseName"


def _minimal(**domain_body) -> dict:
    return {
        "ConceptSets": [],
        "PrimaryCriteria": {
            "CriteriaList": [{"ConditionOccurrence": domain_body}],
            "ObservationWindow": {"PriorDays": 0, "PostDays": 0},
            "PrimaryCriteriaLimit": {"Type": "First"},
        },
    }


def _write(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "cohort.json"
    path.write_text(json.dumps(payload))
    return path


def test_unsupported_domain_strict_raises(tmp_path: Path) -> None:
    payload = _minimal()
    payload["PrimaryCriteria"]["CriteriaList"] = [{"WaveformOccurrence": {}}]
    with pytest.raises(capr.JsonToCaprError, match="Unsupported domain key"):
        capr.json_to_capr(_write(tmp_path, payload))


def test_unsupported_domain_skip_records_reason(tmp_path: Path) -> None:
    payload = _minimal()
    payload["PrimaryCriteria"]["CriteriaList"] = [{"WaveformOccurrence": {}}]
    # Every entry query was skipped, so there is nothing usable to emit.
    with pytest.raises(capr.JsonToCaprError, match="no supported entry queries"):
        capr.json_to_capr(_write(tmp_path, payload), mode="skip")


def test_type_exclude_true_is_rejected_in_strict_mode(tmp_path: Path) -> None:
    with pytest.raises(capr.JsonToCaprError, match="TypeExclude not supported"):
        capr.json_to_capr(_write(tmp_path, _minimal(ConditionTypeExclude=True)))


def test_type_exclude_true_is_skipped_in_skip_mode(tmp_path: Path) -> None:
    result = capr.json_to_capr(
        _write(tmp_path, _minimal(ConditionTypeExclude=True)), mode="skip", return_skipped=True
    )
    assert isinstance(result, capr.DecompiledCohort)
    assert any("TypeExclude" in reason for reason in result.skipped)
    assert "# --- SKIPPED" in result.source


def test_unknown_key_detected(tmp_path: Path) -> None:
    with pytest.raises(capr.JsonToCaprError, match="Unsupported key"):
        capr.json_to_capr(_write(tmp_path, _minimal(SomeNewField=[1, 2])))


def test_unknown_key_skipped(tmp_path: Path) -> None:
    result = capr.json_to_capr(
        _write(tmp_path, _minimal(SomeNewField=[1, 2])), mode="skip", return_skipped=True
    )
    assert isinstance(result, capr.DecompiledCohort)
    assert any("SomeNewField" in reason for reason in result.skipped)


def test_missing_primary_criteria_raises(tmp_path: Path) -> None:
    with pytest.raises(capr.JsonToCaprError, match="missing PrimaryCriteria"):
        capr.json_to_capr(_write(tmp_path, {"ConceptSets": []}))


def test_dangling_codeset_id_raises(tmp_path: Path) -> None:
    with pytest.raises(capr.JsonToCaprError, match="CodesetId not found"):
        capr.json_to_capr(_write(tmp_path, _minimal(CodesetId=7)))


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        capr.json_to_capr(tmp_path / "nope.json")


def test_invalid_mode_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="mode must be"):
        capr.json_to_capr(_write(tmp_path, _minimal()), mode="loose")


def test_json_to_capr_file_writes_source(tmp_path: Path) -> None:
    source_json = FIXTURES / "minimal.json"
    target = tmp_path / "nested" / "cohort.py"
    written = capr.json_to_capr_file(source_json, target)
    assert written == target
    assert "capr.cohort(" in target.read_text()


def test_decompiled_cohort_write(tmp_path: Path) -> None:
    result = capr.json_to_capr(FIXTURES / "minimal.json", return_skipped=True)
    assert isinstance(result, capr.DecompiledCohort)
    target = result.write(tmp_path / "out.py")
    assert target.read_text() == result.source


def test_string_value_decompiles_with_op(tmp_path: Path) -> None:
    payload = {
        "ConceptSets": [
            {
                "id": 0,
                "name": "obs",
                "expression": {
                    "items": [
                        {
                            "concept": {"CONCEPT_ID": 1},
                            "isExcluded": False,
                            "includeDescendants": False,
                            "includeMapped": False,
                        }
                    ]
                },
            }
        ],
        "PrimaryCriteria": {
            "CriteriaList": [
                {"Observation": {"CodesetId": 0, "ValueAsString": {"Text": "neg", "Op": "startsWith"}}}
            ],
            "ObservationWindow": {"PriorDays": 0, "PostDays": 0},
            "PrimaryCriteriaLimit": {"Type": "First"},
        },
    }
    source = capr.json_to_capr(_write(tmp_path, payload))
    assert "value_as_string('neg', op='startsWith')" in source

    namespace: dict[str, object] = {}
    exec(compile(source, "<string-op>", "exec"), namespace)
    regenerated = json.loads(capr.to_cohort_json(namespace["cohort_definition"]))
    assert (
        regenerated["PrimaryCriteria"]["CriteriaList"][0]["Observation"]["ValueAsString"]["Op"]
        == "startsWith"
    )
