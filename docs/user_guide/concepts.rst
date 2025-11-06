Core Concepts
=============

Understanding the key concepts in CIRCE Python is essential for creating effective cohort definitions.

OMOP Common Data Model
-----------------------

The OMOP CDM (Observational Medical Outcomes Partnership Common Data Model) is a standardized data model for observational health data. CIRCE Python generates SQL queries that run against OMOP CDM databases.

Key OMOP tables used by CIRCE:

* ``PERSON`` - Patient demographics
* ``OBSERVATION_PERIOD`` - Time periods when patients are observed
* ``CONDITION_OCCURRENCE`` - Diagnoses and conditions
* ``DRUG_EXPOSURE`` - Medication exposures
* ``PROCEDURE_OCCURRENCE`` - Medical procedures
* ``MEASUREMENT`` - Lab results and measurements
* ``OBSERVATION`` - Clinical observations
* ``VISIT_OCCURRENCE`` - Healthcare visits

Cohort Definitions
------------------

A **cohort** is a set of persons who satisfy one or more inclusion criteria for a duration of time.

Cohort Expression
~~~~~~~~~~~~~~~~~

A cohort expression defines the logic for identifying cohort members. It consists of:

* **Primary Criteria** - Initial events that qualify persons for the cohort
* **Additional Criteria** - Optional filters applied to primary events
* **Inclusion Rules** - Additional requirements for cohort membership
* **Cohort Exit** - When persons exit the cohort
* **Censoring** - Events that end cohort membership

Primary Criteria
~~~~~~~~~~~~~~~~

Primary criteria identify the initial qualifying events (index events). Key components:

* **Criteria List** - One or more criteria (conditions, drugs, procedures, etc.)
* **Observation Window** - Required observation period around the event
* **Primary Limit** - Which events to include (First, Last, All)

Example primary criteria:

.. code-block:: python

   PrimaryCriteria(
       criteria_list=[
           ConditionOccurrence(codeset_id=1, first=True)
       ],
       observation_window=ObservationFilter(prior_days=365, post_days=0),
       primary_limit=ResultLimit(type="First")
   )

Concept Sets
------------

Concept sets define groups of OMOP concepts representing clinical entities.

Components:

* **Concept** - A single OMOP standardized concept
* **Include Descendants** - Whether to include child concepts
* **Is Excluded** - Exclusion flag for negative concept selection

Example concept set:

.. code-block:: python

   ConceptSet(
       id=1,
       name="Type 2 Diabetes",
       expression=ConceptSetExpression(
           items=[
               ConceptSetItem(
                   concept=Concept(concept_id=201826),
                   include_descendants=True,
                   is_excluded=False
               )
           ]
       )
   )

Criteria Types
--------------

CIRCE supports multiple criteria types corresponding to OMOP domains:

Clinical Events
~~~~~~~~~~~~~~~

* **ConditionOccurrence** - Diagnoses and conditions
* **DrugExposure** - Medication exposures
* **ProcedureOccurrence** - Medical procedures
* **Measurement** - Lab results and vital signs
* **Observation** - Clinical observations
* **DeviceExposure** - Medical device usage
* **Specimen** - Biospecimen collection

Eras
~~~~

* **ConditionEra** - Continuous condition periods
* **DrugEra** - Continuous drug exposure periods
* **DoseEra** - Continuous dose exposure periods

Administrative
~~~~~~~~~~~~~~

* **VisitOccurrence** - Healthcare visits
* **VisitDetail** - Detailed visit information
* **ObservationPeriod** - Observation time periods
* **PayerPlanPeriod** - Insurance coverage periods

Special
~~~~~~~

* **Death** - Death events
* **LocationRegion** - Geographic criteria

Time Windows
------------

Time windows define temporal relationships between events.

Window Components
~~~~~~~~~~~~~~~~~

* **Start Bound** - Window start (days before/after index)
* **End Bound** - Window end (days before/after index)
* **Use Index End** - Reference index event end date
* **Use Event End** - Reference event end date

Example: 30 days after index

.. code-block:: python

   Window(
       start=WindowBound(days=0, coeff=-1),  # Index date
       end=WindowBound(days=30, coeff=1),    # 30 days after
       use_index_end=False,
       use_event_end=False
   )

Correlated Criteria
-------------------

Correlated criteria define events that must (or must not) occur relative to primary events.

Components:

* **Criteria** - The event to look for
* **Start Window** - When to start looking
* **End Window** - When to stop looking (optional)
* **Occurrence** - How many times (At Least, At Most, Exactly)

Example: Must have drug exposure within 30 days

.. code-block:: python

   CorelatedCriteria(
       criteria=DrugExposure(codeset_id=2),
       start_window=Window(
           start=WindowBound(days=0, coeff=-1),
           end=WindowBound(days=30, coeff=1)
       ),
       occurrence=Occurrence(type=2, count=1)  # At least 1
   )

Demographic Criteria
--------------------

Filter cohorts by person-level attributes:

Age
~~~

Age at index or age at end of period:

.. code-block:: python

   age=NumericRange(value=18, op="gte")  # 18 or older
   age_at_end=NumericRange(value=65, op="lte")  # 65 or younger

Gender
~~~~~~

Filter by gender concept:

.. code-block:: python

   gender=[Concept(concept_id=8507)]  # Male
   gender=[Concept(concept_id=8532)]  # Female

Date Ranges
~~~~~~~~~~~

Filter by calendar dates:

.. code-block:: python

   occurrence_start_date=DateRange(value="2020-01-01", op="gte")

Numeric Ranges
--------------

Numeric ranges filter continuous values.

Operators:

* ``lt`` - Less than
* ``lte`` - Less than or equal
* ``eq`` - Equal
* ``gt`` - Greater than
* ``gte`` - Greater than or equal
* ``bt`` - Between (requires extent)
* ``!bt`` - Not between

Example:

.. code-block:: python

   # Age between 18 and 65
   NumericRange(value=18, op="bt", extent=65)

   # HbA1c > 6.5
   NumericRange(value=6.5, op="gt")

Inclusion Rules
---------------

Inclusion rules add additional requirements after initial cohort selection.

Components:

* **Name** - Rule description
* **Expression** - Criteria group defining the rule

Example:

.. code-block:: python

   InclusionRule(
       name="Has follow-up visit",
       expression=CriteriaGroup(
           type="ALL",
           criteria_list=[
               CorelatedCriteria(
                   criteria=VisitOccurrence(codeset_id=3),
                   start_window=Window(...)
               )
           ]
       )
   )

Criteria Groups
---------------

Criteria groups combine multiple criteria with logic.

Group Types:

* ``ALL`` - Must meet all criteria
* ``ANY`` - Must meet at least one criterion
* ``AT_LEAST`` - Must meet at least N criteria
* ``AT_MOST`` - Must meet at most N criteria

Example:

.. code-block:: python

   CriteriaGroup(
       type="ALL",
       criteria_list=[criteria1, criteria2, criteria3]
   )

Next Steps
----------

* :doc:`cohort_definitions` - Build cohort definitions
* :doc:`sql_generation` - Generate SQL queries
* :doc:`validation` - Validate your cohorts
* :doc:`examples` - See practical examples

