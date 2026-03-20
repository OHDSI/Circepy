"""
Simple library API for CIRCE Python

This module provides a simple R CirceR-style API for working with cohort definitions:
- cohort_expression_from_json(): Load cohort expression from JSON string
- build_cohort_query(): Generate SQL from cohort expression
- build_cohort(): Build cohort as a relational expression (experimental)
- write_cohort(): Write OHDSI cohort-table rows to a database table
- cohort_print_friendly(): Generate Markdown from cohort expression
"""

from typing import Literal, Optional

from .cohortdefinition import (
    BuildExpressionQueryOptions,
    CohortExpression,
    CohortExpressionQueryBuilder,
    MarkdownRender,
)
from .evaluation.models import EvaluationRubric, RubricSet
from .execution.typing import IbisBackendLike, Table
from .vocabulary.concept import ConceptSet


def cohort_expression_from_json(json_str: str) -> CohortExpression:
    """Load a cohort expression from a JSON string.

    This is equivalent to R CirceR's `cohortExpressionFromJson()` function.

    Args:
        json_str: JSON string containing the cohort definition

    Returns:
        CohortExpression instance

    Raises:
        ValueError: If the JSON is invalid or doesn't conform to the schema

    Example:
        >>> json_str = '{"ConceptSets": [], "PrimaryCriteria": {...}}'
        >>> expression = cohort_expression_from_json(json_str)
    """
    import json

    # Parse JSON
    data = json.loads(json_str)

    # Handle cdmVersionRange as string
    if "cdmVersionRange" in data and isinstance(data["cdmVersionRange"], str):
        data.pop("cdmVersionRange", None)

    # Handle empty censorWindow
    if "censorWindow" in data and data["censorWindow"] == {}:
        data.pop("censorWindow", None)

    # Ensure ConceptSetExpression objects have required fields
    if "conceptSets" in data and data["conceptSets"]:
        for concept_set in data["conceptSets"]:
            if (
                isinstance(concept_set, dict)
                and "expression" in concept_set
                and concept_set["expression"] is not None
            ):
                expr = concept_set["expression"]
                if isinstance(expr, dict):
                    if "isExcluded" not in expr:
                        expr["isExcluded"] = False
                    if "includeMapped" not in expr:
                        expr["includeMapped"] = False
                    if "includeDescendants" not in expr:
                        expr["includeDescendants"] = False

    try:
        return CohortExpression.model_validate(data)
    except Exception as e:
        raise ValueError(f"Invalid cohort expression JSON: {str(e)}") from e


def build_cohort_query(
    expression: CohortExpression,
    options: Optional[BuildExpressionQueryOptions] = None,
) -> str:
    """Generate SQL query from a cohort expression.

    This is equivalent to R CirceR's `buildCohortQuery()` function.

    Args:
        expression: CohortExpression instance
        options: Build options (schema names, cohort ID, etc.)

    Returns:
        SQL query string

    Example:
        >>> expression = cohort_expression_from_json(json_str)
        >>> options = BuildExpressionQueryOptions()
        >>> options.cdm_schema = "cdm"
        >>> options.target_table = "cohort"
        >>> options.cohort_id = 1
        >>> sql = build_cohort_query(expression, options)
    """
    if options is None:
        options = BuildExpressionQueryOptions()

    builder = CohortExpressionQueryBuilder()
    return builder.build_expression_query(expression, options)


