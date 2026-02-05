"""
SQL Generation Engine for the Phenotype Evaluation Framework.
"""

from typing import List, Optional
from circe.cohortdefinition.cohort_expression_query_builder import CohortExpressionQueryBuilder
from circe.evaluation.models import EvaluationRubric, EvaluationRule


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
        target_table: str = "cohort_rubric"
    ) -> str:
        """
        Generates T-SQL to produce a normalized evaluation results table.
        
        The results are inserted into the target table (default: cohort_rubric).
        The output columns are: ruleset_id, subject_id, index_date, rule_id, score.
        
        Args:
            rubric: The EvaluationRubric definition.
            ruleset_id: Identifier for this rubric/evaluation set.
            index_event_table: Temp table containing (subject_id, index_date).
            cdm_schema: SQL parameter for the CDM schema.
            vocabulary_schema: SQL parameter for the vocabulary schema.
            results_schema: SQL parameter for the results schema.
            target_table: The table to populate with evaluation results.
            
        Returns:
            A string containing the T-SQL query.
        """
        # 1. Generate Codesets
        codeset_sql = self._cohort_builder.get_codeset_query(rubric.concept_sets)
        codeset_sql = codeset_sql.replace("@vocabulary_database_schema", vocabulary_schema)
        
        # 2. Define the Index Event Table Expression for CIRCE
        # CIRCE WindowedCriteria/CorrelatedCriteria expect a table 'P' with:
        # person_id, event_id, start_date, end_date, op_start_date, op_end_date
        index_event_subquery = f"""
        (
          SELECT 
            E.subject_id as person_id, 
            0 as event_id, 
            E.index_date as start_date, 
            E.index_date as end_date,
            OP.observation_period_start_date as OP_START_DATE,
            OP.observation_period_end_date as OP_END_DATE
          FROM {index_event_table} E
          JOIN {cdm_schema}.observation_period OP ON E.subject_id = OP.person_id 
            AND E.index_date >= OP.observation_period_start_date 
            AND E.index_date <= OP.observation_period_end_date
        )"""


        rule_queries = []
        for rule in rubric.rules:
            # Generate the Correlated Criteria SQL
            # This handles temporal windows and occurrences relative to the index_date
            cc_sql = self._cohort_builder.get_corelated_criteria_query(rule.criteria, index_event_subquery)
            cc_sql = cc_sql.replace("@indexId", str(rule.rule_id))
            cc_sql = cc_sql.replace("@cdm_database_schema", cdm_schema)
            
            # The CC query returns (index_id, person_id, event_id) for matched events.
            # We wrap it to return the weighted score for the subject.
            rule_query = f"""
            SELECT 
              {ruleset_id} as ruleset_id,
              E.subject_id,
              E.index_date,
              {rule.rule_id} as rule_id,
              CAST(COALESCE(R.score, 0) AS FLOAT) as score
            FROM {index_event_table} E
            LEFT JOIN (
              SELECT person_id, {rule.weight} * {rule.polarity} as score
              FROM (
                {cc_sql}
              ) InnerR
            ) R ON E.subject_id = R.person_id
            """
            rule_queries.append(rule_query)

        final_union = "\nUNION ALL\n".join(rule_queries)
        
        # Wrap everything in an INSERT INTO statement
        target_full_name = f"{results_schema}.{target_table}"
        
        sql = f"""
{codeset_sql}

DELETE FROM {target_full_name} WHERE ruleset_id = {ruleset_id};
INSERT INTO {target_full_name} (ruleset_id, subject_id, index_date, rule_id, score)
{final_union};
"""
        
        # Strip T-SQL specific bits that might not be handled by all translators
        sql = sql.replace("UPDATE STATISTICS #Codesets;", "")
        if sql.strip() and not sql.strip().endswith(";"):
            sql = sql.strip() + ";"
        
        return sql

