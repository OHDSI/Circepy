from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from ..cohortdefinition.cohort import CohortExpression
else:
    from ..cohortdefinition.cohort import CohortExpression


@dataclass
class CohortDefinition:
    """A single cohort entry in a CohortDefinitionSet."""

    cohort_id: int
    cohort_name: str
    expression: CohortExpression


@dataclass
class CohortGenerationResult:
    """Result of generating a single cohort from a CohortDefinitionSet."""

    cohort_id: int
    cohort_name: str
    status: Literal["COMPLETE", "SKIPPED", "FAILED"]
    checksum: str
    start_time: datetime
    end_time: datetime
    error: Exception | None = field(default=None, compare=False)


class CohortDefinitionSet:
    """Container for a collection of cohort definitions to be generated together.

    Modelled after OHDSI/CohortGenerator's CohortDefinitionSet, but using typed
    Python classes rather than an R data.frame.

    Example:
        >>> cds = CohortDefinitionSet()
        >>> cds.add(cohort_id=1, cohort_name="Diabetes", expression=expr1)
        >>> cds.add(cohort_id=2, cohort_name="Hypertension", expression=expr2)
        >>> len(cds)
        2
    """

    def __init__(self) -> None:
        self._cohorts: list[CohortDefinition] = []
        self._id_index: dict[int, int] = {}  # cohort_id -> list index

    def add(self, cohort_id: int, cohort_name: str, expression: CohortExpression) -> None:
        """Add a cohort definition to this set.

        Args:
            cohort_id: Unique integer identifier for this cohort.
            cohort_name: Human-readable name for this cohort.
            expression: The CohortExpression defining the cohort logic.

        Raises:
            ValueError: If a cohort with the same cohort_id already exists.
        """
        if cohort_id in self._id_index:
            raise ValueError(
                f"A cohort with cohort_id={cohort_id} already exists in this CohortDefinitionSet."
            )
        self._id_index[cohort_id] = len(self._cohorts)
        self._cohorts.append(
            CohortDefinition(cohort_id=cohort_id, cohort_name=cohort_name, expression=expression)
        )

    def __len__(self) -> int:
        return len(self._cohorts)

    def __iter__(self) -> Iterator[CohortDefinition]:
        return iter(self._cohorts)

    def __getitem__(self, cohort_id: int) -> CohortDefinition:
        """Retrieve a cohort definition by its cohort_id.

        Raises:
            KeyError: If no cohort with the given id exists.
        """
        if cohort_id not in self._id_index:
            raise KeyError(f"No cohort with cohort_id={cohort_id} in this CohortDefinitionSet.")
        return self._cohorts[self._id_index[cohort_id]]

    def checksums(self) -> dict[int, str]:
        """Return a mapping of cohort_id to the expression checksum for each cohort.

        Checksums are computed using CohortExpression.checksum(), which normalises
        the expression JSON and produces a SHA-256 hex digest. This is suitable for
        detecting whether a cohort definition has changed between runs.

        Returns:
            dict mapping cohort_id -> hex checksum string
        """
        return {c.cohort_id: c.expression.checksum() for c in self._cohorts}