def build_cohort(
    expression: CohortExpression,
    *,
    backend: IbisBackendLike,
    cdm_schema: str,
    vocabulary_schema: Optional[str] = None,
    results_schema: Optional[str] = None,
) -> Table:
    """Build a cohort as a relational table expression.

    This uses the experimental Ibis execution engine to compile the cohort
    expression into a backend-native relational expression.

    Args:
        expression: CohortExpression instance
        backend: Ibis backend used to compile the cohort relation
        cdm_schema: Schema containing the OMOP CDM tables
        vocabulary_schema: Optional schema for vocabulary tables. Defaults to
            ``cdm_schema`` when omitted.
        results_schema: Optional schema used for result-side table resolution

    Returns:
        Ibis table expression representing the cohort result

    Raises:
        ExecutionError: If the cohort cannot be normalized, lowered, or
            compiled into a relational expression

    Example:
        >>> import ibis
        >>> backend = ibis.duckdb.connect()
        >>> expression = cohort_expression_from_json(json_str)
        >>> relation = build_cohort(
        ...     expression,
        ...     backend=backend,
        ...     cdm_schema="cdm",
        ...     vocabulary_schema="vocab",
        ... )
    """
    from .execution import build_cohort as _build_cohort

    return _build_cohort(
        expression,
        backend=backend,
        cdm_schema=cdm_schema,
        vocabulary_schema=vocabulary_schema,
        results_schema=results_schema,
    )


def write_cohort(
    expression: CohortExpression,
    *,
    backend: IbisBackendLike,
    cdm_schema: str,
    cohort_table: str,
    cohort_id: int,
    vocabulary_schema: Optional[str] = None,
    results_schema: Optional[str] = None,
    if_exists: Literal["fail", "replace"] = "fail",
) -> None:
    """Build and write an OHDSI cohort table.

    This wraps :func:`build_cohort`, projects the resulting relation into the
    standard OHDSI cohort-table shape, and materializes it to a backend table.
    Existing rows for other cohort IDs are preserved.

    Args:
        expression: CohortExpression instance
        backend: Ibis backend used to compile and write the cohort relation
        cdm_schema: Schema containing the OMOP CDM tables
        cohort_table: Name of the OHDSI cohort table to create or update
        cohort_id: Cohort definition identifier written to
            ``cohort_definition_id``
        vocabulary_schema: Optional schema for vocabulary tables. Defaults to
            ``cdm_schema`` when omitted.
        results_schema: Optional schema for the target table
        if_exists: Cohort-row policy, either ``"fail"`` or ``"replace"``.
            ``"fail"`` raises if rows for ``cohort_id`` already exist.
            ``"replace"`` replaces only rows for ``cohort_id``.

    Returns:
        None

    Raises:
        ExecutionError: If the cohort cannot be built or the target table
            cannot be written

    Example:
        >>> import ibis
        >>> backend = ibis.duckdb.connect()
        >>> expression = cohort_expression_from_json(json_str)
        >>> write_cohort(
        ...     expression,
        ...     backend=backend,
        ...     cdm_schema="cdm",
        ...     cohort_table="cohort",
        ...     cohort_id=1,
        ...     results_schema="results",
        ...     if_exists="replace",
        ... )
    """
    from .execution import write_cohort as _write_cohort

    _write_cohort(
        expression,
        backend=backend,
        cdm_schema=cdm_schema,
        cohort_table=cohort_table,
        cohort_id=cohort_id,
        vocabulary_schema=vocabulary_schema,
        results_schema=results_schema,
        if_exists=if_exists,
    )


def evaluate_cohort(
    rubric: EvaluationRubric,
    index_events: Table,
    *,
    ruleset_id: int,
    backend: IbisBackendLike,
    cdm_schema: str,
    results_schema: Optional[str] = None,
    vocabulary_schema: Optional[str] = None,
    include_cohort_id: bool = True,
) -> Table:
    """Evaluate an Ibis cohort table using an EvaluationRubric natively.

    Args:
        rubric: EvaluationRubric instance
        index_events: Ibis table representing the cohort to evaluate
        ruleset_id: Identifier for the evaluation run
        backend: Ibis backend used to compile the relation
        cdm_schema: Schema containing the OMOP CDM tables
        results_schema: Optional schema for result-side table resolution
        vocabulary_schema: Optional schema for vocabulary tables
        include_cohort_id: Whether to include cohort_definition_id in output

    Returns:
        Ibis table expression representing the normalized evaluation results.
    """
    from .execution import evaluate_cohort as _evaluate_cohort

    return _evaluate_cohort(
        rubric,
        index_events,
        ruleset_id=ruleset_id,
        backend=backend,
        cdm_schema=cdm_schema,
        results_schema=results_schema,
        vocabulary_schema=vocabulary_schema,
        include_cohort_id=include_cohort_id,
    )


