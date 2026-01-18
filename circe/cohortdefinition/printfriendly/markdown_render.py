"""
Markdown rendering for cohort definitions.

This module provides functionality to generate human-readable markdown descriptions
of cohort definitions, mirroring the Java CIRCE-BE MarkdownRender functionality.

REFACTORED: Now uses Jinja2 templates for 1:1 parity with Java FreeMarker implementation.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List, Optional, Union
from datetime import datetime
from pathlib import Path
import json
import jinja2

from ..cohort import CohortExpression
from ...vocabulary.concept import ConceptSet


class MarkdownRender:
    """Generates human-readable markdown descriptions of cohort definitions.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.printfriendly.MarkdownRender
    
    This implementation uses Jinja2 templates to achieve 1:1 parity with the Java
    FreeMarker template implementation. Templates are located in the templates/
    subdirectory and mirror the structure of Java's .ftl files.
    """
    
    def __init__(self, concept_sets: Optional[List[ConceptSet]] = None, include_concept_sets: bool = False):
        """Initialize the markdown renderer.
        
        Args:
            concept_sets: Optional list of concept sets for resolving codeset IDs to names
            include_concept_sets: Whether to include concept set tables in the output (default: False)
        """
        self._concept_sets = concept_sets or []
        self._include_concept_sets = include_concept_sets
        
        # Initialize Jinja2 environment
        template_dir = Path(__file__).parent / 'templates'
        self._env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False  # We're generating markdown, not HTML
        )
        
        # Register custom filters (matching Java utils.ftl)
        self._env.filters['format_date'] = self._format_date
        self._env.filters['format_number'] = self._format_number
        
        # Register global functions
        self._env.globals['codeset_name'] = self._codeset_name
        self._env.globals['format_date'] = self._format_date
        self._env.globals['format_number'] = self._format_number
    
    def render_cohort_expression(
        self, 
        cohort_expression: Union[CohortExpression, str], 
        include_concept_sets: Optional[bool] = None, 
        title: Optional[str] = None
    ) -> str:
        """Render a cohort expression to markdown format.
        
        Java equivalent: renderCohort(CohortExpression)
        
        Args:
            cohort_expression: The cohort expression to render, or JSON string
            include_concept_sets: Whether to include concept set tables in the output 
                                (overrides init parameter if provided)
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
        
        # Determine whether to include concept sets
        should_include = include_concept_sets if include_concept_sets is not None else self._include_concept_sets
        
        # Load and render the main template
        template = self._env.get_template('cohort_expression.j2')
        
        return template.render(
            cohort=cohort_expression,
            conceptSets=self._concept_sets,
            title=title or cohort_expression.title or "Untitled Cohort",
            include_concept_sets=should_include
        )
    
    def render_concept_set_list(self, concept_sets: Union[List[ConceptSet], str]) -> str:
        """Render a list of concept sets to markdown format.
        
        Java equivalent: renderConceptSetList(ConceptSet[])
        
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
        
        # Load and render the concept set template
        template = self._env.get_template('concept_set.j2')
        
        return template.render(conceptSets=concept_sets)
    
    def render_concept_set(self, concept_set: Union[ConceptSet, str]) -> str:
        """Render a single concept set to markdown format.
        
        Java equivalent: renderConceptSet(ConceptSet)
        
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
    
    # =========================================================================
    # Custom Filters and Functions (matching Java utils.ftl)
    # =========================================================================
    
    def _codeset_name(self, codeset_id: Optional[int], default_name: str = "any") -> str:
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
            if isinstance(date_string, str) and len(date_string) == 10:
                dt = datetime.strptime(date_string, "%Y-%m-%d")
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
