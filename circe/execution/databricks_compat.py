from __future__ import annotations

import functools
import inspect

ISSUE_REFERENCE = "https://github.com/ibis-project/ibis/issues/11598"
_PATCH_FLAG = "_circe_databricks_post_connect_patched"


def _databricks_backend_class():
    try:
        import ibis.backends.databricks as databricks_backend
    except Exception:
        return None
    return getattr(databricks_backend, "Backend", None)


def _post_connect_needs_workaround(post_connect) -> bool:
    try:
        source = inspect.getsource(post_connect).lower()
    except (OSError, TypeError):
        return True
    return "create volume if not exists" in source and "memtable" in source


def _is_memtable_volume_error(exc: Exception) -> bool:
    message = str(exc).lower()
    if "create volume if not exists" in message:
        return True
    if "memtable" in message and "volume" in message:
        return True
    return False


def apply_databricks_post_connect_workaround(*, backend_cls=None) -> bool:
    """
    Patch Databricks backend `_post_connect` for Ibis issue #11598.

    Some Ibis Databricks versions call `CREATE VOLUME IF NOT EXISTS ...` during
    `_post_connect` for memtable support and can fail in read-only/locked-down
    schemas. This workaround suppresses only that known failure mode and should
    be removed once upstream behavior is fixed.
    """
    backend_cls = _databricks_backend_class() if backend_cls is None else backend_cls
    if backend_cls is None:
        return False

    post_connect = getattr(backend_cls, "_post_connect", None)
    if not callable(post_connect):
        return False

    if getattr(backend_cls, _PATCH_FLAG, False):
        return True

    if not _post_connect_needs_workaround(post_connect):
        return False

    @functools.wraps(post_connect)
    def _patched_post_connect(self, *args, **kwargs):
        try:
            return post_connect(self, *args, **kwargs)
        except Exception as exc:
            if _is_memtable_volume_error(exc):
                return None
            raise

    setattr(backend_cls, "_post_connect", _patched_post_connect)
    setattr(backend_cls, _PATCH_FLAG, True)
    return True


__all__ = ["ISSUE_REFERENCE", "apply_databricks_post_connect_workaround"]
