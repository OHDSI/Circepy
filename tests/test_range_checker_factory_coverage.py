import unittest
from unittest.mock import Mock, call, patch

from circe.check.checkers.range_checker_factory import RangeCheckerFactory
from circe.check.constants import Constants
from circe.cohortdefinition.cohort import CohortExpression
from circe.cohortdefinition.core import DateRange, NumericRange, Period
from circe.cohortdefinition.criteria import (
    ConditionEra,
    ConditionOccurrence,
    Death,
    DemographicCriteria,
    DeviceExposure,
    DoseEra,
    DrugEra,
    DrugExposure,
    LocationRegion,
    Measurement,
    Observation,
    ObservationPeriod,
    PayerPlanPeriod,
    ProcedureOccurrence,
    Specimen,
    VisitDetail,
    VisitOccurrence,
)


class TestRangeCheckerFactoryCoverage(unittest.TestCase):
    def setUp(self):
        self.reporter = Mock()
        self.group_name = "Test Group"
        self.factory = RangeCheckerFactory.get_factory(self.reporter, self.group_name)

    def test_check_condition_era(self):
        c = ConditionEra(codeset_id=0)
        with patch.object(self.factory, "_check_range") as mock_check:
            self.factory.check(c)
            calls = [
                call(
                    c.age_at_start,
                    Constants.Criteria.CONDITION_ERA,
                    Constants.Attributes.AGE_AT_ERA_START_ATTR,
                ),
                call(
                    c.age_at_end,
                    Constants.Criteria.CONDITION_ERA,
                    Constants.Attributes.AGE_AT_ERA_END_ATTR,
                ),
                call(
                    c.era_length,
                    Constants.Criteria.CONDITION_ERA,
                    Constants.Attributes.ERA_LENGTH_ATTR,
                ),
                call(
                    c.occurrence_count,
                    Constants.Criteria.CONDITION_ERA,
                    Constants.Attributes.OCCURRENCE_COUNT_ATTR,
                ),
                call(
                    c.era_start_date,
                    Constants.Criteria.CONDITION_ERA,
                    Constants.Attributes.ERA_START_DATE_ATTR,
                ),
                call(
                    c.era_end_date,
                    Constants.Criteria.CONDITION_ERA,
                    Constants.Attributes.ERA_END_DATE_ATTR,
                ),
            ]
            mock_check.assert_has_calls(calls, any_order=True)

    def test_check_condition_occurrence(self):
        c = ConditionOccurrence(codeset_id=0)
        with patch.object(self.factory, "_check_range") as mock_check:
            self.factory.check(c)
            calls = [
                call(
                    c.occurrence_start_date,
                    Constants.Criteria.CONDITION_OCCURRENCE,
                    Constants.Attributes.OCCURRENCE_START_DATE_ATTR,
                ),
                call(
                    c.occurrence_end_date,
                    Constants.Criteria.CONDITION_OCCURRENCE,
                    Constants.Attributes.OCCURRENCE_END_DATE_ATTR,
                ),
                call(
                    c.age,
                    Constants.Criteria.CONDITION_OCCURRENCE,
                    Constants.Attributes.AGE_ATTR,
                ),
            ]
            mock_check.assert_has_calls(calls, any_order=True)

    def test_check_death(self):
        c = Death(codeset_id=0)
        with patch.object(self.factory, "_check_range") as mock_check:
            self.factory.check(c)
            calls = [
                call(c.age, Constants.Criteria.DEATH, Constants.Attributes.AGE_ATTR),
                call(
                    c.occurrence_start_date,
                    Constants.Criteria.DEATH,
                    Constants.Attributes.OCCURRENCE_START_DATE_ATTR,
                ),
            ]
            mock_check.assert_has_calls(calls, any_order=True)

    def test_check_device_exposure(self):
        c = DeviceExposure(codeset_id=0)
        with patch.object(self.factory, "_check_range") as mock_check:
            self.factory.check(c)
            calls = [
                call(
                    c.occurrence_start_date,
                    Constants.Criteria.DEVICE_EXPOSURE,
                    Constants.Attributes.OCCURRENCE_START_DATE_ATTR,
                ),
                call(
                    c.occurrence_end_date,
                    Constants.Criteria.DEVICE_EXPOSURE,
                    Constants.Attributes.OCCURRENCE_END_DATE_ATTR,
                ),
                call(
                    c.quantity,
                    Constants.Criteria.DEVICE_EXPOSURE,
                    Constants.Attributes.QUANTITY_ATTR,
                ),
                call(
                    c.age,
                    Constants.Criteria.DEVICE_EXPOSURE,
                    Constants.Attributes.AGE_ATTR,
                ),
            ]
            mock_check.assert_has_calls(calls, any_order=True)

    def test_check_dose_era(self):
        c = DoseEra(codeset_id=0)
        with patch.object(self.factory, "_check_range") as mock_check:
            self.factory.check(c)
            calls = [
                call(
                    c.era_start_date,
                    Constants.Criteria.DOSE_ERA,
                    Constants.Attributes.ERA_START_DATE_ATTR,
                ),
                call(
                    c.era_end_date,
                    Constants.Criteria.DOSE_ERA,
                    Constants.Attributes.ERA_END_DATE_ATTR,
                ),
                call(
                    c.dose_value,
                    Constants.Criteria.DOSE_ERA,
                    Constants.Attributes.DOSE_VALUE_ATTR,
                ),
                call(
                    c.era_length,
                    Constants.Criteria.DOSE_ERA,
                    Constants.Attributes.ERA_LENGTH_ATTR,
                ),
                call(
                    c.age_at_start,
                    Constants.Criteria.DOSE_ERA,
                    Constants.Attributes.AGE_AT_START_ATTR,
                ),
                call(
                    c.age_at_end,
                    Constants.Criteria.DOSE_ERA,
                    Constants.Attributes.AGE_AT_END_ATTR,
                ),
            ]
            mock_check.assert_has_calls(calls, any_order=True)

    def test_check_drug_era(self):
        c = DrugEra(codeset_id=0)
        with patch.object(self.factory, "_check_range") as mock_check:
            self.factory.check(c)
            calls = [
                call(
                    c.era_start_date,
                    Constants.Criteria.DRUG_ERA,
                    Constants.Attributes.ERA_START_DATE_ATTR,
                ),
                call(
                    c.era_end_date,
                    Constants.Criteria.DRUG_ERA,
                    Constants.Attributes.ERA_END_DATE_ATTR,
                ),
                call(
                    c.occurrence_count,
                    Constants.Criteria.DRUG_ERA,
                    Constants.Attributes.OCCURRENCE_COUNT_ATTR,
                ),
                call(
                    c.gap_days,
                    Constants.Criteria.DRUG_ERA,
                    Constants.Attributes.GAP_DAYS_ATTR,
                ),
                call(
                    c.era_length,
                    Constants.Criteria.DRUG_ERA,
                    Constants.Attributes.ERA_LENGTH_ATTR,
                ),
                call(
                    c.age_at_start,
                    Constants.Criteria.DRUG_ERA,
                    Constants.Attributes.AGE_AT_START_ATTR,
                ),
                call(
                    c.age_at_end,
                    Constants.Criteria.DRUG_ERA,
                    Constants.Attributes.AGE_AT_END_ATTR,
                ),
            ]
            mock_check.assert_has_calls(calls, any_order=True)

    def test_check_drug_exposure(self):
        c = DrugExposure(codeset_id=0)
        with patch.object(self.factory, "_check_range") as mock_check:
            self.factory.check(c)
            calls = [
                call(
                    c.occurrence_start_date,
                    Constants.Criteria.DRUG_EXPOSURE,
                    Constants.Attributes.OCCURRENCE_START_DATE_ATTR,
                ),
                call(
                    c.occurrence_end_date,
                    Constants.Criteria.DRUG_EXPOSURE,
                    Constants.Attributes.OCCURRENCE_END_DATE_ATTR,
                ),
                call(
                    c.refills,
                    Constants.Criteria.DRUG_EXPOSURE,
                    Constants.Attributes.REFILLS_ATTR,
                ),
                call(
                    c.quantity,
                    Constants.Criteria.DRUG_EXPOSURE,
                    Constants.Attributes.QUANTITY_ATTR,
                ),
                call(
                    c.days_supply,
                    Constants.Criteria.DRUG_EXPOSURE,
                    Constants.Attributes.DAYS_SUPPLY_ATTR,
                ),
                call(
                    c.effective_drug_dose,
                    Constants.Criteria.DRUG_EXPOSURE,
                    Constants.Attributes.EFFECTIVE_DRUG_DOSE_ATTR,
                ),
                call(
                    c.age,
                    Constants.Criteria.DRUG_EXPOSURE,
                    Constants.Attributes.AGE_ATTR,
                ),
            ]
            mock_check.assert_has_calls(calls, any_order=True)

    def test_check_measurement(self):
        c = Measurement(codeset_id=0)
        with patch.object(self.factory, "_check_range") as mock_check:
            self.factory.check(c)
            calls = [
                call(
                    c.occurrence_start_date,
                    Constants.Criteria.MEASUREMENT,
                    Constants.Attributes.OCCURRENCE_START_DATE_ATTR,
                ),
                call(
                    c.value_as_number,
                    Constants.Criteria.MEASUREMENT,
                    Constants.Attributes.VALUE_AS_NUMBER_ATTR,
                ),
                call(
                    c.range_low,
                    Constants.Criteria.MEASUREMENT,
                    Constants.Attributes.RANGE_LOW_ATTR,
                ),
                call(
                    c.range_high,
                    Constants.Criteria.MEASUREMENT,
                    Constants.Attributes.RANGE_HIGH_ATTR,
                ),
                call(
                    c.range_low_ratio,
                    Constants.Criteria.MEASUREMENT,
                    Constants.Attributes.RANGE_LOW_RATIO_ATTR,
                ),
                call(
                    c.range_high_ratio,
                    Constants.Criteria.MEASUREMENT,
                    Constants.Attributes.RANGE_HIGH_RATIO_ATTR,
                ),
                call(
                    c.age, Constants.Criteria.MEASUREMENT, Constants.Attributes.AGE_ATTR
                ),
            ]
            mock_check.assert_has_calls(calls, any_order=True)

    def test_check_observation(self):
        c = Observation(codeset_id=0)
        with patch.object(self.factory, "_check_range") as mock_check:
            self.factory.check(c)
            calls = [
                call(
                    c.occurrence_start_date,
                    Constants.Criteria.OBSERVATION,
                    Constants.Attributes.OCCURRENCE_START_DATE_ATTR,
                ),
                call(
                    c.value_as_number,
                    Constants.Criteria.OBSERVATION,
                    Constants.Attributes.VALUE_AS_NUMBER_ATTR,
                ),
                call(
                    c.age, Constants.Criteria.OBSERVATION, Constants.Attributes.AGE_ATTR
                ),
            ]
            mock_check.assert_has_calls(calls, any_order=True)

    def test_check_observation_period(self):
        c = ObservationPeriod()
        with patch.object(self.factory, "_check_range") as mock_check:
            self.factory.check(c)
            calls = [
                call(
                    c.period_start_date,
                    Constants.Criteria.OBSERVATION_PERIOD,
                    Constants.Attributes.PERIOD_START_DATE_ATTR,
                ),
                call(
                    c.period_end_date,
                    Constants.Criteria.OBSERVATION_PERIOD,
                    Constants.Attributes.PERIOD_END_DATE_ATTR,
                ),
                call(
                    c.period_length,
                    Constants.Criteria.OBSERVATION_PERIOD,
                    Constants.Attributes.PERIOD_LENGTH_ATTR,
                ),
                call(
                    c.age_at_start,
                    Constants.Criteria.OBSERVATION_PERIOD,
                    Constants.Attributes.AGE_AT_START_ATTR,
                ),
                call(
                    c.age_at_end,
                    Constants.Criteria.OBSERVATION_PERIOD,
                    Constants.Attributes.AGE_AT_END_ATTR,
                ),
                call(
                    c.user_defined_period,
                    Constants.Criteria.OBSERVATION_PERIOD,
                    Constants.Attributes.USER_DEFINED_PERIOD_ATTR,
                ),
            ]
            mock_check.assert_has_calls(calls, any_order=True)

    def test_check_procedure_occurrence(self):
        c = ProcedureOccurrence(codeset_id=0)
        with patch.object(self.factory, "_check_range") as mock_check:
            self.factory.check(c)
            calls = [
                call(
                    c.occurrence_start_date,
                    Constants.Criteria.PROCEDURE_OCCURRENCE,
                    Constants.Attributes.OCCURRENCE_START_DATE_ATTR,
                ),
                call(
                    c.quantity,
                    Constants.Criteria.PROCEDURE_OCCURRENCE,
                    Constants.Attributes.QUANTITY_ATTR,
                ),
                call(
                    c.age,
                    Constants.Criteria.PROCEDURE_OCCURRENCE,
                    Constants.Attributes.AGE_ATTR,
                ),
            ]
            mock_check.assert_has_calls(calls, any_order=True)

    def test_check_specimen(self):
        c = Specimen(codeset_id=0)
        with patch.object(self.factory, "_check_range") as mock_check:
            self.factory.check(c)
            calls = [
                call(
                    c.occurrence_start_date,
                    Constants.Criteria.SPECIMEN,
                    Constants.Attributes.OCCURRENCE_START_DATE_ATTR,
                ),
                call(
                    c.quantity,
                    Constants.Criteria.SPECIMEN,
                    Constants.Attributes.QUANTITY_ATTR,
                ),
                call(c.age, Constants.Criteria.SPECIMEN, Constants.Attributes.AGE_ATTR),
            ]
            mock_check.assert_has_calls(calls, any_order=True)

    def test_check_visit_occurrence(self):
        c = VisitOccurrence(codeset_id=0)
        with patch.object(self.factory, "_check_range") as mock_check:
            self.factory.check(c)
            calls = [
                call(
                    c.occurrence_start_date,
                    Constants.Criteria.VISIT_OCCURRENCE,
                    Constants.Attributes.OCCURRENCE_START_DATE_ATTR,
                ),
                call(
                    c.occurrence_end_date,
                    Constants.Criteria.VISIT_OCCURRENCE,
                    Constants.Attributes.OCCURRENCE_END_DATE_ATTR,
                ),
                call(
                    c.visit_length,
                    Constants.Criteria.VISIT_OCCURRENCE,
                    Constants.Attributes.VISIT_LENGTH_ATTR,
                ),
                call(
                    c.age,
                    Constants.Criteria.VISIT_OCCURRENCE,
                    Constants.Attributes.AGE_ATTR,
                ),
            ]
            mock_check.assert_has_calls(calls, any_order=True)

    def test_check_visit_detail(self):
        c = VisitDetail()
        with patch.object(self.factory, "_check_range") as mock_check:
            self.factory.check(c)
            calls = [
                call(
                    c.visit_detail_start_date,
                    Constants.Criteria.VISIT_DETAIL,
                    Constants.Attributes.VISIT_DETAIL_START_DATE_ATTR,
                ),
                call(
                    c.visit_detail_end_date,
                    Constants.Criteria.VISIT_DETAIL,
                    Constants.Attributes.VISIT_DETAIL_END_DATE_ATTR,
                ),
                call(
                    c.visit_detail_length,
                    Constants.Criteria.VISIT_DETAIL,
                    Constants.Attributes.VISIT_DETAIL_LENGTH_ATTR,
                ),
                call(
                    c.age,
                    Constants.Criteria.VISIT_DETAIL,
                    Constants.Attributes.AGE_ATTR,
                ),
            ]
            mock_check.assert_has_calls(calls, any_order=True)

    def test_check_payer_plan_period(self):
        c = PayerPlanPeriod()
        with patch.object(self.factory, "_check_range") as mock_check:
            self.factory.check(c)
            calls = [
                call(
                    c.period_start_date,
                    Constants.Criteria.PAYER_PLAN_PERIOD,
                    Constants.Attributes.PERIOD_START_DATE_ATTR,
                ),
                call(
                    c.period_end_date,
                    Constants.Criteria.PAYER_PLAN_PERIOD,
                    Constants.Attributes.PERIOD_END_DATE_ATTR,
                ),
                call(
                    c.period_length,
                    Constants.Criteria.PAYER_PLAN_PERIOD,
                    Constants.Attributes.PERIOD_LENGTH_ATTR,
                ),
                call(
                    c.age_at_start,
                    Constants.Criteria.PAYER_PLAN_PERIOD,
                    Constants.Attributes.AGE_AT_START_ATTR,
                ),
                call(
                    c.age_at_end,
                    Constants.Criteria.PAYER_PLAN_PERIOD,
                    Constants.Attributes.AGE_AT_END_ATTR,
                ),
                call(
                    c.user_defined_period,
                    Constants.Criteria.PAYER_PLAN_PERIOD,
                    Constants.Attributes.USER_DEFINED_PERIOD_ATTR,
                ),
            ]
            mock_check.assert_has_calls(calls, any_order=True)

    def test_check_location_region(self):
        c = LocationRegion()
        # Workaround: LocationRegion class def is missing these fields, but Factory checks them.
        # Bypass Pydantic validation to add them.
        object.__setattr__(c, "start_date", DateRange(value="2020-01-01"))
        object.__setattr__(c, "end_date", DateRange(value="2020-01-02"))

        with patch.object(self.factory, "_check_range") as mock_check:
            self.factory.check(c)
            calls = [
                call(
                    c.end_date,
                    Constants.Criteria.LOCATION_REGION,
                    Constants.Attributes.LOCATION_REGION_START_DATE_ATTR,
                ),
                call(
                    c.start_date,
                    Constants.Criteria.LOCATION_REGION,
                    Constants.Attributes.LOCATION_REGION_END_DATE_ATTR,
                ),
            ]
            mock_check.assert_has_calls(calls, any_order=True)

    def test_check_demographic_criteria(self):
        c = DemographicCriteria()
        with patch.object(self.factory, "_check_range") as mock_check:
            self.factory.check(c)
            calls = [
                call(
                    c.occurrence_end_date,
                    Constants.Criteria.DEMOGRAPHIC,
                    Constants.Attributes.OCCURRENCE_END_DATE_ATTR,
                ),
                call(
                    c.occurrence_start_date,
                    Constants.Criteria.DEMOGRAPHIC,
                    Constants.Attributes.OCCURRENCE_START_DATE_ATTR,
                ),
                call(
                    c.age, Constants.Criteria.DEMOGRAPHIC, Constants.Attributes.AGE_ATTR
                ),
            ]
            mock_check.assert_has_calls(calls, any_order=True)

    def test_check_default(self):
        # Unhandled criteria should just return (noop)
        # Must inherit from Criteria to bypass BaseCheckerFactory check and reach _get_check_criteria
        from pydantic import BaseModel

        from circe.cohortdefinition.criteria import Criteria

        # Pydantic requires forward references to be resolved.
        # Since 'Criteria' definition refers to 'CriteriaGroup', we need to mock it
        # or at least ensure it's available for the new subclass to be built.
        # We'll define a dummy CriteriaGroup to satisfy the forward ref.
        class CriteriaGroup(BaseModel):
            pass

        class UnknownCriteria(Criteria):
            pass

        c = UnknownCriteria()

        with patch.object(
            self.factory, "_get_check_criteria", wraps=self.factory._get_check_criteria
        ) as mock_get:
            self.factory.check(c)
            # Verify that we actually reached the factory method
            mock_get.assert_called_with(c)

        # No error, no mocked calls (because _check_range not reachable if no match)
        # To be safe, verify no reporter calls are made
        self.reporter.assert_not_called()

    # --- Test Logic of _check_range with DateRange ---

    def test_check_range_date_invalid(self):
        # Invalid date string
        dr = DateRange(value="invalid-date", op="eq")
        self.factory._check_range(dr, "TestCriteria", "TestAttr")
        self.reporter.assert_called_with(
            self.factory.WARNING_DATE_IS_INVALID,
            "Test Group",
            "TestCriteria",
            "TestAttr",
        )

    def test_check_range_date_bt_empty_start(self):
        # 'bt' op but missing value (start). Provide extent so we only get one warning.
        dr = DateRange(op="bt", value=None, extent="2020-01-01")
        self.factory._check_range(dr, "TestCriteria", "TestAttr")
        self.reporter.assert_called_with(
            self.factory.WARNING_EMPTY_START_VALUE,
            "Test Group",
            "TestCriteria",
            "TestAttr",
        )

    def test_check_range_date_bt_empty_end(self):
        # 'bt' op but missing extent (end). Provide value so we only get one warning.
        dr = DateRange(op="bt", value="2020-01-01", extent=None)
        self.factory._check_range(dr, "TestCriteria", "TestAttr")
        self.reporter.assert_called_with(
            self.factory.WARNING_EMPTY_END_VALUE,
            "Test Group",
            "TestCriteria",
            "TestAttr",
        )

    def test_check_range_date_bt_invalid_end(self):
        # 'bt' op with invalid extent
        dr = DateRange(op="bt", value="2020-01-01", extent="bad-date")
        self.factory._check_range(dr, "TestCriteria", "TestAttr")
        self.reporter.assert_called_with(
            self.factory.WARNING_DATE_IS_INVALID,
            "Test Group",
            "TestCriteria",
            "TestAttr",
        )

    def test_check_range_date_bt_start_gt_end(self):
        # 'bt' start > end
        dr = DateRange(op="bt", value="2020-02-01", extent="2020-01-01")
        self.factory._check_range(dr, "TestCriteria", "TestAttr")
        self.reporter.assert_called_with(
            self.factory.WARNING_START_GREATER_THAN_END,
            "Test Group",
            "TestCriteria",
            "TestAttr",
        )

    def test_check_range_date_other_op_empty(self):
        # non-bt op with empty value
        dr = DateRange(op="gt", value=None)
        self.factory._check_range(dr, "TestCriteria", "TestAttr")
        self.reporter.assert_called_with(
            self.factory.WARNING_EMPTY_START_VALUE,
            "Test Group",
            "TestCriteria",
            "TestAttr",
        )

    # --- Test Logic of _check_range with NumericRange ---

    def test_check_range_numeric_bt_empty_start(self):
        # Provide extent to avoid double warning
        nr = NumericRange(op="bt", value=None, extent=10)
        self.factory._check_range(nr, "TestCriteria", "TestAttr")
        self.reporter.assert_called_with(
            self.factory.WARNING_EMPTY_START_VALUE,
            "Test Group",
            "TestCriteria",
            "TestAttr",
        )

    def test_check_range_numeric_bt_empty_end(self):
        # Provide value to avoid double warning
        nr = NumericRange(op="bt", value=10, extent=None)
        self.factory._check_range(nr, "TestCriteria", "TestAttr")
        self.reporter.assert_called_with(
            self.factory.WARNING_EMPTY_END_VALUE,
            "Test Group",
            "TestCriteria",
            "TestAttr",
        )

    def test_check_range_numeric_bt_start_gt_end(self):
        nr = NumericRange(op="bt", value=20, extent=10)
        self.factory._check_range(nr, "TestCriteria", "TestAttr")
        self.reporter.assert_called_with(
            self.factory.WARNING_START_GREATER_THAN_END,
            "Test Group",
            "TestCriteria",
            "TestAttr",
        )

    def test_check_range_numeric_other_op_empty(self):
        nr = NumericRange(op="gt", value=None)
        self.factory._check_range(nr, "TestCriteria", "TestAttr")
        self.reporter.assert_called_with(
            self.factory.WARNING_EMPTY_START_VALUE,
            "Test Group",
            "TestCriteria",
            "TestAttr",
        )

    def test_check_range_none(self):
        self.factory._check_range(None, "TestCriteria", "TestAttr")
        self.reporter.assert_not_called()

    # --- Test check_range (Period) ---

    def test_check_range_period_none(self):
        self.factory.check_range(None, "TestCriteria", "TestAttr")
        self.reporter.assert_not_called()

    def test_check_range_period_invalid_start(self):
        p = Period(start_date="bad-date")
        self.factory.check_range(p, "TestCriteria", "TestAttr")
        self.reporter.assert_called_with(
            self.factory.WARNING_DATE_IS_INVALID,
            "Test Group",
            "TestCriteria",
            "TestAttr",
        )

    def test_check_range_period_invalid_end(self):
        p = Period(start_date="2020-01-01", end_date="bad-date")
        self.factory.check_range(p, "TestCriteria", "TestAttr")
        self.reporter.assert_called_with(
            self.factory.WARNING_DATE_IS_INVALID,
            "Test Group",
            "TestCriteria",
            "TestAttr",
        )

    def test_check_range_period_start_gt_end(self):
        p = Period(start_date="2020-02-01", end_date="2020-01-01")
        self.factory.check_range(p, "TestCriteria", "TestAttr")
        self.reporter.assert_called_with(
            self.factory.WARNING_START_GREATER_THAN_END,
            "Test Group",
            "TestCriteria",
            "TestAttr",
        )

    # --- Test check(expression) for censor window ---

    def test_check_cohort_expression_censor_window(self):
        ce = CohortExpression(censor_window=Period(start_date="bad-date"))
        self.factory.check(ce)
        self.reporter.assert_called_with(
            self.factory.WARNING_DATE_IS_INVALID,
            "Test Group",
            self.factory.ROOT_OBJECT,
            Constants.Attributes.CENSOR_WINDOW_ATTR,
        )
