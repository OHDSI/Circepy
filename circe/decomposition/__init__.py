"""Decomposable, composable cohort definitions.

The package exposes:

* :func:`decompose_cohort_set` -- split a definition set into shared bases plus
  v1-placed refinements (:class:`Decomposition`).
* :class:`ConceptSetCanonicalizer` -- content-address concept sets so cohorts
  that use different local ids for the same concepts share checkpoints.
* :class:`~circe.execution.shared.SharedCohortExecutor` -- execute the resulting
  checkpoint DAG, materialising each shared base stage once.

Example:
    >>> from circe.cohort_definition_set import CohortDefinitionSet
    >>> from circe.decomposition import decompose_cohort_set
    >>> decomposition = decompose_cohort_set(cohort_set)
    >>> print(decomposition.describe())
"""

from .algebra import Decomposition, DerivedCohort, decompose_cohort_set
from .canonical import (
    ConceptSetCanonicalizer,
    concept_set_content_key,
    semantic_expression_key,
    stable_digest,
)
from .operators import (
    AddCensoring,
    AddConceptSets,
    AddInclusionRule,
    Refinement,
    RequireAtEntry,
    SetCensorWindow,
    SetCollapse,
    SetEndStrategy,
    SetExpressionLimit,
    SetQualifiedLimit,
    SetTitle,
)

__all__ = [
    "Decomposition",
    "DerivedCohort",
    "decompose_cohort_set",
    "ConceptSetCanonicalizer",
    "concept_set_content_key",
    "semantic_expression_key",
    "stable_digest",
    "Refinement",
    "RequireAtEntry",
    "AddInclusionRule",
    "SetQualifiedLimit",
    "SetExpressionLimit",
    "SetEndStrategy",
    "AddCensoring",
    "SetCensorWindow",
    "SetCollapse",
    "AddConceptSets",
    "SetTitle",
]
