from __future__ import annotations

import sys
import types

import pytest

from circe.execution import databricks_compat
from circe.execution.databricks_compat import (
    _backend_looks_like_databricks,
    _is_memtable_volume_error,
    _post_connect_needs_workaround,
    apply_databricks_post_connect_workaround,
    connect_databricks,
    maybe_apply_databricks_post_connect_workaround,
)


def test_databricks_post_connect_workaround_swallows_memtable_volume_error():
    class FakeDatabricksBackend:
        def _post_connect(self):
            raise RuntimeError("CREATE VOLUME IF NOT EXISTS my_catalog.my_schema.memtable")

    with pytest.warns(DeprecationWarning):
        patched = apply_databricks_post_connect_workaround(backend_cls=FakeDatabricksBackend)
    assert patched is True

    backend = FakeDatabricksBackend()
    assert backend._post_connect() is None


def test_databricks_post_connect_workaround_keeps_non_volume_errors():
    class FakeDatabricksBackend:
        def _post_connect(self):
            _ = "CREATE VOLUME IF NOT EXISTS my_catalog.my_schema.memtable"
            raise RuntimeError("different setup error")

    with pytest.warns(DeprecationWarning):
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

    with pytest.warns(DeprecationWarning):
        assert apply_databricks_post_connect_workaround(backend_cls=FakeDatabricksBackend) is True
    # Second call is idempotent — no warning because the patch flag is already set
    assert apply_databricks_post_connect_workaround(backend_cls=FakeDatabricksBackend) is True
    assert maybe_apply_databricks_post_connect_workaround(FakeDatabricksBackend()) is True


def test_missing_catalog_error_is_recognised_without_sql_text():
    # Databricks omits the statement from this server error.
    exc = RuntimeError("[NO_SUCH_CATALOG_EXCEPTION] Catalog 'hive_metastore' was not found. SQLSTATE: 42704")
    assert _is_memtable_volume_error(exc) is True


def test_workaround_applies_to_current_ibis_versions(monkeypatch):
    class FakeDatabricksBackend:
        def _post_connect(self):
            _ = "CREATE VOLUME IF NOT EXISTS `hive_metastore`.`default`.`ibis_memtable`"
            raise RuntimeError("[NO_SUCH_CATALOG_EXCEPTION] Catalog 'hive_metastore' was not found.")

    monkeypatch.setattr(databricks_compat, "_databricks_backend_class", lambda: FakeDatabricksBackend)

    with pytest.warns(DeprecationWarning):
        assert apply_databricks_post_connect_workaround(backend_cls=None) is True
    assert FakeDatabricksBackend()._post_connect() is None


def test_connect_databricks_patches_backend_before_connecting(monkeypatch):
    class FakeDatabricksBackend:
        def _post_connect(self):
            _ = "CREATE VOLUME IF NOT EXISTS `hive_metastore`.`default`.`ibis_memtable`"
            raise RuntimeError("[NO_SUCH_CATALOG_EXCEPTION] Catalog 'hive_metastore' was not found.")

    calls = []

    def fake_connect(*args, **kwargs):
        backend = FakeDatabricksBackend()
        # This mirrors ibis: do_connect() calls _post_connect() while connecting.
        backend._post_connect()
        calls.append((args, kwargs))
        return "connected-backend"

    monkeypatch.setattr(databricks_compat, "_databricks_backend_class", lambda: FakeDatabricksBackend)
    monkeypatch.setattr(databricks_compat, "_databricks_connect_fn", lambda: fake_connect)

    with pytest.warns(DeprecationWarning):
        result = connect_databricks(server_hostname="host", http_path="path")

    assert result == "connected-backend"
    assert calls == [((), {"server_hostname": "host", "http_path": "path"})]


def test_connect_databricks_requires_installed_backend(monkeypatch):
    monkeypatch.setattr(databricks_compat, "_databricks_backend_class", lambda: None)

    with pytest.raises(ImportError, match="ibis Databricks backend"):
        connect_databricks(server_hostname="host")


def test_databricks_backend_class_handles_missing_and_present_modules(monkeypatch):
    monkeypatch.setitem(sys.modules, "ibis.backends.databricks", None)
    assert databricks_compat._databricks_backend_class() is None

    fake_module = types.SimpleNamespace(Backend=object)
    monkeypatch.setitem(sys.modules, "ibis.backends.databricks", fake_module)
    assert databricks_compat._databricks_backend_class() is fake_module.Backend


def test_databricks_connect_fn_reads_ibis_module(monkeypatch):
    fake_connect = lambda *args, **kwargs: "connected"  # noqa: E731
    fake_ibis = types.SimpleNamespace(
        databricks=types.SimpleNamespace(connect=fake_connect),
    )
    monkeypatch.setitem(sys.modules, "ibis", fake_ibis)

    assert databricks_compat._databricks_connect_fn() is fake_connect
