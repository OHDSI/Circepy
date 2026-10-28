"""Loader for legacy OHDSI CohortGenerator cohort-definition sets.

The legacy layout is a settings CSV (``Cohorts.csv``), a folder of Circe JSON
expressions (``cohorts/``) and a folder of pre-generated SQL files
(``sql/sql_server/``).  JSON is the authoritative definition source; SQL is
loaded into memory for provenance and for the legacy-SQL oracle.

Subset cohorts and custom SQL/template cohorts are intentionally unsupported:
they are rejected by default, or skipped with ``unsupported="skip"``.
"""

from __future__ import annotations

import csv
import io
import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from ._core import CohortDefinition, CohortDefinitionSet
from ._r_compat import format_file_stem, normalize_header

logger = logging.getLogger(__name__)

_TRUE_VALUES = {"1", "true", "t", "yes", "y"}
_MISSING_VALUES = {"", "na", "n/a", "none", "null"}
_PATH_SEPARATORS = {"/", "\\"}

__all__ = [
    "CohortSource",
    "LegacyCohortDefinitionSet",
    "LegacyCohortSetError",
    "LegacyCohortSetReport",
    "LoadedCohortDefinition",
    "MissingCohortDefinitionFileError",
    "SkippedCohort",
    "UnsupportedLegacyFeatureError",
    "load_cohort_definition_set",
]


class LegacyCohortSetError(ValueError):
    """Base error for legacy cohort-definition set loading."""


class UnsupportedLegacyFeatureError(LegacyCohortSetError):
    """Raised when a set uses subsets, templates or custom SQL definitions."""


class MissingCohortDefinitionFileError(LegacyCohortSetError):
    """Raised when a required JSON/SQL file is missing."""


@dataclass(frozen=True)
class CohortSource:
    """Paths the loaded definition came from."""

    settings_file: Path
    json_file: Path
    sql_file: Path | None = None


@dataclass
class LoadedCohortDefinition(CohortDefinition):
    """A cohort definition plus its legacy SQL and CSV metadata."""

    sql: str | None = field(default=None, compare=False)
    metadata: dict[str, Any] = field(default_factory=dict, compare=False)
    source: CohortSource | None = field(default=None, compare=False)


@dataclass(frozen=True)
class SkippedCohort:
    """A row that the loader intentionally did not load."""

    cohort_id: int | None
    cohort_name: str | None
    reason: str


@dataclass
class LegacyCohortSetReport:
    """Summary of a legacy cohort-definition load."""

    settings_file: Path
    loaded_cohort_ids: list[int] = field(default_factory=list)
    skipped: list[SkippedCohort] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_sql: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "settings_file": str(self.settings_file),
            "loaded_cohort_ids": list(self.loaded_cohort_ids),
            "skipped": [
                {
                    "cohort_id": row.cohort_id,
                    "cohort_name": row.cohort_name,
                    "reason": row.reason,
                }
                for row in self.skipped
            ],
            "warnings": list(self.warnings),
            "missing_sql": list(self.missing_sql),
        }


class LegacyCohortDefinitionSet(CohortDefinitionSet):
    """A CohortDefinitionSet loaded from disk, with a load report."""

    def __init__(self, report: LegacyCohortSetReport) -> None:
        super().__init__()
        self.report = report


def _read_text(path: Path) -> str:
    """Read a text file without newline normalization, mirroring R readChar()."""
    return path.read_bytes().decode("utf-8-sig")


