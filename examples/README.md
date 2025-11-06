# CIRCE Python Examples

This directory contains practical examples demonstrating how to use the CIRCE Python package for cohort definition and SQL generation.

## Examples Overview

### 1. `type2_diabetes_cohort.ipynb` - Interactive Jupyter Notebook

**Purpose**: Interactive notebook demonstrating the complete workflow using athena-client to fetch concepts.

**What it covers**:
- Using athena-client to search ATHENA for OMOP concepts
- Building concept sets from search results
- Creating cohort definitions interactively
- Validation and SQL generation with immediate feedback
- Saving outputs (JSON and SQL)

**Usage**:
```bash
# Install Jupyter and dependencies
pip install jupyter athena-client

# Launch notebook
jupyter notebook type2_diabetes_cohort.ipynb
```

**Perfect for**: Learning, exploration, and rapid prototyping

---

### 2. `basic_cohort.py` - Simple Cohort Definition

**Purpose**: Demonstrates creating a basic cohort definition with a single condition.

**What it covers**:
- Creating concept sets
- Defining primary criteria
- Generating SQL from a cohort definition
- Exporting cohort definitions as JSON

**Usage**:
```bash
python basic_cohort.py
```

**Output Files**:
- `diabetes_cohort.sql` - Generated SQL query
- `diabetes_cohort.json` - Cohort definition in JSON format

---

### 3. `complex_cohort.py` - Advanced Cohort Features

**Purpose**: Shows how to create complex cohorts with multiple criteria, time windows, and restrictions.

**What it covers**:
- Multiple concept sets
- Time windows for correlated criteria
- Age and gender restrictions
- Inclusion and exclusion criteria
- "At least" and "exactly" occurrence constraints

**Usage**:
```bash
python complex_cohort.py
```

**Output Files**:
- `complex_diabetes_cohort.sql` - Generated SQL query
- `complex_diabetes_cohort.json` - Cohort definition in JSON format

**Cohort Logic**:
- Index: First Type 2 Diabetes diagnosis
- Age: 18-75 at diagnosis
- Must have: Metformin prescription within 30 days after diagnosis
- Must not have: Insulin exposure in 180 days before diagnosis

---

### 4. `generate_sql.py` - SQL Generation Techniques

**Purpose**: Demonstrates different methods for generating SQL from cohort definitions.

**What it covers**:
- Simple API usage
- Loading cohorts from JSON files
- Advanced API with custom options
- Generating SQL components separately (codesets, primary events, inclusion rules)

**Usage**:
```bash
python generate_sql.py
```

**Output Files**:
- `simple_cohort.sql`
- `advanced_cohort.sql`
- `cohort_codeset.sql`
- `cohort_primary_events.sql`
- `cohort_inclusion_rules.sql`

---

### 5. `validate_cohort.py` - Cohort Validation

**Purpose**: Shows how to validate cohort definitions and handle validation warnings.

**What it covers**:
- Programmatic validation
- Parsing validation warnings
- Differentiating between errors, warnings, and info messages
- Validating cohorts from files

**Usage**:
```bash
python validate_cohort.py
```

**Validation Severity Levels**:
- **ERROR**: Cohort definition is invalid and cannot be used
- **WARNING**: Potential issues that should be reviewed
- **INFO**: Informational messages about the cohort definition

---

## Running the Examples

### Prerequisites

Install the CIRCE package:
```bash
pip install ohdsi-circe
```

### Run All Examples

To run all examples in sequence:

```bash
# Run each example
python basic_cohort.py
python complex_cohort.py
python generate_sql.py
python validate_cohort.py
```

### Clean Up Generated Files

To remove all generated files:

```bash
rm -f *_cohort.sql *_cohort.json *.sql
```

## Example Execution Order

For the best learning experience, run the examples in this order:

1. **basic_cohort.py** - Start here to understand the fundamentals
2. **validate_cohort.py** - Learn how to validate your cohort definitions
3. **complex_cohort.py** - Explore advanced features
4. **generate_sql.py** - Master different SQL generation techniques

## Common Patterns

### Loading a Cohort from JSON

```python
from circe import cohort_expression_from_json

with open('my_cohort.json', 'r') as f:
    json_data = f.read()

cohort = cohort_expression_from_json(json_data)
```

### Generating SQL

```python
from circe.api import build_cohort_query

sql = build_cohort_query(
    cohort,
    cdm_schema="my_cdm_schema",
    vocab_schema="my_vocab_schema",
    cohort_id=1
)
```

### Validating a Cohort

```python
from circe.check import Checker

checker = Checker()
warnings = checker.check(cohort)

if not warnings:
    print("Cohort is valid!")
else:
    for warning in warnings:
        print(f"{warning.severity}: {warning.message}")
```

## Modifying the Examples

Feel free to modify these examples to:

- Change concept IDs to match your vocabulary
- Adjust time windows and occurrence constraints
- Add additional criteria (drug exposures, procedures, measurements)
- Experiment with different primary criteria
- Add inclusion rules for more complex cohort logic

## Using with OMOP CDM

These examples generate SQL for the OMOP Common Data Model. To use the generated SQL:

1. Replace placeholder schema names (`my_cdm_schema`, `my_vocab_schema`) with your actual schema names
2. Ensure concept IDs exist in your vocabulary tables
3. Run the SQL against your OMOP CDM database
4. Results will be inserted into your cohort table

## Getting Help

- **Documentation**: See the main [README.md](../README.md)
- **API Reference**: Use `help()` in Python: `help(CohortExpression)`
- **Issues**: Report problems at https://github.com/OHDSI/circe-be-python/issues

## Additional Resources

- [OHDSI Community](https://www.ohdsi.org/)
- [OMOP Common Data Model](https://github.com/OHDSI/CommonDataModel)
- [OHDSI Atlas](https://github.com/OHDSI/Atlas) - Web-based cohort definition tool
- [Java CIRCE-BE](https://github.com/OHDSI/circe-be) - Original Java implementation
