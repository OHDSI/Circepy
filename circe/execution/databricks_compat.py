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
    """Return True when *exc* is the memtable-volume setup failure.

    Databricks errors often omit the failing SQL statement, so a missing
    catalog during ``_post_connect`` (whose only operation is CREATE VOLUME)
    must be recognised from the server error code as well.
    """
    message = str(exc).lower()
    if "create volume if not exists" in message:
        return True
    if "memtable" in message and "volume" in message:
        return True
    if "no_such_catalog" in message:
        return True
    return "catalog" in message and "not found" in message


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
    # Resolve the installed backend when the caller did not supply a class.
    # Ibis 12.0.0 still performs the CREATE VOLUME in ``_post_connect``, so the
    # version gate that previously skipped this patch on newer Ibis releases was
    # wrong. Source inspection below decides whether the patch is needed.
    if backend_cls is None:
        backend_cls = _databricks_backend_class()

    if backend_cls is None:
        return False

    post_connect = getattr(backend_cls, "_post_connect", None)
    if not callable(post_connect):
        return False

    if getattr(backend_cls, _PATCH_FLAG, False):
        return True

    if not _post_connect_needs_workaround(post_connect):
        return False

    import warnings

    warnings.warn(
        "The Databricks workaround for Ibis issue #11598 is active. "
        "It will be removed once the upstream memtable-volume initialisation is fixed.",
        DeprecationWarning,
        stacklevel=2,
    )

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


def _databricks_connect_fn() -> Callable[..., Any]:
    """Return the ibis Databricks connect callable (isolated for testing)."""
    import ibis

    return ibis.databricks.connect


def connect_databricks(*args: Any, **kwargs: Any) -> Any:
    """Connect to Databricks through ibis with the memtable workaround applied.

    The workaround has to be installed *before* the backend is constructed:
    ``Backend.do_connect()`` calls ``_post_connect()`` (the CREATE VOLUME
    statement) while connecting.  Calling
    :func:`apply_databricks_post_connect_workaround` after
    ``ibis.databricks.connect()`` is too late for that failure.

    Use this helper instead of ``ibis.databricks.connect()`` when the
    workspace has no ``hive_metastore`` catalog, or call
    :func:`apply_databricks_post_connect_workaround` yourself first.

    Args:
        *args: Positional arguments forwarded to ``ibis.databricks.connect``.
        **kwargs: Keyword arguments forwarded to ``ibis.databricks.connect``.
            ``memtable_volume`` can be supplied when a writable volume exists;
            the workaround then suppresses only the catalog-related failures.

    Returns:
        The connected ibis Databricks backend.

    Raises:
        ImportError: If the ibis Databricks backend is not installed.
    """
    from ._sqlglot_compat import require_compatible_sqlglot

    require_compatible_sqlglot()

    backend_cls = _databricks_backend_class()
    if backend_cls is None:
        raise ImportError(
            "The ibis Databricks backend is unavailable. "
            "Install it with: pip install 'ibis-framework[databricks]'"
        )

    apply_databricks_post_connect_workaround(backend_cls=backend_cls)
    return _databricks_connect_fn()(*args, **kwargs)


def maybe_apply_databricks_post_connect_workaround(backend: object) -> bool:
    """Apply the workaround only for Databricks-like backends."""
    if not _backend_looks_like_databricks(backend):
        return False
    return apply_databricks_post_connect_workaround(backend_cls=backend.__class__)


__all__ = [
    "ISSUE_REFERENCE",
    "apply_databricks_post_connect_workaround",
    "connect_databricks",
    "maybe_apply_databricks_post_connect_workaround",
]
