from __future__ import annotations

from ...cohortdefinition.core import CollapseSettings
from .._dataclass import frozen_slots_dataclass


@frozen_slots_dataclass
class NormalizedCollapseSettings:
    era_pad: int
    collapse_type: str


def normalize_collapse_settings(
    value: CollapseSettings | None,
) -> NormalizedCollapseSettings | None:
    if value is None:
        return None
    collapse_type = "era"
    if value.collapse_type is not None:
        collapse_type = str(value.collapse_type).lower()
    return NormalizedCollapseSettings(
        era_pad=int(value.era_pad),
        collapse_type=collapse_type,
    )
