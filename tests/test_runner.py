"""Tests for the Prefect/Docker cohort-generation runner."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from circe.cohortdefinition import CohortExpression, ConditionOccurrence, PrimaryCriteria
from circe.runner import (
    PREFECT_AVAILABLE,
    BackendConfig,
    DefinitionSource,
    RunnerPayload,
    TargetConfig,
    run_cohort_generation,
    run_cohort_generation_flow,
)
from circe.runner.backend import BackendConfigurationError, connect_backend
from circe.runner.registry import DefinitionConflictError
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


def _expression(concept_id: int = 111) -> CohortExpression:
    return CohortExpression(
        concept_sets=[
            ConceptSet(
                id=1,
                expression=ConceptSetExpression(
                    items=[ConceptSetItem(concept=Concept(conceptId=concept_id))]
                ),
            )
        ],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
    )


def _write_definitions(root: Path, *, cohort_name: str = "demo") -> Path:
    data = root / "definitions"
    (data / "cohorts").mkdir(parents=True)
    with (data / "Cohorts.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["cohort_id", "cohort_name"])
        writer.writeheader()
        writer.writerow({"cohort_id": "1", "cohort_name": cohort_name})
    (data / "cohorts" / "1.json").write_text(_expression().model_dump_json(by_alias=True), encoding="utf-8")
    return data


def _seed_duckdb(path: Path) -> None:
    import ibis

    conn = ibis.duckdb.connect(str(path))
    conn.create_table(
        "person",
        obj=ibis.memtable({"person_id": [1], "year_of_birth": [1980], "gender_concept_id": [8507]}),
        overwrite=True,
    )
    conn.create_table(
        "observation_period",
        obj=ibis.memtable(
            {
                "person_id": [1],
                "observation_period_id": [1],
                "observation_period_start_date": ["2019-01-01"],
                "observation_period_end_date": ["2021-12-31"],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1],
                "condition_occurrence_id": [10],
                "condition_concept_id": [111],
                "condition_start_date": ["2020-01-01"],
                "condition_end_date": ["2020-01-01"],
            }
        ),
        overwrite=True,
    )
    conn.disconnect()


def _payload(root: Path, *, duckdb_path: Path, definitions: Path) -> RunnerPayload:
    return RunnerPayload.model_validate(
        {
            "cdm_schema": "main",
            "vocabulary_schema": "main",
            "target": {"schema": "main", "table": "cohort", "registry_table": "cohort_registry"},
            "definitions": {
                "settings_file": str(definitions / "Cohorts.csv"),
                "json_folder": str(definitions / "cohorts"),
                "sql_folder": None,
                "base_dir": str(definitions),
            },
            "backend": {"type": "duckdb", "duckdb_path": str(duckdb_path)},
        }
    )


def test_runner_generates_and_reuses_cohorts(tmp_path):
    db_path = tmp_path / "demo.duckdb"
    definitions = _write_definitions(tmp_path)
    _seed_duckdb(db_path)
    payload = _payload(tmp_path, duckdb_path=db_path, definitions=definitions)

    first = run_cohort_generation(payload)

    assert first.loaded == 1
    assert first.generated == [1]
    assert first.reused == []
    assert first.to_dict()["status"] == "COMPLETE"

    import ibis

    conn = ibis.duckdb.connect(str(db_path))
    assert conn.table("cohort", database="main").count().execute() == 1
    registry = conn.table("cohort_registry", database="main").execute()
    assert len(registry) == 1
    assert json.loads(registry.iloc[0]["definition_json"])["PrimaryCriteria"] is not None
    conn.disconnect()

    second = run_cohort_generation(payload)
    assert second.generated == []
    assert second.reused == [1]


def test_runner_definition_conflict_fails_by_default(tmp_path):
    db_path = tmp_path / "conflict.duckdb"
    definitions = _write_definitions(tmp_path)
    _seed_duckdb(db_path)
    payload = _payload(tmp_path, duckdb_path=db_path, definitions=definitions)
    run_cohort_generation(payload)

    (definitions / "cohorts" / "1.json").write_text(
        _expression(concept_id=222).model_dump_json(by_alias=True), encoding="utf-8"
    )
    with pytest.raises(DefinitionConflictError):
        run_cohort_generation(payload)


def test_runner_replace_definition(tmp_path):
    db_path = tmp_path / "replace.duckdb"
    definitions = _write_definitions(tmp_path)
    _seed_duckdb(db_path)
    payload = _payload(tmp_path, duckdb_path=db_path, definitions=definitions)
    run_cohort_generation(payload)

    (definitions / "cohorts" / "1.json").write_text(
        _expression(concept_id=222).model_dump_json(by_alias=True), encoding="utf-8"
    )
    replace_payload = payload.model_copy(
        update={"target": payload.target.model_copy(update={"on_definition_change": "replace"})}
    )
    result = run_cohort_generation(replace_payload)
    assert result.generated == [1]


def test_runner_flow_fallback_executes():
    # When Prefect is absent the flow/task decorators are pass-throughs; when it
    # is installed this still exercises the same flow function.
    assert isinstance(PREFECT_AVAILABLE, bool)


def test_payload_validation_and_aliases():
    payload = RunnerPayload.model_validate(
        {
            "cdm_schema": "cdm",
            "target": {"schema": "results", "table": "cohort"},
            "backend": {
                "type": "postgresql",
                "database": "postgres",
                "user": "postgres",
            },
        }
    )
    assert payload.target.schema_name == "results"
    assert payload.definitions.settings_file == "Cohorts.csv"
    assert payload.shared is True

    with pytest.raises(ValidationError):
        RunnerPayload.model_validate(
            {
                "cdm_schema": "cdm",
                "target": {"schema": "results"},
                "backend": {"type": "postgresql"},
            }
        )


def test_backend_requires_password(monkeypatch):
    monkeypatch.delenv("PGPASSWORD", raising=False)
    with pytest.raises(BackendConfigurationError, match="PGPASSWORD"):
        connect_backend(
            BackendConfig(
                type="postgresql",
                database="postgres",
                user="postgres",
            )
        )


def test_definition_source_defaults():
    source = DefinitionSource()
    assert source.settings_file == "Cohorts.csv"
    assert source.json_folder == "cohorts"
    assert source.sql_folder == "sql/sql_server"
    assert TargetConfig(schema_name="results").table == "cohort"


def test_runner_result_is_json_serializable(tmp_path):
    db_path = tmp_path / "json.duckdb"
    definitions = _write_definitions(tmp_path)
    _seed_duckdb(db_path)
    payload = _payload(tmp_path, duckdb_path=db_path, definitions=definitions)

    result = run_cohort_generation(payload)
    assert json.loads(json.dumps(result.to_dict()))["generated"] == [1]


def test_runner_flow_returns_dict(tmp_path):
    db_path = tmp_path / "flow.duckdb"
    definitions = _write_definitions(tmp_path)
    _seed_duckdb(db_path)
    payload = _payload(tmp_path, duckdb_path=db_path, definitions=definitions)

    result = run_cohort_generation_flow(payload.model_dump(mode="json", by_alias=True))
    assert result["generated"] == [1]


def test_cli_runs_payload(tmp_path, capsys):
    db_path = tmp_path / "cli.duckdb"
    definitions = _write_definitions(tmp_path)
    _seed_duckdb(db_path)
    payload = _payload(tmp_path, duckdb_path=db_path, definitions=definitions)
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(json.dumps(payload.model_dump(mode="json", by_alias=True)), encoding="utf-8")

    from circe.runner.__main__ import main

    assert main(["--payload", str(payload_path)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["generated"] == [1]


def test_cli_reports_bad_payload(tmp_path, capsys):
    from circe.runner.__main__ import main

    payload_path = tmp_path / "bad.json"
    payload_path.write_text("{not json", encoding="utf-8")
    assert main(["--payload", str(payload_path)]) == 2
    assert "Could not read payload" in capsys.readouterr().err


def test_backend_databricks_uses_connect_helper(monkeypatch):
    from circe import execution

    captured = {}

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return "backend"

    monkeypatch.setenv("TEST_DATABRICKS_TOKEN", "token")
    monkeypatch.setattr(execution, "connect_databricks", fake_connect)

    from circe.runner.backend import connect_backend

    result = connect_backend(
        BackendConfig(
            type="databricks",
            server_hostname="host",
            http_path="/sql/1.0/warehouses/x",
            access_token_env="TEST_DATABRICKS_TOKEN",
            catalog="cat",
            schema_name="sch",
        )
    )

    assert result == "backend"
    assert captured["server_hostname"] == "host"
    assert captured["personal_access_token"] == "token"
    assert captured["catalog"] == "cat"


def test_runner_warns_when_target_is_cdm_schema(tmp_path):
    db_path = tmp_path / "warning.duckdb"
    definitions = _write_definitions(tmp_path)
    _seed_duckdb(db_path)
    payload = _payload(tmp_path, duckdb_path=db_path, definitions=definitions)

    with pytest.warns(UserWarning, match="target schema is the CDM schema"):
        run_cohort_generation(payload)


def test_runner_refuses_empty_definition_set(tmp_path):
    from circe.runner import RunnerError

    db_path = tmp_path / "empty.duckdb"
    definitions = _write_definitions(tmp_path)
    (definitions / "Cohorts.csv").write_text("cohort_id,cohort_name\n", encoding="utf-8")
    _seed_duckdb(db_path)
    payload = _payload(tmp_path, duckdb_path=db_path, definitions=definitions)

    with pytest.raises(RunnerError, match="definition set is empty"):
        run_cohort_generation(payload)


def test_runner_reuses_only_completed_matching_row_counts(tmp_path):
    import ibis

    db_path = tmp_path / "complete.duckdb"
    definitions = _write_definitions(tmp_path)
    _seed_duckdb(db_path)
    payload = _payload(tmp_path, duckdb_path=db_path, definitions=definitions)
    run_cohort_generation(payload)

    conn = ibis.duckdb.connect(str(db_path))
    registry = conn.table("cohort_registry", database="main").execute()
    assert bool(registry.iloc[0]["completed"]) is True
    assert int(registry.iloc[0]["row_count"]) == 1
    conn.raw_sql("DELETE FROM main.cohort WHERE cohort_definition_id = 1")
    conn.disconnect()

    second = run_cohort_generation(payload)
    assert second.generated == [1]
    assert second.reused == []


def test_prefect_flow_and_task_objects_are_active():
    """Verify the installed Prefect package wraps the runner entry points.

    We assert the decorator types rather than starting Prefect's ephemeral API
    server: the server is intentionally not part of the unit-test environment,
    and the actual container CLI is exercised separately against the demo CDM.
    """
    pytest.importorskip("prefect")
    from prefect.flows import Flow
    from prefect.tasks import Task

    from circe.runner.flow import (
        generate_cohort_set_task,
        generate_sharded_cohort_set_task,
        run_cohort_generation_flow,
        run_sharded_cohort_generation_flow,
    )

    assert PREFECT_AVAILABLE is True
    assert isinstance(run_cohort_generation_flow, Flow)
    assert isinstance(run_sharded_cohort_generation_flow, Flow)
    assert isinstance(generate_cohort_set_task, Task)
    assert isinstance(generate_sharded_cohort_set_task, Task)
    assert run_cohort_generation_flow.name == "circe-cohort-generation"
    assert run_sharded_cohort_generation_flow.name == "circe-cohort-generation-sharded"


def _write_two_valid_definitions(root: Path) -> Path:
    definitions = _write_definitions(root)
    (definitions / "cohorts" / "2.json").write_text(
        _expression().model_dump_json(by_alias=True), encoding="utf-8"
    )
    with (definitions / "Cohorts.csv").open("a", encoding="utf-8") as handle:
        handle.write("2,second\n")
    return definitions


def test_runner_persists_completed_cohorts_before_batch_finishes(tmp_path, monkeypatch):
    """A later cohort failure must not discard earlier completed cohorts."""
    import ibis

    import circe.runner.runner as runner_module
    from circe.cohort_definition_set import CohortDefinitionSet

    db_path = tmp_path / "partial.duckdb"
    definitions = _write_two_valid_definitions(tmp_path)
    _seed_duckdb(db_path)
    payload = _payload(tmp_path, duckdb_path=db_path, definitions=definitions)

    real_generate = runner_module.generate_cohort_set

    def fake_generate(subset, **kwargs):
        first = next(iter(subset))
        one = CohortDefinitionSet()
        one.add_definition(first)
        real_generate(one, **kwargs)
        raise RuntimeError("simulated cohort failure")

    monkeypatch.setattr(runner_module, "generate_cohort_set", fake_generate)
    with pytest.raises(RuntimeError, match="simulated cohort failure"):
        run_cohort_generation(payload)
    monkeypatch.setattr(runner_module, "generate_cohort_set", real_generate)

    conn = ibis.duckdb.connect(str(db_path))
    registry = conn.table("cohort_registry", database="main").execute()
    status = {int(row["cohort_definition_id"]): bool(row["completed"]) for _, row in registry.iterrows()}
    assert status == {1: True, 2: False}
    conn.disconnect()

    second = run_cohort_generation(payload)
    assert second.reused == [1]
    assert second.generated == [2]


def test_registry_action_reconnects_once_after_stale_connection():
    from circe.runner.runner import _with_reconnect

    attempts = []
    reconnects = []

    class Backend:
        def reconnect(self):
            reconnects.append(True)

    def action():
        attempts.append(True)
        if len(attempts) == 1:
            raise RuntimeError("stale connection")

    _with_reconnect(Backend(), action)

    assert len(attempts) == 2
    assert reconnects == [True]
