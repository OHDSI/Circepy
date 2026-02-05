"""
Evaluation framework data models.

Defines EvaluationRule, EvaluationRubric, and result classes for phenotype scoring.
"""

from typing import List, Optional, Literal, Union, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import date


class EvaluationRule(BaseModel):
    """A single rule in a phenotype evaluation rubric.
    
    Each rule defines clinical criteria to check and the score to assign if matched.
    
    Attributes:
        rule_id: Unique identifier for this rule within the rubric
        name: Human-readable name for the rule
        description: Detailed description of what this rule checks
        domain: CDM domain table to query (condition_occurrence, procedure_occurrence, etc.)
        concept_ids: List of concept IDs to match
        weight: Score to assign if rule matches (0 if no match)
        window_start_days: Days before index date to search (negative = before)
        window_end_days: Days after index date to search (positive = after)
    """
    rule_id: int = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Rule name")
    description: Optional[str] = Field(default=None, description="Rule description")
    
    # Clinical criteria
    domain: Literal[
        "condition_occurrence",
        "procedure_occurrence",
        "drug_exposure",
        "measurement",
        "observation",
        "visit_occurrence",
        "device_exposure"
    ] = Field(..., description="CDM domain table")
    concept_ids: List[int] = Field(..., description="Concept IDs to match")
    
    # Temporal window relative to index date
    window_start_days: int = Field(default=-30, description="Days before index (negative)")
    window_end_days: int = Field(default=30, description="Days after index (positive)")
    
    # Scoring
    weight: float = Field(default=1.0, description="Score if matched")
    
    # Optional: value constraints for measurements
    value_threshold: Optional[float] = Field(default=None, description="Value threshold for measurements")
    value_operator: Optional[Literal["lt", "lte", "gt", "gte", "eq"]] = Field(
        default=None, description="Comparison operator for value"
    )
    
    model_config = ConfigDict(frozen=True)


class EvaluationRubric(BaseModel):
    """A complete phenotype validation rubric.
    
    Contains a set of rules to evaluate individuals against, with configuration
    for how to identify the rubric in results.
    
    Attributes:
        ruleset_id: Unique identifier for this rubric
        name: Human-readable name
        description: Detailed description
        target_phenotype: The phenotype being evaluated
        rules: List of evaluation rules
    """
    ruleset_id: int = Field(..., description="Unique ruleset identifier")
    name: str = Field(..., description="Rubric name")
    description: Optional[str] = Field(default=None, description="Rubric description")
    target_phenotype: str = Field(..., description="Phenotype being evaluated")
    rules: List[EvaluationRule] = Field(default_factory=list, description="Evaluation rules")
    
    model_config = ConfigDict(frozen=True)
    
    def add_rule(self, rule: EvaluationRule) -> "EvaluationRubric":
        """Return a new rubric with the rule added."""
        return self.model_copy(update={"rules": [*self.rules, rule]})


class RuleResult(BaseModel):
    """Result of evaluating a single rule for one individual.
    
    Matches the normalized output table schema:
    ruleset_id, subject_id, rule_id, score
    """
    ruleset_id: int
    subject_id: int
    rule_id: int
    score: float
    
    model_config = ConfigDict(frozen=True)


class SubjectEvaluation(BaseModel):
    """Aggregated evaluation result for one subject.
    
    Produced by aggregating RuleResults for a single subject.
    """
    ruleset_id: int
    subject_id: int
    total_score: float
    matched_rules: List[int] = Field(default_factory=list, description="IDs of matched rules")
    
    model_config = ConfigDict(frozen=True)
