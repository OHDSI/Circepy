import unittest
from circe.cohortdefinition import DrugExposure, TextFilter, ConditionOccurrence, VisitOccurrence, ProcedureOccurrence, NumericRange
from circe.vocabulary.concept import Concept
from circe.cohortdefinition.builders.drug_exposure import DrugExposureSqlBuilder
from circe.cohortdefinition.builders.condition_occurrence import ConditionOccurrenceSqlBuilder
from circe.cohortdefinition.builders.visit_occurrence import VisitOccurrenceSqlBuilder
from circe.cohortdefinition.builders.procedure_occurrence import ProcedureOccurrenceSqlBuilder
from circe.cohortdefinition.builders.measurement import MeasurementSqlBuilder
from circe.cohortdefinition.builders.observation import ObservationSqlBuilder
from circe.cohortdefinition.builders.device_exposure import DeviceExposureSqlBuilder
from circe.cohortdefinition.builders.death import DeathSqlBuilder
from circe.cohortdefinition.builders.condition_era import ConditionEraSqlBuilder
from circe.cohortdefinition.builders.drug_era import DrugEraSqlBuilder
from circe.cohortdefinition.builders.dose_era import DoseEraSqlBuilder
from circe.cohortdefinition.builders.specimen import SpecimenSqlBuilder
from circe.cohortdefinition.builders.visit_detail import VisitDetailSqlBuilder
from circe.cohortdefinition.builders.payer_plan_period import PayerPlanPeriodSqlBuilder
from circe.cohortdefinition.builders.observation_period import ObservationPeriodSqlBuilder
from circe.cohortdefinition.builders.location_region import LocationRegionSqlBuilder
from circe.cohortdefinition import (
    DrugExposure, TextFilter, ConditionOccurrence, VisitOccurrence, ConceptSetSelection,
    ProcedureOccurrence, NumericRange, Measurement, Observation, DeviceExposure, Death, DateRange,
    ConditionEra, DrugEra, DoseEra, Specimen, VisitDetail, PayerPlanPeriod, ObservationPeriod, Period,
    LocationRegion
)

class TestDrugExposureBuilder(unittest.TestCase):
    
    def setUp(self):
        self.builder = DrugExposureSqlBuilder()
        
    def test_includes_dose_unit_logic(self):
        # Create DrugExposure with dose_unit criteria
        de = DrugExposure(
            doseUnit=[Concept(conceptId=123, conceptName="mg", domainId="Unit", vocabularyId="UCUM", standardConcept="S", conceptCode="mg")],
            doseUnitCS=None,
            first=False  # Using default
        )
        
        sql = self.builder.get_criteria_sql(de)
        
        # Check Select Clause
        self.assertIn("de.dose_unit_concept_id", sql, "SQL should select dose_unit_concept_id when doseUnit criteria is present")
        
        # Check Where Clause
        self.assertIn("C.dose_unit_concept_id in (123)", sql, "SQL should filter by dose_unit_concept_id in WHERE clause")

    def test_includes_lot_number_logic(self):
        # Create DrugExposure with lot_number criteria
        de = DrugExposure(
            lotNumber=TextFilter(text="LOT123", op="eq"),
            first=False
        )
        
        sql = self.builder.get_criteria_sql(de)
        
        # Check Select Clause
        self.assertIn("de.lot_number", sql, "SQL should select lot_number when lotNumber criteria is present")
        
        # Check Where Clause  -- TextFilter usually renders as LIKE or = depending on op
        # BuilderUtils.build_text_filter_clause("C.lot_number", criteria.lot_number)
        # Assuming op="eq" -> = 'LOT123'
        self.assertIn("C.lot_number", sql, "SQL should filter by C.lot_number")
        self.assertIn("'LOT123'", sql, "SQL should contain the lot number value")

class TestConditionOccurrenceBuilder(unittest.TestCase):
    
    def setUp(self):
        self.builder = ConditionOccurrenceSqlBuilder()
        
    def test_includes_condition_status_logic(self):
        # Create ConditionOccurrence with conditionStatus
        co = ConditionOccurrence(
            conditionStatus=[Concept(conceptId=456, conceptName="Active", domainId="Condition", vocabularyId="SNOMED", standardConcept="S", conceptCode="Active")],
            first=False
        )
        
        sql = self.builder.get_criteria_sql(co)
        
        # Check Select Clause
        self.assertIn("co.condition_status_concept_id", sql, "SQL should select condition_status_concept_id when conditionStatus criteria is present")
        
        # Check Where Clause
        self.assertIn("C.condition_status_concept_id in (456)", sql, "SQL should filter by condition_status_concept_id")


