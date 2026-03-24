"""
Vocabulary classes for concept management.

This module contains classes for managing concepts, concept sets, and concept set expressions.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class Concept(BaseModel):
    """Represents a concept in the OMOP vocabulary.

    Java equivalent: org.ohdsi.circe.vocabulary.Concept

    Supports both legacy and new OHDSI concept set schema formats.
    Note: In Java, conceptId is Long (nullable), but new schema marks it as required.
    We make it Optional to match Java runtime behavior while maintaining schema compatibility.

    New schema adds: validStartDate, validEndDate, invalidReason with specific formats.
    """

    concept_id: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("ConceptId", "CONCEPT_ID", "conceptId", "ConceptID"),
        serialization_alias="CONCEPT_ID",
    )
    concept_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("ConceptName", "CONCEPT_NAME", "conceptName"),
        serialization_alias="CONCEPT_NAME",
    )
    concept_code: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("ConceptCode", "CONCEPT_CODE", "conceptCode"),
        serialization_alias="CONCEPT_CODE",
    )
    concept_class_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("ConceptClassId", "CONCEPT_CLASS_ID", "conceptClassId"),
        serialization_alias="CONCEPT_CLASS_ID",
    )
    standard_concept: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("StandardConcept", "STANDARD_CONCEPT", "standardConcept"),
        serialization_alias="STANDARD_CONCEPT",
    )
    invalid_reason: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("InvalidReason", "INVALID_REASON", "invalidReason"),
        serialization_alias="INVALID_REASON",
    )
    domain_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("DomainId", "DOMAIN_ID", "domainId"),
        serialization_alias="DOMAIN_ID",
    )
    vocabulary_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("VocabularyId", "VOCABULARY_ID", "vocabularyId"),
        serialization_alias="VOCABULARY_ID",
    )
    # New schema fields
    valid_start_date: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("validStartDate", "valid_start_date"),
        serialization_alias="validStartDate",
    )
    valid_end_date: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("validEndDate", "valid_end_date"),
        serialization_alias="validEndDate",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("standard_concept")
    @classmethod
    def validate_standard_concept(cls, v: Optional[str]) -> Optional[str]:
        """Validate standard_concept is 'S', 'C', or null (relaxed for legacy data)."""
        # Relaxed validation - warn but don't fail on unexpected values
        return v


class ConceptExpressionItem(BaseModel):
    """Represents an item in a concept set expression.

    Renamed from ConceptSetItem for clarity - this is an item within an expression,
    not a concept set itself.

    Java equivalent: org.ohdsi.circe.vocabulary.ConceptSetExpression.ConceptSetItem (inner class)

    New schema makes includeMapped required. We default to False for backward compatibility
    with legacy JSON files that don't have this field.
    """

    concept: Concept
    is_excluded: bool = Field(default=False, alias="isExcluded")
    include_descendants: bool = Field(default=False, alias="includeDescendants")
    include_mapped: bool = Field(default=False, alias="includeMapped")

    model_config = ConfigDict(populate_by_name=True)


# Maintain backward compatibility alias
ConceptSetItem = ConceptExpressionItem


class ConceptSetExpression(BaseModel):
    """Represents a concept set expression - the logical query definition.

    Java equivalent: org.ohdsi.circe.vocabulary.ConceptSetExpression

    Note: isExcluded, includeMapped, includeDescendants may not be present in all Java JSONs
    (they're sometimes only on the items), so we provide defaults.
    """

    concept: Optional[Concept] = None
    is_excluded: bool = Field(default=False, alias="isExcluded")
    include_mapped: bool = Field(default=False, alias="includeMapped")
    include_descendants: bool = Field(default=False, alias="includeDescendants")
    items: Optional[list[ConceptExpressionItem]] = None

    model_config = ConfigDict(populate_by_name=True)


class ConceptSet(BaseModel):
    """A named collection of concepts with metadata.

    Java equivalent: org.ohdsi.circe.cohortdefinition.ConceptSet

    Supports both legacy and new OHDSI concept set schema formats.
    New schema adds audit fields, tags, metadata, and tool tracking.
    """

    id: int = Field(
        alias="id",
        validation_alias=AliasChoices("id", "ID"),
        description="Unique identifier for the concept set",
    )

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        alias="name",
        validation_alias=AliasChoices("name", "NAME"),
        description="Human-readable name for the concept set",
    )

    expression: Optional[ConceptSetExpression] = Field(
        default=None,
        alias="expression",
        validation_alias=AliasChoices("expression", "EXPRESSION"),
        description="The logical expression defining which concepts are included",
    )

    # Optional fields for both legacy and new schema
    description: Optional[str] = Field(
        default=None,
        max_length=4000,
        description="Optional detailed description of the concept set purpose and contents",
    )

    # New schema fields (all optional for backward compatibility)
    version: Optional[str] = Field(
        default=None,
        description="Version identifier for the concept set (semantic versioning)",
    )
    created_by: Optional[str] = Field(
        default=None,
        alias="createdBy",
        validation_alias=AliasChoices("createdBy", "created_by"),
        max_length=255,
        description="Username or identifier of the concept set creator",
    )
    created_date: Optional[datetime] = Field(
        default=None,
        alias="createdDate",
        validation_alias=AliasChoices("createdDate", "created_date"),
        description="ISO 8601 timestamp of concept set creation",
    )
    modified_by: Optional[str] = Field(
        default=None,
        alias="modifiedBy",
        validation_alias=AliasChoices("modifiedBy", "modified_by"),
        max_length=255,
        description="Username or identifier of the last modifier",
    )
    modified_date: Optional[datetime] = Field(
        default=None,
        alias="modifiedDate",
        validation_alias=AliasChoices("modifiedDate", "modified_date"),
        description="ISO 8601 timestamp of last modification",
    )
    created_by_tool: Optional[str] = Field(
        default=None,
        alias="createdByTool",
        validation_alias=AliasChoices("createdByTool", "created_by_tool"),
        max_length=255,
        description="Name and version of the tool used to create the concept set",
    )
    modified_by_tool: Optional[str] = Field(
        default=None,
        alias="modifiedByTool",
        validation_alias=AliasChoices("modifiedByTool", "modified_by_tool"),
        max_length=255,
        description="Name and version of the tool used for the last modification",
    )
    tags: Optional[list[str]] = Field(
        default=None,
        description="Optional array of tags for categorization",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional additional metadata",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: Optional[str]) -> Optional[str]:
        """Validate semantic versioning pattern if provided (relaxed for legacy compatibility)."""
        # Relaxed - allow any version string for backward compatibility
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate tags if provided."""
        if v is not None:
            for tag in v:
                if not tag or len(tag) > 100:
                    raise ValueError(f"Each tag must be 1-100 characters, got: {tag}")
        return v


# Forward references will be resolved when all classes are imported
ConceptSet.model_rebuild()
