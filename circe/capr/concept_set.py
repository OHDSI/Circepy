"""Concept sets with Capr-compatible identity.

R's Capr gives every concept set a content-derived id: the md5 of an
R-serialized payload built from the concepts' flags, with ``TRUE``/``FALSE``
stringification. Keeping the same derivation means a concept set built here has
the same identity as the one built in R, which matters when the two are used
side by side.

The id is *internal* to this layer. It is replaced by a dense ``0..n-1``
``CodesetId`` when the definition is compiled to a :class:`CohortExpression`,
because CIRCE requires integer ids.
"""

from __future__ import annotations

import hashlib
import struct
import warnings
from dataclasses import dataclass, field
from typing import Any

from ..vocabulary.concept import Concept, ConceptSetItem

__all__ = ["ConceptSpec", "CaprConceptSet", "cs", "descendants", "exclude", "mapped"]

_MALE_CONCEPT_ID = 8507
_FEMALE_CONCEPT_ID = 8532


def _r_logical(value: bool) -> str:
    """R stringifies logicals as ``TRUE``/``FALSE``, not ``True``/``False``."""
    return "TRUE" if value else "FALSE"


def _r_serialize_v2_body(text: str) -> bytes:
    """Reproduce the bytes hashed by R's ``digest::digest()`` default.

    ``digest()`` serializes its input (version 2) and then skips the 14-byte
    header (``set_skip()``), so the hashed payload for a length-1 character
    vector is the fixed prefix below followed by the UTF-8 string.
    """
    raw = text.encode("utf-8")
    return (
        b"\x00\x00\x00\x10"  # XCHARSXP marker
        + b"\x00\x00\x00\x01"  # length
        + b"\x00\x04"  # STRSXP type marker
        + b"\x00"  # length continuation
        + b"\x09"  # CHARSXP
        + struct.pack(">i", len(raw))
        + raw
    )


@dataclass(frozen=True)
class ConceptSpec:
    """A ``cs()`` argument that carries modifiers (descendants/exclude/mapped)."""

    kind: str
    ids: tuple[Any, ...]

    def __iter__(self) -> Any:
        return iter(self.ids)


def _spec(kind: str, ids: tuple[Any, ...]) -> ConceptSpec:
    """Build a spec, keeping nested specs intact so modifiers compose."""
    return ConceptSpec(kind, tuple(i if isinstance(i, ConceptSpec) else int(i) for i in ids))


def descendants(*ids: Any) -> ConceptSpec:
    """Include the descendants of each concept id."""
    return _spec("descendants", ids)


def exclude(*ids: Any) -> ConceptSpec:
    """Exclude each concept id. Exclusion does not imply descendants or mapped."""
    return _spec("exclude", ids)


def mapped(*ids: Any) -> ConceptSpec:
    """Include mapped source concepts for each concept id."""
    return _spec("mapped", ids)


@dataclass(frozen=True)
class CaprConceptSet:
    """A concept set with a Capr-compatible content id.

    ``id`` is the md5 of the sorted ``(concept_id, isExcluded,
    includeDescendants, includeMapped)`` payload. It deliberately ignores
    ``name``, matching Capr 3.0, so two sets with identical contents collapse
    into one when a definition is compiled.
    """

    name: str
    items: tuple[ConceptSetItem, ...] = field(default_factory=tuple)

    @property
    def id(self) -> str:
        """Content-derived identity, independent of item order and name."""
        payload = "".join(
            sorted(
                f"{item.concept.concept_id}"
                f"{_r_logical(item.is_excluded)}"
                f"{_r_logical(item.include_descendants)}"
                f"{_r_logical(item.include_mapped)}"
                for item in self.items
                if item.concept.concept_id is not None
            )
        )
        return hashlib.md5(_r_serialize_v2_body(payload)).hexdigest()  # noqa: S324

    def __len__(self) -> int:
        return len(self.items)

    def __bool__(self) -> bool:
        return bool(self.items)

    def __repr__(self) -> str:
        return f"CaprConceptSet(name={self.name!r}, items={len(self.items)})"

    @classmethod
    def from_concept_set(cls, concept_set: Any) -> CaprConceptSet:
        """Adapt a :class:`circe.vocabulary.concept.ConceptSet` to this layer."""
        expression = getattr(concept_set, "expression", None)
        raw_items = getattr(expression, "items", None) or []
        return cls(
            name=getattr(concept_set, "name", None) or "",
            items=tuple(raw_items),
        )


def _concept(concept_id: int, **kwargs: Any) -> Concept:
    return Concept(CONCEPT_ID=int(concept_id), **kwargs)


def cs(*args: Any, name: str) -> CaprConceptSet:
    """Create a concept set.

    Accepts bare concept ids, :func:`descendants`/:func:`exclude`/``mapped``
    (nestable, e.g. ``exclude(descendants(mapped(5)))``), :class:`ConceptSpec`,
    and pre-built :class:`ConceptSetItem` objects.
    """
    specs: list[tuple[int, bool, bool, bool]] = []

    def expand(arg: Any, excluded: bool = False, desc: bool = False, mapped_: bool = False) -> None:
        if isinstance(arg, ConceptSpec):
            ex = excluded or arg.kind == "exclude"
            d = desc or arg.kind == "descendants"
            m = mapped_ or arg.kind == "mapped"
            for inner in arg.ids:
                expand(inner, ex, d, m)
        elif isinstance(arg, ConceptSetItem):
            cid = arg.concept.concept_id
            if cid is not None:
                specs.append((cid, arg.is_excluded, arg.include_descendants, arg.include_mapped))
        elif isinstance(arg, bool):
            raise TypeError("cs() takes concept ids, not booleans")
        elif isinstance(arg, int):
            if arg < 0:
                raise ValueError(
                    f"concept ids must be positive (got {arg}); use exclude({abs(arg)}) to exclude a concept"
                )
            specs.append((arg, excluded, desc, mapped_))
        elif arg is None:
            return
        else:
            raise TypeError(f"cs() does not accept {type(arg).__name__}")

    for arg in args:
        expand(arg)

    seen: set[int] = set()
    duplicates: list[int] = []
    for cid, *_ in specs:
        if cid in seen:
            duplicates.append(cid)
        seen.add(cid)
    if duplicates:
        joined = ", ".join(str(d) for d in sorted(set(duplicates)))
        warnings.warn(f"ID: {joined} are duplicated in the concept set.", stacklevel=2)

    items = tuple(
        ConceptSetItem(
            concept=_concept(cid),
            is_excluded=excluded,
            include_descendants=desc,
            include_mapped=mapped,
        )
        for cid, excluded, desc, mapped in specs
    )
    return CaprConceptSet(name=name, items=items)
