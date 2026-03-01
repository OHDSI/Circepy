from __future__ import annotations

from ..config import GenerationConfig
from ..fingerprint import stable_hash
from ..status import get_generated_cohort_status
from .definitions import CohortSubsetOperator, SubsetDefinition


def _referenced_cohort_ids(definition: SubsetDefinition) -> tuple[int, ...]:
    ids = {
        int(operator.subset_cohort_id)
        for operator in definition.operators
        if isinstance(operator, CohortSubsetOperator)
    }
    return tuple(sorted(ids))


def resolve_generation_dependencies(
    backend,
    *,
    definition: SubsetDefinition,
    config: GenerationConfig,
) -> dict:
    parent_status = get_generated_cohort_status(
        backend,
        cohort_id=definition.parent_cohort_id,
        config=config,
    )
    if not parent_status.combined_hash:
        raise RuntimeError(
            "Subset dependency missing: parent cohort "
            f"{definition.parent_cohort_id} has no generation checksum."
        )

    referenced_hashes: dict[str, str] = {}
    for cohort_id in _referenced_cohort_ids(definition):
        status = get_generated_cohort_status(
            backend,
            cohort_id=cohort_id,
            config=config,
        )
        if not status.combined_hash:
            raise RuntimeError(
                "Subset dependency missing: referenced cohort "
                f"{cohort_id} has no generation checksum."
            )
        referenced_hashes[str(cohort_id)] = status.combined_hash

    payload = {
        "parent_cohort_id": int(definition.parent_cohort_id),
        "parent_combined_hash": parent_status.combined_hash,
        "referenced": referenced_hashes,
    }
    return {
        "payload": payload,
        "dependency_hash": stable_hash(payload),
    }
