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

