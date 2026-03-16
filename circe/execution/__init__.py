"""Experimental backend execution APIs."""

from .cohort_definition_set import CohortDefinitionMember, CohortDefinitionSet
from .cohort_generator import CohortGenerator, GenerationResult, SetGenerationResult
from .hash_utils import compute_definition_hash, compute_set_hash
from .ibis import (
    IbisExecutor,
    build_ibis,
    generate_cohort,
    generate_cohort_set,
    generate_many,
    to_polars,
    write_cohort,
)
from .options import ExecutionOptions, SchemaName
from .registry import (
    CohortGenerationRegistry,
    CohortRunRecord,
    InMemoryRegistry,
    SetMemberRecord,
    SetRunRecord,
)

__all__ = [
    "ExecutionOptions",
    "SchemaName",
    "IbisExecutor",
    "build_ibis",
    "to_polars",
    "write_cohort",
    "generate_cohort",
    "generate_cohort_set",
    "generate_many",
    "CohortGenerator",
    "GenerationResult",
    "SetGenerationResult",
    "CohortDefinitionMember",
    "CohortDefinitionSet",
    "compute_definition_hash",
    "compute_set_hash",
    "CohortGenerationRegistry",
    "InMemoryRegistry",
    "CohortRunRecord",
    "SetRunRecord",
    "SetMemberRecord",
]
