"""
Simple library API for CIRCE Python

This module provides a simple R CirceR-style API for working with cohort definitions:
- cohort_expression_from_json(): Load cohort expression from JSON string
- build_cohort_query(): Generate SQL from cohort expression
- cohort_print_friendly(): Generate Markdown from cohort expression
- create_cohort_prompt(): Generate LLM prompts for cohort generation
"""

from typing import Optional, List, Dict, Any, Literal
from .cohortdefinition import (
    CohortExpression,
    CohortExpressionQueryBuilder,
    BuildExpressionQueryOptions,
    MarkdownRender,
)
from .vocabulary.concept import ConceptSet
from .prompt_builder import (
    CohortPromptBuilder,
    ConceptSet as PromptConceptSet,
    create_prompt as _create_prompt_impl,
    ModelType
)


def cohort_expression_from_json(json_str: str) -> CohortExpression:
    """Load a cohort expression from a JSON string.
    
    This is equivalent to R CirceR's `cohortExpressionFromJson()` function.
    
    Args:
        json_str: JSON string containing the cohort definition
        
    Returns:
        CohortExpression instance
        
    Raises:
        ValueError: If the JSON is invalid or doesn't conform to the schema
        
    Example:
        >>> json_str = '{"ConceptSets": [], "PrimaryCriteria": {...}}'
        >>> expression = cohort_expression_from_json(json_str)
    """
    import json
    
    # Parse JSON
    data = json.loads(json_str)
    
    # Handle cdmVersionRange as string
    if 'cdmVersionRange' in data and isinstance(data['cdmVersionRange'], str):
        data.pop('cdmVersionRange', None)

    # Handle empty censorWindow
    if 'censorWindow' in data and data['censorWindow'] == {}:
        data.pop('censorWindow', None)

    # Ensure ConceptSetExpression objects have required fields
    if 'conceptSets' in data and data['conceptSets']:
        for concept_set in data['conceptSets']:
            if isinstance(concept_set, dict) and 'expression' in concept_set and concept_set['expression'] is not None:
                expr = concept_set['expression']
                if isinstance(expr, dict):
                    if 'isExcluded' not in expr:
                        expr['isExcluded'] = False
                    if 'includeMapped' not in expr:
                        expr['includeMapped'] = False
                    if 'includeDescendants' not in expr:
                        expr['includeDescendants'] = False

    try:
        return CohortExpression.model_validate(data)
    except Exception as e:
        raise ValueError(f"Invalid cohort expression JSON: {str(e)}") from e


def build_cohort_query(
    expression: CohortExpression,
    options: Optional[BuildExpressionQueryOptions] = None
) -> str:
    """Generate SQL query from a cohort expression.

    This is equivalent to R CirceR's `buildCohortQuery()` function.

    Args:
        expression: CohortExpression instance
        options: Build options (schema names, cohort ID, etc.)

    Returns:
        SQL query string

    Example:
        >>> expression = cohort_expression_from_json(json_str)
        >>> options = BuildExpressionQueryOptions()
        >>> options.cdm_schema = "cdm"
        >>> options.target_table = "cohort"
        >>> options.cohort_id = 1
        >>> sql = build_cohort_query(expression, options)
    """
    if options is None:
        options = BuildExpressionQueryOptions()

    builder = CohortExpressionQueryBuilder()
    return builder.build_expression_query(expression, options)


def cohort_print_friendly(
    expression: CohortExpression,
    concept_sets: Optional[List[ConceptSet]] = None,
    title: Optional[str] = None,
    include_concept_sets: bool = False
) -> str:
    """Generate human-readable Markdown from a cohort expression.
    
    This is equivalent to R CirceR's `cohortPrintFriendly()` function.
    
    Args:
        expression: CohortExpression instance
        concept_sets: Optional list of concept sets (uses expression.concept_sets if None)
        include_concept_sets: Whether to include concept set tables in the output (default: False)
        title: Optional title for the output (default: None)
    Returns:
        Markdown string
        
    Example:
        >>> expression = cohort_expression_from_json(json_str)
        >>> markdown = cohort_print_friendly(expression)
        >>> # Include concept sets in output
        >>> markdown_with_sets = cohort_print_friendly(expression, include_concept_sets=True)
    """
    if concept_sets is None:
        concept_sets = expression.concept_sets or []
    
    renderer = MarkdownRender(concept_sets=concept_sets, include_concept_sets=include_concept_sets)
    return renderer.render_cohort_expression(expression, title=title)


def create_cohort_prompt(
    clinical_description: str,
    concept_sets: List[Dict[str, Any]],
    model_type: ModelType = "standard",
    additional_notes: Optional[str] = None
) -> str:
    """
    Generate a complete prompt for LLM-based cohort generation.
    
    This combines the appropriate system prompt with your clinical description
    and concept sets to create a ready-to-use prompt for AI models.
    
    Args:
        clinical_description: Clinical description of the cohort to generate
        concept_sets: List of dicts with 'id', 'name', and optional 'description'
        model_type: Target model type: 'reasoning', 'standard', or 'fast'
        additional_notes: Optional additional instructions or constraints
        
    Returns:
        Complete prompt string ready to send to an LLM
        
    Example:
        >>> from circe.api import create_cohort_prompt
        >>> 
        >>> concept_sets = [
        ...     {"id": 1, "name": "Type 2 Diabetes", "description": "Standard T2DM codes"},
        ...     {"id": 2, "name": "Metformin"},
        ...     {"id": 3, "name": "Insulin"}
        ... ]
        >>> 
        >>> prompt = create_cohort_prompt(
        ...     clinical_description="Adults aged 18-65 with new T2DM, prior Metformin, no Insulin",
        ...     concept_sets=concept_sets,
        ...     model_type="standard"
        ... )
        >>> 
        >>> # Send to your LLM
        >>> # response = openai.chat.completions.create(..., messages=[{"role": "user", "content": prompt}])
    """
    return _create_prompt_impl(
        clinical_description=clinical_description,
        concept_sets=concept_sets,
        model_type=model_type,
        additional_notes=additional_notes
    )

