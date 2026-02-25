"""
Helper Module

This module contains utility helper classes.
It mirrors the Java CIRCE-BE helper package structure.
"""

from .cohort_modifiers import (
    # Constants
    GENDER_MALE_CONCEPT_ID,
    GENDER_FEMALE_CONCEPT_ID,
    # Modifier functions
    set_prior_observation,
    set_post_observation,
    set_limit_to_first_event,
    set_allow_all_events,
    set_cohort_era,
    set_age_criteria,
    set_gender_criteria,
    set_end_date_strategy,
    set_washout_period,
    set_clean_window,
    set_date_range,
    set_censor_event,
    clear_censor_events,
    # Reset helpers
    reset_observation_window,
    reset_age_criteria,
    reset_gender_criteria,
    reset_end_strategy,
    reset_collapse_settings,
    reset_clean_window,
    reset_date_range,
    # Convenience
    apply_standard_rules,
)

__all__ = [
    # Constants
    "GENDER_MALE_CONCEPT_ID",
    "GENDER_FEMALE_CONCEPT_ID",
    # Modifier functions
    "set_prior_observation",
    "set_post_observation",
    "set_limit_to_first_event",
    "set_allow_all_events",
    "set_cohort_era",
    "set_age_criteria",
    "set_gender_criteria",
    "set_end_date_strategy",
    "set_washout_period",
    "set_clean_window",
    "set_date_range",
    "set_censor_event",
    "clear_censor_events",
    # Reset helpers
    "reset_observation_window",
    "reset_age_criteria",
    "reset_gender_criteria",
    "reset_end_strategy",
    "reset_collapse_settings",
    "reset_clean_window",
    "reset_date_range",
    # Convenience
    "apply_standard_rules",
]
