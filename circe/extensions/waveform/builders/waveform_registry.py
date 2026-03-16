from typing import Set

from circe.cohortdefinition.builders.base import CriteriaSqlBuilder
from circe.cohortdefinition.builders.utils import CriteriaColumn, BuilderUtils, BuilderOptions
from circe.extensions import sql_builder, markdown_template
from ..criteria import WaveformRegistry


@sql_builder(WaveformRegistry)
@markdown_template(WaveformRegistry, "waveform_registry.j2")
class WaveformRegistrySqlBuilder(CriteriaSqlBuilder[WaveformRegistry]):
    """
    SQL Builder for Waveform Registry criteria.
    
    Maps to the waveform_registry table in the OHDSI Waveform Extension.
    Reference: https://ohdsi.github.io/WaveformWG/waveform-tables.html
    """
    
    def get_query_template(self) -> str:
        return """
SELECT C.person_id, C.waveform_registry_id as event_id,
       C.waveform_file_start_datetime as start_date,
       C.waveform_file_end_datetime as end_date,
       C.visit_occurrence_id,
       C.waveform_file_start_datetime as sort_date
FROM @cdm_database_schema.waveform_registry C
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
            return "C.waveform_file_start_datetime"
        elif column == CriteriaColumn.END_DATE:
            return "C.waveform_file_end_datetime"
        elif column == CriteriaColumn.VISIT_ID:
            return "C.visit_occurrence_id"
        else:
            raise ValueError(f"Invalid CriteriaColumn for Waveform Registry: {column}")

    def get_criteria_sql_with_options(self, criteria: WaveformRegistry, options: BuilderOptions) -> str:
        query = self.get_query_template()
        
        where_clauses = []
        join_clauses = []
        codeset_clause = ""
        
        # Link to parent occurrence
        if criteria.waveform_occurrence_id:
            where_clauses.append(
                BuilderUtils.build_numeric_range_clause("C.waveform_occurrence_id", criteria.waveform_occurrence_id)
            )
        
        # File temporal bounds
        if criteria.file_start_datetime:
            where_clauses.append(
                BuilderUtils.build_date_range_clause("C.waveform_file_start_datetime", criteria.file_start_datetime)
            )
        if criteria.file_end_datetime:
            where_clauses.append(
                BuilderUtils.build_date_range_clause("C.waveform_file_end_datetime", criteria.file_end_datetime)
            )
        
        # File format
        if criteria.file_extension_concept_id:
            ids = [str(c.concept_id) for c in criteria.file_extension_concept_id if c.concept_id]
            if ids:
                where_clauses.append(f"C.file_extension_concept_id IN ({','.join(ids)})")
        if criteria.file_extension_source_value:
            where_clauses.append(
                BuilderUtils.build_text_filter_clause("C.file_extension_source_value", criteria.file_extension_source_value)
            )
        
        # Visit context
        if criteria.visit_occurrence_id:
            where_clauses.append(
                BuilderUtils.build_numeric_range_clause("C.visit_occurrence_id", criteria.visit_occurrence_id)
            )
        if criteria.visit_detail_id:
            where_clauses.append(
                BuilderUtils.build_numeric_range_clause("C.visit_detail_id", criteria.visit_detail_id)
            )
        
        # Apply replacements
        query = query.replace("@cdm_database_schema", options.cdm_database_schema if options else "@cdm_database_schema")
        query = query.replace("@codesetClause", codeset_clause)
        query = query.replace("@joinClause", "\n".join(join_clauses))
        query = query.replace("@whereClause", " AND ".join(where_clauses) if where_clauses else "1=1")
        
        return query
