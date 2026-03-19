from __future__ import annotations

import pytest

from circe.execution.databricks_compat import (
    _backend_looks_like_databricks,
    _is_memtable_volume_error,
    _post_connect_needs_workaround,
    apply_databricks_post_connect_workaround,
    maybe_apply_databricks_post_connect_workaround,
)


def test_databricks_post_connect_workaround_swallows_memtable_volume_error():
    class FakeDatabricksBackend:
        def _post_connect(self):
            raise RuntimeError("CREATE VOLUME IF NOT EXISTS my_catalog.my_schema.memtable")

    patched = apply_databricks_post_connect_workaround(backend_cls=FakeDatabricksBackend)
    assert patched is True

    backend = FakeDatabricksBackend()
    assert backend._post_connect() is None


def test_databricks_post_connect_workaround_keeps_non_volume_errors():
    class FakeDatabricksBackend:
        def _post_connect(self):
            _ = "CREATE VOLUME IF NOT EXISTS my_catalog.my_schema.memtable"
            raise RuntimeError("different setup error")

    patched = apply_databricks_post_connect_workaround(backend_cls=FakeDatabricksBackend)
    assert patched is True

    backend = FakeDatabricksBackend()
    with pytest.raises(RuntimeError, match="different setup error"):
        backend._post_connect()


def test_post_connect_needs_workaround_handles_missing_source_and_false_pattern(monkeypatch):
    def _plain_post_connect():
        return None

    monkeypatch.setattr("inspect.getsource", lambda _fn: "plain setup")
    assert _post_connect_needs_workaround(_plain_post_connect) is False

    monkeypatch.setattr("inspect.getsource", lambda _fn: (_ for _ in ()).throw(OSError("no source")))
    assert _post_connect_needs_workaround(_plain_post_connect) is True


def test_databricks_detection_helpers_cover_non_patched_paths():
    assert _is_memtable_volume_error(RuntimeError("memtable volume failure")) is True
    assert _is_memtable_volume_error(RuntimeError("different failure")) is False

    assert _backend_looks_like_databricks(type("DatabricksConn", (), {})()) is True
    assert _backend_looks_like_databricks(type("Backend", (), {"name": "databricks"})()) is True
    assert _backend_looks_like_databricks(type("Backend", (), {"name": "duckdb"})()) is False


def test_apply_databricks_workaround_returns_false_when_not_patchable():
    class NoPostConnectBackend:
        pass

    class PlainBackend:
        def _post_connect(self):
            return None

    assert apply_databricks_post_connect_workaround(backend_cls=None) is False
    assert apply_databricks_post_connect_workaround(backend_cls=NoPostConnectBackend) is False
    assert apply_databricks_post_connect_workaround(backend_cls=PlainBackend) is False
    assert maybe_apply_databricks_post_connect_workaround(object()) is False


def test_apply_databricks_workaround_is_idempotent():
    class FakeDatabricksBackend:
        def _post_connect(self):
            raise RuntimeError("CREATE VOLUME IF NOT EXISTS my_catalog.my_schema.memtable")

    assert apply_databricks_post_connect_workaround(backend_cls=FakeDatabricksBackend) is True
    assert apply_databricks_post_connect_workaround(backend_cls=FakeDatabricksBackend) is True
    assert maybe_apply_databricks_post_connect_workaround(FakeDatabricksBackend()) is True
