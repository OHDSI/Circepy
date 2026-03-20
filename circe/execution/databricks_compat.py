from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from typing import Any

ISSUE_REFERENCE = "https://github.com/ibis-project/ibis/issues/11598"
_PATCH_FLAG = "_circe_databricks_post_connect_patched"


def _databricks_backend_class() -> type[Any] | None:
    try:
        import ibis.backends.databricks as databricks_backend
    except Exception:
        return None
    return getattr(databricks_backend, "Backend", None)


def _post_connect_needs_workaround(post_connect: Callable[..., Any]) -> bool:
    try:
        source = inspect.getsource(post_connect).lower()
    except (OSError, TypeError):
        return True
    return "create volume if not exists" in source and "memtable" in source


def _is_memtable_volume_error(exc: Exception) -> bool:
    message = str(exc).lower()
    if "create volume if not exists" in message:
        return True
    return bool("memtable" in message and "volume" in message)


def _backend_looks_like_databricks(backend: object) -> bool:
    backend_name = getattr(backend, "name", None)
    if isinstance(backend_name, str) and backend_name.lower() == "databricks":
        return True
    class_name = backend.__class__.__name__.lower()
    return "databricks" in class_name


def apply_databricks_post_connect_workaround(
    *,
    backend_cls: type[Any] | None = None,
) -> bool:
    """
    Patch Databricks backend `_post_connect` for Ibis issue #11598.

    Some Ibis Databricks versions call `CREATE VOLUME IF NOT EXISTS ...` during
    `_post_connect` for memtable support and can fail in read-only/locked-down
    schemas. This workaround suppresses only that known failure mode and should
    be removed once upstream behavior is fixed.

    Activation note:
    This helper should be applied lazily by the execution path when a
    Databricks backend is actually used.
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
    def _patched_post_connect(self: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return post_connect(self, *args, **kwargs)
        except Exception as exc:
            if _is_memtable_volume_error(exc):
                return None
            raise

    backend_cls._post_connect = _patched_post_connect
    setattr(backend_cls, _PATCH_FLAG, True)
    return True


def maybe_apply_databricks_post_connect_workaround(backend: object) -> bool:
    """Apply the workaround only for Databricks-like backends."""
    if not _backend_looks_like_databricks(backend):
        return False
    return apply_databricks_post_connect_workaround(backend_cls=backend.__class__)


__all__ = [
    "ISSUE_REFERENCE",
    "apply_databricks_post_connect_workaround",
    "maybe_apply_databricks_post_connect_workaround",
]
