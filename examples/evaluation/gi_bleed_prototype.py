"""
GI Bleed prototype for Phenotype Evaluation Framework.
"""

from circe.evaluation.builder import EvaluationBuilder
from circe.evaluation.models import EvaluationRubric, IndividualEvaluation, RuleResult


def create_gi_bleed_rubric() -> EvaluationRubric:
    """
    Creates a GI Bleed evaluation rubric using Eunomia concept IDs.
    
    All rules are time-dependent and evaluated within 30 days before the index date
    of the suspected GI bleed event, representing a clinically relevant acute window.

    Concept IDs:
    - 192671 (GI hemorrhage)
    - 4171917 (EGD procedure)
    - 40213201 (Hemoglobin measurement)
    - 432 (Anemia)
    - 4103703 (Blood in stool)

    Rules:
    1. GI Hemorrhage diagnosis within 30 days (weight: 10.0)
    2. EGD procedure within 30 days (weight: 5.5)
    3. Hemoglobin measurement within 30 days (weight: 2.0)
    4. Low Hemoglobin < 10 g/dL within 30 days (weight: 8.0)
    5. Anemia diagnosis within 30 days (weight: 6.0)
    6. Blood in stool observation within 30 days (weight: 7.0)

    Returns:
        EvaluationRubric: The populated rubric.
    """
    with EvaluationBuilder("GI Bleed Evaluation") as ev:
        # 1. Define Concept Sets
        gi_hemorrhage = ev.concept_set("GI Hemorrhage", 192671)
        egd_procedure = ev.concept_set("EGD procedure", 4171917)
        hemoglobin = ev.concept_set("Hemoglobin measurement", 40213201)
        anemia = ev.concept_set("Anemia", 432)
        blood_in_stool = ev.concept_set("Blood in stool", 4103703)

        # 2. Define Rules
        # All rules use a 30-day window before index date to capture acute GI bleed events

        # Primary evidence: GI hemorrhage diagnosis within 30 days before index
        ev.add_rule("GI Hemorrhage", weight=10.0, category="Primary") \
            .condition(gi_hemorrhage).at_least(1).within_days_before(30)

        # Validation evidence: EGD procedure within 30 days before index
        ev.add_rule("EGD procedure", weight=5.5, category="Validation") \
            .procedure(egd_procedure).at_least(1).within_days(30)

        # Laboratory evidence: Hemoglobin measurement within 30 days before index
        ev.add_rule("Hemoglobin measurement", weight=2.0, category="Laboratory") \
            .measurement(hemoglobin).at_least(1).within_days(30)

        # Laboratory evidence: Low hemoglobin indicating anemia from GI bleed
        # Hemoglobin < 10 g/dL within 30 days is clinically significant for acute blood loss
        ev.add_rule("Low Hemoglobin (< 10 g/dL)", weight=8.0, category="Laboratory") \
            .measurement(hemoglobin).with_value(lt=10.0).at_least(1).within_days(30)

        # Supporting evidence: Anemia diagnosis within 30 days before index
        ev.add_rule("Anemia diagnosis", weight=6.0, category="Primary") \
            .condition(anemia).at_least(1).within_days(30)

        # Clinical observation: Blood in stool within 30 days before index
        # Strong indicator of lower GI bleeding
        ev.add_rule("Blood in stool", weight=7.0, category="Clinical") \
            .observation(blood_in_stool).at_least(1).within_days_before(30)

    return ev.rubric


def get_sample_eunomia_report() -> IndividualEvaluation:
    """
    Returns a sample evaluation report for a subject in the Eunomia dataset.
    This simulates the JSON output produced after executing the generated SQL.
    All rules are evaluated within 30 days before the index date.
    """
    return IndividualEvaluation(
        subject_id=1,
        index_date="2010-01-01",
        ruleset_id=1,
        total_score=36.5,  # GI Hemorrhage (10.0) + EGD (5.5) + Low Hgb (8.0) + Anemia (6.0) + Blood in stool (7.0)
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
            ),
            RuleResult(
                rule_id=4,
                rule_name="Low Hemoglobin (< 10 g/dL)",
                score=8.0,
                matched=True,
                category="Laboratory"
            ),
            RuleResult(
                rule_id=5,
                rule_name="Anemia diagnosis",
                score=6.0,
                matched=True,
                category="Primary"
            ),
            RuleResult(
                rule_id=6,
                rule_name="Blood in stool",
                score=7.0,
                matched=True,
                category="Clinical"
            )
        ]
    )


if __name__ == "__main__":
    from circe.evaluation.engine import EvaluationQueryBuilder

    rubric = create_gi_bleed_rubric()
    builder = EvaluationQueryBuilder()
    sql = builder.build_query(rubric, ruleset_id=1)
    
    print("--- GI Bleed Evaluation SQL ---")
    print(sql)
    
    print("\n--- Sample Eunomia Evaluation Report (JSON) ---")
    report = get_sample_eunomia_report()
    # Use by_alias=True to match PascalCase if that's what's expected in the final report
    print(report.model_dump_json(indent=2, by_alias=True))
