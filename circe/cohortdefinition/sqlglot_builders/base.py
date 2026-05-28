from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from sqlglot import exp as sge

from ..builders.utils import CriteriaColumn
from ..criteria import Criteria

T = TypeVar("T", bound=Criteria)


class CriteriaColumnMap(ABC):
    """Maps CriteriaColumn enum values to sqlglot column expressions."""

    @abstractmethod
    def get_column(self, column: CriteriaColumn) -> sge.Expression:
        pass


class SqlGlotCriteriaBuilder(ABC, Generic[T]):
    """Abstract base for sqlglot AST-based criteria builders."""

    @abstractmethod
    def build_select(self, criteria: T) -> sge.Select:
        pass

    def compile(self, criteria: T, dialect: str = "duckdb") -> str:
        sel = self.build_select(criteria)
        return sel.sql(dialect=dialect)
