from __future__ import annotations

from typing import Literal

from ..cohortdefinition import BuildExpressionQueryOptions, CohortExpression
from ..execution._dataclass import frozen_slots_dataclass

GenerationPolicy = Literal["fail", "replace", "skip_if_same", "replace_if_changed"]


@frozen_slots_dataclass
class MetadataTableNames:
    metadata_table: str = "cohort_generation_metadata"
    checksum_table: str = "cohort_generation_checksums"
    subset_metadata_table: str = "cohort_subset_metadata"


@frozen_slots_dataclass
class GenerationConfig:
    cdm_schema: str
    results_schema: str
    vocabulary_schema: str | None = None
    cohort_table: str = "cohort"
    cohort_inclusion_table: str | None = None
    metadata_table: str = "cohort_generation_metadata"
    checksum_table: str = "cohort_generation_checksums"
    subset_metadata_table: str = "cohort_subset_metadata"
    default_policy: GenerationPolicy = "fail"

    def metadata_tables(self) -> MetadataTableNames:
        return MetadataTableNames(
            metadata_table=self.metadata_table,
            checksum_table=self.checksum_table,
            subset_metadata_table=self.subset_metadata_table,
        )


@frozen_slots_dataclass
class GenerationTarget:
    cohort_id: int
    expression: CohortExpression
    cohort_name: str | None = None
    options: BuildExpressionQueryOptions | None = None


@frozen_slots_dataclass
class NamedCohortExpression:
    cohort_id: int
    expression: CohortExpression
    cohort_name: str | None = None
    options: BuildExpressionQueryOptions | None = None


@frozen_slots_dataclass
class CohortSetDefinition:
    cohorts: tuple[NamedCohortExpression, ...]
