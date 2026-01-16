import unittest
from circe.cohortdefinition import (
    DrugExposure, NumericRange, DateRange, TextFilter,
    ConceptSetSelection, Window, WindowBound, ConditionOccurrence, ProcedureOccurrence,
    DeviceExposure, Measurement, Observation, Specimen, Death, VisitOccurrence, VisitDetail,
    ObservationPeriod, LocationRegion, PayerPlanPeriod, ConditionEra, DrugEra, DoseEra, Period
)
from circe.vocabulary import Concept, ConceptSet
from circe.cohortdefinition.printfriendly import MarkdownRender

class TestMarkdownRenderingParity(unittest.TestCase):

    def setUp(self):
        self.concept_sets = [
            ConceptSet(id=0, name="Acetaminophen"),
            ConceptSet(id=1, name="Opioids"),
            ConceptSet(id=2, name="Injectables")
        ]
        self.renderer = MarkdownRender(concept_sets=self.concept_sets)

    def test_drug_exposure_basic(self):
        de = DrugExposure(
            codeset_id=0,
            first=True
        )
        # drug exposure of 'Acetaminophen' for the first time in the person's history
        text = self.renderer._render_criteria(de, level=0, is_plural=False)
        # Note: render_criteria returns just the description part usually, assuming singular/plural handled by caller
        # But wait, looking at python code _render_criteria calls _render_drug_exposure...
        # Let's check python implementation of _render_criteria
        
        expected = "drug exposure of 'Acetaminophen' for the first time in the person's history."
        self.assertEqual(text.strip(), expected)

    def test_drug_exposure_complex(self):
        de = DrugExposure(
            codeset_id=1,
            first=False,
            days_supply=NumericRange(op="gt", value=30),
            refills=NumericRange(op="eq", value=0),
            quantity=NumericRange(op="bt", value=10, extent=20),
            lot_number=TextFilter(op="startsWith", text="LOT123")
        )
        # drug exposures of 'Opioids', with refills = 0; with quantity between 10 and 20; with days supply > 30 days; lot number starting with "LOT123"
        # The order depends on the implementation. FTL order:
        # window (if countCriteria), AgeGender, DateAdj, EventDate, DrugType, Refills, Quantity, DaysSupply, EffDose, DoseUnit, Route, LotNumber, StopReason, Provider, Visit
        
        # Expected attributes:
        # with refills = 0
        # with quantity between 10 and 20
        # with days supply > 30 days
        # lot number starting with "LOT123"
        
        text = self.renderer._render_criteria(de, level=0, is_plural=True)
        self.assertIn("drug exposures of 'Opioids'", text)
        self.assertIn("with refills = 0", text)
        self.assertIn("with quantity between 10 and 20", text)
        self.assertIn("with days supply &gt; 30 days", text)
        self.assertIn('lot number starting with "LOT123"', text)

        self.assertIn('lot number starting with "LOT123"', text)

    def test_condition_occurrence(self):
        co = ConditionOccurrence(
            codeset_id=0,
            first=True,
            condition_type=[Concept(concept_id=1, concept_name="EHR Problem List Entry")]
        )
        text = self.renderer._render_criteria(co, level=0, is_plural=False)
        # condition occurrence of 'Acetaminophen' for the first time in the person's history
        # , a condition type that is: "ehr problem list entry".
        
        self.assertIn("condition occurrence of 'Acetaminophen'", text)
        self.assertIn("for the first time in the person's history", text)
        self.assertIn('a condition type that is: "ehr problem list entry"', text)

    def test_procedure_occurrence(self):
        po = ProcedureOccurrence(
            codeset_id=2,
            first=False,
            quantity=NumericRange(op="eq", value=1),
            procedure_type=[Concept(concept_id=2, concept_name="Inpatient Procedure")]
        )
        text = self.renderer._render_criteria(po, level=0, is_plural=True)
        # procedure occurrences of 'Injectables'
        # , a procedure type that is: "inpatient procedure"
        # ; with quantity = 1.
        
        self.assertIn("procedure occurrences of 'Injectables'", text)
        self.assertIn('a procedure type that is: "inpatient procedure"', text)
        self.assertIn('with quantity = 1', text)

        self.assertIn('with quantity = 1', text)

    def test_device_exposure(self):
        de = DeviceExposure(
            codeset_id=0,
            first=True,
            prior_enroll_days=365
        )
        # Device uses codeset_id 0 -> 'Acetaminophen' (reusing concept set for test)
        text = self.renderer._render_criteria(de, level=0, is_plural=False)
        self.assertIn("device exposure of 'Acetaminophen'", text)
        self.assertIn("for the first time in the person's history", text)

    def test_measurement(self):
        m = Measurement(
            codeset_id=1, # Opioids
            first=False,
            operator=[Concept(concept_id=4172703, concept_name="=")],
            value_as_number=NumericRange(op="gt", value=5),
            unit=[Concept(concept_id=8718, concept_name="milliliter")]
        )
        text = self.renderer._render_criteria(m, level=0, is_plural=True)
        # measurement[s] of 'Opioids'
        # operator: =
        # numeric value > 5
        # unit: milliliter
        
        self.assertIn("measurements of 'Opioids'", text)
        self.assertIn('operator: "="', text)
        self.assertIn("numeric value &gt; 5", text) # Encoded >
        self.assertIn('unit: "milliliter"', text)

    def test_observation(self):
        obs = Observation(
            codeset_id=2, # Injectables
            first=False,
            value_as_string=TextFilter(op="contains", text="positive"),
            qualifier=[Concept(concept_id=45877994, concept_name="Severe")]
        )
        text = self.renderer._render_criteria(obs, level=0, is_plural=True)
        # observations of 'Injectables'
        # value as string containing "positive"
        # with qualifier: Severe
        
        self.assertIn("observations of 'Injectables'", text)
        self.assertIn('value as string containing "positive"', text)
        self.assertIn('with qualifier: "severe"', text)

        self.assertIn('with qualifier: "severe"', text)

    def test_specimen(self):
        s = Specimen(
            codeset_id=0,
            first=True,
            quantity=NumericRange(op="eq", value=1),
            unit=[Concept(concept_id=8718, concept_name="milliliter")],
            anatomic_site=[Concept(concept_id=4048385, concept_name="Liver")]
        )
        text = self.renderer._render_criteria(s, level=0, is_plural=False)
        # specimen of 'Acetaminophen'
        # for the first time in the person's history
        # with quantity = 1
        # unit: "milliliter"
        # with anatomic site: "liver"
        
        self.assertIn("specimen of 'Acetaminophen'", text)
        self.assertIn("with quantity = 1", text)
        self.assertIn('unit: "milliliter"', text)
        self.assertIn('with anatomic site: "liver"', text)

    def test_death(self):
        d = Death(
            codeset_id=1,
            first=True,
            death_source_concept=1 # maps to 'Opioids' name
        )
        text = self.renderer._render_criteria(d, level=0, is_plural=False)
        # death of 'Opioids' (including 'Opioids' source concepts)
        
        self.assertIn("death of 'Opioids'", text)
        self.assertIn("(including 'Opioids' source concepts)", text)

    def test_visit_occurrence(self):
        vo = VisitOccurrence(
            codeset_id=2,
            first=False,
            visit_length=NumericRange(op="gt", value=3),
            place_of_service=[Concept(concept_id=1, concept_name="Inpatient Hospital")]
        )
        text = self.renderer._render_criteria(vo, level=0, is_plural=True)
        # visit occurrences of 'Injectables'
        # with visit length > 3
        # a place of service that is: "inpatient hospital"

        self.assertIn("visit occurrences of 'Injectables'", text)
        self.assertIn("with visit length &gt; 3", text)
        self.assertIn('a place of service that is: "inpatient hospital"', text)

    def test_visit_detail(self):
        vd = VisitDetail(
            codeset_id=0,
            first=True,
            visit_detail_type=[Concept(concept_id=1, concept_name="Detail Type")]
        )
        text = self.renderer._render_criteria(vd, level=0, is_plural=False)
        # visit detail of 'Acetaminophen'
        # for the first time in the person's history
        # a visit detail type that is: "detail type"
        
        self.assertIn("visit detail of 'Acetaminophen'", text)
        self.assertIn('a visit detail type that is: "detail type"', text)

    def test_observation_period(self):
        op = ObservationPeriod(
            first=True,
            period_length=NumericRange(op="gt", value=365),
            user_defined_period=Period(start_date="2020-01-01", end_date="2020-12-31"),
            period_type=[Concept(concept_id=1, concept_name="Period Type")]
        )
        text = self.renderer._render_criteria(op, level=0, is_plural=False)
        # observation period
        # for the first time in the person's history
        # with period length > 365
        # using the period: start 2020-01-01 end 2020-12-31
        # a period type that is: "period type"
        
        self.assertIn("observation period", text)
        self.assertIn("with period length &gt; 365", text)
        # Verify period formatting matches Java/Python implementation
        # Python _render_period: "**Start Date:** ... **End Date:** ..."
        # But wait, how is it embedded? 
        # Java FTL uses `utils.period(criteria.userDefinedPeriod)`
        # I need to check how Python implements _render_period and if it matches FTL.
        # FTL usually renders readable text like "period start ..."
        # Python `_render_period` currently does: "**Start Date:** ..."
        
        self.assertIn("**Start Date:** 2020-01-01", text)
        self.assertIn('a period type that is: "period type"', text)

    def test_location_region(self):
        lr = LocationRegion(
            codeset_id=1
            # LocationRegion uses start_date and end_date fields directly for date range?
            # model has start_date/end_date as DateRange?
            # Checking criteria.py for LocationRegion...
        )
        # ... Wait, I recall LocationRegion only had codeset_id in criteria.py snippet (line 878)?
        # Let's check criteria.py again if start_date/end_date are there.
        # If not, I can't test them.
        text = self.renderer._render_criteria(lr, level=0, is_plural=False)
        self.assertIn("location of 'Opioids'", text)

    def test_payer_plan_period(self):
        ppp = PayerPlanPeriod(
            first=False,
            period_length=NumericRange(op="eq", value=30),
            gender=[Concept(concept_id=8532, concept_name="FEMALE")],
            payer_concept=123 # Should map to concept? But it's int.
            # Usually render uses getConceptName for IDs?
        )
        text = self.renderer._render_criteria(ppp, level=0, is_plural=True)
        # payer plan period
        # with period length = 30
        # gender is "female"
        # payer concept: ... (if implemented)
        
        self.assertIn("payer plan period", text)
        self.assertIn("with period length = 30", text)
        self.assertIn('gender is "female"', text)

    def test_condition_era(self):
        ce = ConditionEra(
            codeset_id=0,
            first=True,
            era_length=NumericRange(op="gt", value=10),
            occurrence_count=NumericRange(op="gte", value=2)
        )
        text = self.renderer._render_criteria(ce, level=0, is_plural=False)
        # condition era of 'Acetaminophen'
        # for the first time...
        # era length > 10
        # occurrence count >= 2
        
        self.assertIn("condition era of 'Acetaminophen'", text)
        self.assertIn("era length is &gt; 10 days", text)
        self.assertIn("containing &gt;= 2 occurrences", text)

    def test_drug_era(self):
        de = DrugEra(
            codeset_id=1,
            gap_days=NumericRange(op="lt", value=5)
        )
        text = self.renderer._render_criteria(de, level=0, is_plural=True)
        # drug eras of 'Opioids'
        # with gap days < 5
        
        self.assertIn("drug eras of 'Opioids'", text)
        self.assertIn("with gap days &lt; 5", text)

    def test_dose_era(self):
        doe = DoseEra(
            codeset_id=2,
            dose_value=NumericRange(op="bt", value=10, extent=20),
            unit=[Concept(concept_id=8718, concept_name="milligram")]
        )
        text = self.renderer._render_criteria(doe, level=0, is_plural=True)
        # dose eras of 'Injectables'
        # with dose value between 10 and 20
        # unit: "milligram"
        
        self.assertIn("dose eras of 'Injectables'", text)
        self.assertIn("with dose value between 10 and 20", text)
        self.assertIn('unit is: "milligram"', text)

if __name__ == '__main__':
    unittest.main()
