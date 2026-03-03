Extending circe_py
===================

This guide explains how to extend ``circe_py`` with custom criteria types using the ``@register_criteria`` decorator. Once decorated, your criteria class automatically gets:

1. **Registry registration** — discoverable by SQL builders, markdown renderers, and serialization
2. **Auto-generated fluent query class** — ``BaseQuery`` subclass created via introspection
3. **Dynamic builder methods** — ``CohortBuilder``, ``EvaluationBuilder``, and ``CriteriaGroupBuilder`` gain ``with_``, ``require_``, ``exclude_``, and domain methods automatically

Architecture Overview
---------------------

.. code-block:: text

    @register_criteria("WeatherCondition", extension="weather")
    class WeatherCondition(Criteria):
        ...

    ↓ Automatically:
    1. registry.register_criteria_class("WeatherCondition", cls)
    2. WeatherConditionQuery = _make_query_class("WeatherCondition", cls)
    3. registry.register_domain_query("WeatherCondition", WeatherConditionQuery)

    ↓ Enables:
    cohort.with_weather_condition(cs_id)       # CohortBuilder entry
    cohort.require_weather_condition(cs_id)     # CohortWithEntry inclusion
    rule.weather_condition(cs_id)               # EvaluationBuilder rule

The extension system has four components:

1. **Criteria Class** — Pydantic model decorated with ``@register_criteria``
2. **SQL Builder** — translates criteria to SQL (registered manually via ``@register_sql_builder``)
3. **Ibis Builder** (Optional) - translates criteria to Ibis relations (registered via ``@register_ibis_builder``)
4. **Markdown Template** — human-readable output (registered manually)

Example: Weather Conditions
---------------------------

Step 1: Define the Criteria Class
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Decorate your ``Criteria`` subclass with ``@register_criteria``. The decorator handles all registry plumbing.

.. code-block:: python

   from typing import Optional, List
   from pydantic import Field, AliasChoices
   from circe.cohortdefinition.criteria import Criteria
   from circe.vocabulary.concept import Concept
   from circe.extensions import register_criteria

   @register_criteria(extension="weather")
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

   WeatherCondition.model_rebuild()

After this single decorator, ``WeatherCondition`` is fully registered. A ``WeatherConditionQuery`` class is auto-generated and all builder classes gain dynamic methods.

Step 2: Implement the SQL Builder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Decorate your builder with ``@register_sql_builder``:

.. code-block:: python

   from circe.cohortdefinition.builders.base import CriteriaSqlBuilder
   from circe.cohortdefinition.builders.utils import CriteriaColumn, BuilderOptions
   from circe.extensions import register_sql_builder

   @register_sql_builder(WeatherCondition)
   class WeatherConditionSqlBuilder(CriteriaSqlBuilder[WeatherCondition]):
       def get_query_template(self) -> str:
           return """
   SELECT C.person_id, C.weather_id as event_id, C.observation_date as start_date,
          C.observation_date as end_date, NULL as visit_occurrence_id, C.observation_date as sort_date
   FROM @cdm_database_schema.weather_data C
   WHERE @whereClause
   """

       def get_default_columns(self):
           return {CriteriaColumn.START_DATE, CriteriaColumn.END_DATE}

       def get_table_column_for_criteria_column(self, column):
           return "C.observation_date"

       def get_criteria_sql_with_options(self, criteria, options):
           query = self.get_query_template()
           where_clauses = ["1=1"]
           if criteria.weather_concept_id:
               ids = [str(c.concept_id) for c in criteria.weather_concept_id if c.concept_id]
               if ids:
                   where_clauses.append(f"C.weather_concept_id IN ({','.join(ids)})")
           if criteria.temperature_celsius is not None:
               where_clauses.append(f"C.temp_c >= {criteria.temperature_celsius}")
           return query.replace("@cdm_database_schema", options.cdm_database_schema)\
                       .replace("@whereClause", " AND ".join(where_clauses))

Step 3: Implement the Ibis Builder (Optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your extension supports Ibis execution, decorate your Ibis builder function with ``@register_ibis_builder``:

.. code-block:: python

   from circe.extensions import register_ibis_builder
   from circe.execution.build_context import BuildContext
   import ibis.expr.types as ir

   @register_ibis_builder("WeatherCondition")
   def build_weather_condition(criteria: WeatherCondition, ctx: BuildContext) -> ir.Table:
       # Access the initialized database connection via ctx.conn or the mapped tables via ctx.table()
       table = ctx.table("weather_data")
       
       # Use Ibis expressions to filter the table based on the criteria
       if criteria.weather_concept_id:
           ids = [c.concept_id for c in criteria.weather_concept_id if c.concept_id]
           table = table.filter(table.weather_concept_id.isin(ids))
           
       if criteria.temperature_celsius is not None:
           table = table.filter(table.temp_c >= criteria.temperature_celsius)
           
       # Return the finalized Ibis table relation
       return table

Step 4: Register the Extension Name
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With decorators, only the named extension needs manual registration:

.. code-block:: python

   from circe.extensions import get_registry

   def register():
       get_registry().register_named_extension("weather", version="1.0.0")

Fluent Builder Support
----------------------

Once ``@register_criteria`` is applied, all builder classes gain dynamic methods via ``__getattr__``:

**CohortBuilder** (entry events):

.. code-block:: python

   cohort = CohortBuilder("Weather Cohort")
   cohort.with_weather_condition(concept_set_id)

**CohortWithEntry / CohortWithCriteria** (inclusion/exclusion):

.. code-block:: python

   cohort.with_condition(0).require_weather_condition(1, anytime_before=True)
   cohort.with_condition(0).exclude_weather_condition(1, within_days_before=30)

**EvaluationBuilder** (rubric rules):

.. code-block:: python

   ev = EvaluationBuilder("Weather Rubric")
   ev.add_rule("Cold Weather", weight=5).weather_condition(cs_id).at_least(1)

**CriteriaGroupBuilder** (nested groups):

.. code-block:: python

   cohort.with_condition(0).any_of().weather_condition(1).end_group()

The method name mapping is:
  - ``with_<snake_case>`` → entry event for ``PascalCase`` domain
  - ``require_<snake_case>`` → inclusion criterion
  - ``exclude_<snake_case>`` → exclusion criterion
  - ``censor_on_<snake_case>`` → censoring criterion
  - ``<snake_case>`` → alias for ``require_`` (on ``CriteriaGroupBuilder`` and ``RuleBuilder``)

Entry Points
------------

For packages that depend on ``circe_py``, configure automatic discovery via ``pyproject.toml``:

.. code-block:: toml

   [project.entry-points."circe_py.extensions"]
   weather = "weather_extension:register"

This allows ``circe_py`` to auto-load your extension without explicit import.

Full End-to-End Usage
---------------------

.. code-block:: python

   # Import triggers @register_criteria decorators
   import weather_extension
   weather_extension.register()

   from circe.cohort_builder.builder import CohortBuilder

   cohort = CohortBuilder("Cold Weather Asthma")
   cohort.with_concept_sets(asthma_cs, cold_weather_cs)
   expr = (
       cohort
       .with_condition(0)                              # Entry: asthma diagnosis
       .require_weather_condition(1, within_days=7)     # Within 7 days of cold weather
       .build()
   )
