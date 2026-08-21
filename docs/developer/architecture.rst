Architecture
============

CIRCE Python follows the architecture of the Java CIRCE-BE implementation.

Package Structure
-----------------

* **cohortdefinition/** - Core cohort classes and SQL builders
* **vocabulary/** - Concept and concept set management
* **check/** - Validation framework
* **helper/** - Utility functions
* **api.py** - High-level API
* **cli.py** - Command-line interface
* **execution/** - Experimental Ibis-based cohort execution engine

SQL Generation
--------------

SQL generation uses a template-based approach with domain-specific builders.

Validation Framework
--------------------

The validation framework uses a checker pattern with pluggable validators.

Execution Engine
----------------

The ``circe.execution`` package is an experimental, table-first Ibis executor
for ``CohortExpression`` models. It runs in parallel with the existing SQL
builder.

Public API
~~~~~~~~~~

The main execution entrypoints are:

* ``build_cohort(...)`` - build a lazy Ibis relation in canonical execution shape
* ``write_cohort(...)`` - project to OHDSI cohort-table shape and write rows for one ``cohort_id``

The write contract is cohort-scoped:

* ``if_exists="fail"`` errors only if rows already exist for that ``cohort_id``
* ``if_exists="replace"`` replaces only that ``cohort_id`` and preserves other cohorts in the same table

Layered Design
~~~~~~~~~~~~~~

The subsystem is intentionally split into five layers.

1. ``normalize/``

   * converts public cohort-definition models into frozen internal dataclasses
   * removes aliasing and optional-shape noise from downstream code
   * rejects explicitly unsupported semantics early

2. ``lower/``

   * turns normalized criteria into backend-agnostic execution plans
   * encodes reusable event and predicate planning logic
   * keeps domain-specific lowering separate from backend-specific compilation

3. ``ibis/``

   * compiles lowered plans into Ibis relations
   * standardizes domain tables into the canonical event schema
   * resolves concept sets and person filters
   * provides backend operations used by the public write path

4. ``engine/``

   * evaluates cohort semantics over canonical event relations
   * handles primary events, additional criteria, inclusion rules, censoring,
     limits, collapse, and end strategy

5. API materialization layer

   * connects public API calls to normalization, compilation, and engine execution
   * projects final relations into OHDSI cohort-table shape
   * handles backend table existence checks and cohort-scoped writes

Canonical Event Schema
~~~~~~~~~~~~~~~~~~~~~~

Compiled domain event relations are standardized before engine orchestration.
The canonical columns are defined in ``circe/execution/plan/schema.py``.
Important columns include:

* ``person_id``
* ``event_id``
* ``start_date``
* ``end_date``
* ``domain``
* ``concept_id``
* ``source_concept_id``
* ``visit_occurrence_id``
* ``criterion_index``
* ``criterion_type``
* ``source_table``

This standardization is one of the main design differences from the legacy
builder-based path. The engine operates on one event shape instead of many
domain-specific SQL-builder shapes.

Data Flow
~~~~~~~~~

The end-to-end flow is:

1. ``CohortExpression``
2. normalize to frozen internal dataclasses
3. lower criteria into event and predicate plans
4. compile plans into canonical Ibis relations
5. run cohort semantics in ``engine/``
6. optionally materialize to OHDSI cohort-table rows

Codeset Resolution
~~~~~~~~~~~~~~~~~~

Codeset expansion is handled by ``CachedConceptSetResolver``.
Resolution semantics are:

* direct inclusion
* descendant expansion through ``concept_ancestor``
* mapped concept expansion through ``concept_relationship``
* exclusion precedence after expansion

The cache is scoped to one execution context run.

Migration Notes
~~~~~~~~~~~~~~~

If you used the legacy execution prototype:

* use ``build_cohort(...)`` to get the lazy relation
* use backend operations on that relation for inspection and collection
* use ``write_cohort(...)`` for cohort-table writes

Current Execution Limitations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The executor should fail explicitly for unsupported execution semantics rather
than silently degrading behavior.

Current explicit limitation:

* ``custom_era`` end strategy is not implemented in this base execution branch
