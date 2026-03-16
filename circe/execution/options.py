"""Execution options for backend-native cohort execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

SchemaName = Union[str, tuple[str, str]]


@dataclass(frozen=True)
class ExecutionOptions:
    """Runtime options for backend execution via ibis.

    This API is experimental and may evolve while execution parity is built out.
    """

    cdm_schema: SchemaName | None = None
    vocabulary_schema: SchemaName | None = None
    result_schema: SchemaName | None = None

    cohort_id: int | None = None

    materialize_stages: bool = False
    materialize_codesets: bool = True
    temp_emulation_schema: SchemaName | None = None

    capture_sql: bool = False
    profile_dir: str | None = None


def schema_to_str(schema: SchemaName | None) -> str | None:
    """Normalize schema names to a string representation."""
    if schema is None:
        return None
    if isinstance(schema, tuple):
        return ".".join(schema)
    return schema
