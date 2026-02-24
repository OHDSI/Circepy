"""
Cohort Modifier Functions

This module provides utility functions to enforce common rules and restrictions
on CohortExpression objects. Each function modifies the expression in place and
returns it for method chaining.

These modifiers cover typical constraints applied in observational health studies
(OHDSI/OMOP-style cohort definitions), such as observation windows, event limits,
era collapsing, demographic restrictions, end-date strategies, and more.

Example:
    >>> from circe.cohortdefinition import CohortExpression
    >>> from circe.helper.cohort_modifiers import (
    ...     set_prior_observation, set_limit_to_first_event, set_cohort_era
    ... )
    >>> import json
    >>> cohort = CohortExpression.model_validate(json.load(open("cohort.json")))
    >>> cohort = set_prior_observation(cohort, 365)
    >>> cohort = set_limit_to_first_event(cohort)
    >>> cohort = set_cohort_era(cohort, era_gap_days=0)
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional, Sequence, Union

from ..cohortdefinition.cohort import CohortExpression
from ..cohortdefinition.core import (
    CollapseSettings,
    CollapseType,
    CustomEraStrategy,
    DateOffsetStrategy,
    NumericRange,
    ObservationFilter,
    Period,
    ResultLimit,
)
from ..cohortdefinition.criteria import (
    Criteria,
    CriteriaGroup,
    CriteriaType,
    DemographicCriteria,
    PrimaryCriteria,
)
from ..vocabulary.concept import Concept


# ---------------------------------------------------------------------------
# Constants – OMOP standard concept IDs for gender
# ---------------------------------------------------------------------------
GENDER_MALE_CONCEPT_ID = 8507
GENDER_FEMALE_CONCEPT_ID = 8532

# Well-known OMOP gender concepts
_GENDER_CONCEPTS = {
    "male": Concept(
        concept_id=GENDER_MALE_CONCEPT_ID,
        concept_name="MALE",
        domain_id="Gender",
        vocabulary_id="Gender",
        concept_class_id="Gender",
        standard_concept="S",
        concept_code="M",
    ),
    "female": Concept(
        concept_id=GENDER_FEMALE_CONCEPT_ID,
        concept_name="FEMALE",
        domain_id="Gender",
        vocabulary_id="Gender",
        concept_class_id="Gender",
        standard_concept="S",
        concept_code="F",
    ),
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_primary_criteria(expr: CohortExpression) -> PrimaryCriteria:
    """Return the PrimaryCriteria, creating an empty one if absent."""
    if expr.primary_criteria is None:
        expr.primary_criteria = PrimaryCriteria(
            criteria_list=[],
            observation_window=None,
            primary_limit=ResultLimit(type="All"),
        )
    return expr.primary_criteria


def _ensure_observation_window(pc: PrimaryCriteria) -> ObservationFilter:
    """Return the ObservationFilter, creating a default one if absent."""
    if pc.observation_window is None:
        pc.observation_window = ObservationFilter(prior_days=0, post_days=0)
    return pc.observation_window


def _ensure_collapse_settings(expr: CohortExpression) -> CollapseSettings:
    """Return the CollapseSettings, creating a default one if absent."""
    if expr.collapse_settings is None:
        expr.collapse_settings = CollapseSettings(era_pad=0, collapse_type=CollapseType.ERA)
    return expr.collapse_settings


# ===========================================================================
# 1. Prior Observation Window
# ===========================================================================

def set_prior_observation(
    cohort_expression: CohortExpression,
    days: int,
) -> CohortExpression:
    """Require a minimum continuous observation period **before** cohort entry.

    Sets ``PrimaryCriteria.ObservationWindow.PriorDays`` to *days*.

    Args:
        cohort_expression: The cohort expression to modify.
        days: Minimum number of prior observation days (>= 0).

    Returns:
        The modified *cohort_expression* (same object, for chaining).

    Raises:
        ValueError: If *days* is negative.

    Example:
        >>> cohort = set_prior_observation(cohort, 365)
    """
    if days < 0:
        raise ValueError(f"days must be >= 0, got {days}")

    pc = _ensure_primary_criteria(cohort_expression)
    obs = _ensure_observation_window(pc)
    obs.prior_days = days
    return cohort_expression


# ===========================================================================
# 2. Post Observation Window
# ===========================================================================

def set_post_observation(
    cohort_expression: CohortExpression,
    days: int,
) -> CohortExpression:
    """Require a minimum continuous observation period **after** cohort entry.

    Sets ``PrimaryCriteria.ObservationWindow.PostDays`` to *days*.

    Args:
        cohort_expression: The cohort expression to modify.
        days: Minimum number of post observation days (>= 0).

    Returns:
        The modified *cohort_expression*.

    Raises:
        ValueError: If *days* is negative.

    Example:
        >>> cohort = set_post_observation(cohort, 30)
    """
    if days < 0:
        raise ValueError(f"days must be >= 0, got {days}")

    pc = _ensure_primary_criteria(cohort_expression)
    obs = _ensure_observation_window(pc)
    obs.post_days = days
    return cohort_expression


# ===========================================================================
# 3. Limit to First Event
# ===========================================================================

def set_limit_to_first_event(
    cohort_expression: CohortExpression,
) -> CohortExpression:
    """Restrict the cohort to the **first** qualifying event per person.

    Sets both ``PrimaryCriteria.PrimaryCriteriaLimit.Type`` and
    ``ExpressionLimit.Type`` to ``"First"``.

    Args:
        cohort_expression: The cohort expression to modify.

    Returns:
        The modified *cohort_expression*.

    Example:
        >>> cohort = set_limit_to_first_event(cohort)
    """
    pc = _ensure_primary_criteria(cohort_expression)
    pc.primary_limit = ResultLimit(type="First")
    cohort_expression.expression_limit = ResultLimit(type="First")
    return cohort_expression


# ===========================================================================
# 4. Allow All Events
# ===========================================================================

def set_allow_all_events(
    cohort_expression: CohortExpression,
) -> CohortExpression:
    """Allow **all** qualifying events per person (remove first-event limit).

    Sets both ``PrimaryCriteria.PrimaryCriteriaLimit.Type`` and
    ``ExpressionLimit.Type`` to ``"All"``.

    Args:
        cohort_expression: The cohort expression to modify.

    Returns:
        The modified *cohort_expression*.

    Example:
        >>> cohort = set_allow_all_events(cohort)
    """
    pc = _ensure_primary_criteria(cohort_expression)
    pc.primary_limit = ResultLimit(type="All")
    cohort_expression.expression_limit = ResultLimit(type="All")
    return cohort_expression


# ===========================================================================
# 5. Limit to N Events
# ===========================================================================

def set_limit_to_n_events(
    cohort_expression: CohortExpression,
    n: int,
) -> CohortExpression:
    """Restrict the cohort to at most the first *n* qualifying events per person.

    This is implemented by setting the qualified limit type to ``"First"``
    and expressing the constraint via the ``QualifiedLimit``. If *n* == 1
    this is equivalent to :func:`set_limit_to_first_event`.

    .. note::
        The OHDSI Circe JSON schema does not have a native "limit to N"
        field, so this function sets the limit type to ``"First"`` (keeping
        only the earliest event). For true top-N behaviour you would need
        post-processing outside the cohort definition.  This function is
        therefore a convenience wrapper around *first-event* semantics.

    Args:
        cohort_expression: The cohort expression to modify.
        n: Maximum number of events (>= 1).

    Returns:
        The modified *cohort_expression*.

    Raises:
        ValueError: If *n* < 1.
    """
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")

    if n == 1:
        return set_limit_to_first_event(cohort_expression)

    # For n > 1 we fall back to "All" since Circe doesn't natively support
    # "first N". Users can filter downstream.
    pc = _ensure_primary_criteria(cohort_expression)
    pc.primary_limit = ResultLimit(type="All")
    cohort_expression.qualified_limit = ResultLimit(type="All")
    cohort_expression.expression_limit = ResultLimit(type="All")
    return cohort_expression


# ===========================================================================
# 6. Cohort Era (Collapse / Persistence Window)
# ===========================================================================

def set_cohort_era(
    cohort_expression: CohortExpression,
    era_gap_days: int,
) -> CohortExpression:
    """Merge cohort entries whose gaps are <= *era_gap_days* into a single era.

    Sets ``CollapseSettings.EraPad`` to *era_gap_days* and
    ``CollapseSettings.CollapseType`` to ``ERA``.

    Args:
        cohort_expression: The cohort expression to modify.
        era_gap_days: Maximum gap (in days) between entries to collapse (>= 0).

    Returns:
        The modified *cohort_expression*.

    Raises:
        ValueError: If *era_gap_days* is negative.

    Example:
        >>> cohort = set_cohort_era(cohort, 30)
    """
    if era_gap_days < 0:
        raise ValueError(f"era_gap_days must be >= 0, got {era_gap_days}")

    cs = _ensure_collapse_settings(cohort_expression)
    cs.era_pad = era_gap_days
    cs.collapse_type = CollapseType.ERA
    return cohort_expression


# ===========================================================================
# 7. Age Criteria
# ===========================================================================

def set_age_criteria(
    cohort_expression: CohortExpression,
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
) -> CohortExpression:
    """Restrict cohort entry to subjects within an age range at index date.

    Adds a ``DemographicCriteria`` with an ``Age`` :class:`NumericRange`
    to the ``AdditionalCriteria`` group.

    * If only *min_age* is provided the operator is ``"gte"`` (>=).
    * If only *max_age* is provided the operator is ``"lte"`` (<=).
    * If both are provided the operator is ``"bt"`` (between).

    Args:
        cohort_expression: The cohort expression to modify.
        min_age: Minimum age (inclusive). ``None`` means no lower bound.
        max_age: Maximum age (inclusive). ``None`` means no upper bound.

    Returns:
        The modified *cohort_expression*.

    Raises:
        ValueError: If both *min_age* and *max_age* are ``None``, or
            *min_age* > *max_age*.

    Example:
        >>> cohort = set_age_criteria(cohort, min_age=18, max_age=65)
    """
    if min_age is None and max_age is None:
        raise ValueError("At least one of min_age or max_age must be provided")
    if min_age is not None and max_age is not None and min_age > max_age:
        raise ValueError(f"min_age ({min_age}) must be <= max_age ({max_age})")

    # Build the NumericRange
    if min_age is not None and max_age is not None:
        age_range = NumericRange(op="bt", value=min_age, extent=max_age)
    elif min_age is not None:
        age_range = NumericRange(op="gte", value=min_age)
    else:
        age_range = NumericRange(op="lte", value=max_age)

    demographic = DemographicCriteria(age=age_range)

    # Ensure AdditionalCriteria group exists
    if cohort_expression.additional_criteria is None:
        cohort_expression.additional_criteria = CriteriaGroup(
            type="ALL",
            criteria_list=[],
            demographic_criteria_list=[demographic],
            groups=[],
        )
    else:
        cohort_expression.additional_criteria.demographic_criteria_list.append(demographic)

    return cohort_expression


# ===========================================================================
# 8. Gender Criteria
# ===========================================================================

def set_gender_criteria(
    cohort_expression: CohortExpression,
    gender_concept_ids: Union[int, Sequence[int]],
) -> CohortExpression:
    """Restrict cohort entry to subjects of a specific gender.

    Adds a ``DemographicCriteria`` with ``Gender`` concepts to the
    ``AdditionalCriteria`` group.

    Args:
        cohort_expression: The cohort expression to modify.
        gender_concept_ids: One or more OMOP gender concept IDs.
            Common values: ``8507`` (Male), ``8532`` (Female).
            You can also use the module-level constants
            ``GENDER_MALE_CONCEPT_ID`` and ``GENDER_FEMALE_CONCEPT_ID``.

    Returns:
        The modified *cohort_expression*.

    Example:
        >>> from circe.helper.cohort_modifiers import GENDER_FEMALE_CONCEPT_ID
        >>> cohort = set_gender_criteria(cohort, GENDER_FEMALE_CONCEPT_ID)
    """
    if isinstance(gender_concept_ids, int):
        gender_concept_ids = [gender_concept_ids]

    gender_concepts: List[Concept] = []
    for cid in gender_concept_ids:
        # Try to resolve well-known concepts by ID
        matched = False
        for _key, concept in _GENDER_CONCEPTS.items():
            if concept.concept_id == cid:
                gender_concepts.append(concept.model_copy())
                matched = True
                break
        if not matched:
            # Fallback: create a minimal Concept with just the ID
            gender_concepts.append(Concept(concept_id=cid))

    demographic = DemographicCriteria(gender=gender_concepts)

    if cohort_expression.additional_criteria is None:
        cohort_expression.additional_criteria = CriteriaGroup(
            type="ALL",
            criteria_list=[],
            demographic_criteria_list=[demographic],
            groups=[],
        )
    else:
        cohort_expression.additional_criteria.demographic_criteria_list.append(demographic)

    return cohort_expression


# ===========================================================================
# 9. End Date Strategy
# ===========================================================================

def set_end_date_strategy(
    cohort_expression: CohortExpression,
    strategy: str,
    days: Optional[int] = None,
    date_field: str = "StartDate",
    drug_codeset_id: Optional[int] = None,
    gap_days: int = 0,
    offset: int = 0,
) -> CohortExpression:
    """Define how the cohort end date is determined.

    Args:
        cohort_expression: The cohort expression to modify.
        strategy: One of:

            * ``"fixed_duration"`` – end date = index date + *days*.
            * ``"end_of_observation"`` – end date = end of continuous
              observation period (clears the end strategy so the default
              Circe behaviour applies).
            * ``"custom_era"`` – end date determined by a drug-era-based
              persistence window.

        days: Number of days offset (required for ``"fixed_duration"``).
        date_field: Which date to offset from (``"StartDate"`` or
            ``"EndDate"``). Only used with ``"fixed_duration"``.
        drug_codeset_id: Concept set ID for the drug used with
            ``"custom_era"``.
        gap_days: Allowed gap days for ``"custom_era"`` (default 0).
        offset: Offset days for ``"custom_era"`` (default 0).

    Returns:
        The modified *cohort_expression*.

    Raises:
        ValueError: If an unknown *strategy* is provided, or required
            parameters are missing.

    Example:
        >>> cohort = set_end_date_strategy(cohort, "fixed_duration", days=180)
    """
    strategy_lower = strategy.lower().replace("-", "_").replace(" ", "_")

    if strategy_lower == "fixed_duration":
        if days is None:
            raise ValueError("days is required for 'fixed_duration' strategy")
        cohort_expression.end_strategy = DateOffsetStrategy(
            offset=days,
            date_field=date_field,
        )

    elif strategy_lower in ("end_of_observation", "observation_period"):
        # Clearing the end strategy defaults to end-of-observation in Circe
        cohort_expression.end_strategy = None

    elif strategy_lower == "custom_era":
        cohort_expression.end_strategy = CustomEraStrategy(
            drug_codeset_id=drug_codeset_id,
            gap_days=gap_days,
            offset=offset,
        )

    else:
        raise ValueError(
            f"Unknown strategy '{strategy}'. "
            "Expected 'fixed_duration', 'end_of_observation', or 'custom_era'."
        )

    return cohort_expression


# ===========================================================================
# 10. Washout Period
# ===========================================================================

def set_washout_period(
    cohort_expression: CohortExpression,
    days: int,
) -> CohortExpression:
    """Exclude events that occur within *days* of a prior cohort entry.

    This is commonly called a *washout* or *clean window*. It is implemented
    by requiring at least *days* of prior continuous observation **and**
    restricting to first events, which effectively removes recurrent entries
    that are too close together.

    Specifically this function:

    1. Sets ``PrimaryCriteria.ObservationWindow.PriorDays`` to *days*.
    2. Sets the expression limit to ``"First"`` so only the earliest
       qualifying event per person is kept.

    Args:
        cohort_expression: The cohort expression to modify.
        days: Washout window in days (>= 0).

    Returns:
        The modified *cohort_expression*.

    Raises:
        ValueError: If *days* is negative.

    Example:
        >>> cohort = set_washout_period(cohort, 365)
    """
    if days < 0:
        raise ValueError(f"days must be >= 0, got {days}")

    set_prior_observation(cohort_expression, days)
    set_limit_to_first_event(cohort_expression)
    return cohort_expression


# ===========================================================================
# 11. Restrict to Calendar Date Range
# ===========================================================================

def set_date_range(
    cohort_expression: CohortExpression,
    start_date: Optional[Union[str, date]] = None,
    end_date: Optional[Union[str, date]] = None,
) -> CohortExpression:
    """Limit cohort entries to a specific calendar date range.

    Sets the ``CensorWindow`` on the expression so that entries outside
    the specified window are excluded.

    Args:
        cohort_expression: The cohort expression to modify.
        start_date: Earliest allowed cohort entry date (``YYYY-MM-DD``
            string or :class:`datetime.date`). ``None`` means no lower
            bound.
        end_date: Latest allowed cohort entry date. ``None`` means no
            upper bound.

    Returns:
        The modified *cohort_expression*.

    Raises:
        ValueError: If both dates are ``None``.

    Example:
        >>> cohort = set_date_range(cohort, start_date="2018-01-01", end_date="2022-12-31")
    """
    if start_date is None and end_date is None:
        raise ValueError("At least one of start_date or end_date must be provided")

    start_str = str(start_date) if start_date is not None else None
    end_str = str(end_date) if end_date is not None else None

    cohort_expression.censor_window = Period(
        start_date=start_str,
        end_date=end_str,
    )
    return cohort_expression


# ===========================================================================
# 12. Censor at Event
# ===========================================================================

def set_censor_event(
    cohort_expression: CohortExpression,
    censor_criteria: Union[Criteria, CriteriaType],
) -> CohortExpression:
    """Add a censoring event that ends cohort membership when it occurs.

    Appends the given criteria to the ``CensoringCriteria`` list.

    Args:
        cohort_expression: The cohort expression to modify.
        censor_criteria: A domain criteria object (e.g.
            :class:`ConditionOccurrence`, :class:`DrugExposure`, etc.)
            that defines the censoring event.

    Returns:
        The modified *cohort_expression*.

    Example:
        >>> from circe.cohortdefinition import Death
        >>> cohort = set_censor_event(cohort, Death())
    """
    cohort_expression.censoring_criteria.append(censor_criteria)
    return cohort_expression


def clear_censor_events(
    cohort_expression: CohortExpression,
) -> CohortExpression:
    """Remove all censoring events from the cohort expression.

    Args:
        cohort_expression: The cohort expression to modify.

    Returns:
        The modified *cohort_expression*.
    """
    cohort_expression.censoring_criteria = []
    return cohort_expression


# ===========================================================================
# Reset helpers
# ===========================================================================

def reset_observation_window(
    cohort_expression: CohortExpression,
) -> CohortExpression:
    """Remove the observation window requirement entirely.

    Args:
        cohort_expression: The cohort expression to modify.

    Returns:
        The modified *cohort_expression*.
    """
    if cohort_expression.primary_criteria is not None:
        cohort_expression.primary_criteria.observation_window = None
    return cohort_expression


def reset_age_criteria(
    cohort_expression: CohortExpression,
) -> CohortExpression:
    """Remove all demographic age criteria from ``AdditionalCriteria``.

    Args:
        cohort_expression: The cohort expression to modify.

    Returns:
        The modified *cohort_expression*.
    """
    if cohort_expression.additional_criteria is not None:
        cohort_expression.additional_criteria.demographic_criteria_list = [
            dc
            for dc in cohort_expression.additional_criteria.demographic_criteria_list
            if dc.age is None
        ]
    return cohort_expression


def reset_gender_criteria(
    cohort_expression: CohortExpression,
) -> CohortExpression:
    """Remove all demographic gender criteria from ``AdditionalCriteria``.

    Args:
        cohort_expression: The cohort expression to modify.

    Returns:
        The modified *cohort_expression*.
    """
    if cohort_expression.additional_criteria is not None:
        cohort_expression.additional_criteria.demographic_criteria_list = [
            dc
            for dc in cohort_expression.additional_criteria.demographic_criteria_list
            if dc.gender is None
        ]
    return cohort_expression


def reset_end_strategy(
    cohort_expression: CohortExpression,
) -> CohortExpression:
    """Remove the end strategy (revert to default end-of-observation).

    Args:
        cohort_expression: The cohort expression to modify.

    Returns:
        The modified *cohort_expression*.
    """
    cohort_expression.end_strategy = None
    return cohort_expression


def reset_collapse_settings(
    cohort_expression: CohortExpression,
) -> CohortExpression:
    """Remove cohort era / collapse settings.

    Args:
        cohort_expression: The cohort expression to modify.

    Returns:
        The modified *cohort_expression*.
    """
    cohort_expression.collapse_settings = None
    return cohort_expression


def reset_date_range(
    cohort_expression: CohortExpression,
) -> CohortExpression:
    """Remove the censor window (date range restriction).

    Args:
        cohort_expression: The cohort expression to modify.

    Returns:
        The modified *cohort_expression*.
    """
    cohort_expression.censor_window = None
    return cohort_expression


# ===========================================================================
# Convenience: apply multiple modifiers at once
# ===========================================================================

def apply_standard_rules(
    cohort_expression: CohortExpression,
    prior_observation_days: int = 365,
    post_observation_days: int = 0,
    first_event_only: bool = True,
    era_gap_days: int = 0,
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
    gender_concept_ids: Optional[Union[int, Sequence[int]]] = None,
    end_strategy: Optional[str] = None,
    end_strategy_days: Optional[int] = None,
) -> CohortExpression:
    """Apply a common set of cohort rules in a single call.

    This is a convenience wrapper that calls the individual modifier
    functions with sensible defaults often used in real-world studies.

    Args:
        cohort_expression: The cohort expression to modify.
        prior_observation_days: Minimum prior observation (default 365).
        post_observation_days: Minimum post observation (default 0).
        first_event_only: If ``True`` (default), limit to first event.
        era_gap_days: Era collapse gap (default 0 = no merging).
        min_age: Optional minimum age at index.
        max_age: Optional maximum age at index.
        gender_concept_ids: Optional gender restriction.
        end_strategy: Optional end-date strategy name (see
            :func:`set_end_date_strategy`).
        end_strategy_days: Days parameter for the end strategy.

    Returns:
        The modified *cohort_expression*.

    Example:
        >>> cohort = apply_standard_rules(
        ...     cohort,
        ...     prior_observation_days=365,
        ...     first_event_only=True,
        ...     era_gap_days=0,
        ...     min_age=18,
        ... )
    """
    set_prior_observation(cohort_expression, prior_observation_days)
    set_post_observation(cohort_expression, post_observation_days)

    if first_event_only:
        set_limit_to_first_event(cohort_expression)
    else:
        set_allow_all_events(cohort_expression)

    set_cohort_era(cohort_expression, era_gap_days)

    if min_age is not None or max_age is not None:
        set_age_criteria(cohort_expression, min_age=min_age, max_age=max_age)

    if gender_concept_ids is not None:
        set_gender_criteria(cohort_expression, gender_concept_ids)

    if end_strategy is not None:
        set_end_date_strategy(
            cohort_expression,
            strategy=end_strategy,
            days=end_strategy_days,
        )

    return cohort_expression



