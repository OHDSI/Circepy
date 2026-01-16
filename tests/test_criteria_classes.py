"""
Tests for Criteria Domain Classes

This module contains comprehensive tests for all the criteria domain classes
that were recently implemented.
"""

import unittest
import sys
import os
from typing import List, Optional

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from circe.cohortdefinition.criteria import (
    ConditionOccurrence, DrugExposure, ProcedureOccurrence, VisitOccurrence,
    Observation, Measurement, DeviceExposure, Specimen, Death, VisitDetail,
    ObservationPeriod, PayerPlanPeriod, LocationRegion, ConditionEra,
    DrugEra, DoseEra, GeoCriteria, WindowedCriteria
)
from circe.cohortdefinition.core import (
    TextFilter, WindowBound, Window,
    DateOffsetStrategy, CustomEraStrategy, DateRange, NumericRange,
    ConceptSetSelection
)
from circe.vocabulary.concept import Concept


class TestConditionOccurrence(unittest.TestCase):
    """Test ConditionOccurrence criteria class."""

    def test_condition_occurrence_initialization(self):
        """Test basic initialization of ConditionOccurrence."""
        condition = ConditionOccurrence(
            first=True,
            condition_type_exclude=False
        )
        self.assertTrue(condition.first)
        self.assertFalse(condition.condition_type_exclude)
        self.assertIsNone(condition.gender)
        self.assertIsNone(condition.codeset_id)

    def test_condition_occurrence_with_all_fields(self):
        """Test ConditionOccurrence with all fields populated."""
        condition = ConditionOccurrence(
            gender=[Concept(concept_id=8507, concept_name="Male")],
            occurrence_end_date=DateRange(op="lt", extent="30", value="2023-01-01"),
            stop_reason=TextFilter(text="completed", op="eq"),
            condition_source_concept=12345,
            gender_cs=ConceptSetSelection(codeset_id=1, is_exclusion=False),
            condition_status=[Concept(concept_id=1, concept_name="Active")],
            condition_type=[Concept(concept_id=2, concept_name="Primary")],
            condition_type_cs=ConceptSetSelection(codeset_id=2, is_exclusion=False),
            condition_type_exclude=False,
            provider_specialty_cs=ConceptSetSelection(codeset_id=3, is_exclusion=False),
            visit_type_cs=ConceptSetSelection(codeset_id=4, is_exclusion=False),
            visit_type=[Concept(concept_id=5, concept_name="Inpatient")],
            condition_status_cs=ConceptSetSelection(codeset_id=6, is_exclusion=False),
            codeset_id=100,
            first=True,
            provider_specialty=[Concept(concept_id=7, concept_name="Cardiology")],
            age=NumericRange(op="gte", value=18, extent=65),
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01")
        )
        
        self.assertEqual(len(condition.gender), 1)
        self.assertEqual(condition.gender[0].concept_id, 8507)
        self.assertEqual(condition.stop_reason.text, "completed")
        self.assertEqual(condition.codeset_id, 100)
        self.assertTrue(condition.first)

    def test_condition_occurrence_camel_case_aliases(self):
        """Test that camelCase aliases work correctly."""
        condition = ConditionOccurrence.model_validate({
            "occurrenceEndDate": {"op": "lt", "extent": "30", "value": "2023-01-01"},
            "conditionSourceConcept": 12345,
            "genderCS": {"codesetId": 1, "isExclusion": False},
            "conditionTypeExclude": False,
            "providerSpecialtyCS": {"codesetId": 3, "isExclusion": False},
            "visitTypeCS": {"codesetId": 4, "isExclusion": False},
            "conditionStatusCS": {"codesetId": 6, "isExclusion": False},
            "codesetId": 100,
            "first": True,
            "occurrenceStartDate": {"op": "gte", "extent": "0", "value": "2020-01-01"}
        })
        
        self.assertIsNotNone(condition.occurrence_end_date)
        self.assertEqual(condition.condition_source_concept, 12345)
        self.assertEqual(condition.codeset_id, 100)
        self.assertTrue(condition.first)


