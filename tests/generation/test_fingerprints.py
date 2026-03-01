from __future__ import annotations

from circe.cohortdefinition import BuildExpressionQueryOptions
from circe.generation.fingerprint import (
    fingerprint_expression,
    fingerprint_generation_request,
    fingerprint_options,
)

from tests.generation.conftest import make_expression


def test_fingerprint_expression_is_deterministic():
    expression = make_expression(111)
    assert fingerprint_expression(expression) == fingerprint_expression(expression)


def test_fingerprint_expression_changes_on_semantic_change():
    a = make_expression(111)
    b = make_expression(222)
    assert fingerprint_expression(a) != fingerprint_expression(b)


def test_fingerprint_options_ignores_runtime_noise():
    options = BuildExpressionQueryOptions()
    options.cdm_schema = "cdm"
    options.result_schema = "results"

    first = fingerprint_options(options)
    second = fingerprint_options(options)
    assert first == second


def test_fingerprint_generation_request_changes_with_target_and_options():
    expression = make_expression(111)

    options = BuildExpressionQueryOptions()
    options.cdm_schema = "cdm"
    options.result_schema = "results"

    a = fingerprint_generation_request(expression, options, target_table="cohort")
    b = fingerprint_generation_request(expression, options, target_table="other")
    assert a != b


def test_fingerprint_generation_request_changes_with_data_version_token():
    expression = make_expression(111)
    options = BuildExpressionQueryOptions()

    a = fingerprint_generation_request(
        expression,
        options,
        target_table="cohort",
    )
    b = fingerprint_generation_request(
        expression,
        options,
        target_table="cohort",
        data_version_token="snapshot-2026-03-01",
    )
    assert a != b
