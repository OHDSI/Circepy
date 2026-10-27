"""Tests for the legacy CohortGenerator-style cohort-set loader."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from circe.cohort_definition_set import (
    LegacyCohortDefinitionSet,
    LegacyCohortSetError,
    LoadedCohortDefinition,
    MissingCohortDefinitionFileError,
    UnsupportedLegacyFeatureError,
    load_cohort_definition_set,
)
from circe.cohort_definition_set._r_compat import (
    format_file_stem,
    normalize_header,
    snake_case_to_camel_case,
    transliterate_latin_ascii,
)
from circe.cohortdefinition import CohortExpression, ConditionOccurrence, PrimaryCriteria
from circe.vocabulary import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


def _load(**kwargs):
    kwargs.setdefault("base_dir", Path(kwargs["settings_file"]).parent)
    return load_cohort_definition_set(**kwargs)


def _expression(concept_id: int = 111) -> CohortExpression:
    concept_set = ConceptSet(
        id=1,
        expression=ConceptSetExpression(items=[ConceptSetItem(concept=Concept(conceptId=concept_id))]),
    )
    return CohortExpression(
        concept_sets=[concept_set],
        primary_criteria=PrimaryCriteria(criteria_list=[ConditionOccurrence(codeset_id=1)]),
    )


def _write_layout(
    root: Path,
    *,
    rows: list[dict[str, str]],
    json_files: dict[str, str],
    sql_files: dict[str, str] | None = None,
    json_folder: str = "cohorts",
    sql_folder: str = "sql/sql_server",
    settings_file: str = "Cohorts.csv",
) -> Path:
    settings = root / settings_file
    settings.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with settings.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    json_dir = root / json_folder
    json_dir.mkdir(parents=True, exist_ok=True)
    for stem, content in json_files.items():
        (json_dir / f"{stem}.json").write_text(content, encoding="utf-8")

    if sql_files is not None:
        sql_dir = root / sql_folder
        sql_dir.mkdir(parents=True, exist_ok=True)
        for stem, content in sql_files.items():
            (sql_dir / f"{stem}.sql").write_text(content, encoding="utf-8")

    return settings


def _basic_layout(tmp_path: Path, **kwargs) -> Path:
    expression_json = _expression().model_dump_json(by_alias=True)
    return _write_layout(
        tmp_path,
        rows=[
            {
                "cohort_id": "1",
                "cohort_name": "celecoxib",
                "atlas_id": "10",
                "logic_description": "Celecoxib exposure",
            },
            {
                "cohort_id": "2",
                "cohort_name": "celecoxibAge40",
                "atlas_id": "11",
                "logic_description": "Celecoxib and age >= 40",
            },
        ],
        json_files={"1": expression_json, "2": expression_json},
        sql_files={"1": "SELECT 1;", "2": "SELECT 2;"},
        **kwargs,
    )


def test_load_legacy_set_by_id(tmp_path):
    settings = _basic_layout(tmp_path)

    cohort_set = _load(
        settings_file=settings,
        json_folder="cohorts",
        sql_folder="sql/sql_server",
    )

    assert isinstance(cohort_set, LegacyCohortDefinitionSet)
    assert len(cohort_set) == 2
    first = cohort_set[1]
    assert isinstance(first, LoadedCohortDefinition)
    assert first.cohort_name == "celecoxib"
    assert first.sql == "SELECT 1;"
    assert first.metadata["atlasId"] == "10"
    assert first.source is not None
    assert first.source.json_file == tmp_path / "cohorts" / "1.json"
    assert first.source.sql_file == tmp_path / "sql" / "sql_server" / "1.sql"
    assert first.expression.primary_criteria is not None
    assert cohort_set.report.loaded_cohort_ids == [1, 2]
    assert cohort_set.report.missing_sql == []
    assert cohort_set.report.to_dict()["settings_file"] == str(settings)


def test_load_legacy_set_uses_cohort_name_for_files(tmp_path):
    expression_json = _expression().model_dump_json(by_alias=True)
    settings = _write_layout(
        tmp_path,
        rows=[
            {"cohort_id": "1", "cohort_name": "celecoxib"},
            {"cohort_id": "2", "cohort_name": "celecoxibAge40"},
        ],
        json_files={"celecoxib": expression_json, "celecoxibAge40": expression_json},
        sql_files={"celecoxib": "SELECT 1;", "celecoxibAge40": "SELECT 2;"},
    )

    cohort_set = _load(
        settings_file=settings,
        cohort_file_name_value=("cohortName",),
    )

    assert len(cohort_set) == 2
    assert cohort_set[2].source.json_file.name == "celecoxibAge40.json"


def test_load_legacy_set_custom_file_name_format(tmp_path):
    expression_json = _expression().model_dump_json(by_alias=True)
    settings = _write_layout(
        tmp_path,
        rows=[{"cohort_id": "7", "cohort_name": "SensitiveName"}],
        json_files={"7-SensitiveName": expression_json},
        sql_files={"7-SensitiveName": "SELECT 7;"},
    )

    cohort_set = _load(
        settings_file=settings,
        cohort_file_name_format="%s-%s",
        cohort_file_name_value=("cohortId", "cohortName"),
    )

    assert len(cohort_set) == 1
    assert cohort_set[7].source.json_file.name == "7-SensitiveName.json"


def test_missing_json_is_an_error(tmp_path):
    expression_json = _expression().model_dump_json(by_alias=True)
    settings = _write_layout(
        tmp_path,
        rows=[
            {"cohort_id": "1", "cohort_name": "ok"},
            {"cohort_id": "2", "cohort_name": "custom sql only"},
        ],
        json_files={"1": expression_json},
        sql_files={"1": "SELECT 1;", "2": "SELECT 2;"},
    )

    with pytest.raises(MissingCohortDefinitionFileError, match="Custom SQL"):
        _load(settings_file=settings)


def test_missing_json_can_be_skipped(tmp_path):
    expression_json = _expression().model_dump_json(by_alias=True)
    settings = _write_layout(
        tmp_path,
        rows=[
            {"cohort_id": "1", "cohort_name": "ok"},
            {"cohort_id": "2", "cohort_name": "custom sql only"},
        ],
        json_files={"1": expression_json},
        sql_files={"1": "SELECT 1;", "2": "SELECT 2;"},
    )

    cohort_set = _load(settings_file=settings, unsupported="skip")

    assert len(cohort_set) == 1
    assert cohort_set.report.loaded_cohort_ids == [1]
    assert cohort_set.report.skipped[0].cohort_id == 2


def test_missing_sql_warns_by_default_and_can_be_required(tmp_path):
    settings = _basic_layout(tmp_path)
    # Remove one SQL file.
    (tmp_path / "sql" / "sql_server" / "2.sql").unlink()

    cohort_set = _load(settings_file=settings)

    assert cohort_set[2].sql is None
    assert cohort_set.report.missing_sql == [2]
    assert any("no SQL file" in warning for warning in cohort_set.report.warnings)

    with pytest.raises(MissingCohortDefinitionFileError, match="missing its SQL"):
        _load(settings_file=settings, sql_required=True)


def test_include_sql_false_does_not_read_sql(tmp_path):
    settings = _basic_layout(tmp_path)

    cohort_set = _load(settings_file=settings, include_sql=False)

    assert cohort_set[1].sql is None
    assert cohort_set[1].source.sql_file is None
    assert cohort_set.report.missing_sql == []


def test_subset_rows_are_rejected_or_skipped(tmp_path):
    expression_json = _expression().model_dump_json(by_alias=True)
    settings = _write_layout(
        tmp_path,
        rows=[
            {"cohort_id": "1", "cohort_name": "base"},
            {"cohort_id": "2", "cohort_name": "subset", "is_subset": "TRUE"},
        ],
        json_files={"1": expression_json, "2": expression_json},
        sql_files={"1": "SELECT 1;", "2": "SELECT 2;"},
    )

    with pytest.raises(UnsupportedLegacyFeatureError, match="subset"):
        _load(settings_file=settings)

    cohort_set = _load(settings_file=settings, unsupported="skip")
    assert len(cohort_set) == 1
    assert cohort_set.report.skipped[0].cohort_id == 2


def test_templated_rows_are_rejected(tmp_path):
    expression_json = _expression().model_dump_json(by_alias=True)
    settings = _write_layout(
        tmp_path,
        rows=[{"cohort_id": "1", "cohort_name": "template", "is_templated_cohort": "TRUE"}],
        json_files={"1": expression_json},
    )

    with pytest.raises(UnsupportedLegacyFeatureError, match="templated"):
        _load(settings_file=settings)


def test_invalid_settings_and_headers(tmp_path):
    expression_json = _expression().model_dump_json(by_alias=True)
    settings = _write_layout(
        tmp_path,
        rows=[{"id": "1", "name": "bad"}],
        json_files={"1": expression_json},
    )
    with pytest.raises(LegacyCohortSetError, match="cohortId"):
        _load(settings_file=settings)

    bad_json = _write_layout(
        tmp_path / "bad_json",
        rows=[{"cohort_id": "1", "cohort_name": "bad"}],
        json_files={"1": "{not json"},
    )
    with pytest.raises(LegacyCohortSetError, match="Invalid Circe JSON"):
        _load(settings_file=bad_json)


def test_duplicate_ids_and_file_stems(tmp_path):
    expression_json = _expression().model_dump_json(by_alias=True)
    duplicate_id = _write_layout(
        tmp_path / "dup_id",
        rows=[
            {"cohort_id": "1", "cohort_name": "a"},
            {"cohort_id": "1", "cohort_name": "b"},
        ],
        json_files={"1": expression_json},
    )
    with pytest.raises(LegacyCohortSetError, match="Duplicate cohortId"):
        _load(settings_file=duplicate_id)

    duplicate_stem = _write_layout(
        tmp_path / "dup_stem",
        rows=[
            {"cohort_id": "1", "cohort_name": "same"},
            {"cohort_id": "2", "cohort_name": "same"},
        ],
        json_files={"same": expression_json},
    )
    with pytest.raises(LegacyCohortSetError, match="same file stem"):
        _load(
            settings_file=duplicate_stem,
            cohort_file_name_value=("cohortName",),
        )


def test_path_traversal_in_file_stem_is_rejected(tmp_path):
    expression_json = _expression().model_dump_json(by_alias=True)
    settings = _write_layout(
        tmp_path,
        rows=[{"cohort_id": "1", "cohort_name": "x"}],
        json_files={"1": expression_json},
    )

    with pytest.raises(LegacyCohortSetError, match="path separator"):
        _load(
            settings_file=settings,
            cohort_file_name_format="../%s",
        )


def test_loaded_definition_set_can_be_generated(tmp_path):
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    expression_json = _expression().model_dump_json(by_alias=True)
    settings = _write_layout(
        tmp_path,
        rows=[{"cohort_id": "1", "cohort_name": "loaded"}],
        json_files={"1": expression_json},
    )
    cohort_set = _load(settings_file=settings)

    from circe.cohort_definition_set import generate_cohort_set

    conn = ibis.duckdb.connect()
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

    results = generate_cohort_set(
        cohort_set,
        backend=conn,
        cdm_schema="main",
        cohort_table="cohort",
        shared=True,
    )
    assert [result.status for result in results] == ["COMPLETE"]
    assert conn.table("cohort").count().execute() == 1


# ---------------------------------------------------------------------------
# R string compatibility
# ---------------------------------------------------------------------------


def test_snake_case_to_camel_case_matches_sqlrender():
    assert snake_case_to_camel_case("cohort_id") == "cohortId"
    assert snake_case_to_camel_case("cohort_ID") == "cohortId"
    assert snake_case_to_camel_case("logic_description_2") == "logicDescription2"
    assert normalize_header("cohortId") == "cohortId"
    assert normalize_header("COHORT_ID") == "COHORT_ID"


def test_transliteration_matches_stringi_examples():
    assert transliterate_latin_ascii("café") == "cafe"
    assert transliterate_latin_ascii("Straße") == "Strasse"
    assert transliterate_latin_ascii("Ærø") == "AEro"
    assert transliterate_latin_ascii("naïve") == "naive"
    # stringi's Latin-ASCII transform leaves non-Latin scripts untouched.
    assert transliterate_latin_ascii("Москва") == "Москва"
    assert transliterate_latin_ascii("東京") == "東京"


def test_format_file_stem():
    assert format_file_stem("%s", [1]) == "1"
    assert format_file_stem("%d", ["1"]) == "1"
    assert format_file_stem("%s-%s", [1, "café"]) == "1-cafe"
    with pytest.raises(ValueError):
        format_file_stem("%s-%s", [1])


def test_legacy_sql_oracle_matches_generated_rows(tmp_path):
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    expression_json = _expression().model_dump_json(by_alias=True)
    legacy_sql = """
