Extending circe_py
===================

This guide explains how to extend ``circe_py`` with custom criteria types.
This is useful when you have data in your CDM that isn't part of the standard
OMOP domains (e.g., weather data, genomic features, or specialized clinical
registries).

Architecture Overview
---------------------

The extension system consists of four main components:

1. **Criteria Class** – A Pydantic model that defines the fields available in your new criteria.
2. **SQL Builder** – A class that translates your criteria into template-based SQL strings.
3. **Ibis Execution Builder** – A function that builds an ``ibis`` table expression so the criteria can be executed against a live database through the ibis execution layer.
4. **Markdown Template** – A Jinja2 template that generates a human-readable description.

All four components are registered through the ``ExtensionRegistry``.  Registration
can be done either **programmatically** (calling methods on the registry) or
**declaratively** (using decorator helpers).  Both approaches are shown below.

.. important::

   Every component is registered dynamically at runtime—there must be no
   hard-coded imports of extension types inside the core library.  This means
   an extension only needs to be *imported* (or call its registration function)
   for its criteria to become available everywhere: SQL generation, ibis
   execution, JSON round-tripping, and markdown rendering.

Example: Weather Conditions
---------------------------

Imagine you want to create a cohort based on weather conditions (e.g.,
"Patients diagnosed with asthma during extreme cold").  The extension assumes a
custom ``weather_data`` table in your CDM with the following columns:

* ``weather_id`` (PK)
* ``person_id``
* ``weather_concept_id``
* ``temp_c``
* ``observation_date``
* ``visit_occurrence_id`` (nullable)


Step 1: Define the Criteria Class
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Your class must inherit from ``circe.cohortdefinition.criteria.Criteria``.  Use
Pydantic's ``Field`` and ``AliasChoices`` to maintain compatibility with both
Pythonic (``snake_case``) and Java-style (``PascalCase``) field names.

.. code-block:: python

   from typing import Optional, List
   from pydantic import Field, AliasChoices
   from circe.cohortdefinition.criteria import Criteria, CriteriaGroup
   from circe.cohortdefinition.core import NumericRange
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

       # --- helpers used by the ibis builder ---
       def get_primary_key_column(self) -> str:
           return "weather_id"

       def get_start_date_column(self) -> str:
           return "observation_date"

       def get_end_date_column(self) -> str:
           return "observation_date"

   # Resolve forward references (required for complex criteria types)
   WeatherCondition.model_rebuild()

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

Step 3: Implement the Ibis Execution Builder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ibis execution builder is a plain function that receives the criteria
instance and a ``BuildContext``, and returns an ``ibis.expr.types.Table`` that
conforms to the **standard pipeline output contract**:

.. list-table::
   :header-rows: 1

   * - Column
     - Type
   * - ``person_id``
     - ``int64``
   * - ``event_id``
     - ``int64``
   * - ``start_date``
     - ``timestamp``
   * - ``end_date``
     - ``timestamp``
   * - ``visit_occurrence_id``
     - ``int64`` (nullable)

Use the shared helpers in ``circe.execution.builders.common`` to apply
filters—these handle ``NumericRange``, ``DateRange``, ``TextFilter``, and
concept list comparisons consistently.

.. code-block:: python

   from circe.execution.build_context import BuildContext
   from circe.execution.builders.common import (
       apply_concept_filters,
       apply_numeric_range,
       standardize_output,
   )
   from circe.execution.builders.groups import apply_criteria_group

   def build_weather_condition(criteria: WeatherCondition, ctx: BuildContext):
       """Build an ibis event table from weather_data."""
       table = ctx.table("weather_data")

       # Apply concept filter on weather type
       if criteria.weather_concept_id:
           table = apply_concept_filters(
               table,
               "weather_concept_id",
               criteria.weather_concept_id,
           )

       # Apply temperature threshold
       if criteria.temperature_celsius is not None:
           table = table.filter(table.temp_c >= criteria.temperature_celsius)

       # Project to the standard output contract
       events = standardize_output(
           table,
           primary_key=criteria.get_primary_key_column(),
           start_column=criteria.get_start_date_column(),
           end_column=criteria.get_end_date_column(),
       )

       # Handle any correlated criteria (inclusion/exclusion sub-groups)
       return apply_criteria_group(events, criteria.correlated_criteria, ctx)

``standardize_output`` renames and casts columns to match the pipeline
contract.  ``apply_criteria_group`` recursively processes nested
``CriteriaGroup`` filters attached to your criteria, just as built-in criteria
do.

Step 4: Create a Markdown Template
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a file named ``weather_condition.j2``:

.. code-block:: jinja

   Weather condition: {{ criteria.weather_concept_id[0].concept_name if criteria.weather_concept_id else 'Any' }}
   {% if criteria.temperature_celsius %} with temperature >= {{ criteria.temperature_celsius }}°C{% endif %}.


Step 5: Register the Extension
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All four components must be registered before they can be used.  There are two
equivalent approaches.

Option A: Programmatic Registration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Call the registry methods directly.  This is useful when you want full control
over the registration order or need to register at a specific point in your
application startup.

