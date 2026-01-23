import sys
import re

file_path = '/Users/jamie/PycharmProjects/circe_py/circe/cohort_builder/builder.py'
content = open(file_path).read()

# Pattern for finalizing methods in builder.py
# Example: def require_death(self, **kwargs) -> "CohortWithCriteria":
#              """require_death (Updated API)"""
#              return DeathQuery(parent=self).apply_params(**kwargs)._finalize()

finalizing_params = ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']

# List of all query classes and their requirement names
queries = {
    'ConditionQuery': ['require_condition', 'exclude_condition', 'censor_on_condition'],
    'DrugQuery': ['require_drug', 'exclude_drug', 'censor_on_drug'],
    'MeasurementQuery': ['require_measurement', 'exclude_measurement', 'censor_on_measurement'],
    'ProcedureQuery': ['require_procedure', 'exclude_procedure', 'censor_on_procedure'],
    'VisitQuery': ['require_visit', 'exclude_visit', 'censor_on_visit'],
    'ObservationQuery': ['require_observation', 'exclude_observation', 'censor_on_observation'],
    'DeathQuery': ['require_death', 'exclude_death', 'censor_on_death'],
    'ConditionEraQuery': ['require_condition_era', 'exclude_condition_era'],
    'DrugEraQuery': ['require_drug_era', 'exclude_drug_era'],
    'DeviceExposureQuery': ['require_device_exposure', 'exclude_device_exposure'],
    'SpecimenQuery': ['require_specimen', 'exclude_specimen'],
    'VisitDetailQuery': ['require_visit_detail', 'exclude_visit_detail'],
    'DoseEraQuery': ['require_dose_era', 'exclude_dose_era'],
    'PayerPlanPeriodQuery': ['require_payer_plan_period', 'exclude_payer_plan_period'],
    'ObservationPeriodQuery': ['require_observation_period'],
}

for q_class, methods in queries.items():
    for method in methods:
        # Search for both variants (with and without concept_set_id)
        # Variant 1: def name(self, concept_set_id: int, **kwargs)
        p1 = rf'    def {method}\(self, concept_set_id: int, \*\*kwargs\) -> Union\[\'{q_class}\', \'CohortWithCriteria\'\]:\n        """{method} \(Supports both chaining and parameter-based API\)\"""\n        query = {q_class}\(concept_set_id, parent=self, is_exclusion=(True|False), is_censor=(True|False)\)'
        # This one is already fixed by my previous script, but let's make sure it's correct.
        
        # Variant 2: def name(self, **kwargs) (e.g. require_death)
        # It currently looks like:
        # def require_death(self, **kwargs) -> "CohortWithCriteria":
        #     """require_death (Updated API)"""
        #     return DeathQuery(parent=self).apply_params(**kwargs)._finalize()
        
        p2 = rf'    def {method}\(self, \*\*kwargs\) -> "CohortWithCriteria":\n        """{method} \(Updated API\)\"""\n        return {q_class}\(parent=self, is_exclusion=(True|False), is_censor=(True|False)\)\.apply_params\(\*\*kwargs\)\._finalize\(\)'
        
        # Replace Variant 2
        def repl2(m):
            is_excl = m.group(1)
            is_censor = m.group(2)
            return f'''    def {method}(self, **kwargs) -> Union['{q_class}', 'CohortWithCriteria']:
        """{method} (Supports both chaining and parameter-based API)"""
        query = {q_class}(parent=self, is_exclusion={is_excl}, is_censor={is_censor})
        if kwargs:
            query.apply_params(**kwargs)
            if any(p in kwargs for p in {finalizing_params}):
                return query._finalize()
        return query'''

        content = re.sub(p2, repl2, content)

with open(file_path, 'w') as f:
    f.write(content)
