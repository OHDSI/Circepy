"""
Vocabulary classes for concept management.

This module contains classes for managing concepts, concept sets, and concept set expressions.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, AliasChoices


class Concept(BaseModel):
    """Represents a concept in the OMOP vocabulary.
    
    Java equivalent: org.ohdsi.circe.vocabulary.Concept
    Note: In Java, conceptId is Long (nullable), but JSON schema marks it as required.
    We make it Optional to match Java runtime behavior while maintaining schema compatibility.
    """
    concept_id: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("CONCEPT_ID", "conceptId"),
        serialization_alias="CONCEPT_ID"
    )
    concept_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("CONCEPT_NAME", "conceptName"),
        serialization_alias="CONCEPT_NAME"
    )
    concept_code: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("CONCEPT_CODE", "conceptCode"),
        serialization_alias="CONCEPT_CODE"
    )
    concept_class_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("CONCEPT_CLASS_ID", "conceptClassId"),
        serialization_alias="CONCEPT_CLASS_ID"
    )
    standard_concept: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("STANDARD_CONCEPT", "standardConcept"),
        serialization_alias="STANDARD_CONCEPT"
    )
    standard_concept_caption: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("STANDARD_CONCEPT_CAPTION", "standardConceptCaption"),
        serialization_alias="STANDARD_CONCEPT_CAPTION"
    )
    invalid_reason: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("INVALID_REASON", "invalidReason"),
        serialization_alias="INVALID_REASON"
    )
    invalid_reason_caption: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("INVALID_REASON_CAPTION", "invalidReasonCaption"),
        serialization_alias="INVALID_REASON_CAPTION"
    )
    domain_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("DOMAIN_ID", "domainId"),
        serialization_alias="DOMAIN_ID"
    )
    vocabulary_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("VOCABULARY_ID", "vocabularyId"),
        serialization_alias="VOCABULARY_ID"
    )
    # Java-specific fields for 1:1 compatibility (excluded from export)
    false: Optional[Any] = Field(default=None, exclude=True)
    other: Optional['Concept'] = Field(default=None, exclude=True)
    true: Optional[Any] = Field(default=None, exclude=True)

    model_config = ConfigDict(populate_by_name=True)


class ConceptSetItem(BaseModel):
    """Represents an item in a concept set.
    
    Java equivalent: org.ohdsi.circe.vocabulary.ConceptSetItem
    """
    concept: Optional[Concept] = None
    is_excluded: bool = Field(default=False, alias="isExcluded")
    include_mapped: bool = Field(default=False, alias="includeMapped")
    include_descendants: bool = Field(default=False, alias="includeDescendants")

    model_config = ConfigDict(populate_by_name=True)


class ConceptSetExpression(BaseModel):
    """Represents a concept set expression.
    
    Java equivalent: org.ohdsi.circe.vocabulary.ConceptSetExpression
    
    Note: isExcluded, includeMapped, includeDescendants may not be present in all Java JSONs
    (they're sometimes only on the items), so we provide defaults.
    """
    concept: Optional[Concept] = None
    is_excluded: bool = Field(default=False, alias="isExcluded")
    other: Optional[ConceptSetItem] = Field(default=None, exclude=True)
    include_mapped: bool = Field(default=False, alias="includeMapped")
    json_mapper: Optional[Any] = Field(default=None, alias="JSON_MAPPER", exclude=True)
    include_descendants: bool = Field(default=False, alias="includeDescendants")
    items: Optional[List[ConceptSetItem]] = None
    # Java-specific fields for 1:1 compatibility (excluded from export)
    true: Optional[Any] = Field(default=None, exclude=True)
    false: Optional[Any] = Field(default=None, exclude=True)

    model_config = ConfigDict(populate_by_name=True)


class ConceptSet(BaseModel):
    """Represents a concept set.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.ConceptSet
    """
    id: int
    name: Optional[str] = None
    expression: Optional[ConceptSetExpression] = None
    other: Optional['ConceptSet'] = Field(default=None, exclude=True)
    true: Optional[Any] = Field(default=None, exclude=True)
    false: Optional[Any] = Field(default=None, exclude=True)


# Forward references will be resolved when all classes are imported
ConceptSet.model_rebuild()
