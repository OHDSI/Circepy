from __future__ import annotations

from typing import Any

from ...cohortdefinition.core import CustomEraStrategy, DateOffsetStrategy, EndStrategy
from .._dataclass import frozen_slots_dataclass


@frozen_slots_dataclass
class NormalizedEndStrategy:
    kind: str
    payload: dict[str, Any]


def normalize_end_strategy(
    value: EndStrategy | DateOffsetStrategy | CustomEraStrategy | None,
) -> NormalizedEndStrategy | None:
    if value is None:
        return None
    if isinstance(value, DateOffsetStrategy):
        return NormalizedEndStrategy(
            kind="date_offset",
            payload={
                "offset": int(value.offset),
                "date_field": str(value.date_field),
            },
        )
    if isinstance(value, CustomEraStrategy):
        return NormalizedEndStrategy(
            kind="custom_era",
            payload={
                "drug_codeset_id": value.drug_codeset_id,
                "offset": int(value.offset),
                "gap_days": int(value.gap_days),
                "days_supply_override": (
                    None if value.days_supply_override is None else int(value.days_supply_override)
                ),
            },
        )
    return NormalizedEndStrategy(kind="end_strategy", payload={})
