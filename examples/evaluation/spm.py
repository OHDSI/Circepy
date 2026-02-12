from circe.evaluation.builder import EvaluationBuilder
from circe.evaluation.engine import EvaluationQueryBuilder

# --- SPM Rubric Definition (Simplified for this example) ---
def create_spm_rubric():
    """
    Builds an evaluation rubric for Secondary Primary Malignancy (SPM).

    SPM refers to a new primary cancer in a patient with a history of a previous,
    independent primary cancer. This rubric scores the likelihood that a second
    cancer event is a new primary rather than a metastasis.
    """

    with EvaluationBuilder("Secondary Primary Malignancy Evaluation") as ev:
        # 1. Concept Sets with detailed logic (Descendants, Exclusions, etc.)
        from circe.vocabulary import descendants, exclude, mapped

        # General Primary Cancer (Malignant neoplastic disease)
        # We use descendants() explicitly to show the power of the new API
        primary_cancer = ev.concept_set("Primary Cancer",
                                        443392)

        # Secondary/Metastatic Cancer (Secondary malignant neoplasm)
        metastatic_cancer = ev.concept_set("Metastatic Cancer", 432851)  # int defaults to descendants

        # Treatment markers
        chemo = ev.concept_set("Chemotherapy", 4163872)
        radiation = ev.concept_set("Radiation Therapy", 4126119)

        # 2. Evidence Rules

        # Rule 1: History of a previous primary cancer
        # This confirms the patient passed the "first" primary threshold.
        ev.add_rule("History of Prior Primary Cancer", weight=5.0, category="Baseline") \
            .condition(primary_cancer) \
            .at_least(1) \
            .within_days_before(3650)  # Within 10 years before index

        # Rule 2: New Primary Cancer Diagnosis at Index
        # The anchor point (index_date) should be the suspected second primary.
        ev.add_rule("Index Primary Cancer Diagnosis", weight=10.0, category="Evidence") \
            .condition(primary_cancer) \
            .at_least(1) \
            .within_days_before(0)  # On the index date

        # Rule 3: Long interval between cancers (supports independence)
        # Using a gap of at least 2 years before the index date.
        with ev.rule("Long Disease-Free Interval (>2yrs)", weight=8.0, category="Clinical Confidence") as rule:
            rule.condition(primary_cancer).at_least(1).within_days_before(365 * 2)
            # This is conceptually a gap check; in Circe evaluation, we score based on presence.
            # A truly incident case evaluation might require advanced logic,
            # but for characterize, we look for signs of a gap.

        # Rule 4: Distinctive Treatment for Second Cancer
        # New treatments initiated around the index date.
        with ev.rule("New Treatment Course Near Index", weight=7.0, category="Treatment") as rule:
            with rule.any_of() as group:
                group.procedure(chemo)
                group.procedure(radiation)
            rule.within_days_before(30)  # Within 30 days before/on index

        # 3. Exclusion Rules (Negative Polarity)

        # Rule 5: Exclusion - Metastatic Evidence
        # If the codes around index are explicitly for secondary/metastatic sites,
        # it strongly suggests it's not a new primary.
        ev.add_rule("Explicit Metastasis Diagnosis", weight=15.0, polarity=-1, category="Exclusion") \
            .condition(metastatic_cancer) \
            .at_least(1) \
            .within_days_before(30)
        # 4. Rare Covariates (Genetics & Histology)

        # Rule 6: Genetic Susceptibility (High confidence in second primary)
        # Using Concept IDs for common cancer syndromes (simplified)
        genetic_risk = ev.concept_set("Genetic Cancer Syndrome", 40766929, 36769062)  # BRCA, Lynch
        ev.add_rule("Genetic Susceptibility Marker", weight=12.0, category="Biomarker") \
            .observation(genetic_risk) \
            .anytime_before()
        # Rule 7: Distinct Histology (Supports SPM over metastasis)
        # In practice, this would look for specific pathology observations.
        histology = ev.concept_set("Distinct Histology Report", 4235804)
        ev.add_rule("Histology Confirmed Distinct", weight=10.0, category="Pathology") \
            .observation(histology) \
            .within_days_before(60)
        # Rule 8: Site Specificity (e.g., Contralateral involvement)
        # Marker for when the second cancer is in a paired organ but the opposite side.
        contralateral = ev.concept_set("Contralateral Body Site", 4032822)
        ev.add_rule("Contralateral Organ Involvement", weight=15.0, category="Clinical Confidence") \
            .observation(contralateral) \
            .within_days_before(30)
        # 5. Negative Covariates (Decrease Score)

        # Rule 9: Multi-focal Disease at Index
        # Suggestive of metastasis rather than a single new primary.
        multi_focal = ev.concept_set("Multi-focal Disease", 4197576)
        ev.add_rule("Multi-focal/Systemic Involvement", weight=10.0, polarity=-1, category="Exclusion") \
            .observation(multi_focal) \
            .within_days_before(30)
        # 6. Advanced Clinical Measures

        # Rule 10: Radical Surgical Intervention
        # Radical surgery on the second site suggests primary intent (curative).
        radical_surgery = ev.concept_set("Radical Resection", 4324887)  # e.g., Mastectomy, Prostatectomy
        ev.add_rule("Radical Surgical Intent", weight=12.0, category="Treatment") \
            .procedure(radical_surgery) \
            .within_days_before(30)
        # Rule 11: Unified Sex-Specific Tumor Markers (OR Condition)
        # Matches PSA elevation in Males OR CA-125 elevation in Females.
        psa = ev.concept_set("PSA Marker", 3006314)
        ca125 = ev.concept_set("CA-125 Marker", 3013721)

        with ev.rule("Any Sex-Specific Marker Elevation", weight=8.0, category="Laboratory") as rule:
            with rule.any_of() as group:
                group.measurement(psa, gender=8507, at_least=1, within_days_before=30)
                group.measurement(ca125, gender=8532, at_least=1, within_days_before=30)
        # 7. Advanced Exclusion Logic

        # Rule 12: Advanced Stage of First Cancer
        # If the patient already had Stage IV disease documented before the index,
        # the new event is much more likely to be a metastatic progression.
        stage_iv = ev.concept_set("Stage IV Disease", 4166060)
        ev.add_rule("Pre-existing Advanced Staging", weight=15.0, polarity=-1, category="Exclusion") \
            .observation(stage_iv) \
            .anytime_before()

    return ev.rubric



query_builder = EvaluationQueryBuilder()
evaluation_sql = query_builder.build_query(
    rubric=create_spm_rubric(),
    ruleset_id=1,
    index_event_table="scratch.scratch_jgilber2.spm_cohort_test",
    cdm_schema=f"optum_ehr.cdm_optum_ehr_v3765",
    vocabulary_schema=f"optum_ehr.cdm_optum_ehr_v3765",  # Assuming vocab is in same schema or accessible
    results_schema=f"scratch.scratch_jgilber2",
    target_table="spm_rubric_results"
)

print(evaluation_sql)
