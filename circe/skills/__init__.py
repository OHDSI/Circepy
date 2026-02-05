"""
Skills module for AI agent integration.

This module provides documentation and API reference for AI agents
that use the circe package to build OHDSI cohort definitions.

Usage:
    from circe.skills import get_cohort_builder_skill

    # Get the skill documentation as a string
    skill_docs = get_cohort_builder_skill()
"""

from importlib.resources import files
from typing import Optional


def get_cohort_builder_skill() -> str:
    """
    Return the CohortBuilder skill documentation for AI agents.
    """
    skill_file = files("circe.skills").joinpath("cohort_builder.md")
    return skill_file.read_text()


def get_evaluation_builder_skill() -> str:
    """
    Return the EvaluationBuilder skill documentation for AI agents.
    
    This returns a markdown document describing how to use the
    EvaluationBuilder context manager API to build phenotype evaluation rubrics.
    
    Returns:
        str: Markdown documentation for the EvaluationBuilder API
    """
    skill_file = files("circe.skills").joinpath("evaluation_builder.md")
    return skill_file.read_text()


def get_skill(name: str = "cohort_builder") -> Optional[str]:
    """
    Return skill documentation by name.
    
    Args:
        name: Name of the skill (default: "cohort_builder")
        
    Returns:
        str: Skill documentation, or None if not found
        
    Available skills:
        - cohort_builder: Build OHDSI cohort definitions using CohortBuilder
        - evaluation_builder: Build OHDSI evaluation rubrics using EvaluationBuilder
    """
    skill_map = {
        "cohort_builder": get_cohort_builder_skill,
        "evaluation_builder": get_evaluation_builder_skill,
    }
    
    func = skill_map.get(name)
    if func:
        return func()
    return None


def list_skills() -> list:
    """
    List all available skills.
    
    Returns:
        list: Names of available skills
    """
    return ["cohort_builder", "evaluation_builder"]
