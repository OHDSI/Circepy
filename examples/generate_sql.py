"""
SQL Generation Example

This example demonstrates different ways to generate SQL from cohort definitions.
"""

import json
from pathlib import Path
from circe import cohort_expression_from_json, build_cohort_query
from circe.cohortdefinition.cohort_expression_query_builder import (
    CohortExpressionQueryBuilder,
    BuildExpressionQueryOptions
)


def load_cohort_from_json_file(file_path):
    """Load a cohort expression from a JSON file."""
    with open(file_path, 'r') as f:
        json_data = f.read()
    
    # Use the API function to parse JSON
    cohort = cohort_expression_from_json(json_data)
    return cohort


def generate_sql_simple(cohort_json_string):
    """Generate SQL using the simple API."""
    
    sql = build_cohort_query(
        cohort_json_string,
        cdm_schema="cdm_schema",
        vocab_schema="vocab_schema",
        cohort_id=1
    )
    
    return sql


def generate_sql_advanced(cohort):
    """Generate SQL using the advanced API with custom options."""
    
    # Create custom options
    options = BuildExpressionQueryOptions()
    options.cdm_schema = "my_custom_cdm"
    options.vocabulary_schema = "my_custom_vocab"
    options.target_table = "#cohort_inclusion"
    options.results_schema = "results"
    options.generate_stats = True
    
    # Use the query builder directly
    builder = CohortExpressionQueryBuilder()
    sql = builder.build_expression_query(cohort, options)
    
    return sql


def generate_sql_with_templates(cohort):
    """Generate different parts of the SQL separately."""
    
    builder = CohortExpressionQueryBuilder()
    options = BuildExpressionQueryOptions()
    options.cdm_schema = "cdm"
    
    # Generate codeset query
    codeset_sql = builder.get_codeset_query(cohort.concept_sets)
    
    # Generate primary events query
    primary_events_sql = builder.get_primary_events_query(cohort.primary_criteria)
    
    # Generate inclusion rules
    if cohort.inclusion_rules:
        inclusion_rules_sql = builder.get_inclusion_rule_table_sql(cohort)
    else:
        inclusion_rules_sql = "-- No inclusion rules defined"
    
    return {
        "codeset": codeset_sql,
        "primary_events": primary_events_sql,
        "inclusion_rules": inclusion_rules_sql
    }


def save_sql_to_file(sql, output_path):
    """Save generated SQL to a file."""
    with open(output_path, 'w') as f:
        f.write(sql)
    print(f"SQL saved to: {output_path}")


def main():
    """Main example execution."""
    
    print("SQL Generation Examples\n" + "=" * 50)
    
    # Example 1: Generate from JSON string
    print("\n1. Simple API - Generate from JSON string")
    simple_cohort_json = json.dumps({
        "ConceptSets": [],
        "PrimaryCriteria": {
            "CriteriaList": [
                {
                    "ConditionOccurrence": {
                        "CodesetId": 1,
                        "First": True
                    }
                }
            ],
            "ObservationWindow": {
                "PriorDays": 0,
                "PostDays": 0
            },
            "PrimaryLimit": {"Type": "All"}
        }
    })
    
    sql = generate_sql_simple(simple_cohort_json)
    print(f"Generated SQL length: {len(sql)} characters")
    save_sql_to_file(sql, "simple_cohort.sql")
    
    # Example 2: Load from file and generate
    print("\n2. Load from JSON file")
    # Note: This assumes you have a cohort JSON file
    try:
        # Check if we have example cohort files from other examples
        example_files = list(Path(".").glob("*_cohort.json"))
        if example_files:
            cohort_file = example_files[0]
            print(f"Loading cohort from: {cohort_file}")
            cohort = load_cohort_from_json_file(cohort_file)
            
            sql = build_cohort_query(
                cohort,
                cdm_schema="my_cdm",
                vocab_schema="my_vocab",
                cohort_id=100
            )
            
            output_file = cohort_file.stem + "_generated.sql"
            save_sql_to_file(sql, output_file)
        else:
            print("No example cohort JSON files found. Run basic_cohort.py first.")
    except Exception as e:
        print(f"Could not load from file: {e}")
    
    # Example 3: Generate with custom options
    print("\n3. Advanced API with custom options")
    cohort = cohort_expression_from_json(simple_cohort_json)
    advanced_sql = generate_sql_advanced(cohort)
    print(f"Generated SQL length: {len(advanced_sql)} characters")
    save_sql_to_file(advanced_sql, "advanced_cohort.sql")
    
    # Example 4: Generate SQL parts separately
    print("\n4. Generate SQL components separately")
    sql_parts = generate_sql_with_templates(cohort)
    
    print(f"  - Codeset SQL: {len(sql_parts['codeset'])} chars")
    print(f"  - Primary Events SQL: {len(sql_parts['primary_events'])} chars")
    print(f"  - Inclusion Rules SQL: {len(sql_parts['inclusion_rules'])} chars")
    
    # Save parts
    for part_name, part_sql in sql_parts.items():
        filename = f"cohort_{part_name}.sql"
        save_sql_to_file(part_sql, filename)
    
    print("\n" + "=" * 50)
    print("All examples completed successfully!")


if __name__ == "__main__":
    main()
