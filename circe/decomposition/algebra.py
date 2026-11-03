"""Decomposition of a v1 cohort definition set into shared bases + refinements.

A :class:`Decomposition` answers the question *"can cohort B be expressed as
cohort A plus a bounded set of v1-placed edits?"*.  When it can, B is recorded
as ``base + [refinements]`` and ``flatten(B)`` reproduces B's semantics by
construction, while execution can reuse A's checkpoints up to the first touched
stage.

The decomposition is conservative: every candidate relation is validated by
flattening and comparing semantic keys.  A cohort that cannot be reproduced
exactly stays a base, so the invariant

    semantic(flatten(decompose(S))) == semantic(S)

always holds.  Definitions whose concept-set ids already line up also flatten
byte-for-byte (reported as ``exact_definition`` in :meth:`Decomposition.explain`).
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..cohortdefinition import CohortExpression
from ..vocabulary.concept import ConceptSet
from .canonical import (
    ConceptSetCanonicalizer,
    _rewrite_codeset_ids,
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

if TYPE_CHECKING:
    from ..cohort_definition_set._core import CohortDefinitionSet

__all__ = [
    "Decomposition",
    "DerivedCohort",
    "decompose_cohort_set",
]


@dataclass(frozen=True)
class DerivedCohort:
    """A cohort expressed as a base plus an ordered list of refinements."""

    cohort_id: int
    cohort_name: str
    base_id: int
    parent_id: int
    refinements: tuple[Refinement, ...]
    original_expression: CohortExpression = field(repr=False, compare=False)

    @property
    def depth(self) -> int:
        return sum(1 for refinement in self.refinements if refinement.kind != "add_concept_sets")

    def describe(self) -> str:
        operators = ", ".join(refinement.describe() for refinement in self.refinements)
        return f"{self.cohort_name} = base {self.base_id} + [{operators}]"


class Decomposition:
    """A cohort definition set split into bases and derived definitions."""

    def __init__(
        self,
        *,
        bases: Mapping[int, Any],
        derived: Mapping[int, DerivedCohort],
        canonical: Mapping[int, CohortExpression],
        names: Mapping[int, str],
    ) -> None:
        self._bases = dict(bases)
        self._derived = dict(derived)
        self._canonical = dict(canonical)
        self._names = dict(names)

    # -- structure ---------------------------------------------------------
    @property
    def bases(self) -> dict[int, Any]:
        """Base cohort definitions, keyed by cohort id."""
        return dict(self._bases)

    @property
    def derived(self) -> dict[int, DerivedCohort]:
        """Derived cohort nodes, keyed by cohort id."""
        return dict(self._derived)

    def __len__(self) -> int:
        return len(self._bases) + len(self._derived)

    def __iter__(self) -> Iterator[int]:
        return iter([*self._bases, *self._derived])

    def is_base(self, cohort_id: int) -> bool:
        return cohort_id in self._bases

    # -- flattening --------------------------------------------------------
    def flatten(self, cohort_id: int) -> CohortExpression:
        """Return the stand-alone v1 expression for *cohort_id*.

        Bases return their original definition.  Derived cohorts return
        ``base + refinements``, which is semantically identical to the original
        definition and byte-identical when concept-set ids are already aligned.
        """
        if cohort_id in self._bases:
            # Bases are returned verbatim; callers comparing definitions get the
            # exact bytes they supplied.
            return self._bases[cohort_id].expression.model_copy(deep=True)

        node = self._derived.get(cohort_id)
        if node is None:
            raise KeyError(f"Unknown cohort_id={cohort_id} in this decomposition.")

        # Derived cohorts start from the canonicalised base so the refinement
        # payloads (which use canonical concept-set ids) resolve correctly.
        expression = self._canonical[node.base_id].model_copy(deep=True)
        for refinement in node.refinements:
            refinement.apply(expression)
        return expression

    def flatten_all(self) -> CohortDefinitionSet:
        """Return a :class:`CohortDefinitionSet` of flattened definitions."""
        from ..cohort_definition_set._core import CohortDefinitionSet

        cohort_set = CohortDefinitionSet()
        for cohort_id in self:
            cohort_set.add(
                cohort_id=cohort_id,
                cohort_name=self._names.get(cohort_id, str(cohort_id)),
                expression=self.flatten(cohort_id),
            )
        return cohort_set

    # -- verification / reporting -----------------------------------------
    def verify(self) -> list[str]:
        """Return a list of semantic mismatches (empty when the invariant holds)."""
        problems: list[str] = []
        for cohort_id, node in self._derived.items():
            flattened = self.flatten(cohort_id)
            if semantic_expression_key(flattened) != semantic_expression_key(node.original_expression):
                problems.append(
                    f"cohort {cohort_id} ({node.cohort_name}) does not flatten to its original definition"
                )
        return problems

    def _is_exact(self, cohort_id: int) -> bool:
        node = self._derived.get(cohort_id)
        if node is None:
            return True
        flattened = self.flatten(cohort_id)
        return flattened.model_dump(
            by_alias=True, mode="json", exclude_none=True
        ) == node.original_expression.model_dump(by_alias=True, mode="json", exclude_none=True)

    def explain(self) -> dict[str, Any]:
        """Return a machine-readable summary of the decomposition."""
        derived_rows = []
        for cohort_id, node in self._derived.items():
            derived_rows.append(
                {
                    "cohort_id": cohort_id,
                    "cohort_name": node.cohort_name,
                    "base_id": node.base_id,
                    "parent_id": node.parent_id,
                    "depth": node.depth,
                    "refinements": [refinement.to_dict() for refinement in node.refinements],
                    "exact_definition": self._is_exact(cohort_id),
                }
            )

        signature_counts: dict[str, int] = {}
        for cohort_id in self:
            signature = _base_signature(self._canonical[cohort_id])
            signature_counts[signature] = signature_counts.get(signature, 0) + 1

        return {
            "cohorts": len(self),
            "bases": [
                {
                    "cohort_id": cohort_id,
                    "cohort_name": self._names.get(cohort_id, str(cohort_id)),
                    "derived_count": sum(1 for node in self._derived.values() if node.base_id == cohort_id),
                }
                for cohort_id in self._bases
            ],
            "derived": derived_rows,
            "shared_primary_signatures": sum(1 for count in signature_counts.values() if count > 1),
            "primary_checkpoints": len(signature_counts),
            "primary_scans_saved": len(self) - len(signature_counts),
            "all_definitions_semantically_identical": not self.verify(),
            "all_definitions_byte_identical": all(self._is_exact(cohort_id) for cohort_id in self._derived),
        }

    def describe(self) -> str:
        """Return a human-readable summary suitable for logs."""
        summary = self.explain()
        lines = [
            f"Decomposed {summary['cohorts']} cohort(s) into "
            f"{len(summary['bases'])} base(s) and {len(summary['derived'])} derived cohort(s); "
            f"{summary['primary_checkpoints']} shared primary checkpoint(s)."
        ]
        for base in summary["bases"]:
            lines.append(
                f"  base {base['cohort_id']} ({base['cohort_name']}): {base['derived_count']} derived"
            )
        for row in summary["derived"]:
            operators = ", ".join(item["operator"] for item in row["refinements"])
            lines.append(
                f"  cohort {row['cohort_id']} ({row['cohort_name']}) <- base {row['base_id']} [{operators}]"
            )
        if summary["all_definitions_byte_identical"]:
            lines.append("All flattened definitions are byte-identical to the originals.")
        elif summary["all_definitions_semantically_identical"]:
            lines.append(
                "All flattened definitions are semantically identical (concept-set ids canonicalised)."
            )
        return "\n".join(lines)


def _limit_type(expression: CohortExpression, attribute: str) -> str:
    limit = getattr(expression, attribute)
    value = getattr(limit, "type", None)
    return (str(value) if value else "all").lower()


def _is_empty_group(group: Any) -> bool:
    if group is None:
        return True
    return not (
        getattr(group, "criteria_list", None)
        or getattr(group, "demographic_criteria_list", None)
        or getattr(group, "groups", None)
    )


def _base_signature(expression: CohortExpression) -> str:
    primary = expression.primary_criteria
    return stable_digest(
        {
            "primary": primary.model_dump(by_alias=True, mode="json", exclude_none=True)
            if primary is not None
            else None,
            "cdm_version_range": expression.cdm_version_range,
        }
    )


def _complexity(expression: CohortExpression) -> tuple[int, ...]:
    additional = 0 if _is_empty_group(expression.additional_criteria) else 1
    return (
        len(expression.inclusion_rules),
        additional,
        len(expression.censoring_criteria),
        0 if _limit_type(expression, "expression_limit") == "all" else 1,
        0 if _limit_type(expression, "qualified_limit") == "all" else 1,
        0 if expression.end_strategy is None else 1,
        len(expression.concept_sets),
    )


def _align_concept_sets(
    parent: CohortExpression,
    child: CohortExpression,
) -> tuple[dict[int, int], list[ConceptSet]] | None:
    """Map child concept-set ids onto parent ids, collecting genuinely new sets.

    Returns ``None`` when the child is not an additive extension of the parent
    (duplicate ids, or a parent concept set that the child dropped).
    """
    parent_id_by_key: dict[str, int] = {}
    parent_ids: set[int] = set()
    for concept_set in parent.concept_sets:
        parent_ids.add(int(concept_set.id))
        parent_id_by_key.setdefault(concept_set_content_key(concept_set.expression), int(concept_set.id))

    child_ids: set[int] = set()
    mapping: dict[int, int] = {}
    additions: list[ConceptSet] = []
    used_ids = set(parent_ids)
    next_free = max(parent_ids, default=0) + 1

    for concept_set in child.concept_sets:
        child_id = int(concept_set.id)
        if child_id in child_ids:
            return None
        child_ids.add(child_id)

        key = concept_set_content_key(concept_set.expression)
        parent_id = parent_id_by_key.get(key)
        if parent_id is not None:
            mapping[child_id] = parent_id
            continue

        new_id = child_id if child_id not in used_ids else next_free
        if new_id == next_free:
            next_free += 1
        while new_id in used_ids:
            new_id = next_free
            next_free += 1
        used_ids.add(new_id)
        mapping[child_id] = new_id
        addition = concept_set.model_copy(deep=True)
        addition.id = new_id
        additions.append(addition)

    if not set(parent_id_by_key).issubset(
        {concept_set_content_key(cs.expression) for cs in child.concept_sets}
    ):
        # The child dropped (or replaced) a parent concept set; flattening would
        # keep it, so the definitions would no longer be identical.
        return None

    return mapping, additions


def _try_derive(
    parent: CohortExpression,
    child: CohortExpression,
) -> tuple[Refinement, ...] | None:
    """Return the refinements turning *parent* into *child*, or ``None``."""
    aligned_result = _align_concept_sets(parent, child)
    if aligned_result is None:
        return None
    mapping, additions = aligned_result

    aligned = child.model_copy(deep=True)
    _rewrite_codeset_ids(aligned, mapping)

    refinements: list[Refinement] = []
    if additions:
        refinements.append(AddConceptSets(tuple(additions)))

    parent_limit = _limit_type(parent, "qualified_limit")
    child_limit = _limit_type(aligned, "qualified_limit")
    if parent_limit != child_limit:
        if parent_limit != "all":
            return None
        refinements.append(SetQualifiedLimit(aligned.qualified_limit.model_copy(deep=True)))
    elif parent.qualified_limit != aligned.qualified_limit:
        # Same effective limit but different representation is not worth
        # decomposing; keep the child as its own base.
        return None

    if _is_empty_group(parent.additional_criteria):
        if not _is_empty_group(aligned.additional_criteria):
            refinements.append(RequireAtEntry(aligned.additional_criteria.model_copy(deep=True)))
    elif parent.additional_criteria != aligned.additional_criteria:
        return None

    parent_rules = parent.inclusion_rules
    child_rules = aligned.inclusion_rules
    if len(child_rules) < len(parent_rules):
        return None
    for parent_rule, child_rule in zip(parent_rules, child_rules, strict=False):
        if parent_rule != child_rule:
            return None
    for rule in child_rules[len(parent_rules) :]:
        refinements.append(AddInclusionRule(rule.model_copy(deep=True)))

    parent_limit = _limit_type(parent, "expression_limit")
    child_limit = _limit_type(aligned, "expression_limit")
    if parent_limit != child_limit:
        if parent_limit != "all":
            return None
        refinements.append(SetExpressionLimit(aligned.expression_limit.model_copy(deep=True)))
    elif parent.expression_limit != aligned.expression_limit:
        return None

    if parent.end_strategy != aligned.end_strategy:
        refinements.append(
            SetEndStrategy(
                aligned.end_strategy.model_copy(deep=True) if aligned.end_strategy is not None else None
            )
        )

    parent_censoring = parent.censoring_criteria
    child_censoring = aligned.censoring_criteria
    if len(child_censoring) < len(parent_censoring):
        return None
    for parent_criterion, child_criterion in zip(parent_censoring, child_censoring, strict=False):
        if parent_criterion != child_criterion:
            return None
    for criterion in child_censoring[len(parent_censoring) :]:
        refinements.append(AddCensoring(criterion.model_copy(deep=True)))

    if parent.censor_window != aligned.censor_window:
        refinements.append(
            SetCensorWindow(
                aligned.censor_window.model_copy(deep=True) if aligned.censor_window is not None else None
            )
        )

    if parent.collapse_settings != aligned.collapse_settings:
        refinements.append(
            SetCollapse(
                aligned.collapse_settings.model_copy(deep=True)
                if aligned.collapse_settings is not None
                else None
            )
        )

    if parent.title != child.title:
        refinements.append(SetTitle(child.title))

    return tuple(refinements)


def decompose_cohort_set(cohort_definition_set: Any) -> Decomposition:
    """Decompose a cohort definition set into shared bases and refinements.

    Args:
        cohort_definition_set: Any iterable of objects exposing ``cohort_id``,
            ``cohort_name`` and ``expression`` (for example a
            :class:`~circe.cohort_definition_set.CohortDefinitionSet`).

    Returns:
        A :class:`Decomposition` whose ``flatten`` method reproduces every
        input definition (semantically; byte-identically when concept-set ids
        already line up).
    """
    cohorts = list(cohort_definition_set)
    if not cohorts:
        return Decomposition(bases={}, derived={}, canonical={}, names={})

    canonicalizer = ConceptSetCanonicalizer()
    for cohort in cohorts:
        canonicalizer.register_expression(cohort.expression)

    canonical: dict[int, CohortExpression] = {}
    names: dict[int, str] = {}
    for cohort in cohorts:
        canonical[int(cohort.cohort_id)] = canonicalizer.canonicalize(cohort.expression)
        names[int(cohort.cohort_id)] = cohort.cohort_name

    order = sorted(
        cohorts,
        key=lambda cohort: (
            _complexity(canonical[int(cohort.cohort_id)]),
            str(cohort.cohort_name),
            int(cohort.cohort_id),
        ),
    )

    bases: dict[int, Any] = {}
    derived: dict[int, DerivedCohort] = {}
    flat_canonical: dict[int, CohortExpression] = {}
    signatures: dict[int, str] = {}

    for cohort in order:
        cohort_id = int(cohort.cohort_id)
        expression = canonical[cohort_id]
        signature = _base_signature(expression)
        signatures[cohort_id] = signature

        best: tuple[int, int, int, tuple[Refinement, ...]] | None = None
        for candidate_id, candidate_expression in flat_canonical.items():
            if signatures[candidate_id] != signature:
                continue
            refinements = _try_derive(candidate_expression, expression)
            if refinements is None:
                continue
            score = (
                len(refinements),
                derived[candidate_id].depth if candidate_id in derived else 0,
                candidate_id,
                refinements,
            )
            if best is None or score[:3] < best[:3]:
                best = score

        if best is not None:
            _, _, parent_id, refinements = best
            base_id = parent_id if parent_id in bases else derived[parent_id].base_id
            derivations = (derived[parent_id].refinements if parent_id in derived else ()) + refinements
            node = DerivedCohort(
                cohort_id=cohort_id,
                cohort_name=cohort.cohort_name,
                base_id=int(base_id),
                parent_id=int(parent_id),
                refinements=derivations,
                original_expression=cohort.expression,
            )
            # Flatten now: this is both the validation step and the parent
            # expression future siblings will be compared against.
            flattened = flat_canonical[base_id].model_copy(deep=True)
            for refinement in derivations:
                refinement.apply(flattened)
            if semantic_expression_key(flattened) != semantic_expression_key(cohort.expression):
                bases[cohort_id] = cohort
                flat_canonical[cohort_id] = expression
            else:
                derived[cohort_id] = node
                flat_canonical[cohort_id] = flattened
        else:
            bases[cohort_id] = cohort
            flat_canonical[cohort_id] = expression

    return Decomposition(
        bases=bases,
        derived=derived,
        canonical=canonical,
        names=names,
    )
