"""Shared backend connection helpers for the benchmarks.

Used by both :file:`benchmark_run_py.py` and :file:`benchmark_analyze_duckdb.py`
to connect to DuckDB (local file) or Databricks (via YAML config) uniformly.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import ibis
import yaml

# Optional Databricks support — checked lazily at connect time.
try:
    import ibis.backends.databricks  # noqa: F401

    _HAS_IBIS_DATABRICKS = True
except ImportError:
    _HAS_IBIS_DATABRICKS = False

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "benchmark_output"
CONFIG_PATH = Path(__file__).resolve().parent / "benchmark_db_config.yaml"
DUCKDB_PATH = OUTPUT_DIR / "eunomia.duckdb"

R_COHORT_TABLE = "cohort"
PY_COHORT_TABLE = "cohort_py"
R_CHECKSUM_TABLE = "cohort_checksum"
PY_CHECKSUM_TABLE = "cohort_py_checksum"

# CSV paths
R_CSV = OUTPUT_DIR / "r_checksum_times.csv"
PY_CSV = OUTPUT_DIR / "py_checksum_times.csv"

ENV_PATH = REPO_ROOT / ".env"


def _strip_wrapping_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _load_env_file() -> None:
    """Load repo-local environment variables without overriding the shell."""
    if not ENV_PATH.exists():
        return

    for raw_line in ENV_PATH.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue

        os.environ[key] = _strip_wrapping_quotes(value.strip())


_load_env_file()


def _expandvars(text: str) -> str:
    """Expand ``${ENV_VAR}`` patterns in *text*, falling back to an empty string."""
    return re.sub(
        r"\$\{(\w+)\}",
        lambda m: _get_env_var(m.group(1)),
        text,
    )


def _get_env_var(name: str) -> str:
    """Return an environment variable, including benchmark-specific aliases."""
    value = os.environ.get(name)
    if value:
        return value

    aliases = {
        "DATABRICKS_RESULTS_SCHEMA": "DATABRICKS_SCRATCH_SCHEMA",
    }
    alias = aliases.get(name)
    if alias is None:
        return ""
    return os.environ.get(alias, "")


def _expandvars_recursive(obj: Any) -> Any:
    """Expand environment variables throughout a nested dict/list."""
    if isinstance(obj, str):
        return _expandvars(obj)
    if isinstance(obj, dict):
        return {k: _expandvars_recursive(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expandvars_recursive(v) for v in obj]
    return obj


def _require_config_value(cfg: dict[str, Any], path: tuple[str, ...], env_var: str | None = None) -> str:
    """Return a non-empty configuration value or raise a helpful error."""
    current: Any = cfg
    for key in path:
        if not isinstance(current, dict):
            current = None
            break
        current = current.get(key)

    if isinstance(current, str) and current:
        return current

    dotted = ".".join(path)
    if env_var is not None:
        raise ValueError(
            f"Missing Databricks config value '{dotted}'. Set {env_var} or update {CONFIG_PATH}."
        )
    raise ValueError(f"Missing Databricks config value '{dotted}' in {CONFIG_PATH}.")


def _split_catalog_schema(qualified_schema: str | None) -> tuple[str | None, str | None]:
    """Split a qualified Databricks schema into catalog and schema parts."""
    if not qualified_schema:
        return None, None

    parts = [part for part in qualified_schema.split(".") if part]
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None, parts[0] if parts else None


def _infer_databricks_namespace(cfg: dict[str, Any]) -> tuple[str | None, str | None]:
    """Infer a sensible catalog/schema for the initial Databricks connection."""
    conn_cfg = cfg.get("connection", {})
    if conn_cfg.get("catalog") or conn_cfg.get("schema"):
        return conn_cfg.get("catalog"), conn_cfg.get("schema")

    for key in ("results_schema", "cdm_schema", "vocabulary_schema"):
        catalog, schema = _split_catalog_schema(cfg.get(key))
        if catalog or schema:
            return catalog, schema

    return None, None


@dataclass
class BackendConnection:
    """Hold the configured connection and schema information for a benchmark run."""

    backend: ibis.BaseBackend
    cdm_schema: str
    results_schema: str
    vocabulary_schema: str
    r_cohort_table: str
    py_cohort_table: str
    r_checksum_table: str
    py_checksum_table: str


def load_config(backend_name: str) -> dict[str, Any]:
    """Load the YAML configuration for *backend_name*.

    ``${ENV_VAR}`` placeholders are expanded from the process environment.
    """
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config not found: {CONFIG_PATH}")

    config = yaml.safe_load(CONFIG_PATH.read_text())
    section = config.get(backend_name)
    if section is None:
        available = [k for k in config if k != "eunomia"]
        raise ValueError(f"Unknown backend '{backend_name}'. Available: {', '.join(available)}")

    return _expandvars_recursive(section)


def connect_backend(backend_name: str) -> BackendConnection:
    """Create and return a backend connection from the YAML config.

    For ``duckdb`` the configuration is pre-set (points to the local Eunomia
    DuckDB file).  For ``databricks`` the configuration must be provided in
    :file:`benchmarks/benchmark_db_config.yaml`.
    """
    if backend_name == "duckdb":
        if not DUCKDB_PATH.exists():
            raise FileNotFoundError(
                f"{DUCKDB_PATH} not found. Run 'Rscript benchmarks/benchmark_run_r.R' first."
            )
        backend = ibis.duckdb.connect(str(DUCKDB_PATH))
        return BackendConnection(
            backend=backend,
            cdm_schema="main",
            results_schema="main",
            vocabulary_schema="main",
            r_cohort_table=R_COHORT_TABLE,
            py_cohort_table=PY_COHORT_TABLE,
            r_checksum_table=R_CHECKSUM_TABLE,
            py_checksum_table=PY_CHECKSUM_TABLE,
        )

    cfg = load_config(backend_name)
    driver = cfg.get("driver", backend_name)

    if driver == "databricks":
        if not _HAS_IBIS_DATABRICKS:
            raise ImportError(
                "ibis-framework[databricks] is required. Install with: "
                "pip install 'ibis-framework[databricks]'"
            )

        catalog, schema = _infer_databricks_namespace(cfg)
        db_cfg: dict[str, Any] = {
            "server_hostname": _require_config_value(
                cfg, ("connection", "server_hostname"), env_var="DATABRICKS_HOST"
            ),
            "http_path": _require_config_value(
                cfg, ("connection", "http_path"), env_var="DATABRICKS_HTTP_PATH"
            ),
        }
        token = _require_config_value(
            cfg, ("connection", "personal_access_token"), env_var="DATABRICKS_TOKEN"
        )
        if token:
            db_cfg["access_token"] = token
        if catalog:
            db_cfg["catalog"] = catalog
        if schema:
            db_cfg["schema"] = schema

        backend = ibis.databricks.connect(**db_cfg)
        return BackendConnection(
            backend=backend,
            cdm_schema=_require_config_value(cfg, ("cdm_schema",), env_var="DATABRICKS_CDM_SCHEMA"),
            results_schema=_require_config_value(
                cfg, ("results_schema",), env_var="DATABRICKS_RESULTS_SCHEMA"
            ),
            vocabulary_schema=cfg.get("vocabulary_schema")
            or _require_config_value(cfg, ("cdm_schema",), env_var="DATABRICKS_CDM_SCHEMA"),
            r_cohort_table=cfg.get("r_cohort_table", R_COHORT_TABLE),
            py_cohort_table=cfg.get("py_cohort_table", PY_COHORT_TABLE),
            r_checksum_table=cfg.get("r_checksum_table", R_CHECKSUM_TABLE),
            py_checksum_table=cfg.get("py_checksum_table", PY_CHECKSUM_TABLE),
        )

    raise ValueError(f"Unsupported driver: {driver}")
