"""
SQL Generation Engine for the Phenotype Evaluation Framework.
"""

from typing import Optional
from circe.cohortdefinition.cohort_expression_query_builder import CohortExpressionQueryBuilder
from circe.evaluation.models import EvaluationRubric


class EvaluationQueryBuilder:
    """
    Translates an EvaluationRubric into T-SQL results.
    """

    def __init__(self):
        self._cohort_builder = CohortExpressionQueryBuilder()

    def get_ddl(self, results_schema: str = "@results_database_schema", target_table: str = "cohort_rubric") -> str:
        """
        Generates T-SQL for creating the cohort_rubric table.
        Uses a DROP IF EXISTS then CREATE approach for better SqlRender compatibility.
        """
        table_full_name = f"{results_schema}.{target_table}"
        return f"""
IF OBJECT_ID('{table_full_name}', 'U') IS NOT NULL 
    DROP TABLE {table_full_name};

CREATE TABLE {table_full_name} (
    ruleset_id INT NOT NULL,
    cohort_definition_id BIGINT NULL,
    subject_id BIGINT NOT NULL, 
    index_date DATE NOT NULL,
    rule_id INT NOT NULL, 
    score FLOAT NOT NULL
);
"""


    def build_query(
        self, 
        rubric: EvaluationRubric, 
        ruleset_id: int, 
        index_event_table: str = "#evaluation_index_events",
        cdm_schema: str = "@cdm_database_schema",
        vocabulary_schema: str = "@vocabulary_database_schema",
        results_schema: str = "@results_database_schema",
        target_table: str = "cohort_rubric",
        subject_id_field: str = "subject_id",
        index_date_field: str = "cohort_start_date",
        cohort_id_field: str = "cohort_definition_id",
        cohort_id: Optional[int] = None,
        include_cohort_id: bool = True,
    ) -> str:
        """
        Generates T-SQL to produce a normalized evaluation results table.
        
        The results are inserted into the target table (default: cohort_rubric).
        The output columns are: ruleset_id, cohort_definition_id, subject_id, index_date, rule_id, score.

        Args:
            rubric: The EvaluationRubric definition.
            ruleset_id: Identifier for this rubric/evaluation set.
            index_event_table: Temp table containing (subject_id, index_date).
            cdm_schema: SQL parameter for the CDM schema.
            vocabulary_schema: SQL parameter for the vocabulary schema.
            results_schema: SQL parameter for the results schema.
            target_table: The table to populate with evaluation results.
            subject_id_field: Name of the field for subject ID (default: subject_id).
            index_date_field: Name of the field for index date (default: cohort_start_date).
            cohort_id_field: Name of the field for cohort ID (default: cohort_definition_id).
            cohort_id: Optional single cohort ID to filter.
            include_cohort_id: Flag to include cohort_id in query and results.

        Returns:
            A string containing the T-SQL query.
        """
        # 1. Generate Codesets
        codeset_sql = self._cohort_builder.get_codeset_query(rubric.concept_sets)
        codeset_sql = codeset_sql.replace("@vocabulary_database_schema", vocabulary_schema)
        
        # 2. Define the Index Event Table Expression for CIRCE
        # CIRCE WindowedCriteria/CorrelatedCriteria expect a table 'P' with:
        # person_id, event_id, start_date, end_date, op_start_date, op_end_date
        
        where_clauses = []
        if cohort_id is not None and include_cohort_id:
            where_clauses.append(f"E.{cohort_id_field} = {cohort_id}")

        where_stmt = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        index_event_subquery = f"""
        (
          SELECT DISTINCT
            E.{subject_id_field} as person_id, 
            0 as event_id, 
            E.{index_date_field} as start_date, 
            E.{index_date_field} as end_date,
            OP.observation_period_start_date as OP_START_DATE,
            OP.observation_period_end_date as OP_END_DATE
          FROM {index_event_table} E
          JOIN {cdm_schema}.observation_period OP ON E.{subject_id_field} = OP.person_id 
            AND E.{index_date_field} >= OP.observation_period_start_date 
            AND E.{index_date_field} <= OP.observation_period_end_date
          {where_stmt}
        )"""


        rule_queries = []
        for rule in rubric.rules:
            # Generate the Criteria Group SQL
            # This handles temporal windows and occurrences relative to the index_date
            # as well as complex logical grouping (AND/OR).
            cg_sql = self._cohort_builder.get_criteria_group_query(rule.expression, index_event_subquery)
            cg_sql = cg_sql.replace("@indexId", str(rule.rule_id))
            cg_sql = cg_sql.replace("@cdm_database_schema", cdm_schema)
            
            # The Criteria Group query returns (index_id, person_id, event_id) for matched events.
            # We need to join back to the index events to get the start_date for proper matching.
            rule_comment = f"-- Rule {rule.rule_id}: {rule.name} (weight: {rule.weight}, polarity: {rule.polarity})"
            if rule.category:
                rule_comment += f" [Category: {rule.category}]"

            if include_cohort_id:
                select_columns = f"""
              {ruleset_id} as ruleset_id,
              E.{cohort_id_field} as cohort_definition_id,
              E.{subject_id_field} as subject_id,
              E.{index_date_field} as index_date,
              {rule.rule_id} as rule_id,
              CAST(COALESCE(R.score, 0) AS FLOAT) as score"""
            else:
                select_columns = f"""
              {ruleset_id} as ruleset_id,
              E.{subject_id_field} as subject_id,
              E.{index_date_field} as index_date,
              {rule.rule_id} as rule_id,
              CAST(COALESCE(R.score, 0) AS FLOAT) as score"""

            rule_query = f"""
            {rule_comment}
            SELECT DISTINCT{select_columns}
            FROM {index_event_table} E
            LEFT JOIN (
              SELECT CG.person_id, P.start_date, {rule.weight} * {rule.polarity} as score
              FROM (
                {cg_sql}
              ) CG
              JOIN {index_event_subquery} P ON CG.person_id = P.person_id
            ) R ON E.{subject_id_field} = R.person_id
            AND E.{index_date_field} = R.start_date
            {where_stmt}
            """
            rule_queries.append(rule_query)

        final_union = "\nUNION ALL\n".join(rule_queries)
        
        # Wrap everything in an INSERT INTO statement
        target_full_name = f"{results_schema}.{target_table}"

        delete_filter = f"WHERE ruleset_id = {ruleset_id}"
        if include_cohort_id and cohort_id is not None:
            delete_filter += f" AND cohort_definition_id = {cohort_id}"

        insert_columns = (
            "ruleset_id, cohort_definition_id, subject_id, index_date, rule_id, score"
            if include_cohort_id
            else "ruleset_id, subject_id, index_date, rule_id, score"
        )

        sql = f"""
        {codeset_sql}
        
        DELETE FROM {target_full_name} {delete_filter};
        INSERT INTO {target_full_name} ({insert_columns})
        {final_union};
"""
        
        # Strip T-SQL specific bits that might not be handled by all translators
        sql = sql.replace("UPDATE STATISTICS #Codesets;", "")
        if sql.strip() and not sql.strip().endswith(";"):
            sql = sql.strip() + ";"
        
        return sql

