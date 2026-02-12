"""
Markdown rendering for evaluation rubrics.
"""

from typing import List, Optional, Union
from datetime import datetime
from pathlib import Path
import jinja2

from circe.evaluation.models import EvaluationRubric, EvaluationRule
from circe.vocabulary import ConceptSet


class EvaluationMarkdownRender:
    """Generates human-readable markdown descriptions of evaluation rubrics.
    
    Reuses existing cohort markdown templates for consistency.
    """
    
    def __init__(self, concept_sets: Optional[List[ConceptSet]] = None):
        """Initialize the evaluation markdown renderer.
        
        Args:
            concept_sets: Optional list of concept sets for resolving codeset IDs to names
        """
        self._concept_sets = concept_sets or []
        
        # Initialize Jinja2 environment with multiple loaders
        # This allows us to access both evaluation-specific templates and cohort ones
        self._env = jinja2.Environment(
            loader=jinja2.ChoiceLoader([
                jinja2.PackageLoader('circe.evaluation', 'templates'),
                jinja2.PackageLoader('circe.cohortdefinition.printfriendly', 'templates')
            ]),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False
        )
        
        # Register custom filters and globals (matching cohort MarkdownRender)
        self._env.filters['format_date'] = self._format_date
        self._env.filters['format_number'] = self._format_number
        self._env.globals['codeset_name'] = self._codeset_name
        self._env.globals['format_date'] = self._format_date
        self._env.globals['format_number'] = self._format_number

    def render_rubric(
        self, 
        rubric: Union[EvaluationRubric, str], 
        title: Optional[str] = None
    ) -> str:
        """Render an evaluation rubric to markdown format.
        
        Args:
            rubric: The evaluation rubric to render, or JSON string
            title: Optional title for the markdown output
            
        Returns:
            Markdown formatted string describing the rubric
        """
        if isinstance(rubric, str):
            rubric = EvaluationRubric.model_validate_json(rubric)
        
        if not rubric:
            return "# Invalid Rubric\n\nNo rubric provided."
        
        # Update concept sets for resolving names
        if rubric.concept_sets:
            self._concept_sets = rubric.concept_sets
        
        # Load and render the main template
        template = self._env.get_template('evaluation_rubric.j2')
        
        return template.render(
            rubric=rubric,
            conceptSets=self._concept_sets,
            title=title or "Evaluation Rubric"
        )

    def _codeset_name(self, codeset_id: Optional[int], default_name: str = "any") -> str:
        if codeset_id is None:
            return default_name
        for concept_set in self._concept_sets:
            if concept_set.id == codeset_id:
                return f"'{concept_set.name}'"
        return default_name

    def _format_date(self, date_string: str) -> str:
        try:
            if isinstance(date_string, str) and len(date_string) == 10:
                dt = datetime.strptime(date_string, "%Y-%m-%d")
                day = dt.strftime("%d").lstrip("0")
                return f"{dt.strftime('%B')} {day}, {dt.strftime('%Y')}"
            return date_string
        except (ValueError, AttributeError):
            return "_invalid date_"

    def _format_number(self, value: Union[int, float]) -> str:
        if value is None:
            return ""
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        return f"{value:,}"
