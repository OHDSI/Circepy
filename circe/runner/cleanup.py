"""Independent cleanup of Circe session/staging tables.

This job is intentionally separate from cohort generation.  Run it on a
schedule (or after a failed job) so orphaned staging tables do not accumulate
against a warehouse's table quota.
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import timedelta
from pathlib import Path

from ..execution.session import cleanup_stale_sessions
from .backend import close_backend, connect_backend
from .payload import RunnerPayload

logger = logging.getLogger(__name__)


def cleanup_sessions(
    payload: RunnerPayload,
    *,
    older_than_days: float = 1.0,
    schema: str | None = None,
) -> dict[str, object]:
    """Drop registered stale sessions in the cache/target schema."""
    target = payload.target
    cleanup_schema = schema or target.cache_schema or target.schema_name
    backend = connect_backend(payload.backend)
    try:
        dropped = cleanup_stale_sessions(
            backend,
            schema=cleanup_schema,
            older_than=timedelta(days=older_than_days),
        )
        return {"schema": cleanup_schema, "dropped": dropped}
    finally:
        close_backend(backend)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", default="/payload.json")
    parser.add_argument("--schema", default=None)
    parser.add_argument("--older-than-days", type=float, default=1.0)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))

    try:
        payload = RunnerPayload.model_validate(json.loads(Path(args.payload).read_text(encoding="utf-8")))
        result = cleanup_sessions(
            payload,
            older_than_days=args.older_than_days,
            schema=args.schema,
        )
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        logger.exception("Cleanup failed")
        print(f"Cleanup failed: {exc}")
        return 1

    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
