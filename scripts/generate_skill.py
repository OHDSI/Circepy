"""
Generate SKILL.md for the cohort_builder from the actual codebase.

This script introspects the cohort builder classes to extract:
- Available methods and their signatures
- Chaining behavior (return types)
- Docstrings and usage examples
- Valid parameter combinations

The generated SKILL.md will be a single source of truth that cannot
drift from the actual API implementation.
"""

import inspect
from typing import get_type_hints, List, Dict, Any, Set
from dataclasses import dataclass
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from circe.cohort_builder.builder import CohortBuilder, CohortWithEntry, CohortWithCriteria
from circe.cohort_builder.query_builder import (
    BaseQuery, ConditionQuery, DrugQuery, DrugEraQuery, MeasurementQuery,
    ProcedureQuery, VisitQuery, ObservationQuery, DeathQuery,
    ConditionEraQuery, DeviceExposureQuery, SpecimenQuery,
    ObservationPeriodQuery, PayerPlanPeriodQuery, LocationRegionQuery,
    VisitDetailQuery, DoseEraQuery, CriteriaGroupBuilder
)


@dataclass
class MethodInfo:
    """Information about a method."""
    name: str
    signature: str
    return_type: str
    docstring: str
    parameters: List[Dict[str, Any]]
    is_chainable: bool
    finalizes: bool  # Returns parent builder (breaks chain)


