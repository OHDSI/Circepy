from __future__ import annotations

from circe.cohortdefinition.criteria import CustomEra
from circe.extensions import lowerer

from ..normalize.criteria import NormalizedCriterion
from ..plan.events import CollapseCustomEra, EventPlan, EventSource


@lowerer(CustomEra)
def lower_custom_era(
    criterion: NormalizedCriterion,
    *,
    criterion_index: int,
) -> EventPlan:
    raw = criterion.raw_criteria

    return EventPlan(
        source=EventSource(
            table_name="custom_era",
            domain=criterion.domain,
            event_id_column=criterion.event_id_column,
            start_date_column=criterion.start_date_column,
            end_date_column=criterion.end_date_column,
        ),
        criterion_type=criterion.criterion_type,
        criterion_index=criterion_index,
        steps=(
            CollapseCustomEra(
                criteria=tuple(raw.criteria_list),
                gap_days=int(raw.gap_days if raw.gap_days is not None else 0),
                criterion=criterion,
            ),
        ),
    )