class TestProcedureOccurrenceBuilder(unittest.TestCase):
    
    def setUp(self):
        self.builder = ProcedureOccurrenceSqlBuilder()
        
    def test_includes_full_logic(self):
        # Create ProcedureOccurrence with various criteria to test select, join, and where clauses
        po = ProcedureOccurrence(
            procedure_type=[Concept(conceptId=10, conceptName="Type A", domainId="Type", vocabularyId="Type", standardConcept="S", conceptCode="A")],
            provider_specialty=[Concept(conceptId=20, conceptName="Surgeon", domainId="Provider", vocabularyId="Specialty", standardConcept="S", conceptCode="Surg")],
            visit_type=[Concept(conceptId=30, conceptName="Inpatient", domainId="Visit", vocabularyId="Visit", standardConcept="S", conceptCode="IP")],
            gender=[Concept(conceptId=8507, conceptName="Male", domainId="Gender", vocabularyId="Gender", standardConcept="S", conceptCode="M")],
            quantity=NumericRange(op="gt", value=5),
            first=False
        )
        
        sql = self.builder.get_criteria_sql(po)
        
        # 1. Check Select Clauses
        self.assertIn("po.procedure_type_concept_id", sql, "SQL should select procedure_type_concept_id")
        self.assertIn("po.provider_id", sql, "SQL should select provider_id")
        
        # 2. Check Join Clauses
        # Gender -> Join Person
        self.assertIn("JOIN @cdm_database_schema.PERSON P", sql, "Should join PERSON for gender check")
        # VisitType -> Join VisitOccurrence
        self.assertIn("JOIN @cdm_database_schema.VISIT_OCCURRENCE V", sql, "Should join VISIT_OCCURRENCE for visit type check")
        # ProviderSpecialty -> Join Provider
        self.assertIn("LEFT JOIN @cdm_database_schema.PROVIDER PR", sql, "Should join PROVIDER for specialty check")
        
        # 3. Check Where Clauses
        self.assertIn("C.procedure_type_concept_id in (10)", sql, "Should filter procedure_type_concept_id")
        self.assertIn("PR.specialty_concept_id in (20)", sql, "Should filter provider specialty")
        self.assertIn("V.visit_concept_id in (30)", sql, "Should filter visit type")
        self.assertIn("P.gender_concept_id in (8507)", sql, "Should filter gender")
        self.assertIn("C.quantity > 5", sql, "Should filter quantity")

        self.assertIn("C.quantity > 5", sql, "Should filter quantity")

class TestMeasurementBuilder(unittest.TestCase):
    
    def setUp(self):
        self.builder = MeasurementSqlBuilder()
        
    def test_includes_full_logic(self):
        # Create Measurement with various criteria
        meas = Measurement(
            measurement_type=[Concept(conceptId=10, conceptName="Type A", domainId="Type", vocabularyId="Type", standardConcept="S", conceptCode="A")],
            operator=[Concept(conceptId=20, conceptName="Op", domainId="Op", vocabularyId="Op", standardConcept="S", conceptCode="Op")],
            value_as_number=NumericRange(op="gt", value=150.5),
            unit=[Concept(conceptId=30, conceptName="mg/dL", domainId="Unit", vocabularyId="Unit", standardConcept="S", conceptCode="mg/dL")],
            abnormal=True,
            age=NumericRange(op="gt", value=18),
            gender=[Concept(conceptId=8507, conceptName="Male", domainId="Gender", vocabularyId="Gender", standardConcept="S", conceptCode="M")],
            visit_type=[Concept(conceptId=40, conceptName="IP", domainId="Visit", vocabularyId="Visit", standardConcept="S", conceptCode="IP")],
            first=False
        )
        
        sql = self.builder.get_criteria_sql(meas)
        
        # 1. Check Select Clauses
        self.assertIn("m.measurement_type_concept_id", sql, "Should select measurement_type_concept_id")
        self.assertIn("m.operator_concept_id", sql, "Should select operator_concept_id")
        self.assertIn("m.unit_concept_id", sql, "Should select unit_concept_id")
        
        # 2. Check Join Clauses
        self.assertIn("JOIN @cdm_database_schema.PERSON P", sql, "Should join PERSON")
        self.assertIn("JOIN @cdm_database_schema.VISIT_OCCURRENCE V", sql, "Should join VISIT_OCCURRENCE")
        
        # 3. Check Where Clauses
        self.assertIn("C.measurement_type_concept_id in (10)", sql, "Should filter measurement type")
        self.assertIn("C.operator_concept_id in (20)", sql, "Should filter operator")
        self.assertIn("C.value_as_number > 150.5000", sql, "Should filter value_as_number")
        self.assertIn("C.unit_concept_id in (30)", sql, "Should filter unit")
        self.assertIn("(C.value_as_number < C.range_low or C.value_as_number > C.range_high or C.value_as_concept_id in (4155142, 4155143))", sql, "Should filter abnormal")
        self.assertIn("YEAR(C.start_date) - P.year_of_birth > 18", sql, "Should filter age")
        self.assertIn("P.gender_concept_id in (8507)", sql, "Should filter gender")
        self.assertIn("V.visit_concept_id in (40)", sql, "Should filter visit type")

