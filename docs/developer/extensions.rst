Extending circe_py
===================

This guide explains how to extend ``circe_py`` with custom criteria types.
This is useful when you have data in your CDM that isn't part of the standard
OMOP domains (e.g., weather data, genomic features, or specialized clinical
registries).

Architecture Overview
---------------------

An extension is made of five components, all registered through the global
``ExtensionRegistry``:

1. **Criteria class** – A Pydantic model defining the fields available in your
   new criteria.
2. **SQL Builder** – A class that translates the criteria into template-based
   SQL strings for the SQL-generation path.
3. **Normalizer** – A function that converts the criteria into a
   ``NormalizedCriterion`` describing the source table and column contract.
4. **Ibis lowerer** – A function that turns the normalized criterion into an
   ``EventPlan`` for the ibis execution engine.
5. **Markdown template** – A Jinja2 template that renders a human-readable
   description.

Registration can be done **programmatically** (methods on the registry) or
**declaratively** (decorator helpers).  Both approaches are shown below.

.. important::

   Components are registered dynamically at runtime — there must be no
   hard-coded imports of extension types inside the core library.  Importing
   the extension package (or calling its registration function) makes its
   criteria available for SQL generation, ibis execution, JSON
   deserialization, and markdown rendering.

Example: Weather Conditions
---------------------------

Imagine you want to create a cohort based on weather conditions (e.g.,
"Patients with asthma during extreme cold").  The extension assumes a custom
``weather_data`` table in your CDM with these columns:

* ``weather_id`` (PK)
* ``person_id``
* ``weather_concept_id``
* ``temp_c``
* ``observation_date``
* ``visit_occurrence_id`` (nullable)

Step 1: Define the Criteria Class
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Your class must inherit from ``circe.cohortdefinition.criteria.Criteria``.  Use
Pydantic's ``Field`` and ``AliasChoices`` to support both Pythonic
(``snake_case``) and Java-style (``PascalCase``) field names.

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
           serialization_alias="WeatherConceptId",
       )
       temperature_celsius: Optional[float] = Field(
           default=None,
           validation_alias=AliasChoices("TemperatureCelsius", "temperatureCelsius"),
           serialization_alias="TemperatureCelsius",
       )

   # Criteria declares forward references to CriteriaGroup; resolve them.
   WeatherCondition.model_rebuild(_types_namespace={"CriteriaGroup": CriteriaGroup})

Step 2: Implement the SQL Builder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The SQL builder must inherit from
``circe.cohortdefinition.builders.base.CriteriaSqlBuilder``.

.. code-block:: python

   from typing import Set
   from circe.cohortdefinition.builders.base import CriteriaSqlBuilder
   from circe.cohortdefinition.builders.utils import CriteriaColumn, BuilderOptions

   class WeatherConditionSqlBuilder(CriteriaSqlBuilder[WeatherCondition]):
       def get_query_template(self) -> str:
           return """
   SELECT C.person_id, C.weather_id as event_id,
          C.observation_date as start_date, C.observation_date as end_date,
          NULL as visit_occurrence_id, C.observation_date as sort_date
   FROM @cdm_database_schema.weather_data C
   WHERE @whereClause
   """

       def get_default_columns(self) -> Set[CriteriaColumn]:
           return {CriteriaColumn.START_DATE, CriteriaColumn.END_DATE}

       def get_table_column_for_criteria_column(self, column: CriteriaColumn) -> str:
           if column in (CriteriaColumn.START_DATE, CriteriaColumn.END_DATE):
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

Step 3: Implement the Normalizer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The normalizer describes how the criteria map onto the CDM.  It returns a
``NormalizedCriterion`` built with the public
``build_normalized_criterion()`` helper, which also derives the standard
person-level filters (age, gender, race, ethnicity).

.. code-block:: python

   from circe.extensions import normalizer
   from circe.execution.normalize import build_normalized_criterion

   @normalizer(WeatherCondition)
   def normalize_weather_condition(criteria: WeatherCondition):
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

Notes:

