Extending circe_py
===================

This guide explains how to extend `circe_py` with custom criteria types. This is useful when you have data in your CDM that isn't part of the standard OMOP domains (e.g., weather data, genomic features, or specialized clinical registries).

Architecture Overview
---------------------

The extension system consists of three main components:

1. **Criteria Class**: A Pydantic model that defines the fields available in your new criteria.
2. **SQL Builder**: A class that translates your criteria into SQL.
3. **Markdown Template**: A Jinja2 template that generates a human-readable description.

Registration is handled by the `ExtensionRegistry`.

Example: Weather Conditions
---------------------------

Imagine you want to create a cohort based on weather conditions (e.g., "Patients diagnosed with asthma during extreme cold").

Step 1: Define the Criteria Class
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Your class must inherit from `circe.cohortdefinition.criteria.Criteria`. Use Pydantic's `Field` and `AliasChoices` to maintain compatibility with both Pythonic (`snake_case`) and Java-style (`PascalCase`) field names.

.. code-block:: python

   from typing import Optional, List
   from pydantic import Field, AliasChoices
   from circe.cohortdefinition.criteria import Criteria, CriteriaGroup
   from circe.vocabulary.concept import Concept

   class WeatherCondition(Criteria):
       """Criteria for weather data linked to persons."""
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

   # Resolve forward references (required for complex criteria types)
   WeatherCondition.model_rebuild()

Step 2: Implement the SQL Builder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The SQL builder must inherit from `circe.cohortdefinition.builders.base.CriteriaSqlBuilder`.

.. code-block:: python

   from typing import Set
   from circe.cohortdefinition.builders.base import CriteriaSqlBuilder
   from circe.cohortdefinition.builders.utils import CriteriaColumn, BuilderOptions

   class WeatherConditionSqlBuilder(CriteriaSqlBuilder[WeatherCondition]):
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

           query = query.replace("@cdm_database_schema", options.cdm_database_schema)
           query = query.replace("@whereClause", " AND ".join(where_clauses))
           return query

Step 3: Register the Extension
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use the extension registry to link your classes and templates.

.. code-block:: python

   from circe.extensions import get_registry
   from pathlib import Path

   def register_weather_extension():
       registry = get_registry()
       
       # 1. Register the Criteria Class
       registry.register_criteria_class("WeatherCondition", WeatherCondition)
       
       # 2. Register the SQL Builder
       registry.register_sql_builder(WeatherCondition, WeatherConditionSqlBuilder)
       
       # 3. Register Markdown Template
       # Ensure templates/weather_condition.j2 exists
       template_path = Path(__file__).parent / "templates"
       registry.add_template_path(template_path)
       registry.register_markdown_template(WeatherCondition, "weather_condition.j2")

Step 4: Create a Markdown Template
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a file named `weather_condition.j2`:

.. code-block:: jinja

   Weather condition: {{ criteria.weather_concept_id[0].concept_name if criteria.weather_concept_id else 'Any' }}
   {% if criteria.temperature_celsius %} with temperature >= {{ criteria.temperature_celsius }}°C{% endif %}.

Full End-to-End Usage
---------------------

Once registered, you can use your custom criteria just like any built-in type.

.. code-block:: python

   from circe.cohortdefinition import CohortExpression, PrimaryCriteria
   from circe.vocabulary.concept import Concept

   # Setup
   register_weather_extension()

   # Define cohort
   weather_criteria = WeatherCondition(
       weather_concept_id=[Concept(concept_id=123, concept_name="Snowing")],
       temperature_celsius=-5.0
   )
   
   cohort = CohortExpression(
       primary_criteria=PrimaryCriteria(criteria_list=[weather_criteria])
   )

   # generate SQL or Markdown as usual
   # ...
