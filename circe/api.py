"""
Simple library API for CIRCE Python

This module provides a simple R CirceR-style API for working with cohort definitions:
- cohort_expression_from_json(): Load cohort expression from JSON string
- build_cohort_query(): Generate SQL from cohort expression
- cohort_print_friendly(): Generate Markdown from cohort expression
"""

from typing import Optional, List
from .cohortdefinition import (
    CohortExpression,
    CohortExpressionQueryBuilder,
    BuildExpressionQueryOptions,
    MarkdownRender,
)
from .vocabulary.concept import ConceptSet


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
    
    # Normalize field names
    data = _normalize_dict(data)
    
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


def _normalize_dict(obj):
    """Recursively normalize dictionary keys."""
    if not isinstance(obj, dict):
        return obj
    
    result = {}
    for key, value in obj.items():
        # Recurse into nested structures
        if isinstance(value, dict):
            value = _normalize_dict(value)
        elif isinstance(value, list):
            value = [_normalize_dict(item) if isinstance(item, dict) else item for item in value]
        
        # Normalize key
        normalized_key = key
        
        # Handle ALL_CAPS_WITH_UNDERSCORES → camelCase (for concept fields)
        if key.isupper() and '_' in key:
            parts = key.split('_')
            normalized_key = parts[0].lower() + ''.join(p.capitalize() for p in parts[1:])
        # Handle PascalCase top-level fields → camelCase
        # BUT preserve certain fields that have explicit Field(alias=...) in models
        elif key and key[0].isupper() and not key.isupper():
            # Fields that must be preserved as-is (have explicit aliases in Pydantic models)
            preserved_fields = [
                # Criteria type names (polymorphic discriminators)
                'ConditionOccurrence', 'DrugExposure', 'ProcedureOccurrence',
                'VisitOccurrence', 'Observation', 'Measurement', 'DeviceExposure',
                'Specimen', 'Death', 'VisitDetail', 'ObservationPeriod',
                'PayerPlanPeriod', 'LocationRegion', 'ConditionEra',
                'DrugEra', 'DoseEra',
                # Window and criteria fields (have Field aliases)
                'StartWindow', 'EndWindow', 'RestrictVisit', 'IgnoreObservationPeriod',
                'Criteria', 'Occurrence',
                # Other fields with explicit aliases
                'UseEventEnd', 'UseIndexEnd', 'Start', 'End', 'Coeff', 'Days',
                'Type', 'Count', 'IsDistinct'
            ]
            if key in preserved_fields:
                # Keep as-is - explicit aliases or type discriminators
                normalized_key = key
            else:
                # Convert to camelCase (lowercase first letter)
                normalized_key = key[0].lower() + key[1:]
        
        result[normalized_key] = value
    
    return result


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
    include_concept_sets: bool = False
) -> str:
    """Generate human-readable Markdown from a cohort expression.
    
    This is equivalent to R CirceR's `cohortPrintFriendly()` function.
    
    Args:
        expression: CohortExpression instance
        concept_sets: Optional list of concept sets (uses expression.concept_sets if None)
        include_concept_sets: Whether to include concept set tables in the output (default: False)
        
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
    return renderer.render_cohort_expression(expression)

