from typing import Set

from circe.cohortdefinition.builders.base import CriteriaSqlBuilder
from circe.cohortdefinition.builders.utils import CriteriaColumn, BuilderUtils, BuilderOptions
from circe.extensions import register_sql_builder
from ..criteria import WaveformFeature

@register_sql_builder(WaveformFeature)
class WaveformFeatureSqlBuilder(CriteriaSqlBuilder[WaveformFeature]):
    """
    SQL Builder for Waveform Feature criteria.
    
    Maps to the waveform_feature table in the OHDSI Waveform Extension.
    This is the most clinically valuable table for cohort selection, containing
    derived measurements like heart rate, SpO2, arrhythmia detections, etc.
    
    Reference: https://ohdsi.github.io/WaveformWG/waveform-tables.html
    """
    
    def get_query_template(self) -> str:
        return """
SELECT C.person_id, C.waveform_feature_id as event_id,
       C.waveform_feature_start_timestamp as start_date,
       C.waveform_feature_end_timestamp as end_date,
       WO.visit_occurrence_id,
       C.waveform_feature_start_timestamp as sort_date
FROM @cdm_database_schema.waveform_feature C
LEFT JOIN @cdm_database_schema.waveform_occurrence WO ON C.waveform_occurrence_id = WO.waveform_occurrence_id
@codesetClause
@joinClause
WHERE @whereClause
"""
    
    def get_default_columns(self) -> Set[CriteriaColumn]:
        return {
            CriteriaColumn.START_DATE,
            CriteriaColumn.END_DATE,
            CriteriaColumn.VISIT_ID
        }
    
    def get_table_column_for_criteria_column(self, column: CriteriaColumn) -> str:
        if column == CriteriaColumn.START_DATE:
            return "C.waveform_feature_start_timestamp"
        elif column == CriteriaColumn.END_DATE:
            return "C.waveform_feature_end_timestamp"
        elif column == CriteriaColumn.VISIT_ID:
            return "WO.visit_occurrence_id"
        else:
            raise ValueError(f"Invalid CriteriaColumn for Waveform Feature: {column}")

    def get_criteria_sql_with_options(self, criteria: WaveformFeature, options: BuilderOptions) -> str:
        query = self.get_query_template()
        
        where_clauses = []
        join_clauses = []
        codeset_clause = ""
        
        # Parent links
        if criteria.waveform_occurrence_id:
            where_clauses.append(
                BuilderUtils.build_numeric_range_clause("C.waveform_occurrence_id", criteria.waveform_occurrence_id)
            )
        if criteria.waveform_registry_id:
            where_clauses.append(
                BuilderUtils.build_numeric_range_clause("C.waveform_registry_id", criteria.waveform_registry_id)
            )
        if criteria.waveform_channel_metadata_id:
            where_clauses.append(
                BuilderUtils.build_numeric_range_clause("C.waveform_channel_metadata_id", criteria.waveform_channel_metadata_id)
            )
        
        # Feature type (e.g., heart rate, SpO2)
        if criteria.feature_concept_id:
            ids = [str(c.concept_id) for c in criteria.feature_concept_id if c.concept_id]
            if ids:
                where_clauses.append(f"C.feature_concept_id IN ({','.join(ids)})")
        
        # Algorithm used
        if criteria.algorithm_concept_id:
            ids = [str(c.concept_id) for c in criteria.algorithm_concept_id if c.concept_id]
            if ids:
                where_clauses.append(f"C.algorithm_concept_id IN ({','.join(ids)})")
        if criteria.algorithm_source_value:
            where_clauses.append(
                BuilderUtils.build_text_filter_clause("C.algorithm_source_value", criteria.algorithm_source_value)
            )
        
        # Temporal window
        if criteria.feature_start_timestamp:
            where_clauses.append(
                BuilderUtils.build_date_range_clause("C.waveform_feature_start_timestamp", criteria.feature_start_timestamp)
            )
        if criteria.feature_end_timestamp:
            where_clauses.append(
                BuilderUtils.build_date_range_clause("C.waveform_feature_end_timestamp", criteria.feature_end_timestamp)
            )
        
        # Feature values
        if criteria.value_as_number:
            where_clauses.append(
                BuilderUtils.build_numeric_range_clause("C.value_as_number", criteria.value_as_number)
            )
        if criteria.value_as_concept_id:
            ids = [str(c.concept_id) for c in criteria.value_as_concept_id if c.concept_id]
            if ids:
                where_clauses.append(f"C.value_as_concept_id IN ({','.join(ids)})")
        
        # Units
        if criteria.unit_concept_id:
            ids = [str(c.concept_id) for c in criteria.unit_concept_id if c.concept_id]
            if ids:
                where_clauses.append(f"C.unit_concept_id IN ({','.join(ids)})")
        
        # Links to standard OMOP tables
        if criteria.measurement_id:
            where_clauses.append(
                BuilderUtils.build_numeric_range_clause("C.measurement_id", criteria.measurement_id)
            )
        if criteria.observation_id:
            where_clauses.append(
                BuilderUtils.build_numeric_range_clause("C.observation_id", criteria.observation_id)
            )
        
        # Get person_id from occurrence
        where_clauses.append("WO.person_id IS NOT NULL")
        
        # Apply replacements
        query = query.replace("@cdm_database_schema", options.cdm_database_schema if options else "@cdm_database_schema")
        query = query.replace("@codesetClause", codeset_clause)
        query = query.replace("@joinClause", "\n".join(join_clauses))
        query = query.replace("@whereClause", " AND ".join(where_clauses) if where_clauses else "1=1")
        
        # Fix person_id in SELECT - need to pull from occurrence
        query = query.replace("C.person_id", "WO.person_id")
        
        return query
