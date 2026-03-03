from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Dict

import ibis.expr.types as ir

from ...cohortdefinition.criteria import Criteria
from ..build_context import BuildContext

from ...extensions import get_registry


def get_builder(criteria: Criteria):
    name = criteria.__class__.__name__
    builder = get_registry().get_ibis_builder(name)
    if not builder:
        raise NotImplementedError(f"Ibis execution not implemented for criteria: {name}")
    return builder


def build_events(criteria: Criteria, ctx: BuildContext) -> ir.Table:
    builder = get_builder(criteria)
    table = builder(criteria, ctx)
    cache_key, label = _criteria_cache_key(criteria)
    return ctx.get_or_materialize_slice(cache_key, table, label=label)


def _criteria_cache_key(criteria: Criteria) -> tuple[str, str]:
    payload = criteria.model_dump_json(
        by_alias=True,
        exclude_defaults=False,
        exclude_none=False,
    )
    raw_key = f"{criteria.__class__.__name__}:{payload}"
    digest = hashlib.sha1(raw_key.encode("utf-8")).hexdigest()[:8]
    label = f"{criteria.__class__.__name__.lower()}_{digest}"
    return raw_key, label
