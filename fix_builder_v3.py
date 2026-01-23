import sys
import re

file_path = '/Users/jamie/PycharmProjects/circe_py/circe/cohort_builder/builder.py'
content = open(file_path).read()

finalizing_params = ['anytime_before', 'anytime_after', 'within_days_before', 'within_days_after', 'within_days', 'same_day', 'during_event', 'before_event_end']

# Match methods with concept_set_id
def repl_with_id(m):
    indent = m.group(1)
    name = m.group(2)
    q_class = m.group(3)
    is_excl = m.group(4)
    is_censor = m.group(5)
    return f'''{indent}def {name}(self, concept_set_id: int, **kwargs) -> Union['{q_class}', 'CohortWithCriteria']:
{indent}    """{name} (Supports both chaining and parameter-based API)"""
{indent}    query = {q_class}(concept_set_id, parent=self, is_exclusion={is_excl}, is_censor={is_censor})
{indent}    if kwargs:
{indent}        query.apply_params(**kwargs)
{indent}        if any(p in kwargs for p in {finalizing_params}):
{indent}            return query._finalize()
{indent}    return query'''

pattern_with_id = r'(\s+)def (\w+)\(self, concept_set_id: int, \*\*kwargs\) -> "CohortWithCriteria":\n\s+""".*?"""\n\s+return (\w+)\(concept_set_id, parent=self, is_exclusion=(True|False), is_censor=(True|False)\)\.apply_params\(\*\*kwargs\)\._finalize\(\)'

content = re.sub(pattern_with_id, repl_with_id, content)

# Match methods without concept_set_id
def repl_no_id(m):
    indent = m.group(1)
    name = m.group(2)
    q_class = m.group(3)
    is_excl = m.group(4)
    is_censor = m.group(5)
    return f'''{indent}def {name}(self, **kwargs) -> Union['{q_class}', 'CohortWithCriteria']:
{indent}    """{name} (Supports both chaining and parameter-based API)"""
{indent}    query = {q_class}(parent=self, is_exclusion={is_excl}, is_censor={is_censor})
{indent}    if kwargs:
{indent}        query.apply_params(**kwargs)
{indent}        if any(p in kwargs for p in {finalizing_params}):
{indent}            return query._finalize()
{indent}    return query'''

pattern_no_id = r'(\s+)def (\w+)\(self, \*\*kwargs\) -> "CohortWithCriteria":\n\s+""".*?"""\n\s+return (\w+)\(parent=self, is_exclusion=(True|False), is_censor=(True|False)\)\.apply_params\(\*\*kwargs\)\._finalize\(\)'

content = re.sub(pattern_no_id, repl_no_id, content)

with open(file_path, 'w') as f:
    f.write(content)
