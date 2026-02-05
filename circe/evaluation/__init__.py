"""
Cohort Evaluation Framework.

This module provides tools for evaluating individuals against phenotype rubrics,
producing rule-by-rule scores that can be aggregated using flexible methods.
"""

from .models import EvaluationRule, EvaluationRubric, RuleResult
from .sql_generator import RubricSqlGenerator

__all__ = [
    "EvaluationRule",
    "EvaluationRubric",
    "RuleResult",
    "RubricSqlGenerator",
]
