from __future__ import annotations

PERSON_ID = "person_id"
EVENT_ID = "event_id"
START_DATE = "start_date"
END_DATE = "end_date"
VISIT_OCCURRENCE_ID = "visit_occurrence_id"
VISIT_DETAIL_ID = "visit_detail_id"
DOMAIN = "domain"
CONCEPT_ID = "concept_id"
SOURCE_CONCEPT_ID = "source_concept_id"
QUANTITY = "quantity"
DAYS_SUPPLY = "days_supply"
REFILLS = "refills"
RANGE_LOW = "range_low"
RANGE_HIGH = "range_high"
VALUE_AS_NUMBER = "value_as_number"
UNIT_CONCEPT_ID = "unit_concept_id"
OCCURRENCE_COUNT = "occurrence_count"
GAP_DAYS = "gap_days"
DURATION = "duration"
CRITERION_INDEX = "criterion_index"
CRITERION_TYPE = "criterion_type"
SOURCE_TABLE = "source_table"

STANDARD_EVENT_COLUMNS = (
    PERSON_ID,
    EVENT_ID,
    START_DATE,
    END_DATE,
    DOMAIN,
    CONCEPT_ID,
    SOURCE_CONCEPT_ID,
    VISIT_OCCURRENCE_ID,
    VISIT_DETAIL_ID,
    QUANTITY,
    DAYS_SUPPLY,
    REFILLS,
    RANGE_LOW,
    RANGE_HIGH,
    VALUE_AS_NUMBER,
    UNIT_CONCEPT_ID,
    OCCURRENCE_COUNT,
    GAP_DAYS,
    DURATION,
    CRITERION_INDEX,
    CRITERION_TYPE,
    SOURCE_TABLE,
)
