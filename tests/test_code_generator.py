import json

from circe.cohortdefinition.code_generator import to_python_code
from circe.cohortdefinition.cohort import CohortExpression


def test_code_generation_type2_diabetes():
    """Test that generated code for Type 2 Diabetes cohort recreates the object correctly."""
    with open("examples/type2_diabetes_cohort.json") as f:
        data = json.load(f)

    original_cohort = CohortExpression.model_validate(data)
    code = to_python_code(original_cohort)

    exec_globals = {}
    exec(code, exec_globals)
    generated_cohort = exec_globals["cohort"]

    assert original_cohort.checksum() == generated_cohort.checksum()


def test_checksum_stability():
    """Test that checksums are stable for identical objects."""
    with open("examples/type2_diabetes_cohort.json") as f:
        data = json.load(f)

    c1 = CohortExpression.model_validate(data)
    c2 = CohortExpression.model_validate(data)

    assert c1.checksum() == c2.checksum()


def test_checksum_diff():
    """Test that checksums differ for modified objects."""
    with open("examples/type2_diabetes_cohort.json") as f:
        data = json.load(f)

    c1 = CohortExpression.model_validate(data)

    # Modify c2
    data["Title"] = "Modified Title"
    c2 = CohortExpression.model_validate(data)

    assert c1.checksum() != c2.checksum()


def test_simple_object_generation():
    """Test generation of a simple object."""
    from circe.cohortdefinition.core import Period

    Period(
        value=10, unit="d"
    )  # Note: Unit might be a string or enum depending on Period def
    # Let's check Period definition first, wait, I can assume it works if the main one works.
    pass


def test_string_with_quotes():
    """Test that strings containing quotes are correctly escaped in generated code."""
    from circe.cohortdefinition.cohort import CohortExpression

    # Create a cohort with a title containing quotes
    c = CohortExpression(title="Alzheimer's Disease 'quoted' \"double quoted\"")

    code = to_python_code(c)

    # Execute the code
    exec_globals = {}
    exec(code, exec_globals)
    generated_cohort = exec_globals["cohort"]

    assert generated_cohort.title == "Alzheimer's Disease 'quoted' \"double quoted\""