* If the criteria uses a concept set instead of a concept list, set
  ``codeset_id=criteria.codeset_id`` and give the corresponding
  ``concept_column``.  The execution engine resolves the id through the
  cohort's codeset table.
* Use ``normalize_date_range()`` / ``normalize_numeric_range()`` from
  ``circe.execution.normalize`` for temporal or numeric fields.
* ``first=True`` keeps one event per person, ordered by start date and event id.

Step 4: Implement the Ibis Lowerer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The lowerer converts the ``NormalizedCriterion`` into an ``EventPlan``.  The
lowerer has access to the raw criteria through ``criterion.raw_criteria``.

.. code-block:: python

   from circe.extensions import lowerer
   from circe.execution.lower.common import (
       append_concept_filters,
       build_standard_domain_plan,
       lower_common_steps,
   )
   from circe.execution.plan.events import FilterByNumericRange
   from circe.execution.plan.predicates import NumericRangePredicate

   @lowerer(WeatherCondition)
   def lower_weather_condition(criterion, *, criterion_index: int):
       raw = criterion.raw_criteria
       if not isinstance(raw, WeatherCondition):
           raise TypeError("lower_weather_condition requires WeatherCondition")

       # Shared handling for codesets, person filters and `first`.
       steps = lower_common_steps(criterion)

       # Concept list on the weather concept column.
       append_concept_filters(
           steps,
           column="weather_concept_id",
           concepts=raw.weather_concept_id,
       )

       # Domain-specific filter on the raw temperature column.
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

       # Adds the standard event-shape projection and correlated criteria.
       return build_standard_domain_plan(
           criterion,
           criterion_index=criterion_index,
           steps=steps,
       )

The normalizer's ``source_table`` / column names determine which table the
engine reads.  The lowerer is responsible for every filter the criteria
supports, using the plan steps in ``circe.execution.plan.events``.

Step 5: Create a Markdown Template
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``templates/weather_condition.j2``:

.. code-block:: jinja

   Weather condition: {{ criteria.weather_concept_id[0].concept_name if criteria.weather_concept_id else 'Any' }}
   {% if criteria.temperature_celsius %} with temperature >= {{ criteria.temperature_celsius }}°C{% endif %}.

Step 6: Register the Extension
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All five components must be registered.  There are two equivalent approaches.

Option A: Programmatic Registration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pathlib import Path
   from circe.extensions import get_registry

   def register_weather_extension() -> None:
       registry = get_registry()

       registry.register_criteria_class("WeatherCondition", WeatherCondition)
       registry.register_sql_builder(WeatherCondition, WeatherConditionSqlBuilder)
       registry.register_normalizer(WeatherCondition, normalize_weather_condition)
       registry.register_lowerer(WeatherCondition, lower_weather_condition)

       templates = Path(__file__).parent / "templates"
       registry.add_template_path(templates)
       registry.register_markdown_template(WeatherCondition, "weather_condition.j2")

Option B: Decorator Registration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Decorators fire at import time, so importing the extension package is enough.

.. code-block:: python

   from pathlib import Path
   from circe.extensions import (
       criteria_class,
       lowerer,
       markdown_template,
       normalizer,
       sql_builder,
       template_path,
   )

   @criteria_class("WeatherCondition")
   class WeatherCondition(Criteria):
       ...

   @sql_builder(WeatherCondition)
   class WeatherConditionSqlBuilder(CriteriaSqlBuilder[WeatherCondition]):
       ...

   @normalizer(WeatherCondition)
   def normalize_weather_condition(criteria: WeatherCondition):
       ...

   @lowerer(WeatherCondition)
   def lower_weather_condition(criterion, *, criterion_index: int):
       ...

   @markdown_template(WeatherCondition, "weather_condition.j2")
   class WeatherConditionRenderer:
       pass

   template_path(Path(__file__).parent / "templates")

``@criteria_class`` takes the JSON key (a string); the other decorators take
the criteria **class** itself.

Full End-to-End Usage
---------------------

Once registered, a custom criterion works in both the SQL builder and the
ibis execution engine, and round-trips through JSON.

