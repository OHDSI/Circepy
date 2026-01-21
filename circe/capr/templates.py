from typing import Optional, List
from circe.cohort_builder import CohortBuilder
from circe.cohortdefinition import CohortExpression
from circe.vocabulary import ConceptSet


def sensitive_disease_cohort(
    concept_set_id: int,
    title: Optional[str] = None,
    observation_prior_days: int = 0,
    observation_post_days: int = 0,
    concept_sets: Optional[List[ConceptSet]] = None
) -> CohortExpression:
    """
    Create a sensitive disease cohort - all occurrences from a concept set.
    """
    builder = (
        CohortBuilder(title or "Sensitive Disease Cohort")
        .with_condition(concept_set_id)
        .with_observation(prior_days=observation_prior_days, post_days=observation_post_days)
        .all_occurrences()
    )
    
    if concept_sets:
        builder.with_concept_sets(*concept_sets)
        
    return builder.build()


def specific_disease_cohort(
    concept_set_id: int,
    confirmation_days: int = 30,
    inpatient_visit_concept_set_id: Optional[int] = None,
    title: Optional[str] = None,
    observation_prior_days: int = 365,
    concept_sets: Optional[List[ConceptSet]] = None
) -> CohortExpression:
    """
    Create a specific disease cohort requiring confirmation.
    """
    builder = (
        CohortBuilder(title or "Specific Disease Cohort")
        .with_condition(concept_set_id)
        .first_occurrence()
        .with_observation(prior_days=observation_prior_days)
    )
    
    if concept_sets:
        builder.with_concept_sets(*concept_sets)
        
    # confirmation criteria
    builder = builder.require_condition(concept_set_id).within_days_after(confirmation_days)
    
    return builder.build()


def acute_disease_cohort(
    concept_set_id: int,
    washout_days: int = 180,
    title: Optional[str] = None,
    observation_prior_days: int = 0,
    concept_sets: Optional[List[ConceptSet]] = None
) -> CohortExpression:
    """
    Create an acute disease cohort with washout period.
    """
    if observation_prior_days == 0:
        observation_prior_days = washout_days
        
    builder = (
        CohortBuilder(title or "Acute Disease Cohort")
        .with_condition(concept_set_id)
        .all_occurrences()
        .with_observation(prior_days=observation_prior_days)
    )
    
    if concept_sets:
        builder.with_concept_sets(*concept_sets)
        
    builder = builder.exclude_condition(concept_set_id).within_days_before(washout_days)
    
    return builder.build()


def chronic_disease_cohort(
    concept_set_id: int,
    lookback_days: int = 365,
    title: Optional[str] = None,
    concept_sets: Optional[List[ConceptSet]] = None
) -> CohortExpression:
    """
    Create a chronic disease cohort - first ever diagnosis.
    """
    builder = (
        CohortBuilder(title or "Chronic Disease Cohort")
        .with_condition(concept_set_id)
        .first_occurrence()
        .with_observation(prior_days=lookback_days)
    )
    
    if concept_sets:
        builder.with_concept_sets(*concept_sets)
        
    builder = builder.exclude_condition(concept_set_id).anytime_before()
    
    return builder.build()


def new_user_drug_cohort(
    drug_concept_set_id: int,
    washout_days: int = 365,
    indication_concept_set_id: Optional[int] = None,
    indication_lookback_days: int = 365,
    title: Optional[str] = None,
    observation_prior_days: int = 0,
    concept_sets: Optional[List[ConceptSet]] = None
) -> CohortExpression:
    """
    Create a new user drug cohort with clean washout.
    """
    if observation_prior_days == 0:
        observation_prior_days = washout_days
        
    builder = (
        CohortBuilder(title or "New User Drug Cohort")
        .with_drug_era(drug_concept_set_id)
        .first_occurrence()
        .with_observation(prior_days=observation_prior_days)
    )
    
    builder = builder.exclude_drug(drug_concept_set_id).within_days_before(washout_days)
    
    if indication_concept_set_id:
        builder = builder.require_condition(indication_concept_set_id).within_days_before(indication_lookback_days)
        
    if concept_sets:
        builder.with_concept_sets(*concept_sets)
        
    return builder.build()

