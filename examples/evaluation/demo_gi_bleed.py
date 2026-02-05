#!/usr/bin/env python
"""
GI Bleed Phenotype Evaluation Demo for Eunomia Dataset.

This script demonstrates the evaluation framework by:
1. Defining a GI Bleed rubric with 4 rules
2. Generating T-SQL for evaluation
3. Saving the SQL for execution against Eunomia

Usage:
    python -m circe.evaluation.demo_gi_bleed

The generated SQL can be run via SQLRender to translate for your database.
"""

from pathlib import Path
from circe.evaluation import EvaluationRule, EvaluationRubric, RubricSqlGenerator


def create_gi_bleed_rubric() -> EvaluationRubric:
    """Create a GI Bleed phenotype evaluation rubric using Eunomia concept IDs."""
    
    # Rule 1: GI Hemorrhage Diagnosis
    # Concept IDs from OHDSI vocabulary:
    # - 192671: Gastrointestinal hemorrhage
    # - 4291649: Upper gastrointestinal hemorrhage
    gi_hemorrhage_rule = EvaluationRule(
        rule_id=1,
        name="GI Hemorrhage Diagnosis",
        description="Diagnosis of gastrointestinal hemorrhage within ±30 days of index",
        domain="condition_occurrence",
        concept_ids=[192671, 4291649],
        window_start_days=-30,
        window_end_days=30,
        weight=2.0,
    )
    
    # Rule 2: EGD Procedure
    # Concept ID: 4171917 - Esophagogastroduodenoscopy
    egd_rule = EvaluationRule(
        rule_id=2,
        name="EGD Procedure",
        description="Esophagogastroduodenoscopy within ±7 days of index",
        domain="procedure_occurrence",
        concept_ids=[4171917],
        window_start_days=-7,
        window_end_days=7,
        weight=2.0,
    )
    
    # Rule 3: Low Hemoglobin
    # Concept ID: 3000963 - Hemoglobin [Mass/volume] in Blood
    # Value threshold: < 10 g/dL
    low_hemoglobin_rule = EvaluationRule(
        rule_id=3,
        name="Low Hemoglobin",
        description="Hemoglobin < 10 g/dL within ±3 days of index",
        domain="measurement",
        concept_ids=[3000963],
        window_start_days=-3,
        window_end_days=3,
        weight=1.5,
        value_threshold=10.0,
        value_operator="lt",
    )
    
    # Rule 4: Melena Symptom
    # Concept ID: 4318535 - Melena (blood in stool)
    melena_rule = EvaluationRule(
        rule_id=4,
        name="Melena Symptom",
        description="Documentation of melena (blood in stool) within ±30 days",
        domain="condition_occurrence",
        concept_ids=[4318535],
        window_start_days=-30,
        window_end_days=30,
        weight=1.0,
    )
    
    # Assemble the rubric
    rubric = EvaluationRubric(
        ruleset_id=1,
        name="GI Bleed Phenotype Validation",
        description="Evaluate individuals for likely true positive GI bleed cases",
        target_phenotype="Gastrointestinal Hemorrhage",
        rules=[gi_hemorrhage_rule, egd_rule, low_hemoglobin_rule, melena_rule],
    )
    
    return rubric


def main():
    """Generate and display GI Bleed evaluation SQL."""
    print("=" * 60)
    print("GI Bleed Phenotype Evaluation Demo")
    print("=" * 60)
    print()
    
    # Create the rubric
    rubric = create_gi_bleed_rubric()
    
    print(f"Rubric: {rubric.name}")
    print(f"Target Phenotype: {rubric.target_phenotype}")
    print(f"Ruleset ID: {rubric.ruleset_id}")
    print(f"Number of Rules: {len(rubric.rules)}")
    print()
    
    print("Rules:")
    print("-" * 40)
    for rule in rubric.rules:
        print(f"  {rule.rule_id}. {rule.name} (weight: {rule.weight})")
        print(f"     Domain: {rule.domain}")
        print(f"     Concepts: {rule.concept_ids}")
        print(f"     Window: {rule.window_start_days} to {rule.window_end_days} days")
        if rule.value_threshold:
            print(f"     Value: {rule.value_operator} {rule.value_threshold}")
        print()
    
    # Generate SQL
    generator = RubricSqlGenerator(rubric)
    sql = generator.generate_evaluation_sql(include_aggregation=True)
    
    print("=" * 60)
    print("Generated T-SQL (SQLRender compatible)")
    print("=" * 60)
    print()
    print(sql)
    print()
    
    # Save to file (outside of package, in project root examples/)
    project_root = Path(__file__).parent.parent.parent
    output_dir = project_root / "examples" / "evaluation"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "gi_bleed_evaluation.sql"
    output_file.write_text(sql)
    
    print("=" * 60)
    print(f"SQL saved to: {output_file}")
    print("=" * 60)
    print()
    print("To run against Eunomia:")
    print("  1. Replace @cdm_schema with your CDM schema (e.g., 'main')")
    print("  2. Replace @cohort_table with your cohort table")
    print("  3. Replace @cohort_id with the GI bleed cohort definition ID")
    print("  4. Use SQLRender to translate for your database dialect")
    
    return rubric, sql


if __name__ == "__main__":
    main()