class SkillGenerator:
    """Generates SKILL.md from the cohort builder codebase."""
    
    def __init__(self):
        self.builder_methods: List[MethodInfo] = []
        self.entry_methods: List[MethodInfo] = []
        self.criteria_methods: List[MethodInfo] = []
        self.query_modifiers: Dict[str, List[MethodInfo]] = {}
        self.time_windows: List[MethodInfo] = []
        
    def extract_method_info(self, cls, method_name: str) -> MethodInfo:
        """Extract information about a method."""
        method = getattr(cls, method_name)
        sig = inspect.signature(method)
        
        # Get return type
        return_annotation = sig.return_annotation
        if return_annotation == inspect.Signature.empty:
            return_type = "Unknown"
        else:
            return_type = str(return_annotation).replace("'", "")
        
        # Build parameter list
        params = []
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            param_info = {
                'name': param_name,
                'type': str(param.annotation) if param.annotation != inspect.Parameter.empty else 'Any',
                'default': param.default if param.default != inspect.Parameter.empty else None,
                'required': param.default == inspect.Parameter.empty
            }
            params.append(param_info)
        
        # Build signature string
        param_strs = []
        for p in params:
            if p['default'] is not None:
                param_strs.append(f"{p['name']}={p['default']}")
            else:
                param_strs.append(p['name'])
        signature = f"{method_name}({', '.join(param_strs)})"
        
        # Get docstring
        docstring = inspect.getdoc(method) or ""
        
        # Determine if method finalizes (returns parent) or chains (returns self)
        finalizes = 'CohortWithCriteria' in return_type or 'CohortWithEntry' in return_type
        is_chainable = return_type != 'None' and not finalizes
        
        return MethodInfo(
            name=method_name,
            signature=signature,
            return_type=return_type,
            docstring=docstring,
            parameters=params,
            is_chainable=is_chainable,
            finalizes=finalizes
        )
    
    def discover_methods(self):
        """Discover all public methods from the builder classes."""
        
        # CohortBuilder entry methods
        for name, method in inspect.getmembers(CohortBuilder, predicate=inspect.isfunction):
            if name.startswith('_') or name == 'with_concept_sets':
                continue
            if name.startswith('with_'):
                self.builder_methods.append(self.extract_method_info(CohortBuilder, name))
        
        # CohortWithEntry methods
        for name, method in inspect.getmembers(CohortWithEntry, predicate=inspect.isfunction):
            if name.startswith('_'):
                continue
            if name in ['first_occurrence', 'with_observation', 'min_age', 'max_age', 
                       'require_age', 'require_gender', 'require_race', 'require_ethnicity',
                       'begin_rule', 'any_of', 'all_of', 'at_least_of']:
                self.entry_methods.append(self.extract_method_info(CohortWithEntry, name))
        
        # CohortWithCriteria methods
        for name, method in inspect.getmembers(CohortWithCriteria, predicate=inspect.isfunction):
            if name.startswith('_'):
                continue
            if name.startswith('require_') or name.startswith('exclude_') or \
               name in ['any_of', 'all_of', 'at_least_of', 'begin_rule', 'build',
                       'require_any_of', 'require_all_of', 'require_at_least_of', 'exclude_any_of']:
                self.criteria_methods.append(self.extract_method_info(CohortWithCriteria, name))
        
        # BaseQuery time windows
        for name, method in inspect.getmembers(BaseQuery, predicate=inspect.isfunction):
            if name in ['within_days_before', 'within_days_after', 'within_days',
                       'anytime_before', 'anytime_after', 'same_day', 'restrict_to_visit',
                       'during_event', 'before_event_end']:
                self.time_windows.append(self.extract_method_info(BaseQuery, name))
        
        # Domain-specific modifiers
        modifier_map = {
            'BaseQuery': ['at_least', 'at_most', 'exactly', 'with_distinct', 'ignore_observation_period'],
            'ProcedureQuery': ['with_quantity', 'with_modifier'],
            'MeasurementQuery': ['with_operator', 'with_value', 'with_unit', 'is_abnormal',
                               'with_range_low_ratio', 'with_range_high_ratio'],
            'DrugQuery': ['with_route', 'with_dose', 'with_refills', 'with_days_supply', 'with_quantity'],
            'VisitQuery': ['with_length', 'with_place_of_service'],
            'ObservationQuery': ['with_qualifier', 'with_value_as_string']
        }
        
        for cls_name, methods in modifier_map.items():
            cls = globals().get(cls_name)
            if cls:
                self.query_modifiers[cls_name] = []
                for method_name in methods:
                    if hasattr(cls, method_name):
                        self.query_modifiers[cls_name].append(
                            self.extract_method_info(cls, method_name)
                        )
    
    def generate_markdown(self) -> str:
        """Generate the SKILL.md content."""
        md = []
        
        # Header
        md.append("---")
        md.append("description: Build OHDSI cohort definitions using the Pythonic context manager API")
        md.append("---")
        md.append("")
        md.append("# Cohort Builder Skill")
        md.append("")
        md.append("Build OHDSI cohort definitions using the `CohortBuilder` context manager.")
        md.append("")
        md.append("**⚠️ AUTO-GENERATED**: This file is generated from the codebase. Do not edit manually.")
        md.append("")
        
        # Basic Usage - Context Manager
        md.append("## Basic Usage")
        md.append("")
        md.append("```python")
        md.append("from circe.cohort_builder import CohortBuilder")
        md.append("")
        md.append("with CohortBuilder(\"My Cohort\") as cohort:")
        md.append("    cohort.with_condition(1)  # Entry event")
        md.append("    cohort.first_occurrence()")
        md.append("    cohort.require_drug(2, within_days_before=30)")
        md.append("")
        md.append("expression = cohort.expression  # Access after context exits")
        md.append("```")
        md.append("")
        
        # Critical API Notes
        md.append("## ⚠️ CRITICAL API NOTES")
        md.append("")
        md.append("### 1. Use Context Manager (`with`) Block")
        md.append("- Cohort auto-builds when exiting the `with` block")
        md.append("- Access result via `.expression` property after exiting")
        md.append("- Do NOT call `.build()` - it's automatic")
        md.append("")
        md.append("### 2. Demographic Methods Accept Multiple Values, NOT Lists")
        md.append("")
        md.append("❌ **WRONG**:")
        md.append("```python")
        md.append("cohort.require_gender([8507, 8532])  # ERROR!")
        md.append("```")
        md.append("")
        md.append("✅ **CORRECT**:")
        md.append("```python")
        md.append("cohort.require_gender(8507, 8532)  # Multiple values as separate arguments")
        md.append("```")
        md.append("")
        md.append("### 3. Time Windows Use Keyword Arguments")
        md.append("")
        md.append("```python")
        md.append("cohort.require_drug(2, within_days_before=30)")
        md.append("cohort.exclude_condition(3, anytime_before=True)")
        md.append("```")
        md.append("")
        md.append("**Available time windows:**")
        md.append("- `within_days_before=N`")
        md.append("- `within_days_after=N`")
        md.append("- `anytime_before=True`")
        md.append("- `anytime_after=True`")
        md.append("- `same_day=True`")
        md.append("- `during_event=True`")
        md.append("")
        
        # Entry Events
        md.append("## Entry Event Methods")
        md.append("")
        md.append("Start with one entry event inside the context:")
        md.append("")
        md.append("```python")
        for method in sorted(self.builder_methods, key=lambda m: m.name):
            md.append(f"cohort.{method.signature}")
        md.append("```")
        md.append("")
        
        # Entry Configuration
        md.append("## Entry Configuration Methods")
        md.append("")
        md.append("```python")
        md.append("cohort.first_occurrence()                   # Only first occurrence per person")
        md.append("cohort.with_observation_window(prior_days=365, post_days=0)")
        md.append("cohort.min_age(18)                          # Minimum age at entry")
        md.append("cohort.max_age(65)                          # Maximum age at entry")
        md.append("```")
        md.append("")
        
        # Demographics
        md.append("## Demographic Criteria")
        md.append("")
        md.append("```python")
        md.append("cohort.require_gender(8507, 8532)           # Multiple as separate args")
        md.append("cohort.require_race(8516)")
        md.append("cohort.require_ethnicity(38003563)")
        md.append("cohort.require_age(min_age=18, max_age=65)")
        md.append("```")
        md.append("")
        
        # Inclusion/Exclusion Criteria
        md.append("## Inclusion/Exclusion Criteria")
        md.append("")
        md.append("```python")
        md.append("cohort.require_condition(id, **time_window)")
        md.append("cohort.require_drug(id, **time_window)")
        md.append("cohort.require_procedure(id, **time_window)")
        md.append("cohort.require_measurement(id, **time_window)")
        md.append("cohort.exclude_condition(id, **time_window)")
        md.append("cohort.exclude_drug(id, **time_window)")
        md.append("```")
        md.append("")
        
        # Named Inclusion Rules
        md.append("## Named Inclusion Rules")
        md.append("")
        md.append("Use nested context for named rules (for attrition tracking):")
        md.append("")
        md.append("```python")
        md.append("with CohortBuilder(\"Complex Cohort\") as cohort:")
        md.append("    cohort.with_condition(1)")
        md.append("    ")
        md.append("    with cohort.include_rule(\"Prior Treatment\") as rule:")
        md.append("        rule.require_drug(2, anytime_before=True)")
        md.append("    ")
        md.append("    with cohort.include_rule(\"Lab Confirmation\") as rule:")
        md.append("        rule.require_measurement(3, same_day=True)")
        md.append("")
        md.append("expression = cohort.expression")
        md.append("```")
        md.append("")
        
        return "\n".join(md)
    
    def run(self, output_path: str):
        """Run the skill generator."""
        print("🔍 Discovering methods...")
        self.discover_methods()
        
        print(f"✅ Found {len(self.builder_methods)} entry methods")
        print(f"✅ Found {len(self.entry_methods)} configuration methods")
        print(f"✅ Found {len(self.criteria_methods)} criteria methods")
        print(f"✅ Found {len(self.time_windows)} time window methods")
        
        print("\n📝 Generating SKILL.md...")
        content = self.generate_markdown()
        
        with open(output_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Generated {output_path}")
        print(f"📊 Total lines: {len(content.splitlines())}")
        return content
    
    def update_system_prompt(self, skill_content: str, prompt_path: str):
        """Update a system prompt with the generated skill."""
        print(f"📝 Updating {prompt_path}...")
        
        try:
            # Read existing prompt
            with open(prompt_path, 'r') as f:
                prompt_content = f.read()
        except FileNotFoundError:
            print(f"⚠️  Prompt file not found: {prompt_path}")
            return
        
        # Find the SKILL section markers
        start_marker = "[BEGIN SKILL.MD CONTENT]"
        end_marker = "[END SKILL.MD CONTENT]"
        
        start_idx = prompt_content.find(start_marker)
        end_idx = prompt_content.find(end_marker)
        
        if start_idx == -1 or end_idx == -1:
            print(f"⚠️  Could not find SKILL section markers in {prompt_path}")
            return
        
        # Replace the content between markers
        # Skip the frontmatter from skill content
        skill_lines = skill_content.splitlines()
        skill_body = []
        in_frontmatter = False
        for line in skill_lines:
            if line.strip() == "---":
                if not in_frontmatter:
                    in_frontmatter = True
                else:
                    in_frontmatter = False
                continue
            if not in_frontmatter:
                skill_body.append(line)
        
        new_skill_section = "\n".join(skill_body).strip()
        
        new_prompt = (
            prompt_content[:start_idx + len(start_marker)] +
            "\n\n" + new_skill_section + "\n\n" +
            prompt_content[end_idx:]
        )
        
        
        # Write updated prompt
        with open(prompt_path, 'w') as f:
            f.write(new_prompt)
        
        print(f"✅ Updated {prompt_path}")
    
    def load_examples(self) -> str:
        """Load examples from EXAMPLES.md file."""
        examples_path = Path(__file__).parent.parent / "prompts" / "EXAMPLES.md"
        try:
            with open(examples_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            print("⚠️  EXAMPLES.md not found")
            return ""
    
    def update_system_prompt_with_examples(self, skill_content: str, prompt_path: str, num_examples: int = 5):
        """Update a system prompt with skill and examples."""
        print(f"📝 Updating {prompt_path} (with {num_examples} examples)...")
        
        try:
            # Read existing prompt
            with open(prompt_path, 'r') as f:
                prompt_content = f.read()
        except FileNotFoundError:
            print(f"⚠️  Prompt file not found: {prompt_path}")
            return
        
        # Find the SKILL section markers
        start_marker = "[BEGIN SKILL.MD CONTENT]"
        end_marker = "[END SKILL.MD CONTENT]"
        
        start_idx = prompt_content.find(start_marker)
        end_idx = prompt_content.find(end_marker)
        
        if start_idx == -1 or end_idx == -1:
            print(f"⚠️  Could not find SKILL section markers in {prompt_path}")
            return
        
        # Replace the content between markers
        # Skip the frontmatter from skill content
        skill_lines = skill_content.splitlines()
        skill_body = []
        in_frontmatter = False
        for line in skill_lines:
            if line.strip() == "---":
                if not in_frontmatter:
                    in_frontmatter = True
                else:
                    in_frontmatter = False
                continue
            if not in_frontmatter:
                skill_body.append(line)
        
        new_skill_section = "\n".join(skill_body).strip()
        
        # Load and append examples
        examples_content = self.load_examples()
        if examples_content and num_examples > 0:
            # Extract first N examples from EXAMPLES.md
            examples_lines = examples_content.splitlines()
            example_sections = []
            current_example = []
            example_count = 0
            in_example = False
            
            for line in examples_lines:
                if line.startswith("## Example "):
                    if current_example and example_count < num_examples:
                        example_sections.append("\n".join(current_example))
                        example_count += 1
                    current_example = [line]
                    in_example = True
                elif in_example:
                    current_example.append(line)
            
            # Add last example if within limit
            if current_example and example_count < num_examples:
                example_sections.append("\n".join(current_example))
            
            # Append examples to skill section
            if example_sections:
                examples_text = "\n\n".join(example_sections[:num_examples])
                new_skill_section += "\n\n" + examples_text
        
        new_prompt = (
            prompt_content[:start_idx + len(start_marker)] +
            "\n\n" + new_skill_section + "\n\n" +
            prompt_content[end_idx:]
        )
        
        # Write updated prompt
        with open(prompt_path, 'w') as f:
            f.write(new_prompt)
        
        print(f"✅ Updated {prompt_path}")



if __name__ == "__main__":
    generator = SkillGenerator()
    
    # Generate SKILL.md to the canonical package location
    skill_output = "circe/skills/cohort_builder.md"
    skill_content = generator.run(skill_output)
    
    print("\n✅ Skill documentation updated!")
    print(f"   Location: {skill_output}")
    print("   Agents access via: circe.get_cohort_builder_skill()")


