import unittest
from circe.cohortdefinition.builders.visit_occurrence import VisitOccurrenceSqlBuilder
from circe.cohortdefinition.builders.utils import BuilderOptions, CriteriaColumn
from circe.cohortdefinition.criteria import VisitOccurrence
from circe.cohortdefinition.core import DateRange, NumericRange, ConceptSetSelection

class TestVisitOccurrenceSqlBuilderParity(unittest.TestCase):
    def setUp(self):
        self.builder = VisitOccurrenceSqlBuilder()

    def test_get_query_template(self):
        template = self.builder.get_query_template()
        self.assertIn("FROM @cdm_database_schema.VISIT_OCCURRENCE vo", template)
        self.assertIn("@codesetClause", template)
        self.assertIn("@ordinalExpression", template)

    def test_get_default_columns(self):
        columns = self.builder.get_default_columns()
        self.assertEqual(columns, {CriteriaColumn.START_DATE, CriteriaColumn.END_DATE, CriteriaColumn.VISIT_ID})

    def test_get_table_column_for_criteria_column(self):
        self.assertEqual(self.builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT), "C.visit_concept_id")
        self.assertEqual(self.builder.get_table_column_for_criteria_column(CriteriaColumn.DURATION), "DATEDIFF(d, C.start_date, C.end_date)")
        with self.assertRaises(ValueError):
            self.builder.get_table_column_for_criteria_column(CriteriaColumn.VALUE_AS_NUMBER)

    def test_get_criteria_sql_basic(self):
        criteria = VisitOccurrence()
        sql = self.builder.get_criteria_sql(criteria)
        self.assertIn("C.person_id, C.visit_occurrence_id as event_id, C.start_date, C.end_date", sql)
        self.assertIn("vo.person_id,vo.visit_occurrence_id,vo.visit_concept_id", sql)
        self.assertIn("vo.visit_start_date as start_date, vo.visit_end_date as end_date", sql)

    def test_get_criteria_sql_with_codeset(self):
        criteria = VisitOccurrence(codeset_id=123)
        sql = self.builder.get_criteria_sql(criteria)
        self.assertIn("JOIN #Codesets cs on (vo.visit_concept_id = cs.concept_id and cs.codeset_id = 123)", sql)

    def test_get_criteria_sql_with_date_ranges(self):
        criteria = VisitOccurrence(
            occurrence_start_date=DateRange(op="gt", value="2020-01-01"),
            occurrence_end_date=DateRange(op="lt", value="2021-01-01")
        )
        sql = self.builder.get_criteria_sql(criteria)
        self.assertIn("C.start_date > DATEFROMPARTS(2020, 1, 1)", sql)
        self.assertIn("C.end_date < DATEFROMPARTS(2021, 1, 1)", sql)

    def test_get_criteria_sql_with_visit_type(self):
        # Using codeset for visit type
        criteria = VisitOccurrence(visit_type_cs=ConceptSetSelection(codeset_id=456))
        sql = self.builder.get_criteria_sql(criteria)
        self.assertIn("vo.visit_type_concept_id", sql) # Added to select
        self.assertIn("C.visit_type_concept_id in (select concept_id from #Codesets where codeset_id = 456)", sql)

    def test_get_criteria_sql_with_visit_length(self):
        criteria = VisitOccurrence(visit_length=NumericRange(op="gt", value=5))
        sql = self.builder.get_criteria_sql(criteria)
        self.assertIn("DATEDIFF(d,C.start_date, C.end_date) > 5", sql)

    def test_get_criteria_sql_with_age(self):
        criteria = VisitOccurrence(age=NumericRange(op="gte", value=18))
        sql = self.builder.get_criteria_sql(criteria)
        self.assertIn("JOIN @cdm_database_schema.PERSON P on C.person_id = P.person_id", sql)
        self.assertIn("YEAR(C.start_date) - P.year_of_birth >= 18", sql)

    def test_get_criteria_sql_with_provider_specialty(self):
        criteria = VisitOccurrence(provider_specialty_cs=ConceptSetSelection(codeset_id=789))
        sql = self.builder.get_criteria_sql(criteria)
        self.assertIn("vo.provider_id", sql) # Added to select
        self.assertIn("LEFT JOIN @cdm_database_schema.PROVIDER PR on C.provider_id = PR.provider_id", sql)
        self.assertIn("PR.specialty_concept_id in (select concept_id from #Codesets where codeset_id = 789)", sql)

    def test_get_criteria_sql_with_place_of_service(self):
        criteria = VisitOccurrence(place_of_service_cs=ConceptSetSelection(codeset_id=101))
        sql = self.builder.get_criteria_sql(criteria)
        self.assertIn("vo.care_site_id", sql) # Added to select
        self.assertIn("JOIN @cdm_database_schema.CARE_SITE CS on C.care_site_id = CS.care_site_id", sql)
        self.assertIn("CS.place_of_service_concept_id in (select concept_id from #Codesets where codeset_id = 101)", sql)

    def test_get_criteria_sql_with_place_of_service_location(self):
        criteria = VisitOccurrence(place_of_service_location=202)
        sql = self.builder.get_criteria_sql(criteria)
        self.assertIn("JOIN @cdm_database_schema.LOCATION_HISTORY LH on LH.entity_id = C.care_site_id AND LH.domain_id = 'CARE_SITE'", sql)
        self.assertIn("JOIN @cdm_database_schema.LOCATION LOC on LOC.location_id = LH.location_id", sql)
        self.assertIn("JOIN #Codesets cs on (LOC.region_concept_id = cs.concept_id and cs.codeset_id = 202)", sql)

    def test_get_criteria_sql_with_first(self):
        criteria = VisitOccurrence(first=True)
        sql = self.builder.get_criteria_sql(criteria)
        self.assertIn(", row_number() over (PARTITION BY vo.person_id ORDER BY vo.visit_start_date, vo.visit_occurrence_id) as ordinal", sql)
        self.assertIn("C.ordinal = 1", sql)

if __name__ == "__main__":
    unittest.main()
