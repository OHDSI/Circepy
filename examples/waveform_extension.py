"""
Comprehensive example demonstrating the full OHDSI Waveform Extension.

This example showcases all 4 waveform tables:
1. waveform_occurrence - Clinical context for recording sessions
2. waveform_registry - File metadata
3. waveform_channel_metadata - Signal parameters (sampling rates, etc.)
4. waveform_feature - Derived measurements (heart rate, SpO2, etc.)

Reference: https://ohdsi.github.io/WaveformWG/waveform-tables.html
"""

from circe.cohortdefinition import CohortExpression, PrimaryCriteria
from circe.cohortdefinition.cohort_expression_query_builder import BuildExpressionQueryOptions, CohortExpressionQueryBuilder
from circe.cohortdefinition.core import DateRange, NumericRange
from circe.cohortdefinition.printfriendly.markdown_render import MarkdownRender

# Import the extension — registration is automatic via decorators
# Import criteria classes
from circe.extensions.waveform.criteria import WaveformChannelMetadata, WaveformFeature, WaveformOccurrence, WaveformRegistry
from circe.vocabulary.concept import Concept


def create_concept(concept_id, name):
    """Helper to create a concept."""
    return Concept(
        concept_id=concept_id,
        concept_name=name,
        invalid_reason="",
        domain_id="Waveform",
        vocabulary_id="Custom",
        concept_class_id="Waveform",
        standard_concept="S",
        concept_code=str(concept_id),
    )


# =============================================================================
# Example 1: ICU monitoring session with multiple files
# =============================================================================
print("=" * 80)
print("Example 1: ICU Telemetry Session with ≥10 Files")
print("=" * 80)

waveform_occ_example = WaveformOccurrence(
    waveform_occurrence_concept_id=[create_concept(2000000001, "ICU Continuous Monitoring")],
    occurrence_start_datetime=DateRange(value="2025-01-01", op="gte"),
    num_of_files=NumericRange(value=10, op="gte"),
)

expression1 = CohortExpression(
    primary_criteria=PrimaryCriteria(
        criteria_list=[waveform_occ_example], observation_window={"priorDays": 0, "postDays": 0}, primary_limit={"type": "First"}
    ),
    concept_sets=[],
    inclusion_rules=[],
    qualified_limit={"type": "First"},
    expression_limit={"type": "First"},
)

builder = CohortExpressionQueryBuilder()
options = BuildExpressionQueryOptions()
options.cdm_schema = "cdm"
options.result_schema = "results"
options.cohort_id = 1

sql1 = builder.build_expression_query(expression1, options)
print("\n--- SQL Snippet ---")
print(sql1[sql1.find("FROM") : sql1.find("FROM") + 200] + "...")
print("\n✓ Table: waveform_occurrence")
print("✓ Filters: ICU monitoring, ≥10 files, starting after 2025-01-01")

md1 = MarkdownRender().render_cohort_expression(expression1)
print("\n--- Markdown ---")
print(md1.split("\n")[4:7])  # Print relevant lines

# =============================================================================
# Example 2: EDF files from emergency department
# =============================================================================
print("\n" + "=" * 80)
print("Example 2: EDF Waveform Files")
print("=" * 80)

waveform_reg_example = WaveformRegistry(file_extension_concept_id=[create_concept(2000000010, "EDF")])

expression2 = CohortExpression(
    primary_criteria=PrimaryCriteria(
        criteria_list=[waveform_reg_example], observation_window={"priorDays": 0, "postDays": 0}, primary_limit={"type": "First"}
    ),
    concept_sets=[],
    inclusion_rules=[],
    qualified_limit={"type": "First"},
)

sql2 = builder.build_expression_query(expression2, options)
print("\n--- SQL Snippet ---")
print(sql2[sql2.find("FROM") : sql2.find("FROM") + 200] + "...")
print("\n✓ Table: waveform_registry")
print("✓ Filters: EDF file format only")

# =============================================================================
# Example 3: High-quality ECG Lead II at ≥500Hz
# =============================================================================
print("\n" + "=" * 80)
print("Example 3: High-Quality ECG Lead II (≥500 Hz)")
print("=" * 80)

