import json
from datetime import date

import pytest
from pydantic import AliasChoices, Field

from circe.cohortdefinition import CohortExpression, CriteriaGroup, PrimaryCriteria
from circe.cohortdefinition.builders.base import CriteriaSqlBuilder
from circe.cohortdefinition.builders.utils import BuilderOptions, CriteriaColumn
from circe.cohortdefinition.cohort_expression_query_builder import (
    BuildExpressionQueryOptions,
    CohortExpressionQueryBuilder,
)
from circe.cohortdefinition.criteria import Criteria
from circe.cohortdefinition.printfriendly.markdown_render import MarkdownRender
from circe.execution import build_cohort
from circe.execution.lower.common import (
    append_concept_filters,
    build_standard_domain_plan,
    lower_common_steps,
)
from circe.execution.lower.criteria import lower_criterion
from circe.execution.normalize import build_normalized_criterion, normalize_criterion
from circe.execution.plan.events import FilterByNumericRange
from circe.execution.plan.predicates import NumericRangePredicate
from circe.extensions import get_registry, lowerer, normalizer
from circe.vocabulary.concept import Concept

# -----------------------------------------------------------------------------
# 1. Define the Extension Components
# -----------------------------------------------------------------------------


class WeatherCondition(Criteria):
    """
    Example extension criteria for 'Weather Conditions'.
    Imagine a CDM extension where weather data is linked to persons.
    """

    weather_concept_id: list[Concept] | None = Field(
        default=None,
        validation_alias=AliasChoices("WeatherConceptId", "weatherConceptId"),
        serialization_alias="WeatherConceptId",
    )
    temperature_celsius: float | None = Field(
        default=None,
        validation_alias=AliasChoices("TemperatureCelsius", "temperatureCelsius"),
        serialization_alias="TemperatureCelsius",
    )


# Important: Rebuild models to resolve forward references inherited from Criteria
WeatherCondition.model_rebuild(_types_namespace={"CriteriaGroup": CriteriaGroup})


class WeatherConditionSqlBuilder(CriteriaSqlBuilder[WeatherCondition]):
    """
    SQL Builder for WeatherCondition.
    """

    def get_query_template(self) -> str:
        return """
SELECT C.person_id, C.weather_id as event_id, C.observation_date as start_date, C.observation_date as end_date,
       NULL as visit_occurrence_id, C.observation_date as sort_date
FROM @cdm_database_schema.weather_data C
WHERE @whereClause
"""

    def get_default_columns(self) -> set[CriteriaColumn]:
        return {CriteriaColumn.START_DATE, CriteriaColumn.END_DATE}

    def get_table_column_for_criteria_column(self, column: CriteriaColumn) -> str:
        if column == CriteriaColumn.START_DATE or column == CriteriaColumn.END_DATE:
            return "C.observation_date"
        else:
            raise ValueError(f"Unsupported column: {column}")

    def get_criteria_sql_with_options(self, criteria: WeatherCondition, options: BuilderOptions) -> str:
        query = self.get_query_template()
        where_clauses = ["1=1"]

        if criteria.weather_concept_id:
            ids = [str(c.concept_id) for c in criteria.weather_concept_id if c.concept_id]
            if ids:
                where_clauses.append(f"C.weather_concept_id IN ({','.join(ids)})")

        if criteria.temperature_celsius is not None:
            where_clauses.append(f"C.temp_c >= {criteria.temperature_celsius}")

        query = query.replace(
            "@cdm_database_schema", options.cdm_database_schema if options else "@cdm_database_schema"
        )
        query = query.replace("@whereClause", " AND ".join(where_clauses))
        return query


# Register the ibis normalizer/lowerer at import time, mirroring how a real
# extension package registers itself.
@normalizer(WeatherCondition)
def _normalize_weather_condition(criteria: WeatherCondition):
    return build_normalized_criterion(
        criteria=criteria,
        criterion_type="WeatherCondition",
        domain="weather",
        source_table="weather_data",
        event_id_column="weather_id",
        start_date_column="observation_date",
        end_date_column="observation_date",
        concept_column="weather_concept_id",
        source_concept_column=None,
        visit_occurrence_column="visit_occurrence_id",
        codeset_id=None,
        first=False,
        occurrence_start_date=None,
        occurrence_end_date=None,
    )


@lowerer(WeatherCondition)
def _lower_weather_condition(criterion, *, criterion_index: int):
    raw = criterion.raw_criteria
    steps = lower_common_steps(criterion)
    append_concept_filters(
        steps,
        column="weather_concept_id",
        concepts=raw.weather_concept_id,
    )
    if raw.temperature_celsius is not None:
        steps.append(
            FilterByNumericRange(
                column="temp_c",
                predicate=NumericRangePredicate(
                    op=">=",
                    value=raw.temperature_celsius,
                    extent=None,
                ),
            )
        )
    return build_standard_domain_plan(
        criterion,
        criterion_index=criterion_index,
        steps=steps,
    )


# -----------------------------------------------------------------------------
# 2. Test Cases
# -----------------------------------------------------------------------------


