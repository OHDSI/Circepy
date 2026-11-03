"""Guards for sqlglot regressions that affect DDL rendering.

sqlglot 30.18.0 and later render ``Drop`` expressions without their table
identifier (e.g. ``DROP TABLE IF EXISTS``), which breaks ibis' Databricks
``create_table(overwrite=True)`` path and circepy's staging cleanup.  The
project pins ``sqlglot<30.18.0``, but environments that installed the
Databricks extra after circepy can end up with a newer version.
"""

from __future__ import annotations

import re

import sqlglot

MAX_SUPPORTED_SQLGLOT = (30, 17, 0)
"""First version known to render ``Drop`` correctly is 30.17.x."""


def sqlglot_version() -> tuple[int, int, int]:
    """Return the installed sqlglot version as a comparable tuple."""
    parts = [int(part) for part in re.findall(r"\d+", sqlglot.__version__)[:3]]
    return tuple(parts + [0] * (3 - len(parts)))[:3]  # type: ignore[return-value]


def require_compatible_sqlglot() -> None:
    """Raise a clear error when the installed sqlglot breaks ibis DDL.

    Raises:
        RuntimeError: If sqlglot >= 30.18.0 is installed.
    """
    installed = sqlglot_version()
    if installed > MAX_SUPPORTED_SQLGLOT:
        raise RuntimeError(
            "Circepy's ibis execution requires sqlglot<30.18.0; installed "
            f"sqlglot=={sqlglot.__version__}. sqlglot >=30.18.0 renders DROP TABLE "
            "statements without the table identifier, which breaks staging cleanup "
            "and Databricks cohort-table writes. Fix with:\n\n"
            '    pip install "sqlglot<30.18.0"\n'
        )


__all__ = ["MAX_SUPPORTED_SQLGLOT", "require_compatible_sqlglot", "sqlglot_version"]