waveform_chan_example = WaveformChannelMetadata(
    channel_concept_id=[create_concept(2000000020, "ECG Lead II")],
    metadata_concept_id=[create_concept(2000000030, "Sampling Rate")],
    value_as_number=NumericRange(value=500, op="gte"),  # ≥500 Hz
    unit_concept_id=[create_concept(8504, "Hz")],
)

expression3 = CohortExpression(
    primary_criteria=PrimaryCriteria(
        criteria_list=[waveform_chan_example], observation_window={"priorDays": 0, "postDays": 0}, primary_limit={"type": "First"}
    ),
    concept_sets=[],
    inclusion_rules=[],
    qualified_limit={"type": "First"},
)

sql3 = builder.build_expression_query(expression3, options)
print("\n--- SQL Snippet ---")
print(sql3[sql3.find("FROM") : sql3.find("FROM") + 250] + "...")
print("\n✓ Table: waveform_channel_metadata")
print("✓ Filters: ECG Lead II, sampling rate ≥500 Hz")
print("✓ Use Case: Ensure high-quality signals for QRS detection")

# =============================================================================
# Example 4: Derived Heart Rate 60-100 bpm (MOST CLINICALLY VALUABLE)
# =============================================================================
print("\n" + "=" * 80)
print("Example 4: Derived Heart Rate 60-100 bpm (Normal Range)")
print("=" * 80)

waveform_feat_example = WaveformFeature(
    feature_concept_id=[create_concept(3027018, "Heart Rate")],
    algorithm_concept_id=[create_concept(2000000040, "Pan-Tompkins QRS Detection")],
    value_as_number=NumericRange(value=60, op="gte", extent=100),  # 60-100 bpm
    unit_concept_id=[create_concept(8541, "beats/min")],
)

expression4 = CohortExpression(
    primary_criteria=PrimaryCriteria(
        criteria_list=[waveform_feat_example], observation_window={"priorDays": 0, "postDays": 0}, primary_limit={"type": "First"}
    ),
    concept_sets=[],
    inclusion_rules=[],
    qualified_limit={"type": "First"},
)

sql4 = builder.build_expression_query(expression4, options)
print("\n--- SQL Snippet ---")
print(sql4[sql4.find("FROM") : sql4.find("FROM") + 250] + "...")
print("\n✓ Table: waveform_feature")
print("✓ Filters: Heart Rate 60-100 bpm derived by Pan-Tompkins algorithm")
print("✓ Use Case: Identify patients with normal cardiac rhythm")

md4 = MarkdownRender().render_cohort_expression(expression4)
print("\n--- Markdown ---")
print(md4.split("\n")[4:7])  # Print relevant lines

# =============================================================================
# Verification Summary
# =============================================================================
print("\n" + "=" * 80)
print("VERIFICATION SUMMARY")
print("=" * 80)

checks = [
    ("waveform_occurrence table used", "waveform_occurrence" in sql1),
    ("waveform_registry table used", "waveform_registry" in sql2),
    ("waveform_channel_metadata table used", "waveform_channel_metadata" in sql3),
    ("waveform_feature table used", "waveform_feature" in sql4),
    ("Correct column: waveform_occurrence_concept_id", "waveform_occurrence_concept_id" in sql1),
    ("Correct column: waveform_occurrence_start_datetime", "waveform_occurrence_start_datetime" in sql1),
    ("Correct column: file_extension_concept_id", "file_extension_concept_id" in sql2),
    ("Correct column: channel_concept_id", "channel_concept_id" in sql3),
    ("Correct column: feature_concept_id", "feature_concept_id" in sql4),
    ("Markdown rendering works", "waveform-derived feature" in md4.lower()),
]

for check_name, result in checks:
    status = "✓" if result else "✗"
    print(f"{status} {check_name}")

all_passed = all(r for _, r in checks)
print("\n" + ("=" * 80))
if all_passed:
    print("SUCCESS: All 4 OHDSI Waveform Extension tables implemented correctly!")
else:
    print("FAILURE: Some checks failed")
print("=" * 80)
