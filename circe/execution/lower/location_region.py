from __future__ import annotations

from ..normalize.criteria import NormalizedCriterion
from ..plan.events import (
    EventPlan,
    EventSource,
    FilterByCodeset,
    FilterByText,
    JoinLocationRegion,
    StandardizeEventShape,
)


def lower_location_region(
    criterion: NormalizedCriterion,
    *,
    criterion_index: int,
) -> EventPlan:
    steps = [
        FilterByText(column="domain_id", op="eq", text="PERSON"),
        JoinLocationRegion(location_id_column="location_id", region_column="region_concept_id"),
    ]
    if criterion.codeset_id is not None:
        steps.append(
            FilterByCodeset(column="region_concept_id", codeset_id=int(criterion.codeset_id))
        )
    steps.append(
        StandardizeEventShape(
            criterion_type=criterion.criterion_type,
            criterion_index=criterion_index,
        )
    )

    return EventPlan(
        source=EventSource(
            table_name=criterion.source_table,
            domain=criterion.domain,
            event_id_column=criterion.event_id_column,
            start_date_column=criterion.start_date_column,
            end_date_column=criterion.end_date_column,
            person_id_column="entity_id",
            concept_column=criterion.concept_column,
            source_concept_column=criterion.source_concept_column,
            visit_occurrence_column=criterion.visit_occurrence_column,
        ),
        criterion_type=criterion.criterion_type,
        criterion_index=criterion_index,
        steps=tuple(steps),
    )
