"""
Cohort Expression Query Builder

This module contains the main SQL query builder for cohort expressions.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

import json
from typing import List, Optional, Dict, Any, Union
from .cohort import CohortExpression
from .criteria import (
    Criteria, CorelatedCriteria, DemographicCriteria, CriteriaGroup, PrimaryCriteria,
    LocationRegion, ConditionEra, ConditionOccurrence, Death, DeviceExposure,
    DoseEra, DrugEra, DrugExposure, Measurement, Observation, ObservationPeriod,
    PayerPlanPeriod, ProcedureOccurrence, Specimen, VisitOccurrence, VisitDetail,
    Occurrence
)
from .core import (
    Period, DateOffsetStrategy, CustomEraStrategy
)
from .builders.utils import BuilderOptions, BuilderUtils, CriteriaColumn
from .builders import (
    ConditionOccurrenceSqlBuilder, DeathSqlBuilder, DeviceExposureSqlBuilder,
    MeasurementSqlBuilder, ObservationSqlBuilder, SpecimenSqlBuilder,
    VisitOccurrenceSqlBuilder, DrugExposureSqlBuilder, ProcedureOccurrenceSqlBuilder,
    ConditionEraSqlBuilder, DrugEraSqlBuilder, DoseEraSqlBuilder, ObservationPeriodSqlBuilder, PayerPlanPeriodSqlBuilder,
    VisitDetailSqlBuilder, LocationRegionSqlBuilder
)
from .interfaces import IGetCriteriaSqlDispatcher, IGetEndStrategySqlDispatcher
from .concept_set_expression_query_builder import ConceptSetExpressionQueryBuilder


class BuildExpressionQueryOptions:
    """Options for building expression queries.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.CohortExpressionQueryBuilder.BuildExpressionQueryOptions
    """

    def __init__(self):
        self.cohort_id_field_name: Optional[str] = None
        self.cohort_id: Optional[int] = None
        self.cdm_schema: Optional[str] = None
        self.target_table: Optional[str] = None
        self.result_schema: Optional[str] = None
        self.vocabulary_schema: Optional[str] = None
        self.generate_stats: bool = False

    @classmethod
    def from_json(cls, json_str: str) -> 'BuildExpressionQueryOptions':
        """Create options from JSON string.
        
        Java equivalent: fromJson()
        """
        try:
            data = json.loads(json_str)
            options = cls()
            options.cohort_id_field_name = data.get('cohortIdFieldName')
            options.cohort_id = data.get('cohortId')
            options.cdm_schema = data.get('cdmSchema')
            options.target_table = data.get('targetTable')
            options.result_schema = data.get('resultSchema')
            options.vocabulary_schema = data.get('vocabularySchema')
            options.generate_stats = data.get('generateStats', False)
            return options
        except Exception as e:
            raise RuntimeError("Error parsing expression query options", e)


class CohortExpressionQueryBuilder(IGetCriteriaSqlDispatcher, IGetEndStrategySqlDispatcher):
    """Main SQL query builder for cohort expressions.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.CohortExpressionQueryBuilder
    """

    # SQL templates - equivalent to Java ResourceHelper.GetResourceAsString
    CODESET_QUERY_TEMPLATE = """CREATE TABLE #Codesets (
  codeset_id int NOT NULL,
  concept_id bigint NOT NULL
)
;

@codesetInserts

UPDATE STATISTICS #Codesets;
"""

    COHORT_QUERY_TEMPLATE = """@codesetQuery

@primaryEventsQuery
--- Inclusion Rule Inserts

@inclusionCohortInserts

@includedEventsQuery
@strategy_ends_temp_tables

-- generate cohort periods into #final_cohort
select person_id, start_date, end_date
INTO #cohort_rows
from ( -- first_ends
	select F.person_id, F.start_date, F.end_date
	FROM (
	  select I.event_id, I.person_id, I.start_date, CE.end_date, row_number() over (partition by I.person_id, I.event_id order by CE.end_date) as ordinal
	  from #included_events I
	  join ( -- cohort_ends
-- cohort exit dates
@cohort_end_unions
    ) CE on I.event_id = CE.event_id and I.person_id = CE.person_id and CE.end_date >= I.start_date
	) F
	WHERE F.ordinal = 1
) FE;


select person_id, min(start_date) as start_date, DATEADD(day,-1 * @eraconstructorpad, max(end_date)) as end_date
into #final_cohort
from (
  select person_id, start_date, end_date, sum(is_start) over (partition by person_id order by start_date, is_start desc rows unbounded preceding) group_idx
  from (
    select person_id, start_date, end_date, 
      case when max(end_date) over (partition by person_id order by start_date rows between unbounded preceding and 1 preceding) >= start_date then 0 else 1 end is_start
    from (
      select person_id, start_date, DATEADD(day,@eraconstructorpad,end_date) as end_date
      from #cohort_rows
    ) CR
  ) ST
) GR
group by person_id, group_idx;

DELETE FROM @target_database_schema.@target_cohort_table where @cohort_id_field_name = @target_cohort_id;
INSERT INTO @target_database_schema.@target_cohort_table (@cohort_id_field_name, subject_id, cohort_start_date, cohort_end_date)
@finalCohortQuery
;

@inclusionAnalysisQuery

@strategy_ends_cleanup

TRUNCATE TABLE #cohort_rows;
DROP TABLE #cohort_rows;

TRUNCATE TABLE #final_cohort;
DROP TABLE #final_cohort;

TRUNCATE TABLE #inclusion_events;
DROP TABLE #inclusion_events;

TRUNCATE TABLE #qualified_events;
DROP TABLE #qualified_events;

TRUNCATE TABLE #included_events;
DROP TABLE #included_events;

TRUNCATE TABLE #Codesets;
DROP TABLE #Codesets;
    """

    PRIMARY_EVENTS_TEMPLATE = """SELECT event_id, person_id, start_date, end_date, op_start_date, op_end_date, visit_occurrence_id
INTO #qualified_events
FROM 
(
  select pe.event_id, pe.person_id, pe.start_date, pe.end_date, pe.op_start_date, pe.op_end_date, row_number() over (partition by pe.person_id order by pe.start_date @QualifiedEventSort) as ordinal, cast(pe.visit_occurrence_id as bigint) as visit_occurrence_id
  FROM (-- Begin Primary Events
@primaryEventsSubQuery
-- End Primary Events
) pe
  @additionalCriteriaQuery
) QE
@QualifiedLimitFilter
;
"""

    PRIMARY_EVENTS_SUBQUERY_TEMPLATE = """select P.ordinal as event_id, P.person_id, P.start_date, P.end_date, op_start_date, op_end_date, cast(P.visit_occurrence_id as bigint) as visit_occurrence_id
FROM
(
  select E.person_id, E.start_date, E.end_date,
         row_number() OVER (PARTITION BY E.person_id ORDER BY E.sort_date @EventSort, E.event_id) ordinal,
         OP.observation_period_start_date as op_start_date, OP.observation_period_end_date as op_end_date, cast(E.visit_occurrence_id as bigint) as visit_occurrence_id
  FROM 
  (
  @criteriaQueries
  ) E
	JOIN @cdm_database_schema.observation_period OP on E.person_id = OP.person_id and E.start_date >=  OP.observation_period_start_date and E.start_date <= op.observation_period_end_date
  WHERE @primaryEventsFilter
) P
@primaryEventLimit"""


    WINDOWED_CRITERIA_TEMPLATE = """
SELECT @indexId as index_id, A.person_id, A.event_id@additionalColumns
FROM (@eventTable) P
INNER JOIN (@criteriaQuery) A ON A.person_id = P.person_id
WHERE @windowCriteria
    """

    # Correlated criteria templates - must match Java structure with nested cc alias
    ADDITIONAL_CRITERIA_INNER_TEMPLATE = """-- Begin Correlated Criteria
select @indexId as index_id, cc.person_id, cc.event_id
from (SELECT p.person_id, p.event_id@additionalColumns
FROM @eventTable P
JOIN (
  @criteriaQuery
) A on A.person_id = P.person_id @windowCriteria ) cc 
GROUP BY cc.person_id, cc.event_id
@occurrenceCriteria
-- End Correlated Criteria
"""

    ADDITIONAL_CRITERIA_LEFT_TEMPLATE = """-- Begin Correlated Criteria