def write_evaluation(
    rubric: EvaluationRubric,
    index_events: Table,
    *,
    ruleset_id: int,
    backend: IbisBackendLike,
    cdm_schema: str,
    target_table: str = "cohort_rubric",
    results_schema: Optional[str] = None,
    vocabulary_schema: Optional[str] = None,
    include_cohort_id: bool = True,
    if_exists: Literal["fail", "replace"] = "fail",
) -> None:
    """Build evaluation rows and materialize them to a backend table.

    Args:
        rubric: EvaluationRubric instance
        index_events: Ibis table representing the cohort to evaluate
        ruleset_id: Identifier for the evaluation run
        backend: Ibis backend used to compile and write the relation
        cdm_schema: Schema containing the OMOP CDM tables
        target_table: Name of the table to create or update (default: cohort_rubric)
        results_schema: Optional schema for result-side table resolution
        vocabulary_schema: Optional schema for vocabulary tables
        include_cohort_id: Whether to include cohort_definition_id in output
        if_exists: Cohort-row policy, either "fail" or "replace"
    """
    from .execution import write_evaluation as _write_evaluation

    _write_evaluation(
        rubric,
        index_events,
        ruleset_id=ruleset_id,
        backend=backend,
        cdm_schema=cdm_schema,
        target_table=target_table,
        results_schema=results_schema,
        vocabulary_schema=vocabulary_schema,
        include_cohort_id=include_cohort_id,
        if_exists=if_exists,
    )


def calculate_cohort_metrics(
    rubric_set: RubricSet,
    index_events: Table,
    *,
    backend: IbisBackendLike,
    cdm_schema: str,
    results_schema: Optional[str] = None,
    vocabulary_schema: Optional[str] = None,
) -> Table:
    """Calculate Positive Predictive Value (PPV) and Sensitivity estimates for a target cohort.

    Args:
        rubric_set: RubricSet containing sensitive and specific proxy rubrics
        index_events: Ibis table representing the cohort evaluation universe
        backend: Ibis backend used to compile the relation
        cdm_schema: Schema containing the OMOP CDM tables
        results_schema: Optional schema for result-side table resolution
        vocabulary_schema: Optional schema for vocabulary tables

    Returns:
        Ibis table expression with target_cohort_id, pseudo_tp, pseudo_fp, pseudo_fn, ppv, sensitivity.
    """
    from .execution import calculate_cohort_metrics as _calculate_cohort_metrics

    return _calculate_cohort_metrics(
        rubric_set,
        index_events,
        backend=backend,
        cdm_schema=cdm_schema,
        results_schema=results_schema,
        vocabulary_schema=vocabulary_schema,
    )


def cohort_print_friendly(
    expression: CohortExpression,
    concept_sets: Optional[list[ConceptSet]] = None,
    title: Optional[str] = None,
    include_concept_sets: bool = False,
) -> str:
    """Generate human-readable Markdown from a cohort expression.

    This is equivalent to R CirceR's `cohortPrintFriendly()` function.

    Args:
        expression: CohortExpression instance
        concept_sets: Optional list of concept sets (uses expression.concept_sets if None)
        include_concept_sets: Whether to include concept set tables in the output (default: False)
        title: Optional title for the output (default: None)
    Returns:
        Markdown string

    Example:
        >>> expression = cohort_expression_from_json(json_str)
        >>> markdown = cohort_print_friendly(expression)
        >>> # Include concept sets in output
        >>> markdown_with_sets = cohort_print_friendly(expression, include_concept_sets=True)
    """
    if concept_sets is None:
        concept_sets = expression.concept_sets or []

    renderer = MarkdownRender(concept_sets=concept_sets, include_concept_sets=include_concept_sets)
    return renderer.render_cohort_expression(expression, title=title)
