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
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from circe.cohort_builder.builder import (
    CohortBuilder,
    CohortWithCriteria,
    CohortWithEntry,
)
from circe.cohort_builder.query_builder import (
    BaseQuery,
)


@dataclass
class MethodInfo:
    """Information about a method."""

    name: str
    signature: str
    return_type: str
    docstring: str
    parameters: list[dict[str, Any]]
    is_chainable: bool
    finalizes: bool  # Returns parent builder (breaks chain)


class SkillGenerator:
    """Generates SKILL.md from the cohort builder codebase."""

    def __init__(self):
        self.builder_methods: list[MethodInfo] = []
        self.entry_methods: list[MethodInfo] = []
        self.criteria_methods: list[MethodInfo] = []
        self.query_modifiers: dict[str, list[MethodInfo]] = {}
        self.time_windows: list[MethodInfo] = []

    def extract_method_info(self, cls, method_name: str) -> MethodInfo:
        """Extract information about a method."""
        method = getattr(cls, method_name)
        sig = inspect.signature(method)

        # Get return type
        return_annotation = sig.return_annotation
        return_type = "Unknown" if return_annotation == inspect.Signature.empty else str(return_annotation).replace("'", "")

        # Build parameter list
        params = []
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
            param_info = {
                "name": param_name,
                "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any",
                "default": param.default if param.default != inspect.Parameter.empty else None,
                "required": param.default == inspect.Parameter.empty,
            }
            params.append(param_info)

        # Build signature string
        param_strs = []
        for p in params:
            if p["default"] is not None:
                param_strs.append(f"{p['name']}={p['default']}")
            else:
                param_strs.append(p["name"])
        signature = f"{method_name}({', '.join(param_strs)})"

        # Get docstring
        docstring = inspect.getdoc(method) or ""

        # Determine if method finalizes (returns parent) or chains (returns self)
        finalizes = "CohortWithCriteria" in return_type or "CohortWithEntry" in return_type
        is_chainable = return_type != "None" and not finalizes

        return MethodInfo(
            name=method_name,
            signature=signature,
            return_type=return_type,
            docstring=docstring,
            parameters=params,
            is_chainable=is_chainable,
            finalizes=finalizes,
        )

    def discover_methods(self):
        """Discover all public methods from the builder classes."""

        # CohortBuilder entry methods
        for name, _method in inspect.getmembers(CohortBuilder, predicate=inspect.isfunction):
            if name.startswith("_") or name == "with_concept_sets":
                continue
            if name.startswith("with_"):
                self.builder_methods.append(self.extract_method_info(CohortBuilder, name))

        # CohortWithEntry methods
        for name, _method in inspect.getmembers(CohortWithEntry, predicate=inspect.isfunction):
            if name.startswith("_"):
                continue
            if name in [
                "first_occurrence",
                "with_observation",
                "min_age",
                "max_age",
                "require_age",
                "require_gender",
                "require_race",
                "require_ethnicity",
                "begin_rule",
                "any_of",
                "all_of",
                "at_least_of",
            ]:
                self.entry_methods.append(self.extract_method_info(CohortWithEntry, name))

        # CohortWithCriteria methods
        for name, _method in inspect.getmembers(CohortWithCriteria, predicate=inspect.isfunction):
            if name.startswith("_"):
                continue
            if (
                name.startswith("require_")
                or name.startswith("exclude_")
                or name
                in [
                    "any_of",
                    "all_of",
                    "at_least_of",
                    "begin_rule",
                    "build",
                    "require_any_of",
                    "require_all_of",
                    "require_at_least_of",
                    "exclude_any_of",
                ]
            ):
                self.criteria_methods.append(self.extract_method_info(CohortWithCriteria, name))

        # BaseQuery time windows
        for name, _method in inspect.getmembers(BaseQuery, predicate=inspect.isfunction):
            if name in [
                "within_days_before",
                "within_days_after",
                "within_days",
                "anytime_before",
                "anytime_after",
                "same_day",
                "restrict_to_visit",
                "during_event",
                "before_event_end",
            ]:
                self.time_windows.append(self.extract_method_info(BaseQuery, name))

        # Domain-specific modifiers
        modifier_map = {
            "BaseQuery": [
                "at_least",
                "at_most",
                "exactly",
                "with_distinct",
                "ignore_observation_period",
            ],
            "ProcedureQuery": ["with_quantity", "with_modifier"],
            "MeasurementQuery": [
                "with_operator",
                "with_value",
                "with_unit",
                "is_abnormal",
                "with_range_low_ratio",
                "with_range_high_ratio",
            ],
            "DrugQuery": [
                "with_route",
                "with_dose",
                "with_refills",
                "with_days_supply",
                "with_quantity",
            ],
            "VisitQuery": ["with_length", "with_place_of_service"],
            "ObservationQuery": ["with_qualifier", "with_value_as_string"],
        }

        for cls_name, methods in modifier_map.items():
            cls = globals().get(cls_name)
            if cls:
                self.query_modifiers[cls_name] = []
                for method_name in methods:
                    if hasattr(cls, method_name):
                        self.query_modifiers[cls_name].append(self.extract_method_info(cls, method_name))

    def generate_markdown(self) -> str:
        """Generate the SKILL.md content."""
        md = []

        # Header
        md.append("---")
        md.append("description: Build OHDSI cohort definitions using the fluent Python API")
        md.append("---")
        md.append("")
        md.append("# Cohort Builder Skill")
        md.append("")
        md.append("Build OHDSI cohort definitions step-by-step using the fluent `cohort_builder` API.")
        md.append("")
        md.append("**⚠️ AUTO-GENERATED**: This file is generated from the codebase. Do not edit manually.")
        md.append("")

        # Entry Events
        md.append("## Entry Event Methods")
        md.append("")
        md.append("Start building a cohort with one of these methods on `CohortBuilder`:")
        md.append("")
        md.append("```python")
        for method in sorted(self.builder_methods, key=lambda m: m.name):
            md.append(f'CohortBuilder("Title").{method.signature}')
        md.append("```")
        md.append("")

        # Entry Configuration
        md.append("## Entry Configuration Methods")
        md.append("")
        md.append("After defining the entry event, configure it with:")
        md.append("")
        for method in sorted(self.entry_methods, key=lambda m: m.name):
            if method.name in [
                "first_occurrence",
                "with_observation",
                "min_age",
                "max_age",
            ]:
                md.append(f"### `.{method.signature}`")
                if method.docstring:
                    md.append(f"{method.docstring}")
                md.append("")

        # Demographics
        md.append("## Demographic Criteria")
        md.append("")
        md.append("Add demographic requirements:")
        md.append("")
        for method in sorted(self.entry_methods, key=lambda m: m.name):
            if method.name.startswith("require_"):
                md.append(f"- `.{method.signature}`: {method.docstring.split('.')[0] if method.docstring else ''}")
        md.append("")

        # CRITICAL CHAINING RULE
        md.append("## ⚠️ CRITICAL CHAINING RULE")
        md.append("")
        md.append("**Modifiers MUST be called BEFORE time windows!**")
        md.append("")
        md.append("Time window methods finalize the criteria and return to the parent builder.")
        md.append("Once a time window is called, you cannot chain further modifiers.")
        md.append("")
        md.append("✅ **CORRECT**:")
        md.append("```python")
        md.append(".require_drug(10).at_least(2).within_days_before(30)")
        md.append("```")
        md.append("")
        md.append("❌ **INCORRECT**:")
        md.append("```python")
        md.append(".require_drug(10).within_days_before(30).at_least(2)  # ERROR!")
        md.append("```")
        md.append("")

        # Time Windows
        md.append("## Time Window Methods (Call LAST)")
        md.append("")
        md.append("These methods finalize the criteria:")
        md.append("")
        for method in sorted(self.time_windows, key=lambda m: m.name):
            md.append(f"- `.{method.signature}`: {method.docstring.split('.')[0] if method.docstring else ''}")
        md.append("")

        # Modifiers
        md.append("## Modifier Methods (Call BEFORE time windows)")
        md.append("")
        for cls_name, methods in self.query_modifiers.items():
            if methods:
                md.append(f"### {cls_name}")
                md.append("")
                for method in sorted(methods, key=lambda m: m.name):
                    md.append(f"- `.{method.signature}`")
                md.append("")

        # Inclusion Criteria
        md.append("## Inclusion Criteria Methods")
        md.append("")
        md.append("Build complex criteria with:")
        md.append("")
        for method in sorted(self.criteria_methods, key=lambda m: m.name):
            if method.name in [
                "require_any_of",
                "require_all_of",
                "require_at_least_of",
                "exclude_any_of",
            ]:
                md.append(f"### `.{method.signature}`")
                if method.docstring:
                    md.append(f"{method.docstring[:200]}...")
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

        with open(output_path, "w") as f:
            f.write(content)

        print(f"✅ Generated {output_path}")
        print(f"📊 Total lines: {len(content.splitlines())}")
        return content

    def update_system_prompt(self, skill_content: str, prompt_path: str):
        """Update a system prompt with the generated skill."""
        print(f"📝 Updating {prompt_path}...")

        try:
            # Read existing prompt
            with open(prompt_path) as f:
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
                in_frontmatter = bool(not in_frontmatter)
                continue
            if not in_frontmatter:
                skill_body.append(line)

        new_skill_section = "\n".join(skill_body).strip()

        new_prompt = prompt_content[: start_idx + len(start_marker)] + "\n\n" + new_skill_section + "\n\n" + prompt_content[end_idx:]

        # Write updated prompt
        with open(prompt_path, "w") as f:
            f.write(new_prompt)

        print(f"✅ Updated {prompt_path}")


if __name__ == "__main__":
    generator = SkillGenerator()

    # Generate SKILL.md
    skill_output = ".agent/skills/cohort_builder/SKILL.md"
    skill_content = generator.run(skill_output)

    # Update all system prompt variants
    prompts = [
        ("prompts/reasoning_models_prompt.md", "Reasoning Models"),
        ("prompts/standard_models_prompt.md", "Standard Models"),
        ("prompts/fast_models_prompt.md", "Fast Models"),
    ]

    for prompt_path, _model_type in prompts:
        generator.update_system_prompt(skill_content, prompt_path)

    print("\n✅ All documentation updated!")
    print("   - SKILL.md")
    print(f"   - {len(prompts)} model-specific prompts")
