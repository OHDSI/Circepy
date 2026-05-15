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


def _expandvars(text: str) -> str:
    """Expand ``${ENV_VAR}`` patterns in *text*, falling back to an empty string."""
    return re.sub(
        r"\$\{(\w+)\}",
        lambda m: os.environ.get(m.group(1), ""),
        text,
    )


def _expandvars_recursive(obj: Any) -> Any:
    """Expand environment variables throughout a nested dict/list."""
    if isinstance(obj, str):
        return _expandvars(obj)
    if isinstance(obj, dict):
        return {k: _expandvars_recursive(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expandvars_recursive(v) for v in obj]
    return obj


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

        conn_cfg = cfg["connection"]
        db_cfg: dict[str, Any] = {
            "host": conn_cfg["server_hostname"],
            "http_path": conn_cfg["http_path"],
        }
        if conn_cfg.get("personal_access_token"):
            db_cfg["token"] = conn_cfg["personal_access_token"]
        if conn_cfg.get("catalog"):
            db_cfg["catalog"] = conn_cfg["catalog"]
        if conn_cfg.get("schema"):
            db_cfg["schema"] = conn_cfg["schema"]

        backend = ibis.databricks.connect(**db_cfg)
        return BackendConnection(
            backend=backend,
            cdm_schema=cfg["cdm_schema"],
            results_schema=cfg["results_schema"],
            vocabulary_schema=cfg.get("vocabulary_schema", cfg["cdm_schema"]),
            r_cohort_table=cfg.get("r_cohort_table", R_COHORT_TABLE),
            py_cohort_table=cfg.get("py_cohort_table", PY_COHORT_TABLE),
            r_checksum_table=cfg.get("r_checksum_table", R_CHECKSUM_TABLE),
            py_checksum_table=cfg.get("py_checksum_table", PY_CHECKSUM_TABLE),
        )

    raise ValueError(f"Unsupported driver: {driver}")
