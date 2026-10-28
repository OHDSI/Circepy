"""Tests for family tagging and family-balanced shard generation."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from circe.cohort_definition_set import (
    CohortDefinitionSet,
    load_cohort_definition_set,
)
from circe.cohortdefinition import CohortExpression, ConditionOccurrence, PrimaryCriteria
from circe.runner import RunnerPayload, plan_family_shards, run_sharded_cohort_generation
from circe.runner.sharding import build_shard_payload, plan_payload_shards
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


def _write_definitions(root: Path, rows: list[dict[str, str]]) -> Path:
    data = root / "definitions"
    (data / "cohorts").mkdir(parents=True)
    with (data / "Cohorts.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["cohort_id", "cohort_name", "family"])
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        (data / "cohorts" / f"{row['cohort_id']}.json").write_text(
            _expression().model_dump_json(by_alias=True), encoding="utf-8"
        )
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


def _tagged_set() -> CohortDefinitionSet:
    cohort_set = CohortDefinitionSet()
    families = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}
    cohort_id = 1
    for family, count in families.items():
        for _ in range(count):
            cohort_set.add(cohort_id, f"cohort {cohort_id}", _expression(), family=family)
            cohort_id += 1
    return cohort_set


def test_family_tags_are_loaded_and_grouped(tmp_path):
    definitions = _write_definitions(
        tmp_path,
        [
            {"cohort_id": "1", "cohort_name": "one", "family": "family-a"},
            {"cohort_id": "2", "cohort_name": "two", "family": "family-a"},
            {"cohort_id": "3", "cohort_name": "three", "family": "family-b"},
            {"cohort_id": "4", "cohort_name": "four", "family": ""},
        ],
    )

    cohort_set = load_cohort_definition_set(
        settings_file=definitions / "Cohorts.csv",
        json_folder=definitions / "cohorts",
        sql_folder=None,
        base_dir=definitions,
    )

    assert cohort_set[1].family == "family-a"
    assert cohort_set[3].family == "family-b"
    assert cohort_set[4].family is None
    assert cohort_set.families()["family-a"] == [1, 2]
    assert cohort_set.families()["__cohort_4"] == [4]


def test_loader_family_and_cohort_id_filters(tmp_path):
    definitions = _write_definitions(
        tmp_path,
        [
            {"cohort_id": "1", "cohort_name": "one", "family": "a"},
            {"cohort_id": "2", "cohort_name": "two", "family": "a"},
            {"cohort_id": "3", "cohort_name": "three", "family": "b"},
        ],
    )
    settings = definitions / "Cohorts.csv"

    family_set = load_cohort_definition_set(
        settings_file=settings,
        json_folder=definitions / "cohorts",
        sql_folder=None,
        base_dir=definitions,
        families=["b"],
    )
    assert [cohort.cohort_id for cohort in family_set] == [3]

    id_set = load_cohort_definition_set(
        settings_file=settings,
        json_folder=definitions / "cohorts",
        sql_folder=None,
        base_dir=definitions,
        cohort_ids=[1, 3],
    )
    assert [cohort.cohort_id for cohort in id_set] == [1, 3]


def test_plan_family_shards_keeps_families_together_and_balances():
    cohort_set = _tagged_set()

    shards = plan_family_shards(cohort_set, shard_count=3, registry_table="cohort_registry")

    assert len(shards) == 3
    assigned = [cohort_id for shard in shards for cohort_id in shard.cohort_ids]
    assert sorted(assigned) == list(range(1, 16))
    assert len(assigned) == len(set(assigned))

    for family in {"A", "B", "C", "D", "E"}:
        family_ids = {cohort.cohort_id for cohort in cohort_set if cohort.family == family}
        for cohort_id in family_ids:
            owners = [shard for shard in shards if cohort_id in shard.cohort_ids]
            assert len(owners) == 1
        assert len({owner.shard_id for owner in shards if family_ids & set(owner.cohort_ids)}) == 1

    loads = [len(shard.cohort_ids) for shard in shards]
    assert max(loads) - min(loads) <= 5
    assert all(shard.registry_table.startswith("cohort_registry_s") for shard in shards)


def test_plan_one_shard_per_family_when_fewer_families():
    shards = plan_family_shards(_tagged_set(), shard_count=100, registry_table=None)
    assert len(shards) == 5
    assert all(shard.registry_table is None for shard in shards)


def test_shard_payload_filters_to_shard_ids(tmp_path):
    definitions = _write_definitions(
        tmp_path,
        [
            {"cohort_id": "1", "cohort_name": "one", "family": "a"},
            {"cohort_id": "2", "cohort_name": "two", "family": "b"},
        ],
    )
    payload = _payload(tmp_path, duckdb_path=tmp_path / "x.duckdb", definitions=definitions)
    shards = plan_payload_shards(payload, shard_count=2)
    worker = build_shard_payload(payload, shards[0])

    assert worker.definitions.cohort_ids == list(shards[0].cohort_ids)
    assert worker.target.registry_table == shards[0].registry_table
    assert worker.metadata["circe_shard"] == shards[0].shard_id


def test_run_sharded_generation_same_table(tmp_path):
    db_path = tmp_path / "sharded.duckdb"
    definitions = _write_definitions(
        tmp_path,
        [
            {"cohort_id": str(index), "cohort_name": f"cohort {index}", "family": f"f{index % 2}"}
            for index in range(1, 7)
        ],
    )
    _seed_duckdb(db_path)
    payload = _payload(tmp_path, duckdb_path=db_path, definitions=definitions)

    result = run_sharded_cohort_generation(
        payload,
        shard_count=2,
        # DuckDB permits only one writer per file; the process driver is still
        # exercised, while true parallel writers are covered by Postgres/
        # Databricks integration runs.
        max_workers=1,
        retries=0,
    )

    assert result.to_dict()["status"] == "COMPLETE"
    assert sorted(result.results) == [0, 1]

    import ibis

    conn = ibis.duckdb.connect(str(db_path))
    assert conn.table("cohort", database="main").count().execute() == 6
    registry_tables = {name for name in conn.list_tables() if name.startswith("cohort_registry_s")}
    assert len(registry_tables) == 2
    conn.disconnect()


def test_plan_scales_to_564_families():
    cohort_set = CohortDefinitionSet()
    for index in range(564):
        cohort_set.add(index + 1, f"cohort {index + 1}", _expression(), family=f"family-{index}")

    shards = plan_family_shards(cohort_set, shard_count=10, registry_table="registry")

    assert len(shards) == 10
    assigned = [cohort_id for shard in shards for cohort_id in shard.cohort_ids]
    assert sorted(assigned) == list(range(1, 565))
    assert len(assigned) == 564
    assert max(len(shard.cohort_ids) for shard in shards) <= 57
    assert min(len(shard.cohort_ids) for shard in shards) >= 56


def test_cli_plan_shards(tmp_path, capsys):
    definitions = _write_definitions(
        tmp_path,
        [
            {"cohort_id": "1", "cohort_name": "one", "family": "a"},
            {"cohort_id": "2", "cohort_name": "two", "family": "b"},
        ],
    )
    payload = _payload(tmp_path, duckdb_path=tmp_path / "plan.duckdb", definitions=definitions)
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(payload.model_dump_json(by_alias=True), encoding="utf-8")
    manifest_path = tmp_path / "shards.json"

    from circe.runner.__main__ import main

    assert (
        main(
            [
                "--payload",
                str(payload_path),
                "--shards",
                "2",
                "--plan-shards",
                str(manifest_path),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["shards"] == 2
    manifest = json.loads(manifest_path.read_text())
    assert manifest["shard_count"] == 2
    assert len(manifest["shards"]) == 2
    assert all(shard["payload"]["definitions"]["cohort_ids"] for shard in manifest["shards"])
