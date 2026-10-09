"""Example demonstrating YAML cohort definition and usage.

This example shows:
1. Loading a cohort from a YAML file
2. Creating a cohort programmatically and saving as YAML
3. Working with YAML cohorts in the same way as JSON cohorts
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from circe.api import build_cohort_query, cohort_expression_from_yaml, cohort_print_friendly
from circe.cohortdefinition import BuildExpressionQueryOptions
from circe.io import load_expression


def example_1_load_yaml_cohort():
    """Example 1: Load a cohort from YAML file."""
    print("=" * 60)
    print("Example 1: Loading a YAML Cohort")
    print("=" * 60)

    # Load a YAML cohort file
    # The file uses snake_case naming convention, which is more Pythonic
    cohort_path = Path(__file__).parent.parent / "tests" / "cohorts" / "isolated_immune_thrombocytopenia.yaml"

    if cohort_path.exists():
        # Method 1: Using load_expression (auto-detects YAML by extension)
        cohort = load_expression(cohort_path)
        print(f"✓ Loaded YAML cohort: {cohort.title}")
        print(f"  Concept sets: {len(cohort.concept_sets) if cohort.concept_sets else 0}")

        # Method 2: Directly from YAML string
        yaml_content = cohort_path.read_text()
        cohort_expression_from_yaml(yaml_content)
        print("✓ Also loaded via cohort_expression_from_yaml()")

        return cohort
    else:
        print(f"✗ Example YAML file not found at {cohort_path}")
        print("  Creating a simple YAML cohort instead...")
        return None


def example_2_create_and_save_yaml():
    """Example 2: Create a cohort programmatically and save as YAML."""
    print("\n" + "=" * 60)
    print("Example 2: Creating and Saving a YAML Cohort")
    print("=" * 60)

    # Create YAML content with snake_case names
    yaml_content = """
title: "Hypertension Patients"
cdm_version_range: ">=5.0.0"

concept_sets:
  - id: 1
    name: "Hypertension diagnosis"
    expression:
      items:
        - concept:
            concept_id: 316866
            concept_name: "Essential hypertension"
            domain_id: "Condition"
            vocabulary_id: "SNOMED"
            concept_class_id: "Clinical Finding"
            standard_concept: "S"
          is_excluded: false
          include_descendants: true
          include_mapped: false
      is_excluded: false
      include_descendants: false
      include_mapped: false

primary_criteria:
  criteria_list:
    - condition_occurrence:
        codeset_id: 1
        condition_type_exclude: false
  observation_window:
    prior_days: 0
    post_days: 0
  primary_criteria_limit:
    type: "All"

inclusion_rules: []
"""

    # Parse and save to a file
    with TemporaryDirectory() as tmpdir:
        yaml_path = Path(tmpdir) / "hypertension_cohort.yaml"
        yaml_path.write_text(yaml_content)
        print(f"✓ Created YAML cohort at {yaml_path}")

        # Load it back to verify
        cohort = load_expression(yaml_path)
        print(f"✓ Loaded cohort: '{cohort.title}'")
        print(f"  Concept sets: {len(cohort.concept_sets) if cohort.concept_sets else 0}")

        # Read back and show snake_case naming
        loaded_yaml = yaml_path.read_text()
        print("\n✓ YAML file uses snake_case naming:")
        for line in loaded_yaml.split("\n")[:15]:
            if line.strip() and not line.strip().startswith("#"):
                print(f"  {line}")

        return cohort, yaml_path


def example_3_yaml_sql_generation():
    """Example 3: Generate SQL from a YAML cohort."""
    print("\n" + "=" * 60)
    print("Example 3: Generate SQL from YAML Cohort")
    print("=" * 60)

    # Create a YAML cohort with proper primary_criteria
    yaml_content = """
title: "Simple Test Cohort"
concept_sets: []
primary_criteria:
  criteria_list: []
  observation_window:
    prior_days: 0
    post_days: 0
  primary_criteria_limit:
    type: "All"
"""

    with TemporaryDirectory() as tmpdir:
        yaml_path = Path(tmpdir) / "test_cohort.yaml"
        yaml_path.write_text(yaml_content)

        # Load YAML cohort
        cohort = load_expression(yaml_path)

        # Generate SQL (same as with JSON cohorts)
        options = BuildExpressionQueryOptions()
        options.cdm_schema = "cdm"
        options.target_table = "public.cohort"
        options.cohort_id = 1

        sql = build_cohort_query(cohort, options)
        print("✓ Generated SQL from YAML cohort")
        print("\nSQL Preview (first 20 lines):")
        print("-" * 60)
        lines = sql.split("\n")
        for line in lines[:20]:
            print(line)
        if len(lines) > 20:
            print("... (truncated)")


def example_4_yaml_markdown_generation():
    """Example 4: Generate Markdown from a YAML cohort."""
    print("\n" + "=" * 60)
    print("Example 4: Generate Markdown from YAML Cohort")
    print("=" * 60)

    yaml_content = """
title: "Drug Allergy Cohort"
concept_sets:
  - id: 1
    name: "Penicillin allergy"
    expression:
      items: []
      is_excluded: false
      include_descendants: false
      include_mapped: false
primary_criteria: null
"""

    with TemporaryDirectory() as tmpdir:
        yaml_path = Path(tmpdir) / "allergy_cohort.yaml"
        yaml_path.write_text(yaml_content)

        # Load YAML cohort
        cohort = load_expression(yaml_path)

        # Generate Markdown (same as with JSON cohorts)
        markdown = cohort_print_friendly(cohort, include_concept_sets=True, title="YAML Cohort Example")

        print("✓ Generated Markdown from YAML cohort")
        print("\nMarkdown Preview (first 30 lines):")
        print("-" * 60)
        lines = markdown.split("\n")
        for line in lines[:30]:
            print(line)
        if len(lines) > 30:
            print("... (truncated)")


def example_5_yaml_vs_json():
    """Example 5: Compare YAML and JSON formats."""
    print("\n" + "=" * 60)
    print("Example 5: YAML vs JSON Format Comparison")
    print("=" * 60)

    print("\nJSON Format (PascalCase):")
    print("-" * 40)
    print("  - Uses PascalCase field names: conceptSets, primaryCriteria, etc.")
    print("  - More compact representation")
    print("  - Compatible with Java/R CIRCE implementations")
    print("\nYAML Format (snake_case):")
    print("-" * 40)
    print("  - Uses snake_case field names: concept_sets, primary_criteria, etc.")
    print("  - More readable for Python developers")
    print("  - Better matches Python naming conventions")
    print("\nBoth formats are supported and interchangeable in circepy!")


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  YAML Cohort Support Examples in circepy".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")

    example_1_load_yaml_cohort()
    example_2_create_and_save_yaml()
    example_3_yaml_sql_generation()
    example_4_yaml_markdown_generation()
    example_5_yaml_vs_json()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