class TestDrugExposure(unittest.TestCase):
    """Test DrugExposure criteria class."""

    def test_drug_exposure_initialization(self):
        """Test basic initialization of DrugExposure."""
        drug = DrugExposure(
            first=True,
            drug_type_exclude=False
        )
        self.assertTrue(drug.first)
        self.assertFalse(drug.drug_type_exclude)
        self.assertIsNone(drug.gender)
        self.assertIsNone(drug.codeset_id)

    def test_drug_exposure_with_fields(self):
        """Test DrugExposure with key fields populated."""
        drug = DrugExposure(
            gender=[Concept(concept_id=8507, concept_name="Male")],
            occurrence_end_date=DateRange(op="lt", extent="30", value="2023-01-01"),
            stop_reason=TextFilter(text="completed", op="eq"),
            drug_source_concept=12345,
            gender_cs=ConceptSetSelection(codeset_id=1, is_exclusion=False),
            drug_type=[Concept(concept_id=2, concept_name="Prescription")],
            drug_type_cs=ConceptSetSelection(codeset_id=2, is_exclusion=False),
            drug_type_exclude=False,
            provider_specialty_cs=ConceptSetSelection(codeset_id=3, is_exclusion=False),
            visit_type_cs=ConceptSetSelection(codeset_id=4, is_exclusion=False),
            visit_type=[Concept(concept_id=5, concept_name="Inpatient")],
            route_concept=[Concept(concept_id=6, concept_name="Oral")],
            route_concept_cs=ConceptSetSelection(codeset_id=7, is_exclusion=False),
            codeset_id=100,
            first=True,
            provider_specialty=[Concept(concept_id=8, concept_name="Cardiology")],
            age=NumericRange(op="gte", value=18, extent=65),
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01")
        )
        
        self.assertEqual(len(drug.gender), 1)
        self.assertEqual(drug.stop_reason.text, "completed")
        self.assertEqual(drug.codeset_id, 100)
        self.assertTrue(drug.first)

    def test_drug_exposure_camel_case_aliases(self):
        """Test that camelCase aliases work correctly."""
        drug = DrugExposure.model_validate({
            "occurrenceEndDate": {"op": "lt", "extent": "30", "value": "2023-01-01"},
            "drugSourceConcept": 12345,
            "genderCS": {"codesetId": 1, "isExclusion": False},
            "drugTypeExclude": False,
            "providerSpecialtyCS": {"codesetId": 3, "isExclusion": False},
            "visitTypeCS": {"codesetId": 4, "isExclusion": False},
            "routeConceptCS": {"codesetId": 7, "isExclusion": False},
            "codesetId": 100,
            "first": True,
            "occurrenceStartDate": {"op": "gte", "extent": "0", "value": "2020-01-01"}
        })
        
        self.assertIsNotNone(drug.occurrence_end_date)
        self.assertEqual(drug.drug_source_concept, 12345)
        self.assertEqual(drug.codeset_id, 100)
        self.assertTrue(drug.first)


class TestProcedureOccurrence(unittest.TestCase):
    """Test ProcedureOccurrence criteria class."""

    def test_procedure_occurrence_initialization(self):
        """Test basic initialization of ProcedureOccurrence."""
        procedure = ProcedureOccurrence(
            first=True,
            procedure_type_exclude=False
        )
        self.assertTrue(procedure.first)
        self.assertFalse(procedure.procedure_type_exclude)
        self.assertIsNone(procedure.gender)
        self.assertIsNone(procedure.codeset_id)

    def test_procedure_occurrence_with_fields(self):
        """Test ProcedureOccurrence with key fields populated."""
        procedure = ProcedureOccurrence(
            gender=[Concept(concept_id=8507, concept_name="Male")],
            occurrence_end_date=DateRange(op="lt", extent="30", value="2023-01-01"),
            procedure_source_concept=12345,
            gender_cs=ConceptSetSelection(codeset_id=1, is_exclusion=False),
            procedure_type=[Concept(concept_id=2, concept_name="Surgery")],
            procedure_type_cs=ConceptSetSelection(codeset_id=2, is_exclusion=False),
            procedure_type_exclude=False,
            provider_specialty_cs=ConceptSetSelection(codeset_id=3, is_exclusion=False),
            visit_type_cs=ConceptSetSelection(codeset_id=4, is_exclusion=False),
            visit_type=[Concept(concept_id=5, concept_name="Inpatient")],
            modifier=[Concept(concept_id=6, concept_name="Bilateral")],
            modifier_cs=ConceptSetSelection(codeset_id=7, is_exclusion=False),
            codeset_id=100,
            first=True,
            provider_specialty=[Concept(concept_id=8, concept_name="Surgery")],
            age=NumericRange(op="gte", value=18, extent=65),
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01")
        )
        
        self.assertEqual(len(procedure.gender), 1)
        self.assertEqual(procedure.procedure_source_concept, 12345)
        self.assertEqual(procedure.codeset_id, 100)
        self.assertTrue(procedure.first)


