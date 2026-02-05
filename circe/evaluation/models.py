"""
Pydantic models for the Phenotype Evaluation Framework.
"""

from typing import List, Optional
from pydantic import Field, ConfigDict
from circe.cohortdefinition.core import CirceBaseModel
from circe.cohortdefinition.criteria import CorelatedCriteria
from circe.vocabulary import ConceptSet


class EvaluationRule(CirceBaseModel):
    """
    Wraps a CorelatedCriteria with scoring metadata.
    """
    rule_id: int = Field(..., description="Unique identifier for the rule")
    name: str = Field(..., description="Human-readable name for the rule")
    criteria: CorelatedCriteria = Field(..., description="CIRCE criteria to evaluate")
    weight: float = Field(..., description="Score awarded if criteria is matched")
    category: Optional[str] = Field(None, description="Rule category (e.g., Primary, Validation)")
    polarity: int = Field(1, description="1 for positive evidence, -1 for negative evidence")

    model_config = ConfigDict(populate_by_name=True)


class EvaluationRubric(CirceBaseModel):
    """
    A collection of rules and concept sets targeting a specific phenotype.
    """
    concept_sets: List[ConceptSet] = Field(default_factory=list, description="Concept sets used by the rules")
    rules: List[EvaluationRule] = Field(..., description="List of evaluation rules")

    model_config = ConfigDict(populate_by_name=True)


class RuleResult(CirceBaseModel):
    """
    Result of a single rule evaluation for an individual.
    """
    rule_id: int
    rule_name: str
    score: float
    matched: bool
    category: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class IndividualEvaluation(CirceBaseModel):
    """
    Structured result object for a single person at a given index date.
    """
    subject_id: int
    index_date: str
    ruleset_id: int
    total_score: float
    rules: List[RuleResult]

    model_config = ConfigDict(populate_by_name=True)