class TestObservationBuilder(unittest.TestCase):
    
    def setUp(self):
        self.builder = ObservationSqlBuilder()
        
    def test_includes_full_logic(self):
        # Create Observation with various criteria
        obs = Observation(
            observation_type=[Concept(conceptId=10, conceptName="Type A", domainId="Type", vocabularyId="Type", standardConcept="S", conceptCode="A")],
            value_as_string=TextFilter(text="Positive", op="eq"),
            value_as_number=NumericRange(op="gt", value=100),
            unit=[Concept(conceptId=30, conceptName="mg", domainId="Unit", vocabularyId="Unit", standardConcept="S", conceptCode="mg")],
            qualifier=[Concept(conceptId=50, conceptName="Severe", domainId="Qualifier", vocabularyId="Qualifier", standardConcept="S", conceptCode="Sev")],
            age=NumericRange(op="gt", value=18),
            gender=[Concept(conceptId=8507, conceptName="Male", domainId="Gender", vocabularyId="Gender", standardConcept="S", conceptCode="M")],
            visit_type=[Concept(conceptId=40, conceptName="IP", domainId="Visit", vocabularyId="Visit", standardConcept="S", conceptCode="IP")],
            first=False
        )
        
        sql = self.builder.get_criteria_sql(obs)
        
        # 1. Check Select Clauses
        self.assertIn("o.observation_type_concept_id", sql, "Should select observation_type_concept_id")
        self.assertIn("o.value_as_string", sql, "Should select value_as_string")
        self.assertIn("o.qualifier_concept_id", sql, "Should select qualifier_concept_id")
        self.assertIn("o.unit_concept_id", sql, "Should select unit_concept_id")
        
        # 2. Check Join Clauses
        self.assertIn("JOIN @cdm_database_schema.PERSON P", sql, "Should join PERSON")
        # Discrepancy check: Java uses 'V', Python uses 'VO' currently. We strictly test for 'V' to enforce parity.
        self.assertIn("JOIN @cdm_database_schema.VISIT_OCCURRENCE V ", sql, "Should join VISIT_OCCURRENCE with alias V")
        
        # 3. Check Where Clauses
        self.assertIn("C.observation_type_concept_id in (10)", sql, "Should filter observation type")
        self.assertIn("C.value_as_string = 'Positive'", sql, "Should filter value_as_string")
        self.assertIn("C.value_as_number > 100", sql, "Should filter value_as_number")
        self.assertIn("C.unit_concept_id in (30)", sql, "Should filter unit")
        self.assertIn("C.qualifier_concept_id in (50)", sql, "Should filter qualifier")
        self.assertIn("YEAR(C.start_date) - P.year_of_birth > 18", sql, "Should filter age")
        self.assertIn("P.gender_concept_id in (8507)", sql, "Should filter gender")
        self.assertIn("P.gender_concept_id in (8507)", sql, "Should filter gender")
        self.assertIn("V.visit_concept_id in (40)", sql, "Should filter visit type with alias V")

class TestDeviceExposureBuilder(unittest.TestCase):
    
    def setUp(self):
        self.builder = DeviceExposureSqlBuilder()
        
    def test_includes_full_logic(self):
        # Create DeviceExposure with various criteria
        de = DeviceExposure(
            device_type=[Concept(conceptId=10, conceptName="Type A", domainId="Type", vocabularyId="Type", standardConcept="S", conceptCode="A")],
            unique_device_id=TextFilter(text="UDI123", op="eq"),
            quantity=NumericRange(op="gt", value=5),
            age=NumericRange(op="gt", value=18),
            gender=[Concept(conceptId=8507, conceptName="Male", domainId="Gender", vocabularyId="Gender", standardConcept="S", conceptCode="M")],
            visit_type=[Concept(conceptId=40, conceptName="IP", domainId="Visit", vocabularyId="Visit", standardConcept="S", conceptCode="IP")],
            first=False
        )
        
        sql = self.builder.get_criteria_sql(de)
        
        # 1. Check Select Clauses
        self.assertIn("de.device_type_concept_id", sql, "Should select device_type_concept_id")
        self.assertIn("de.unique_device_id", sql, "Should select unique_device_id")
        self.assertIn("de.quantity", sql, "Should select quantity")
        
        # 2. Check Join Clauses
        self.assertIn("JOIN @cdm_database_schema.PERSON P", sql, "Should join PERSON")
        self.assertIn("JOIN @cdm_database_schema.VISIT_OCCURRENCE V", sql, "Should join VISIT_OCCURRENCE")
        
        # 3. Check Where Clauses
        # Note: Testing for case-insensitive match for keywords or exact match if builder is specific
        self.assertTrue("C.device_type_concept_id IN (10)" in sql or "C.device_type_concept_id in (10)" in sql, "Should filter device type")
        self.assertIn("C.unique_device_id = 'UDI123'", sql, "Should filter unique_device_id")
        self.assertIn("C.quantity > 5", sql, "Should filter quantity")
        self.assertIn("YEAR(C.start_date) - P.year_of_birth > 18", sql, "Should filter age")
        # Check gender filter - builder output might be IN or in
        self.assertTrue("P.gender_concept_id IN (8507)" in sql or "P.gender_concept_id in (8507)" in sql, "Should filter gender")
        self.assertTrue("P.gender_concept_id IN (8507)" in sql or "P.gender_concept_id in (8507)" in sql, "Should filter gender")
        self.assertTrue("V.visit_concept_id IN (40)" in sql or "V.visit_concept_id in (40)" in sql, "Should filter visit type")

