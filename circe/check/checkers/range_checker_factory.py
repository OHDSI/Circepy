"""
RangeCheckerFactory class.

This module provides a factory for checking range values (NumericRange, DateRange, Period) in criteria.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Callable, Optional
from ..constants import Constants
from .base_checker_factory import BaseCheckerFactory
from .warning_reporter import WarningReporter
from .comparisons import Comparisons
from ..operations.operations import Operations

# Import at runtime to avoid circular dependencies
try:
    from ...cohortdefinition.criteria import (
        Criteria, DemographicCriteria, ConditionEra, ConditionOccurrence,
        Death, DeviceExposure, DoseEra, DrugEra, DrugExposure, Measurement,
        Observation, ObservationPeriod, ProcedureOccurrence, Specimen,
        VisitOccurrence, VisitDetail, PayerPlanPeriod, LocationRegion
    )
    from ...cohortdefinition.core import NumericRange, DateRange, Period
    from ...cohortdefinition.cohort import CohortExpression
except ImportError:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from ...cohortdefinition.criteria import (
            Criteria, DemographicCriteria, ConditionEra, ConditionOccurrence,
            Death, DeviceExposure, DoseEra, DrugEra, DrugExposure, Measurement,
            Observation, ObservationPeriod, ProcedureOccurrence, Specimen,
            VisitOccurrence, VisitDetail, PayerPlanPeriod, LocationRegion
        )
        from ...cohortdefinition.core import NumericRange, DateRange, Period
        from ...cohortdefinition.cohort import CohortExpression


class RangeCheckerFactory(BaseCheckerFactory):
    """Factory for checking range values in criteria.
    
    Java equivalent: org.ohdsi.circe.check.checkers.RangeCheckerFactory
    """
    
    WARNING_EMPTY_START_VALUE = "%s in the %s has empty %s start value"
    WARNING_EMPTY_END_VALUE = "%s in the %s has empty %s end value"
    WARNING_START_GREATER_THAN_END = "%s in the %s has start value greater than end in %s"
    WARNING_START_IS_NEGATIVE = "%s in the %s start value is negative at %s"
    WARNING_DATE_IS_INVALID = "%s in the %s has invalid date value at %s"
    ROOT_OBJECT = "root object"
    
    def __init__(self, reporter: WarningReporter, group_name: str):
        """Initialize a range checker factory.
        
        Args:
            reporter: The warning reporter to use
            group_name: The name of the criteria group being checked
        """
        super().__init__(reporter, group_name)
    
    @staticmethod
    def get_factory(reporter: WarningReporter, group_name: str) -> 'RangeCheckerFactory':
        """Get a factory instance.
        
        Args:
            reporter: The warning reporter to use
            group_name: The name of the criteria group being checked
            
        Returns:
            A new RangeCheckerFactory instance
        """
        return RangeCheckerFactory(reporter, group_name)
    
    def _get_check_criteria(self, criteria: 'Criteria') -> Callable[['Criteria'], None]:
        """Get a checker function for criteria.
        
        Args:
            criteria: The criteria to get a checker for
            
        Returns:
            A function that checks the criteria
        """
        # Import here to avoid circular dependencies
        from ...cohortdefinition.criteria import (
            ConditionEra, ConditionOccurrence, Death, DeviceExposure,
            DoseEra, DrugEra, DrugExposure, Measurement, Observation,
            ObservationPeriod, ProcedureOccurrence, Specimen,
            VisitOccurrence, VisitDetail, PayerPlanPeriod, LocationRegion
        )
        
        if isinstance(criteria, ConditionEra):
            def check(c: 'ConditionEra') -> None:
                self._check_range(c.age_at_start, Constants.Criteria.CONDITION_ERA, Constants.Attributes.AGE_AT_ERA_START_ATTR)
                self._check_range(c.age_at_end, Constants.Criteria.CONDITION_ERA, Constants.Attributes.AGE_AT_ERA_END_ATTR)
                self._check_range(c.era_length, Constants.Criteria.CONDITION_ERA, Constants.Attributes.ERA_LENGTH_ATTR)
                self._check_range(c.occurrence_count, Constants.Criteria.CONDITION_ERA, Constants.Attributes.OCCURRENCE_COUNT_ATTR)
                self._check_range(c.era_start_date, Constants.Criteria.CONDITION_ERA, Constants.Attributes.ERA_START_DATE_ATTR)
                self._check_range(c.era_end_date, Constants.Criteria.CONDITION_ERA, Constants.Attributes.ERA_END_DATE_ATTR)
            return check
        elif isinstance(criteria, ConditionOccurrence):
            def check(c: 'ConditionOccurrence') -> None:
                self._check_range(c.occurrence_start_date, Constants.Criteria.CONDITION_OCCURRENCE, Constants.Attributes.OCCURRENCE_START_DATE_ATTR)
                self._check_range(c.occurrence_end_date, Constants.Criteria.CONDITION_OCCURRENCE, Constants.Attributes.OCCURRENCE_END_DATE_ATTR)
                self._check_range(c.age, Constants.Criteria.CONDITION_OCCURRENCE, Constants.Attributes.AGE_ATTR)
            return check
        elif isinstance(criteria, Death):
            def check(c: 'Death') -> None:
                self._check_range(c.age, Constants.Criteria.DEATH, Constants.Attributes.AGE_ATTR)
                self._check_range(c.occurrence_start_date, Constants.Criteria.DEATH, Constants.Attributes.OCCURRENCE_START_DATE_ATTR)
            return check
        elif isinstance(criteria, DeviceExposure):
            def check(c: 'DeviceExposure') -> None:
                self._check_range(c.occurrence_start_date, Constants.Criteria.DEVICE_EXPOSURE, Constants.Attributes.OCCURRENCE_START_DATE_ATTR)
                self._check_range(c.occurrence_end_date, Constants.Criteria.DEVICE_EXPOSURE, Constants.Attributes.OCCURRENCE_END_DATE_ATTR)
                self._check_range(c.quantity, Constants.Criteria.DEVICE_EXPOSURE, Constants.Attributes.QUANTITY_ATTR)
                self._check_range(c.age, Constants.Criteria.DEVICE_EXPOSURE, Constants.Attributes.AGE_ATTR)
            return check
        elif isinstance(criteria, DoseEra):
            def check(c: 'DoseEra') -> None:
                self._check_range(c.era_start_date, Constants.Criteria.DOSE_ERA, Constants.Attributes.ERA_START_DATE_ATTR)
                self._check_range(c.era_end_date, Constants.Criteria.DOSE_ERA, Constants.Attributes.ERA_END_DATE_ATTR)
                self._check_range(c.dose_value, Constants.Criteria.DOSE_ERA, Constants.Attributes.DOSE_VALUE_ATTR)
                self._check_range(c.era_length, Constants.Criteria.DOSE_ERA, Constants.Attributes.ERA_LENGTH_ATTR)
                self._check_range(c.age_at_start, Constants.Criteria.DOSE_ERA, Constants.Attributes.AGE_AT_START_ATTR)
                self._check_range(c.age_at_end, Constants.Criteria.DOSE_ERA, Constants.Attributes.AGE_AT_END_ATTR)
            return check
        elif isinstance(criteria, DrugEra):
            def check(c: 'DrugEra') -> None:
                self._check_range(c.era_start_date, Constants.Criteria.DRUG_ERA, Constants.Attributes.ERA_START_DATE_ATTR)
                self._check_range(c.era_end_date, Constants.Criteria.DRUG_ERA, Constants.Attributes.ERA_END_DATE_ATTR)
                self._check_range(c.occurrence_count, Constants.Criteria.DRUG_ERA, Constants.Attributes.OCCURRENCE_COUNT_ATTR)
                self._check_range(c.gap_days, Constants.Criteria.DRUG_ERA, Constants.Attributes.GAP_DAYS_ATTR)
                self._check_range(c.era_length, Constants.Criteria.DRUG_ERA, Constants.Attributes.ERA_LENGTH_ATTR)
                self._check_range(c.age_at_start, Constants.Criteria.DRUG_ERA, Constants.Attributes.AGE_AT_START_ATTR)
                self._check_range(c.age_at_end, Constants.Criteria.DRUG_ERA, Constants.Attributes.AGE_AT_END_ATTR)
            return check
        elif isinstance(criteria, DrugExposure):
            def check(c: 'DrugExposure') -> None:
                self._check_range(c.occurrence_start_date, Constants.Criteria.DRUG_EXPOSURE, Constants.Attributes.OCCURRENCE_START_DATE_ATTR)
                self._check_range(c.occurrence_end_date, Constants.Criteria.DRUG_EXPOSURE, Constants.Attributes.OCCURRENCE_END_DATE_ATTR)
                self._check_range(c.refills, Constants.Criteria.DRUG_EXPOSURE, Constants.Attributes.REFILLS_ATTR)
                self._check_range(c.quantity, Constants.Criteria.DRUG_EXPOSURE, Constants.Attributes.QUANTITY_ATTR)
                self._check_range(c.days_supply, Constants.Criteria.DRUG_EXPOSURE, Constants.Attributes.DAYS_SUPPLY_ATTR)
                self._check_range(c.effective_drug_dose, Constants.Criteria.DRUG_EXPOSURE, Constants.Attributes.EFFECTIVE_DRUG_DOSE_ATTR)
                self._check_range(c.age, Constants.Criteria.DRUG_EXPOSURE, Constants.Attributes.AGE_ATTR)
            return check
        elif isinstance(criteria, Measurement):
            def check(c: 'Measurement') -> None:
                self._check_range(c.occurrence_start_date, Constants.Criteria.MEASUREMENT, Constants.Attributes.OCCURRENCE_START_DATE_ATTR)
                self._check_range(c.value_as_number, Constants.Criteria.MEASUREMENT, Constants.Attributes.VALUE_AS_NUMBER_ATTR)
                self._check_range(c.range_low, Constants.Criteria.MEASUREMENT, Constants.Attributes.RANGE_LOW_ATTR)
                self._check_range(c.range_high, Constants.Criteria.MEASUREMENT, Constants.Attributes.RANGE_HIGH_ATTR)
                self._check_range(c.range_low_ratio, Constants.Criteria.MEASUREMENT, Constants.Attributes.RANGE_LOW_RATIO_ATTR)
                self._check_range(c.range_high_ratio, Constants.Criteria.MEASUREMENT, Constants.Attributes.RANGE_HIGH_RATIO_ATTR)
                self._check_range(c.age, Constants.Criteria.MEASUREMENT, Constants.Attributes.AGE_ATTR)
            return check
        elif isinstance(criteria, Observation):
            def check(c: 'Observation') -> None:
                self._check_range(c.occurrence_start_date, Constants.Criteria.OBSERVATION, Constants.Attributes.OCCURRENCE_START_DATE_ATTR)
                self._check_range(c.value_as_number, Constants.Criteria.OBSERVATION, Constants.Attributes.VALUE_AS_NUMBER_ATTR)
                self._check_range(c.age, Constants.Criteria.OBSERVATION, Constants.Attributes.AGE_ATTR)
            return check
        elif isinstance(criteria, ObservationPeriod):
            def check(c: 'ObservationPeriod') -> None:
                self._check_range(c.period_start_date, Constants.Criteria.OBSERVATION_PERIOD, Constants.Attributes.PERIOD_START_DATE_ATTR)
                self._check_range(c.period_end_date, Constants.Criteria.OBSERVATION_PERIOD, Constants.Attributes.PERIOD_END_DATE_ATTR)
                self._check_range(c.period_length, Constants.Criteria.OBSERVATION_PERIOD, Constants.Attributes.PERIOD_LENGTH_ATTR)
                self._check_range(c.age_at_start, Constants.Criteria.OBSERVATION_PERIOD, Constants.Attributes.AGE_AT_START_ATTR)
                self._check_range(c.age_at_end, Constants.Criteria.OBSERVATION_PERIOD, Constants.Attributes.AGE_AT_END_ATTR)
                self._check_range(c.user_defined_period, Constants.Criteria.OBSERVATION_PERIOD, Constants.Attributes.USER_DEFINED_PERIOD_ATTR)
            return check
        elif isinstance(criteria, ProcedureOccurrence):
            def check(c: 'ProcedureOccurrence') -> None:
                self._check_range(c.occurrence_start_date, Constants.Criteria.PROCEDURE_OCCURRENCE, Constants.Attributes.OCCURRENCE_START_DATE_ATTR)
                self._check_range(c.quantity, Constants.Criteria.PROCEDURE_OCCURRENCE, Constants.Attributes.QUANTITY_ATTR)
                self._check_range(c.age, Constants.Criteria.PROCEDURE_OCCURRENCE, Constants.Attributes.AGE_ATTR)
            return check
        elif isinstance(criteria, Specimen):
            def check(c: 'Specimen') -> None:
                self._check_range(c.occurrence_start_date, Constants.Criteria.SPECIMEN, Constants.Attributes.OCCURRENCE_START_DATE_ATTR)
                self._check_range(c.quantity, Constants.Criteria.SPECIMEN, Constants.Attributes.QUANTITY_ATTR)
                self._check_range(c.age, Constants.Criteria.SPECIMEN, Constants.Attributes.AGE_ATTR)
            return check
        elif isinstance(criteria, VisitOccurrence):
            def check(c: 'VisitOccurrence') -> None:
                self._check_range(c.occurrence_start_date, Constants.Criteria.VISIT_OCCURRENCE, Constants.Attributes.OCCURRENCE_START_DATE_ATTR)
                self._check_range(c.occurrence_end_date, Constants.Criteria.VISIT_OCCURRENCE, Constants.Attributes.OCCURRENCE_END_DATE_ATTR)
                self._check_range(c.visit_length, Constants.Criteria.VISIT_OCCURRENCE, Constants.Attributes.VISIT_LENGTH_ATTR)
                self._check_range(c.age, Constants.Criteria.VISIT_OCCURRENCE, Constants.Attributes.AGE_ATTR)
            return check
        elif isinstance(criteria, VisitDetail):
            def check(c: 'VisitDetail') -> None:
                self._check_range(c.visit_detail_start_date, Constants.Criteria.VISIT_DETAIL, Constants.Attributes.VISIT_DETAIL_START_DATE_ATTR)
                self._check_range(c.visit_detail_end_date, Constants.Criteria.VISIT_DETAIL, Constants.Attributes.VISIT_DETAIL_END_DATE_ATTR)
                self._check_range(c.visit_detail_length, Constants.Criteria.VISIT_DETAIL, Constants.Attributes.VISIT_DETAIL_LENGTH_ATTR)
                self._check_range(c.age, Constants.Criteria.VISIT_DETAIL, Constants.Attributes.AGE_ATTR)
            return check
        elif isinstance(criteria, PayerPlanPeriod):
            def check(c: 'PayerPlanPeriod') -> None:
                self._check_range(c.period_start_date, Constants.Criteria.PAYER_PLAN_PERIOD, Constants.Attributes.PERIOD_START_DATE_ATTR)
                self._check_range(c.period_end_date, Constants.Criteria.PAYER_PLAN_PERIOD, Constants.Attributes.PERIOD_END_DATE_ATTR)
                self._check_range(c.period_length, Constants.Criteria.PAYER_PLAN_PERIOD, Constants.Attributes.PERIOD_LENGTH_ATTR)
                self._check_range(c.age_at_start, Constants.Criteria.PAYER_PLAN_PERIOD, Constants.Attributes.AGE_AT_START_ATTR)
                self._check_range(c.age_at_end, Constants.Criteria.PAYER_PLAN_PERIOD, Constants.Attributes.AGE_AT_END_ATTR)
                self._check_range(c.user_defined_period, Constants.Criteria.PAYER_PLAN_PERIOD, Constants.Attributes.USER_DEFINED_PERIOD_ATTR)
            return check
        elif isinstance(criteria, LocationRegion):
            def check(c: 'LocationRegion') -> None:
                self._check_range(c.end_date, Constants.Criteria.LOCATION_REGION, Constants.Attributes.LOCATION_REGION_START_DATE_ATTR)
                self._check_range(c.start_date, Constants.Criteria.LOCATION_REGION, Constants.Attributes.LOCATION_REGION_END_DATE_ATTR)
            return check
        else:
            def default_check(c) -> None:
                pass
            return default_check
    
    def _get_check_demographic(self, criteria: 'DemographicCriteria') -> Callable[['DemographicCriteria'], None]:
        """Get a checker function for demographic criteria.
        
        Args:
            criteria: The demographic criteria to get a checker for
            
        Returns:
            A function that checks the criteria
        """
        def check(c: 'DemographicCriteria') -> None:
            self._check_range(c.occurrence_end_date, Constants.Criteria.DEMOGRAPHIC, Constants.Attributes.OCCURRENCE_END_DATE_ATTR)
            self._check_range(c.occurrence_start_date, Constants.Criteria.DEMOGRAPHIC, Constants.Attributes.OCCURRENCE_START_DATE_ATTR)
            self._check_range(c.age, Constants.Criteria.DEMOGRAPHIC, Constants.Attributes.AGE_ATTR)
        return check
    
    def _check_range(self, range_val, criteria_name: str, attribute: str) -> None:
        """Check a range (supports both NumericRange and DateRange).
        
        Args:
            range_val: The range to check (NumericRange or DateRange)
            criteria_name: The name of the criteria type
            attribute: The name of the attribute
        """
        if range_val is None:
            return
        
        # Import here to avoid circular dependencies
        from ...cohortdefinition.core import NumericRange, DateRange
        
        def warning(template: str) -> None:
            self._reporter(template, self._group_name, criteria_name, attribute)
        
        if isinstance(range_val, DateRange):
            # Date range checks
            match_result = Operations.match(range_val)
            match_result.when(lambda r: r.value is not None and not Comparisons.is_date_valid(r.value))\
                .then(lambda x: warning(self.WARNING_DATE_IS_INVALID))
            match_result.when(lambda r: r.op is not None and r.op.endswith("bt"))\
                .then(lambda r: Operations.match(r)
                    .when(lambda x: x.value is None)
                    .then(lambda x: warning(self.WARNING_EMPTY_START_VALUE))
                    .when(lambda x: x.extent is None)
                    .then(lambda x: warning(self.WARNING_EMPTY_END_VALUE))
                    .when(lambda x: x.extent is not None and not Comparisons.is_date_valid(x.extent))
                    .then(lambda x: warning(self.WARNING_DATE_IS_INVALID))
                    .when(Comparisons.start_is_greater_than_end)
                    .then(lambda x: warning(self.WARNING_START_GREATER_THAN_END))
                )
            match_result.or_else(lambda r: Operations.match(r)
                .when(lambda x: x.value is None)
                .then(lambda x: warning(self.WARNING_EMPTY_START_VALUE))
            )
        elif isinstance(range_val, NumericRange):
            # Numeric range checks
            match_result = Operations.match(range_val)
            match_result.when(lambda r: r.op is not None and r.op.endswith("bt"))\
                .then(lambda r: Operations.match(r)
                    .when(lambda x: x.value is None)
                    .then(lambda x: warning(self.WARNING_EMPTY_START_VALUE))
                    .when(lambda x: x.extent is None)
                    .then(lambda x: warning(self.WARNING_EMPTY_END_VALUE))
                    .when(Comparisons.start_is_greater_than_end)
                    .then(lambda x: warning(self.WARNING_START_GREATER_THAN_END))
                )
            match_result.or_else(lambda r: Operations.match(r)
                .when(lambda x: x.value is None)
                .then(lambda x: warning(self.WARNING_EMPTY_START_VALUE))
            )
    
    def check_range(self, period: Optional['Period'], criteria_name: str, attribute: str) -> None:
        """Check a period.
        
        Args:
            period: The period to check
            criteria_name: The name of the criteria type
            attribute: The name of the attribute
        """
        if period is None:
            return
        
        def warning(template: str) -> None:
            self._reporter(template, self._group_name, criteria_name, attribute)
        
        match_result = Operations.match(period)
        match_result.when(lambda x: x.start_date is not None and not Comparisons.is_date_valid(x.start_date))\
            .then(lambda x: warning(self.WARNING_DATE_IS_INVALID))
        match_result.when(lambda x: x.end_date is not None and not Comparisons.is_date_valid(x.end_date))\
            .then(lambda x: warning(self.WARNING_DATE_IS_INVALID))
        match_result.when(Comparisons.start_is_greater_than_end)\
            .then(lambda x: warning(self.WARNING_START_GREATER_THAN_END))
    
    def check(self, expression_or_criteria) -> None:
        """Check the cohort expression's censor window or individual criteria.
        
        Args:
            expression_or_criteria: Either a CohortExpression (for censor_window) 
                                or Criteria/DemographicCriteria (for individual criteria)
        """
        # Import here to avoid circular dependencies
        from ...cohortdefinition.cohort import CohortExpression
        from ...cohortdefinition.criteria import Criteria, DemographicCriteria
        
        # Handle CohortExpression (for censor_window)
        if isinstance(expression_or_criteria, CohortExpression):
            self.check_range(expression_or_criteria.censor_window, self.ROOT_OBJECT, Constants.Attributes.CENSOR_WINDOW_ATTR)
        # Handle DemographicCriteria (delegate to base class)
        elif isinstance(expression_or_criteria, DemographicCriteria):
            super().check(expression_or_criteria)
        # Handle Criteria (delegate to base class)
        elif isinstance(expression_or_criteria, Criteria):
            super().check(expression_or_criteria)