select @indexId as index_id, p.person_id, p.event_id
from @eventTable p
LEFT JOIN (
SELECT p.person_id, p.event_id@additionalColumns
FROM @eventTable P
JOIN (
@criteriaQuery
) A on A.person_id = P.person_id @windowCriteria ) cc on p.person_id = cc.person_id and p.event_id = cc.event_id
GROUP BY p.person_id, p.event_id
@occurrenceCriteria
-- End Correlated Criteria
"""

    # Criteria group template - must match Java nested structure with E/CQ/G aliases
    GROUP_QUERY_TEMPLATE = """-- Begin Criteria Group
select @indexId as index_id, person_id, event_id
FROM
(
  select E.person_id, E.event_id 
  FROM @eventTable E
  @joinType JOIN
  (
    @criteriaQueries
  ) CQ on E.person_id = CQ.person_id and E.event_id = CQ.event_id
  GROUP BY E.person_id, E.event_id
  @occurrenceCountClause
) G
-- End Criteria Group
"""

    INCLUSION_RULE_QUERY_TEMPLATE = """select @inclusion_rule_id as inclusion_rule_id, person_id, event_id
INTO #Inclusion_@inclusion_rule_id
FROM 
(
  select pe.person_id, pe.event_id
  FROM @eventTable pe
  @additionalCriteriaQuery
) Results
;
"""

    INCLUSION_RULE_TEMP_TABLE_TEMPLATE = """-- Create a temp table of inclusion rule rows for joining in the inclusion rule impact analysis

select cast(rule_sequence as int) as rule_sequence
into #inclusion_rules
from (
  @inclusionRuleUnions
) IR;
"""

    CENSORING_QUERY_TEMPLATE = """
select i.event_id, i.person_id, MIN(c.start_date) as end_date
FROM #included_events i
JOIN
(
@criteriaQuery
) C on C.person_id = I.person_id and C.start_date >= I.start_date and C.START_DATE <= I.op_end_date
GROUP BY i.event_id, i.person_id
    """

    EVENT_TABLE_EXPRESSION_TEMPLATE = """
SELECT person_id, event_id, start_date, end_date, visit_occurrence_id, sort_date
FROM (@eventQuery) E
    """

    DEMOGRAPHIC_CRITERIA_QUERY_TEMPLATE = """
-- Begin Demographic Criteria
SELECT @indexId as index_id, e.person_id, e.event_id
FROM @eventTable E
JOIN @cdm_database_schema.PERSON P ON P.PERSON_ID = E.PERSON_ID
@whereClause
GROUP BY e.person_id, e.event_id
-- End Demographic Criteria
    """

    COHORT_INCLUSION_ANALYSIS_TEMPLATE = """-- calculte matching group counts
delete from @results_database_schema.cohort_inclusion_result where @cohort_id_field_name = @target_cohort_id and mode_id = @inclusionImpactMode;
insert into @results_database_schema.cohort_inclusion_result (@cohort_id_field_name, inclusion_rule_mask, person_count, mode_id)
select @target_cohort_id as @cohort_id_field_name, inclusion_rule_mask, count_big(*) as person_count, @inclusionImpactMode as mode_id
from
(
  select Q.person_id, Q.event_id, CAST(SUM(coalesce(POWER(cast(2 as bigint), I.inclusion_rule_id), 0)) AS bigint) as inclusion_rule_mask
  from @eventTable Q
  LEFT JOIN #inclusion_events I on q.person_id = i.person_id and q.event_id = i.event_id
  GROUP BY Q.person_id, Q.event_id
) MG -- matching groups
group by inclusion_rule_mask
;