class TestDeathBuilder(unittest.TestCase):
    
    def setUp(self):
        self.builder = DeathSqlBuilder()
        
    def test_includes_full_logic(self):
        # Create Death with various criteria
        death = Death(
            death_type=[Concept(conceptId=10, conceptName="Type A", domainId="Type", vocabularyId="Type", standardConcept="S", conceptCode="A")],
            age=NumericRange(op="gt", value=60),
            gender=[Concept(conceptId=8507, conceptName="Male", domainId="Gender", vocabularyId="Gender", standardConcept="S", conceptCode="M")],
            occurrence_start_date=DateRange(op="gt", value="2020-01-01"),
            first=False
        )
        # Re-check criteria.py for Death structure.
        
        sql = self.builder.get_criteria_sql(death)
        
        # 1. Check Select Clauses
        self.assertIn("d.person_id", sql, "Should select person_id with alias d")
        self.assertIn("d.cause_concept_id", sql, "Should select cause_concept_id")
        self.assertIn("d.death_date", sql, "Should select death_date")
        
        # 2. Check Join Clauses
        self.assertIn("JOIN @cdm_database_schema.PERSON P", sql, "Should join PERSON")
        
        # 3. Check Where Clauses
        self.assertTrue("C.death_type_concept_id IN (10)" in sql or "C.death_type_concept_id in (10)" in sql, "Should filter death type")
        self.assertIn("YEAR(C.start_date) - P.year_of_birth > 60", sql, "Should filter age")
        self.assertTrue("P.gender_concept_id IN (8507)" in sql or "P.gender_concept_id in (8507)" in sql, "Should filter gender")
        self.assertIn("C.start_date > DATEFROMPARTS(2020, 1, 1)", sql, "Should filter occurrence_start_date")

class TestConditionEraBuilder(unittest.TestCase):
    
    def setUp(self):
        self.builder = ConditionEraSqlBuilder()
        
    def test_includes_full_logic(self):
        # Create ConditionEra with various criteria
        ce = ConditionEra(
            codeset_id=1,
            era_start_date=DateRange(op="gt", value="2020-01-01"),
            era_end_date=DateRange(op="lt", value="2021-01-01"),
            occurrence_count=NumericRange(op="gt", value=2),
            era_length=NumericRange(op="gt", value=10),
            age_at_start=NumericRange(op="gt", value=40),
            age_at_end=NumericRange(op="lt", value=80),
            gender=[Concept(conceptId=8507, conceptName="Male", domainId="Gender", vocabularyId="Gender", standardConcept="S", conceptCode="M")],
            first=True
        )
        
        sql = self.builder.get_criteria_sql(ce)
        
        # 1. Check Select Clauses
        self.assertIn("ce.person_id", sql, "Should select person_id")
        self.assertIn("ce.condition_era_id", sql, "Should select condition_era_id")
        
        # 2. Check Join Clauses
        self.assertIn("JOIN @cdm_database_schema.PERSON P", sql, "Should join PERSON")
        
        # 3. Check Where Clauses
        # Codeset filter inside subquery (double filtering might apply)
        # Python implementation currently puts it in subquery via embed_codeset_clause
        self.assertIn("where ce.condition_concept_id in (SELECT concept_id from  #Codesets where codeset_id = 1)", sql, "Should filter codeset inside subquery with Java-style formatting")
        
        self.assertIn("C.start_date > DATEFROMPARTS(2020, 1, 1)", sql, "Should filter era_start_date")
        self.assertIn("C.end_date < DATEFROMPARTS(2021, 1, 1)", sql, "Should filter era_end_date")
        self.assertIn("C.condition_occurrence_count > 2", sql, "Should filter occurrence_count")
        
        # Note: DATEDIFF vs datediff. Python builder uses DATEDIFF(d,C.start_date, C.end_date)
        self.assertIn("DATEDIFF(d,C.start_date, C.end_date) > 10", sql, "Should filter era_length")
        
        self.assertIn("YEAR(C.start_date) - P.year_of_birth > 40", sql, "Should filter age_at_start")
        self.assertIn("YEAR(C.end_date) - P.year_of_birth < 80", sql, "Should filter age_at_end")
        
        self.assertTrue("P.gender_concept_id IN (8507)" in sql or "P.gender_concept_id in (8507)" in sql, "Should filter gender")
        
        # 4. Check Ordinal
        self.assertIn("row_number() over (PARTITION BY ce.person_id ORDER BY ce.condition_era_start_date, ce.condition_era_id) as ordinal", sql, "Should have ordinal window func")
        self.assertIn("row_number() over (PARTITION BY ce.person_id ORDER BY ce.condition_era_start_date, ce.condition_era_id) as ordinal", sql, "Should have ordinal window func")
        self.assertIn("C.ordinal = 1", sql, "Should filter first ordinal")

