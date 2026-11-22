"""Capr-style cohort definition API for Circepy.

This package ports the public surface of OHDSI's R
`Capr <https://ohdsi.github.io/Capr/>`_ package (v3.0.0) to Python, building on
Circepy's existing CIRCE-BE models rather than a parallel representation.

Example:
    >>> import circe as circe
    >>> cs = circe.capr
    >>> t2dm = cs.cs(cs.descendants(201826), name="T2DM")
    >>> cd = cs.cohort(
    ...     entry=cs.entry(cs.condition_occurrence(t2dm, cs.first_occurrence())),
    ...     attrition=cs.attrition(expression_limit="First"),
    ...     exit=cs.exit(cs.observation_exit()),
    ... )
    >>> expression = cs.to_cohort_expression(cd)  # a CohortExpression
"""

from .concept_set import CaprConceptSet, ConceptSpec, cs, descendants, exclude, mapped
from .criteria import *  # noqa: F403
from .criteria import __all__ as _criteria_all
from .json_to_capr import DecompiledCohort, JsonToCaprError, json_to_capr, json_to_capr_file

__all__ = [
    "CaprConceptSet",
    "ConceptSpec",
    "cs",
    "descendants",
    "exclude",
    "mapped",
    "DecompiledCohort",
    "JsonToCaprError",
    "json_to_capr",
    "json_to_capr_file",
    *_criteria_all,
]
