"""Command-line/container entry point for the cohort-generation runner."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .payload import RunnerPayload
from .runner import run_cached_cohort_generation
from .sharding import run_sharded_cohort_generation, write_shard_manifest


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
        "--shards",
        type=int,
        default=1,
        help="Split cohort families across this many shard workers (default: 1)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=10,
        help="Maximum concurrent shard processes (default: 10)",
    )
    parser.add_argument(
        "--shard-retries",
        type=int,
        default=2,
        help="Retries per shard on generation failure (default: 2)",
    )
    parser.add_argument(
        "--plan-shards",
        metavar="PATH",
        help="Write a shard manifest and exit without generating cohorts",
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
        payload = RunnerPayload.model_validate(payload_dict)
        if args.plan_shards:
            destination = write_shard_manifest(
                payload,
                args.plan_shards,
                shard_count=args.shards,
            )
            print(json.dumps({"shard_manifest": str(destination), "shards": args.shards}))
            return 0

        if args.shards > 1:
            if args.prefect:
                from .flow import run_sharded_cohort_generation_flow

                result = run_sharded_cohort_generation_flow(
                    payload_dict,
                    shard_count=args.shards,
                    max_workers=args.max_workers,
                    shard_retries=args.shard_retries,
                )
            else:
                result = run_sharded_cohort_generation(
                    payload,
                    shard_count=args.shards,
                    max_workers=args.max_workers,
                    retries=args.shard_retries,
                ).to_dict()
        elif args.prefect:
            from .flow import run_cohort_generation_flow

            result = run_cohort_generation_flow(payload_dict)
        else:
            result = run_cached_cohort_generation(payload).to_dict()
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        logging.getLogger(__name__).exception("Cohort generation failed")
        print(f"Cohort generation failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