class TestDrugEraBuilder(unittest.TestCase):
    
    def setUp(self):
        self.builder = DrugEraSqlBuilder()
        
    def test_includes_full_logic(self):
        # Create DrugEra with various criteria
        de = DrugEra(
            codeset_id=1,
            era_start_date=DateRange(op="gt", value="2020-01-01"),
            era_end_date=DateRange(op="lt", value="2021-01-01"),
            occurrence_count=NumericRange(op="gt", value=2),
            era_length=NumericRange(op="gt", value=10),
            age_at_start=NumericRange(op="gt", value=40),
            age_at_end=NumericRange(op="lt", value=80),
            gender=[Concept(conceptId=8507, conceptName="Male", domainId="Gender", vocabularyId="Gender", standardConcept="S", conceptCode="M")],
            first=True
        )
        
        sql = self.builder.get_criteria_sql(de)
        
        # 1. Check Select Clauses
        self.assertIn("de.person_id", sql, "Should select person_id")
        self.assertIn("de.drug_era_id", sql, "Should select drug_era_id")
        
        # 2. Check Join Clauses
        self.assertIn("JOIN @cdm_database_schema.PERSON P", sql, "Should join PERSON")
        
        # 3. Check Where Clauses
        # Codeset filter inside subquery
        self.assertIn("where de.drug_concept_id in (SELECT concept_id from  #Codesets where codeset_id = 1)", sql, "Should filter codeset inside subquery with Java-style formatting")
        
        self.assertIn("C.start_date > DATEFROMPARTS(2020, 1, 1)", sql, "Should filter era_start_date")
        self.assertIn("C.end_date < DATEFROMPARTS(2021, 1, 1)", sql, "Should filter era_end_date")
        self.assertIn("C.drug_exposure_count > 2", sql, "Should filter occurrence_count")
        
        self.assertIn("DATEDIFF(d,C.start_date, C.end_date) > 10", sql, "Should filter era_length")
        
        self.assertIn("YEAR(C.start_date) - P.year_of_birth > 40", sql, "Should filter age_at_start")
        self.assertIn("YEAR(C.end_date) - P.year_of_birth < 80", sql, "Should filter age_at_end")
        
        self.assertTrue("P.gender_concept_id IN (8507)" in sql or "P.gender_concept_id in (8507)" in sql, "Should filter gender")
        
        # 4. Check Ordinal
        self.assertIn("row_number() over (PARTITION BY de.person_id ORDER BY de.drug_era_start_date, de.drug_era_id) as ordinal", sql, "Should have ordinal window func")
        self.assertIn("C.ordinal = 1", sql, "Should filter first ordinal")

class TestDoseEraBuilder(unittest.TestCase):
    
    def setUp(self):
        self.builder = DoseEraSqlBuilder()
        
    def test_includes_full_logic(self):
        # Create DoseEra with various criteria
        de = DoseEra(
            codeset_id=1,
            era_start_date=DateRange(op="gt", value="2020-01-01"),
            era_end_date=DateRange(op="lt", value="2021-01-01"),
            unit=[Concept(conceptId=8507, conceptName="mg", domainId="Unit", vocabularyId="Unit", standardConcept="S", conceptCode="mg")],
            dose_value=NumericRange(op="gt", value=10),
            era_length=NumericRange(op="gt", value=5),
            age_at_start=NumericRange(op="gt", value=40),
            age_at_end=NumericRange(op="lt", value=80),
            gender=[Concept(conceptId=8507, conceptName="Male", domainId="Gender", vocabularyId="Gender", standardConcept="S", conceptCode="M")],
            first=True
        )
        
        sql = self.builder.get_criteria_sql(de)
        
        # 1. Check Select Clauses
        self.assertIn("de.person_id", sql, "Should select person_id")
        self.assertIn("de.dose_era_id", sql, "Should select dose_era_id")
        self.assertIn("de.dose_value", sql, "Should select dose_value")
        
        # 2. Check Join Clauses
        self.assertIn("JOIN @cdm_database_schema.PERSON P", sql, "Should join PERSON")
        
        # 3. Check Where Clauses
        # Codeset filter inside subquery
        self.assertIn("where de.drug_concept_id in (SELECT concept_id from  #Codesets where codeset_id = 1)", sql, "Should filter codeset inside subquery with Java-style formatting")
        
        self.assertIn("C.start_date > DATEFROMPARTS(2020, 1, 1)", sql, "Should filter era_start_date")
        self.assertIn("C.end_date < DATEFROMPARTS(2021, 1, 1)", sql, "Should filter era_end_date")
        self.assertIn("C.dose_value > 10.0000", sql, "Should filter dose_value")
        self.assertTrue("C.unit_concept_id IN (8507)" in sql or "C.unit_concept_id in (8507)" in sql, "Should filter unit")
        
        self.assertIn("DATEDIFF(d,C.start_date, C.end_date) > 5", sql, "Should filter era_length")
        
        self.assertIn("YEAR(C.start_date) - P.year_of_birth > 40", sql, "Should filter age_at_start")
        self.assertIn("YEAR(C.end_date) - P.year_of_birth < 80", sql, "Should filter age_at_end")
        
        self.assertTrue("P.gender_concept_id IN (8507)" in sql or "P.gender_concept_id in (8507)" in sql, "Should filter gender")
        
        # 4. Check Ordinal
        self.assertIn("row_number() over (PARTITION BY de.person_id ORDER BY de.dose_era_start_date, de.dose_era_id) as ordinal", sql, "Should have ordinal window func")
        self.assertIn("C.ordinal = 1", sql, "Should filter first ordinal")

