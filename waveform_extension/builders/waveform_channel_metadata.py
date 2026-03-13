from typing import Set

from circe.cohortdefinition.builders.base import CriteriaSqlBuilder
from circe.cohortdefinition.builders.utils import CriteriaColumn, BuilderUtils, BuilderOptions
from ..criteria import WaveformChannelMetadata

class WaveformChannelMetadataSqlBuilder(CriteriaSqlBuilder[WaveformChannelMetadata]):
    """
    SQL Builder for Waveform Channel Metadata criteria.
    
    Maps to the waveform_channel_metadata table in the OHDSI Waveform Extension.
    Reference: https://ohdsi.github.io/WaveformWG/waveform-tables.html
    """
    
    def get_query_template(self) -> str:
        return """
SELECT C.person_id, C.waveform_channel_metadata_id as event_id,
       NULL as start_date, NULL as end_date,
       NULL as visit_occurrence_id,
       NULL as sort_date
FROM @cdm_database_schema.waveform_channel_metadata C
LEFT JOIN @cdm_database_schema.waveform_registry WR ON C.waveform_registry_id = WR.waveform_registry_id
@codesetClause
@joinClause
WHERE @whereClause
"""
    
    def get_default_columns(self) -> Set[CriteriaColumn]:
        return set()  # Metadata doesn't have standard event columns
    
    def get_table_column_for_criteria_column(self, column: CriteriaColumn) -> str:
        # Channel metadata doesn't map to standard event columns
        raise ValueError(f"Invalid CriteriaColumn for Waveform Channel Metadata: {column}")

    def get_criteria_sql_with_options(self, criteria: WaveformChannelMetadata, options: BuilderOptions) -> str:
        query = self.get_query_template()
        
        where_clauses = []
        join_clauses = []
        codeset_clause = ""
        
        # Link to registry file
        if criteria.waveform_registry_id:
            where_clauses.append(
                BuilderUtils.build_numeric_range_clause("C.waveform_registry_id", criteria.waveform_registry_id)
            )
        
        # Channel identification
        if criteria.channel_concept_id:
            ids = [str(c.concept_id) for c in criteria.channel_concept_id if c.concept_id]
            if ids:
                where_clauses.append(f"C.channel_concept_id IN ({','.join(ids)})")
        if criteria.waveform_channel_source_value:
            where_clauses.append(
                BuilderUtils.build_text_filter_clause("C.waveform_channel_source_value", criteria.waveform_channel_source_value)
            )
        
        # Metadata type
        if criteria.metadata_concept_id:
            ids = [str(c.concept_id) for c in criteria.metadata_concept_id if c.concept_id]
            if ids:
                where_clauses.append(f"C.metadata_concept_id IN ({','.join(ids)})")
        if criteria.metadata_source_value:
            where_clauses.append(
                BuilderUtils.build_text_filter_clause("C.metadata_source_value", criteria.metadata_source_value)
            )
        
        # Metadata values
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
        
        # Device/procedure linkage
        if criteria.device_exposure_id:
            where_clauses.append(
                BuilderUtils.build_numeric_range_clause("C.device_exposure_id", criteria.device_exposure_id)
            )
        if criteria.procedure_occurrence_id:
            where_clauses.append(
                BuilderUtils.build_numeric_range_clause("C.procedure_occurrence_id", criteria.procedure_occurrence_id)
            )
        
        # Get person_id from registry since it's not in channel_metadata
        where_clauses.append("WR.person_id IS NOT NULL")
        
        # Apply replacements
        query = query.replace("@cdm_database_schema", options.cdm_database_schema if options else "@cdm_database_schema")
        query = query.replace("@codesetClause", codeset_clause)
        query = query.replace("@joinClause", "\n".join(join_clauses))
        query = query.replace("@whereClause", " AND ".join(where_clauses) if where_clauses else "1=1")
        
        # Fix person_id in SELECT - need to pull from registry
        query = query.replace("C.person_id", "WR.person_id")
        
        return query
