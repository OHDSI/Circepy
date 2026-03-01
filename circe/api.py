"""
Simple library API for CIRCE Python

This module provides a simple R CirceR-style API for working with cohort definitions:
- cohort_expression_from_json(): Load cohort expression from JSON string
- build_cohort_query(): Generate SQL from cohort expression
- build_cohort(): Build cohort as a relational expression (experimental)
- write_cohort(): Materialize a cohort relation to a database table
- create_generation_tables(): Initialize generation metadata tables
- generate_cohort(): Generate one cohort with policy/checksum handling
- generate_cohort_set(): Generate multiple cohorts with aggregated statuses
- generate_* supports optional data_version_token for opt-in data-aware invalidation
- get_generated_cohort_status(): Inspect generation/checksum status for a cohort
- apply_subset(): Apply subset operators to a cohort relation
- generate_subset(): Generate a subset cohort with dependency-aware checksums
- get_generated_cohort_counts(): Get row/person/date metrics for a generated cohort
- validate_generated_cohort(): Validate generated cohort table rows
- cohort_print_friendly(): Generate Markdown from cohort expression
"""

from collections.abc import Iterable
from typing import List, Literal, Optional

from .cohortdefinition import (
    BuildExpressionQueryOptions,
    CohortExpression,
    CohortExpressionQueryBuilder,
    MarkdownRender,
)
from .execution.typing import IbisBackendLike, Table
from .generation.config import (
    CohortSetDefinition,
    GenerationConfig,
    GenerationPolicy,
    GenerationTarget,
    NamedCohortExpression,
)
from .generation.metadata import (
    GeneratedCohortCounts,
    GenerationSetStatus,
    GenerationStatus,
    ValidationResult,
)
from .generation.subsets.definitions import (
    CohortSubsetOperator,
    DemographicSubsetOperator,
    LimitSubsetOperator,
    SubsetDefinition,
)
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
    expression: CohortExpression, options: Optional[BuildExpressionQueryOptions] = None
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
    results_schema: Optional[str] = None,
    options: Optional[BuildExpressionQueryOptions] = None,
) -> Table:
    """Build a cohort as a relational table expression."""
    from .execution import build_cohort as _build_cohort

    return _build_cohort(
        expression,
        backend=backend,
        cdm_schema=cdm_schema,
        results_schema=results_schema,
        options=options,
    )


def write_cohort(
    expression: CohortExpression,
    *,
    backend: IbisBackendLike,
    cdm_schema: str,
    target_table: str,
    results_schema: Optional[str] = None,
    options: Optional[BuildExpressionQueryOptions] = None,
    if_exists: Literal["fail", "replace"] = "fail",
    temporary: bool = False,
) -> None:
    """Build and materialize a cohort relation to a database table."""
    from .execution import write_cohort as _write_cohort

    _write_cohort(
        expression,
        backend=backend,
        cdm_schema=cdm_schema,
        target_table=target_table,
        results_schema=results_schema,
        options=options,
        if_exists=if_exists,
        temporary=temporary,
    )


# Compatibility aliases for transition period.
build_cohort_ibis = build_cohort
write_cohort_ibis = write_cohort


def create_generation_tables(
    *,
    backend: IbisBackendLike,
    config: GenerationConfig,
) -> None:
    """Create generation metadata/checksum tables when missing."""
    from .generation import create_generation_tables as _create_generation_tables

    _create_generation_tables(backend=backend, config=config)


def generate_cohort(
    expression: CohortExpression,
    *,
    backend: IbisBackendLike,
    cohort_id: int,
    config: GenerationConfig,
    cohort_name: Optional[str] = None,
    policy: Optional[GenerationPolicy] = None,
    options: Optional[BuildExpressionQueryOptions] = None,
    data_version_token: Optional[str] = None,
) -> GenerationStatus:
    """Generate one cohort with metadata/checksum policy handling.

    Incremental behavior is definition/dependency-based by default.
    Pass `data_version_token` to opt in to data-version-aware invalidation.
    """
    from .generation import generate_cohort as _generate_cohort

    return _generate_cohort(
        expression,
        backend=backend,
        cohort_id=cohort_id,
        cohort_name=cohort_name,
        config=config,
        policy=policy,
        options=options,
        data_version_token=data_version_token,
    )


