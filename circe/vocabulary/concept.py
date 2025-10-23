"""
Vocabulary classes for concept management.

This module contains classes for managing concepts, concept sets, and concept set expressions.
"""

from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class Concept(BaseModel):
    """Represents a concept in the OMOP vocabulary.
    
    Java equivalent: org.ohdsi.circe.vocabulary.Concept
    """
    concept_id: int = Field(alias="conceptId")
    concept_name: Optional[str] = Field(default=None, alias="conceptName")
    concept_code: Optional[str] = Field(default=None, alias="conceptCode")
    concept_class_id: Optional[str] = Field(default=None, alias="conceptClassId")
    standard_concept: Optional[str] = Field(default=None, alias="standardConcept")
    invalid_reason: Optional[str] = Field(default=None, alias="invalidReason")
    domain_id: Optional[str] = Field(default=None, alias="domainId")
    vocabulary_id: Optional[str] = Field(default=None, alias="vocabularyId")
    # Java-specific fields for 1:1 compatibility
    false: Optional[Any] = None  # return type
    other: Optional['Concept'] = None
    true: Optional[Any] = None  # return type

    model_config = ConfigDict(populate_by_name=True)


class ConceptSetItem(BaseModel):
    """Represents an item in a concept set.
    
    Java equivalent: org.ohdsi.circe.vocabulary.ConceptSetItem
    """
    concept: Optional[Concept] = None
    is_excluded: Optional[bool] = Field(default=None, alias="isExcluded")
    include_mapped: Optional[bool] = Field(default=None, alias="includeMapped")
    include_descendants: Optional[bool] = Field(default=None, alias="includeDescendants")

    model_config = ConfigDict(populate_by_name=True)


class ConceptSetExpression(BaseModel):
    """Represents a concept set expression.
    
    Java equivalent: org.ohdsi.circe.vocabulary.ConceptSetExpression
    """
    concept: Optional[Concept] = None
    is_excluded: bool = Field(alias="isExcluded")
    other: Optional[ConceptSetItem] = None
    include_mapped: bool = Field(alias="includeMapped")
    json_mapper: Optional[Any] = Field(default=None, alias="JSON_MAPPER")
    include_descendants: bool = Field(alias="includeDescendants")
    items: Optional[List[ConceptSetItem]] = None
    # Java-specific fields for 1:1 compatibility
    true: Optional[Any] = None  # return type
    false: Optional[Any] = None  # return type

    model_config = ConfigDict(populate_by_name=True)


class ConceptSet(BaseModel):
    """Represents a concept set.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.ConceptSet
    """
    id: int
    name: Optional[str] = None
    expression: Optional[ConceptSetExpression] = None
    other: Optional['ConceptSet'] = None
    true: Optional[Any] = None  # return type
    false: Optional[Any] = None  # return type


# Forward references will be resolved when all classes are imported
ConceptSet.model_rebuild()
