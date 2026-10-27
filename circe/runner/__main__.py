"""Command-line/container entry point for the cohort-generation runner."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .payload import RunnerPayload
from .runner import run_cohort_generation


def _read_payload(path: str) -> dict:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--payload",
        default="/payload.json",
        help="Path to the JSON payload, or '-' for stdin (default: /payload.json)",
    )
    parser.add_argument(
        "--prefect",
        action="store_true",
        help="Execute through the Prefect flow instead of calling the runner directly",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        payload_dict = _read_payload(args.payload)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not read payload {args.payload!r}: {exc}", file=sys.stderr)
        return 2

    try:
        if args.prefect:
            from .flow import run_cohort_generation_flow

            result = run_cohort_generation_flow(payload_dict)
        else:
            result = run_cohort_generation(RunnerPayload.model_validate(payload_dict)).to_dict()
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        logging.getLogger(__name__).exception("Cohort generation failed")
        print(f"Cohort generation failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