class TestVisitOccurrence(unittest.TestCase):
    """Test VisitOccurrence criteria class."""

    def test_visit_occurrence_initialization(self):
        """Test basic initialization of VisitOccurrence."""
        visit = VisitOccurrence(
            visit_type_exclude=False
        )
        self.assertFalse(visit.visit_type_exclude)
        self.assertIsNone(visit.gender)

    def test_visit_occurrence_with_fields(self):
        """Test VisitOccurrence with key fields populated."""
        visit = VisitOccurrence(
            gender=[Concept(concept_id=8507, concept_name="Male")],
            occurrence_end_date=DateRange(op="lt", extent="30", value="2023-01-01"),
            gender_cs=ConceptSetSelection(codeset_id=1, is_exclusion=False),
            visit_type=[Concept(concept_id=2, concept_name="Inpatient")],
            visit_type_cs=ConceptSetSelection(codeset_id=2, is_exclusion=False),
            visit_type_exclude=False,
            provider_specialty_cs=ConceptSetSelection(codeset_id=3, is_exclusion=False),
            provider_specialty=[Concept(concept_id=4, concept_name="Cardiology")],
            age=NumericRange(op="gte", value=18, extent=65),
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01")
        )
        
        self.assertEqual(len(visit.gender), 1)
        self.assertEqual(len(visit.visit_type), 1)
        self.assertEqual(visit.visit_type[0].concept_id, 2)


class TestObservation(unittest.TestCase):
    """Test Observation criteria class."""

    def test_observation_initialization(self):
        """Test basic initialization of Observation."""
        observation = Observation(
            first=True,
            observation_type_exclude=False
        )
        self.assertTrue(observation.first)
        self.assertFalse(observation.observation_type_exclude)
        self.assertIsNone(observation.gender)
        self.assertIsNone(observation.codeset_id)

    def test_observation_with_fields(self):
        """Test Observation with key fields populated."""
        observation = Observation(
            gender=[Concept(concept_id=8507, concept_name="Male")],
            occurrence_end_date=DateRange(op="lt", extent="30", value="2023-01-01"),
            observation_source_concept=12345,
            gender_cs=ConceptSetSelection(codeset_id=1, is_exclusion=False),
            observation_type=[Concept(concept_id=2, concept_name="Lab")],
            observation_type_cs=ConceptSetSelection(codeset_id=2, is_exclusion=False),
            observation_type_exclude=False,
            provider_specialty_cs=ConceptSetSelection(codeset_id=3, is_exclusion=False),
            visit_type_cs=ConceptSetSelection(codeset_id=4, is_exclusion=False),
            visit_type=[Concept(concept_id=5, concept_name="Inpatient")],
            value_as_string=TextFilter(text="normal", op="eq"),
            codeset_id=100,
            first=True,
            provider_specialty=[Concept(concept_id=6, concept_name="Lab")],
            age=NumericRange(op="gte", value=18, extent=65),
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01")
        )
        
        self.assertEqual(len(observation.gender), 1)
        self.assertEqual(observation.observation_source_concept, 12345)
        self.assertEqual(observation.value_as_string.text, "normal")
        self.assertEqual(observation.codeset_id, 100)


class TestMeasurement(unittest.TestCase):
    """Test Measurement criteria class."""

    def test_measurement_initialization(self):
        """Test basic initialization of Measurement."""
        measurement = Measurement(
            first=True,
            measurement_type_exclude=False
        )
        self.assertTrue(measurement.first)
        self.assertFalse(measurement.measurement_type_exclude)
        self.assertIsNone(measurement.gender)
        self.assertIsNone(measurement.codeset_id)

    def test_measurement_with_fields(self):
        """Test Measurement with key fields populated."""
        measurement = Measurement(
            gender=[Concept(concept_id=8507, concept_name="Male")],
            occurrence_end_date=DateRange(op="lt", extent="30", value="2023-01-01"),
            measurement_source_concept=12345,
            gender_cs=ConceptSetSelection(codeset_id=1, is_exclusion=False),
            measurement_type=[Concept(concept_id=2, concept_name="Lab")],
            measurement_type_cs=ConceptSetSelection(codeset_id=2, is_exclusion=False),
            measurement_type_exclude=False,
            operator=[Concept(concept_id=3, concept_name="Equal")],
            operator_cs=ConceptSetSelection(codeset_id=3, is_exclusion=False),
            value_as_number=NumericRange(op="gte", value=100, extent=200),
            value_as_string=TextFilter(text="high", op="eq"),
            unit=[Concept(concept_id=4, concept_name="mg/dL")],
            unit_cs=ConceptSetSelection(codeset_id=4, is_exclusion=False),
            range_low=NumericRange(op="gte", value=50, extent=100),
            range_high=NumericRange(op="lte", value=150, extent=200),
            provider_specialty_cs=ConceptSetSelection(codeset_id=5, is_exclusion=False),
            visit_type_cs=ConceptSetSelection(codeset_id=6, is_exclusion=False),
            visit_type=[Concept(concept_id=7, concept_name="Inpatient")],
            codeset_id=100,
            first=True,
            provider_specialty=[Concept(concept_id=8, concept_name="Lab")],
            age=NumericRange(op="gte", value=18, extent=65),
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01")
        )
        
        self.assertEqual(len(measurement.gender), 1)
        self.assertEqual(measurement.measurement_source_concept, 12345)
        self.assertEqual(measurement.value_as_number.value, 100)
        self.assertEqual(measurement.value_as_string.text, "high")
        self.assertEqual(measurement.codeset_id, 100)