.. code-block:: python

   from circe.cohortdefinition import CohortExpression, PrimaryCriteria
   from circe.vocabulary.concept import Concept

   weather_criteria = WeatherCondition(
       weather_concept_id=[Concept(concept_id=123, concept_name="Snowing")],
       temperature_celsius=-5.0,
   )
   cohort = CohortExpression(
       primary_criteria=PrimaryCriteria(criteria_list=[weather_criteria])
   )

   # SQL generation
   from circe.cohortdefinition.cohort_expression_query_builder import (
       BuildExpressionQueryOptions,
       CohortExpressionQueryBuilder,
   )

   builder = CohortExpressionQueryBuilder()
   sql_options = BuildExpressionQueryOptions()
   sql_options.cdm_schema = "my_cdm"
   sql = builder.build_expression_query(cohort, sql_options)

   # Ibis execution
   import ibis
   from circe.execution import build_cohort, write_cohort

   conn = ibis.duckdb.connect("my_cdm.ddb")
   events = build_cohort(cohort, backend=conn, cdm_schema="main")
   write_cohort(
       cohort,
       backend=conn,
       cdm_schema="main",
       cohort_table="cohort",
       cohort_id=1,
   )

   # JSON round-trip uses the registered criteria class
   loaded = CohortExpression.model_validate_json(cohort.model_dump_json(by_alias=True))
   assert isinstance(loaded.primary_criteria.criteria_list[0], WeatherCondition)

How Ibis Discovery Works
~~~~~~~~~~~~~~~~~~~~~~~~

The core engine never imports extension classes.  It dispatches through the
registry at two points:

.. code-block:: text

   normalize_cohort(expression)
     └─ normalize_criterion(criteria)
          └─ ExtensionRegistry.get_normalizer(type(criteria))

   lower_criterion(normalized)
     └─ ExtensionRegistry.get_lowerer(type(normalized.raw_criteria))

A normalizer must return a ``NormalizedCriterion`` and a lowerer must return an
``EventPlan``.  Everything after that — compiling the plan to ibis, applying
correlated criteria, observation windows, limits, and so on — is shared with
the built-in criteria.

Available Common Helpers
~~~~~~~~~~~~~~~~~~~~~~~~

Normalization
^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Helper
     - Purpose
   * - ``build_normalized_criterion(**kwargs)``
     - Build the ``NormalizedCriterion`` and derive person filters.
   * - ``normalize_date_range(value)``
     - Normalize a Circe ``DateRange``.
   * - ``normalize_numeric_range(value)``
     - Normalize a Circe ``NumericRange``.

All are importable from ``circe.execution.normalize``.

Lowering
^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Helper
     - Purpose
   * - ``lower_common_steps(criterion)``
     - Codeset, person-filter and ``first`` steps shared by all criteria.
   * - ``append_concept_filters(steps, column=..., concepts=..., codeset_selection=...)``
     - Filter by a concept list or concept-set selection.
   * - ``append_numeric_filter(steps, column=..., value=NumericRange)``
     - Filter by a ``NumericRange``.
   * - ``append_text_filter(steps, column=..., value=TextFilter)``
     - Filter by a ``TextFilter``.
   * - ``append_visit_filters(...)``
     - Visit-occurrence/detail context filters.
   * - ``build_standard_domain_plan(criterion, criterion_index=..., steps=...)``
     - Finish the plan with the standard event-shape projection.

All are importable from ``circe.execution.lower.common``.  For filters that do
not have a helper, append the corresponding step from
``circe.execution.plan.events`` directly.

Reference Implementation
------------------------

The waveform extension (``circe/extensions/waveform``) is a complete example:
four criteria classes, SQL builders, normalizers, lowerers, markdown templates,
and their tests.  Start there when adding a new domain.

Testing an Extension
--------------------

Import your extension package in the test, build a cohort with the custom
criteria against a small DuckDB CDM, and assert the returned rows.  The
extension test module (``tests/test_extension_system.py``) registers a custom
``WeatherCondition`` criteria, lowerer and normalizer, then executes it through
``build_cohort()``.