class TestSpecimenBuilder(unittest.TestCase):
    
    def setUp(self):
        self.builder = SpecimenSqlBuilder()
        
    def test_includes_full_logic(self):
        # Create Specimen with various criteria
        spec = Specimen(
            codeset_id=1,
            occurrence_start_date=DateRange(op="gt", value="2020-01-01"),
            specimen_type=[Concept(conceptId=10, conceptName="Blood", domainId="Specimen", vocabularyId="Specimen", standardConcept="S", conceptCode="Blood")],
            quantity=NumericRange(op="gt", value=5),
            unit=[Concept(conceptId=8587, conceptName="ml", domainId="Unit", vocabularyId="Unit", standardConcept="S", conceptCode="ml")],
            anatomic_site=[Concept(conceptId=123, conceptName="Arm", domainId="Specimen", vocabularyId="Specimen", standardConcept="S", conceptCode="Arm")],
            disease_status=[Concept(conceptId=456, conceptName="Sick", domainId="Specimen", vocabularyId="Specimen", standardConcept="S", conceptCode="Sick")],
            source_id=TextFilter(op="startsWith", text="123"),
            age=NumericRange(op="gt", value=40),
            gender=[Concept(conceptId=8507, conceptName="Male", domainId="Gender", vocabularyId="Gender", standardConcept="S", conceptCode="M")],
            first=True
        )
        
        sql = self.builder.get_criteria_sql(spec)
        
        # 1. Check Select Clauses
        # Java selects: s.person_id, s.specimen_id, s.specimen_concept_id, s.specimen_date, s.visit_occurrence_id
        # Python likely misses some or uses different alias
        self.assertIn("s.person_id", sql, "Should select person_id with alias s")
        
        # 2. Check Join Clauses
        self.assertIn("JOIN @cdm_database_schema.PERSON P", sql, "Should join PERSON")
        
        # codeset join logic
        self.assertIn("JOIN #Codesets cs on (s.specimen_concept_id = cs.concept_id and cs.codeset_id = 1)", sql, "Should filter codeset via JOIN")
        
        self.assertIn("C.specimen_date > DATEFROMPARTS(2020, 1, 1)", sql, "Should filter occurrence_start_date")
        self.assertIn("C.quantity > 5", sql, "Should filter quantity")
        self.assertTrue("C.unit_concept_id IN (8587)" in sql or "C.unit_concept_id in (8587)" in sql, "Should filter unit")
        self.assertTrue("C.anatomic_site_concept_id IN (123)" in sql or "C.anatomic_site_concept_id in (123)" in sql, "Should filter anatomic_site")
        self.assertTrue("C.disease_status_concept_id IN (456)" in sql or "C.disease_status_concept_id in (456)" in sql, "Should filter disease_status")
        
        self.assertIn("C.specimen_source_id LIKE '123%'", sql, "Should filter source_id")
        
        self.assertIn("YEAR(C.specimen_date) - P.year_of_birth > 40", sql, "Should filter age")
        self.assertTrue("P.gender_concept_id IN (8507)" in sql or "P.gender_concept_id in (8507)" in sql, "Should filter gender")
        
        # 4. Check Ordinal
        self.assertIn("row_number() over (PARTITION BY s.person_id ORDER BY s.specimen_date, s.specimen_id) as ordinal", sql, "Should have ordinal window func")
        self.assertIn("C.ordinal = 1", sql, "Should filter first ordinal")

