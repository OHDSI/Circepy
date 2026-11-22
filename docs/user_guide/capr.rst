Capr-Style Cohort Definitions
===============================

``circe.capr`` is a Python port of the public API of OHDSI's R
`Capr <https://ohdsi.github.io/Capr/>`_ package (v3.0.0).

Capr builds OHDSI cohort definitions programmatically and serializes them to
Circe JSON. Neither Capr nor this module needs a database connection: building
and serializing are pure in-memory work. This port produces Circepy's existing
:class:`~circe.cohortdefinition.cohort.CohortExpression`, so a cohort built here
feeds straight into the SQL builders and execution pipeline described in
:doc:`cohort_definitions` and :doc:`sql_generation`.

Quick Start
-----------

.. code-block:: python

   from circe import capr

   t2dm = capr.cs(capr.descendants(201826), name="T2DM")

   cd = capr.cohort(
       entry=capr.entry(
           capr.condition_occurrence(t2dm, capr.first_occurrence()),
           observation_window=capr.continuous_observation(prior_days=365),
           primary_criteria_limit="First",
       ),
       attrition=capr.attrition(
           **{
               "no prior insulin": capr.with_all(
                   capr.exactly(
                       0,
                       capr.drug_exposure(insulin),
                       capr.during_interval(capr.event_starts(-capr.INF, -1)),
                   )
               )
           },
           expression_limit="First",
       ),
       exit=capr.exit(capr.observation_exit()),
       era=capr.era(era_days=0),
   )

   expression = capr.to_cohort_expression(cd)  # circe.cohortdefinition.CohortExpression
   payload = capr.to_cohort_json(cd)  # Circe JSON string

Building Blocks
---------------

A cohort is assembled from four components, mirroring Circe's structure:

.. code-block:: text

   cohort(
     entry      = entry(...)       # index events + observation window
     attrition  = attrition(...)   # named inclusion/exclusion rule groups
     exit       = exit(...)        # end strategy + censoring
     era        = era(...)         # era-collapse gap + study window
   )

Inside those, queries are filtered by attributes, wrapped into criteria with a
count and a time window, and combined into groups.

What Is Covered
---------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Area
     - Functions
   * - Concept sets
     - ``cs``, ``descendants``, ``exclude``, ``mapped``
   * - Operators
     - ``lt``, ``lte``, ``gt``, ``gte``, ``eq``, ``bt``, ``nbt``
   * - Windows
     - ``event_starts``, ``event_ends``, ``during_interval``,
       ``continuous_observation``
   * - Criteria
     - ``exactly``, ``at_least``, ``at_most``
   * - Groups
     - ``with_all``, ``with_any``, ``with_at_least``, ``with_at_most``
   * - Correlated criteria
     - ``nested_with_all``, ``nested_with_any``, ``nested_with_at_least``,
       ``nested_with_at_most``
   * - Attributes
     - ``age``, ``male``, ``female``, ``gender_concepts``,
       ``first_occurrence``, ``start_date``, ``end_date``,
       ``date_adjustment``, ``value_as_number``, ``value_as_string``,
       ``measurement_unit``, ``days_of_supply``, ``drug_refills``,
       ``drug_quantity``, ``range_low``, ``range_high``, ``condition_type``,
       ``condition_type_exclude``, ``condition_source_concept``,
       ``visit_type``, ``provider_specialty_concepts``
   * - Domains
     - ``condition_occurrence``, ``condition_era``, ``drug_exposure``,
       ``drug_era``, ``dose_era``, ``measurement``, ``observation``,
       ``procedure``, ``visit``, ``visit_detail``, ``device``, ``specimen``,
       ``death``, ``observation_period``, ``payer_plan_period``
   * - Exit / era
     - ``observation_exit``, ``fixed_exit``, ``drug_exit``,
       ``censoring_events``, ``era``
   * - Assembly
     - ``entry``, ``attrition``, ``exit``, ``cohort``,
       ``to_cohort_expression``, ``to_cohort_json``, ``validate``
   * - Reverse
     - ``json_to_capr``, ``json_to_capr_file``

Concept Set Identity
--------------------

Concept sets carry a content-derived id: the md5 of an R-serialized payload
built from each concept's flags, exactly as Capr derives it. Item order and the
set's name are deliberately ignored, so two sets with identical contents have
the same identity (matching Capr 3.0, where they collapse to one on compile).

The id is internal. It is renumbered to a dense ``0..n-1`` ``CodesetId`` when
the definition is compiled, because CIRCE requires integer ids.

