from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from circe.execution.normalize.windows import NormalizedDateRange


def test_execution_package_imports():
    import circe.execution
    import circe.execution.api
    import circe.execution.engine
    import circe.execution.ibis
    import circe.execution.lower
    import circe.execution.normalize
    import circe.execution.plan

    assert hasattr(circe.execution, "build_cohort")
    assert hasattr(circe.execution, "write_cohort")


def test_normalized_dataclasses_are_frozen():
    value = NormalizedDateRange(op="gte", value="2020-01-01", extent=None)
    with pytest.raises(FrozenInstanceError):
        value.op = "lt"