class TestDeviceExposure(unittest.TestCase):
    """Test DeviceExposure criteria class."""

    def test_device_exposure_initialization(self):
        """Test basic initialization of DeviceExposure."""
        device = DeviceExposure(
            first=True,
            device_type_exclude=False
        )
        self.assertTrue(device.first)
        self.assertFalse(device.device_type_exclude)
        self.assertIsNone(device.gender)
        self.assertIsNone(device.codeset_id)

    def test_device_exposure_with_fields(self):
        """Test DeviceExposure with key fields populated."""
        device = DeviceExposure(
            gender=[Concept(concept_id=8507, concept_name="Male")],
            occurrence_end_date=DateRange(op="lt", extent="30", value="2023-01-01"),
            device_source_concept=12345,
            gender_cs=ConceptSetSelection(codeset_id=1, is_exclusion=False),
            device_type=[Concept(concept_id=2, concept_name="Pacemaker")],
            device_type_cs=ConceptSetSelection(codeset_id=2, is_exclusion=False),
            device_type_exclude=False,
            unique_device_id=TextFilter(text="DEVICE123", op="eq"),
            quantity=NumericRange(op="gte", value=1, extent=5),
            provider_specialty_cs=ConceptSetSelection(codeset_id=3, is_exclusion=False),
            visit_type_cs=ConceptSetSelection(codeset_id=4, is_exclusion=False),
            visit_type=[Concept(concept_id=5, concept_name="Inpatient")],
            codeset_id=100,
            first=True,
            provider_specialty=[Concept(concept_id=6, concept_name="Cardiology")],
            age=NumericRange(op="gte", value=18, extent=65),
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01")
        )
        
        self.assertEqual(len(device.gender), 1)
        self.assertEqual(device.device_source_concept, 12345)
        self.assertEqual(device.unique_device_id.text, "DEVICE123")
        self.assertEqual(device.quantity.value, 1)
        self.assertEqual(device.codeset_id, 100)


class TestSpecimen(unittest.TestCase):
    """Test Specimen criteria class."""

    def test_specimen_initialization(self):
        """Test basic initialization of Specimen."""
        specimen = Specimen(
            first=True,
            specimen_type_exclude=False
        )
        self.assertTrue(specimen.first)
        self.assertFalse(specimen.specimen_type_exclude)
        self.assertIsNone(specimen.gender)
        self.assertIsNone(specimen.codeset_id)

    def test_specimen_with_fields(self):
        """Test Specimen with key fields populated."""
        specimen = Specimen(
            gender=[Concept(concept_id=8507, concept_name="Male")],
            occurrence_end_date=DateRange(op="lt", extent="30", value="2023-01-01"),
            specimen_source_concept=12345,
            gender_cs=ConceptSetSelection(codeset_id=1, is_exclusion=False),
            specimen_type=[Concept(concept_id=2, concept_name="Blood")],
            specimen_type_cs=ConceptSetSelection(codeset_id=2, is_exclusion=False),
            specimen_type_exclude=False,
            unit=[Concept(concept_id=3, concept_name="mL")],
            unit_cs=ConceptSetSelection(codeset_id=3, is_exclusion=False),
            anatomic_site=[Concept(concept_id=4, concept_name="Arm")],
            anatomic_site_cs=ConceptSetSelection(codeset_id=4, is_exclusion=False),
            disease_status=[Concept(concept_id=5, concept_name="Normal")],
            disease_status_cs=ConceptSetSelection(codeset_id=5, is_exclusion=False),
            quantity=NumericRange(op="gte", value=5, extent=10),
            codeset_id=100,
            first=True,
            age=NumericRange(op="gte", value=18, extent=65),
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01")
        )
        
        self.assertEqual(len(specimen.gender), 1)
        self.assertEqual(specimen.specimen_source_concept, 12345)
        self.assertEqual(len(specimen.specimen_type), 1)
        self.assertEqual(specimen.quantity.value, 5)
        self.assertEqual(specimen.codeset_id, 100)


