from typing import Set

from circe.cohortdefinition.builders.base import CriteriaSqlBuilder
from circe.cohortdefinition.builders.utils import CriteriaColumn, BuilderUtils, BuilderOptions
from circe.extensions import sql_builder, markdown_template
from ..criteria import WaveformOccurrence


@sql_builder(WaveformOccurrence)
@markdown_template(WaveformOccurrence, "waveform_occurrence.j2")
class WaveformOccurrenceSqlBuilder(CriteriaSqlBuilder[WaveformOccurrence]):
    """
    SQL Builder for Waveform Occurrence criteria.
    
    Maps to the waveform_occurrence table in the OHDSI Waveform Extension.
    Reference: https://ohdsi.github.io/WaveformWG/waveform-tables.html
    """
    
    def get_query_template(self) -> str:
        return """
SELECT C.person_id, C.waveform_occurrence_id as event_id, 
       C.waveform_occurrence_start_datetime as start_date, 
       C.waveform_occurrence_end_datetime as end_date,
       C.visit_occurrence_id, 
       C.waveform_occurrence_start_datetime as sort_date
FROM @cdm_database_schema.waveform_occurrence C
@codesetClause
@joinClause
WHERE @whereClause
"""
    
    def get_default_columns(self) -> Set[CriteriaColumn]:
        return {
            CriteriaColumn.START_DATE,
            CriteriaColumn.END_DATE,
            CriteriaColumn.VISIT_ID,
            CriteriaColumn.DOMAIN_CONCEPT
        }
    
    def get_table_column_for_criteria_column(self, column: CriteriaColumn) -> str:
        if column == CriteriaColumn.START_DATE:
            return "C.waveform_occurrence_start_datetime"
        elif column == CriteriaColumn.END_DATE:
            return "C.waveform_occurrence_end_datetime"
        elif column == CriteriaColumn.VISIT_ID:
            return "C.visit_occurrence_id"
        elif column == CriteriaColumn.DOMAIN_CONCEPT:
            return "C.waveform_occurrence_concept_id"
        else:
            raise ValueError(f"Invalid CriteriaColumn for Waveform Occurrence: {column}")

    def get_criteria_sql_with_options(self, criteria: WaveformOccurrence, options: BuilderOptions) -> str:
        query = self.get_query_template()
        
        where_clauses = []
        join_clauses = []
        codeset_clause = ""
        
        # Filter by waveform occurrence concept
        if criteria.waveform_occurrence_concept_id:
            ids = [str(c.concept_id) for c in criteria.waveform_occurrence_concept_id if c.concept_id]
            if ids:
                where_clauses.append(f"C.waveform_occurrence_concept_id IN ({','.join(ids)})")

        # Date filters
        if criteria.occurrence_start_datetime:
            where_clauses.append(
                BuilderUtils.build_date_range_clause("C.waveform_occurrence_start_datetime", criteria.occurrence_start_datetime)
            )
        if criteria.occurrence_end_datetime:
            where_clauses.append(
                BuilderUtils.build_date_range_clause("C.waveform_occurrence_end_datetime", criteria.occurrence_end_datetime)
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
            
        # File metadata
        if criteria.num_of_files:
            where_clauses.append(
                BuilderUtils.build_numeric_range_clause("C.num_of_files", criteria.num_of_files)
            )
            
        # Source value text filter
        if criteria.waveform_occurrence_source_value:
            where_clauses.append(
                BuilderUtils.build_text_filter_clause("C.waveform_occurrence_source_value", criteria.waveform_occurrence_source_value)
            )
            
        # Sequence/chain filtering
        if criteria.preceding_waveform_occurrence_id:
            where_clauses.append(
                BuilderUtils.build_numeric_range_clause("C.preceding_waveform_occurrence_id", criteria.preceding_waveform_occurrence_id)
            )

        # Apply replacements
        query = query.replace("@cdm_database_schema", options.cdm_database_schema if options else "@cdm_database_schema")
        query = query.replace("@codesetClause", codeset_clause)
        query = query.replace("@joinClause", "\n".join(join_clauses))
        query = query.replace("@whereClause", " AND ".join(where_clauses) if where_clauses else "1=1")
        
        return query
