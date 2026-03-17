import json
from typing import Optional, list, set

from pydantic import AliasChoices, Field

from circe.cohortdefinition import CohortExpression, PrimaryCriteria
from circe.cohortdefinition.builders.base import CriteriaSqlBuilder
from circe.cohortdefinition.builders.utils import BuilderOptions, CriteriaColumn
from circe.cohortdefinition.cohort_expression_query_builder import (
    BuildExpressionQueryOptions,
    CohortExpressionQueryBuilder,
)
from circe.cohortdefinition.criteria import Criteria
from circe.cohortdefinition.printfriendly.markdown_render import MarkdownRender
from circe.extensions import get_registry
from circe.vocabulary.concept import Concept

# -----------------------------------------------------------------------------
# 1. Define the Extension Components
# -----------------------------------------------------------------------------


class WeatherCondition(Criteria):
    """
    Example extension criteria for 'Weather Conditions'.
    Imagine a CDM extension where weather data is linked to persons.
    """

    weather_concept_id: Optional[list[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("WeatherConceptId", "weatherConceptId"),
        serialization_alias="WeatherConceptId",
    )
    temperature_celsius: Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices("TemperatureCelsius", "temperatureCelsius"),
        serialization_alias="TemperatureCelsius",
    )


# Important: Rebuild models to resolve forward references inherited from Criteria
WeatherCondition.model_rebuild()


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
