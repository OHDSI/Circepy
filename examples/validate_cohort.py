"""
Cohort Validation Example

This example demonstrates how to validate cohort definitions programmatically
using the CIRCE validation framework.
"""

import json

from circe import cohort_expression_from_json
from circe.check import Checker
from circe.check.warning_severity import WarningSeverity


def validate_cohort_from_json(json_string):
    """
    Validate a cohort definition from JSON.

    Returns:
        tuple: (cohort_expression, validation_warnings)
    """
    # Parse the JSON
    cohort = cohort_expression_from_json(json_string)

    # Run validation checks
    checker = Checker()
    warnings = checker.check(cohort)

    return cohort, warnings


def print_validation_results(warnings):
    """Pretty print validation warnings."""

    if not warnings:
        print("✓ Cohort definition is valid with no warnings!")
        return True

    # Group warnings by severity
    critical = [w for w in warnings if w.severity == WarningSeverity.CRITICAL]
    warnings_list = [w for w in warnings if w.severity == WarningSeverity.WARNING]
    info_list = [w for w in warnings if w.severity == WarningSeverity.INFO]

    # Print critical warnings
    if critical:
        print(f"\n✗ CRITICAL ({len(critical)}):")
        for err in critical:
            print(f"  - {err.to_message()}")
            if hasattr(err, "location") and err.location:
                print(f"    Location: {err.location}")

    # Print warnings
    if warnings_list:
        print(f"\n⚠ WARNINGS ({len(warnings_list)}):")
        for warn in warnings_list:
            print(f"  - {warn.to_message()}")
            if hasattr(warn, "location") and warn.location:
                print(f"    Location: {warn.location}")

    # Print info messages
    if info_list:
        print(f"\nℹ INFO ({len(info_list)}):")
        for info in info_list:
            print(f"  - {info.to_message()}")

    # Return True if no critical warnings
    return len(critical) == 0


def create_valid_cohort_json():
    """Create a valid cohort definition for testing."""
    return json.dumps(
        {
            "ConceptSets": [
                {
                    "id": 1,
                    "name": "Type 2 Diabetes",
                    "expression": {
                        "items": [
                            {
                                "concept": {
                                    "CONCEPT_ID": 201826,
                                    "CONCEPT_NAME": "Type 2 diabetes mellitus",
                                },
                                "includeDescendants": True,
                            }
                        ]
                    },
                }
            ],
            "PrimaryCriteria": {
                "CriteriaList": [{"ConditionOccurrence": {"CodesetId": 1, "First": True}}],
                "ObservationWindow": {"PriorDays": 0, "PostDays": 0},
                "PrimaryLimit": {"Type": "All"},
            },
        }
    )


def create_invalid_cohort_json():
    """Create an invalid cohort definition for testing."""
    return json.dumps(
        {
            "ConceptSets": [],  # Empty concept sets
            "PrimaryCriteria": {
                "CriteriaList": [
                    {
                        "ConditionOccurrence": {
                            "CodesetId": 999,  # References non-existent concept set
                            "First": True,
                        }
                    }
                ],
                "ObservationWindow": {"PriorDays": 0, "PostDays": 0},
                "PrimaryLimit": {"Type": "All"},
            },
        }
    )


def validate_from_file(file_path):
    """Validate a cohort definition from a JSON file."""
    print(f"Validating cohort from: {file_path}")

    try:
        with open(file_path) as f:
            json_string = f.read()

        cohort, warnings = validate_cohort_from_json(json_string)

        print(f"\nCohort Title: {cohort.title if cohort.title else '(Untitled)'}")
        is_valid = print_validation_results(warnings)

        return is_valid

    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        return False
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Main example execution."""

    print("Cohort Validation Examples\n" + "=" * 50)

    # Example 1: Validate a valid cohort
    print("\n1. Validating a VALID cohort definition:")
    print("-" * 50)
    valid_json = create_valid_cohort_json()
    cohort, warnings = validate_cohort_from_json(valid_json)
    is_valid = print_validation_results(warnings)

    if is_valid:
        print("\n✓ Cohort is valid and ready to use!")

    # Example 2: Validate an invalid cohort
    print("\n\n2. Validating an INVALID cohort definition:")
    print("-" * 50)
    invalid_json = create_invalid_cohort_json()
    cohort, warnings = validate_cohort_from_json(invalid_json)
    is_valid = print_validation_results(warnings)

    if not is_valid:
        print("\n✗ Cohort has errors and cannot be used!")

    # Example 3: Validate from file (if available)
    print("\n\n3. Validating cohort from file:")
    print("-" * 50)

    from pathlib import Path

    example_files = list(Path(".").glob("*_cohort.json"))

    if example_files:
        for file_path in example_files[:1]:  # Just validate the first one
            is_valid = validate_from_file(file_path)
            if is_valid:
                print(f"\n✓ {file_path} is valid!")
            else:
                print(f"\n✗ {file_path} has validation issues!")
    else:
        print("No example cohort JSON files found.")
        print("Run basic_cohort.py or complex_cohort.py first to generate example files.")

    print("\n" + "=" * 50)
    print("Validation examples completed!")


if __name__ == "__main__":
    main()