def _read_settings(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    try:
        text = _read_text(path)
    except OSError as exc:
        raise LegacyCohortSetError(f"Could not read cohort settings file {path}: {exc}") from exc

    reader = csv.reader(io.StringIO(text))
    try:
        raw_headers = next(reader)
    except StopIteration as exc:
        raise LegacyCohortSetError(f"Cohort settings file is empty: {path}") from exc

    headers = [normalize_header(header) for header in raw_headers]
    if any(not header for header in headers):
        raise LegacyCohortSetError(f"Cohort settings file {path} contains an empty column name")
    duplicates = {header for header in headers if headers.count(header) > 1}
    if duplicates:
        raise LegacyCohortSetError(
            f"Cohort settings file {path} contains duplicate columns after header normalization: "
            f"{sorted(duplicates)}"
        )

    rows: list[dict[str, str]] = []
    for line_number, raw_row in enumerate(reader, start=2):
        if not any(cell.strip() for cell in raw_row):
            continue
        if len(raw_row) > len(headers):
            raise LegacyCohortSetError(
                f"Cohort settings file {path} line {line_number} has {len(raw_row)} values "
                f"but only {len(headers)} columns"
            )
        padded = [*raw_row, *([""] * (len(headers) - len(raw_row)))]
        rows.append({header: value.strip() for header, value in zip(headers, padded, strict=True)})

    return headers, rows


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in _TRUE_VALUES


def _is_missing(value: str) -> bool:
    return value.strip().lower() in _MISSING_VALUES


def _parse_cohort_id(value: str, *, path: Path) -> int:
    text = value.strip()
    if not text:
        raise LegacyCohortSetError(f"Cohort settings file {path} contains an empty cohortId")
    try:
        return int(text)
    except ValueError:
        pass

    try:
        numeric = float(text)
    except ValueError as exc:
        raise LegacyCohortSetError(
            f"Cohort settings file {path} contains non-integer cohortId {value!r}"
        ) from exc
    if not numeric.is_integer():
        raise LegacyCohortSetError(f"Cohort settings file {path} contains non-integer cohortId {value!r}")
    return int(numeric)


def _validate_file_stem(stem: str, *, cohort_id: int) -> str:
    if not stem or stem in {".", ".."}:
        raise LegacyCohortSetError(f"Cohort {cohort_id} produced an invalid file stem {stem!r}")
    if any(separator in stem for separator in _PATH_SEPARATORS):
        raise LegacyCohortSetError(f"Cohort {cohort_id} file stem {stem!r} contains a path separator")
    if Path(stem).is_absolute() or re.match(r"^[A-Za-z]:", stem):
        raise LegacyCohortSetError(f"Cohort {cohort_id} file stem {stem!r} is an absolute path")
    return stem


def _relative_inputs(
    *,
    settings_file: str | Path,
    json_folder: str | Path,
    sql_folder: str | Path | None,
    base_dir: str | Path | None,
) -> tuple[Path, Path, Path | None]:
    base = Path(base_dir) if base_dir is not None else Path.cwd()
    settings = Path(settings_file)
    if not settings.is_absolute():
        settings = base / settings
    json_dir = Path(json_folder)
    if not json_dir.is_absolute():
        json_dir = base / json_dir
    sql_dir: Path | None = None
    if sql_folder is not None:
        sql_dir = Path(sql_folder)
        if not sql_dir.is_absolute():
            sql_dir = base / sql_dir
    return settings, json_dir, sql_dir


def load_cohort_definition_set(
    *,
    settings_file: str | Path = "Cohorts.csv",
    json_folder: str | Path = "cohorts",
    sql_folder: str | Path | None = "sql/sql_server",
    cohort_file_name_format: str = "%s",
    cohort_file_name_value: Sequence[str] | str = ("cohortId",),
    include_sql: bool = True,
    sql_required: bool = False,
    unsupported: Literal["error", "skip"] = "error",
    base_dir: str | Path | None = None,
    family_column: str = "family",
    families: Sequence[str] | None = None,
    cohort_ids: Sequence[int] | None = None,
) -> LegacyCohortDefinitionSet:
    """Load a legacy CohortGenerator-style cohort definition set from disk.

    Args:
        settings_file: CSV containing cohort id/name and optional metadata.
        json_folder: Folder containing one Circe JSON file per cohort.
        sql_folder: Folder containing pre-generated SQL, or None to disable.
            SQL is read into memory when *include_sql* is True.
        cohort_file_name_format: ``%`` format string for JSON/SQL file stems.
        cohort_file_name_value: CSV column(s) used to build the file stem.
            Pass a string for a single column.
        include_sql: Load SQL text into memory (default True).
        sql_required: Raise when a SQL file is missing instead of warning.
        unsupported: ``"error"`` (default) or ``"skip"`` for subset, template
            and custom-SQL-only cohorts.
        base_dir: Directory used to resolve relative paths (default: cwd).
        family_column: CSV column containing the optional family tag.
        families: Optional family tags to load; untagged cohorts are excluded
            when this filter is set.
        cohort_ids: Optional cohort ids to load.

    Returns:
        A :class:`LegacyCohortDefinitionSet`; its ``report`` attribute contains
        loaded ids, skipped rows, warnings and missing SQL files.
    """
    if unsupported not in {"error", "skip"}:
        raise ValueError("unsupported must be 'error' or 'skip'")
    family_filter = {str(family).strip() for family in families} if families is not None else None
    id_filter = {int(cohort_id) for cohort_id in cohort_ids} if cohort_ids is not None else None
    if not cohort_file_name_format:
        raise ValueError("cohort_file_name_format must be a non-empty string")

    file_name_values = (
        (cohort_file_name_value,)
        if isinstance(cohort_file_name_value, str)
        else tuple(cohort_file_name_value)
    )
    if not file_name_values:
        raise ValueError("cohort_file_name_value must contain at least one column")

    settings_path, json_dir, sql_dir = _relative_inputs(
        settings_file=settings_file,
        json_folder=json_folder,
        sql_folder=sql_folder if include_sql else None,
        base_dir=base_dir,
    )
    headers, rows = _read_settings(settings_path)

    headers = set(headers)
    for required in ("cohortId", "cohortName"):
        if required not in headers:
            raise LegacyCohortSetError(
                f"Cohort settings file {settings_path} is missing required column {required!r}. "
                f"Found: {sorted(headers)}"
            )
    for forbidden in ("json", "sql"):
        if forbidden in headers:
            raise LegacyCohortSetError(
                f"Cohort settings file {settings_path} contains a {forbidden!r} column; "
                "legacy settings files must reference JSON/SQL files on disk instead."
            )
    for column in file_name_values:
        if column not in headers:
            raise LegacyCohortSetError(
                f"cohort_file_name_value column {column!r} is not present in {settings_path}"
            )
    if family_filter is not None and family_column not in headers:
        raise LegacyCohortSetError(
            f"Family column {family_column!r} is not present in {settings_path}; found: {sorted(headers)}"
        )

    report = LegacyCohortSetReport(settings_file=settings_path)
    cohort_set = LegacyCohortDefinitionSet(report)
    seen_ids: set[int] = set()
    seen_stems: dict[str, int] = {}
    unsupported_rows: list[SkippedCohort] = []

    for row_number, row in enumerate(rows, start=2):
        cohort_id = _parse_cohort_id(row["cohortId"], path=settings_path)
        if id_filter is not None and cohort_id not in id_filter:
            continue
        family = row.get(family_column, "").strip() or None
        if family_filter is not None and family not in family_filter:
            continue
        cohort_name = row["cohortName"].strip()
        if not cohort_name:
            raise LegacyCohortSetError(
                f"Cohort settings file {settings_path} line {row_number} has an empty cohortName"
            )
        if cohort_id in seen_ids:
            raise LegacyCohortSetError(
                f"Duplicate cohortId {cohort_id} in {settings_path} (line {row_number})"
            )
        seen_ids.add(cohort_id)

        unsupported_reason = _unsupported_reason(row, cohort_id)
        if unsupported_reason is not None:
            skipped = SkippedCohort(cohort_id, cohort_name, unsupported_reason)
            if unsupported == "error":
                unsupported_rows.append(skipped)
                continue
            report.skipped.append(skipped)
            logger.warning("Skipping cohort %s (%s): %s", cohort_id, cohort_name, unsupported_reason)
            continue

        stem = format_file_stem(
            cohort_file_name_format,
            [row[column] for column in file_name_values],
        )
        stem = _validate_file_stem(stem, cohort_id=cohort_id)
        stem_key = stem.casefold()
        if stem_key in seen_stems:
            raise LegacyCohortSetError(
                f"Cohorts {seen_stems[stem_key]} and {cohort_id} map to the same file stem {stem!r}"
            )
        seen_stems[stem_key] = cohort_id

        json_path = json_dir / f"{stem}.json"
        if not json_path.is_file():
            skipped = SkippedCohort(
                cohort_id,
                cohort_name,
                f"missing JSON definition {json_path} (custom-SQL-only cohorts are unsupported)",
            )
            if unsupported == "error":
                raise MissingCohortDefinitionFileError(
                    f"Cohort {cohort_id} ({cohort_name}) is missing its JSON definition at {json_path}. "
                    "Custom SQL/template cohorts are not supported."
                )
            report.skipped.append(skipped)
            logger.warning("Skipping cohort %s: %s", cohort_id, skipped.reason)
            continue

        try:
            json_text = _read_text(json_path)
        except OSError as exc:
            raise MissingCohortDefinitionFileError(
                f"Could not read JSON definition for cohort {cohort_id} at {json_path}: {exc}"
            ) from exc
        if not json_text.strip():
            raise MissingCohortDefinitionFileError(
                f"JSON definition for cohort {cohort_id} is empty: {json_path}"
            )

        from ..api import cohort_expression_from_json

        try:
            expression = cohort_expression_from_json(json_text)
        except Exception as exc:
            raise LegacyCohortSetError(
                f"Invalid Circe JSON for cohort {cohort_id} ({cohort_name}) at {json_path}: {exc}"
            ) from exc

        sql_path: Path | None = None
        sql_text: str | None = None
        if include_sql and sql_dir is not None:
            sql_path = sql_dir / f"{stem}.sql"
            if sql_path.is_file():
                try:
                    sql_text = _read_text(sql_path)
                except OSError as exc:
                    raise MissingCohortDefinitionFileError(
                        f"Could not read SQL for cohort {cohort_id} at {sql_path}: {exc}"
                    ) from exc
            elif sql_required:
                raise MissingCohortDefinitionFileError(
                    f"Cohort {cohort_id} ({cohort_name}) is missing its SQL file at {sql_path}"
                )
            else:
                report.missing_sql.append(cohort_id)
                message = f"Cohort {cohort_id} ({cohort_name}) has no SQL file at {sql_path}"
                report.warnings.append(message)
                logger.warning(message)

        metadata = {
            key: value for key, value in row.items() if key not in {"cohortId", "cohortName", "json", "sql"}
        }
        definition = LoadedCohortDefinition(
            cohort_id=cohort_id,
            cohort_name=cohort_name,
            expression=expression,
            family=family,
            sql=sql_text,
            metadata=metadata,
            source=CohortSource(
                settings_file=settings_path,
                json_file=json_path,
                sql_file=sql_path if sql_text is not None else None,
            ),
        )
        cohort_set.add_definition(definition)
        report.loaded_cohort_ids.append(cohort_id)

    if unsupported_rows:
        details = "; ".join(
            f"{item.cohort_id} ({item.cohort_name}): {item.reason}" for item in unsupported_rows
        )
        raise UnsupportedLegacyFeatureError(
            "The cohort definition set contains unsupported entries. "
            "Subsets, templated cohorts and custom-SQL-only cohorts are not loaded by this "
            f"loader; use unsupported='skip' to omit them. {details}"
        )

    return cohort_set


def _unsupported_reason(row: dict[str, str], cohort_id: int) -> str | None:
    if _is_truthy(row.get("isSubset", "")):
        return "subset cohorts are not supported"
    if _is_truthy(row.get("isTemplatedCohort", "")):
        return "templated cohorts are not supported"
    subset_definition_id = row.get("subsetDefinitionId", "")
    if not _is_missing(subset_definition_id):
        return f"subset definition {subset_definition_id!r} is not supported"
    subset_parent = row.get("subsetParent", "")
    if not _is_missing(subset_parent) and subset_parent.strip() != str(cohort_id):
        return f"subset parent {subset_parent!r} is not supported"
    return None
