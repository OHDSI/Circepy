from __future__ import annotations

import pytest

from circe.execution.databricks_compat import apply_databricks_post_connect_workaround


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