CREATE TABLE #final_cohort AS
SELECT co.person_id,
       co.condition_start_date AS start_date,
       op.observation_period_end_date AS end_date
FROM @cdm_database_schema.condition_occurrence co
JOIN @cdm_database_schema.observation_period op
  ON co.person_id = op.person_id
 AND co.condition_start_date BETWEEN op.observation_period_start_date AND op.observation_period_end_date
WHERE co.condition_concept_id = 111;

DELETE FROM @target_database_schema.@target_cohort_table
WHERE cohort_definition_id = @target_cohort_id;

INSERT INTO @target_database_schema.@target_cohort_table
  (cohort_definition_id, subject_id, cohort_start_date, cohort_end_date)
SELECT @target_cohort_id, person_id, start_date, end_date FROM #final_cohort;

DROP TABLE #final_cohort;
"""
    settings = _write_layout(
        tmp_path,
        rows=[{"cohort_id": "1", "cohort_name": "oracle"}],
        json_files={"1": expression_json},
        sql_files={"1": legacy_sql},
    )
    cohort_set = _load(settings_file=settings)

    conn = ibis.duckdb.connect()
    conn.create_table(
        "person",
        obj=ibis.memtable(
            {"person_id": [1, 2], "year_of_birth": [1980, 1985], "gender_concept_id": [8507, 8532]}
        ),
        overwrite=True,
    )
    conn.create_table(
        "observation_period",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "observation_period_id": [1, 2],
                "observation_period_start_date": ["2019-01-01", "2019-01-01"],
                "observation_period_end_date": ["2021-12-31", "2021-12-31"],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "condition_occurrence",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "condition_occurrence_id": [10, 11],
                "condition_concept_id": [111, 222],
                "condition_start_date": ["2020-01-01", "2020-01-02"],
                "condition_end_date": ["2020-01-01", "2020-01-02"],
            }
        ),
        overwrite=True,
    )

    from circe.cohort_definition_set import verify_against_legacy_sql

    comparisons = verify_against_legacy_sql(
        cohort_set,
        backend=conn,
        cdm_schema="main",
        vocabulary_schema="main",
        target_schema="main",
        target_table="cohort_legacy",
        generated_table="cohort_circe",
        target_dialect="duckdb",
    )

    assert len(comparisons) == 1
    assert comparisons[0].legacy_rows == 1
    assert comparisons[0].generated_rows == 1
    assert comparisons[0].matching_rows is True


def test_render_legacy_sql_replaces_placeholders(tmp_path):
    expression_json = _expression().model_dump_json(by_alias=True)
    settings = _write_layout(
        tmp_path,
        rows=[{"cohort_id": "5", "cohort_name": "render"}],
        json_files={"5": expression_json},
        sql_files={"5": "SELECT @target_cohort_id AS id;"},
    )
    cohort_set = _load(settings_file=settings)

    from circe.cohort_definition_set import render_legacy_sql

    rendered = render_legacy_sql(
        cohort_set[5],
        cdm_schema="cdm",
        results_schema="results",
        target_table="cohort",
        target_dialect="duckdb",
    )
    assert "5 AS id" in rendered


def test_verify_requires_loaded_definitions(tmp_path):
    from circe.cohort_definition_set import CohortDefinitionSet, verify_against_legacy_sql

    expression_json = _expression().model_dump_json(by_alias=True)
    settings = _write_layout(
        tmp_path,
        rows=[{"cohort_id": "1", "cohort_name": "plain"}],
        json_files={"1": expression_json},
    )
    loaded = _load(settings_file=settings)
    plain = CohortDefinitionSet()
    plain.add(1, "plain", loaded[1].expression)

    class DummyBackend:
        name = "duckdb"

    with pytest.raises(LegacyCohortSetError, match="requires a set loaded"):
        verify_against_legacy_sql(plain, backend=DummyBackend(), cdm_schema="main")


def test_verify_requires_sql(tmp_path):
    from circe.cohort_definition_set import verify_against_legacy_sql

    expression_json = _expression().model_dump_json(by_alias=True)
    settings = _write_layout(
        tmp_path,
        rows=[{"cohort_id": "1", "cohort_name": "no sql"}],
        json_files={"1": expression_json},
    )
    loaded = _load(settings_file=settings)

    class DummyBackend:
        name = "duckdb"

    with pytest.raises(LegacyCohortSetError, match="without SQL"):
        verify_against_legacy_sql(loaded, backend=DummyBackend(), cdm_schema="main")
