"""Content-addressed identity for era-cache features.

Two levels are kept deliberately separate:

``feature_key``
    Identifies the *event selection*: source table, concept set, value class,
    record filters.  It never includes a window, an analysis id or a cohort.
    This is the cache key of the era table.

``read key``
    A window plus an aggregation identifies one column of a feature matrix.  It
    is derived at read time and is not used for storage.

The key excludes display names, local concept-set ids and concept metadata so
that the same selection shares rows across cohorts and runs.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

__all__ = ["era_feature_key", "era_instance_key", "engine_fingerprint"]

ENGINE_VERSION = "0.1.0"

# Bump when the extraction semantics change (columns, dedupe rules, era logic).
ENGINE_FINGERPRINT = hashlib.sha256(
    json.dumps({"engine": "circe.era_cache", "version": ENGINE_VERSION}, sort_keys=True).encode("utf-8")
).hexdigest()[:16]


def _digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def era_feature_key(spec: Any) -> str:
    """Return the content key of a feature's event selection."""
    return f"era_{_digest(spec.canonical_payload())[:16]}"


def era_instance_key(feature_key: str, read_spec: Any) -> str:
    """Return the key for one (window, aggregation) column over a feature."""
    payload = {"feature_key": feature_key, "read": read_spec}
    return f"ins_{_digest(payload)[:16]}"


def engine_fingerprint() -> str:
    return ENGINE_FINGERPRINT
