"""Validated payload for the cohort-generation runner."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BackendConfig(BaseModel):
    """Database connection description.

    Secrets are always read from environment variables, never from the payload.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["postgresql", "postgres", "duckdb", "databricks"]
    host: str = "localhost"
    port: int = 5432
    database: str | None = None
    user: str | None = None
    password_env: str = "PGPASSWORD"

    duckdb_path: str = ":memory:"
    read_only: bool = False

    server_hostname: str | None = None
    http_path: str | None = None
    access_token_env: str = "DATABRICKS_TOKEN"
    catalog: str | None = None
    schema_name: str | None = Field(default=None, alias="schema")


class TargetConfig(BaseModel):
    """Where cohort rows and (optionally) definitions are persisted."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_name: str = Field(alias="schema")
    table: str = "cohort"
    registry_table: str | None = "cohort_definition_registry"
    reuse_existing: bool = True
    on_definition_change: Literal["error", "replace"] = "error"


class DefinitionSource(BaseModel):
    """Legacy CohortGenerator definition layout, mounted into the container."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    settings_file: str = "Cohorts.csv"
    json_folder: str = "cohorts"
    sql_folder: str | None = "sql/sql_server"
    base_dir: str | None = None
    cohort_file_name_format: str = "%s"
    cohort_file_name_value: list[str] = Field(default_factory=lambda: ["cohortId"])
    family_column: str = "family"
    families: list[str] | None = None
    cohort_ids: list[int] | None = None
    include_sql: bool = True
    sql_required: bool = False
    unsupported: Literal["error", "skip"] = "error"


class RunnerPayload(BaseModel):
    """Complete request for a cohort-generation run."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    cdm_schema: str
    vocabulary_schema: str | None = None
    target: TargetConfig
    definitions: DefinitionSource = Field(default_factory=DefinitionSource)
    backend: BackendConfig
    shared: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_backend(self) -> RunnerPayload:
        backend = self.backend
        if backend.type in {"postgresql", "postgres"}:
            if not backend.database:
                raise ValueError("backend.database is required for PostgreSQL")
            if not backend.user:
                raise ValueError("backend.user is required for PostgreSQL")
        elif backend.type == "databricks":
            if not backend.server_hostname or not backend.http_path:
                raise ValueError("backend.server_hostname and backend.http_path are required for Databricks")
        return self

    @property
    def results_schema(self) -> str:
        return self.target.schema_name