class TestVisitDetailBuilder(unittest.TestCase):
    
    def setUp(self):
        self.builder = VisitDetailSqlBuilder()
        
    def test_includes_full_logic(self):
        # Create VisitDetail with various criteria
        vd = VisitDetail(
            codeset_id=1,
            visit_detail_start_date=DateRange(op="gt", value="2020-01-01"),
            visit_detail_end_date=DateRange(op="lt", value="2021-01-01"),
            visit_detail_type_cs=ConceptSetSelection(codesetId=2),
            visit_detail_length=NumericRange(op="gt", value=1),
            provider_specialty_cs=ConceptSetSelection(codesetId=3),
            place_of_service_cs=ConceptSetSelection(codesetId=4),
            place_of_service_location=5,
            age=NumericRange(op="gt", value=40),
            gender=[Concept(conceptId=8507, conceptName="Male", domainId="Gender", vocabularyId="Gender", standardConcept="S", conceptCode="M")],
            first=True
        )
        
        sql = self.builder.get_criteria_sql(vd)
        
        # 1. Check Select Clauses
        self.assertIn("vd.person_id", sql, "Should select person_id")
        self.assertIn("vd.visit_detail_id", sql, "Should select visit_detail_id")
        self.assertIn("vd.provider_id", sql, "Should select provider_id")
        self.assertIn("vd.care_site_id", sql, "Should select care_site_id")
        
        # 2. Check Join Clauses
        self.assertIn("JOIN @cdm_database_schema.PERSON P", sql, "Should join PERSON")
        self.assertIn("JOIN @cdm_database_schema.CARE_SITE CS", sql, "Should join CARE_SITE")
        self.assertIn("LEFT JOIN @cdm_database_schema.PROVIDER PR", sql, "Should join PROVIDER")
        self.assertIn("JOIN @cdm_database_schema.LOCATION_HISTORY LH", sql, "Should join LOCATION_HISTORY")
        self.assertIn("JOIN @cdm_database_schema.LOCATION LOC", sql, "Should join LOCATION")
        
        # 3. Check Where Clauses
        # Codeset join logic
        self.assertIn("JOIN #Codesets cs on (vd.visit_detail_concept_id = cs.concept_id and cs.codeset_id = 1)", sql)
        
        self.assertIn("C.start_date > DATEFROMPARTS(2020, 1, 1)", sql, "Should filter start_date")
        self.assertIn("C.end_date < DATEFROMPARTS(2021, 1, 1)", sql, "Should filter end_date")
        
        self.assertTrue("C.visit_detail_type_concept_id IN (SELECT concept_id from #Codesets where codeset_id = 2)" in sql or "C.visit_detail_type_concept_id in (select concept_id from #Codesets where codeset_id = 2)" in sql, "Should filter visit_detail_type_concept_id")
        
        self.assertIn("DATEDIFF(d,C.start_date, C.end_date) > 1", sql, "Should filter visit_length")
        
        self.assertIn("YEAR(C.end_date) - P.year_of_birth > 40", sql, "Should filter age")
        self.assertIn("P.gender_concept_id in (8507)", sql, "Should filter gender")
        
        self.assertTrue("PR.specialty_concept_id IN (SELECT concept_id from #Codesets where codeset_id = 3)" in sql or "PR.specialty_concept_id in (select concept_id from #Codesets where codeset_id = 3)" in sql, "Should filter provider")
        self.assertTrue("CS.place_of_service_concept_id IN (SELECT concept_id from #Codesets where codeset_id = 4)" in sql or "CS.place_of_service_concept_id in (select concept_id from #Codesets where codeset_id = 4)" in sql, "Should filter place of service")
        
        # Location filtering via join
        # Just check join existence for now
        
        # 4. Check Ordinal
        self.assertIn("row_number() over (PARTITION BY vd.person_id ORDER BY vd.visit_detail_start_date, vd.visit_detail_id) as ordinal", sql, "Should have ordinal window func")
        self.assertIn("C.ordinal = 1", sql, "Should filter first ordinal")

class TestPayerPlanPeriodBuilder(unittest.TestCase):
    
    def setUp(self):
        self.builder = PayerPlanPeriodSqlBuilder()
        
    def test_includes_full_logic(self):
        # Create PayerPlanPeriod with various criteria
        ppp = PayerPlanPeriod(
            payer_concept=1,
            plan_concept=2,
            sponsor_concept=3,
            stop_reason_concept=4,
            payer_source_concept=5,
            plan_source_concept=6,
            sponsor_source_concept=7,
            stop_reason_source_concept=8,
            period_start_date=DateRange(op="gt", value="2020-01-01"),
            period_end_date=DateRange(op="lt", value="2021-01-01"),
            period_length=NumericRange(op="gt", value=10),
            age_at_start=NumericRange(op="gt", value=40),
            age_at_end=NumericRange(op="lt", value=80),
            gender=[Concept(conceptId=8507, conceptName="Male", domainId="Gender", vocabularyId="Gender", standardConcept="S", conceptCode="M")],
            first=True
        )
        
        sql = self.builder.get_criteria_sql(ppp)
        
        # 1. Check Select Clauses
        self.assertIn("ppp.person_id", sql, "Should select person_id")
        self.assertIn("ppp.payer_plan_period_id", sql, "Should select payer_plan_period_id")
        self.assertIn("ppp.payer_concept_id", sql, "Should select payer_concept_id")
        self.assertIn("ppp.plan_concept_id", sql, "Should select plan_concept_id")
        self.assertIn("ppp.sponsor_concept_id", sql, "Should select sponsor_concept_id")
        self.assertIn("ppp.stop_reason_concept_id", sql, "Should select stop_reason_concept_id")
        
        # 2. Check Join Clauses
        self.assertIn("JOIN @cdm_database_schema.PERSON P", sql, "Should join PERSON")
        
        # 3. Check Where Clauses
        self.assertIn("C.payer_concept_id in (SELECT concept_id from #Codesets where codeset_id = 1)", sql, "Should filter payer_concept")
        self.assertIn("C.plan_concept_id in (SELECT concept_id from #Codesets where codeset_id = 2)", sql, "Should filter plan_concept")
        self.assertIn("C.sponsor_concept_id in (SELECT concept_id from #Codesets where codeset_id = 3)", sql, "Should filter sponsor_concept")
        self.assertIn("C.stop_reason_concept_id in (SELECT concept_id from #Codesets where codeset_id = 4)", sql, "Should filter stop_reason_concept")
        
        self.assertIn("C.start_date > DATEFROMPARTS(2020, 1, 1)", sql, "Should filter start_date")
        self.assertIn("C.end_date < DATEFROMPARTS(2021, 1, 1)", sql, "Should filter end_date")
        
        self.assertIn("DATEDIFF(d,C.start_date, C.end_date) > 10", sql, "Should filter period_length")
        
        self.assertIn("YEAR(C.start_date) - P.year_of_birth > 40", sql, "Should filter age_at_start")
        self.assertIn("YEAR(C.end_date) - P.year_of_birth < 80", sql, "Should filter age_at_end")
        
        self.assertIn("P.gender_concept_id in (8507)", sql, "Should filter gender")
        
        # 4. Check Ordinal
        self.assertIn("C.ordinal = 1", sql, "Should filter first ordinal")