class TestDeath(unittest.TestCase):
    """Test Death criteria class."""

    def test_death_initialization(self):
        """Test basic initialization of Death."""
        death = Death(
            death_type_exclude=False
        )
        self.assertFalse(death.death_type_exclude)
        self.assertIsNone(death.gender)
        self.assertIsNone(death.codeset_id)

    def test_death_with_fields(self):
        """Test Death with key fields populated."""
        death = Death(
            gender=[Concept(concept_id=8507, concept_name="Male")],
            occurrence_end_date=DateRange(op="lt", extent="30", value="2023-01-01"),
            death_source_concept=12345,
            gender_cs=ConceptSetSelection(codeset_id=1, is_exclusion=False),
            death_type=[Concept(concept_id=2, concept_name="Natural")],
            death_type_cs=ConceptSetSelection(codeset_id=2, is_exclusion=False),
            death_type_exclude=False,
            cause_source_concept=67890,
            cause_source_concept_cs=ConceptSetSelection(codeset_id=3, is_exclusion=False),
            codeset_id=100,
            age=NumericRange(op="gte", value=18, extent=65),
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01")
        )
        
        self.assertEqual(len(death.gender), 1)
        self.assertEqual(death.death_source_concept, 12345)
        self.assertEqual(death.cause_source_concept, 67890)
        self.assertEqual(death.codeset_id, 100)


class TestEraCriteria(unittest.TestCase):
    """Test Era criteria classes."""

    def test_condition_era_initialization(self):
        """Test basic initialization of ConditionEra."""
        era = ConditionEra(
            first=True
        )
        self.assertTrue(era.first)
        self.assertIsNone(era.gender)
        self.assertIsNone(era.codeset_id)

    def test_drug_era_initialization(self):
        """Test basic initialization of DrugEra."""
        era = DrugEra(
            first=True
        )
        self.assertTrue(era.first)
        self.assertIsNone(era.gender)
        self.assertIsNone(era.codeset_id)

    def test_dose_era_initialization(self):
        """Test basic initialization of DoseEra."""
        era = DoseEra(
            first=True
        )
        self.assertTrue(era.first)
        self.assertIsNone(era.gender)
        self.assertIsNone(era.codeset_id)

    def test_era_with_fields(self):
        """Test Era classes with key fields populated."""
        condition_era = ConditionEra(
            gender=[Concept(concept_id=8507, concept_name="Male")],
            occurrence_end_date=DateRange(op="lt", extent="30", value="2023-01-01"),
            gender_cs=ConceptSetSelection(codeset_id=1, is_exclusion=False),
            era_length=NumericRange(op="gte", value=30, extent=365),
            codeset_id=100,
            first=True,
            age=NumericRange(op="gte", value=18, extent=65),
            occurrence_start_date=DateRange(op="gte", extent="0", value="2020-01-01")
        )
        
        self.assertEqual(len(condition_era.gender), 1)
        self.assertEqual(condition_era.era_length.value, 30)
        self.assertEqual(condition_era.codeset_id, 100)


class TestOtherCriteria(unittest.TestCase):
    """Test other criteria classes."""

    def test_visit_detail_initialization(self):
        """Test basic initialization of VisitDetail."""
        visit_detail = VisitDetail(
            visit_detail_type_exclude=False
        )
        self.assertFalse(visit_detail.visit_detail_type_exclude)
        self.assertIsNone(visit_detail.gender)

    def test_observation_period_initialization(self):
        """Test basic initialization of ObservationPeriod."""
        obs_period = ObservationPeriod()
        # ObservationPeriod does NOT have a gender field in Java - it only has age_at_start and age_at_end
        self.assertIsNone(obs_period.age_at_start)
        self.assertIsNone(obs_period.age_at_end)

    def test_payer_plan_period_initialization(self):
        """Test basic initialization of PayerPlanPeriod."""
        payer_plan = PayerPlanPeriod()
        self.assertIsNone(payer_plan.gender)

    def test_location_region_initialization(self):
        """Test basic initialization of LocationRegion."""
        location = LocationRegion()
        self.assertIsNone(location.codeset_id)

    def test_geo_criteria_initialization(self):
        """Test basic initialization of GeoCriteria."""
        geo = GeoCriteria()
        self.assertIsNone(geo.date_adjustment)
        self.assertIsNone(geo.correlated_criteria)
        self.assertIsNone(geo.include)


if __name__ == '__main__':
    unittest.main()
