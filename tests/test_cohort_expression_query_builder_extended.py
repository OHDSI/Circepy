
import unittest
from unittest.mock import MagicMock, patch
from circe.cohortdefinition import CohortExpressionQueryBuilder
from circe.cohortdefinition.criteria import (
    WindowedCriteria, CorelatedCriteria, Occurrence, CriteriaGroup,
    Window, ConditionOccurrence, Death, VisitOccurrence, VisitDetail,
    PayerPlanPeriod, ProcedureOccurrence, DrugExposure, DrugEra,
    ConditionEra, DoseEra, Measurement, Observation, DeviceExposure,
    Specimen, LocationRegion, ObservationPeriod
)
from circe.cohortdefinition.builders.utils import BuilderOptions, CriteriaColumn

class TestCohortExpressionQueryBuilderExtended(unittest.TestCase):

    def setUp(self):
        self.builder = CohortExpressionQueryBuilder()

    def test_get_criteria_sql_dispatch(self):
        """Test that get_criteria_sql correctly dispatches to the appropriate builder via registry."""
        
        # Define test cases: (criteria_instance, criteria_name)
        test_cases = [
            (ConditionOccurrence(first=True, codeset_id=1), "ConditionOccurrence"),
            (Death(first=True, codeset_id=1), "Death"),
            (VisitOccurrence(first=True, codeset_id=1), "VisitOccurrence"),
            (VisitDetail(first=True, codeset_id=1), "VisitDetail"),
            (PayerPlanPeriod(first=True), "PayerPlanPeriod"),
            (DrugExposure(first=True, codeset_id=1), "DrugExposure"),
            (ProcedureOccurrence(first=True, codeset_id=1), "ProcedureOccurrence"),
            (DeviceExposure(first=True, codeset_id=1, device_type_exclude=False), "DeviceExposure"),
            (Measurement(first=True, codeset_id=1, measurement_type_exclude=False), "Measurement"),
            (Observation(first=True, codeset_id=1, observation_type_exclude=False), "Observation"),
            (Specimen(first=True, codeset_id=1, specimen_type_exclude=False), "Specimen"),
            (ObservationPeriod(first=True), "ObservationPeriod"),
            (LocationRegion(codeset_id=1), "LocationRegion"),
            (ConditionEra(first=True, codeset_id=1), "ConditionEra"),
            (DrugEra(first=True, codeset_id=1), "DrugEra"),
            (DoseEra(first=True, codeset_id=1), "DoseEra"),
        ]

        for criteria, name in test_cases:
            with self.subTest(msg=f"Testing dispatch for {name}"):
                sql = self.builder.get_criteria_sql(criteria)
                self.assertIsInstance(sql, str)
                self.assertTrue(len(sql) > 0, f"Empty SQL for {name}")

    def test_get_criteria_sql_from_dict(self):
        """Test get_criteria_sql handling dictionary input (deserialization)."""
        criteria_dict = {"ConditionOccurrence": {"CodesetId": 1, "First": True}}
        
        sql = self.builder.get_criteria_sql(criteria_dict)
        
        self.assertIsInstance(sql, str)
        self.assertTrue(len(sql) > 0)

    def test_get_windowed_criteria_query_basic(self):
        """Test get_windowed_criteria_query with basic configuration."""
        criteria = WindowedCriteria(
            criteria=ConditionOccurrence(first=True, codeset_id=1),
            start_window=Window(start={'days': 0, 'coeff': -1}, end={'days': 0, 'coeff': 1}),
            ignore_observation_period=False
        )
        # Mock criteria acceptance
        with patch.object(ConditionOccurrence, 'accept', return_value="SELECT * FROM Criteria") as mock_accept:
            sql = self.builder.get_windowed_criteria_query(criteria, "#events")
            
            self.assertIn("SELECT * FROM Criteria", sql)
            self.assertIn("#events", sql)
            self.assertIn("A.START_DATE >= P.OP_START_DATE", sql) # Check OP check
            self.assertIn("A.START_DATE >=", sql) # Window logic

    def test_get_windowed_criteria_query_ignore_op(self):
        """Test get_windowed_criteria_query with ignore_observation_period=True."""
        criteria = WindowedCriteria(
            criteria=ConditionOccurrence(first=True, codeset_id=1),
            start_window=Window(start={'days': 0, 'coeff': -1}, end={'days': 0, 'coeff': 1}),
            ignore_observation_period=True # Important
        )
        with patch.object(ConditionOccurrence, 'accept', return_value="SELECT * FROM Criteria"):
            sql = self.builder.get_windowed_criteria_query(criteria, "#events")
            self.assertNotIn("A.START_DATE >= P.OP_START_DATE AND A.START_DATE <= P.OP_END_DATE", sql)

    def test_get_windowed_criteria_query_restrict_visit(self):
        """Test get_windowed_criteria_query with restrict_visit=True."""
        criteria = WindowedCriteria(
            criteria=ConditionOccurrence(first=True, codeset_id=1),
            start_window=Window(start={'days': 0, 'coeff': -1}, end={'days': 0, 'coeff': 1}),
            restrict_visit=True
        )
        with patch.object(ConditionOccurrence, 'accept', return_value="SELECT * FROM Criteria"):
            sql = self.builder.get_windowed_criteria_query(criteria, "#events")
            self.assertIn("A.visit_occurrence_id = P.visit_occurrence_id", sql)

    def test_get_corelated_criteria_query_formatted_event_table(self):
        """Test get_corelated_criteria_query wraps event query string correctly."""
        # When event_table is a query string (SELECT ...), it should be wrapped with OP join
        cc = CorelatedCriteria(
            criteria=ConditionOccurrence(first=True, codeset_id=1),
            occurrence=Occurrence(type=1, count=1)
        )
        
        event_query = "SELECT person_id, event_id, start_date, end_date FROM #table"
        
        with patch.object(ConditionOccurrence, 'accept', return_value="SELECT * FROM Criteria"):
            sql = self.builder.get_corelated_criteria_query(cc, event_query)
            
            # Should inject observation period join
            self.assertIn("JOIN @cdm_database_schema.OBSERVATION_PERIOD OP", sql)
            self.assertIn("SELECT Q.person_id", sql)

    def test_get_criteria_group_query_at_least(self):
        """Test get_criteria_group_query with AT_LEAST type."""
        group = CriteriaGroup(
            type="AT_LEAST",
            count=2,
            criteria_list=[
                CorelatedCriteria(criteria=ConditionOccurrence(first=True, codeset_id=1),
                                occurrence=Occurrence(type=2, count=1))
            ]
        )
        
        # Mock get_corelated_criteria_query
        self.builder.get_corelated_criteria_query = MagicMock(return_value="SELECT 1")
        
        sql = self.builder.get_criteria_group_query(group, "#events")
        
        self.assertIn("HAVING COUNT(index_id) >= 2", sql)
        self.assertIn("INNER JOIN", sql) # Expect INNER JOIN for AT_LEAST > 0

    def test_get_criteria_group_query_at_most(self):
        """Test get_criteria_group_query with AT_MOST type."""
        group = CriteriaGroup(
            type="AT_MOST",
            count=2,
            criteria_list=[]
        )
        group.criteria_list.append(CorelatedCriteria(criteria=ConditionOccurrence(first=True, codeset_id=1), occurrence=Occurrence(type=2, count=1)))
        
        self.builder.get_corelated_criteria_query = MagicMock(return_value="SELECT 1")
        
        sql = self.builder.get_criteria_group_query(group, "#events")
        
        self.assertIn("HAVING COUNT(index_id) <= 2", sql)
        self.assertIn("LEFT JOIN", sql) # AT_MOST requires LEFT JOIN

    def test_wrap_criteria_query(self):
        """Test wrap_criteria_query structure."""
        group = CriteriaGroup(type="ALL", criteria_list=[])
        base_query = "SELECT * FROM @cdm_database_schema.CONDITION_OCCURRENCE"
        
        sql = self.builder.wrap_criteria_query(base_query, group)
        
        self.assertIn("JOIN @cdm_database_schema.OBSERVATION_PERIOD OP", sql)
        self.assertIn("JOIN (", sql) # Group join
        self.assertIn(") AC on AC.person_id = pe.person_id", sql)

if __name__ == '__main__':
    unittest.main()
