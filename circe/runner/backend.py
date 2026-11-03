"""Backend connection construction for the runner."""

from __future__ import annotations

import contextlib
import os
from typing import Any

from .payload import BackendConfig


class BackendConfigurationError(ValueError):
    """Raised when a backend cannot be configured from the payload/environment."""


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise BackendConfigurationError(f"Environment variable {name} is required for the configured backend")
    return value


def connect_backend(config: BackendConfig) -> Any:
    """Connect to the configured ibis backend."""
    try:
        import ibis
    except ImportError as exc:  # pragma: no cover - dependency is present in the package extra
        raise BackendConfigurationError(
            "ibis is required; install circepy with the relevant ibis extra"
        ) from exc

    backend_type = config.type.lower()
    if backend_type in {"postgresql", "postgres"}:
        password = _required_env(config.password_env)
        return ibis.postgres.connect(
            host=config.host,
            port=int(config.port),
            database=config.database,
            user=config.user,
            password=password,
        )

    if backend_type == "duckdb":
        return ibis.duckdb.connect(config.duckdb_path, read_only=config.read_only)

    if backend_type == "databricks":
        from ..execution import connect_databricks

        return connect_databricks(
            server_hostname=config.server_hostname,
            http_path=config.http_path,
            personal_access_token=_required_env(config.access_token_env),
            catalog=config.catalog,
            schema=config.schema_name,
        )

    raise BackendConfigurationError(f"Unsupported backend type: {config.type!r}")


def close_backend(backend: Any) -> None:
    """Best-effort connection close."""
    disconnect = getattr(backend, "disconnect", None)
    if callable(disconnect):
        with contextlib.suppress(Exception):  # pragma: no cover - backend-specific cleanup
            disconnect()


__all__ = ["BackendConfigurationError", "close_backend", "connect_backend"]
