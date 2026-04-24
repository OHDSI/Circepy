"""
Vocabulary Module

This module contains classes for managing concepts, concept sets, and concept set expressions.
It mirrors the Java CIRCE-BE vocabulary package structure.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import Optional, Union

from .concept import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem

# =============================================================================
# COMPOSER HELPER FUNCTIONS
# =============================================================================


class ConceptReference:
    """
    Lightweight reference to a concept for use in concept_set() builder.

    Attributes:
        concept_id: The OMOP concept ID
        include_descendants: Whether to include descendant concepts
        include_mapped: Whether to include mapped concepts
        is_excluded: Whether this concept is excluded
    """

    def __init__(
        self,
        concept_id: int,
        include_descendants: bool = False,
        include_mapped: bool = False,
        is_excluded: bool = False,
    ):
        self.concept_id = concept_id
        self.include_descendants = include_descendants
        self.include_mapped = include_mapped
        self.is_excluded = is_excluded


def descendants(concept_id: int) -> ConceptReference:
    """
    Create a concept reference that includes all descendants.

    Args:
        concept_id: The OMOP concept ID

    Returns:
        ConceptReference with include_descendants=True

    Example:
        >>> # Type 2 Diabetes and all descendants
        >>> descendants(201826)
    """
    return ConceptReference(concept_id=concept_id, include_descendants=True)


def mapped(concept_id: int) -> ConceptReference:
    """
    Create a concept reference that includes mapped concepts.

    Args:
        concept_id: The OMOP concept ID

    Returns:
        ConceptReference with include_mapped=True
    """
    return ConceptReference(concept_id=concept_id, include_mapped=True)


def exclude(concept_ref: Union[int, ConceptReference]) -> ConceptReference:
    """
    Mark a concept or concept reference as excluded.

    Args:
        concept_ref: Concept ID or ConceptReference to exclude

    Returns:
        ConceptReference with is_excluded=True
    """
    if isinstance(concept_ref, int):
        return ConceptReference(concept_id=concept_ref, is_excluded=True)
    return ConceptReference(
        concept_id=concept_ref.concept_id,
        include_descendants=concept_ref.include_descendants,
        include_mapped=concept_ref.include_mapped,
        is_excluded=True,
    )


def concept_set(
    *concepts: Union[int, ConceptReference], id: Optional[int] = None, name: Optional[str] = None
) -> ConceptSet:
    """
    Create a concept set from concept IDs or references.

    Args:
        *concepts: Variable number of concept IDs or ConceptReference objects
        id: Optional ID for the concept set (auto-generated if not provided)
        name: Optional name for the concept set

    Returns:
        ConceptSet object ready for use in cohort definitions

    Example:
        >>> # Simple concept set with descendants
        >>> t2dm = concept_set(
        ...     descendants(201826),
        ...     name="Type 2 Diabetes"
        ... )

        >>> # Multiple concepts
        >>> diabetes = concept_set(
        ...     descendants(201826),  # T2DM
        ...     descendants(201254),  # T1DM
        ...     name="All Diabetes"
        ... )

        >>> # With exclusions
        >>> t2dm_no_secondary = concept_set(
        ...     descendants(201826),
        ...     exclude(descendants(443238)),  # Exclude secondary diabetes
        ...     name="T2DM (no secondary)"
        ... )
    """
    items = []
    for concept in concepts:
        if isinstance(concept, int):
            # Simple concept ID
            items.append(
                ConceptSetItem(
                    concept=Concept(concept_id=concept),
                    include_descendants=False,
                    include_mapped=False,
                    is_excluded=False,
                )
            )
        elif isinstance(concept, ConceptReference):
            # ConceptReference with options
            items.append(
                ConceptSetItem(
                    concept=Concept(concept_id=concept.concept_id),
                    include_descendants=concept.include_descendants,
                    include_mapped=concept.include_mapped,
                    is_excluded=concept.is_excluded,
                )
            )

    return ConceptSet(
        id=id or 0,  # Will need to be set by user or auto-assigned
        name=name or "Concept Set",
        expression=ConceptSetExpression(items=items),
    )


__all__ = [
    # Core classes
    "Concept",
    "ConceptSet",
    "ConceptSetExpression",
    "ConceptSetItem",
    # Composer helpers
    "concept_set",
    "descendants",
    "mapped",
    "exclude",
    "ConceptReference",
]
