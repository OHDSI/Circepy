from __future__ import annotations

import ibis

from circe.evaluation.models import RubricSet
from circe.execution.api import evaluate_cohort
from circe.execution.typing import IbisBackendLike, Table


def calculate_cohort_metrics(
    rubric_set: RubricSet,
    index_events: Table,
    *,
    backend: IbisBackendLike,
    cdm_schema: str,
    results_schema: str | None = None,
    vocabulary_schema: str | None = None,
) -> Table:
    """
    Calculate Positive Predictive Value (PPV) and Sensitivity estimates for a target cohort
    using a pseudo-gold standard (a sensitive rubric and a specific rubric).

    Returns an Ibis table with metrics: pseudo_fp, pseudo_fn, pseudo_tp, ppv, sensitivity.
    """
    # 1. Evaluate sensitive rubric (proxy for all potential positives)
    sensitive_scores = evaluate_cohort(
        rubric_set.sensitive_rubric,
        index_events,
        ruleset_id=1,  # arbitrary ID for internal use
        backend=backend,
        cdm_schema=cdm_schema,
        results_schema=results_schema,
        vocabulary_schema=vocabulary_schema,
        include_cohort_id=True,
    )

    # 2. Evaluate specific rubric (proxy for definite true positives)
    specific_scores = evaluate_cohort(
        rubric_set.specific_rubric,
        index_events,
        ruleset_id=2,  # arbitrary ID for internal use
        backend=backend,
        cdm_schema=cdm_schema,
        results_schema=results_schema,
        vocabulary_schema=vocabulary_schema,
        include_cohort_id=True,
    )

    # 3. Target cohort population (from index_events)
    # Filter index_events to just the target cohort
    target_cohort_id_expr = ibis.literal(int(rubric_set.target_cohort_id), type="int64")
    target_population = index_events.filter(
        index_events.cohort_definition_id.cast("int64") == target_cohort_id_expr
    )

    # We only care about distinct subject_id for presence in the cohorts
    # Assuming the evaluation rules don't depend on continuous timeline scoring for now,
    # but score > 0 means they matched.

    sens_matches = sensitive_scores.filter(sensitive_scores.score > 0).select("subject_id").distinct()
    spec_matches = specific_scores.filter(specific_scores.score > 0).select("subject_id").distinct()
    target_matches = target_population.select(subject_id=target_population.person_id).distinct()

    # Calculate boolean flags per subject_id in the universe
    # Universe is the union of all subject_ids in sens, spec, or target
    universe = sens_matches.union(spec_matches).union(target_matches).distinct()

    # Create indicator columns
    universe = universe.mutate(
        in_target=universe.subject_id.isin(target_matches.subject_id),
        in_sensitive=universe.subject_id.isin(sens_matches.subject_id),
        in_specific=universe.subject_id.isin(spec_matches.subject_id),
    )

    # Define proxies
    # Pseudo-TP: In target AND in specific
    # Pseudo-FP: In target BUT NOT in sensitive
    # Pseudo-FN: NOT in target BUT IN specific

    universe = universe.mutate(
        pseudo_tp=(ibis._.in_target & ibis._.in_specific).cast("int32"),
        pseudo_fp=(ibis._.in_target & ~ibis._.in_sensitive).cast("int32"),
        pseudo_fn=(~ibis._.in_target & ibis._.in_specific).cast("int32"),
    )

    metrics = universe.aggregate(
        target_cohort_id=target_cohort_id_expr,
        pseudo_tp=ibis._.pseudo_tp.sum(),
        pseudo_fp=ibis._.pseudo_fp.sum(),
        pseudo_fn=ibis._.pseudo_fn.sum(),
    )

    ppv = (metrics.pseudo_tp + metrics.pseudo_fp > 0).ifelse(
        metrics.pseudo_tp / (metrics.pseudo_tp + metrics.pseudo_fp), ibis.literal(None, type="float64")
    )

    sensitivity = (metrics.pseudo_tp + metrics.pseudo_fn > 0).ifelse(
        metrics.pseudo_tp / (metrics.pseudo_tp + metrics.pseudo_fn), ibis.literal(None, type="float64")
    )

    metrics = metrics.mutate(
        ppv=ppv,
        sensitivity=sensitivity,
    )

    return metrics
