import unittest

from circe.cohortdefinition import (
    BuildExpressionQueryOptions,
    CohortExpression,
    CohortExpressionQueryBuilder,
    ConditionOccurrence,
    CorelatedCriteria,
    CriteriaGroup,
    Death,
    InclusionRule,
    Observation,
    ObservationFilter,
    PrimaryCriteria,
    ResultLimit,
)


class TestCohortExpressionQueryBuilderCoverage(unittest.TestCase):
    """Additional tests for valid coverage of CohortExpressionQueryBuilder."""

    def setUp(self):
        self.builder = CohortExpressionQueryBuilder()
        self.options = BuildExpressionQueryOptions()
        self.options.cdm_schema = "cdm"
        self.options.target_table = "cohort"
        self.options.result_schema = "results"
        self.options.cohort_id_field_name = "cohort_definition_id"
        self.options.cohort_id = 1

    def test_inclusion_analysis_section(self):
        """Test _build_inclusion_analysis_section with stats generation."""
        # Create expression with inclusion rules
        expression = CohortExpression(
            primary_criteria=PrimaryCriteria(
                criteria_list=[ConditionOccurrence(codeset_id=1)],
                observation_window=ObservationFilter(prior_days=0, post_days=0),
                primary_limit=ResultLimit(type="All"),
            ),
            inclusion_rules=[
                InclusionRule(
                    name="Rule 1",
                    expression=CriteriaGroup(
                        type="ALL",
                        criteria_list=[
                            CorelatedCriteria(
                                criteria=Death(codeset_id=2, first=True),
                                start_window=None,
                                occurrence=None,
                            )
                        ],
                    ),
                ),
                InclusionRule(
                    name="Rule 2",
                    expression=CriteriaGroup(type="ALL", criteria_list=[]),
                ),
            ],
        )
        # Enable stats
        self.options.generate_stats = True

        # Build query
        sql = self.builder.build_expression_query(expression, self.options).lower()

        # Verify inclusion analysis components
        self.assertIn("into #inclusion_rules", sql)
        self.assertIn("into #best_events", sql)
        self.assertIn("cohort_inclusion_result", sql)
        self.assertIn("cohort_inclusion_stats", sql)
        self.assertIn("cohort_summary_stats", sql)
        self.assertIn("drop table #best_events", sql)
        # Verify 2 rules are handled
        self.assertIn("select cast(0 as int) as rule_sequence", sql)
        self.assertIn("select cast(1 as int) as rule_sequence", sql)

    def test_censoring_events_query(self):
        """Test generation of censoring events query."""
        expression = CohortExpression(
            primary_criteria=PrimaryCriteria(
                criteria_list=[ConditionOccurrence(codeset_id=1)],
                observation_window=ObservationFilter(prior_days=0, post_days=0),
                primary_limit=ResultLimit(type="All"),
            ),
            censoring_criteria=[
                Death(codeset_id=100, first=True),
                Observation(codeset_id=200, first=True, observation_type_exclude=False),
            ],
        )

        sql = self.builder.build_expression_query(expression, self.options).lower()

        # Verify censoring logic
        self.assertIn("-- censor events", sql)
        self.assertIn("select i.event_id, i.person_id", sql.lower())  # CENSORING_QUERY_TEMPLATE
        # Should call get_criteria_sql for checking death/obs tables
        self.assertIn("from cdm.death", sql)
        self.assertIn("from cdm.observation", sql)
        # Verify union if multiple censoring criteria
        self.assertIn("union all", sql)  # between the two censoring queries

    def test_wrap_criteria_query(self):
        """Test wrapping a criteria query with group logic."""
        group = CriteriaGroup(type="ALL", criteria_list=[])
        base_query = "SELECT person_id, event_id FROM #test"

        wrapped = self.builder.wrap_criteria_query(base_query, group)

        # Check structure
        self.assertIn("SELECT Q.person_id", wrapped)
        self.assertIn("JOIN @cdm_database_schema.OBSERVATION_PERIOD OP", wrapped)
        self.assertIn("JOIN (", wrapped)  # Expect join to group query
        self.assertIn(") AC on AC.person_id = pe.person_id", wrapped)

    def test_limits_and_sorts(self):
        """Test various limit and sort configurations."""
        # 1. Primary Limit: LAST
        expression = CohortExpression(
            primary_criteria=PrimaryCriteria(
                criteria_list=[ConditionOccurrence(codeset_id=1)],
                observation_window=ObservationFilter(prior_days=0, post_days=0),
                primary_limit=ResultLimit(type="Last"),
            ),
            # 2. Qualified Limit: LAST
            qualified_limit=ResultLimit(type="Last"),
            # 3. Expression Limit: LAST
            expression_limit=ResultLimit(type="Last"),
            additional_criteria=CriteriaGroup(
                type="ALL", criteria_list=[]
            ),  # needed for qualified limit logic
        )

        sql = self.builder.build_expression_query(expression, self.options)

        # Primary sort verification - check lowercase order by
        self.assertIn("order by pe.start_date DESC", sql)  # @QualifiedEventSort

        # Qualified limit logic
        # If additional criteria + qualified limit != ALL -> WHERE QE.ordinal = 1
        self.assertIn("WHERE QE.ordinal = 1", sql)

        # Expression limit logic
        # If expression limit != ALL -> WHERE Results.ordinal = 1
        self.assertIn("WHERE Results.ordinal = 1", sql)
        # Inclusion sort
        self.assertIn("order by start_date DESC", sql)  # @IncludedEventSort

    def test_limits_and_sorts_first(self):
        """Test limits and sorts with FIRST/ALL."""
        expression = CohortExpression(
            primary_criteria=PrimaryCriteria(
                criteria_list=[ConditionOccurrence(codeset_id=1)],
                observation_window=ObservationFilter(prior_days=0, post_days=0),
                primary_limit=ResultLimit(type="First"),
            ),
            qualified_limit=ResultLimit(type="First"),
            expression_limit=ResultLimit(type="First"),
            additional_criteria=CriteriaGroup(type="ALL", criteria_list=[]),
        )

        sql = self.builder.build_expression_query(expression, self.options)

        self.assertIn("order by pe.start_date ASC", sql)
        self.assertIn("WHERE QE.ordinal = 1", sql)
        self.assertIn("WHERE Results.ordinal = 1", sql)

    def test_inclusion_rules_empty(self):
        """Test explicitly with empty inclusion rules list (edge case branching)."""
        expression = CohortExpression(
            primary_criteria=PrimaryCriteria(
                criteria_list=[ConditionOccurrence(codeset_id=1)],
                observation_window=ObservationFilter(prior_days=0, post_days=0),
                primary_limit=ResultLimit(type="All"),
            ),
            inclusion_rules=[],
        )
        self.options.generate_stats = True

        sql = self.builder.build_expression_query(expression, self.options)

        # Should create empty inclusion events table
        self.assertIn("CREATE TABLE #inclusion_events", sql)
        # Should NOT have inclusion analysis
        self.assertNotIn(
            "INTO #inclusion_rules", sql
        )  # Should be skipped because rule_total == 0 check in _build_inclusion_analysis_section

    def test_rule_total_replacement(self):
        """Verify @ruleTotal replacement handles 0 correctly."""
        expression = CohortExpression(
            primary_criteria=PrimaryCriteria(
                criteria_list=[ConditionOccurrence(codeset_id=1)],
                observation_window=ObservationFilter(prior_days=0, post_days=0),
                primary_limit=ResultLimit(type="All"),
            ),
            inclusion_rules=[],
        )

        sql = self.builder.build_expression_query(expression, self.options)
        # In COHORT_QUERY_TEMPLATE: {1 != 0 & @ruleTotal != 0}
        # If 0 rules, this check fails and skips analysis block logic inside the template
        # We just want to ensure no crash
        self.assertIsNotNone(sql)


if __name__ == "__main__":
    unittest.main()
