"""
GI Bleed prototype for Phenotype Evaluation Framework.
"""

from circe.vocabulary import concept_set, descendants
from circe.cohortdefinition.criteria import (
    ConditionOccurrence, ProcedureOccurrence, Measurement, 
    CorelatedCriteria
)
from circe.evaluation.models import EvaluationRule, EvaluationRubric, IndividualEvaluation, RuleResult


def create_gi_bleed_rubric() -> EvaluationRubric:
    """
    Creates a GI Bleed evaluation rubric using Eunomia concept IDs.
    
    Concept IDs:
    - 192671 (GI hemorrhage)
    - 4171917 (EGD procedure)
    - 40213201 (Hemoglobin measurement)
    
    Returns:
        EvaluationRubric: The populated rubric.
    """
    # 1. Concept Sets
    gi_hemorrhage_cs = concept_set(descendants(192671), id=192671, name="GI Hemorrhage")
    egd_procedure_cs = concept_set(descendants(4171917), id=4171917, name="EGD procedure")
    hemoglobin_cs = concept_set(descendants(40213201), id=40213201, name="Hemoglobin measurement")
    
    # 2. Rules
    
    # Rule 1: GI Hemorrhage (Primary)
    rule1 = EvaluationRule(
        rule_id=1,
        name="GI Hemorrhage",
        criteria=CorelatedCriteria(
            criteria=ConditionOccurrence(codeset_id=gi_hemorrhage_cs.id)
        ),
        weight=10.0,
        category="Primary"
    )
    
    # Rule 2: EGD Procedure (Validation)
    rule2 = EvaluationRule(
        rule_id=2,
        name="EGD procedure",
        criteria=CorelatedCriteria(
            criteria=ProcedureOccurrence(codeset_id=egd_procedure_cs.id)
        ),
        weight=5.5,
        category="Validation"
    )
    
    # Rule 3: Hemoglobin Measurement (Validation/Laboratory)
    rule3 = EvaluationRule(
        rule_id=3,
        name="Hemoglobin measurement",
        criteria=CorelatedCriteria(
            criteria=Measurement(codeset_id=hemoglobin_cs.id)
        ),
        weight=2.0,
        category="Laboratory"
    )
    
    return EvaluationRubric(
        concept_sets=[gi_hemorrhage_cs, egd_procedure_cs, hemoglobin_cs],
        rules=[rule1, rule2, rule3]
    )


def get_sample_eunomia_report() -> IndividualEvaluation:
    """
    Returns a sample evaluation report for a subject in the Eunomia dataset.
    This simulates the JSON output produced after executing the generated SQL.
    """
    return IndividualEvaluation(
        subject_id=1,
        index_date="2010-01-01",
        ruleset_id=1,
        total_score=15.5,
        rules=[
            RuleResult(
                rule_id=1,
                rule_name="GI Hemorrhage",
                score=10.0,
                matched=True,
                category="Primary"
            ),
            RuleResult(
                rule_id=2,
                rule_name="EGD procedure",
                score=5.5,
                matched=True,
                category="Validation"
            ),
            RuleResult(
                rule_id=3,
                rule_name="Hemoglobin measurement",
                score=0.0,
                matched=False,
                category="Laboratory"
            )
        ]
    )


if __name__ == "__main__":
    from circe.evaluation.engine import EvaluationQueryBuilder
    import json
    
    rubric = create_gi_bleed_rubric()
    builder = EvaluationQueryBuilder()
    sql = builder.build_query(rubric, ruleset_id=1)
    
    print("--- GI Bleed Evaluation SQL ---")
    print(sql)
    
    print("\n--- Sample Eunomia Evaluation Report (JSON) ---")
    report = get_sample_eunomia_report()
    # Use by_alias=True to match PascalCase if that's what's expected in the final report
    print(report.model_dump_json(indent=2, by_alias=True))
