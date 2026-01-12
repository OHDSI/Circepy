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
        validation_alias=AliasChoices("ConceptId", "CONCEPT_ID", "conceptId", "ConceptID"),
        serialization_alias="CONCEPT_ID"
    )
    concept_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("ConceptName", "CONCEPT_NAME", "conceptName"),
        serialization_alias="CONCEPT_NAME"
    )
    concept_code: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("ConceptCode", "CONCEPT_CODE", "conceptCode"),
        serialization_alias="CONCEPT_CODE"
    )
    concept_class_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("ConceptClassId", "CONCEPT_CLASS_ID", "conceptClassId"),
        serialization_alias="CONCEPT_CLASS_ID"
    )
    standard_concept: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("StandardConcept", "STANDARD_CONCEPT", "standardConcept"),
        serialization_alias="STANDARD_CONCEPT"
    )
    invalid_reason: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("InvalidReason", "INVALID_REASON", "invalidReason"),
        serialization_alias="INVALID_REASON"
    )
    domain_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("DomainId", "DOMAIN_ID", "domainId"),
        serialization_alias="DOMAIN_ID"
    )
    vocabulary_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("VocabularyId", "VOCABULARY_ID", "vocabularyId"),
        serialization_alias="VOCABULARY_ID"
    )

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
    include_mapped: bool = Field(default=False, alias="includeMapped")
    include_descendants: bool = Field(default=False, alias="includeDescendants")
    items: Optional[List[ConceptSetItem]] = None

    model_config = ConfigDict(populate_by_name=True)


class ConceptSet(BaseModel):
    """Java equivalent: org.ohdsi.circe.cohortdefinition.ConceptSet"""

    id: int = Field(
        alias="id",
        validation_alias=AliasChoices("id", "ID"),
        description="Field: id (int)"
    )

    name: Optional[str] = Field(
        default=None,
        alias="name",
        validation_alias=AliasChoices("name", "NAME"),
        description="Field: name (String)"
    )

    expression: Optional[ConceptSetExpression] = Field(
        default=None,
        alias="expression",
        validation_alias=AliasChoices("expression", "EXPRESSION"),
        description="Field: expression (ConceptSetExpression)"
    )

    model_config = ConfigDict(populate_by_name=True)

# Forward references will be resolved when all classes are imported
ConceptSet.model_rebuild()