def generate_cohort_set(
    cohorts: Iterable[GenerationTarget | NamedCohortExpression] | CohortSetDefinition,
    *,
    backend: IbisBackendLike,
    config: GenerationConfig,
    policy: Optional[GenerationPolicy] = None,
    options: Optional[BuildExpressionQueryOptions] = None,
    cohort_ids: Optional[set[int]] = None,
    cohort_names: Optional[set[str]] = None,
    changed_only: bool = False,
    continue_on_error: bool = False,
    data_version_token: Optional[str] = None,
) -> GenerationSetStatus:
    """Generate a cohort set and return aggregated statuses.

    Incremental behavior is definition/dependency-based by default.
    Pass `data_version_token` to opt in to data-version-aware invalidation.
    `GenerationTarget.options` overrides the shared `options` argument per target.
    """
    from .generation import generate_cohort_set as _generate_cohort_set

    return _generate_cohort_set(
        cohorts,
        backend=backend,
        config=config,
        policy=policy,
        options=options,
        cohort_ids=cohort_ids,
        cohort_names=cohort_names,
        changed_only=changed_only,
        continue_on_error=continue_on_error,
        data_version_token=data_version_token,
    )


def get_generated_cohort_status(
    *,
    backend: IbisBackendLike,
    cohort_id: int,
    config: GenerationConfig,
) -> GenerationStatus:
    """Return generation metadata/checksum status for a cohort."""
    from .generation import get_generated_cohort_status as _get_generated_cohort_status

    return _get_generated_cohort_status(
        backend,
        cohort_id=cohort_id,
        config=config,
    )


def apply_subset(
    relation: Table,
    *,
    backend: IbisBackendLike,
    config: GenerationConfig,
    definition: SubsetDefinition,
) -> Table:
    """Apply a subset definition as a relation transform."""
    from .generation.subsets.api import apply_subset as _apply_subset

    return _apply_subset(
        relation,
        backend=backend,
        config=config,
        definition=definition,
    )


def generate_subset(
    definition: SubsetDefinition,
    *,
    backend: IbisBackendLike,
    generated_cohort_id: int,
    config: GenerationConfig,
    policy: Optional[GenerationPolicy] = None,
    data_version_token: Optional[str] = None,
) -> GenerationStatus:
    """Generate and persist a subset cohort with dependency-aware checksums.

    Incremental behavior is definition/dependency-based by default.
    Pass `data_version_token` to opt in to data-version-aware invalidation.
    """
    from .generation.subsets.api import generate_subset as _generate_subset

    return _generate_subset(
        definition,
        backend=backend,
        generated_cohort_id=generated_cohort_id,
        config=config,
        policy=policy,
        data_version_token=data_version_token,
    )


def get_generated_cohort_counts(
    *,
    backend: IbisBackendLike,
    cohort_id: int,
    config: GenerationConfig,
) -> GeneratedCohortCounts:
    """Return generated cohort row/person/date metrics."""
    from .generation.validate import (
        get_generated_cohort_counts as _get_generated_cohort_counts,
    )

    return _get_generated_cohort_counts(
        backend,
        cohort_id=cohort_id,
        config=config,
    )


def validate_generated_cohort(
    *,
    backend: IbisBackendLike,
    cohort_id: int,
    config: GenerationConfig,
) -> ValidationResult:
    """Validate generated cohort rows and return structured diagnostics."""
    from .generation.validate import validate_generated_cohort as _validate_generated_cohort

    return _validate_generated_cohort(
        backend,
        cohort_id=cohort_id,
        config=config,
    )


def cohort_print_friendly(
    expression: CohortExpression,
    concept_sets: Optional[List[ConceptSet]] = None,
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

    renderer = MarkdownRender(
        concept_sets=concept_sets, include_concept_sets=include_concept_sets
    )
    return renderer.render_cohort_expression(expression, title=title)