def test_simple_extension_integration(tmp_path):
    """
    Full end-to-end test of the extension system.
    """
    registry = get_registry()

    # Register the extension
    registry.register_criteria_class("WeatherCondition", WeatherCondition)
    registry.register_sql_builder(WeatherCondition, WeatherConditionSqlBuilder)

    # Create a dummy template file
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    template_file = template_dir / "weather_condition.j2"
    template_file.write_text("""
Weather condition: {{ criteria.weather_concept_id[0].concept_name if criteria.weather_concept_id else 'Any' }}
{% if criteria.temperature_celsius %} with temperature >= {{ criteria.temperature_celsius }}°C{% endif %}.
""")

    registry.add_template_path(template_dir)
    registry.register_markdown_template(WeatherCondition, "weather_condition.j2")

    # Construct a cohort using the extension
    weather_concept = Concept(
        concept_id=123, concept_name="Snowing", standard_concept="S", concept_code="SNOW"
    )
    weather_criteria = WeatherCondition(weather_concept_id=[weather_concept], temperature_celsius=-5.0)

    expression = CohortExpression(
        primary_criteria=PrimaryCriteria(
            criteria_list=[weather_criteria],
            observation_window={"priorDays": 0, "postDays": 0},
            primary_limit={"type": "First"},
        ),
        concept_sets=[],
        inclusion_rules=[],
        qualified_limit={"type": "First"},
    )

    # 1. Test SQL Generation
    builder = CohortExpressionQueryBuilder()
    sql_options = BuildExpressionQueryOptions()
    sql_options.cdm_schema = "my_cdm"
    sql = builder.build_expression_query(expression, sql_options)

    assert "weather_data" in sql
    assert "weather_concept_id IN (123)" in sql
    assert "temp_c >= -5.0" in sql

    # 2. Test Markdown Rendering
    renderer = MarkdownRender()
    markdown = renderer.render_cohort_expression(expression)

    assert "Weather condition: Snowing" in markdown
    assert "temperature >= -5.0°C" in markdown

    # 3. Test JSON Serialization/Deserialization (Round-trip)
    # This verifies that Pydantic uses the registry to find the class
    json_str = expression.model_dump_json(by_alias=True)
    loaded_expression = CohortExpression.model_validate_json(json_str)

    # Check that it loaded as a WeatherCondition object, not a generic Criteria or dict
    loaded_criteria = loaded_expression.primary_criteria.criteria_list[0]
    assert isinstance(loaded_criteria, WeatherCondition)
    assert loaded_criteria.temperature_celsius == -5.0
    assert loaded_criteria.weather_concept_id[0].concept_name == "Snowing"


def test_unregistered_extension_fails():
    """
    Verifies that using an unregistered extension key in JSON doesn't result
    in a custom extension object. It will instead fall back to a standard
    Criteria type (like ConditionOccurrence) because all of them have optional
    fields and ignore extra fields.
    """
    # Using a key that is NOT registered
    bad_json_str = json.dumps(
        {
            "PrimaryCriteria": {
                "CriteriaList": [{"UnregisteredKey": {"SomeSpecificField": "Value"}}],
                "ObservationWindow": {"PriorDays": 0, "PostDays": 0},
                "PrimaryLimit": {"Type": "First"},
            }
        }
    )

    loaded = CohortExpression.model_validate_json(bad_json_str)
    item = loaded.primary_criteria.criteria_list[0]

    # It should NOT be a WeatherCondition (because it's not registered)
    assert not isinstance(item, WeatherCondition)

    # It will likely be a ConditionOccurrence because it's first in the Union
    # and all fields are optional with extra='ignore'.
    assert not hasattr(item, "SomeSpecificField")


def test_registry_exposes_extension_normalizer_and_lowerer():
    registry = get_registry()
    criteria = WeatherCondition(
        weather_concept_id=[Concept(concept_id=123, concept_name="Snowing")],
        temperature_celsius=-5.0,
    )

    assert registry.get_normalizer(WeatherCondition) is _normalize_weather_condition
    assert registry.get_lowerer(WeatherCondition) is _lower_weather_condition

    normalized = normalize_criterion(criteria)
    assert normalized.criterion_type == "WeatherCondition"
    assert normalized.domain == "weather"
    assert normalized.source_table == "weather_data"
    assert normalized.concept_column == "weather_concept_id"

    plan = lower_criterion(normalized, criterion_index=0)
    assert plan.source.table_name == "weather_data"
    assert plan.source.event_id_column == "weather_id"
    assert any(isinstance(step, FilterByNumericRange) for step in plan.steps)


def test_extension_criteria_execute_through_ibis():
    ibis = pytest.importorskip("ibis")
    _ = pytest.importorskip("duckdb")

    conn = ibis.duckdb.connect()
    conn.create_table(
        "person",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "year_of_birth": [1980, 1985],
                "gender_concept_id": [8507, 8532],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "observation_period",
        obj=ibis.memtable(
            {
                "person_id": [1, 2],
                "observation_period_id": [10, 11],
                "observation_period_start_date": [date(2019, 1, 1), date(2019, 1, 1)],
                "observation_period_end_date": [date(2021, 12, 31), date(2021, 12, 31)],
            }
        ),
        overwrite=True,
    )
    conn.create_table(
        "weather_data",
        obj=ibis.memtable(
            {
                "weather_id": [1, 2],
                "person_id": [1, 2],
                "weather_concept_id": [123, 123],
                "temp_c": [-10.0, 10.0],
                "observation_date": [date(2020, 1, 1), date(2020, 1, 2)],
                "visit_occurrence_id": [0, 0],
            }
        ),
        overwrite=True,
    )

    weather_criteria = WeatherCondition(
        weather_concept_id=[Concept(concept_id=123, concept_name="Snowing")],
        temperature_celsius=-5.0,
    )
    expression = CohortExpression(
        primary_criteria=PrimaryCriteria(
            criteria_list=[weather_criteria],
            observation_window={"priorDays": 0, "postDays": 0},
        )
    )

    rows = build_cohort(expression, backend=conn, cdm_schema="main").execute()

    # Only person 2 has temp_c >= -5 for the requested weather concept.
    assert list(rows["person_id"]) == [2]
    assert len(rows) == 1
