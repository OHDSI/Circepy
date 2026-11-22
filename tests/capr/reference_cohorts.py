"""R Capr reference cohorts used for parity tests.

Each entry builds the same cohort as the matching block in ``tools/capr_parity.R``.
The JSON those R definitions produce lives in ``tests/capr/fixtures/<name>.json``.
"""

from __future__ import annotations

from collections.abc import Callable

from circe import capr


def t2dm():
    return capr.cs(capr.descendants(201826), name="T2DM")


def heart_failure():
    return capr.cs(capr.descendants(316139), name="HF")


def diabetes():
    return capr.cs(201826, 201254, name="Diabetes")


def _minimal() -> capr.Cohort:
    return capr.cohort(
        entry=capr.entry(capr.condition_occurrence(t2dm()), primary_criteria_limit="First"),
        attrition=capr.attrition(expression_limit="First"),
        exit=capr.exit(capr.observation_exit()),
        era=capr.era(era_days=0),
    )


def _attrs() -> capr.Cohort:
    return capr.cohort(
        entry=capr.entry(
            capr.condition_occurrence(
                t2dm(),
                capr.age(capr.gte(18)),
                capr.male(),
                capr.first_occurrence(),
                capr.start_date(capr.gt("2010-01-01")),
            ),
            primary_criteria_limit="First",
        )
    )


def _two_cs() -> capr.Cohort:
    rule = capr.with_all(
        capr.at_least(
            1,
            capr.condition_occurrence(heart_failure()),
            capr.during_interval(capr.event_starts(-capr.INF, 0)),
        )
    )
    return capr.cohort(
        entry=capr.entry(capr.condition_occurrence(t2dm())),
        attrition=capr.attrition(**{"has hf": rule}, expression_limit="First"),
    )


def _obs_win() -> capr.Cohort:
    return capr.cohort(
        entry=capr.entry(
            capr.condition_occurrence(t2dm()),
            observation_window=capr.continuous_observation(365, 0),
            primary_criteria_limit="All",
        ),
        attrition=capr.attrition(expression_limit="All"),
    )


def _fixed_exit() -> capr.Cohort:
    return capr.cohort(
        entry=capr.entry(capr.condition_occurrence(t2dm())),
        exit=capr.exit(capr.fixed_exit(index="startDate", offset_days=30)),
    )


def _era_180() -> capr.Cohort:
    return capr.cohort(entry=capr.entry(capr.condition_occurrence(t2dm())), era=capr.era(era_days=180))


def _nested() -> capr.Cohort:
    inner = capr.at_least(
        1,
        capr.measurement(heart_failure()),
        capr.during_interval(capr.event_starts(-30, 0)),
    )
    return capr.cohort(entry=capr.entry(capr.drug_exposure(diabetes(), capr.nested_with_all(inner))))


def _censoring() -> capr.Cohort:
    return capr.cohort(
        entry=capr.entry(capr.condition_occurrence(t2dm())),
        exit=capr.exit(capr.observation_exit(), censor=capr.censoring_events(capr.death())),
    )


def _value() -> capr.Cohort:
    return capr.cohort(
        entry=capr.entry(
            capr.measurement(t2dm(), capr.value_as_number(capr.lt(5.7)), capr.measurement_unit(8554))
        )
    )


def _demo() -> capr.Cohort:
    return capr.cohort(
        entry=capr.entry(capr.condition_occurrence(t2dm())),
        attrition=capr.attrition(
            **{"adult males": capr.with_all(capr.male(), capr.age(capr.gte(18)))},
            expression_limit="First",
        ),
    )


def _endwin() -> capr.Cohort:
    criterion = capr.exactly(
        1,
        capr.observation_period(),
        capr.during_interval(capr.event_starts(-capr.INF, -365), capr.event_ends(0, capr.INF)),
    )
    return capr.cohort(
        entry=capr.entry(capr.condition_occurrence(t2dm())),
        attrition=capr.attrition(**{"op": capr.with_all(criterion)}, expression_limit="First"),
    )


def _drug_exit() -> capr.Cohort:
    return capr.cohort(
        entry=capr.entry(capr.drug_exposure(t2dm())),
        exit=capr.exit(capr.drug_exit(t2dm(), persistence_window=30, surveillance_window=7)),
    )


REFERENCE_COHORTS: dict[str, Callable[[], capr.Cohort]] = {
    "minimal": _minimal,
    "attrs": _attrs,
    "two-cs": _two_cs,
    "obs-win": _obs_win,
    "fixed-exit": _fixed_exit,
    "era180": _era_180,
    "nested": _nested,
    "censoring": _censoring,
    "value": _value,
    "demo": _demo,
    "endwin": _endwin,
    "drug-exit": _drug_exit,
}
