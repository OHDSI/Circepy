"""Prefect flow/task wrappers for the cohort-generation runner.

Importing this module never requires Prefect.  When Prefect is installed the
functions are real flows/tasks; otherwise they are plain pass-through
decorators, which keeps the CLI and tests usable in the base environment.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, TypeVar

from .payload import RunnerPayload
from .runner import run_cohort_generation
from .sharding import run_sharded_cohort_generation

logger = logging.getLogger(__name__)
T = TypeVar("T")


def _identity_decorator(*dargs: Any, **dkwargs: Any) -> Any:
    if len(dargs) == 1 and callable(dargs[0]) and not dkwargs:
        return dargs[0]

    def decorate(function: Callable[..., T]) -> Callable[..., T]:
        return function

    return decorate


try:  # pragma: no cover - exercised only when the prefect extra is installed
    from prefect import flow as _prefect_flow
    from prefect import task as _prefect_task

    PREFECT_AVAILABLE = True
except ImportError:  # pragma: no cover - default in the core test environment
    _prefect_flow = _identity_decorator  # type: ignore[assignment]
    _prefect_task = _identity_decorator  # type: ignore[assignment]
    PREFECT_AVAILABLE = False


@_prefect_task(name="validate-cohort-generation-payload", retries=1)
def validate_payload_task(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a serialized runner payload."""
    return RunnerPayload.model_validate(payload).model_dump(mode="json", by_alias=True)


@_prefect_task(name="generate-cohort-definition-set", retries=0)
def generate_cohort_set_task(payload: dict[str, Any]) -> dict[str, Any]:
    """Run the cohort-generation job."""
    validated = RunnerPayload.model_validate(payload)
    return run_cohort_generation(validated).to_dict()


@_prefect_task(name="generate-cohort-definition-set-shards", retries=0)
def generate_sharded_cohort_set_task(
    payload: dict[str, Any],
    *,
    shard_count: int,
    max_workers: int,
    shard_retries: int,
) -> dict[str, Any]:
    """Run a family-sharded cohort-generation job."""
    validated = RunnerPayload.model_validate(payload)
    return run_sharded_cohort_generation(
        validated,
        shard_count=shard_count,
        max_workers=max_workers,
        retries=shard_retries,
    ).to_dict()


@_prefect_flow(name="circe-cohort-generation-sharded", log_prints=True)
def run_sharded_cohort_generation_flow(
    payload: dict[str, Any],
    *,
    shard_count: int = 10,
    max_workers: int = 10,
    shard_retries: int = 2,
) -> dict[str, Any]:
    """Prefect entry point for family-balanced, multi-process sharding."""
    validated = validate_payload_task(payload)
    return generate_sharded_cohort_set_task(
        validated,
        shard_count=shard_count,
        max_workers=max_workers,
        shard_retries=shard_retries,
    )


@_prefect_flow(name="circe-cohort-generation", log_prints=True)
def run_cohort_generation_flow(payload: dict[str, Any]) -> dict[str, Any]:
    """Prefect entry point.

    Args:
        payload: Serialized :class:`RunnerPayload` (aliases such as ``schema``
            are accepted).

    Returns:
        The runner result as a JSON-serializable dictionary.
    """
    validated = validate_payload_task(payload)
    return generate_cohort_set_task(validated)


__all__ = [
    "PREFECT_AVAILABLE",
    "generate_cohort_set_task",
    "generate_sharded_cohort_set_task",
    "run_cohort_generation_flow",
    "run_sharded_cohort_generation_flow",
    "validate_payload_task",
]