class TestObservationPeriodBuilder(unittest.TestCase):
    
    def setUp(self):
        self.builder = ObservationPeriodSqlBuilder()
        
    def test_includes_full_logic(self):
        # Create ObservationPeriod with various criteria
        op = ObservationPeriod(
            period_start_date=DateRange(op="gt", value="2020-01-01"),
            period_end_date=DateRange(op="lt", value="2021-01-01"),
            period_type=[Concept(conceptId=1, conceptName="Type1", domainId="Type", vocabularyId="Type", standardConcept="S", conceptCode="1")],
            period_type_cs=ConceptSetSelection(codesetId=2),
            period_length=NumericRange(op="gt", value=365),
            age_at_start=NumericRange(op="gt", value=18),
            age_at_end=NumericRange(op="lt", value=100),
            user_defined_period=Period(start_date="2020-01-01", end_date="2021-01-01"),
            first=True
        )
        
        sql = self.builder.get_criteria_sql(op)
        
        # 1. Check Select Clauses
        self.assertIn("op.person_id", sql, "Should select person_id")
        self.assertIn("op.observation_period_id", sql, "Should select observation_period_id")
        self.assertIn("op.period_type_concept_id", sql, "Should select period_type_concept_id")
        
        # 2. Check Join Clauses
        self.assertIn("JOIN @cdm_database_schema.PERSON P", sql, "Should join PERSON")
        
        # 3. Check Where Clauses
        self.assertIn("C.start_date > DATEFROMPARTS(2020, 1, 1)", sql, "Should filter start_date")
        self.assertIn("C.end_date < DATEFROMPARTS(2021, 1, 1)", sql, "Should filter end_date")
        
        self.assertIn("C.period_type_concept_id in (1)", sql, "Should filter period_type")
        self.assertTrue("C.period_type_concept_id in (select concept_id from #Codesets where codeset_id = 2)" in sql or "C.period_type_concept_id IN (SELECT concept_id from #Codesets where codeset_id = 2)" in sql, "Should filter period_type_cs")
        
        self.assertIn("DATEDIFF(d,C.start_date, C.end_date) > 365", sql, "Should filter period_length")
        
        self.assertIn("YEAR(C.start_date) - P.year_of_birth > 18", sql, "Should filter age_at_start")
        self.assertIn("YEAR(C.end_date) - P.year_of_birth < 100", sql, "Should filter age_at_end")
        
        # User defined period bounds
        self.assertIn("C.start_date <= DATEFROMPARTS(2020, 1, 1) and C.end_date >= DATEFROMPARTS(2020, 1, 1)", sql, "Should filter user defined start")
        self.assertIn("C.start_date <= DATEFROMPARTS(2021, 1, 1) and C.end_date >= DATEFROMPARTS(2021, 1, 1)", sql, "Should filter user defined end")
        
        # 4. Check Ordinal
        self.assertIn("C.ordinal = 1", sql, "Should filter first ordinal")

class TestLocationRegionBuilder(unittest.TestCase):
    
    def setUp(self):
        self.builder = LocationRegionSqlBuilder()
        
    def test_includes_full_logic(self):
        # Create LocationRegion with codeset
        lr = LocationRegion(
            codeset_id=1
        )
        
        sql = self.builder.get_criteria_sql(lr)
        
        # 1. Check Select Clauses
        self.assertIn("C.person_id", sql, "Should select person_id")
        self.assertIn("C.location_id", sql, "Should select location_id")
        self.assertIn("C.region_concept_id", sql, "Should select region_concept_id")
        
        # 2. Check Codeset Clause
        # The python builder now uses AND l.region_concept_id ...
        self.assertTrue("AND l.region_concept_id in (SELECT concept_id from #Codesets where codeset_id = 1)" in sql or "AND l.region_concept_id in (select concept_id from #Codesets where codeset_id = 1)" in sql, "Should have codeset logic")
        
        # 3. Check Template Structure (that implies Person is present)
        self.assertIn("FROM @cdm_database_schema.LOCATION_HISTORY lh", sql, "Should select from LOCATION_HISTORY")
        self.assertIn("JOIN @cdm_database_schema.LOCATION l on lh.location_id = l.location_id", sql, "Should join LOCATION")
        self.assertIn("WHERE lh.domain_id = 'PERSON'", sql, "Should filter PERSON domain")
        
        # Verify that start_date and end_date are selected
        self.assertIn("C.start_date", sql, "Should select C.start_date")
        self.assertIn("C.end_date", sql, "Should select C.end_date")

if __name__ == '__main__':
    unittest.main()
