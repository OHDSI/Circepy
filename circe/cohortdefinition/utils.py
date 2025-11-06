"""
Utility functions for cohort definition processing.

This module contains helper functions for field name conversion and other utilities.
"""


def to_camel_alias(field_name: str) -> str:
    """Convert field name to camelCase for JSON compatibility.
    
    This is used as an alias_generator in Pydantic ConfigDict to automatically
    handle field name conversion from Python snake_case to JSON camelCase.
    
    Examples:
        prior_days -> priorDays
        era_pad -> eraPad
        collapse_type -> collapseType
        
    Args:
        field_name: Python field name (typically snake_case)
        
    Returns:
        camelCase version of the field name
    """
    if '_' in field_name:
        # Convert snake_case to camelCase
        parts = field_name.split('_')
        return parts[0] + ''.join(word.capitalize() for word in parts[1:])
    # Already in camelCase or single word, return as-is
    return field_name


def to_pascal_alias(field_name: str) -> str:
    """Convert field name to PascalCase for Java JSON compatibility.
    
    This is used as an alias_generator in Pydantic ConfigDict to automatically
    handle field name conversion from Python snake_case to Java JSON PascalCase.
    Java CIRCE-BE uses PascalCase for all JSON field names.
    
    Examples:
        concept_sets -> ConceptSets
        primary_criteria -> PrimaryCriteria
        criteria_list -> CriteriaList
        observation_window -> ObservationWindow
        codeset_id -> CodesetId
        condition_type_exclude -> ConditionTypeExclude
        
    Args:
        field_name: Python field name (typically snake_case)
        
    Returns:
        PascalCase version of the field name
    """
    if '_' in field_name:
        # Convert snake_case to PascalCase (capitalize all parts including first)
        parts = field_name.split('_')
        return ''.join(word.capitalize() for word in parts)
    # Single word - capitalize first letter
    return field_name[0].upper() + field_name[1:] if field_name else field_name