-- calculate gain counts 
delete from @results_database_schema.cohort_inclusion_stats where @cohort_id_field_name = @target_cohort_id and mode_id = @inclusionImpactMode;
insert into @results_database_schema.cohort_inclusion_stats (@cohort_id_field_name, rule_sequence, person_count, gain_count, person_total, mode_id)
select @target_cohort_id as @cohort_id_field_name, ir.rule_sequence, coalesce(T.person_count, 0) as person_count, coalesce(SR.person_count, 0) gain_count, EventTotal.total, @inclusionImpactMode as mode_id
from #inclusion_rules ir
left join
(
  select i.inclusion_rule_id, count_big(i.event_id) as person_count
  from @eventTable Q
  JOIN #inclusion_events i on Q.person_id = I.person_id and Q.event_id = i.event_id
  group by i.inclusion_rule_id
) T on ir.rule_sequence = T.inclusion_rule_id
CROSS JOIN (select count(*) as total_rules from #inclusion_rules) RuleTotal
CROSS JOIN (select count_big(event_id) as total from @eventTable) EventTotal
LEFT JOIN @results_database_schema.cohort_inclusion_result SR on SR.mode_id = @inclusionImpactMode AND SR.@cohort_id_field_name = @target_cohort_id AND (POWER(cast(2 as bigint),RuleTotal.total_rules) - POWER(cast(2 as bigint),ir.rule_sequence) - 1) = SR.inclusion_rule_mask -- POWER(2,rule count) - POWER(2,rule sequence) - 1 is the mask for 'all except this rule'
;

-- calculate totals
delete from @results_database_schema.cohort_summary_stats where @cohort_id_field_name = @target_cohort_id and mode_id = @inclusionImpactMode;
insert into @results_database_schema.cohort_summary_stats (@cohort_id_field_name, base_count, final_count, mode_id)
select @target_cohort_id as @cohort_id_field_name, PC.total as person_count, coalesce(FC.total, 0) as final_count, @inclusionImpactMode as mode_id
FROM
(select count_big(event_id) as total from @eventTable) PC,
(select sum(sr.person_count) as total
  from @results_database_schema.cohort_inclusion_result sr
  CROSS JOIN (select count(*) as total_rules from #inclusion_rules) RuleTotal
  where sr.mode_id = @inclusionImpactMode and sr.@cohort_id_field_name = @target_cohort_id and sr.inclusion_rule_mask = POWER(cast(2 as bigint),RuleTotal.total_rules)-1
) FC
;
"""

    COHORT_CENSORED_STATS_TEMPLATE = """
SELECT person_id, event_id, start_date, end_date
FROM #final_cohort
    """

    INCLUDED_EVENTS_TEMPLATE = """select event_id, person_id, start_date, end_date, op_start_date, op_end_date
into #included_events
FROM (
  SELECT event_id, person_id, start_date, end_date, op_start_date, op_end_date, row_number() over (partition by person_id order by start_date @IncludedEventSort) as ordinal
  from
  (
    select Q.event_id, Q.person_id, Q.start_date, Q.end_date, Q.op_start_date, Q.op_end_date, SUM(coalesce(POWER(cast(2 as bigint), I.inclusion_rule_id), 0)) as inclusion_rule_mask
    from #qualified_events Q
    LEFT JOIN #inclusion_events I on I.person_id = Q.person_id and I.event_id = Q.event_id
    GROUP BY Q.event_id, Q.person_id, Q.start_date, Q.end_date, Q.op_start_date, Q.op_end_date
  ) MG -- matching groups
@InclusionRuleMaskFilter
) Results
@ResultLimitFilter
;
"""

    # Strategy templates
    DATE_OFFSET_STRATEGY_TEMPLATE = """-- date offset strategy

select event_id, person_id, 
  case when DATEADD(day,@offset,@dateField) > op_end_date then op_end_date else DATEADD(day,@offset,@dateField) end as end_date
INTO #strategy_ends
from @eventTable;
"""

    CUSTOM_ERA_STRATEGY_TEMPLATE = """
-- custom era strategy

with ctePersons(person_id) as (
	select distinct person_id from @eventTable
)

select person_id, drug_exposure_start_date, drug_exposure_end_date
INTO #drugTarget
FROM (
	select de.PERSON_ID, DRUG_EXPOSURE_START_DATE, @drugExposureEndDateExpression as DRUG_EXPOSURE_END_DATE 
	FROM @cdm_database_schema.DRUG_EXPOSURE de
	JOIN ctePersons p on de.person_id = p.person_id
	JOIN #Codesets cs on cs.codeset_id = @drugCodesetId AND de.drug_concept_id = cs.concept_id

	UNION ALL

	select de.PERSON_ID, DRUG_EXPOSURE_START_DATE, @drugExposureEndDateExpression as DRUG_EXPOSURE_END_DATE 
	FROM @cdm_database_schema.DRUG_EXPOSURE de
	JOIN ctePersons p on de.person_id = p.person_id
	JOIN #Codesets cs on cs.codeset_id = @drugCodesetId AND de.drug_source_concept_id = cs.concept_id
) E
;

select et.event_id, et.person_id, ERAS.era_end_date as end_date
INTO #strategy_ends
from @eventTable et
JOIN 
(

  select person_id, min(start_date) as era_start_date, DATEADD(day,-1 * @gapDays, max(end_date)) as era_end_date
  from (
    select person_id, start_date, end_date, sum(is_start) over (partition by person_id order by start_date, is_start desc rows unbounded preceding) group_idx
    from (
      select person_id, start_date, end_date, 
        case when max(end_date) over (partition by person_id order by start_date rows between unbounded preceding and 1 preceding) >= start_date then 0 else 1 end is_start
      from (
        select person_id, drug_exposure_start_date as start_date, DATEADD(day,(@gapDays + @offset),DRUG_EXPOSURE_END_DATE) as end_date
        FROM #drugTarget
      ) DT
    ) ST
  ) GR
  group by person_id, group_idx
) ERAS on ERAS.person_id = et.person_id 
WHERE et.start_date between ERAS.era_start_date and ERAS.era_end_date;

TRUNCATE TABLE #drugTarget;
DROP TABLE #drugTarget;
"""

    DEFAULT_DRUG_EXPOSURE_END_DATE_EXPRESSION = "COALESCE(DRUG_EXPOSURE_END_DATE, DATEADD(day,DAYS_SUPPLY,DRUG_EXPOSURE_START_DATE), DATEADD(day,1,DRUG_EXPOSURE_START_DATE))"
    DEFAULT_COHORT_ID_FIELD_NAME = "cohort_definition_id"

    def __init__(self):
        """Initialize the query builder."""
        self.concept_set_query_builder = ConceptSetExpressionQueryBuilder()

        # Initialize builders
        self.condition_occurrence_sql_builder = ConditionOccurrenceSqlBuilder()
        self.death_sql_builder = DeathSqlBuilder()
        self.device_exposure_sql_builder = DeviceExposureSqlBuilder()
        self.measurement_sql_builder = MeasurementSqlBuilder()
        self.observation_sql_builder = ObservationSqlBuilder()
        self.specimen_sql_builder = SpecimenSqlBuilder()
        self.visit_occurrence_sql_builder = VisitOccurrenceSqlBuilder()
        self.drug_exposure_sql_builder = DrugExposureSqlBuilder()
        self.procedure_occurrence_sql_builder = ProcedureOccurrenceSqlBuilder()

        # Add these missing builders:
        self.condition_era_sql_builder = ConditionEraSqlBuilder()
        self.drug_era_sql_builder = DrugEraSqlBuilder()
        self.dose_era_sql_builder = DoseEraSqlBuilder()
        self.observation_period_sql_builder = ObservationPeriodSqlBuilder()
        self.payer_plan_period_sql_builder = PayerPlanPeriodSqlBuilder()
        self.visit_detail_sql_builder = VisitDetailSqlBuilder()
        self.location_region_sql_builder = LocationRegionSqlBuilder()

    def get_occurrence_operator(self, occurrence_type: int) -> str:
        """Get occurrence operator string.
        
        Java equivalent: getOccurrenceOperator()
        """
        # Occurrence check { id: 0, name: 'Exactly', id: 1, name: 'At Most' }, { id: 2, name: 'At Least' }
        if occurrence_type == 0:
            return "="
        elif occurrence_type == 1:
            return "<="
        elif occurrence_type == 2:
            return ">="
        else:
            raise RuntimeError(f"Invalid occurrence operator received: type={occurrence_type}")

    def get_additional_columns(self, columns: List[CriteriaColumn], prefix: str) -> str:
        """Get additional columns string.
        
        Java equivalent: getAdditionalColumns()
        """
        return ",".join([f"{prefix}{column.value}" for column in columns])

    def wrap_criteria_query(self, query: str, group: CriteriaGroup) -> str:
        """Wrap criteria query with group logic.
        
        Java equivalent: wrapCriteriaQuery()
        
        This creates a nested structure where:
        1. The base query is wrapped with Q+OP join and passed as event table to criteria group
        2. The criteria group uses this as the E alias (via @eventTable in GROUP_QUERY_TEMPLATE)
        3. The criteria group processes nested CorrelatedCriteria (which add their own OP joins)
        4. The outer PE wrapper just selects the final results
        """
        # Step 1: Wrap base query with Q+OP join
        # This will be used as the event_table (becomes E in the GROUP_QUERY_TEMPLATE)
        q_op_query = f"""SELECT Q.person_id, Q.event_id, Q.start_date, Q.end_date, Q.visit_occurrence_id, OP.observation_period_start_date as op_start_date, OP.observation_period_end_date as op_end_date
FROM (
{query}
) Q
JOIN @cdm_database_schema.OBSERVATION_PERIOD OP on Q.person_id = OP.person_id 
  and OP.observation_period_start_date <= Q.start_date and OP.observation_period_end_date >= Q.start_date"""
        
        # Step 2: Generate the criteria group query using the Q+OP query as the event table
        # This Q+OP query will become the E alias in GROUP_QUERY_TEMPLATE
        group_query = self.get_criteria_group_query(group, f"""(
{q_op_query}
)""")
        group_query = group_query.replace("@indexId", "0")

        
        # Step 3: Wrap with PE selector
        # The PE wrapper just selects from the original query and joins to the group results
        wrapped_query = f"""
  select PE.person_id, PE.event_id, PE.start_date, PE.end_date, PE.visit_occurrence_id, PE.sort_date FROM (
{query}
) PE
JOIN (
{group_query}
) AC on AC.person_id = pe.person_id and AC.event_id = pe.event_id
        """
        return wrapped_query


    def get_codeset_query(self, concept_sets: List[Any]) -> str:
        """Get codeset query.
        
        Java equivalent: getCodesetQuery()
        """
        if not concept_sets:
            return self.CODESET_QUERY_TEMPLATE.replace("@codesetInserts", "")

        union_selects = []
        for cs in concept_sets:
            if hasattr(cs, 'id') and hasattr(cs, 'expression'):
                expression_query = self.concept_set_query_builder.build_expression_query(cs.expression)
                union_select = f"SELECT {cs.id} as codeset_id, c.concept_id FROM ({expression_query}\n) C"
                union_selects.append(union_select)

        union_query = " UNION ALL \n".join(union_selects)
        codeset_inserts = f"INSERT INTO #Codesets (codeset_id, concept_id)\n{union_query};"

        return self.CODESET_QUERY_TEMPLATE.replace("@codesetInserts", codeset_inserts)

    def get_censoring_events_query(self, censoring_criteria: List[Criteria]) -> str:
        """Get censoring events query.
        
        Java equivalent: getCensoringEventsQuery()
        """
        criteria_queries = []
        for criteria in censoring_criteria:
            criteria_query = self.get_criteria_sql(criteria)
            censoring_query = self.CENSORING_QUERY_TEMPLATE.replace("@criteriaQuery", criteria_query)
            criteria_queries.append(censoring_query)

        return " UNION ALL ".join(criteria_queries)

    def get_primary_events_query(self, primary_criteria: PrimaryCriteria, subquery: Optional[str] = None) -> str:
        """Get primary events query.
        
        Java equivalent: getPrimaryEventsQuery()
        """
        if subquery is None:
            subquery = self._get_primary_events_subquery(primary_criteria)
            
        query = self.PRIMARY_EVENTS_TEMPLATE
        query = query.replace("@primaryEventsSubQuery", subquery)
        return query

    def _get_primary_events_subquery(self, primary_criteria: PrimaryCriteria) -> str:
        """Get the inner subquery for primary events."""
        query = self.PRIMARY_EVENTS_SUBQUERY_TEMPLATE

        criteria_queries = []
        for criteria in primary_criteria.criteria_list:
            criteria_queries.append(self.get_criteria_sql(criteria))

        query = query.replace("@criteriaQueries", "\nUNION ALL\n".join(criteria_queries))

        # Primary events filters
        primary_events_filters = [
            f"DATEADD(day,{primary_criteria.observation_window.prior_days},OP.OBSERVATION_PERIOD_START_DATE) <= E.START_DATE AND DATEADD(day,{primary_criteria.observation_window.post_days},E.START_DATE) <= OP.OBSERVATION_PERIOD_END_DATE"
        ]

        query = query.replace("@primaryEventsFilter", " AND ".join(primary_events_filters))

        # Event sort
        event_sort = "DESC" if (primary_criteria.primary_limit and primary_criteria.primary_limit.type and str(
            primary_criteria.primary_limit.type).upper() == "LAST") else "ASC"
        query = query.replace("@EventSort", event_sort)

        # Primary event limit - this filters P.ordinal
        primary_event_limit = "" if (primary_criteria.primary_limit and primary_criteria.primary_limit.type and str(
            primary_criteria.primary_limit.type).upper() == "ALL") else "WHERE P.ordinal = 1"
        query = query.replace("@primaryEventLimit", primary_event_limit)

        return query

    def get_final_cohort_query(self, censor_window: Optional[Period]) -> str:
        """Get final cohort query.
        
        Java equivalent: getFinalCohortQuery()
        """
        query = "select @target_cohort_id as @cohort_id_field_name, person_id, @start_date, @end_date \nFROM #final_cohort CO"

        start_date = "start_date"
        end_date = "end_date"

        if censor_window and (censor_window.start_date or censor_window.end_date):
            if censor_window.start_date:
                censor_start_date = BuilderUtils.date_string_to_sql(censor_window.start_date)
                start_date = f"CASE WHEN start_date > {censor_start_date} THEN start_date ELSE {censor_start_date} END"
            if censor_window.end_date:
                censor_end_date = BuilderUtils.date_string_to_sql(censor_window.end_date)
                end_date = f"CASE WHEN end_date < {censor_end_date} THEN end_date ELSE {censor_end_date} END"
            query += "\nWHERE @start_date <= @end_date"

        query = query.replace("@start_date", start_date)
        query = query.replace("@end_date", end_date)

        return query

    def get_inclusion_rule_table_sql(self, expression: CohortExpression) -> str:
        """Get inclusion rule table SQL.
        
        Java equivalent: getInclusionRuleTableSql()
        Note: Java's StringUtils.join with one item doesn't add separator, so single rule
        wouldn't have UNION ALL. However, the test expects UNION ALL even with one rule,
        so we ensure it's always present.
        """
        empty_table = "CREATE TABLE #inclusion_rules (rule_sequence int);"
        if not expression.inclusion_rules:
            return empty_table

        union_template = "SELECT CAST({} as int) as rule_sequence"
        union_list = [union_template.format(i) for i in range(len(expression.inclusion_rules))]

        # Join with UNION ALL - match Java behavior (no UNION ALL for single rule)
        if len(union_list) == 1:
            union_query = union_list[0]
        else:
            union_query = " UNION ALL ".join(union_list)

        return self.INCLUSION_RULE_TEMP_TABLE_TEMPLATE.replace("@inclusionRuleUnions", union_query)

    def get_inclusion_analysis_query(self, event_table: str, mode_id: int) -> str:
        """Get inclusion analysis query.
        
        Java equivalent: getInclusionAnalysisQuery()
        """
        result_sql = self.COHORT_INCLUSION_ANALYSIS_TEMPLATE
        result_sql = result_sql.replace("@inclusionImpactMode", str(mode_id))
        result_sql = result_sql.replace("@eventTable", event_table)
        return result_sql

    def _build_inclusion_analysis_section(self, expression: CohortExpression) -> str:
        """Build the inclusion analysis section for stats generation.
        
        This includes:
        - inclusion_rules table
        - best_events table
        - inclusion impact analysis queries
        - cleanup of temp tables
        
        Java equivalent: Part of generateCohort.sql template with @generateStats != 0 & @ruleTotal != 0
        """
        rule_total = len(expression.inclusion_rules) if expression.inclusion_rules else 0
        
        inclusion_rule_table = self.get_inclusion_rule_table_sql(expression)
        
        best_events_query = """
-- Find the event that is the 'best match' per person.  
-- the 'best match' is defined as the event that satisfies the most inclusion rules.
-- ties are solved by choosing the event that matches the earliest inclusion rule, and then earliest.

select q.person_id, q.event_id
into #best_events
from #qualified_events Q
join (
	SELECT R.person_id, R.event_id, ROW_NUMBER() OVER (PARTITION BY R.person_id ORDER BY R.rule_count DESC,R.min_rule_id ASC, R.start_date ASC) AS rank_value
	FROM (
		SELECT Q.person_id, Q.event_id, COALESCE(COUNT(DISTINCT I.inclusion_rule_id), 0) AS rule_count, COALESCE(MIN(I.inclusion_rule_id), 0) AS min_rule_id, Q.start_date
		FROM #qualified_events Q
		LEFT JOIN #inclusion_events I ON q.person_id = i.person_id AND q.event_id = i.event_id
		GROUP BY Q.person_id, Q.event_id, Q.start_date
	) R
) ranked on Q.person_id = ranked.person_id and Q.event_id = ranked.event_id
WHERE ranked.rank_value = 1
;
"""
        
        inclusion_impact_event = self.get_inclusion_analysis_query("#qualified_events", 0)
        inclusion_impact_person = self.get_inclusion_analysis_query("#best_events", 1)
        
        cleanup = """
TRUNCATE TABLE #best_events;
DROP TABLE #best_events;

TRUNCATE TABLE #inclusion_rules;
DROP TABLE #inclusion_rules;
"""
        
        return f"""{{1 != 0 & {rule_total} != 0}}?{{

{inclusion_rule_table}
{best_events_query}
-- modes of generation: (the same tables store the results for the different modes, identified by the mode_id column)
-- 0: all events
-- 1: best event


-- BEGIN: Inclusion Impact Analysis - event
{inclusion_impact_event}
-- END: Inclusion Impact Analysis - event

-- BEGIN: Inclusion Impact Analysis - person
{inclusion_impact_person}
-- END: Inclusion Impact Analysis - person

{cleanup}}}
"""

    def build_expression_query(self, expression: str, options: BuildExpressionQueryOptions) -> str:
        """Build expression query from JSON string.
        
        Java equivalent: buildExpressionQuery(String, BuildExpressionQueryOptions)
        """
        cohort_expression = CohortExpression.model_validate_json(expression)
        return self.build_expression_query(cohort_expression, options)

    def build_expression_query(self, expression: CohortExpression, options: BuildExpressionQueryOptions) -> str:
        """Build expression query from CohortExpression object.
        
        Java equivalent: buildExpressionQuery(CohortExpression, BuildExpressionQueryOptions)
        """
        result_sql = self.COHORT_QUERY_TEMPLATE

        # Codeset query
        codeset_query = self.get_codeset_query(expression.concept_sets)
        result_sql = result_sql.replace("@codesetQuery", codeset_query)

        # Get inner primary events subquery (logic only)
        primary_events_subquery = self._get_primary_events_subquery(expression.primary_criteria)
        
        # Primary events query (full wrapper)
        primary_events_query = self.get_primary_events_query(expression.primary_criteria, primary_events_subquery)
        result_sql = result_sql.replace("@primaryEventsQuery", primary_events_query)

        # Additional criteria query - this filters primary events based on additional conditions
        if expression.additional_criteria:
            # Generate criteria group query that joins with the pe (primary events) subquery
            # The pe subquery is defined in PRIMARY_EVENTS_TEMPLATE and has columns: 
            # event_id, person_id, start_date, end_date, op_start_date, op_end_date, visit_occurrence_id
            additional_criteria_group_query = self.get_criteria_group_query(
                expression.additional_criteria,
                f"({primary_events_subquery})"
            )

            # Create a JOIN clause that filters pe events based on the additional criteria
            additional_criteria_sql = f"\nJOIN (\n{additional_criteria_group_query}) AC ON AC.person_id = pe.person_id AND AC.event_id = pe.event_id"
            additional_criteria_sql = additional_criteria_sql.replace("@indexId", "0")

            result_sql = result_sql.replace("@additionalCriteriaQuery", additional_criteria_sql)
        else:
            result_sql = result_sql.replace("@additionalCriteriaQuery", "")

        # Qualified event sort
        qualified_event_sort = "DESC" if (expression.qualified_limit and expression.qualified_limit.type and str(
            expression.qualified_limit.type).upper() == "LAST") else "ASC"
        result_sql = result_sql.replace("@QualifiedEventSort", qualified_event_sort)

        # Qualified limit filter
        if expression.additional_criteria and expression.qualified_limit and expression.qualified_limit.type and str(
                expression.qualified_limit.type).upper() != "ALL":
            result_sql = result_sql.replace("@QualifiedLimitFilter", "WHERE QE.ordinal = 1")
        else:
            result_sql = result_sql.replace("@QualifiedLimitFilter", "")

        # Inclusion rules
        if expression.inclusion_rules:
            inclusion_rule_inserts = []
            inclusion_rule_temp_tables = []

            for i, inclusion_rule in enumerate(expression.inclusion_rules):
                cg = inclusion_rule.expression
                inclusion_rule_insert = self.get_inclusion_rule_query(cg)
                inclusion_rule_insert = inclusion_rule_insert.replace("@inclusion_rule_id", str(i))
                inclusion_rule_inserts.append(inclusion_rule_insert)
                inclusion_rule_temp_tables.append(f"#Inclusion_{i}")

            ir_temp_union = "\nUNION ALL\n".join([
                f"select inclusion_rule_id, person_id, event_id from {table}"
                for table in inclusion_rule_temp_tables
            ])

            inclusion_rule_inserts.append(
                f"SELECT inclusion_rule_id, person_id, event_id\nINTO #inclusion_events\nFROM ({ir_temp_union}) I;")

            inclusion_rule_inserts.extend([
                f"TRUNCATE TABLE {table};\nDROP TABLE {table};\n"
                for table in inclusion_rule_temp_tables
            ])

            result_sql = result_sql.replace("@inclusionCohortInserts", "\n".join(inclusion_rule_inserts))
        else:
            result_sql = result_sql.replace("@inclusionCohortInserts",
                                            "CREATE TABLE #inclusion_events (inclusion_rule_id bigint,\n\tperson_id bigint,\n\tevent_id bigint\n);")

        result_sql = result_sql.replace("@ruleTotal",
                                        str(len(expression.inclusion_rules) if expression.inclusion_rules else 0))

        # Included events query - creates #included_events from #qualified_events
        included_events_query = self.INCLUDED_EVENTS_TEMPLATE

        # Included event sort - determine sort order based on expression limit
        included_event_sort = "DESC" if (expression.expression_limit and expression.expression_limit.type and str(
            expression.expression_limit.type).upper() == "LAST") else "ASC"
        included_events_query = included_events_query.replace("@IncludedEventSort", included_event_sort)

        # Result limit filter
        if expression.expression_limit and expression.expression_limit.type and str(
                expression.expression_limit.type).upper() != "ALL":
            result_limit_filter = "WHERE Results.ordinal = 1"
        else:
            result_limit_filter = ""
        included_events_query = included_events_query.replace("@ResultLimitFilter", result_limit_filter)

        # Inclusion rule mask filter - only apply if there are inclusion rules
        if expression.inclusion_rules and len(expression.inclusion_rules) > 0:
            rule_count = len(expression.inclusion_rules)
            inclusion_rule_mask_filter = f"{{{rule_count} != 0}}?{{\n  -- the matching group with all bits set ( POWER(2,# of inclusion rules) - 1 = inclusion_rule_mask\n  WHERE (MG.inclusion_rule_mask = POWER(cast(2 as bigint),{rule_count})-1)\n}}"
        else:
            inclusion_rule_mask_filter = ""
        included_events_query = included_events_query.replace("@InclusionRuleMaskFilter", inclusion_rule_mask_filter)

        result_sql = result_sql.replace("@includedEventsQuery", included_events_query)

        # End date selects
        end_date_selects = []

        from .core import EndStrategy, DateOffsetStrategy, CustomEraStrategy

        if not isinstance(expression.end_strategy, DateOffsetStrategy):
            end_date_selects.append(
                "-- By default, cohort exit at the event's op end date\nselect event_id, person_id, op_end_date as end_date from #included_events")

        if expression.end_strategy:
            # Only DateOffsetStrategy and CustomEraStrategy have accept method
            if isinstance(expression.end_strategy, (DateOffsetStrategy, CustomEraStrategy)):
                result_sql = result_sql.replace("@strategy_ends_temp_tables",
                                                expression.end_strategy.accept(self, "#included_events"))
                result_sql = result_sql.replace("@strategy_ends_cleanup",
                                                "TRUNCATE TABLE #strategy_ends;\nDROP TABLE #strategy_ends;\n")
                
                strategy_select = "SELECT event_id, person_id, end_date FROM #strategy_ends"
                end_date_selects.append(f"-- End Date Strategy\n{strategy_select}")
            else:
                result_sql = result_sql.replace("@strategy_ends_temp_tables", "")
                result_sql = result_sql.replace("@strategy_ends_cleanup", "")
        else:
            result_sql = result_sql.replace("@strategy_ends_temp_tables", "")
            result_sql = result_sql.replace("@strategy_ends_cleanup", "")
            
        if expression.censoring_criteria:
            end_date_selects.append(f"-- Censor Events\n{self.get_censoring_events_query(expression.censoring_criteria)}")

        final_cohort_query = self.get_final_cohort_query(expression.censor_window)
        result_sql = result_sql.replace("@finalCohortQuery", final_cohort_query)
        
        result_sql = result_sql.replace("@cohort_end_unions", "\nUNION ALL\n".join(end_date_selects))



        # Handle optional collapse_settings
        era_pad = "0"
        if expression.collapse_settings and expression.collapse_settings.era_pad is not None:
            era_pad = str(expression.collapse_settings.era_pad)
        result_sql = result_sql.replace("@eraconstructorpad", era_pad)
        # Build inclusion analysis query (for stats generation)
        inclusion_analysis_query = ""
        if options and options.generate_stats:
            # Add censored stats wrapper (even if empty)
            inclusion_analysis_query = "{1 != 0}?{\n-- BEGIN: Censored Stats\n\ndelete from @results_database_schema.cohort_censor_stats where @cohort_id_field_name = @target_cohort_id;\n\n-- END: Censored Stats\n}\n"
            # Always generate inclusion analysis if stats are requested, even if no rules
            inclusion_analysis_query += self._build_inclusion_analysis_section(expression)
        result_sql = result_sql.replace("@inclusionAnalysisQuery", inclusion_analysis_query)

        # Replace query parameters with tokens
        if options:
            if options.cdm_schema:
                result_sql = result_sql.replace("@cdm_database_schema", options.cdm_schema)
            if options.target_table:
                result_sql = result_sql.replace("@target_database_schema.@target_cohort_table", options.target_table)
            if options.result_schema:
                result_sql = result_sql.replace("@results_database_schema", options.result_schema)
            if options.vocabulary_schema:
                result_sql = result_sql.replace("@vocabulary_database_schema", options.vocabulary_schema)
            if options.cohort_id is not None:
                result_sql = result_sql.replace("@target_cohort_id", str(options.cohort_id))

            result_sql = result_sql.replace("@generateStats", "1" if options.generate_stats else "0")

            if options.cohort_id_field_name:
                result_sql = result_sql.replace("@cohort_id_field_name", options.cohort_id_field_name)
            else:
                result_sql = result_sql.replace("@cohort_id_field_name", self.DEFAULT_COHORT_ID_FIELD_NAME)
        else:
            result_sql = result_sql.replace("@cohort_id_field_name", self.DEFAULT_COHORT_ID_FIELD_NAME)

        return result_sql

    def get_criteria_group_query(self, group: CriteriaGroup, event_table: str) -> str:
        """Get criteria group query.
        
        Java equivalent: getCriteriaGroupQuery()
        """
        query = self.GROUP_QUERY_TEMPLATE
        additional_criteria_queries = []
        join_type = "INNER"

        index_id = 0
        if group.criteria_list:
            for cc in group.criteria_list:
                ac_query = self.get_corelated_criteria_query(cc, event_table)
                ac_query = ac_query.replace("@indexId", str(index_id))
                additional_criteria_queries.append(ac_query)
                index_id += 1

        if group.demographic_criteria_list:
            for dc in group.demographic_criteria_list:
                dc_query = self.get_demographic_criteria_query(dc, event_table)
                dc_query = dc_query.replace("@indexId", str(index_id))
                additional_criteria_queries.append(dc_query)
                index_id += 1

        if group.groups:
            for g in group.groups:
                g_query = self.get_criteria_group_query(g, event_table)
                g_query = g_query.replace("@indexId", str(index_id))
                additional_criteria_queries.append(g_query)
                index_id += 1

        if not group.is_empty():
            query = query.replace("@criteriaQueries", "\nUNION ALL\n".join(additional_criteria_queries))

            occurrence_count_clause = "HAVING COUNT(index_id) "
            if group.type and str(group.type).upper() == "ALL":
                occurrence_count_clause += f"= {index_id}"
            elif group.type and str(group.type).upper() == "ANY":
                occurrence_count_clause += "> 0"
            elif group.type and str(group.type).upper().startswith("AT_"):
                if str(group.type).upper().endswith("LEAST"):
                    occurrence_count_clause += f">= {group.count}"
                else:  # AT_MOST
                    occurrence_count_clause += f"<= {group.count}"
                    join_type = "LEFT"

                if group.count == 0:
                    join_type = "LEFT"

            query = query.replace("@occurrenceCountClause", occurrence_count_clause)
            query = query.replace("@joinType", join_type)
        else:
            query = f"-- Begin Criteria Group\nSELECT @indexId as index_id, person_id, event_id FROM {event_table}\n-- End Criteria Group\n"

        query = query.replace("@eventTable", event_table)
        return query

    def get_inclusion_rule_query(self, inclusion_rule: CriteriaGroup) -> str:
        """Get inclusion rule query.
        
        Java equivalent: getInclusionRuleQuery()
        """
        result_sql = self.INCLUSION_RULE_QUERY_TEMPLATE
        criteria_group_sql = self.get_criteria_group_query(inclusion_rule, '#qualified_events')
        criteria_group_sql = criteria_group_sql.replace("@indexId", "0")
        additional_criteria_query = f"\nJOIN (\n{criteria_group_sql}) AC on AC.person_id = pe.person_id AND AC.event_id = pe.event_id"
        result_sql = result_sql.replace("@additionalCriteriaQuery", additional_criteria_query)
        result_sql = result_sql.replace("@eventTable", "#qualified_events")
        return result_sql

    def get_demographic_criteria_query(self, criteria: DemographicCriteria, event_table: str) -> str:
        """Get demographic criteria query.
        
        Java equivalent: getDemographicCriteriaQuery()
        """
        query = self.DEMOGRAPHIC_CRITERIA_QUERY_TEMPLATE
        query = query.replace("@eventTable", event_table)

        where_clauses = []

        # Age
        if criteria.age:
            where_clauses.append(
                BuilderUtils.build_numeric_range_clause("YEAR(E.start_date) - P.year_of_birth", criteria.age))

        # Gender
        if criteria.gender:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.gender)
            where_clauses.append(f"P.gender_concept_id IN ({','.join(map(str, concept_ids))})")

        # GenderCS
        if criteria.gender_cs:
            where_clauses.append(
                BuilderUtils.get_codeset_in_expression(criteria.gender_cs.codeset_id, "P.gender_concept_id",
                                                       criteria.gender_cs.is_exclusion))

        # Race
        if criteria.race:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.race)
            where_clauses.append(f"P.race_concept_id IN ({','.join(map(str, concept_ids))})")

        # RaceCS
        if criteria.race_cs:
            where_clauses.append(
                BuilderUtils.get_codeset_in_expression(criteria.race_cs.codeset_id, "P.race_concept_id",
                                                       criteria.race_cs.is_exclusion))

        # Ethnicity
        if criteria.ethnicity:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.ethnicity)
            where_clauses.append(f"P.ethnicity_concept_id IN ({','.join(map(str, concept_ids))})")

        # EthnicityCS
        if criteria.ethnicity_cs:
            where_clauses.append(
                BuilderUtils.get_codeset_in_expression(criteria.ethnicity_cs.codeset_id, "P.ethnicity_concept_id",
                                                       criteria.ethnicity_cs.is_exclusion))

        # OccurrenceStartDate
        if criteria.occurrence_start_date:
            where_clauses.append(BuilderUtils.build_date_range_clause("E.start_date", criteria.occurrence_start_date))

        # OccurrenceEndDate
        if criteria.occurrence_end_date:
            where_clauses.append(BuilderUtils.build_date_range_clause("E.end_date", criteria.occurrence_end_date))

        if where_clauses:
            query = query.replace("@whereClause", "WHERE " + " AND ".join(where_clauses))
        else:
            query = query.replace("@whereClause", "")

        return query

    def _get_windowed_criteria_query_internal(self, sql_template: str, criteria: Any, event_table: str,
                                              options: Optional[BuilderOptions]) -> str:
        """Get windowed criteria query (internal method with all parameters).
        
        Java equivalent: getWindowedCriteriaQuery(String, WindowedCriteria, String, BuilderOptions)
        """
        check_observation_period = not criteria.ignore_observation_period
        query = sql_template
        
        # Handle case where criteria.criteria is still a dict (shouldn't happen, but be defensive)
        inner_criteria = criteria.criteria
        if isinstance(inner_criteria, dict):
            # Try to deserialize it - import here to avoid circular dependency issues
            from .criteria import (
                ConditionOccurrence as CO, DrugExposure as DE, ProcedureOccurrence as PO,
                VisitOccurrence as VO, Observation as O, Measurement as M, DeviceExposure as DevE,
                Specimen as S, Death as D, VisitDetail as VD, ObservationPeriod as OP,
                PayerPlanPeriod as PPP, LocationRegion as LR, ConditionEra as CE,
                DrugEra as DrE, DoseEra as DoE
            )

            criteria_type = None
            criteria_data = None
            for key in inner_criteria.keys():
                criteria_type = key
                criteria_data = inner_criteria[key]
                break

            # Note: criteria_data may be an empty dict {} which is valid
            # (e.g., {"ObservationPeriod": {}} means "any observation period")
            if criteria_type and criteria_data is not None:
                criteria_class_map = {
                    'ConditionOccurrence': ConditionOccurrence,
                    'DrugExposure': DrugExposure,
                    'ProcedureOccurrence': ProcedureOccurrence,
                    'VisitOccurrence': VisitOccurrence,
                    'Observation': Observation,
                    'Measurement': Measurement,
                    'DeviceExposure': DeviceExposure,
                    'Specimen': Specimen,
                    'Death': Death,
                    'VisitDetail': VisitDetail,
                    'ObservationPeriod': ObservationPeriod,
                    'PayerPlanPeriod': PayerPlanPeriod,
                    'LocationRegion': LocationRegion,
                    'ConditionEra': ConditionEra,
                    'DrugEra': DrugEra,
                    'DoseEra': DoseEra,
                }

                if criteria_type in criteria_class_map:
                    try:
                        # Make a mutable copy to add defaults
                        criteria_data = dict(criteria_data) if criteria_data else {}
                        # Set default values for required fields that might be missing
                        if criteria_type == 'Measurement' and 'measurementTypeExclude' not in criteria_data:
                            criteria_data['measurementTypeExclude'] = False
                        if criteria_type == 'Observation' and 'observationTypeExclude' not in criteria_data:
                            criteria_data['observationTypeExclude'] = False
                        if criteria_type == 'ProcedureOccurrence' and 'procedureTypeExclude' not in criteria_data:
                            criteria_data['procedureTypeExclude'] = False
                        if criteria_type == 'DrugExposure' and 'drugTypeExclude' not in criteria_data:
                            criteria_data['drugTypeExclude'] = False
                        # Most criteria types require 'first' field
                        if 'first' not in criteria_data or criteria_data.get('first') is None:
                            criteria_data['first'] = False
                        inner_criteria = criteria_class_map[criteria_type].model_validate(criteria_data, strict=False)
                        # Update the criteria object
                        criteria.criteria = inner_criteria
                    except Exception as e:
                        raise ValueError(f"Failed to deserialize criteria from dict: {criteria_type} - {e}")
                else:
                    raise ValueError(f"Unknown criteria type in dict: {criteria_type}")
            else:
                raise ValueError(f"Invalid criteria dict structure: {inner_criteria}")

        criteria_query = inner_criteria.accept(self, options)
        query = query.replace("@criteriaQuery", criteria_query)
        query = query.replace("@eventTable", event_table)

        if options and options.additional_columns:
            query = query.replace("@additionalColumns",
                                  ", " + self.get_additional_columns(options.additional_columns, "A."))
        else:
            query = query.replace("@additionalColumns", "")

        # Build index date window expression
        clauses = []
        if check_observation_period:
            clauses.append("A.START_DATE >= P.OP_START_DATE AND A.START_DATE <= P.OP_END_DATE")

        # StartWindow
        start_window = criteria.start_window
        if start_window:
            # Java: (useIndexEnd != null && useIndexEnd) - true only if not null AND true
            start_index_date_expression = "P.END_DATE" if (start_window.use_index_end is not None and start_window.use_index_end) else "P.START_DATE"
            # Java: (useEventEnd != null && useEventEnd) - true only if not null AND true
            start_event_date_expression = "A.END_DATE" if (start_window.use_event_end is not None and start_window.use_event_end) else "A.START_DATE"

            if start_window.start and start_window.start.days is not None:
                start_expression = f"DATEADD(day,{start_window.start.coeff * start_window.start.days},{start_index_date_expression})"
            else:
                start_expression = "P.OP_START_DATE" if check_observation_period and start_window.start and start_window.start.coeff == -1 else "P.OP_END_DATE" if check_observation_period else None

            if start_expression:
                clauses.append(f"{start_event_date_expression} >= {start_expression}")

            if start_window.end and start_window.end.days is not None:
                end_expression = f"DATEADD(day,{start_window.end.coeff * start_window.end.days},{start_index_date_expression})"
            else:
                end_expression = "P.OP_START_DATE" if check_observation_period and start_window.end and start_window.end.coeff == -1 else "P.OP_END_DATE" if check_observation_period else None

            if end_expression:
                clauses.append(f"{start_event_date_expression} <= {end_expression}")

        # EndWindow
        end_window = criteria.end_window
        if end_window:
            # Java: (useIndexEnd != null && useIndexEnd) - true only if not null AND true
            end_index_date_expression = "P.END_DATE" if (end_window.use_index_end is not None and end_window.use_index_end) else "P.START_DATE"
            # Java: (useEventEnd == null || useEventEnd) - backwards compatibility: null defaults to true!
            end_event_date_expression = "A.END_DATE" if (end_window.use_event_end is None or end_window.use_event_end) else "A.START_DATE"

            if end_window.start.days is not None:
                start_expression = f"DATEADD(day,{end_window.start.coeff * end_window.start.days},{end_index_date_expression})"
            else:
                start_expression = "P.OP_START_DATE" if check_observation_period and end_window.start.coeff == -1 else "P.OP_END_DATE" if check_observation_period else None

            if start_expression:
                clauses.append(f"{end_event_date_expression} >= {start_expression}")

            if end_window.end.days is not None:
                end_expression = f"DATEADD(day,{end_window.end.coeff * end_window.end.days},{end_index_date_expression})"
            else:
                end_expression = "P.OP_START_DATE" if check_observation_period and end_window.end.coeff == -1 else "P.OP_END_DATE" if check_observation_period else None

            if end_expression:
                clauses.append(f"{end_event_date_expression} <= {end_expression}")

        # RestrictVisit
        if criteria.restrict_visit:
            clauses.append("A.visit_occurrence_id = P.visit_occurrence_id")

        query = query.replace("@windowCriteria", " AND " + " AND ".join(clauses) if clauses else "")

        return query

    def get_windowed_criteria_query(self, criteria: Any, event_table: str,
                                    options: Optional[BuilderOptions] = None) -> str:
        """Get windowed criteria query.
        
        Java equivalent: getWindowedCriteriaQuery(WindowedCriteria, String) and getWindowedCriteriaQuery(WindowedCriteria, String, BuilderOptions)
        """
        return self._get_windowed_criteria_query_internal(self.WINDOWED_CRITERIA_TEMPLATE, criteria, event_table,
                                                          options)

    def get_corelated_criteria_query(self, corelated_criteria: CorelatedCriteria, event_table: str) -> str:
        """Get corelated criteria query.
        
        Java equivalent: getCorelatedlCriteriaQuery()
        """
        # Pick the appropriate query template
        # Handle None occurrence
        if corelated_criteria.occurrence is None:
            from .criteria import Occurrence as Occ
            corelated_criteria.occurrence = Occ(type=Occ._AT_LEAST, count=1, is_distinct=False)

        from .criteria import Occurrence as Occ
        query = self.ADDITIONAL_CRITERIA_LEFT_TEMPLATE if corelated_criteria.occurrence.type == Occ._AT_MOST or corelated_criteria.occurrence.count == 0 else self.ADDITIONAL_CRITERIA_INNER_TEMPLATE

        count_column_expression = "cc.event_id"

        builder_options = BuilderOptions()
        if corelated_criteria.occurrence.is_distinct:
            if corelated_criteria.occurrence.count_column is None:
                builder_options.additional_columns.append(CriteriaColumn.DOMAIN_CONCEPT)
                count_column_expression = f"cc.{CriteriaColumn.DOMAIN_CONCEPT.value}"
            else:
                builder_options.additional_columns.append(corelated_criteria.occurrence.count_column)
                count_column_expression = f"cc.{corelated_criteria.occurrence.count_column.value}"

        # If event_table is a query (not a temp table name like #qualified_events),
        # wrap it with observation period join to match reference SQL structure
        # Note: ignore_observation_period applies to window criteria, not the event table join
        # Check if event_table is a query (contains SELECT or FROM) vs a temp table name
        # Temp tables start with #, queries contain SELECT/FROM or are wrapped in parentheses
        is_temp_table = event_table.strip().startswith('#')
        is_query = not is_temp_table and ('SELECT' in event_table.upper() or 'FROM' in event_table.upper() or '(' in event_table)
        
        # Add observation period join to event table when it's a query (matches reference SQL)
        # BUT only if it doesn't already have op_start_date (to avoid double-wrapping)
        if is_query and 'op_start_date' not in event_table.lower():
            # event_table is a query without OP join, wrap it with observation period join
            # Remove outer parentheses if present to avoid double nesting
            clean_event_table = event_table.strip()
            # Remove one level of parentheses if present
            if clean_event_table.startswith('(') and clean_event_table.endswith(')'):
                # Count matching parentheses to ensure we remove only the outer pair
                paren_count = 0
                remove_outer = True
                for i, char in enumerate(clean_event_table):
                    if char == '(':
                        paren_count += 1
                    elif char == ')':
                        paren_count -= 1
                        if paren_count == 0 and i < len(clean_event_table) - 1:
                            # Found closing paren before the end - don't remove outer
                            remove_outer = False
                            break
                
                if remove_outer and paren_count == 0:
                    clean_event_table = clean_event_table[1:-1].strip()
            
            event_table = f"""(SELECT Q.person_id, Q.event_id, Q.start_date, Q.end_date, Q.visit_occurrence_id, OP.observation_period_start_date as op_start_date, OP.observation_period_end_date as op_end_date
FROM (
{clean_event_table}
) Q
JOIN @cdm_database_schema.OBSERVATION_PERIOD OP on Q.person_id = OP.person_id 
  and OP.observation_period_start_date <= Q.start_date and OP.observation_period_end_date >= Q.start_date
)"""


        query = self._get_windowed_criteria_query_internal(query, corelated_criteria, event_table, builder_options)

        # Occurrence criteria
        occurrence_criteria = f"HAVING COUNT({'DISTINCT ' if corelated_criteria.occurrence.is_distinct else ''}{count_column_expression}) {self.get_occurrence_operator(corelated_criteria.occurrence.type)} {corelated_criteria.occurrence.count}"

        query = query.replace("@occurrenceCriteria", occurrence_criteria)

        return query

    def get_criteria_sql(self, criteria: Criteria, options: Optional[BuilderOptions] = None) -> str:
        """Get criteria SQL for any criteria type.
        
        Java equivalent: Various getCriteriaSql methods
        """
        # Handle case where criteria is still a dict (shouldn't happen, but be defensive)
        if isinstance(criteria, dict):
            # Try to deserialize it - import here to avoid circular dependency issues
            from .criteria import (
                ConditionOccurrence as CO, DrugExposure as DE, ProcedureOccurrence as PO,
                VisitOccurrence as VO, Observation as O, Measurement as M, DeviceExposure as DevE,
                Specimen as S, Death as D, VisitDetail as VD, ObservationPeriod as OP,
                PayerPlanPeriod as PPP, LocationRegion as LR, ConditionEra as CE,
                DrugEra as DrE, DoseEra as DoE
            )

            criteria_type = None
            criteria_data = None
            for key in criteria.keys():
                criteria_type = key
                criteria_data = criteria[key]
                break

            # Note: criteria_data may be an empty dict {} which is valid
            # (e.g., {"ObservationPeriod": {}} means "any observation period")
            if criteria_type and criteria_data is not None:
                criteria_class_map = {
                    'ConditionOccurrence': CO,
                    'DrugExposure': DE,
                    'ProcedureOccurrence': PO,
                    'VisitOccurrence': VO,
                    'Observation': O,
                    'Measurement': M,
                    'DeviceExposure': DevE,
                    'Specimen': S,
                    'Death': D,
                    'VisitDetail': VD,
                    'ObservationPeriod': OP,
                    'PayerPlanPeriod': PPP,
                    'LocationRegion': LR,
                    'ConditionEra': CE,
                    'DrugEra': DrE,
                    'DoseEra': DoE,
                }

                if criteria_type in criteria_class_map:
                    try:
                        # Make a mutable copy to add defaults
                        criteria_data = dict(criteria_data) if criteria_data else {}
                        # Set default values for required fields that might be missing
                        if criteria_type == 'Measurement' and 'measurementTypeExclude' not in criteria_data:
                            criteria_data['measurementTypeExclude'] = False
                        if criteria_type == 'Observation' and 'observationTypeExclude' not in criteria_data:
                            criteria_data['observationTypeExclude'] = False
                        if criteria_type == 'ProcedureOccurrence' and 'procedureTypeExclude' not in criteria_data:
                            criteria_data['procedureTypeExclude'] = False
                        if criteria_type == 'DrugExposure' and 'drugTypeExclude' not in criteria_data:
                            criteria_data['drugTypeExclude'] = False
                        # Most criteria types require 'first' field
                        if 'first' not in criteria_data or criteria_data.get('first') is None:
                            criteria_data['first'] = False
                        criteria = criteria_class_map[criteria_type].model_validate(criteria_data, strict=False)
                    except Exception as e:
                        raise ValueError(f"Failed to deserialize criteria from dict: {criteria_type} - {e}")
                else:
                    raise ValueError(f"Unknown criteria type in dict: {criteria_type}")
            else:
                raise ValueError(f"Invalid criteria dict structure: {criteria}")

        # Import here to avoid circular dependency - use the already imported names
        if isinstance(criteria, ConditionOccurrence):
            return self._get_criteria_sql_from_builder(self.condition_occurrence_sql_builder, criteria, options)
        elif isinstance(criteria, Death):
            return self._get_criteria_sql_from_builder(self.death_sql_builder, criteria, options)
        elif isinstance(criteria, DeviceExposure):
            return self._get_criteria_sql_from_builder(self.device_exposure_sql_builder, criteria, options)
        elif isinstance(criteria, Measurement):
            return self._get_criteria_sql_from_builder(self.measurement_sql_builder, criteria, options)
        elif isinstance(criteria, Observation):
            return self._get_criteria_sql_from_builder(self.observation_sql_builder, criteria, options)
        elif isinstance(criteria, Specimen):
            return self._get_criteria_sql_from_builder(self.specimen_sql_builder, criteria, options)
        elif isinstance(criteria, VisitOccurrence):
            return self._get_criteria_sql_from_builder(self.visit_occurrence_sql_builder, criteria, options)
        elif isinstance(criteria, DrugExposure):
            return self._get_criteria_sql_from_builder(self.drug_exposure_sql_builder, criteria, options)
        elif isinstance(criteria, ProcedureOccurrence):
            return self._get_criteria_sql_from_builder(self.procedure_occurrence_sql_builder, criteria, options)
        elif isinstance(criteria, DrugEra):
            return self._get_criteria_sql_from_builder(self.drug_era_sql_builder, criteria, options)
        elif isinstance(criteria, ConditionEra):
            return self._get_criteria_sql_from_builder(self.condition_era_sql_builder, criteria, options)
        elif isinstance(criteria, DoseEra):
            return self._get_criteria_sql_from_builder(self.dose_era_sql_builder, criteria, options)
        elif isinstance(criteria, ObservationPeriod):
            return self._get_criteria_sql_from_builder(self.observation_period_sql_builder, criteria, options)
        elif isinstance(criteria, PayerPlanPeriod):
            return self._get_criteria_sql_from_builder(self.payer_plan_period_sql_builder, criteria, options)
        elif isinstance(criteria, VisitDetail):
            return self._get_criteria_sql_from_builder(self.visit_detail_sql_builder, criteria, options)
        elif isinstance(criteria, LocationRegion):
            return self._get_criteria_sql_from_builder(self.location_region_sql_builder, criteria, options)
        else:
            raise ValueError(f"Unsupported criteria type: {type(criteria)}")

    def _get_criteria_sql_from_builder(self, builder: Any, criteria: Criteria,
                                       options: Optional[BuilderOptions]) -> str:
        """Generic method to get criteria SQL from builder."""
        query = builder.get_criteria_sql_with_options(criteria, options)
        return self.process_correlated_criteria(query, criteria)

    def process_correlated_criteria(self, query: str, criteria: Criteria) -> str:
        """Process correlated criteria."""
        if hasattr(criteria, 'correlated_criteria') and criteria.correlated_criteria:
            query = self.wrap_criteria_query(query, criteria.correlated_criteria)
        return query




    # IGetEndStrategySqlDispatcher implementation
    def get_date_field_for_offset_strategy(self, date_field: str) -> str:
        """Get date field for offset strategy."""
        if date_field == "StartDate":
            return "start_date"
        elif date_field == "EndDate":
            return "end_date"
        return "start_date"

    def get_strategy_sql(self, strategy: Union[DateOffsetStrategy, CustomEraStrategy], event_table: str) -> str:
        """Get strategy SQL for date offset or custom era strategy."""
        if isinstance(strategy, DateOffsetStrategy):
            return self._get_date_offset_strategy_sql(strategy, event_table)
        elif isinstance(strategy, CustomEraStrategy):
            return self._get_custom_era_strategy_sql(strategy, event_table)
        else:
            raise ValueError(f"Unsupported strategy type: {type(strategy)}")

    def _get_date_offset_strategy_sql(self, strategy: DateOffsetStrategy, event_table: str) -> str:
        """Get strategy SQL for date offset strategy."""
        strategy_sql = self.DATE_OFFSET_STRATEGY_TEMPLATE.replace("@eventTable", event_table)
        strategy_sql = strategy_sql.replace("@offset", str(strategy.offset))
        strategy_sql = strategy_sql.replace("@dateField", self.get_date_field_for_offset_strategy(strategy.date_field))
        return strategy_sql

    def _get_custom_era_strategy_sql(self, strategy: CustomEraStrategy, event_table: str) -> str:
        """Get strategy SQL for custom era strategy."""
        if strategy.drug_codeset_id is None:
            raise RuntimeError("Drug Codeset ID cannot be NULL.")

        drug_exposure_end_date_expression = self.DEFAULT_DRUG_EXPOSURE_END_DATE_EXPRESSION

        strategy_sql = self.CUSTOM_ERA_STRATEGY_TEMPLATE.replace("@eventTable", event_table)
        strategy_sql = strategy_sql.replace("@drugCodesetId", str(strategy.drug_codeset_id))
        strategy_sql = strategy_sql.replace("@gapDays", str(strategy.gap_days))
        strategy_sql = strategy_sql.replace("@offset", str(strategy.offset))
        strategy_sql = strategy_sql.replace("@drugExposureEndDateExpression", drug_exposure_end_date_expression)

        return strategy_sql

    def _get_additional_columns(self, columns: List[CriteriaColumn], table_alias: str) -> str:
        """Get additional columns for SQL query."""
        if not columns:
            return ""

        column_mappings = {
            CriteriaColumn.DOMAIN_CONCEPT: "domain_concept"
        }

        column_clauses = []
        for column in columns:
            if column in column_mappings:
                column_clauses.append(f"{table_alias}{column_mappings[column]}")
            else:
                column_clauses.append(f"{table_alias}{column.value}")

        return ", ".join(column_clauses)

