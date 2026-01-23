import sys
import re

file_path = '/Users/jamie/PycharmProjects/circe_py/circe/cohort_builder/query_builder.py'
content = open(file_path).read()

# Add with_status, with_type to ConditionQuery
cond_mod = '''
    def with_status(self, *concept_ids: int) -> 'ConditionQuery':
        self._config.status_concepts.extend(concept_ids)
        return self

    def with_condition_type(self, *concept_ids: int) -> 'ConditionQuery':
        self._config.condition_type_concepts.extend(concept_ids)
        return self
'''
content = re.sub(r'class ConditionQuery\(BaseQuery\):\n    def __init__\(.*?\):\n        super\(\)\.__init__\(.*?\)', 
                r'class ConditionQuery(BaseQuery):\n    def __init__(\1):\n        super().__init__(\2)' + cond_mod, content)

# Actually, it's easier to just explicitly replace the classes since I know their Structure.

drug_mod = '''class DrugQuery(BaseQuery):
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("DrugExposure", concept_set_id, **kwargs)

    def with_days_supply(self, min_days: int, max_days: Optional[int] = None) -> 'DrugQuery':
        self._config.days_supply_min = min_days
        self._config.days_supply_max = max_days
        return self

    def with_quantity(self, min_qty: float, max_qty: Optional[float] = None) -> 'DrugQuery':
        self._config.quantity_min = min_qty
        self._config.quantity_max = max_qty
        return self

    def with_drug_type(self, *concept_ids: int) -> 'DrugQuery':
        self._config.drug_type_concepts.extend(concept_ids)
        return self

    def with_route(self, *concept_ids: int) -> 'DrugQuery':
        self._config.drug_route_concepts.extend(concept_ids)
        return self

    def with_refills(self, min_refills: int, max_refills: Optional[int] = None) -> 'DrugQuery':
        self._config.refills_min = min_refills
        self._config.refills_max = max_refills
        return self

    def with_dose(self, min_dose: float, max_dose: Optional[float] = None) -> 'DrugQuery':
        self._config.dose_min = min_dose
        self._config.dose_max = max_dose
        return self

    def apply_params(self, **kwargs) -> 'DrugQuery':'''

content = content.replace('class DrugQuery(BaseQuery):\n    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):\n        super().__init__("DrugExposure", concept_set_id, **kwargs)\n\n    def apply_params(self, **kwargs) -> \'DrugQuery\':', drug_mod)

meas_mod = '''class MeasurementQuery(BaseQuery):
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("Measurement", concept_set_id, **kwargs)

    def with_value(self, min_val: float, max_val: Optional[float] = None) -> 'MeasurementQuery':
        self._config.value_min = min_val
        self._config.value_max = max_val
        return self

    def with_unit(self, *concept_ids: int) -> 'MeasurementQuery':
        self._config.unit_concepts.extend(concept_ids)
        return self

    def is_abnormal(self, value: bool = True) -> 'MeasurementQuery':
        self._config.abnormal = value
        return self

    def with_range_low_ratio(self, min_ratio: float, max_ratio: Optional[float] = None) -> 'MeasurementQuery':
        self._config.range_low_ratio_min = min_ratio
        self._config.range_low_ratio_max = max_ratio
        return self

    def with_range_high_ratio(self, min_ratio: float, max_ratio: Optional[float] = None) -> 'MeasurementQuery':
        self._config.range_high_ratio_min = min_ratio
        self._config.range_high_ratio_max = max_ratio
        return self

    def with_operator(self, *concept_ids: int) -> 'MeasurementQuery':
        self._config.measurement_operator_concepts.extend(concept_ids)
        return self

    def apply_params(self, **kwargs) -> 'MeasurementQuery':'''

content = content.replace('class MeasurementQuery(BaseQuery):\n    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):\n        super().__init__("Measurement", concept_set_id, **kwargs)\n\n    def apply_params(self, **kwargs) -> \'MeasurementQuery\':', meas_mod)

proc_mod = '''class ProcedureQuery(BaseQuery):
    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):
        super().__init__("ProcedureOccurrence", concept_set_id, **kwargs)

    def with_procedure_type(self, *concept_ids: int) -> 'ProcedureQuery':
        self._config.procedure_type_concepts.extend(concept_ids)
        return self

    def with_modifier(self, *concept_ids: int) -> 'ProcedureQuery':
        self._config.procedure_modifier_concepts.extend(concept_ids)
        return self

    def with_quantity(self, min_qty: float, max_qty: Optional[float] = None) -> 'ProcedureQuery':
        self._config.quantity_min = min_qty
        self._config.quantity_max = max_qty
        return self

    def apply_params(self, **kwargs) -> 'ProcedureQuery':'''

content = content.replace('class ProcedureQuery(BaseQuery):\n    def __init__(self, concept_set_id: Optional[int] = None, **kwargs):\n        super().__init__("ProcedureOccurrence", concept_set_id, **kwargs)\n\n    def apply_params(self, **kwargs) -> \'ProcedureQuery\':', proc_mod)

with open(file_path, 'w') as f:
    f.write(content)
