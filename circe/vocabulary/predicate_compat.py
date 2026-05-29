"""
Compatibility layer and resolution manifest for concept predicate items.

Provides import/export between extended predicate format and traditional
OHDSI concept set JSON, plus resolution manifest generation.

GUARD RAIL: This is a Python-only extension. There is no Java CIRCE-BE equivalent.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from pydantic import BaseModel

from circe.vocabulary.concept import (
    Concept,
    ConceptExpressionItem,
    ConceptSetExpression,
)
from circe.vocabulary.predicate_item import ConceptPredicateItem
from circe.vocabulary.predicate_resolver import ConceptSetResolver
from circe.vocabulary.predicate_sql_compiler import PredicateSQLCompiler


class ItemResolution(BaseModel):
    item_index: int
    item_type: str
    item_name: str | None = None
    is_excluded: bool = False
    resolved_count: int = 0
    compiled_sql: str | None = None


class ResolutionManifest(BaseModel):
    concept_set_id: int = 0
    concept_set_name: str = ""
    resolved_at: datetime = datetime.now(timezone.utc)
    vocabulary_version: str = ""
    total_concept_count: int = 0
    concept_ids_hash: str = ""
    items_resolved: list[ItemResolution] = []


class ConceptSetCompat:
    """Compatibility utilities for concept sets with predicate items."""

    @staticmethod
    def from_ohdsi_json(ohdsi_items: list[dict]) -> ConceptSetExpression:
        """Import a traditional OHDSI concept set expression (ATLAS/WebAPI format).

        Each entry becomes a ConceptExpressionItem. No predicate items are created.
        """
        items: list[ConceptExpressionItem] = []
        for entry in ohdsi_items:
            concept_data = entry.get("concept", {})
            mapping = {
                "CONCEPT_ID": concept_data.get("CONCEPT_ID"),
                "CONCEPT_NAME": concept_data.get("CONCEPT_NAME"),
                "VOCABULARY_ID": concept_data.get("VOCABULARY_ID"),
                "CONCEPT_CODE": concept_data.get("CONCEPT_CODE"),
                "CONCEPT_CLASS_ID": concept_data.get("CONCEPT_CLASS_ID"),
                "STANDARD_CONCEPT": concept_data.get("STANDARD_CONCEPT"),
                "DOMAIN_ID": concept_data.get("DOMAIN_ID"),
            }
            mapping = {k: v for k, v in mapping.items() if v is not None}
            concept = Concept.model_validate(mapping)
            item = ConceptExpressionItem(
                type="concept_item",
                concept=concept,
                isExcluded=entry.get("isExcluded", False),
                includeDescendants=entry.get("includeDescendants", False),
                includeMapped=entry.get("includeMapped", False),
            )
            items.append(item)
        return ConceptSetExpression(items=items)

    @staticmethod
    def to_ohdsi_json(
        concept_set: ConceptSetExpression,
        resolver: ConceptSetResolver,
    ) -> list[dict]:
        """Materialize an extended concept set to traditional OHDSI format.

        Resolves all predicate items, then emits each concept_id as a simple
        ConceptExpressionItem (no descendants, no mapped — already expanded).
        """
        resolved = resolver.resolve(concept_set)

        items: list[dict] = []
        for cid in sorted(resolved):
            items.append(
                {
                    "concept": {"CONCEPT_ID": cid},
                    "isExcluded": False,
                    "includeDescendants": False,
                    "includeMapped": False,
                }
            )
        return items

    @staticmethod
    def is_traditional(concept_set: ConceptSetExpression) -> bool:
        """Check if a concept set contains only traditional items (no predicates)."""
        if not concept_set.items:
            return True
        return not any(isinstance(item, ConceptPredicateItem) for item in concept_set.items)


class ManifestGenerator:
    """Generate a resolution manifest for audit trail purposes."""

    def __init__(self, compiler: PredicateSQLCompiler | None = None):
        self.compiler = compiler

    def generate(
        self,
        concept_set: ConceptSetExpression,
        resolver: ConceptSetResolver,
        vocabulary_version: str = "",
    ) -> ResolutionManifest:
        """Resolve a concept set and produce a full manifest."""
        resolved = resolver.resolve(concept_set)
        sorted_ids = sorted(resolved)
        id_hash = hashlib.sha256(",".join(str(i) for i in sorted_ids).encode()).hexdigest()

        items_resolved: list[ItemResolution] = []
        if concept_set.items:
            for i, item in enumerate(concept_set.items):
                resolved_set = resolver.resolve_item(item)
                sql = None
                if self.compiler and isinstance(item, ConceptPredicateItem):
                    try:
                        sql = self.compiler.compile_expression(item.expression)
                    except Exception:
                        sql = None
                items_resolved.append(
                    ItemResolution(
                        item_index=i,
                        item_type="concept_predicate_item"
                        if isinstance(item, ConceptPredicateItem)
                        else "concept_item",
                        item_name=getattr(item, "name", None),
                        is_excluded=item.is_excluded,
                        resolved_count=len(resolved_set),
                        compiled_sql=sql,
                    )
                )

        return ResolutionManifest(
            concept_set_id=0,
            concept_set_name="",
            resolved_at=datetime.now(timezone.utc),
            vocabulary_version=vocabulary_version,
            total_concept_count=len(sorted_ids),
            concept_ids_hash=id_hash,
            items_resolved=items_resolved,
        )