Deviations from R's Capr
------------------------

Each is a deliberate choice, covered by a test.

- **``cohort()`` takes an explicit ``CohortEntry``.** Capr's ``cohort()``
  resolves a *global* ``entry`` function, so a variable named ``entry`` in scope
  breaks it. A bare query is still accepted and wrapped for convenience.
- **``attrition()`` rejects a bare criterion.** Capr accepts one and silently
  writes an inclusion rule that Atlas cannot render; this raises
  :class:`~circe.capr.CaprError`.
- **``validate()`` exists.** It surfaces silent traps Capr allows through, such
  as ``primary_criteria_limit="All"`` combined with ``expression_limit="First"``,
  which quietly collapses the cohort to one event per person.
- **Negative concept ids are rejected.** Capr's ``cs()`` rejects them too (its
  validity check requires non-negative ids); use ``exclude(id)``.
- **Python naming.** ``snake_case`` throughout; unbounded windows are
  ``-capr.INF`` / ``capr.INF``; ``count_column`` replaces ``countColumn``.

Parity with R
-------------

``tests/capr/fixtures/`` holds the JSON that R's Capr 3.0.0 produces for 12
reference cohorts; ``tests/capr/test_parity.py`` compiles the same cohorts here
and compares them semantically. The comparison normalises a handful of
differences that are not meaningful, or that come from pre-existing Circepy
behaviour:

- ``cdmVersionRange`` is dropped by the shared models on round-trip.
- The shared models always serialize ``False`` defaults (``First``,
  ``ConditionTypeExclude``, ``RestrictVisit``, ``IsDistinct``, ...) that Capr
  omits.
- Blank concept metadata is omitted here but written as ``""`` by Capr.
- Capr writes inclusion rules with lowercase ``name``/``expression``; CIRCE
  uses PascalCase.

Known pre-existing issue surfaced by this work: domain criteria in
``circe/cohortdefinition/criteria.py`` serialize gender as ``gender`` where
CIRCE-BE uses ``Gender``. That is being tracked separately and is normalised in
the parity test.

Decompiling Circe JSON
----------------------

``json_to_capr()`` is the inverse of building: it turns a cohort definition
exported from Atlas into ``circe.capr`` Python source, so an existing definition
can be brought under version control and re-run without an R session.

.. code-block:: python

   from circe import capr

   source = capr.json_to_capr("cohorts/t2dm.json")
   print(source)

   # Write it out, then import and run it like any other module.
   capr.json_to_capr_file("cohorts/t2dm.json", "cohorts/t2dm.py")

The generated file starts with ``from circe import capr`` and assigns the
result to ``cohort_definition``, so it is self-contained and executable:

.. code-block:: python

   from circe import capr

   # Generated by json_to_capr() from t2dm.json

   # --- concept sets ---
   csT2dm0 = capr.cs(capr.descendants(201826), name='T2DM')

   # --- cohort ---
   cohort_definition = capr.cohort(
     entry=capr.entry(
       capr.condition_occurrence(csT2dm0),
       observation_window=capr.continuous_observation(0, 0),
       primary_criteria_limit='First',
       qualified_limit='First',
     ),
     exit=capr.exit(
       end_strategy=capr.observation_exit(),
     ),
     era=capr.era(era_days=0),
   )

Options
~~~~~~~

``mode="strict"`` (the default) raises
:class:`~circe.capr.JsonToCaprError` on anything that cannot be represented, so
a definition is never silently degraded. ``mode="skip"`` omits the unsupported
part, records the reason, and emits a ``# SKIPPED:`` header at the top of the
file. Pass ``return_skipped=True`` to get a
:class:`~circe.capr.DecompiledCohort` carrying the source plus the ``skipped``
and ``empty_group_warnings`` lists.

Round-tripping is verified: every fixture in ``tests/capr/fixtures`` is
decompiled, executed, and re-serialized, and the result must match the original
definition (``tests/capr/test_json_to_capr.py``).

Not Yet Ported
--------------

- Concept vocabulary search against a CDM connection (``searchConcepts``,
  ``rankedSearchConcepts``, ``getConceptInfo``, ...).
- Console ``show``/``summary`` renderers.
- ``insertCaprCode()``, which is RStudio-specific.

See Also
--------

- :doc:`cohort_definitions` for the underlying ``CohortExpression`` model.
- :doc:`concepts` for working with concept sets directly.
- :doc:`validation` for the check framework.