.. code-block:: python

   from circe.extensions import get_registry
   from pathlib import Path

   def register_weather_extension():
       registry = get_registry()

       # 1. Criteria class  (JSON deserialization)
       registry.register_criteria_class("WeatherCondition", WeatherCondition)

       # 2. SQL builder     (template-based SQL generation)
       registry.register_sql_builder(WeatherCondition, WeatherConditionSqlBuilder)

       # 3. Ibis builder    (ibis execution layer)
       registry.register_ibis_builder("WeatherCondition", build_weather_condition)

       # 4. Markdown template
       tpl_path = Path(__file__).parent / "templates"
       registry.add_template_path(tpl_path)
       registry.register_markdown_template(WeatherCondition, "weather_condition.j2")

Option B: Decorator Registration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use the decorator helpers for a more declarative style.  Each decorator fires
at *import time*, so merely importing the module is enough to register
everything.

.. code-block:: python

   from circe.extensions import criteria_class, sql_builder, ibis_builder, markdown_template, template_path
   from pathlib import Path

   @criteria_class("WeatherCondition")
   class WeatherCondition(Criteria):
       # ... fields as shown in Step 1 ...
       pass

   @sql_builder(WeatherCondition)
   class WeatherConditionSqlBuilder(CriteriaSqlBuilder[WeatherCondition]):
       # ... methods as shown in Step 2 ...
       pass

   @ibis_builder("WeatherCondition")
   def build_weather_condition(criteria, ctx):
       # ... implementation as shown in Step 3 ...
       pass

   @markdown_template(WeatherCondition, "weather_condition.j2")
   class WeatherConditionRenderer:
       pass

   template_path(Path(__file__).parent / "templates")

The ``@ibis_builder`` decorator simultaneously registers the function in
**both** the ``ExtensionRegistry`` (for discoverability via
``get_ibis_builder``) and the low-level execution registry (so
``build_events`` resolves it without any hard-coded imports).

.. note::

   The ``@ibis_builder`` decorator accepts the criteria class **name** (a
   string), not the class itself.  This matches the key used by ``get_builder``
   at execution time.


Full End-to-End Usage
---------------------

Once registered, you can use your custom criteria just like any built-in type
for SQL generation, markdown rendering, JSON round-tripping, *and* ibis
execution.

.. code-block:: python

   from circe.cohortdefinition import CohortExpression, PrimaryCriteria
   from circe.vocabulary.concept import Concept

   # Ensure the extension is registered (import or call your registration function)
   register_weather_extension()

   # Define cohort
   weather_criteria = WeatherCondition(
       weather_concept_id=[Concept(concept_id=123, concept_name="Snowing")],
       temperature_celsius=-5.0,
   )

   cohort = CohortExpression(
       primary_criteria=PrimaryCriteria(criteria_list=[weather_criteria])
   )

   # --- SQL generation (template-based) ---
   from circe.cohortdefinition.cohort_expression_query_builder import (
       CohortExpressionQueryBuilder, BuildExpressionQueryOptions,
   )
   builder = CohortExpressionQueryBuilder()
   sql_options = BuildExpressionQueryOptions()
   sql_options.cdm_schema = "my_cdm"
   sql = builder.build_expression_query(cohort, sql_options)

   # --- Ibis execution ---
   import ibis
   from circe.execution import IbisExecutor, ExecutionOptions

   conn = ibis.duckdb.connect("my_cdm.ddb")
   options = ExecutionOptions(cdm_schema="main")
   with IbisExecutor(conn, options) as executor:
       result = executor.to_polars(cohort)
       print(result)


How Ibis Builder Discovery Works
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When ``build_events`` (the core entry point of the ibis pipeline) receives a
criteria instance, it resolves the builder in two steps:

1. **Module-level registry** – checked first; this is where the built-in OMOP
   domain builders (``ConditionOccurrence``, ``DrugExposure``, etc.) live.
2. **Extension registry fallback** – if the name is not found above, the global
   ``ExtensionRegistry`` is consulted via ``get_ibis_builder(name)``.

This two-tier lookup means that extensions never need to be hard-coded
anywhere in the core library.  As long as the builder has been registered
(either via ``@ibis_builder`` or ``register_ibis_builder``), it will be
discovered at execution time.

.. code-block:: text

   build_events(criteria, ctx)
     └─ get_builder(criteria)
          ├─ 1. _REGISTRY[criteria.__class__.__name__]     ← built-in domains
          └─ 2. ExtensionRegistry.get_ibis_builder(name)   ← extensions


Available Common Helpers
~~~~~~~~~~~~~~~~~~~~~~~~

The ``circe.execution.builders.common`` module provides shared filter functions
that extension ibis builders should use for consistency:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Function
     - Purpose
   * - ``standardize_output(table, *, primary_key, start_column, end_column)``
     - Project and rename columns to the standard pipeline output contract.
   * - ``apply_date_range(table, column, date_range)``
     - Filter rows by a ``DateRange`` (before/after/between).
   * - ``apply_numeric_range(table, column, numeric_range)``
     - Filter rows by a ``NumericRange`` (eq, gt, lt, between, etc.).
   * - ``apply_text_filter(table, column, text_filter)``
     - Filter rows by a ``TextFilter`` (contains, startswith, etc.).
   * - ``apply_concept_filters(table, column, concepts)``
     - Filter rows where a concept column matches a list of ``Concept`` objects.
   * - ``apply_codeset_filter(table, column, codeset_id, ctx)``
     - Filter rows by a pre-compiled concept set from the ``BuildContext``.
   * - ``apply_criteria_group(events, group, ctx)``
     - Recursively apply correlated ``CriteriaGroup`` inclusion/exclusion logic.

See the built-in builders (e.g., ``condition_occurrence.py``) or the waveform
extension builders for real-world usage examples.
