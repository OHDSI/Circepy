
import unittest
from unittest.mock import Mock, call

from circe.check.checkers.concept_checker_factory import ConceptCheckerFactory
from circe.check.constants import Constants
from circe.cohortdefinition.criteria import (
    ConditionEra,
    ConditionOccurrence,
    Death,
    DemographicCriteria,
    DeviceExposure,
    DoseEra,
    DrugEra,
    DrugExposure,
    Measurement,
    Observation,
    ObservationPeriod,
    PayerPlanPeriod,
    ProcedureOccurrence,
    Specimen,
    VisitOccurrence,
)


class TestConceptCheckerFactoryCoverage(unittest.TestCase):
    def setUp(self):
        self.reporter = Mock()
        self.group_name = "Test Group"
        self.factory = ConceptCheckerFactory.get_factory(self.reporter, self.group_name)

    def test_check_condition_era(self):
        # Gender is checked
        c = ConditionEra(codeset_id=0, gender=[])
        self.factory.check(c)
        self.reporter.assert_called_with(
            self.factory.WARNING_EMPTY_VALUE,
            self.group_name,
            Constants.Criteria.CONDITION_ERA,
            Constants.Attributes.GENDER_ATTR
        )

    def test_check_condition_occurrence(self):
        c = ConditionOccurrence(
            codeset_id=0,
            condition_type=[],
            gender=[],
            provider_specialty=[],
            visit_type=[]
        )
        self.factory.check(c)
        # Should report all 4
        calls = [
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.CONDITION_OCCURRENCE, Constants.Attributes.CONDITION_TYPE_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.CONDITION_OCCURRENCE, Constants.Attributes.GENDER_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.CONDITION_OCCURRENCE, Constants.Attributes.PROVIDER_SPECIALITY_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.CONDITION_OCCURRENCE, Constants.Attributes.VISIT_TYPE_ATTR),
        ]
        self.reporter.assert_has_calls(calls, any_order=True)

    def test_check_death(self):
        c = Death(
            codeset_id=0,
            death_type=[],
            gender=[]
        )
        self.factory.check(c)
        calls = [
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.DEATH, Constants.Attributes.DEATH_TYPE_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.DEATH, Constants.Attributes.GENDER_ATTR),
        ]
        self.reporter.assert_has_calls(calls, any_order=True)

    def test_check_device_exposure(self):
        c = DeviceExposure(
            codeset_id=0,
            device_type=[],
            gender=[],
            provider_specialty=[],
            visit_type=[]
        )
        self.factory.check(c)
        calls = [
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.DEVICE_EXPOSURE, Constants.Attributes.DEVICE_TYPE_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.DEVICE_EXPOSURE, Constants.Attributes.GENDER_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.DEVICE_EXPOSURE, Constants.Attributes.PROVIDER_SPECIALITY_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.DEVICE_EXPOSURE, Constants.Attributes.VISIT_TYPE_ATTR),
        ]
        self.reporter.assert_has_calls(calls, any_order=True)

    def test_check_dose_era(self):
        c = DoseEra(
            codeset_id=0,
            unit=[],
            gender=[]
        )
        self.factory.check(c)
        calls = [
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.DOSE_ERA, Constants.Attributes.UNIT_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.DOSE_ERA, Constants.Attributes.GENDER_ATTR),
        ]
        self.reporter.assert_has_calls(calls, any_order=True)

    def test_check_drug_era(self):
        c = DrugEra(
            codeset_id=0,
            gender=[]
        )
        self.factory.check(c)
        self.reporter.assert_called_with(
            self.factory.WARNING_EMPTY_VALUE, 
            self.group_name, 
            Constants.Criteria.DRUG_ERA, 
            Constants.Attributes.GENDER_ATTR
        )

    def test_check_drug_exposure(self):
        c = DrugExposure(
            codeset_id=0,
            drug_type=[],
            route_concept=[],
            dose_unit=[],
            gender=[],
            provider_specialty=[],
            visit_type=[]
        )
        self.factory.check(c)
        calls = [
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.DRUG_EXPOSURE, Constants.Attributes.DRUG_TYPE_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.DRUG_EXPOSURE, Constants.Attributes.ROUTE_CONCEPT_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.DRUG_EXPOSURE, Constants.Attributes.DOSE_UNIT_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.DRUG_EXPOSURE, Constants.Attributes.GENDER_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.DRUG_EXPOSURE, Constants.Attributes.PROVIDER_SPECIALITY_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.DRUG_EXPOSURE, Constants.Attributes.VISIT_TYPE_ATTR),
        ]
        self.reporter.assert_has_calls(calls, any_order=True)

    def test_check_measurement(self):
        c = Measurement(
            codeset_id=0,
            measurement_type=[],
            operator=[],
            value_as_concept=[],
            unit=[],
            gender=[],
            provider_specialty=[],
            visit_type=[]
        )
        self.factory.check(c)
        calls = [
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.MEASUREMENT, Constants.Attributes.MEASUREMENT_TYPE_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.MEASUREMENT, Constants.Attributes.OPERATOR_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.MEASUREMENT, Constants.Attributes.VALUE_AS_CONCEPT_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.MEASUREMENT, Constants.Attributes.UNIT_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.MEASUREMENT, Constants.Attributes.GENDER_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.MEASUREMENT, Constants.Attributes.PROVIDER_SPECIALITY_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.MEASUREMENT, Constants.Attributes.VISIT_TYPE_ATTR),
        ]
        self.reporter.assert_has_calls(calls, any_order=True)

    def test_check_observation(self):
        c = Observation(
            codeset_id=0,
            observation_type=[],
            value_as_concept=[],
            qualifier=[],
            unit=[],
            gender=[],
            provider_specialty=[],
            visit_type=[]
        )
        self.factory.check(c)
        calls = [
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.OBSERVATION, Constants.Attributes.OBSERVATION_TYPE_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.OBSERVATION, Constants.Attributes.VALUE_AS_CONCEPT_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.OBSERVATION, Constants.Attributes.QUALIFIER_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.OBSERVATION, Constants.Attributes.UNIT_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.OBSERVATION, Constants.Attributes.GENDER_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.OBSERVATION, Constants.Attributes.PROVIDER_SPECIALITY_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.OBSERVATION, Constants.Attributes.VISIT_TYPE_ATTR),
        ]
        self.reporter.assert_has_calls(calls, any_order=True)

    def test_check_observation_period(self):
        c = ObservationPeriod(
            period_type=[]
        )
        self.factory.check(c)
        self.reporter.assert_called_with(
            self.factory.WARNING_EMPTY_VALUE,
            self.group_name,
            Constants.Criteria.OBSERVATION_PERIOD,
            Constants.Attributes.PERIOD_TYPE_ATTR
        )

    def test_check_procedure_occurrence(self):
        c = ProcedureOccurrence(
            codeset_id=0,
            procedure_type=[],
            modifier=[],
            gender=[],
            provider_specialty=[],
            visit_type=[]
        )
        self.factory.check(c)
        calls = [
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.PROCEDURE_OCCURRENCE, Constants.Attributes.PROCEDURE_TYPE_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.PROCEDURE_OCCURRENCE, Constants.Attributes.MODIFIER_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.PROCEDURE_OCCURRENCE, Constants.Attributes.GENDER_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.PROCEDURE_OCCURRENCE, Constants.Attributes.PROVIDER_SPECIALITY_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.PROCEDURE_OCCURRENCE, Constants.Attributes.VISIT_TYPE_ATTR),
        ]
        self.reporter.assert_has_calls(calls, any_order=True)

    def test_check_specimen(self):
        c = Specimen(
            codeset_id=0,
            specimen_type=[],
            unit=[],
            anatomic_site=[],
            disease_status=[],
            gender=[]
        )
        self.factory.check(c)
        calls = [
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.SPECIMEN, Constants.Attributes.SPECIMEN_TYPE_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.SPECIMEN, Constants.Attributes.UNIT_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.SPECIMEN, Constants.Attributes.ANATOMIC_SITE_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.SPECIMEN, Constants.Attributes.DISEASE_STATUS_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.SPECIMEN, Constants.Attributes.GENDER_ATTR),
        ]
        self.reporter.assert_has_calls(calls, any_order=True)

    def test_check_visit_occurrence(self):
        c = VisitOccurrence(
            codeset_id=0,
            visit_type=[],
            gender=[],
            provider_specialty=[],
            place_of_service=[]
        )
        self.factory.check(c)
        calls = [
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.VISIT_OCCURRENCE, Constants.Attributes.VISIT_TYPE_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.VISIT_OCCURRENCE, Constants.Attributes.GENDER_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.VISIT_OCCURRENCE, Constants.Attributes.PROVIDER_SPECIALITY_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.VISIT_OCCURRENCE, Constants.Attributes.PLACE_OF_SERVICE_ATTR),
        ]
        self.reporter.assert_has_calls(calls, any_order=True)

    def test_check_payer_plan_period(self):
        c = PayerPlanPeriod(
            gender=[]
        )
        self.factory.check(c)
        self.reporter.assert_called_with(
            self.factory.WARNING_EMPTY_VALUE,
            self.group_name,
            Constants.Criteria.PAYER_PLAN_PERIOD,
            Constants.Attributes.GENDER_ATTR
        )

    def test_check_demographic_criteria(self):
        c = DemographicCriteria(
            ethnicity=[],
            gender=[],
            race=[]
        )
        # DemographicCriteria needs special handling because it's distinct from Criteria in dispatch
        self.factory.check(c)
        calls = [
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.DEMOGRAPHIC, Constants.Attributes.ETHNICITY_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.DEMOGRAPHIC, Constants.Attributes.GENDER_ATTR),
            call(self.factory.WARNING_EMPTY_VALUE, self.group_name, Constants.Criteria.DEMOGRAPHIC, Constants.Attributes.RACE_ATTR),
        ]
        self.reporter.assert_has_calls(calls, any_order=True)

    def test_default_check(self):
        # Use LocationRegion which is not handled by ConceptCheckerFactory
        from circe.cohortdefinition.criteria import LocationRegion
        
        c = LocationRegion()
        self.factory.check(c)
        # Should not call reporter
        self.reporter.assert_not_called()

    def test_check_valid_concepts(self):
        # Test that populated lists do not trigger warnings
        from circe.vocabulary.concept import Concept
        c = ConditionEra(
            codeset_id=0,
            gender=[Concept(concept_id=1, concept_name="Male", domain_id="Gender", vocabulary_id="Gender")]
        )
        self.factory.check(c)
        self.reporter.assert_not_called()

