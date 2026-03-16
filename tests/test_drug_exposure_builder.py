import unittest

from circe.cohortdefinition.builders.drug_exposure import DrugExposureSqlBuilder
from circe.cohortdefinition.builders.utils import CriteriaColumn
from circe.cohortdefinition.core import (
    ConceptSetSelection,
    DateAdjustment,
    DateRange,
    NumericRange,
    TextFilter,
)
from circe.cohortdefinition.criteria import DrugExposure
from circe.vocabulary.concept import Concept


class TestDrugExposureSqlBuilder(unittest.TestCase):
    
    def setUp(self):
        self.builder = DrugExposureSqlBuilder()
        
    def test_get_default_columns(self):
        columns = self.builder.get_default_columns()
        self.assertIn(CriteriaColumn.START_DATE, columns)
        self.assertIn(CriteriaColumn.END_DATE, columns)
        self.assertIn(CriteriaColumn.VISIT_ID, columns)
        
    def test_get_table_column_for_criteria_column(self):
        self.assertEqual(self.builder.get_table_column_for_criteria_column(CriteriaColumn.DOMAIN_CONCEPT), "C.drug_concept_id")
        self.assertEqual(self.builder.get_table_column_for_criteria_column(CriteriaColumn.DURATION), "(DATEDIFF(d,C.start_date, C.end_date))")
        self.assertEqual(self.builder.get_table_column_for_criteria_column(CriteriaColumn.START_DATE), "C.start_date")
        self.assertEqual(self.builder.get_table_column_for_criteria_column(CriteriaColumn.END_DATE), "C.end_date")
        self.assertEqual(self.builder.get_table_column_for_criteria_column(CriteriaColumn.VISIT_ID), "C.visit_occurrence_id")
        
    def test_resolve_select_clauses_basic(self):
        criteria = DrugExposure(codeset_id=1, first=False)
        select_cols = self.builder.resolve_select_clauses(criteria)
        self.assertIn("de.person_id", select_cols)
        self.assertIn("de.drug_exposure_id", select_cols)
        
    def test_resolve_select_clauses_with_attributes(self):
        """Test selection of additional columns based on attributes used."""
        criteria = DrugExposure(
            codeset_id=1,
            first=False,
            drug_type=[Concept(concept_id=1, concept_name="Type")],
            stop_reason=TextFilter(text="Reason", op="eq"),
            route_concept=[Concept(concept_id=2, concept_name="Route")],
            provider_specialty=[Concept(concept_id=3, concept_name="Spec")]
        )
        select_cols = self.builder.resolve_select_clauses(criteria)
        self.assertIn("de.drug_type_concept_id", select_cols)
        self.assertIn("de.stop_reason", select_cols)
        self.assertIn("de.route_concept_id", select_cols)
        self.assertIn("de.provider_id", select_cols)
        
    def test_resolve_select_clauses_date_adjustment(self):
        criteria = DrugExposure(
            codeset_id=1,
            first=False,
            date_adjustment=DateAdjustment(start_with="start_date", end_with="start_date", start_offset=1, end_offset=1)
        )
        select_cols = self.builder.resolve_select_clauses(criteria)
        # Verify custom select logic replaces the default one
        self.assertTrue(any("DATEADD(day,1, de.drug_exposure_start_date)" in col for col in select_cols))
        
    def test_resolve_join_clauses(self):
        criteria = DrugExposure(
            codeset_id=1,
            first=False,
            age=NumericRange(value=20, op="gt"),
            visit_type=[Concept(concept_id=1, concept_name="Visit")],
            provider_specialty=[Concept(concept_id=2, concept_name="Spec")]
        )
        joins = self.builder.resolve_join_clauses(criteria)
        self.assertTrue(any("JOIN @cdm_database_schema.PERSON P" in join for join in joins))
        self.assertTrue(any("JOIN @cdm_database_schema.VISIT_OCCURRENCE V" in join for join in joins))
        self.assertTrue(any("LEFT JOIN @cdm_database_schema.PROVIDER PR" in join for join in joins))
        
    def test_resolve_where_clauses_basic(self):
        criteria = DrugExposure(
            codeset_id=1,
            first=False,
            occurrence_start_date=DateRange(value="2020-01-01", op="gt"),
            occurrence_end_date=DateRange(value="2021-01-01", op="lt")
        )
        where_clauses = self.builder.resolve_where_clauses(criteria)
        self.assertTrue(any("C.start_date" in clause for clause in where_clauses))
        self.assertTrue(any("C.end_date" in clause for clause in where_clauses))
        
    def test_resolve_where_clauses_attributes(self):
        criteria = DrugExposure(
            codeset_id=1,
            first=False,
            drug_type=[Concept(concept_id=1, concept_name="Type")],
            drug_type_exclude=True,
            refills=NumericRange(value=1, op="gt"),
            quantity=NumericRange(value=10, op="lt"),
            days_supply=NumericRange(value=30, op="eq"),
            age=NumericRange(value=18, op="gt"),
            gender=[Concept(concept_id=8507, concept_name="Male")],
            provider_specialty=[Concept(concept_id=3, concept_name="Spec")],
            visit_type=[Concept(concept_id=4, concept_name="Visit")],
            route_concept=[Concept(concept_id=5, concept_name="Route")]
        )
        where_clauses = self.builder.resolve_where_clauses(criteria)
        
        self.assertTrue(any("C.drug_type_concept_id not in (1)" in clause for clause in where_clauses))
        self.assertTrue(any("C.refills > 1" in clause for clause in where_clauses))
        self.assertTrue(any("C.quantity < 10" in clause for clause in where_clauses))
        self.assertTrue(any("C.days_supply = 30" in clause for clause in where_clauses))
        self.assertTrue(any("YEAR(C.start_date) - P.year_of_birth" in clause for clause in where_clauses))
        self.assertTrue(any("P.gender_concept_id in (8507)" in clause for clause in where_clauses))
        self.assertTrue(any("PR.specialty_concept_id in (3)" in clause for clause in where_clauses))
        self.assertTrue(any("V.visit_concept_id in (4)" in clause for clause in where_clauses))
        self.assertTrue(any("C.route_concept_id in (5)" in clause for clause in where_clauses))

    def test_resolve_where_clauses_codesets(self):
        """Test attributes using codesets."""
        criteria = DrugExposure(
            codeset_id=1,
            first=False,
            drug_type_cs=ConceptSetSelection(codeset_id=2, is_exclusion=False),
            route_concept_cs=ConceptSetSelection(codeset_id=3, is_exclusion=False),
            gender_cs=ConceptSetSelection(codeset_id=4, is_exclusion=False),
            provider_specialty_cs=ConceptSetSelection(codeset_id=5, is_exclusion=False),
            visit_type_cs=ConceptSetSelection(codeset_id=6, is_exclusion=False)
        )
        where_clauses = self.builder.resolve_where_clauses(criteria)
        
        self.assertTrue(any("C.drug_type_concept_id" in clause and "codeset_id = 2" in clause for clause in where_clauses))
        self.assertTrue(any("C.route_concept_id" in clause and "codeset_id = 3" in clause for clause in where_clauses))
        self.assertTrue(any("P.gender_concept_id" in clause and "codeset_id = 4" in clause for clause in where_clauses))
        self.assertTrue(any("PR.specialty_concept_id" in clause and "codeset_id = 5" in clause for clause in where_clauses))
        self.assertTrue(any("V.visit_concept_id" in clause and "codeset_id = 6" in clause for clause in where_clauses))
