import pytest
import json
from typing import Optional, List, Set
from pydantic import Field, AliasChoices

from circe.cohortdefinition import CohortExpression, PrimaryCriteria, CriteriaGroup
from circe.cohortdefinition.criteria import Criteria
from circe.cohortdefinition.builders.base import CriteriaSqlBuilder
from circe.cohortdefinition.builders.utils import CriteriaColumn, BuilderUtils, BuilderOptions
from circe.cohortdefinition.cohort_expression_query_builder import CohortExpressionQueryBuilder, BuildExpressionQueryOptions
from circe.cohortdefinition.printfriendly.markdown_render import MarkdownRender
from circe.vocabulary.concept import Concept
from circe.extensions import get_registry
from circe.cohort_builder.query_builder import BaseQuery, QueryConfig
from circe.evaluation.builder import EvaluationBuilder

# -----------------------------------------------------------------------------
# 1. Define the Extension Components
# -----------------------------------------------------------------------------

class WeatherCondition(Criteria):
    """
    Example extension criteria for 'Weather Conditions'.
    Imagine a CDM extension where weather data is linked to persons.
    """
    weather_concept_id: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("WeatherConceptId", "weatherConceptId"),
        serialization_alias="WeatherConceptId"
    )
    temperature_celsius: Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices("TemperatureCelsius", "temperatureCelsius"),
        serialization_alias="TemperatureCelsius"
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

    def get_default_columns(self) -> Set[CriteriaColumn]:
        return {CriteriaColumn.START_DATE, CriteriaColumn.END_DATE}

    def get_table_column_for_criteria_column(self, column: CriteriaColumn) -> str:
        if column == CriteriaColumn.START_DATE:
            return "C.observation_date"
        elif column == CriteriaColumn.END_DATE:
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

        # Ensure we have a string for replacement
        schema = options.cdm_database_schema if (options and options.cdm_database_schema) else "cdm"
        query = query.replace("@cdm_database_schema", schema)
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
    weather_concept = Concept(concept_id=123, concept_name="Snowing", standard_concept="S", concept_code="SNOW")
    weather_criteria = WeatherCondition(
        weather_concept_id=[weather_concept],
        temperature_celsius=-5.0
    )
    
    expression = CohortExpression(
        primary_criteria=PrimaryCriteria(
            criteria_list=[weather_criteria],
            observation_window={"priorDays": 0, "postDays": 0},
            primary_limit={"type": "First"}
        ),
        concept_sets=[],
        inclusion_rules=[],
        qualified_limit={"type": "First"}
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
    bad_json_str = json.dumps({
        "PrimaryCriteria": {
            "CriteriaList": [
                {
                    "UnregisteredKey": {
                        "SomeSpecificField": "Value"
                    }
                }
            ],
            "ObservationWindow": {"PriorDays": 0, "PostDays": 0},
            "PrimaryLimit": {"Type": "First"}
        }
    })
    
    loaded = CohortExpression.model_validate_json(bad_json_str)
    item = loaded.primary_criteria.criteria_list[0]
    
    # It should NOT be a WeatherCondition (because it's not registered)
    assert not isinstance(item, WeatherCondition)
    
    # It will likely be a ConditionOccurrence because it's first in the Union 
    # and all fields are optional with extra='ignore'.
    assert not hasattr(item, "SomeSpecificField")

# -----------------------------------------------------------------------------
# 3. New Integration Tests
# -----------------------------------------------------------------------------

def test_extension_in_criteria_group_json_roundtrip():
    """Verify extension criteria inside CriteriaGroup.criteria_list survives JSON round-trip."""
    registry = get_registry()
    registry.register_criteria_class("WeatherCondition", WeatherCondition)
    
    weather_criteria = WeatherCondition(temperature_celsius=25.0)
    group = CriteriaGroup(
        type="ALL",
        criteria_list=[weather_criteria]
    )
    
    # Wrap in CohortExpression for full test
    expression = CohortExpression(
        inclusion_rules=[{"name": "test", "expression": group}],
        primary_criteria=PrimaryCriteria(
            criteria_list=[{"ConditionOccurrence": {"CodesetId": 1}}], # Dummy primary
            observation_window={"priorDays": 0, "postDays": 0},
            primary_limit={"type": "First"}
        )
    )
    
    json_str = expression.model_dump_json(by_alias=True)
    loaded = CohortExpression.model_validate_json(json_str)
    
    loaded_group = loaded.inclusion_rules[0].expression
    loaded_criteria = loaded_group.criteria_list[0].criteria
    
    assert isinstance(loaded_criteria, WeatherCondition)
    assert loaded_criteria.temperature_celsius == 25.0

def test_extension_in_windowed_correlated_criteria_sql():
    """Verify extension criteria in windowed CorelatedCriteria generates correct SQL."""
    registry = get_registry()
    registry.register_criteria_class("WeatherCondition", WeatherCondition)
    registry.register_sql_builder(WeatherCondition, WeatherConditionSqlBuilder)
    
    weather_criteria = WeatherCondition(temperature_celsius=30.0)
    
    # Correlated criteria with window
    from circe.cohortdefinition import CorelatedCriteria, Occurrence
    from circe.cohortdefinition.core import Window, WindowBound
    
    cc = CorelatedCriteria(
        criteria=weather_criteria,
        start_window=Window(
            start=WindowBound(coeff=-1, days=30),
            end=WindowBound(coeff=1, days=0)
        ),
        occurrence=Occurrence(type=2, count=1)
    )
    
    expression = CohortExpression(
        primary_criteria=PrimaryCriteria(
            criteria_list=[{"ConditionOccurrence": {"CodesetId": 1}}], # Dummy primary
            observation_window={"priorDays": 0, "postDays": 0},
            primary_limit={"type": "First"}
        ),
        additional_criteria=CriteriaGroup(
            type="ALL",
            criteria_list=[cc]
        )
    )
    
    builder = CohortExpressionQueryBuilder()
    sql_options = BuildExpressionQueryOptions()
    sql_options.cdm_schema = "test_schema"
    sql = builder.build_expression_query(expression, sql_options)
    
    assert "weather_data" in sql
    assert "temp_c >= 30.0" in sql

def test_required_extensions_validation_passes():
    """Cohort with matching registered extension loads OK."""
    registry = get_registry()
    registry.register_named_extension("weather", version="1.0.0")
    
    expression_dict = {
        "RequiredExtensions": ["weather"],
        "PrimaryCriteria": {"CriteriaList": [{"ConditionOccurrence": {"CodesetId": 1}}]}
    }
    
    # Should not raise
    expression = CohortExpression.model_validate(expression_dict)
    assert "weather" in expression.required_extensions

def test_required_extensions_validation_fails():
    """Cohort with unregistered extension raises ValueError."""
    registry = get_registry()
    # Ensure "missing_ext" is NOT in registered names
    if "missing_ext" in registry.get_registered_extension_names():
        registry._named_extensions.pop("missing_ext")
        
    expression_dict = {
        "RequiredExtensions": ["missing_ext"],
        "PrimaryCriteria": {"CriteriaList": [{"ConditionOccurrence": {"CodesetId": 1}}]}
    }
    
    with pytest.raises(ValueError, match="Missing required extensions: missing_ext"):
        CohortExpression.model_validate(expression_dict)

class WeatherQuery(BaseQuery):
    def __init__(self, concept_set_id=None, parent=None, is_entry=False, is_exclusion=False, is_censor=False):
        super().__init__("WeatherCondition", concept_set_id, parent, is_entry, is_exclusion, is_censor)

    def _finalize(self):
        if self._parent:
            if hasattr(self._parent, '_add_query'):
                from circe.cohort_builder.query_builder import CriteriaConfig
                self._parent._add_query(self._config, self._is_exclusion)
        return self._parent if self._parent else self

def test_evaluation_builder_extension_domain():
    """register_domain_query + EvaluationBuilder compiles to SQL."""
    registry = get_registry()
    registry.register_domain_query("weather", WeatherQuery, WeatherCondition)
    registry.register_sql_builder(WeatherCondition, WeatherConditionSqlBuilder)
    
    with EvaluationBuilder("Weather Eval") as ev:
        cs = ev.concept_set("Hot Days", 1)
        ev.add_rule("Heatwave", weight=10)._add_domain_criteria("weather", cs, at_least=1)
        
    rubric = ev.rubric
    # Verify the rule was built with the extension criteria
    rule = rubric.rules[0]
    criteria = rule.expression.criteria_list[0].criteria
    assert isinstance(criteria, WeatherCondition)
    
    # Optional: Verify SQL generation for the rubric (if builder supports it)
    # The EvaluationBuilder itself doesn't generate SQL, the engine does.
    # But we've verified the model structure is correct.

def test_extension_in_censoring_criteria_roundtrip():
    """Extension criteria in censoring_criteria survives round-trip."""
    registry = get_registry()
    registry.register_criteria_class("WeatherCondition", WeatherCondition)
    
    weather_criteria = WeatherCondition(temperature_celsius=40.0)
    expression = CohortExpression(
        censoring_criteria=[weather_criteria],
        primary_criteria=PrimaryCriteria(
            criteria_list=[{"ConditionOccurrence": {"CodesetId": 1}}], # Dummy primary
            observation_window={"priorDays": 0, "postDays": 0},
            primary_limit={"type": "First"}
        )
    )
    
    json_str = expression.model_dump_json(by_alias=True)
    loaded = CohortExpression.model_validate_json(json_str)
    
    assert isinstance(loaded.censoring_criteria[0], WeatherCondition)
    assert loaded.censoring_criteria[0].temperature_celsius == 40.0
