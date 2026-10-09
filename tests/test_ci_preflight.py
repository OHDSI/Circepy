"""Tests for the local CI-preflight harness helpers.

Only the pure helper functions are exercised here; the gate runners shell out to
real tooling and are covered manually via ``python scripts/ci_preflight.py``.
"""

from __future__ import annotations

import json

from scripts.ci_preflight import (
    Config,
    compute_patch_coverage,
    compute_project_coverage,
    load_config,
    new_failures,
    parse_changed_lines,
    parse_coverage_xml,
    parse_pip_versions,
    parse_test_report,
    percentage,
)


def test_parse_changed_lines_basic():
    diff = (
        "diff --git a/circe/a.py b/circe/a.py\n"
        "index 111..222 100644\n"
        "--- a/circe/a.py\n"
        "+++ b/circe/a.py\n"
        "@@ -1,3 +1,4 @@\n"
        " line1\n"
        "+added2\n"
        " line3\n"
        "-removed4\n"
    )
    assert parse_changed_lines(diff) == {"circe/a.py": {2}}


def test_parse_changed_lines_new_file_and_multiple_hunks():
    diff = (
        "--- /dev/null\n"
        "+++ b/scripts/x.py\n"
        "@@ -0,0 +1,2 @@\n"
        "+a\n"
        "+b\n"
        "--- a/circe/b.py\n"
        "+++ b/circe/b.py\n"
        "@@ -10,0 +11,1 @@\n"
        "+new\n"
    )
    assert parse_changed_lines(diff) == {"scripts/x.py": {1, 2}, "circe/b.py": {11}}


def test_parse_coverage_xml(tmp_path):
    xml = (
        "<coverage><packages><package><classes>"
        '<class filename="circe/a.py"><lines>'
        '<line number="1" hits="1"/><line number="2" hits="0"/>'
        "</lines></class>"
        "</classes></package></packages></coverage>"
    )
    path = tmp_path / "coverage.xml"
    path.write_text(xml)
    assert parse_coverage_xml(path) == {"circe/a.py": {1: 1, 2: 0}}


def test_compute_patch_coverage_ignores_unmeasured_files():
    changed = {"circe/a.py": {1, 2, 3}, "tests/test_x.py": {1}}
    coverage = {"circe/a.py": {1: 1, 2: 0, 3: 5}}
    assert compute_patch_coverage(changed, coverage) == (2, 3)


def test_compute_project_coverage():
    coverage = {"a.py": {1: 1, 2: 0}, "b.py": {5: 3}}
    assert compute_project_coverage(coverage) == (2, 3)


def test_percentage_handles_zero_total():
    assert percentage(0, 0) == 100.0
    assert percentage(1, 4) == 25.0


def test_parse_test_report_and_new_failures(tmp_path):
    payload = {
        "tests": [
            {"nodeid": "tests/a.py::test_a", "outcome": "passed"},
            {"nodeid": "tests/a.py::test_b", "outcome": "failed"},
        ]
    }
    path = tmp_path / "report.json"
    path.write_text(json.dumps(payload))
    report = parse_test_report(path)
    assert report == {"tests/a.py::test_a": "passed", "tests/a.py::test_b": "failed"}

    baseline = {"tests/a.py::test_a": "passed", "tests/a.py::test_b": "failed"}
    final = dict(baseline, **{"tests/c.py::test_c": "error"})
    assert new_failures(baseline, final) == {"tests/c.py::test_c"}


def test_parse_pip_versions():
    freeze = "ruff==0.16.3\nFoo_Bar==1.2\n# comment\nnot-a-pin\n"
    assert parse_pip_versions(freeze) == {"ruff": "0.16.3", "foo-bar": "1.2"}


def test_load_config_reads_pyproject():
    config = load_config()
    assert isinstance(config, Config)
    assert config.base_ref == "origin/develop"
    assert config.project_target == 80.0
    assert "sqlglot" in config.sensitive_packages
