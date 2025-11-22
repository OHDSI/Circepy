"""
Markdown rendering for cohort definitions.

This module provides functionality to generate human-readable markdown descriptions
of cohort definitions, mirroring the Java CIRCE-BE MarkdownRender functionality.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List, Optional, Any, Union, Dict
from datetime import datetime
import json
from ..cohort import CohortExpression
from ..criteria import (
    Criteria, CriteriaGroup, DemographicCriteria, InclusionRule,
    ConditionOccurrence, DrugExposure, ProcedureOccurrence, VisitOccurrence,
    Observation, Measurement, DeviceExposure, Specimen, Death, VisitDetail,
    ObservationPeriod, PayerPlanPeriod, LocationRegion, ConditionEra,
    DrugEra, DoseEra, GeoCriteria, Occurrence, CorelatedCriteria
)
from ..core import (
    ResultLimit, Period, CollapseSettings, EndStrategy, DateOffsetStrategy,
    CustomEraStrategy, PrimaryCriteria, DateRange, NumericRange,
    ConceptSetSelection, CollapseType, DateType, TextFilter, Window, WindowBound,
    DateAdjustment, ObservationFilter
)
from ...vocabulary.concept import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


class MarkdownRender:
    """Generates human-readable markdown descriptions of cohort definitions.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.printfriendly.MarkdownRender
    """
    
    def __init__(self, concept_sets: Optional[List[ConceptSet]] = None, include_concept_sets: bool = False):
        """Initialize the markdown renderer.
        
        Args:
            concept_sets: Optional list of concept sets for resolving codeset IDs to names
            include_concept_sets: Whether to include concept set tables in the output (default: False)
        """
        self._concept_sets = concept_sets or []
        self._include_concept_sets = include_concept_sets
    
    def render_cohort_expression(self, cohort_expression: Union[CohortExpression, str], include_concept_sets: Optional[bool] = None, title: Optional[str] = None) -> str:
        """Render a cohort expression to markdown format.
        
        Args:
            cohort_expression: The cohort expression to render, or JSON string
            include_concept_sets: Whether to include concept set tables in the output (overrides init parameter if provided)
            title: Optional title for the markdown output
            
        Returns:
            Markdown formatted string describing the cohort
        """
        # Handle JSON string input
        if isinstance(cohort_expression, str):
            cohort_expression = CohortExpression.model_validate_json(cohort_expression)
        
        if not cohort_expression:
            return "# Invalid Cohort Expression\n\nNo cohort expression provided."
        
        # Update concept sets for resolving names
        if cohort_expression.concept_sets:
            self._concept_sets = cohort_expression.concept_sets
        
        markdown_parts = []
        
        # Title
        title = title or cohort_expression.title or "Untitled Cohort"
        markdown_parts.append(f"# {title}\n")
        
        # Description section
        markdown_parts.append("## Description\n")
        markdown_parts.append(self._render_description(cohort_expression))
        
        # Primary criteria (Cohort Entry Events)
        if cohort_expression.primary_criteria:
            markdown_parts.append("### Cohort Entry Events\n")
            markdown_parts.append(self._render_primary_criteria(
                cohort_expression.primary_criteria,
                cohort_expression.additional_criteria,
                cohort_expression.inclusion_rules,
                cohort_expression.qualified_limit,
                cohort_expression.expression_limit
            ))
        
        # Additional criteria (restricts entry events)
        if cohort_expression.additional_criteria:
            markdown_parts.append(self._render_additional_criteria(
                cohort_expression.primary_criteria,
                cohort_expression.additional_criteria,
                cohort_expression.qualified_limit
            ))
        
        # Inclusion rules
        if cohort_expression.inclusion_rules:
            markdown_parts.append("### Inclusion Criteria\n")
            markdown_parts.append(self._render_inclusion_rules(cohort_expression.inclusion_rules))
        
        # Expression limit (conditional)
        if cohort_expression.expression_limit:
            primary_limit = cohort_expression.primary_criteria.primary_limit if cohort_expression.primary_criteria else None
            if (not primary_limit or primary_limit.type == "All") and \
               (not cohort_expression.additional_criteria or not cohort_expression.qualified_limit or cohort_expression.qualified_limit.type == "All") and \
               cohort_expression.expression_limit.type != "All":
                markdown_parts.append(f"\nLimit qualifying entry events to the {self._format_result_limit(cohort_expression.expression_limit)} per person.\n")
        
        # Cohort Exit
        markdown_parts.append("### Cohort Exit\n")
        if cohort_expression.end_strategy:
            markdown_parts.append(self._render_end_strategy(cohort_expression.end_strategy))
        
        # Censor criteria
        if cohort_expression.censoring_criteria:
            markdown_parts.append(self._render_censor_criteria(cohort_expression.censoring_criteria))
        
        # Cohort Eras - always show this section (R shows it even when collapse_settings is missing)
        markdown_parts.append("### Cohort Eras\n")
        markdown_parts.append(self._render_cohort_eras(cohort_expression.collapse_settings))
        
        # Censor window
        if cohort_expression.censor_window:
            markdown_parts.append(self._render_censor_window(cohort_expression.censor_window))
        
        # CDM version range
        if cohort_expression.cdm_version_range:
            markdown_parts.append("## CDM Version Range\n")
            markdown_parts.append(self._render_period(cohort_expression.cdm_version_range))
        
        # Concept sets (only if explicitly requested)
        should_include_concept_sets = include_concept_sets if include_concept_sets is not None else self._include_concept_sets
        if should_include_concept_sets and cohort_expression.concept_sets:
            markdown_parts.append("## Concept Sets\n")
            markdown_parts.append(self._render_concept_sets(cohort_expression.concept_sets))
        
        return "\n".join(markdown_parts)
    
    def render_concept_set_list(self, concept_sets: Union[List[ConceptSet], str]) -> str:
        """Render a list of concept sets to markdown format.
        
        Args:
            concept_sets: List of ConceptSet objects or JSON string
            
        Returns:
            Markdown formatted string describing the concept sets
        """
        # Handle JSON string input
        if isinstance(concept_sets, str):
            data = json.loads(concept_sets)
            if isinstance(data, list):
                concept_sets = [ConceptSet.model_validate(item) for item in data]
            else:
                concept_sets = [ConceptSet.model_validate(data)]
        
        if not concept_sets:
            return "No concept sets specified.\n"
        
        # Update internal concept sets for name resolution
        self._concept_sets = concept_sets
        
        return self._render_concept_sets(concept_sets)
    
    def render_concept_set(self, concept_set: Union[ConceptSet, str]) -> str:
        """Render a single concept set to markdown format.
        
        Args:
            concept_set: ConceptSet object or JSON string
            
        Returns:
            Markdown formatted string describing the concept set
        """
        # Handle JSON string input
        if isinstance(concept_set, str):
            data = json.loads(concept_set)
            concept_set = ConceptSet.model_validate(data)
        
        return self.render_concept_set_list([concept_set])
    
    # ============================================================================
    # Utility Methods (matching Java FreeMarker utilities)
    # ============================================================================
    
    def _get_concept_set_name(self, codeset_id: Optional[int], default_name: str) -> str:
        """Get concept set name from codeset ID, or return default.
        
        Java equivalent: utils.codesetName()
        
        Args:
            codeset_id: Optional concept set ID
            default_name: Default name if codeset_id is None or not found
            
        Returns:
            Concept set name in quotes, or default name
        """
        if not codeset_id:
            return default_name
        
        # Find concept set by ID
        for concept_set in self._concept_sets:
            if concept_set.id == codeset_id:
                return f"'{concept_set.name}'"
        
        return default_name
    
    def _format_date(self, date_string: str) -> str:
        """Format date string from YYYY-MM-DD to "Month Day, Year".
        
        Java equivalent: utils.formatDate()
        
        Args:
            date_string: Date string in YYYY-MM-DD format
            
        Returns:
            Formatted date string like "January 1, 2010"
        """
        try:
            # Parse YYYY-MM-DD format
            if isinstance(date_string, str) and len(date_string) == 10:
                dt = datetime.strptime(date_string, "%Y-%m-%d")
                return dt.strftime("%B %d, %Y")
            return date_string
        except (ValueError, AttributeError):
            return "_invalid date_"
    
    def _format_numeric_range(self, numeric_range: NumericRange) -> str:
        """Format numeric range with proper operators.
        
        Java equivalent: inputTypes.NumericRange macro
        
        Args:
            numeric_range: NumericRange object
            
        Returns:
            Formatted string like ">= 18" or "between 18 and 65"
        """
        if not numeric_range or not numeric_range.op:
            return ""
        
        op_map = {
            "lt": "&lt;",
            "lte": "&lt;=",
            "eq": "=",
            "gt": "&gt;",
            "gte": "&gt;=",
            "bt": "between",
            "!bt": "not Between"
        }
        
        op_name = op_map.get(numeric_range.op, numeric_range.op)
        
        if numeric_range.op.endswith("bt") and numeric_range.value is not None and numeric_range.extent is not None:
            return f"{op_name} {numeric_range.value} and {numeric_range.extent}"
        elif numeric_range.value is not None:
            return f"{op_name} {numeric_range.value}"
        else:
            return op_name
    
    def _format_date_range(self, date_range: DateRange) -> str:
        """Format date range with proper operators and formatted dates.
        
        Java equivalent: inputTypes.DateRange macro
        
        Args:
            date_range: DateRange object
            
        Returns:
            Formatted string like "before January 1, 2010" or "between January 1, 2010 and December 31, 2010"
        """
        if not date_range or not date_range.op:
            return ""
        
        op_map = {
            "lt": "before",
            "lte": "on or Before",
            "eq": "on",
            "gt": "after",
            "gte": "on or after",
            "bt": "between",
            "!bt": "not between"
        }
        
        op_name = op_map.get(date_range.op, date_range.op)
        
        if date_range.value:
            formatted_date = self._format_date(date_range.value)
            if date_range.op.endswith("bt") and date_range.extent:
                formatted_extent = self._format_date(date_range.extent)
                return f"{op_name} {formatted_date} and {formatted_extent}"
            else:
                return f"{op_name} {formatted_date}"
        else:
            return op_name
    
    def _format_text_filter(self, text_filter: TextFilter) -> str:
        """Format text filter with proper operators.
        
        Java equivalent: inputTypes.TextFilter macro
        
        Args:
            text_filter: TextFilter object
            
        Returns:
            Formatted string like 'containing "some text"'
        """
        if not text_filter or not text_filter.op:
            return ""
        
        op_map = {
            "startsWith": "starting with",
            "contains": "containing",
            "endsWith": "ending with",
            "!startsWith": "not starting with",
            "!contains": "not containing",
            "!endsWith": "not ending with"
        }
        
        op_name = op_map.get(text_filter.op, text_filter.op)
        text = text_filter.text or ""
        
        return f'{op_name} "{text}"'
    
    def _format_concept_list(self, concepts: List[Concept], quote: str = '"') -> str:
        """Format list of concepts as quoted list.
        
        Java equivalent: inputTypes.ConceptList macro
        
        Args:
            concepts: List of Concept objects
            quote: Quote character to use
            
        Returns:
            Formatted string like '"admission note" or "ancillary report"' or '[none specified]'
        """
        if not concepts or len(concepts) == 0:
            return "[none specified]"
        
        quoted = [f'{quote}{c.concept_name.lower()}{quote}' for c in concepts if c and c.concept_name]
        
        if len(quoted) == 1:
            return quoted[0]
        elif len(quoted) == 2:
            return f"{quoted[0]} or {quoted[1]}"
        else:
            result = ", ".join(quoted[:-1])
            return f"{result} or {quoted[-1]}"
    
    def _format_concept_set_selection(self, selection: ConceptSetSelection, default_name: str = "any") -> str:
        """Format concept set selection.
        
        Java equivalent: inputTypes.ConceptSetSelection macro
        
        Args:
            selection: ConceptSetSelection object
            default_name: Default name if codeset_id is None
            
        Returns:
            Formatted string like "in 'Concept Set 1'" or "not in 'Concept Set 1'"
        """
        if not selection:
            return ""
        
        prefix = "not " if selection.is_exclusion else ""
        codeset_name = self._get_concept_set_name(selection.codeset_id, default_name)
        
        return f"{prefix}in {codeset_name}"
    
    def _format_window_criteria(self, window: Window, index_label: str = "cohort entry") -> str:
        """Format window criteria with natural language.
        
        Java equivalent: inputTypes.Window macro
        
        Args:
            window: Window object
            index_label: Label for the index event (e.g., "cohort entry", "Concept Set 1")
            
        Returns:
            Formatted string describing the time window
        """
        if not window:
            return ""
        
        use_end = getattr(window, 'use_event_end', False) or getattr(window, 'useEventEnd', False)
        use_index_end = getattr(window, 'use_index_end', False) or getattr(window, 'useIndexEnd', False)
        
        event_part = "ending" if use_end else "starting"
        index_part = "end date" if use_index_end else "start date"
        
        start = window.start
        end = window.end
        
        # Handle various window patterns
        if start and end:
            start_days = start.days if start.days is not None else 0
            end_days = end.days if end.days is not None else "all"
            start_coeff = start.coeff if start else 1
            end_coeff = end.coeff if end else 1
            
            start_dir = "before" if start_coeff < 0 else "after"
            end_dir = "before" if end_coeff < 0 else "after"
            
            # Special case: both in the past (coeff=-1, end_days < start_days)
            if start_coeff == -1 and end_coeff == -1 and isinstance(start_days, int) and isinstance(end_days, int) and end_days < start_days:
                return f"{event_part} in the {start_days} days prior to {index_label} {index_part}"
            elif start_days == "all" and end_days == 0 and start_coeff == -1:
                return f"{event_part} anytime on or before {index_label} {index_part}"
            elif end_days == "all" and isinstance(start_days, int) and start_days > 0 and end_coeff == 1:
                return f"{event_part} anytime after {start_days} days {start_dir} {index_label} {index_part}"
            elif start_days == "all" and isinstance(end_days, int) and end_days > 0 and start_coeff == -1:
                return f"{event_part} anytime up to {end_days} days {end_dir} {index_label} {index_part}"
            else:
                return f"{event_part} between {start_days} days {start_dir} and {end_days} days {end_dir} {index_label} {index_part}"
        
        return f"{event_part} {index_label} {index_part}"
    
    def _format_occurrence(self, occurrence: Occurrence) -> str:
        """Format occurrence with count type.
        
        Java equivalent: getCountType() function
        
        Args:
            occurrence: Occurrence object
            
        Returns:
            Formatted string like "at least 1", "at most 5", "exactly 3"
        """
        if not occurrence:
            return ""
        
        type_map = {
            0: "exactly",
            1: "at most",
            2: "at least"
        }
        
        type_name = type_map.get(occurrence.type, "")
        count = occurrence.count if occurrence.count is not None else 1
        
        if type_name:
            return f"{type_name} {count}"
        else:
            return str(count)
    
    def _format_result_limit(self, limit: ResultLimit) -> str:
        """Format result limit.
        
        Java equivalent: inputTypes.Limit macro
        
        Args:
            limit: ResultLimit object
            
        Returns:
            Formatted string like "all events", "earliest event", "latest event"
        """
        if not limit or not limit.type:
            return "all events"
        
        type_map = {
            "All": "all events",
            "First": "earliest event",
            "Last": "latest event"
        }
        
        return type_map.get(limit.type, limit.type)
    
    def _format_group_type(self, group_type: str) -> str:
        """Format group type.
        
        Java equivalent: groupTypeOptions
        
        Args:
            group_type: Group type string (ALL, ANY, AT_LEAST, AT_MOST)
            
        Returns:
            Formatted string like "all", "any", "at least", "at most"
        """
        type_map = {
            "ALL": "all",
            "ANY": "any",
            "AT_LEAST": "at least",
            "AT_MOST": "at most"
        }
        
        return type_map.get(group_type, group_type.lower() if group_type else "")
    
    def _render_description(self, cohort_expression: CohortExpression) -> str:
        """Render the description section."""
        description_parts = []
        
        if cohort_expression.title:
            description_parts.append(f"**Title:** {cohort_expression.title}")
        
        # Add any other descriptive information
        description_parts.append("This cohort definition specifies the criteria for identifying patients.")
        
        return "\n".join(description_parts) + "\n"
    
    def _render_primary_criteria(self, primary_criteria: PrimaryCriteria, 
                                 additional_criteria: Optional[CriteriaGroup] = None,
                                 inclusion_rules: Optional[List[InclusionRule]] = None,
                                 qualified_limit: Optional[ResultLimit] = None,
                                 expression_limit: Optional[ResultLimit] = None) -> str:
        """Render primary criteria (Cohort Entry Events section).
        
        Java equivalent: cohortExpression.ftl "Cohort Entry Events" section
        
        Args:
            primary_criteria: PrimaryCriteria object
            additional_criteria: Optional additional criteria
            inclusion_rules: Optional inclusion rules list
            qualified_limit: Optional qualified limit
            expression_limit: Optional expression limit
        """
        if not primary_criteria or not primary_criteria.criteria_list:
            return "No primary criteria specified.\n"
        
        criteria_parts = []
        
        # Build opening sentence
        opening = "People"
        
        # Add observation window if present
        if primary_criteria.observation_window:
            obs_window = primary_criteria.observation_window
            prior_days = getattr(obs_window, 'prior_days', None) or getattr(obs_window, 'priorDays', None) or 0
            post_days = getattr(obs_window, 'post_days', None) or getattr(obs_window, 'postDays', None) or 0
            
            if prior_days > 0 or post_days > 0:
                opening += " with continuous observation of"
                if prior_days > 0:
                    opening += f" {prior_days} days before"
                    if post_days > 0:
                        opening += " and"
                if post_days > 0:
                    opening += f" {post_days} days after"
                opening += " event"
        
        # Add "may" if there are additional criteria or inclusion rules
        if (additional_criteria or (inclusion_rules and len(inclusion_rules) > 0)):
            opening += " may"
        
        opening += " enter the cohort when observing any of the following:"
        criteria_parts.append(opening)
        criteria_parts.append("")
        
        # Render each primary criteria
        for i, criteria in enumerate(primary_criteria.criteria_list, 1):
            criteria_parts.append(f"{i}. {self._render_criteria(criteria, level=0, is_plural=False)}")
            criteria_parts.append("")
        
        # Add primary limit if not "All"
        if primary_criteria.primary_limit and primary_criteria.primary_limit.type != "All":
            criteria_parts.append(f"\nLimit cohort entry events to the {self._format_result_limit(primary_criteria.primary_limit)} per person.")
            criteria_parts.append("")
        
        return "\n".join(criteria_parts)
    
    def _render_additional_criteria(self, primary_criteria: Optional[PrimaryCriteria],
                                   additional_criteria: CriteriaGroup,
                                   qualified_limit: Optional[ResultLimit]) -> str:
        """Render additional criteria section.
        
        Java equivalent: cohortExpression.ftl additional criteria section
        """
        if not additional_criteria:
            return ""
        
        criteria_parts = []
        
        # Get the group type
        group_type = self._format_group_type(additional_criteria.type or "ALL")
        criteria_parts.append(f"\nRestrict entry events to with {group_type} of the following criteria:")
        criteria_parts.append("")
        
        # Render each criteria as a numbered bullet with details
        if additional_criteria.criteria_list:
            for i, criteria in enumerate(additional_criteria.criteria_list, 1):
                # Render with full details, including occurrence and windows
                criteria_text = self._render_corelated_criteria_detail(criteria)
                if criteria_text:
                    criteria_parts.append(f"   {i}. {criteria_text}")
        
        criteria_parts.append("  ")
        criteria_parts.append("")
        
        # Add qualified limit if primary limit is "All"
        primary_limit = primary_criteria.primary_limit if primary_criteria else None
        if primary_limit and primary_limit.type == "All" and qualified_limit and qualified_limit.type != "All":
            criteria_parts.append(f"Limit these restricted entry events to the {self._format_result_limit(qualified_limit)} per person.")
            criteria_parts.append("")
        
        return "\n".join(criteria_parts)
    
    def _render_corelated_criteria_detail(self, corelated_criteria: Any) -> str:
        """Render detailed text for CorelatedCriteria including occurrence and windows.
        
        Args:
            corelated_criteria: CorelatedCriteria object
            
        Returns:
            Detailed criteria text like "having at least 1 drug exposure of 'X', starting between..."
        """
        from ..criteria import CorelatedCriteria, Occurrence
        
        if not isinstance(corelated_criteria, CorelatedCriteria):
            return self._render_criteria(corelated_criteria, level=0, is_plural=True)
        
        parts = []
        
        # Start with occurrence phrase
        occurrence = corelated_criteria.occurrence
        if occurrence:
            if occurrence.type == 0:  # EXACTLY
                if occurrence.count == 0:
                    parts.append("having no")
                else:
                    parts.append(f"having exactly {occurrence.count}")
            elif occurrence.type == 1:  # AT_MOST
                parts.append(f"having at most {occurrence.count}")
            elif occurrence.type == 2:  # AT_LEAST
                parts.append(f"having at least {occurrence.count}")
        else:
            parts.append("having")
        
        # Add the criteria description
        # Pluralize based on occurrence count: singular if count=1, plural otherwise
        inner_criteria = corelated_criteria.criteria
        should_pluralize = not (occurrence and occurrence.count == 1)
        criteria_text = self._render_criteria(inner_criteria, level=0, is_plural=should_pluralize)
        # Strip trailing period to avoid double periods when adding window details
        if criteria_text.endswith('.'):
            criteria_text = criteria_text[:-1]
        parts.append(criteria_text)
        
        # Add window details
        window_parts = []
        if corelated_criteria.start_window:
            window_text = self._format_window_criteria(corelated_criteria.start_window, "cohort entry")
            if window_text:
                window_parts.append(window_text)
        
        if corelated_criteria.end_window:
            window_text = self._format_window_criteria(corelated_criteria.end_window, "cohort entry")
            if window_text:
                window_parts.append(window_text)
        
        # Add final period at the end
        result = ", ".join([" ".join(parts)] + window_parts) + "."
        return result
    
    def _render_censor_criteria(self, censoring_criteria: List[Any]) -> str:
        """Render censor criteria section.
        
        Java equivalent: cohortExpression.ftl censor criteria section
        
        Args:
            censoring_criteria: List of criteria that cause exit from cohort
        """
        if not censoring_criteria:
            return ""
        
        criteria_parts = []
        # R always shows this line first
        criteria_parts.append("The person exits the cohort at the end of continuous observation.")
        criteria_parts.append("The person exits the cohort when encountering any of the following events:")
        criteria_parts.append("")
        
        for i, criteria in enumerate(censoring_criteria, 1):
            criteria_parts.append(f"{i}. {self._render_criteria(criteria, level=0, is_plural=False)}")
            criteria_parts.append("")
        
        return "\n".join(criteria_parts)
    
    def _render_cohort_eras(self, collapse_settings: CollapseSettings) -> str:
        """Render cohort eras section.
        
        Java equivalent: cohortExpression.ftl "Cohort Eras" section
        
        Args:
            collapse_settings: CollapseSettings object
        """
        # R shows cohort eras even when collapse_settings is None (defaults to era_pad=0)
        era_pad = 0
        if collapse_settings and collapse_settings.era_pad is not None:
            era_pad = collapse_settings.era_pad
        
        day_word = "day" if era_pad == 1 else "days"
        return f"Remaining events will be combined into cohort eras if they are within {era_pad} {day_word} of each other.\n"
    
    def _render_censor_window(self, censor_window: Period) -> str:
        """Render censor window with left/right censor messages.
        
        Java equivalent: cohortExpression.ftl censor window section
        """
        if not censor_window:
            return ""
        
        window_parts = []
        
        if censor_window.start_date:
            formatted_date = self._format_date(censor_window.start_date)
            window_parts.append(f"Left censor cohort start dates to {formatted_date}.")
        
        if censor_window.end_date:
            formatted_date = self._format_date(censor_window.end_date)
            window_parts.append(f"Right censor cohort end dates to {formatted_date}")
        
        return " ".join(window_parts) + "\n" if window_parts else ""
    
    def _render_criteria_group(self, criteria_group: CriteriaGroup, level: int = 0) -> str:
        """Render a criteria group.
        
        Java equivalent: criteriaTypes.ftl Group macro
        
        Args:
            criteria_group: CriteriaGroup object
            level: Indentation level for nested groups
        """
        if not criteria_group:
            return "No criteria group specified.\n"
        
        group_parts = []
        
        # Build group description
        group_type = self._format_group_type(criteria_group.type or "ALL")
        
        # Handle count if present
        if criteria_group.count is not None:
            count_str = f"{group_type} {criteria_group.count}"
        else:
            count_str = group_type
        
        # Build criteria list
        criteria_descriptions = []
        
        # Add demographic criteria
        if criteria_group.demographic_criteria_list:
            for demo in criteria_group.demographic_criteria_list:
                demo_str = self._render_demographic_criteria(demo)
                if demo_str and demo_str.strip():
                    criteria_descriptions.append(demo_str.strip())
        
        # Add regular criteria
        if criteria_group.criteria_list:
            for criteria in criteria_group.criteria_list:
                criteria_str = self._render_criteria(criteria, level=level + 1, is_plural=True)
                if criteria_str and criteria_str.strip():
                    criteria_descriptions.append(criteria_str.strip())
        
        # Add sub-groups
        if criteria_group.groups:
            for sub_group in criteria_group.groups:
                sub_str = self._render_criteria_group(sub_group, level=level + 1)
                if sub_str and sub_str.strip():
                    criteria_descriptions.append(sub_str.strip())
        
        # Build final description
        if criteria_descriptions:
            if len(criteria_descriptions) == 1:
                return f"{count_str}: {criteria_descriptions[0]}"
            else:
                return f"{count_str} of: {', '.join(criteria_descriptions)}"
        else:
            return count_str
    
    def _render_criteria(self, criteria: Criteria, level: int = 0, is_plural: bool = True, 
                        count_criteria: Optional[Dict] = None, index_label: str = "cohort entry") -> str:
        """Render individual criteria (dispatcher to domain-specific renderers).
        
        Java equivalent: criteriaTypes.ftl Criteria macro
        
        Args:
            criteria: Criteria object (or specific criteria type)
            level: Indentation level
            is_plural: Whether to use plural form
            count_criteria: Optional count criteria dict
            index_label: Label for index event
        """
        if not criteria:
            return "No criteria specified."
        
        # Dispatch to domain-specific renderers based on type
        if isinstance(criteria, ConditionOccurrence):
            return self._render_condition_occurrence(criteria, level, is_plural, count_criteria, index_label)
        elif isinstance(criteria, DrugExposure):
            return self._render_drug_exposure(criteria, level, is_plural, count_criteria, index_label)
        elif isinstance(criteria, ProcedureOccurrence):
            return self._render_procedure_occurrence(criteria, level, is_plural, count_criteria, index_label)
        elif isinstance(criteria, Death):
            return self._render_death(criteria, level, is_plural, count_criteria, index_label)
        elif isinstance(criteria, DeviceExposure):
            return self._render_device_exposure(criteria, level, is_plural, count_criteria, index_label)
        elif isinstance(criteria, Measurement):
            return self._render_measurement(criteria, level, is_plural, count_criteria, index_label)
        elif isinstance(criteria, Observation):
            return self._render_observation(criteria, level, is_plural, count_criteria, index_label)
        elif isinstance(criteria, Specimen):
            return self._render_specimen(criteria, level, is_plural, count_criteria, index_label)
        elif isinstance(criteria, VisitOccurrence):
            return self._render_visit_occurrence(criteria, level, is_plural, count_criteria, index_label)
        elif isinstance(criteria, VisitDetail):
            return self._render_visit_detail(criteria, level, is_plural, count_criteria, index_label)
        elif isinstance(criteria, ObservationPeriod):
            return self._render_observation_period(criteria, level, is_plural, count_criteria, index_label)
        elif isinstance(criteria, PayerPlanPeriod):
            return self._render_payer_plan_period(criteria, level, is_plural, count_criteria, index_label)
        elif isinstance(criteria, LocationRegion):
            return self._render_location_region(criteria, level, is_plural, count_criteria, index_label)
        elif isinstance(criteria, ConditionEra):
            return self._render_condition_era(criteria, level, is_plural, count_criteria, index_label)
        elif isinstance(criteria, DrugEra):
            return self._render_drug_era(criteria, level, is_plural, count_criteria, index_label)
        elif isinstance(criteria, DoseEra):
            return self._render_dose_era(criteria, level, is_plural, count_criteria, index_label)
        elif isinstance(criteria, GeoCriteria):
            return self._render_geo_criteria(criteria, level, is_plural, count_criteria, index_label)
        elif isinstance(criteria, CorelatedCriteria):
            # CorelatedCriteria wraps a Criteria object - render the inner criteria
            if criteria.criteria:
                return self._render_criteria(criteria.criteria, level, is_plural, count_criteria, index_label)
            else:
                return "No criteria specified in CorelatedCriteria."
        else:
            # Generic fallback
            return f"Unknown criteria type: {type(criteria).__name__}"
    
    def _render_demographic_criteria(self, demographic_criteria: DemographicCriteria) -> str:
        """Render demographic criteria."""
        if not demographic_criteria:
            return "No demographic criteria specified.\n"
        
        demo_parts = []
        
        # Age
        if demographic_criteria.age:
            demo_parts.append(f"**Age:** {self._render_numeric_range(demographic_criteria.age)}")
        
        # Gender
        if demographic_criteria.gender:
            demo_parts.append(f"**Gender:** {', '.join([str(g) for g in demographic_criteria.gender])}")
        
        # Race
        if demographic_criteria.race:
            demo_parts.append(f"**Race:** {', '.join([str(r) for r in demographic_criteria.race])}")
        
        # Ethnicity
        if demographic_criteria.ethnicity:
            demo_parts.append(f"**Ethnicity:** {', '.join([str(e) for e in demographic_criteria.ethnicity])}")
        
        # Occurrence dates
        if demographic_criteria.occurrence_start_date:
            demo_parts.append(f"**Occurrence Start Date:** {self._render_date_range(demographic_criteria.occurrence_start_date)}")
        
        if demographic_criteria.occurrence_end_date:
            demo_parts.append(f"**Occurrence End Date:** {self._render_date_range(demographic_criteria.occurrence_end_date)}")
        
        return "\n".join(demo_parts) + "\n" if demo_parts else "No demographic criteria specified.\n"
    
    def _render_inclusion_rules(self, inclusion_rules: List[InclusionRule]) -> str:
        """Render inclusion rules.
        
        Java equivalent: cohortExpression.ftl inclusion rules section
        """
        if not inclusion_rules:
            return "No inclusion rules specified.\n"
        
        rules_parts = []
        
        for i, rule in enumerate(inclusion_rules, 1):
            rule_name = rule.name or "Unnamed Rule"
            description = f": {rule.description}" if rule.description else ""
            
            rules_parts.append(f"#### {i}. {rule_name}{description}")
            rules_parts.append("")
            
            if rule.expression and rule.expression.criteria_list:
                # For inclusion rules, render CorelatedCriteria with detail
                from ..criteria import CorelatedCriteria
                for j, criteria in enumerate(rule.expression.criteria_list):
                    if isinstance(criteria, CorelatedCriteria):
                        criteria_text = self._render_corelated_criteria_detail(criteria)
                        rules_parts.append(f"Entry events {criteria_text}")
                    else:
                        criteria_text = self._render_criteria(criteria, level=0, is_plural=True)
                        rules_parts.append(f"Entry events {criteria_text}")
                rules_parts.append("")
        
        return "\n".join(rules_parts)
    
    def _render_end_strategy(self, end_strategy: Union[EndStrategy, DateOffsetStrategy, CustomEraStrategy]) -> str:
        """Render end strategy."""
        if not end_strategy:
            return "No end strategy specified.\n"
        
        strategy_parts = []
        
        if isinstance(end_strategy, EndStrategy) and not isinstance(end_strategy, (DateOffsetStrategy, CustomEraStrategy)):
            # Base EndStrategy (default exit)
            strategy_parts.append("The person exits the cohort at the end of continuous observation.")
        
        elif isinstance(end_strategy, DateOffsetStrategy):
            # DateOffsetStrategy uses 'offset' not 'date_offset'
            date_field_name = "end date" if end_strategy.date_field == "EndDate" else "start date"
            day_word = "day" if end_strategy.offset == 1 else "days"
            strategy_parts.append(f"The cohort end date will be offset from index event's {date_field_name} plus {end_strategy.offset} {day_word}.")
        
        elif isinstance(end_strategy, CustomEraStrategy):
            # CustomEraStrategy doesn't have drug_era_criteria field
            drug_name = self._get_concept_set_name(end_strategy.drug_codeset_id, "_invalid drug specified_")
            day_word1 = "day" if end_strategy.gap_days == 1 else "days"
            day_word2 = "day" if end_strategy.offset == 1 else "days"
            strategy_parts.append(f"The cohort end date will be based on a continuous exposure to {drug_name}:")
            strategy_parts.append(f"allowing {end_strategy.gap_days} {day_word1} between exposures, adding {end_strategy.offset} {day_word2} after exposure ends, and using days supply and exposure end date for exposure duration.")
        
        return "\n".join(strategy_parts) + "\n"
    
    def _render_collapse_settings(self, collapse_settings: CollapseSettings) -> str:
        """Render collapse settings."""
        if not collapse_settings:
            return "No collapse settings specified.\n"
        
        collapse_parts = []
        
        if collapse_settings.collapse_type:
            collapse_parts.append(f"**Collapse Type:** {collapse_settings.collapse_type}")
        
        if collapse_settings.era_pad:
            collapse_parts.append(f"**Era Pad:** {collapse_settings.era_pad}")
        
        return "\n".join(collapse_parts) + "\n"
    
    def _render_period(self, period: Period) -> str:
        """Render a period."""
        if not period:
            return "No period specified.\n"
        
        period_parts = []
        
        if period.start_date:
            period_parts.append(f"**Start Date:** {period.start_date}")
        
        if period.end_date:
            period_parts.append(f"**End Date:** {period.end_date}")
        
        return "\n".join(period_parts) + "\n"
    
    def _render_date_range(self, date_range: DateRange) -> str:
        """Render a date range."""
        if not date_range:
            return "No date range specified"
        
        range_parts = []
        
        if date_range.op:
            range_parts.append(f"Operation: {date_range.op}")
        
        if date_range.extent:
            range_parts.append(f"Extent: {date_range.extent}")
        
        if date_range.value:
            range_parts.append(f"Value: {date_range.value}")
        
        return ", ".join(range_parts) if range_parts else "No date range details"
    
    def _render_numeric_range(self, numeric_range: NumericRange) -> str:
        """Render a numeric range."""
        if not numeric_range:
            return "No numeric range specified"
        
        range_parts = []
        
        if numeric_range.op:
            range_parts.append(f"Operation: {numeric_range.op}")
        
        if numeric_range.value:
            range_parts.append(f"Value: {numeric_range.value}")
        
        if numeric_range.extent:
            range_parts.append(f"Extent: {numeric_range.extent}")
        
        return ", ".join(range_parts) if range_parts else "No numeric range details"
    
    def _render_date_adjustment(self, date_adjustment: DateAdjustment) -> str:
        """Render date adjustment.
        
        Java equivalent: inputTypes.DateAdjustment macro
        
        Args:
            date_adjustment: DateAdjustment object
            
        Returns:
            Formatted string like "starting 10 days after and ending 20 days after the event start date"
        """
        if not date_adjustment:
            return ""
        
        # Format start offset
        if date_adjustment.start_offset == 0:
            start_str = "on"
        else:
            abs_offset = abs(date_adjustment.start_offset)
            direction = "before" if date_adjustment.start_offset < 0 else "after"
            day_word = "day" if abs_offset == 1 else "days"
            start_str = f"{abs_offset} {day_word} {direction}"
        
        # Format end offset
        if date_adjustment.end_offset == 0:
            end_str = "on"
        else:
            abs_offset = abs(date_adjustment.end_offset)
            direction = "before" if date_adjustment.end_offset < 0 else "after"
            day_word = "day" if abs_offset == 1 else "days"
            end_str = f"{abs_offset} {day_word} {direction}"
        
        # Determine date parts
        start_with = date_adjustment.start_with or DateType.START_DATE
        end_with = date_adjustment.end_with or DateType.END_DATE
        
        start_date_part = "start date" if start_with == DateType.START_DATE else "end date"
        end_date_part = "start date" if end_with == DateType.START_DATE else "end date"
        
        # Build the full string
        if start_with != end_with:
            return f"starting {start_str} the event {start_date_part} and ending {end_str} the event {end_date_part}"
        else:
            return f"starting {start_str} and ending {end_str} the event {start_date_part}"
    
    def _render_concept_sets(self, concept_sets: List[ConceptSet]) -> str:
        """Render concept sets as markdown tables.
        
        Java equivalent: conceptSet.ftl template
        
        Args:
            concept_sets: List of ConceptSet objects
            
        Returns:
            Markdown formatted string with concept set tables
        """
        if not concept_sets:
            return "No concept sets specified.\n"
        
        concept_parts = []
        
        for concept_set in concept_sets:
            # Use concept set name as header
            name = concept_set.name if concept_set.name else "Unnamed Concept Set"
            concept_parts.append(f"### {name}")
            
            if concept_set.expression and concept_set.expression.items:
                # Render as markdown table
                concept_parts.append("|Concept ID|Concept Name|Code|Vocabulary|Excluded|Descendants|Mapped|")
                concept_parts.append("|:---|:---------------------------------------|:--|:-----|:--:|:--:|:--:|")
                
                for item in concept_set.expression.items:
                    if item.concept:
                        concept_id = item.concept.concept_id if hasattr(item.concept, 'concept_id') else ""
                        concept_name = item.concept.concept_name if hasattr(item.concept, 'concept_name') else ""
                        concept_code = item.concept.concept_code if hasattr(item.concept, 'concept_code') else ""
                        vocabulary_id = item.concept.vocabulary_id if hasattr(item.concept, 'vocabulary_id') else ""
                        
                        excluded = "YES" if item.is_excluded else "NO"
                        descendants = "YES" if item.include_descendants else "NO"
                        mapped = "YES" if item.include_mapped else "NO"
                        
                        concept_parts.append(f"|{concept_id}|{concept_name}|{concept_code}|{vocabulary_id}|{excluded}|{descendants}|{mapped}|")
                
                concept_parts.append("")
            else:
                # Empty concept set
                concept_parts.append("There are no concept set items in this concept set.")
                concept_parts.append("")
        
        return "\n".join(concept_parts)
    
    def _render_concept_set_expression(self, expression: ConceptSetExpression) -> str:
        """Render a concept set expression."""
        if not expression:
            return "No concept set expression specified.\n"
        
        expr_parts = []
        
        if expression.items:
            expr_parts.append("**Items:**")
            for item in expression.items:
                expr_parts.append(f"- {self._render_concept_set_item(item)}")
        
        return "\n".join(expr_parts) + "\n"
    
    def _render_concept_set_item(self, item: ConceptSetItem) -> str:
        """Render a concept set item (used in expression rendering).
        
        Args:
            item: ConceptSetItem object
            
        Returns:
            Formatted string describing the item
        """
        if not item:
            return "No concept set item specified"
        
        item_parts = []
        
        if item.concept:
            concept_id = item.concept.concept_id if hasattr(item.concept, 'concept_id') else ""
            concept_name = item.concept.concept_name if hasattr(item.concept, 'concept_name') else ""
            item_parts.append(f"Concept {concept_id}: {concept_name}")
        
        if item.is_excluded:
            item_parts.append("(Excluded)")
        
        if item.include_descendants:
            item_parts.append("(Include Descendants)")
        
        if item.include_mapped:
            item_parts.append("(Include Mapped)")
        
        return " ".join(item_parts) if item_parts else "No concept set item details"
    
    # ============================================================================
    # Domain-Specific Criteria Rendering Methods
    # ============================================================================
    
    def _build_criteria_attributes(self, criteria: Any, count_criteria: Optional[Dict] = None,
                                   index_label: str = "cohort entry") -> List[str]:
        """Build list of attribute strings for criteria rendering.
        
        Helper method to build attribute list like Java templates do.
        
        Args:
            criteria: Criteria object
            count_criteria: Optional count criteria dict
            index_label: Label for index event
            
        Returns:
            List of attribute strings
        """
        attrs = []
        
        # Window criteria (if count_criteria provided)
        if count_criteria and 'occurrence' in count_criteria:
            occurrence = count_criteria.get('occurrence')
            if occurrence:
                window_str = self._format_window_criteria(
                    count_criteria.get('window'),
                    index_label
                )
                if window_str:
                    attrs.append(window_str)
        
        # Age/Gender (common pattern)
        age = getattr(criteria, 'age', None)
        age_at_start = getattr(criteria, 'age_at_start', None)
        age_at_end = getattr(criteria, 'age_at_end', None)
        gender = getattr(criteria, 'gender', None)
        gender_cs = getattr(criteria, 'gender_cs', None)
        
        age_gender_str = self._format_age_gender(age or age_at_start, age_at_end, gender, gender_cs)
        if age_gender_str:
            attrs.append(age_gender_str)
        
        # Date adjustment
        date_adjustment = getattr(criteria, 'date_adjustment', None)
        if date_adjustment:
            adj_str = self._render_date_adjustment(date_adjustment)
            if adj_str:
                attrs.append(adj_str)
        
        # Event dates (occurrence start/end dates)
        occurrence_start_date = getattr(criteria, 'occurrence_start_date', None)
        occurrence_end_date = getattr(criteria, 'occurrence_end_date', None)
        era_start_date = getattr(criteria, 'era_start_date', None)
        era_end_date = getattr(criteria, 'era_end_date', None)
        
        start_date = occurrence_start_date or era_start_date
        end_date = occurrence_end_date or era_end_date
        
        if start_date or end_date:
            date_str = self._format_event_dates(start_date, end_date)
            if date_str:
                attrs.append(date_str)
        
        return attrs
    
    def _format_age_gender(self, age: Optional[NumericRange] = None,
                          age_at_end: Optional[NumericRange] = None,
                          gender: Optional[List[Concept]] = None,
                          gender_cs: Optional[ConceptSetSelection] = None) -> str:
        """Format age and gender criteria."""
        parts = []
        
        if age:
            age_str = self._format_numeric_range(age)
            if age_str:
                # R format: "who are >= X years old" instead of "age >= X"
                parts.append(f"who are {age_str} years old")
        
        if age_at_end:
            age_str = self._format_numeric_range(age_at_end)
            if age_str:
                parts.append(f"age at end {age_str}")
        
        if gender:
            gender_str = self._format_concept_list(gender)
            if gender_str:
                parts.append(f"gender: {gender_str}")
        
        if gender_cs:
            gender_str = self._format_concept_set_selection(gender_cs, "any gender")
            if gender_str:
                parts.append(f"gender concept {gender_str} concept set")
        
        return "; ".join(parts) if parts else ""
    
    def _format_event_dates(self, start_date: Optional[DateRange] = None,
                           end_date: Optional[DateRange] = None) -> str:
        """Format event date criteria."""
        parts = []
        
        if start_date:
            date_str = self._format_date_range(start_date)
            if date_str:
                parts.append(f"occurrence start date {date_str}")
        
        if end_date:
            date_str = self._format_date_range(end_date)
            if date_str:
                parts.append(f"occurrence end date {date_str}")
        
        return "; ".join(parts) if parts else ""
    
    def _render_condition_occurrence(self, criteria: ConditionOccurrence, level: int = 0,
                                     is_plural: bool = True, count_criteria: Optional[Dict] = None,
                                     index_label: str = "cohort entry") -> str:
        """Render ConditionOccurrence criteria.
        
        Java equivalent: criteriaTypes.ftl ConditionOccurrence macro
        """
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        # Domain-specific attributes
        if criteria.condition_type:
            exclude_str = "is not:" if getattr(criteria, 'condition_type_exclude', False) else "is:"
            concept_str = self._format_concept_list(criteria.condition_type)
            attrs.append(f"a condition type that {exclude_str} {concept_str}")
        
        if criteria.condition_type_cs:
            selection_str = self._format_concept_set_selection(criteria.condition_type_cs, "any condition")
            attrs.append(f"a condition type concept {selection_str} concept set")
        
        if criteria.stop_reason:
            stop_str = self._format_text_filter(criteria.stop_reason)
            attrs.append(f"with a stop reason {stop_str}")
        
        if criteria.provider_specialty:
            provider_str = self._format_concept_list(criteria.provider_specialty)
            attrs.append(f"a provider specialty that is: {provider_str}")
        
        if criteria.provider_specialty_cs:
            provider_str = self._format_concept_set_selection(criteria.provider_specialty_cs, "any specialty")
            attrs.append(f"a provider specialty concept {provider_str} concept set")
        
        if criteria.condition_status:
            status_str = self._format_concept_list(criteria.condition_status)
            attrs.append(f"a condition status that is: {status_str}")
        
        if criteria.condition_status_cs:
            status_str = self._format_concept_set_selection(criteria.condition_status_cs, "any status")
            attrs.append(f"a condition status concept {status_str} concept set")
        
        if criteria.visit_type:
            visit_str = self._format_concept_list(criteria.visit_type)
            attrs.append(f"a visit occurrence that is: {visit_str}")
        
        if criteria.visit_type_cs:
            visit_str = self._format_concept_set_selection(criteria.visit_type_cs, "any visit")
            attrs.append(f"a visit concept {visit_str} concept set")
        
        # Build main description
        codeset_name = self._get_concept_set_name(criteria.codeset_id, "any condition")
        plural = "s" if (is_plural and not criteria.first) else ""
        first_time = " for the first time in the person's history" if criteria.first else ""
        
        source_concept = ""
        if criteria.condition_source_concept:
            source_name = self._get_concept_set_name(criteria.condition_source_concept, "any condition")
            source_concept = f" (including {source_name} source concepts)"
        
        # Combine attributes
        attrs_str = f", {', '.join(attrs)}" if attrs else ""
        
        # Correlated criteria
        correlated = ""
        if criteria.correlated_criteria:
            correlated_label = self._get_concept_set_name(criteria.codeset_id, "any condition")
            correlated = f"; {self._render_criteria_group(criteria.correlated_criteria, level=level + 1)}"
        else:
            correlated = "."
        
        return f"condition occurrence{plural} of {codeset_name}{source_concept}{first_time}{attrs_str}{correlated}"
    
    def _render_drug_exposure(self, criteria: DrugExposure, level: int = 0,
                             is_plural: bool = True, count_criteria: Optional[Dict] = None,
                             index_label: str = "cohort entry") -> str:
        """Render DrugExposure criteria.
        
        Java equivalent: criteriaTypes.ftl DrugExposure macro
        """
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        # Domain-specific attributes
        if criteria.drug_type:
            exclude_str = "is not:" if getattr(criteria, 'drug_type_exclude', False) else "is:"
            drug_type_str = self._format_concept_list(criteria.drug_type)
            attrs.append(f"a drug type that {exclude_str} {drug_type_str}")
        
        if criteria.drug_type_cs:
            drug_type_str = self._format_concept_set_selection(criteria.drug_type_cs, "any drug")
            attrs.append(f"a drug type concept {drug_type_str} concept set")
        
        # Use getattr to maintain compatibility with Java fields that may not exist in Python model
        if getattr(criteria, 'refills', None):
            refills_str = self._format_numeric_range(getattr(criteria, 'refills'))
            attrs.append(f"with refills {refills_str}")
        
        if getattr(criteria, 'quantity', None):
            quantity_str = self._format_numeric_range(getattr(criteria, 'quantity'))
            attrs.append(f"with quantity {quantity_str}")
        
        if getattr(criteria, 'days_supply', None):
            days_str = self._format_numeric_range(getattr(criteria, 'days_supply'))
            attrs.append(f"with days supply {days_str} days")
        
        if getattr(criteria, 'effective_drug_dose', None):
            dose_str = self._format_numeric_range(getattr(criteria, 'effective_drug_dose'))
            attrs.append(f"with effective drug dose {dose_str}")
        
        if getattr(criteria, 'dose_unit', None):
            unit_str = self._format_concept_list(getattr(criteria, 'dose_unit'))
            attrs.append(f"dose unit: {unit_str}")
        
        if getattr(criteria, 'dose_unit_cs', None):
            unit_str = self._format_concept_set_selection(getattr(criteria, 'dose_unit_cs'), "any unit")
            attrs.append(f"a dose unit concept {unit_str} concept set")
        
        if getattr(criteria, 'route_concept', None):
            route_str = self._format_concept_list(getattr(criteria, 'route_concept'))
            attrs.append(f"with route: {route_str}")
        
        if getattr(criteria, 'route_concept_cs', None):
            route_str = self._format_concept_set_selection(getattr(criteria, 'route_concept_cs'), "any route")
            attrs.append(f"a route concept {route_str} concept set")
        
        if getattr(criteria, 'lot_number', None):
            lot_str = self._format_text_filter(getattr(criteria, 'lot_number'))
            attrs.append(f"lot number {lot_str}")
        
        if criteria.stop_reason:
            stop_str = self._format_text_filter(criteria.stop_reason)
            attrs.append(f"with a stop reason {stop_str}")
        
        if criteria.provider_specialty:
            provider_str = self._format_concept_list(criteria.provider_specialty)
            attrs.append(f"a provider specialty that is: {provider_str}")
        
        if criteria.provider_specialty_cs:
            provider_str = self._format_concept_set_selection(criteria.provider_specialty_cs, "any specialty")
            attrs.append(f"a provider specialty concept {provider_str} concept set")
        
        if criteria.visit_type:
            visit_str = self._format_concept_list(criteria.visit_type)
            attrs.append(f"a visit occurrence that is: {visit_str}")
        
        if criteria.visit_type_cs:
            visit_str = self._format_concept_set_selection(criteria.visit_type_cs, "any visit")
            attrs.append(f"a visit concept {visit_str} concept set")
        
        # Build main description
        codeset_name = self._get_concept_set_name(criteria.codeset_id, "any drug")
        plural = "s" if (is_plural and not criteria.first) else ""
        first_time = " for the first time in the person's history" if criteria.first else ""
        
        source_concept = ""
        if criteria.drug_source_concept:
            source_name = self._get_concept_set_name(criteria.drug_source_concept, "any drug")
            source_concept = f" (including {source_name} source concepts)"
        
        attrs_str = f", {', '.join(attrs)}" if attrs else ""
        
        correlated = ""
        if criteria.correlated_criteria:
            correlated_label = self._get_concept_set_name(criteria.codeset_id, "any drug")
            correlated = f"; {self._render_criteria_group(criteria.correlated_criteria, level=level + 1)}"
        else:
            correlated = "."
        
        return f"drug exposure{plural} of {codeset_name}{source_concept}{first_time}{attrs_str}{correlated}"
    
    def _render_procedure_occurrence(self, criteria: ProcedureOccurrence, level: int = 0,
                                   is_plural: bool = True, count_criteria: Optional[Dict] = None,
                                   index_label: str = "cohort entry") -> str:
        """Render ProcedureOccurrence criteria."""
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        # Domain-specific attributes (similar pattern to ConditionOccurrence)
        codeset_name = self._get_concept_set_name(criteria.codeset_id, "any procedure")
        plural = "s" if (is_plural and not criteria.first) else ""
        first_time = " for the first time in the person's history" if criteria.first else ""
        
        attrs_str = f", {', '.join(attrs)}" if attrs else ""
        
        correlated = ""
        if criteria.correlated_criteria:
            correlated = f"; {self._render_criteria_group(criteria.correlated_criteria, level=level + 1)}"
        else:
            correlated = "."
        
        return f"procedure occurrence{plural} of {codeset_name}{first_time}{attrs_str}{correlated}"
    
    def _render_death(self, criteria: Death, level: int = 0,
                     is_plural: bool = True, count_criteria: Optional[Dict] = None,
                     index_label: str = "cohort entry") -> str:
        """Render Death criteria."""
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        codeset_name = self._get_concept_set_name(criteria.codeset_id, "any form")
        source_concept = ""
        if criteria.death_source_concept:
            source_name = self._get_concept_set_name(criteria.death_source_concept, "any form")
            source_concept = f" (including {source_name} source concepts)"
        
        attrs_str = f", {', '.join(attrs)}" if attrs else ""
        
        correlated = ""
        if criteria.correlated_criteria:
            correlated = f"; {self._render_criteria_group(criteria.correlated_criteria, level=level + 1)}"
        else:
            correlated = "."
        
        return f"death of {codeset_name}{source_concept}{attrs_str}{correlated}"
    
    def _render_device_exposure(self, criteria: DeviceExposure, level: int = 0,
                              is_plural: bool = True, count_criteria: Optional[Dict] = None,
                              index_label: str = "cohort entry") -> str:
        """Render DeviceExposure criteria."""
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        codeset_name = self._get_concept_set_name(criteria.codeset_id, "any device")
        plural = "s" if (is_plural and not criteria.first) else ""
        first_time = " for the first time in the person's history" if criteria.first else ""
        
        attrs_str = f", {', '.join(attrs)}" if attrs else ""
        
        correlated = ""
        if criteria.correlated_criteria:
            correlated = f"; {self._render_criteria_group(criteria.correlated_criteria, level=level + 1)}"
        else:
            correlated = "."
        
        return f"device exposure{plural} of {codeset_name}{first_time}{attrs_str}{correlated}"
    
    def _render_measurement(self, criteria: Measurement, level: int = 0,
                           is_plural: bool = True, count_criteria: Optional[Dict] = None,
                           index_label: str = "cohort entry") -> str:
        """Render Measurement criteria."""
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        codeset_name = self._get_concept_set_name(criteria.codeset_id, "any measurement")
        plural = "s" if (is_plural and not criteria.first) else ""
        first_time = " for the first time in the person's history" if criteria.first else ""
        
        attrs_str = f", {', '.join(attrs)}" if attrs else ""
        
        correlated = ""
        if criteria.correlated_criteria:
            correlated = f"; {self._render_criteria_group(criteria.correlated_criteria, level=level + 1)}"
        else:
            correlated = "."
        
        return f"measurement{plural} of {codeset_name}{first_time}{attrs_str}{correlated}"
    
    def _render_observation(self, criteria: Observation, level: int = 0,
                           is_plural: bool = True, count_criteria: Optional[Dict] = None,
                           index_label: str = "cohort entry") -> str:
        """Render Observation criteria."""
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        codeset_name = self._get_concept_set_name(criteria.codeset_id, "any observation")
        plural = "s" if (is_plural and not criteria.first) else ""
        first_time = " for the first time in the person's history" if criteria.first else ""
        
        attrs_str = f", {', '.join(attrs)}" if attrs else ""
        
        correlated = ""
        if criteria.correlated_criteria:
            correlated = f"; {self._render_criteria_group(criteria.correlated_criteria, level=level + 1)}"
        else:
            correlated = "."
        
        return f"observation{plural} of {codeset_name}{first_time}{attrs_str}{correlated}"
    
    def _render_specimen(self, criteria: Specimen, level: int = 0,
                        is_plural: bool = True, count_criteria: Optional[Dict] = None,
                        index_label: str = "cohort entry") -> str:
        """Render Specimen criteria."""
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        codeset_name = self._get_concept_set_name(criteria.codeset_id, "any specimen")
        plural = "s" if (is_plural and not criteria.first) else ""
        first_time = " for the first time in the person's history" if criteria.first else ""
        
        attrs_str = f", {', '.join(attrs)}" if attrs else ""
        
        correlated = ""
        if criteria.correlated_criteria:
            correlated = f"; {self._render_criteria_group(criteria.correlated_criteria, level=level + 1)}"
        else:
            correlated = "."
        
        return f"specimen{plural} of {codeset_name}{first_time}{attrs_str}{correlated}"
    
    def _render_visit_occurrence(self, criteria: VisitOccurrence, level: int = 0,
                                is_plural: bool = True, count_criteria: Optional[Dict] = None,
                                index_label: str = "cohort entry") -> str:
        """Render VisitOccurrence criteria."""
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        codeset_name = self._get_concept_set_name(criteria.codeset_id, "any visit")
        plural = "s" if (is_plural and not criteria.first) else ""
        first_time = " for the first time in the person's history" if criteria.first else ""
        
        attrs_str = f", {', '.join(attrs)}" if attrs else ""
        
        correlated = ""
        if criteria.correlated_criteria:
            correlated = f"; {self._render_criteria_group(criteria.correlated_criteria, level=level + 1)}"
        else:
            correlated = "."
        
        return f"visit occurrence{plural} of {codeset_name}{first_time}{attrs_str}{correlated}"
    
    def _render_visit_detail(self, criteria: VisitDetail, level: int = 0,
                            is_plural: bool = True, count_criteria: Optional[Dict] = None,
                            index_label: str = "cohort entry") -> str:
        """Render VisitDetail criteria."""
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        codeset_name = self._get_concept_set_name(criteria.codeset_id, "any visit")
        plural = "s" if (is_plural and not criteria.first) else ""
        first_time = " for the first time in the person's history" if criteria.first else ""
        
        attrs_str = f", {', '.join(attrs)}" if attrs else ""
        
        correlated = ""
        if criteria.correlated_criteria:
            correlated = f"; {self._render_criteria_group(criteria.correlated_criteria, level=level + 1)}"
        else:
            correlated = "."
        
        return f"visit detail{plural} of {codeset_name}{first_time}{attrs_str}{correlated}"
    
    def _render_observation_period(self, criteria: ObservationPeriod, level: int = 0,
                                  is_plural: bool = True, count_criteria: Optional[Dict] = None,
                                  index_label: str = "cohort entry") -> str:
        """Render ObservationPeriod criteria."""
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        # Use getattr to maintain compatibility with Java fields that may not exist in Python model
        codeset_id = getattr(criteria, 'codeset_id', None)
        codeset_name = self._get_concept_set_name(codeset_id, "any observation period")
        attrs_str = f", {', '.join(attrs)}" if attrs else ""
        
        correlated = ""
        if getattr(criteria, 'correlated_criteria', None):
            correlated = f"; {self._render_criteria_group(getattr(criteria, 'correlated_criteria'), level=level + 1)}"
        else:
            correlated = "."
        
        return f"observation period of {codeset_name}{attrs_str}{correlated}"
    
    def _render_payer_plan_period(self, criteria: PayerPlanPeriod, level: int = 0,
                                  is_plural: bool = True, count_criteria: Optional[Dict] = None,
                                  index_label: str = "cohort entry") -> str:
        """Render PayerPlanPeriod criteria."""
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        # Use getattr to maintain compatibility with Java fields that may not exist in Python model
        codeset_id = getattr(criteria, 'codeset_id', None)
        codeset_name = self._get_concept_set_name(codeset_id, "any payer plan")
        attrs_str = f", {', '.join(attrs)}" if attrs else ""
        
        correlated = ""
        if getattr(criteria, 'correlated_criteria', None):
            correlated = f"; {self._render_criteria_group(getattr(criteria, 'correlated_criteria'), level=level + 1)}"
        else:
            correlated = "."
        
        return f"payer plan period of {codeset_name}{attrs_str}{correlated}"
    
    def _render_location_region(self, criteria: LocationRegion, level: int = 0,
                               is_plural: bool = True, count_criteria: Optional[Dict] = None,
                               index_label: str = "cohort entry") -> str:
        """Render LocationRegion criteria."""
        attrs = []
        
        # LocationRegion uses startDate/endDate instead of occurrence dates
        start_date = getattr(criteria, 'start_date', None)
        end_date = getattr(criteria, 'end_date', None)
        if start_date or end_date:
            date_str = self._format_event_dates(start_date, end_date)
            if date_str:
                attrs.append(date_str)
        
        codeset_name = self._get_concept_set_name(criteria.codeset_id, "any location")
        attrs_str = f", {', '.join(attrs)}" if attrs else ""
        
        correlated = ""
        if criteria.correlated_criteria:
            correlated = f"; {self._render_criteria_group(criteria.correlated_criteria, level=level + 1)}"
        else:
            correlated = "."
        
        return f"location of {codeset_name}{attrs_str}{correlated}"
    
    def _render_condition_era(self, criteria: ConditionEra, level: int = 0,
                              is_plural: bool = True, count_criteria: Optional[Dict] = None,
                              index_label: str = "cohort entry") -> str:
        """Render ConditionEra criteria."""
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        # Era-specific attributes
        if criteria.era_length:
            era_str = self._format_numeric_range(criteria.era_length)
            attrs.append(f"era length is {era_str} days")
        
        if criteria.occurrence_count:
            count_str = self._format_numeric_range(criteria.occurrence_count)
            attrs.append(f"containing {count_str} occurrences")
        
        codeset_name = self._get_concept_set_name(criteria.codeset_id, "any condition")
        plural = "s" if (is_plural and not criteria.first) else ""
        first_time = " for the first time in the person's history" if criteria.first else ""
        
        attrs_str = f", {', '.join(attrs)}" if attrs else ""
        
        correlated = ""
        if criteria.correlated_criteria:
            correlated = f"; {self._render_criteria_group(criteria.correlated_criteria, level=level + 1)}"
        else:
            correlated = "."
        
        return f"condition era{plural} of {codeset_name}{first_time}{attrs_str}{correlated}"
    
    def _render_drug_era(self, criteria: DrugEra, level: int = 0,
                        is_plural: bool = True, count_criteria: Optional[Dict] = None,
                        index_label: str = "cohort entry") -> str:
        """Render DrugEra criteria."""
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        # Era-specific attributes
        if criteria.era_length:
            era_str = self._format_numeric_range(criteria.era_length)
            attrs.append(f"with era length {era_str} days")
        
        if criteria.occurrence_count:
            count_str = self._format_numeric_range(criteria.occurrence_count)
            attrs.append(f"with occurrence count {count_str}")
        
        if criteria.gap_days:
            gap_str = self._format_numeric_range(criteria.gap_days)
            attrs.append(f"with gap days {gap_str}")
        
        codeset_name = self._get_concept_set_name(criteria.codeset_id, "any drug")
        plural = "s" if (is_plural and not criteria.first) else ""
        first_time = " for the first time in the person's history" if criteria.first else ""
        
        attrs_str = f", {', '.join(attrs)}" if attrs else ""
        
        correlated = ""
        if criteria.correlated_criteria:
            correlated = f"; {self._render_criteria_group(criteria.correlated_criteria, level=level + 1)}"
        else:
            correlated = "."
        
        return f"drug era{plural} of {codeset_name}{first_time}{attrs_str}{correlated}"
    
    def _render_dose_era(self, criteria: DoseEra, level: int = 0,
                        is_plural: bool = True, count_criteria: Optional[Dict] = None,
                        index_label: str = "cohort entry") -> str:
        """Render DoseEra criteria."""
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        # Era-specific attributes
        if criteria.unit:
            unit_str = self._format_concept_list(criteria.unit)
            attrs.append(f"unit is: {unit_str}")
        
        if criteria.unit_cs:
            unit_str = self._format_concept_set_selection(criteria.unit_cs, "any unit")
            attrs.append(f"a unit concept {unit_str} concept set")
        
        if criteria.era_length:
            era_str = self._format_numeric_range(criteria.era_length)
            attrs.append(f"with era length {era_str} days")
        
        if criteria.dose_value:
            dose_str = self._format_numeric_range(criteria.dose_value)
            attrs.append(f"with dose value {dose_str}")
        
        codeset_name = self._get_concept_set_name(criteria.codeset_id, "any drug")
        plural = "s" if (is_plural and not criteria.first) else ""
        first_time = " for the first time in the person's history" if criteria.first else ""
        
        attrs_str = f", {', '.join(attrs)}" if attrs else ""
        
        correlated = ""
        if criteria.correlated_criteria:
            correlated = f"; {self._render_criteria_group(criteria.correlated_criteria, level=level + 1)}"
        else:
            correlated = "."
        
        return f"dose era{plural} of {codeset_name}{first_time}{attrs_str}{correlated}"
    
    def _render_geo_criteria(self, criteria: GeoCriteria, level: int = 0,
                            is_plural: bool = True, count_criteria: Optional[Dict] = None,
                            index_label: str = "cohort entry") -> str:
        """Render GeoCriteria."""
        attrs = []
        
        # Use getattr to maintain compatibility with Java fields that may not exist in Python model
        codeset_id = getattr(criteria, 'codeset_id', None)
        codeset_name = self._get_concept_set_name(codeset_id, "any location")
        attrs_str = f", {', '.join(attrs)}" if attrs else ""
        
        correlated = ""
        if getattr(criteria, 'correlated_criteria', None):
            correlated = f"; {self._render_criteria_group(getattr(criteria, 'correlated_criteria'), level=level + 1)}"
        else:
            correlated = "."
        
        return f"geo criteria of {codeset_name}{attrs_str}{correlated}"

