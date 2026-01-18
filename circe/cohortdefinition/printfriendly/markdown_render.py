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
    DrugEra, DoseEra, GeoCriteria, Occurrence, CorelatedCriteria,
    PrimaryCriteria, CriteriaColumn
)
from ..core import (
    ResultLimit, Period, CollapseSettings, EndStrategy, DateOffsetStrategy,
    CustomEraStrategy, DateRange, NumericRange,
    ConceptSetSelection, CollapseType, DateType, TextFilter, Window, WindowBound,
    DateAdjustment, ObservationFilter, CirceBaseModel
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
        else:
            # Default end strategy when none is specified (continuous observation)
            markdown_parts.append("The person exits the cohort at the end of continuous observation.\n")
        
        # Censor criteria
        if cohort_expression.censoring_criteria:
            markdown_parts.append(self._render_censor_criteria(cohort_expression.censoring_criteria))
        
        # Cohort Eras - always show this section (R shows it even when collapse_settings is missing)
        markdown_parts.append("### Cohort Eras\n")
        markdown_parts.append(self._render_cohort_eras(cohort_expression.collapse_settings))
        
        # Censor window
        if cohort_expression.censor_window:
            markdown_parts.append(self._render_censor_window(cohort_expression.censor_window))
        
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
        if codeset_id is None:
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
                # Use %-d for non-zero-padded day on Unix, or manual lstrip
                day = dt.strftime("%d").lstrip("0")
                return f"{dt.strftime('%B')} {day}, {dt.strftime('%Y')}"
            return date_string
        except (ValueError, AttributeError):
            return "_invalid date_"

    def _format_number(self, value: Union[int, float]) -> str:
        """Format number with thousands separators and handle integer/float logic.
        
        Args:
            value: Number to format
            
        Returns:
            Formatted string (e.g. "1,500" or "1.5")
        """
        if value is None:
            return ""
            
        # If matches integer, convert to int for clean formatting
        if isinstance(value, float) and value.is_integer():
            value = int(value)
            
        return f"{value:,}"
    
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
            "lte": "&le;",
            "eq": "=",
            "gt": "&gt;",
            "gte": "&ge;",
            "bt": "between",
            "!bt": "not between"
        }
        
        op_name = op_map.get(numeric_range.op, numeric_range.op)
        
        if numeric_range.op.endswith("bt") and numeric_range.value is not None and numeric_range.extent is not None:
            return f"{op_name} {self._format_number(numeric_range.value)} and {self._format_number(numeric_range.extent)}"
        elif numeric_range.value is not None:
            return f"{op_name} {self._format_number(numeric_range.value)}"
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
        
        quoted = [f'{quote}{c.concept_name.lower().replace("<=", "&le;").replace(">=", "&ge;").replace("<", "&lt;").replace(">", "&gt;")}{quote}' for c in concepts if c and c.concept_name]
        
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
            # Handle None values: use "all" for None when going backwards (coeff=-1), 0 otherwise
            start_coeff = start.coeff if start else 1
            end_coeff = end.coeff if end else 1
            
            if start.days is None:
                start_days = "all" if start_coeff == -1 else 0
            else:
                start_days = start.days
            
            if end.days is None:
                end_days = "all" if end_coeff == 1 else 0
            else:
                end_days = end.days
            
            start_dir = "before" if start_coeff < 0 else "after"
            end_dir = "before" if end_coeff < 0 else "after"
            
            end_dir = "before" if end_coeff < 0 else "after"
            
            # # Special case: "in the X days prior to" (Java Window macro)
            ## IS THIS AN HALUNICATION?
            # # If both coefficients are -1 (before) and start > end
            # if isinstance(start_days, int) and isinstance(end_days, int) and start_coeff == -1 and end_coeff == -1 and start_days > end_days:
            #      return f"{event_part} in the {start_days} days prior to {index_label} {index_part}"
            
            # Special case: both in the past (coeff=-1, end_days < start_days)
            # if start_coeff == -1 and end_coeff == -1 and isinstance(start_days, int) and isinstance(end_days, int) and end_days < start_days:
            #    return f"{event_part} in the {start_days} days prior to {index_label} {index_part}"
            
            # Special case: suppression of default "all days" window
            if start_days == "all" and end_days == "all":
                return ""

            # Special case: "anytime prior to" when start is all and end is 1 day before
            if start_days == "all" and end_days == 1 and start_coeff == -1 and end_coeff == -1:
                return f"{event_part} anytime prior to {index_label} {index_part}"
            # Special case: "anytime on or before" when start is all and end is 0
            elif start_days == "all" and end_days == 0 and start_coeff == -1 and end_coeff == -1:
                return f"{event_part} anytime on or before {index_label} {index_part}"
            elif end_days == "all" and isinstance(start_days, int) and start_days > 0 and start_coeff == 1 and end_coeff == 1:
                # Java says "starting 1 days after" for [1 after, all after]
                return f"{event_part}  {start_days} days {start_dir} {index_label} {index_part}"
            elif start_days == "all" and isinstance(end_days, int) and end_days > 0 and start_coeff == -1 and end_coeff == -1:
                # Java says "anytime up to X days before"
                return f"{event_part} anytime up to {end_days} days {end_dir} {index_label} {index_part}"
            elif start_days == "all" and isinstance(end_days, int) and end_days > 0 and start_coeff == -1 and end_coeff == 1:
                # Java says "anytime up to X days after"
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
    
    def _format_group_type(self, group_type: str, count: Optional[int] = None) -> str:
        """Format group type.
        
        Java equivalent: groupTypeOptions
        
        Args:
            group_type: Group type string (ALL, ANY, AT_LEAST, AT_MOST)
            count: Optional count for AT_LEAST, AT_MOST
            
        Returns:
            Formatted string like "all", "any", "at least 1", "at most 1"
        """
        type_map = {
            "ALL": "all",
            "ANY": "any",
            "AT_LEAST": "at least",
            "AT_MOST": "at most"
        }
        
        type_name = type_map.get(group_type, group_type.lower() if group_type else "")
        if count is not None and group_type in ("AT_LEAST", "AT_MOST"):
            return f"{type_name} {count}"
        return type_name
    
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
            criteria_parts.append(f"{i}. {self._render_criteria(criteria, level=0, is_plural=True)}")
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
        
        # Check if single item (no groups, 1 criteria)
        is_single_item = (additional_criteria.criteria_list and len(additional_criteria.criteria_list) == 1 and 
                          (not additional_criteria.groups or len(additional_criteria.groups) == 0))
        
        if is_single_item:
            criteria = additional_criteria.criteria_list[0]
            criteria_text = self._render_corelated_criteria_detail(criteria, index_label="cohort entry")
            criteria_parts.append(f"\nRestrict entry events to {criteria_text}.")
            criteria_parts.append("")
        else:
            # Get the group type
            group_type = self._format_group_type(additional_criteria.type or "ALL", additional_criteria.count)
            criteria_parts.append(f"\nRestrict entry events to with {group_type} of the following criteria:")
            criteria_parts.append("")
            
            # Render each criteria as a numbered bullet with details
            if additional_criteria.criteria_list:
                for i, criteria in enumerate(additional_criteria.criteria_list, 1):
                    # Render with full details, including occurrence and windows
                    criteria_text = self._render_corelated_criteria_detail(criteria, index_label="cohort entry")
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
    
    def _render_corelated_criteria_detail(self, corelated_criteria: Any, index_label: str = "cohort entry") -> str:
        """Render detailed text for CorelatedCriteria including occurrence and windows.
        
        Args:
            corelated_criteria: CorelatedCriteria object
            index_label: The event name used as reference for timing (default: "cohort entry")
            
        Returns:
            Detailed criteria text like "having at least 1 drug exposure of 'X', starting between..."
        """
        from ..criteria import CorelatedCriteria, Occurrence, Measurement
        
        if not isinstance(corelated_criteria, CorelatedCriteria):
            return self._render_criteria(corelated_criteria, level=0, is_plural=True, index_label=index_label)
        
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
            
            # Handle distinct counts
            if getattr(occurrence, 'is_distinct', False):
                count_col = getattr(occurrence, 'count_column', None)
                if count_col == CriteriaColumn.DOMAIN_CONCEPT:
                    parts.append("distinct standard concepts from")
                elif count_col == CriteriaColumn.START_DATE:
                    parts.append("distinct start dates of")
        else:
            parts.append("having")
        
        # Add the criteria description
        # Pluralize based on occurrence count: singular if count=1, plural otherwise
        inner_criteria = corelated_criteria.criteria
        should_pluralize = not (occurrence and occurrence.count == 1)
        criteria_text = self._render_criteria(inner_criteria, level=0, is_plural=should_pluralize, index_label=index_label)
        # Strip trailing period to avoid double periods when adding window details
        if criteria_text.endswith('.'):
            criteria_text = criteria_text[:-1]
        
        # Determine separator for final parts
        # If there are NO windows and NO observation flag, and NO domain attributes, it ends here.
        # But usually we call this when we HAVE something to add.
        
        # Extract domain-specific attributes to append after window
        domain_attrs = []
        from ..criteria import Measurement, ProcedureOccurrence, ConditionOccurrence
        
        # Look for attribute patterns: ", key: value" or ", with key: value" or " (including ...)"
        import re
        attribute_patterns = [
            (r'[,;]\s*(numeric value [^;]+?)(?=[,;]\s*(?:unit:|operator:|value as string|low range|high range|starting|ending)|$)', 'numeric value'),
            (r'[,;]\s*(unit: [^;]+(?:,\s*"[^"]*")*(?:\s+or\s+"[^"]*")?)(?=[,;]\s*(?:numeric value|operator:|value as string|low range|high range|a measurement|an operator|a unit|starting|ending)|$)', 'unit'),
            (r'[,;]\s*(operator: [^;]+?)(?=[,;]\s*(?:unit:|numeric value|value as string|value as concept|low range|high range|starting|ending)|$)', 'operator'),
            (r'[,;]\s*(value as string [^;]+?)(?=[,;]\s*(?:unit:|operator:|numeric value|value as concept|low range|high range|starting|ending)|$)', 'value as string'),
            (r'[,;]\s*(with value as concept: .*?)(?=[,;]\s*(?:unit:|operator:|numeric value|value as string|low range|high range|starting|ending)|$)', 'value as concept'),
            (r'[,;]\s*(a value as concept [^;]+? concept set)(?=[,;]\s*(?:unit:|operator:|numeric value|value as string|with value as concept:|low range|high range|starting|ending)|$)', 'value as concept set'),
            (r'[,;]\s*(low range [^;]+?)(?=[,;]\s*(?:unit:|operator:|value as string|numeric value|high range|starting|ending)|$)', 'low range'),
            (r'[,;]\s*(high range [^;]+?)(?=[,;]\s*(?:unit:|operator:|value as string|low range|numeric value|starting|ending)|$)', 'high range'),
            (r'[,;]\s*(a measurement type [^;]+?)(?=[,;]\s*(?:unit:|operator:|starting|ending)|$)', 'measurement type'),
            (r'[,;]\s*(an operator concept [^;]+?)(?=[,;]\s*(?:unit:|starting|ending)|$)', 'operator concept'),
            (r'[,;]\s*(a unit concept [^;]+?)(?=[,;]\s*(?:starting|ending)|$)', 'unit concept'),
            # Modifiers and status usually come last in Java/R
            (r'[,;]\s*(with modifier: [^;]+?)(?=[,;]\s*(?:starting|ending)|$)', 'modifier'),
            (r'[,;]\s*(a modifier concept [^;]+?)(?=[,;]\s*(?:starting|ending)|$)', 'modifier concept'),
            (r'[,;]\s*(with a condition status: [^;]+?)(?=[,;]\s*(?:starting|ending)|$)', 'condition status'),
            (r'\s*(with a condition status: [^;]+?)(?=[,;]\s*(?:starting|ending)|$)', 'condition status')  # Sometimes no comma
        ]
        
        # Protect nested group phrases from attribute stripping
        nested_group_pattern = r'(;\s*(?:with .+? of the following criteria:|having .+?)\s*.*)'
        match = re.search(nested_group_pattern, criteria_text)
        nested_part = ""
        
        if match:
             nested_part = criteria_text[match.start():]
             criteria_text = criteria_text[:match.start()]

        for pattern, desc in attribute_patterns:
            matches = list(re.finditer(pattern, criteria_text))
            for match in matches:
                domain_attrs.append(match.group(1).lstrip(', ').lstrip())
            criteria_text = re.sub(pattern, '', criteria_text)
        
        # Restore nested part
        criteria_text += nested_part
        
        parts.append(criteria_text)
        
        # Add window details
        window_parts = []
        if corelated_criteria.start_window:
            window_text = self._format_window_criteria(corelated_criteria.start_window, index_label)
            if window_text:
                window_parts.append(window_text)
        
        if corelated_criteria.end_window:
            window_text = self._format_window_criteria(corelated_criteria.end_window, index_label)
            if window_text:
                window_parts.append(window_text)
        
        if domain_attrs:
            # Re-add attributes that were stripped
            pass
            
        # Add ignore observation period flag
        obs_flag = ""
        if getattr(corelated_criteria, 'ignore_observation_period', False):
            obs_flag = "; allow events outside observation period"

        # Build final string in order: Description -> Window -> Obs Flag -> Attributes
        joined_parts = " ".join(parts)
        # Verify if description is multiline
        is_multiline = "\n" in joined_parts
        
        description_text = joined_parts
        window_text = ""
        if window_parts:
            window_text = ", " + " and ".join(window_parts)
            
        attr_text = ""
        if domain_attrs:
            # Attributes are usually semicolon separated if they follow window/flag
            attr_text = "; " + "; ".join(domain_attrs)

        if is_multiline:
            lines = description_text.split("\n")
            first_line = lines[0]
            rest = "\n".join(lines[1:])
            
            # Check if first_line contains a nested group phrase (plural or single item optimization)
            nested_group_pattern = r'(;\s*(?:with .+? of the following criteria:|having .+?)\s*.*)'
            match = re.search(nested_group_pattern, first_line)
            
            if match:
                main_desc = first_line[:match.start()]
                group_phrase = first_line[match.start():]
                # Strip trailing period from main_desc if present, to avoid ".," before window
                if main_desc.endswith('.'):
                    main_desc = main_desc[:-1]
                
                # Check if group phrase starts with semicolon, we want comma before window
                # logic: main_desc + window + group_phrase
                # group_phrase starts with "; ..."
                # result: "Description, window; nested..."
                
                result = []
                result.append(main_desc)
                if window_parts:
                    result.append(window_text)
                
                # We need to construct string carefully.
                # main_desc might have been stripped of attributes already.
                
                # If window exists, we want: "Desc, window; nested"
                # If obs_flag exists: "Desc, window, obs_flag; nested"
                
                # Direct concatenation as window_text and obs_flag already have separators
                attr_str = ""
                if domain_attrs:
                     attr_str = "; " + "; ".join(domain_attrs)
                
                middle_str = f"{window_text}{obs_flag}{attr_str}"
                
                return f"{main_desc}{middle_str}{group_phrase}\n{rest}"
            else:
                # Insert window/flag/attributes into first line end
                return f"{first_line}{window_text}{obs_flag}{attr_text}\n{rest}"
        else:
            # Check if description contains a nested group phrase
            nested_group_pattern = r'(;\s*(?:with .+? of the following criteria:|having .+?)\s*.*)'
            match = re.search(nested_group_pattern, description_text)
            
            if match:
                 # Split at the group phrase
                main_desc = description_text[:match.start()]
                group_phrase = description_text[match.start():]
                # Insert window/flag/attributes BEFORE the group phrase
                return f"{main_desc}{window_text}{obs_flag}{attr_text}{group_phrase}"
            else:
                return f"{description_text}{window_text}{obs_flag}{attr_text}."
    
    def _render_censor_criteria(self, censoring_criteria: List[Any]) -> str:
        """Render censor criteria section.
        
        Java equivalent: cohortExpression.ftl censor criteria section
        
        Args:
            censoring_criteria: List of criteria that cause exit from cohort
        """
        if not censoring_criteria:
            return ""
        
        criteria_parts = []
        criteria_parts.append("The person exits the cohort when encountering any of the following events:")
        criteria_parts.append("")
        
        for i, criteria in enumerate(censoring_criteria, 1):
            criteria_parts.append(f"{i}. {self._render_criteria(criteria, level=0, is_plural=True)}")
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
        
        # R always uses plural 'days' regardless of count
        day_word = "days" # "day" if era_pad == 1 else "days"
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
    
    def _render_criteria_group(self, criteria_group: CriteriaGroup, level: int = 0, index_label: str = "cohort entry") -> str:
        """Render a criteria group with proper multiline support and indentation.
        
        Java equivalent: criteriaTypes.ftl Group macro
        """
        if not criteria_group:
            return "No criteria group specified"
        
        # Build group description phrase
        count_str = self._format_group_type(criteria_group.type or "ALL", criteria_group.count)
        phrase = f"with {count_str} of the following criteria:"
        
        # Collect items
        items = []
        
        # Demographic
        for demo in (criteria_group.demographic_criteria_list or []):
            items.append(self._render_demographic_criteria(demo) + ".")
            
        # Regular criteria
        for criteria in (criteria_group.criteria_list or []):
            from ..criteria import CorelatedCriteria
            if isinstance(criteria, CorelatedCriteria):
                item = self._render_corelated_criteria_detail(criteria, index_label=index_label)
            else:
                item = self._render_criteria(criteria, is_plural=True, index_label=index_label)
            
            if item:
                item = item.strip()
                if not item.endswith('.'):
                    item += "."
            items.append(item)
                
        # Subgroups
        for sub_group in (criteria_group.groups or []):
            rendered_sub = self._render_criteria_group(sub_group, level=level + 1, index_label=index_label)
            if rendered_sub:
                items.append(rendered_sub)
            
        if not items:
            return f"{phrase} [none]"
            
        if len(items) == 1 and not criteria_group.groups:
            # Optimization: If only 1 item, render directly without header
            return items[0]
            
        # Multiline format
        indent = "   " * (level + 1)
        formatted_items = []
        for i, item in enumerate(items, 1):
            if "\n" in item:
                # Indent nested multiline items
                nested_indent = "   "
                indented_item = item.replace("\n", "\n" + nested_indent)
                formatted_items.append(f"{indent}{i}. {indented_item}")
            else:
                formatted_items.append(f"{indent}{i}. {item}")
                
        return f"{phrase}\n\n" + "\n".join(formatted_items) + "\n"
    
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
        elif isinstance(criteria, CriteriaGroup):
            # Special case for CriteriaGroup as individual criteria
            return self._render_criteria_group(criteria, level=level, index_label=index_label)
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
        """Render demographic criteria in natural language.
        
        Java equivalent: criteriaTypes.ftl DemographicCriteria macro
        """
        if not demographic_criteria:
            return "No demographic criteria specified"
        
        demo_parts = []
        
        # Age
        if demographic_criteria.age:
            age_range = self._format_numeric_range(demographic_criteria.age)
            demo_parts.append(f"who are {age_range} years old")
        
        # Gender
        if demographic_criteria.gender:
            gender_list = self._format_concept_list(demographic_criteria.gender, quote="")
            demo_parts.append(f"who are {gender_list}")
        
        # Race
        if demographic_criteria.race:
            race_list = self._format_concept_list(demographic_criteria.race, quote="")
            demo_parts.append(f"who are {race_list}")
        
        # Ethnicity
        if demographic_criteria.ethnicity:
            ethnicity_list = self._format_concept_list(demographic_criteria.ethnicity, quote="")
            demo_parts.append(f"who are {ethnicity_list}")
        
        # Occurrence dates
        if demographic_criteria.occurrence_start_date:
            start_range = self._format_date_range(demographic_criteria.occurrence_start_date)
            demo_parts.append(f"with occurrence start date {start_range}")
        
        if demographic_criteria.occurrence_end_date:
            end_range = self._format_date_range(demographic_criteria.occurrence_end_date)
            demo_parts.append(f"with occurrence end date {end_range}")
        
        return ", ".join(demo_parts) if demo_parts else "No demographic criteria specified"
    
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
            
            if rule.expression:
                # Java uses a specific framing for inclusion rules
                # The expression is a CriteriaGroup
                group = rule.expression
                
                # Check for demographic only rules or simple rules
                has_demographic = bool(group.demographic_criteria_list)
                has_criteria = bool(group.criteria_list)
                has_groups = bool(group.groups)
                
                total_items = (len(group.demographic_criteria_list or []) + 
                               len(group.criteria_list or []) + 
                               len(group.groups or []))
                
                if total_items == 0:
                    rules_parts.append("Entry events without any additional criteria.")
                elif total_items == 1:
                    if has_demographic:
                        demo_str = self._render_demographic_criteria(group.demographic_criteria_list[0])
                        rules_parts.append(f"Entry events with the following event criteria: {demo_str}.")
                    elif has_criteria:
                        from ..criteria import CorelatedCriteria
                        criteria = group.criteria_list[0]
                        # For inclusion rules, we default to "cohort entry" as index
                        index_label = "cohort entry"
                        if isinstance(criteria, CorelatedCriteria):
                            criteria_text = self._render_corelated_criteria_detail(criteria, index_label=index_label)
                            if criteria_text:
                                criteria_text = criteria_text.rstrip()
                                if not criteria_text.endswith('.'):
                                    criteria_text += "."
                            rules_parts.append(f"Entry events {criteria_text}")
                        else:
                            criteria_text = self._render_criteria(criteria, is_plural=True, index_label=index_label)
                            if criteria_text:
                                criteria_text = criteria_text.rstrip()
                                if not criteria_text.endswith('.'):
                                    criteria_text += "."
                            rules_parts.append(f"Entry events {criteria_text}")
                    elif has_groups:
                        group_str = self._render_criteria_group(group.groups[0], level=0, index_label="cohort entry")
                        rules_parts.append(f"Entry events {group_str}")
                else:
                    # Multi-item group
                    group_type_str = self._format_group_type(group.type or "ALL", group.count)
                    rules_parts.append(f"Entry events with {group_type_str} of the following criteria:")
                    rules_parts.append("")
                    
                    item_idx = 1
                    # Render demographic criteria
                    for demo in (group.demographic_criteria_list or []):
                        demo_str = self._render_demographic_criteria(demo)
                        rules_parts.append(f"   {item_idx}. {demo_str}.")
                        item_idx += 1
                        
                    # Render criteria
                    for criteria in (group.criteria_list or []):
                        from ..criteria import CorelatedCriteria
                        if isinstance(criteria, CorelatedCriteria):
                            criteria_text = self._render_corelated_criteria_detail(criteria, index_label="cohort entry")
                        else:
                            criteria_text = self._render_criteria(criteria, is_plural=True, index_label="cohort entry")
                        if criteria_text and not criteria_text.strip().endswith('.'):
                            criteria_text = criteria_text.strip() + "."
                        rules_parts.append(f"   {item_idx}. {criteria_text}")
                        item_idx += 1
                        
                    # Render groups
                    for sub_group in (group.groups or []):
                        group_str = self._render_criteria_group(sub_group, level=1, index_label="cohort entry")
                        rules_parts.append(f"   {item_idx}. {group_str}")
                        item_idx += 1
                        
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
        
        result_parts = []
        if period.start_date:
            result_parts.append(f"a user defiend start date of {self._format_date(period.start_date)}")
            
        if period.end_date:
            result_parts.append(f"end date of {self._format_date(period.end_date)}")
            
        if not result_parts:
             return ""
             
        return " and ".join(result_parts)
    
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
        """Format age and gender criteria.
        
        Java equivalent: InputTypes.ftl (ageGender macro)
        """
        parts = []
        
        gender_text = ""
        if gender:
            gender_text = self._format_concept_list(gender, quote="")
        elif gender_cs:
            gender_text = self._format_concept_set_selection(gender_cs, "any gender")
            if gender_text.startswith("in "):
                 gender_text = "gender " + gender_text

        if gender_text:
            parts.append(gender_text)
            
        age_text = ""
        if age:
            age_str = self._format_numeric_range(age)
            if age_at_end:
                 age_text = f"{age_str} years old at era start"
            else:
                 age_text = f"{age_str} years old"
                 
        if age_text:
            if gender_text:
                 # Check for comma or " or " to determine separator
                 if "," in gender_text or " or " in gender_text:
                     parts.append(f", {age_text}")
                 else:
                     parts.append(f" {age_text}")
            else:
                 parts.append(age_text)
                 
        if age_at_end:
            age_end_str = self._format_numeric_range(age_at_end)
            attrs_text = f"{age_end_str} years old at era end"
            if age_text:
                # If we had start age, join with " and " (no parts append needed if we modify last part?
                # Actually parts is list of strings.
                # Let's rebuild for simplicity.
                pass
                
        # Simpler reconstruction to avoid parts confusion
        result = ""
        
        # 1. Gender
        if gender_text:
            result = gender_text
            
        # 2. Age (Start)
        if age_text:
            if result:
                 if "," in result or " or " in result:
                     result += f", {age_text}"
                 else:
                     result += f" {age_text}"
            else:
                result = age_text
                
        # 3. Age (End)
        if age_at_end:
            age_end_str = self._format_numeric_range(age_at_end)
            end_text = f"{age_end_str} years old at era end"
            if result:
                result += f" and {end_text}"
            else:
                result = end_text
                
        if not result:
            return ""
            
        return f"who are {result}"
    
    def _format_event_dates(self, start_date: Optional[DateRange] = None,
                           end_date: Optional[DateRange] = None) -> str:
        """Format event date criteria."""
        parts = []
        
        if start_date:
            date_str = self._format_date_range(start_date)
            if date_str:
                parts.append(f"starting {date_str}")
        
        if end_date:
            date_str = self._format_date_range(end_date)
            if date_str:
                parts.append(f"ending {date_str}")
        
        return " and ".join(parts) if parts else ""
    
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
        
        if criteria.provider_specialty is not None:
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
        
        if criteria.visit_type is not None:
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
        if criteria.condition_source_concept is not None:
            source_name = self._get_concept_set_name(criteria.condition_source_concept, "any condition")
            source_concept = f" (including {source_name} source concepts)"
        
        if criteria.condition_status:
            status_str = self._format_concept_list(criteria.condition_status)
            attrs.append(f"with a condition status: {status_str}")
            
        if criteria.condition_status_cs:
            status_str = self._format_concept_set_selection(criteria.condition_status_cs, "any status")
            attrs.append(f"a condition status concept {status_str} concept set")
            
        if criteria.stop_reason:
            stop_str = self._format_text_filter(criteria.stop_reason)
            attrs.append(f"with a stop reason: {stop_str}")
            
        # Combine attributes
        attrs_str = f", {'; '.join(attrs)}" if attrs else ""
        
        # Main criteria description
        description = f"condition occurrence{plural} of {codeset_name}{source_concept}{first_time}{attrs_str}"
        
        # Correlated criteria
        if criteria.correlated_criteria:
            correlated_text = self._render_criteria_group(criteria.correlated_criteria, level=level, index_label=codeset_name)
            return f"{description}; {correlated_text}"
        else:
            return f"{description}."
    
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
        if criteria.drug_source_concept is not None:
            source_name = self._get_concept_set_name(criteria.drug_source_concept, "any drug")
            source_concept = f" (including {source_name} source concepts)"
        
        if getattr(criteria, 'effective_drug_dose', None):
            dose_str = self._format_numeric_range(criteria.effective_drug_dose)
            attrs.append(f"with effective drug dose {dose_str}")
        
        attrs_str = f", {'; '.join(attrs)}" if attrs else ""
        
        # Main description
        description = f"drug exposure{plural} of {codeset_name}{source_concept}{first_time}{attrs_str}"
        
        # Correlated criteria
        if criteria.correlated_criteria:
            # Use same level for the group header
            correlated_text = self._render_criteria_group(criteria.correlated_criteria, level=level, index_label=codeset_name)
            return f"{description}; {correlated_text}"
        else:
            return f"{description}."
    
    def _render_procedure_occurrence(self, criteria: ProcedureOccurrence, level: int = 0,
                                   is_plural: bool = True, count_criteria: Optional[Dict] = None,
                                   index_label: str = "cohort entry") -> str:
        """Render ProcedureOccurrence criteria."""
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        # Domain-specific attributes
        if criteria.procedure_type:
            exclude_str = "is not:" if getattr(criteria, 'procedure_type_exclude', False) else "is:"
            type_str = self._format_concept_list(criteria.procedure_type)
            attrs.append(f"a procedure type that {exclude_str} {type_str}")
            
        if criteria.procedure_type_cs:
            type_str = self._format_concept_set_selection(criteria.procedure_type_cs, "any procedure")
            attrs.append(f"a procedure type concept {type_str} concept set")
            
        if criteria.modifier:
            modifier_str = self._format_concept_list(criteria.modifier)
            attrs.append(f"with modifier: {modifier_str}")
            
        if criteria.modifier_cs:
            modifier_str = self._format_concept_set_selection(criteria.modifier_cs, "any modifier")
            attrs.append(f"a modifier concept {modifier_str} concept set")
            
        if getattr(criteria, 'quantity', None):
            quantity_str = self._format_numeric_range(getattr(criteria, 'quantity'))
            attrs.append(f"with quantity {quantity_str}")
            
        if getattr(criteria, 'quantity', None):
            quantity_str = self._format_numeric_range(getattr(criteria, 'quantity'))
            attrs.append(f"with quantity {quantity_str}")
            
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
            
        codeset_name = self._get_concept_set_name(criteria.codeset_id, "any procedure")
        plural = "s" if (is_plural and not criteria.first) else ""
        first_time = " for the first time in the person's history" if criteria.first else ""
        
        source_concept = ""
        if criteria.procedure_source_concept:
             source_name = self._get_concept_set_name(criteria.procedure_source_concept, "any procedure")
             source_concept = f" (including {source_name} source concepts)"
        
        attrs_str = f", {'; '.join(attrs)}" if attrs else ""
        
        # Main description
        description = f"procedure occurrence{plural} of {codeset_name}{source_concept}{first_time}{attrs_str}"
        
        # Correlated criteria
        if criteria.correlated_criteria:
            correlated_text = self._render_criteria_group(criteria.correlated_criteria, level=level, index_label=codeset_name)
            return f"{description}; {correlated_text}"
        else:
            return f"{description}."
    
    def _render_death(self, criteria: Death, level: int = 0,
                     is_plural: bool = True, count_criteria: Optional[Dict] = None,
                     index_label: str = "cohort entry") -> str:
        """Render Death criteria."""
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        codeset_name = self._get_concept_set_name(criteria.codeset_id, "any form")
        source_concept = ""
        if criteria.death_source_concept is not None:
            source_name = self._get_concept_set_name(criteria.death_source_concept, "any form")
            source_concept = f" (including {source_name} source concepts)"
        
        attrs_str = f", {'; '.join(attrs)}" if attrs else ""
        
        # Main description
        description = f"death of {codeset_name}{source_concept}{attrs_str}"
        
        # Correlated criteria
        if criteria.correlated_criteria:
            correlated_text = self._render_criteria_group(criteria.correlated_criteria, level=level, index_label=codeset_name)
            return f"{description}; {correlated_text}"
        else:
            return f"{description}."
    
    def _render_device_exposure(self, criteria: DeviceExposure, level: int = 0,
                              is_plural: bool = True, count_criteria: Optional[Dict] = None,
                              index_label: str = "cohort entry") -> str:
        """Render DeviceExposure criteria."""
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        if criteria.device_type:
             exclude_str = "is not:" if getattr(criteria, 'device_type_exclude', False) else "is:"
             type_str = self._format_concept_list(criteria.device_type)
             attrs.append(f"a device type that {exclude_str} {type_str}")
        
        if criteria.device_type_cs:
             type_str = self._format_concept_set_selection(criteria.device_type_cs, "any type")
             attrs.append(f"a device type concept {type_str} concept set")
             
        if criteria.unique_device_id:
             ids = ", ".join([f'"{uid}"' for uid in criteria.unique_device_id])
             attrs.append(f"with unique device id: {ids}")
             
        if criteria.quantity:
             quantity_str = self._format_numeric_range(criteria.quantity)
             attrs.append(f"with quantity {quantity_str}")
             
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
        
        codeset_name = self._get_concept_set_name(criteria.codeset_id, "any device")
        plural = "s" if (is_plural and not criteria.first) else ""
        first_time = " for the first time in the person's history" if criteria.first else ""
        
        source_concept = ""
        if criteria.device_source_concept:
             source_name = self._get_concept_set_name(criteria.device_source_concept, "any device")
             source_concept = f" (including {source_name} source concepts)"
        
        attrs_str = f", {'; '.join(attrs)}" if attrs else ""
        
        # Main description
        description = f"device exposure{plural} of {codeset_name}{source_concept}{first_time}{attrs_str}"
        
        # Correlated criteria
        if criteria.correlated_criteria:
            correlated_text = self._render_criteria_group(criteria.correlated_criteria, level=level, index_label=codeset_name)
            return f"{description}; {correlated_text}"
        else:
            return f"{description}."
    
    def _render_measurement(self, criteria: Measurement, level: int = 0,
                           is_plural: bool = True, count_criteria: Optional[Dict] = None,
                           index_label: str = "cohort entry") -> str:
        """Render Measurement criteria."""
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        # Add measurement-specific attributes
        if criteria.measurement_type:
            exclude_str = "is not:" if getattr(criteria, 'measurement_type_exclude', False) else "is:"
            measurement_type_str = self._format_concept_list(criteria.measurement_type)
            attrs.append(f"a measurement type that {exclude_str} {measurement_type_str}")
        
        if criteria.measurement_type_cs:
            measurement_type_str = self._format_concept_set_selection(criteria.measurement_type_cs, "any measurement")
            attrs.append(f"a measurement type concept {measurement_type_str} concept set")
        
        if criteria.operator:
            operator_str = self._format_concept_list(criteria.operator)
            attrs.append(f"with operator: {operator_str}")
        
        if criteria.operator_cs:
            operator_str = self._format_concept_set_selection(criteria.operator_cs, "any operator")
            attrs.append(f"an operator concept {operator_str} concept set")
        
        if criteria.value_as_number:
            value_str = self._format_numeric_range(criteria.value_as_number)
            attrs.append(f"numeric value {value_str}")
        
        if criteria.value_as_string:
            value_str = self._format_text_filter(criteria.value_as_string)
            attrs.append(f"value as string {value_str}")
        
        if criteria.unit:
            unit_str = self._format_concept_list(criteria.unit)
            attrs.append(f"unit: {unit_str}")
        
        if criteria.unit_cs:
            unit_str = self._format_concept_set_selection(criteria.unit_cs, "any unit")
            attrs.append(f"a unit concept {unit_str} concept set")
            
        if criteria.value_as_concept:
            value_str = self._format_concept_list(criteria.value_as_concept)
            attrs.append(f"with value as concept: {value_str}")
        
        if criteria.value_as_concept_cs:
            value_str = self._format_concept_set_selection(criteria.value_as_concept_cs, "any value")
            attrs.append(f"a value as concept {value_str} concept set")
        
        if criteria.range_low:
            range_str = self._format_numeric_range(criteria.range_low)
            attrs.append(f"low range {range_str}")
        
        if criteria.range_high:
            range_str = self._format_numeric_range(criteria.range_high)
            attrs.append(f"high range {range_str}")
        
        if getattr(criteria, 'range_low_ratio', None):
            range_str = self._format_numeric_range(criteria.range_low_ratio)
            attrs.append(f"low range-to-value ratio {range_str}")
            
        if getattr(criteria, 'range_high_ratio', None):
            range_str = self._format_numeric_range(criteria.range_high_ratio)
            attrs.append(f"high range-to-value ratio {range_str}")
            
        if getattr(criteria, 'abnormal', False):
            attrs.append("with abnormal result")
        
        if criteria.provider_specialty_cs:
            provider_str = self._format_concept_set_selection(criteria.provider_specialty_cs, "any specialty")
            attrs.append(f"a provider specialty concept {provider_str} concept set")
        
        if criteria.visit_type:
            visit_str = self._format_concept_list(criteria.visit_type)
            attrs.append(f"a visit occurrence that is: {visit_str}")
        
        if criteria.visit_type_cs:
            visit_str = self._format_concept_set_selection(criteria.visit_type_cs, "any visit")
            attrs.append(f"a visit concept {visit_str} concept set")
        
        codeset_name = self._get_concept_set_name(criteria.codeset_id, "any measurement")
        plural = "s" if (is_plural and not criteria.first) else ""
        first_time = " for the first time in the person's history" if criteria.first else ""
        
        source_concept = ""
        if criteria.measurement_source_concept:
             source_name = self._get_concept_set_name(criteria.measurement_source_concept, "any measurement")
             source_concept = f" (including {source_name} source concepts)"
        
        attrs_str = f", {'; '.join(attrs)}" if attrs else ""
        
        # Main description
        description = f"measurement{plural} of {codeset_name}{source_concept}{first_time}{attrs_str}"
        
        # Correlated criteria
        if criteria.correlated_criteria:
            correlated_text = self._render_criteria_group(criteria.correlated_criteria, level=level, index_label=codeset_name)
            return f"{description}; {correlated_text}"
        else:
            return f"{description}."
    
    def _render_observation(self, criteria: Observation, level: int = 0,
                           is_plural: bool = True, count_criteria: Optional[Dict] = None,
                           index_label: str = "cohort entry") -> str:
        """Render Observation criteria."""
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        # Domain-specific attributes
        if criteria.observation_type:
            exclude_str = "is not:" if getattr(criteria, 'observation_type_exclude', False) else "is:"
            type_str = self._format_concept_list(criteria.observation_type)
            attrs.append(f"an observation type that {exclude_str} {type_str}")
        
        if criteria.observation_type_cs:
            type_str = self._format_concept_set_selection(criteria.observation_type_cs, "any observation type")
            attrs.append(f"an observation type concept {type_str} concept set")
            
        if criteria.value_as_number:
            value_str = self._format_numeric_range(criteria.value_as_number)
            attrs.append(f"numeric value {value_str}")
            
        if criteria.unit:
            unit_str = self._format_concept_list(criteria.unit)
            attrs.append(f"unit: {unit_str}")
            
        if criteria.unit_cs:
            unit_str = self._format_concept_set_selection(criteria.unit_cs, "any unit")
            attrs.append(f"a unit concept {unit_str} concept set")
            
        if criteria.value_as_string:
            value_str = self._format_text_filter(criteria.value_as_string)
            attrs.append(f"with value as string {value_str}")
            
        if criteria.value_as_concept:
            value_str = self._format_concept_list(criteria.value_as_concept)
            attrs.append(f"with value as concept: {value_str}")
            
        if criteria.value_as_concept_cs:
            value_str = self._format_concept_set_selection(criteria.value_as_concept_cs, "any value")
            attrs.append(f"a value as concept {value_str} concept set")
            
        if criteria.qualifier:
            val_str = self._format_concept_list(criteria.qualifier)
            attrs.append(f"with qualifier: {val_str}")
            
        if criteria.qualifier_cs:
            val_str = self._format_concept_set_selection(criteria.qualifier_cs, "any qualifier")
            attrs.append(f"a qualifier concept {val_str} concept set")
            
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
            
        codeset_name = self._get_concept_set_name(criteria.codeset_id, "any observation")
        plural = "s" if (is_plural and not criteria.first) else ""
        first_time = " for the first time in the person's history" if criteria.first else ""
        
        attrs_str = f", {'; '.join(attrs)}" if attrs else ""
        
        # Main description
        description = f"observation{plural} of {codeset_name}{first_time}{attrs_str}"
        
        # Correlated criteria
        if criteria.correlated_criteria:
            correlated_text = self._render_criteria_group(criteria.correlated_criteria, level=level, index_label=codeset_name)
            return f"{description}; {correlated_text}"
        else:
            return f"{description}."
    
    def _render_specimen(self, criteria: Specimen, level: int = 0,
                        is_plural: bool = True, count_criteria: Optional[Dict] = None,
                        index_label: str = "cohort entry") -> str:
        """Render Specimen criteria."""
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        # Domain-specific attributes
        if criteria.specimen_type:
            exclude_str = "is not:" if getattr(criteria, 'specimen_type_exclude', False) else "is:"
            type_str = self._format_concept_list(criteria.specimen_type)
            attrs.append(f"a specimen type that {exclude_str} {type_str}")
        
        if criteria.specimen_type_cs:
            type_str = self._format_concept_set_selection(criteria.specimen_type_cs, "any specimen")
            attrs.append(f"a specimen type concept {type_str} concept set")
            
        if criteria.quantity:
            quantity_str = self._format_numeric_range(criteria.quantity)
            attrs.append(f"with quantity {quantity_str}")
            
        if criteria.unit:
            unit_str = self._format_concept_list(criteria.unit)
            attrs.append(f"with unit: {unit_str}")
            
        if criteria.unit_cs:
            unit_str = self._format_concept_set_selection(criteria.unit_cs, "any unit")
            attrs.append(f"a unit concept {unit_str} concept set")
            
        if criteria.anatomic_site:
            site_str = self._format_concept_list(criteria.anatomic_site)
            attrs.append(f"with anatomic site: {site_str}")
            
        if criteria.anatomic_site_cs:
            site_str = self._format_concept_set_selection(criteria.anatomic_site_cs, "any anatomic site")
            attrs.append(f"an anatomic site concept {site_str} concept set")
            
        if criteria.disease_status:
            status_str = self._format_concept_list(criteria.disease_status)
            attrs.append(f"with disease status: {status_str}")
            
        if criteria.disease_status_cs:
            status_str = self._format_concept_set_selection(criteria.disease_status_cs, "any disease status")
            attrs.append(f"a disease status concept {status_str} concept set")
            
        if criteria.source_id:
            source_str = self._format_text_filter(criteria.source_id)
            attrs.append(f"with source ID {source_str}")
        
        codeset_name = self._get_concept_set_name(criteria.codeset_id, "any specimen")
        plural = "s" if (is_plural and not criteria.first) else ""
        first_time = " for the first time in the person's history" if criteria.first else ""
        
        source_concept = ""
        if criteria.specimen_source_concept is not None:
            source_name = self._get_concept_set_name(criteria.specimen_source_concept, "any specimen")
            source_concept = f" (including {source_name} source concepts)"
        
        attrs_str = f", {'; '.join(attrs)}" if attrs else ""
        
        # Main description
        description = f"specimen{plural} of {codeset_name}{source_concept}{first_time}{attrs_str}"
        
        # Correlated criteria
        if criteria.correlated_criteria:
            correlated_text = self._render_criteria_group(criteria.correlated_criteria, level=level, index_label=codeset_name)
            return f"{description}; {correlated_text}"
        else:
            return f"{description}."
    
    def _render_visit_occurrence(self, criteria: VisitOccurrence, level: int = 0,
                                is_plural: bool = True, count_criteria: Optional[Dict] = None,
                                index_label: str = "cohort entry") -> str:
        """Render VisitOccurrence criteria."""
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        # Domain-specific attributes
        if criteria.visit_type:
            exclude_str = "is not:" if getattr(criteria, 'visit_type_exclude', False) else "is:"
            type_str = self._format_concept_list(criteria.visit_type)
            attrs.append(f"a visit type that {exclude_str} {type_str}")
        
        if criteria.visit_type_cs:
            type_str = self._format_concept_set_selection(criteria.visit_type_cs, "any visit type")
            attrs.append(f"a visit type concept {type_str} concept set")
            
        if criteria.provider_specialty:
            provider_str = self._format_concept_list(criteria.provider_specialty)
            attrs.append(f"a provider specialty that is: {provider_str}")
            
        if criteria.provider_specialty_cs:
            provider_str = self._format_concept_set_selection(criteria.provider_specialty_cs, "any specialty")
            attrs.append(f"a provider specialty concept {provider_str} concept set")
            
        if criteria.visit_length:
            length_str = self._format_numeric_range(criteria.visit_length)
            attrs.append(f"with length {length_str} days")
            
        if criteria.place_of_service:
            pos_str = self._format_concept_list(criteria.place_of_service)
            attrs.append(f"a place of service that is: {pos_str}")
            
        if criteria.place_of_service_cs:
            pos_str = self._format_concept_set_selection(criteria.place_of_service_cs, "any place of service")
            attrs.append(f"a place of service concept {pos_str} concept set")
            
        if criteria.place_of_service_location:
            # Assumed to be location ID or filtering
            pass 
        
        codeset_name = self._get_concept_set_name(criteria.codeset_id, "any visit")
        plural = "s" if (is_plural and not criteria.first) else ""
        first_time = " for the first time in the person's history" if criteria.first else ""
        
        source_concept = ""
        if criteria.visit_source_concept is not None:
             source_name = self._get_concept_set_name(criteria.visit_source_concept, "any visit")
             source_concept = f" (including {source_name} source concepts)"
        
        attrs_str = f", {'; '.join(attrs)}" if attrs else ""
        
        # Main description
        description = f"visit occurrence{plural} of {codeset_name}{source_concept}{first_time}{attrs_str}"
        
        # Correlated criteria
        if criteria.correlated_criteria:
            correlated_text = self._render_criteria_group(criteria.correlated_criteria, level=level, index_label=codeset_name)
            return f"{description}; {correlated_text}"
        else:
            return f"{description}."
    
    def _render_visit_detail(self, criteria: VisitDetail, level: int = 0,
                            is_plural: bool = True, count_criteria: Optional[Dict] = None,
                            index_label: str = "cohort entry") -> str:
        """Render VisitDetail criteria."""
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)

        if criteria.visit_detail_start_date or criteria.visit_detail_end_date:
            ds = self._format_event_dates(criteria.visit_detail_start_date, criteria.visit_detail_end_date)
            if ds:
                attrs.append(ds)
        
        # Domain-specific attributes
        if criteria.visit_detail_type:
            exclude_str = "is not:" if getattr(criteria, 'visit_detail_type_exclude', False) else "is:"
            type_str = self._format_concept_list(criteria.visit_detail_type)
            attrs.append(f"a visit detail type that {exclude_str} {type_str}")
        
        if criteria.visit_detail_type_cs:
            type_str = self._format_concept_set_selection(criteria.visit_detail_type_cs, "any visit detail type")
            attrs.append(f"a visit detail type concept {type_str} concept set")
            
        if criteria.provider_specialty:
            provider_str = self._format_concept_list(criteria.provider_specialty)
            attrs.append(f"a provider specialty that is: {provider_str}")
            
        if criteria.provider_specialty_cs:
            provider_str = self._format_concept_set_selection(criteria.provider_specialty_cs, "any specialty")
            attrs.append(f"a provider specialty concept {provider_str} concept set")
            
        if criteria.visit_detail_length:
            length_str = self._format_numeric_range(criteria.visit_detail_length)
            attrs.append(f"with length {length_str} days")
            
        if criteria.place_of_service:
            pos_str = self._format_concept_list(criteria.place_of_service)
            attrs.append(f"a place of service that is: {pos_str}")
            
        if criteria.place_of_service_cs:
            pos_str = self._format_concept_set_selection(criteria.place_of_service_cs, "any place of service")
            attrs.append(f"a place of service concept {pos_str} concept set")
        
        if criteria.discharge_to:
            discharge_str = self._format_concept_list(criteria.discharge_to)
            attrs.append(f"with discharge to: {discharge_str}")
            
        if criteria.discharge_to_cs:
            discharge_str = self._format_concept_set_selection(criteria.discharge_to_cs, "any discharge to")
            attrs.append(f"a discharge to concept {discharge_str} concept set")
            
        codeset_name = self._get_concept_set_name(criteria.codeset_id, "any visit detail")
        plural = "s" if (is_plural and not criteria.first) else ""
        first_time = " for the first time in the person's history" if criteria.first else ""
        
        source_concept = ""
        if criteria.visit_detail_source_concept is not None:
             source_name = self._get_concept_set_name(criteria.visit_detail_source_concept, "any visit detail")
             source_concept = f" (including {source_name} source concepts)"
        
        attrs_str = f", {'; '.join(attrs)}" if attrs else ""
        
        # Main description
        description = f"visit detail{plural} of {codeset_name}{source_concept}{first_time}{attrs_str}"
        
        # Correlated criteria
        if criteria.correlated_criteria:
            correlated_text = self._render_criteria_group(criteria.correlated_criteria, level=level, index_label=codeset_name)
            return f"{description}; {correlated_text}"
        else:
            return f"{description}."
    
    def _render_observation_period(self, criteria: ObservationPeriod, level: int = 0,
                                  is_plural: bool = True, count_criteria: Optional[Dict] = None,
                                  index_label: str = "cohort entry") -> str:
        """Render ObservationPeriod criteria."""
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        if criteria.user_defined_period:
            period_str = self._render_period(criteria.user_defined_period)
            attrs.append(f"using the period: {period_str}")
            
        if criteria.period_type:
            type_str = self._format_concept_list(criteria.period_type)
            attrs.append(f"period type is: {type_str}")
            
        if criteria.period_type_cs:
             type_str = self._format_concept_set_selection(criteria.period_type_cs, "any period type")
             attrs.append(f"a period type concept {type_str} concept set")
             
        if criteria.period_length:
            length_str = self._format_numeric_range(criteria.period_length)
            attrs.append(f"with a length {length_str} days")
            

             
        if criteria.period_start_date and criteria.period_end_date:
            start_str = self._format_date_range(criteria.period_start_date)
            end_str = self._format_date_range(criteria.period_end_date)
            attrs.append(f"starting {start_str} and ending {end_str}")
        elif criteria.period_start_date:
            date_str = self._format_date_range(criteria.period_start_date)
            attrs.append(f"starting {date_str}")
        elif criteria.period_end_date:
             date_str = self._format_date_range(criteria.period_end_date)
             attrs.append(f"ending {date_str}")

        codeset_id = getattr(criteria, 'codeset_id', None)
        codeset_name = self._get_concept_set_name(codeset_id, "observation period")
        
        plural = "s" if (is_plural and not criteria.first) else ""
        first_time = " for the first time in the person's history" if criteria.first else ""
        
        attrs_str = f", {'; '.join(attrs)}" if attrs else ""
        
        # Main description
        if codeset_name == "observation period":
             if criteria.first is True:
                 description = f"observation period (first obsrvation period in person's history){attrs_str}"
             else:
                 description = f"observation period{plural}{first_time}{attrs_str}"
        else:
             if criteria.first is True:
                 # Logic for first with codeset name? Java might not support codeset name check here cleanly or handles it uniquely
                 # For now, match the "any observation period" case which corresponds to ObservationPeriod test
                  description = f"observation period (first obsrvation period in person's history) of {codeset_name}{attrs_str}"
             else:
                  description = f"observation period{plural} of {codeset_name}{first_time}{attrs_str}"
            
        # Correlated criteria
        correlated_criteria = getattr(criteria, 'correlated_criteria', None)
        if correlated_criteria:
            correlated_text = self._render_criteria_group(correlated_criteria, level=level, index_label=codeset_name)
            return f"{description}; {correlated_text}"
        else:
            return f"{description}."
    
    def _render_payer_plan_period(self, criteria: PayerPlanPeriod, level: int = 0,
                                 is_plural: bool = True, count_criteria: Optional[Dict] = None,
                                 index_label: str = "cohort entry") -> str:
        """Render PayerPlanPeriod criteria."""
        attrs = self._build_criteria_attributes(criteria, count_criteria, index_label)
        
        if criteria.period_length:
            length_str = self._format_numeric_range(criteria.period_length)
            attrs.append(f"with period length {length_str}")
            
        if criteria.user_defined_period:
            period_str = self._render_period(criteria.user_defined_period)
            attrs.append(f"using the period: {period_str}")
            
        if criteria.payer_concept:
            # PayerConcept is int?
            # Assuming logic similar to concept set but for single concept ID if needed?
            # Or usually excluded in print friendly if not a list?
            pass
            
        # ... Other attributes
        
        codeset_name = self._get_concept_set_name(None, "any payer plan period")
        # PayerPlanPeriod usually doesn't have codeset_id in the same way? 
        # Java uses "payer plan period"
        
        plural = "s" if (is_plural and not criteria.first) else ""
        first_time = " for the first time in the person's history" if criteria.first else ""
        
        attrs_str = f", {'; '.join(attrs)}" if attrs else ""
        
        description = f"payer plan period{plural} of {codeset_name}{first_time}{attrs_str}"
        
        if criteria.correlated_criteria:
            correlated_text = self._render_criteria_group(criteria.correlated_criteria, level=level, index_label="payer plan")
            return f"{description}; {correlated_text}"
        else:
            return f"{description}."
            
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
        
        # Main description
        description = f"location of {codeset_name}{attrs_str}"
        
        # Correlated criteria
        if criteria.correlated_criteria:
            correlated_text = self._render_criteria_group(criteria.correlated_criteria, level=level, index_label=codeset_name)
            return f"{description}; {correlated_text}"
        else:
            return f"{description}."
    
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
        
        attrs_str = f", {'; '.join(attrs)}" if attrs else ""
        
        # Main description
        description = f"condition era{plural} of {codeset_name}{first_time}{attrs_str}"
        
        # Correlated criteria
        if criteria.correlated_criteria:
            correlated_text = self._render_criteria_group(criteria.correlated_criteria, level=level, index_label=codeset_name)
            return f"{description}; {correlated_text}"
        else:
            return f"{description}."
    
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
        
        attrs_str = f", {'; '.join(attrs)}" if attrs else ""
        
        # Main description
        description = f"drug era{plural} of {codeset_name}{first_time}{attrs_str}"
        
        # Correlated criteria
        if criteria.correlated_criteria:
            correlated_text = self._render_criteria_group(criteria.correlated_criteria, level=level, index_label=codeset_name)
            return f"{description}; {correlated_text}"
        else:
            return f"{description}."
    
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
        
        attrs_str = f", {'; '.join(attrs)}" if attrs else ""
        
        # Main description
        description = f"dose era{plural} of {codeset_name}{first_time}{attrs_str}"
        
        # Correlated criteria
        if criteria.correlated_criteria:
            correlated_text = self._render_criteria_group(criteria.correlated_criteria, level=level, index_label=codeset_name)
            return f"{description}; {correlated_text}"
        else:
            return f"{description}."
    
    def _render_geo_criteria(self, criteria: GeoCriteria, level: int = 0,
                            is_plural: bool = True, count_criteria: Optional[Dict] = None,
                            index_label: str = "cohort entry") -> str:
        """Render GeoCriteria."""
        attrs = []
        
        # Use getattr to maintain compatibility with Java fields that may not exist in Python model
        codeset_id = getattr(criteria, 'codeset_id', None)
        codeset_name = self._get_concept_set_name(codeset_id, "any location")
        attrs_str = f", {'; '.join(attrs)}" if attrs else ""
        
        # Correlated criteria
        correlated_criteria = getattr(criteria, 'correlated_criteria', None)
        if correlated_criteria:
            correlated_text = self._render_criteria_group(correlated_criteria, level=level, index_label=codeset_name)
            return f"geo criteria of {codeset_name}{attrs_str}; {correlated_text}"
        else:
            return f"geo criteria of {codeset_name}{attrs_str}."

