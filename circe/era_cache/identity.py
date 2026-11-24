"""Cache-generation identity.

A cache generation is identified by the CDM, vocabulary, engine and *scope*
fingerprints.  Feature identity (``feature_key``) deliberately excludes those
fingerprints so a feature keeps its meaning across data refreshes; the rows that
answer it, however, belong to a generation.

When a CDM or vocabulary changes, a new ``cache_key`` is produced.  Old rows stay
in place until explicitly purged, so a rebuild can be validated before the old
generation is dropped.
"""

from __future__ import annotations

import hashlib
import json

from .keys import ENGINE_FINGERPRINT

__all__ = ["cache_key"]

DEFAULT_FINGERPRINT = "unversioned"


def cache_key(
    *,
    cdm_schema: str | None,
    vocabulary_schema: str | None,
    cdm_fingerprint: str | None = None,
    vocab_fingerprint: str | None = None,
    engine_fingerprint: str = ENGINE_FINGERPRINT,
    scope_fingerprint: str = "whole_cdm",
) -> str:
    """Return the cache-generation key.

    ``scope_fingerprint`` keeps builds over different subject populations apart.
    A cohort-scoped build and a whole-CDM build of the same features must never
    share rows, or a study would silently pick up rows for people it never
    selected.
    """
    payload = {
        "cdm_schema": cdm_schema,
        "vocabulary_schema": vocabulary_schema,
        "cdm_fingerprint": cdm_fingerprint or DEFAULT_FINGERPRINT,
        "vocab_fingerprint": vocab_fingerprint or DEFAULT_FINGERPRINT,
        "engine_fingerprint": engine_fingerprint,
        "scope_fingerprint": scope_fingerprint,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"gen_{digest[:16]}"
