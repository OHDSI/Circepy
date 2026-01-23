import sys
import re

file_path = '/Users/jamie/PycharmProjects/circe_py/circe/cohort_builder/builder.py'
content = open(file_path).read()

# Methods to update
mapping = {
    'require_condition': ('ConditionQuery', False, False),
    'require_drug': ('DrugQuery', False, False),
    'require_measurement': ('MeasurementQuery', False, False),
    'require_procedure': ('ProcedureQuery', False, False),
    'require_visit': ('VisitQuery', False, False),
    'require_observation': ('ObservationQuery', False, False),
    'require_condition_era': ('ConditionEraQuery', False, False),
    'require_drug_era': ('DrugEraQuery', False, False),
    'require_device_exposure': ('DeviceExposureQuery', False, False),
    'require_specimen': ('SpecimenQuery', False, False),
    'require_visit_detail': ('VisitDetailQuery', False, False),
    'require_dose_era': ('DoseEraQuery', False, False),
    'require_payer_plan_period': ('PayerPlanPeriodQuery', False, False),
    'exclude_condition': ('ConditionQuery', True, False),
    'exclude_drug': ('DrugQuery', True, False),
    'exclude_condition_era': ('ConditionEraQuery', True, False),
    'exclude_device_exposure': ('DeviceExposureQuery', True, False),
    'exclude_specimen': ('SpecimenQuery', True, False),
    'exclude_visit_detail': ('VisitDetailQuery', True, False),
    'exclude_dose_era': ('DoseEraQuery', True, False),
    'exclude_payer_plan_period': ('PayerPlanPeriodQuery', True, False),
    'censor_on_condition': ('ConditionQuery', False, True),
    'censor_on_drug': ('DrugQuery', False, True),
    'censor_on_procedure': ('ProcedureQuery', False, True),
    'censor_on_measurement': ('MeasurementQuery', False, True),
}

finalizing_params = ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']

for name, (q_class, is_excl, is_censor) in mapping.items():
    # Use simpler regex that matches the current pattern in builder.py
    pattern = rf'    def {name}\(self, concept_set_id: int, \*\*kwargs\) -> "CohortWithCriteria":\n        """.*?"""\n        return {q_class}\(concept_set_id, parent=self, is_exclusion={is_excl}, is_censor={is_censor}\)\.apply_params\(\*\*kwargs\)\._finalize\(\)'
    
    replacement = f'''    def {name}(self, concept_set_id: int, **kwargs) -> Union['{q_class}', 'CohortWithCriteria']:
        """{name} (Supports both chaining and parameter-based API)"""
        query = {q_class}(concept_set_id, parent=self, is_exclusion={is_excl}, is_censor={is_censor})
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in {finalizing_params}):
                return query._finalize()
        return query'''
    
    content = re.sub(pattern, replacement, content)

with open(file_path, 'w') as f:
    f.write(content)
