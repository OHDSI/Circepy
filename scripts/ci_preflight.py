#!/usr/bin/env python3
"""Local CI preflight harness for coding agents.

This reproduces the checks GitHub Actions runs so contributors (human or
automated) can catch failures *before* pushing and waiting on a CI round trip.

It exists because three classes of failure only ever showed up in CI:

1. **Tool-version skew** -- CI installs the *latest* ``ruff`` while the local
   ``pre-commit`` pin can be older.  Code that satisfies one version can fail
   the other.  The ``lint`` gate always runs the latest ruff.
2. **Dependency drift** -- CI resolves the *latest allowed* transitive
   dependencies (it ignores ``uv.lock``), so a regression in e.g. ``sqlglot``
   breaks the suite locally without reproducing for anyone on an older env.
   The ``tests`` gate installs/upgrades into an isolated env before running.
3. **Coverage thresholds** -- Codecov fails the PR when patch coverage is below
   the project target or when project coverage regresses.  The ``coverage``
   gate computes both locally from ``coverage.xml``.

Usage
-----
    python scripts/ci_preflight.py                 # run every gate
    python scripts/ci_preflight.py --only lint tests
    python scripts/ci_preflight.py --skip coverage
    python scripts/ci_preflight.py --base-ref origin/develop
    python scripts/ci_preflight.py --no-install    # use the current interpreter

Exit code is non-zero if any gate fails.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]

import tomllib

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_DIR = REPO_ROOT / ".ci_preflight" / "venv"

# Packages whose version drift is worth surfacing explicitly (they have bitten
# us before: a single upstream regression in any of these fails the whole suite).
DEFAULT_SENSITIVE_PACKAGES = (
    "ruff",
    "ibis-framework",
    "sqlglot",
    "duckdb",
    "pandas",
    "polars",
)

_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
_FAILED_OUTCOMES = {"failed", "error"}


# ---------------------------------------------------------------------------
# Pure helpers (unit tested in tests/test_ci_preflight.py)
# ---------------------------------------------------------------------------


def parse_changed_lines(diff_text: str) -> dict[str, set[int]]:
    """Return the set of added line numbers per file from a unified diff.

    Only ``+`` (added) lines are returned; context and removed lines are
    ignored.  Paths are normalised to be relative to the repository root.
    """
    changed: dict[str, set[int]] = {}
    current_file: str | None = None
    new_line = 0

    for raw in diff_text.splitlines():
        if raw.startswith("+++ "):
            path = raw[4:].strip()
            if path == "/dev/null":
                current_file = None
            else:
                current_file = path[2:] if path.startswith("b/") else path
                changed.setdefault(current_file, set())
        elif raw.startswith("--- "):
            continue
        elif raw.startswith("@@"):
            match = _HUNK_RE.match(raw)
            new_line = int(match.group(1)) if match else 0
        elif raw.startswith("+") and not raw.startswith("+++"):
            if current_file is not None:
                changed[current_file].add(new_line)
            new_line += 1
        elif raw.startswith("-") and not raw.startswith("---"):
            continue
        elif raw.startswith(" "):
            new_line += 1

    return changed


def parse_coverage_xml(
    path: Path,
    repo_root: Path | None = REPO_ROOT,
) -> dict[str, dict[int, int]]:
    """Parse a Cobertura ``coverage.xml`` into ``{filename: {line: hits}}``.

    ``coverage.py`` emits class filenames relative to the configured source
    root(s) (e.g. ``__init__.py`` for ``circe/__init__.py``), so when
    *repo_root* is provided the paths are rebased onto it to match ``git diff``
    output.
    """
    tree = ElementTree.parse(path)
    root = tree.getroot()
    sources = [source.text for source in root.iter("source") if source.text]

    result: dict[str, dict[int, int]] = {}
    for class_el in root.iter("class"):
        filename = class_el.get("filename")
        if not filename:
            continue
        key = _rebase_source_path(filename, sources, repo_root)
        lines = {
            int(line_el.get("number")): int(line_el.get("hits") or 0)
            for line_el in class_el.iter("line")
            if line_el.get("number") is not None
        }
        result.setdefault(key, {}).update(lines)
    return result


def _rebase_source_path(filename: str, sources: list[str], repo_root: Path | None) -> str:
    if repo_root is None or not sources:
        return filename
    for source in sources:
        candidate = (Path(source) / filename).resolve()
        try:
            relative = candidate.relative_to(repo_root.resolve())
        except ValueError:
            continue
        return relative.as_posix()
    return filename


def compute_patch_coverage(
    changed: dict[str, set[int]],
    coverage: dict[str, dict[int, int]],
) -> tuple[int, int]:
    """Return ``(covered, total)`` for the changed lines that appear in coverage.

    Lines in files with no coverage data (e.g. tests, scripts) are ignored, which
    mirrors how Codecov scores patch coverage from the uploaded report.
    """
    covered = 0
    total = 0
    for filename, lines in changed.items():
        file_coverage = coverage.get(filename)
        if not file_coverage:
            continue
        for line in lines:
            if line in file_coverage:
                total += 1
                if file_coverage[line] > 0:
                    covered += 1
    return covered, total


def compute_project_coverage(coverage: dict[str, dict[int, int]]) -> tuple[int, int]:
    """Return ``(covered, total)`` across every measured line."""
    total = sum(len(lines) for lines in coverage.values())
    covered = sum(1 for lines in coverage.values() for hits in lines.values() if hits > 0)
    return covered, total


def percentage(covered: int, total: int) -> float:
    """Return ``covered / total`` as a percentage (100.0 when total is 0)."""
    return 100.0 * covered / total if total else 100.0


def parse_test_report(path: Path) -> dict[str, str]:
    """Map ``nodeid -> outcome`` from a ``pytest-json-report`` file."""
    data = json.loads(path.read_text())
    return {test["nodeid"]: test.get("outcome", "unknown") for test in data.get("tests", [])}


def new_failures(baseline: dict[str, str], final: dict[str, str]) -> set[str]:
    """Return nodeids that are failing/erroring in *final* but not in *baseline*."""
    baseline_failed = {node for node, outcome in baseline.items() if outcome in _FAILED_OUTCOMES}
    return {
        node for node, outcome in final.items() if outcome in _FAILED_OUTCOMES and node not in baseline_failed
    }


def parse_pip_versions(freeze_output: str) -> dict[str, str]:
    """Parse ``pip freeze`` output into a ``{package: version}`` mapping."""
    versions: dict[str, str] = {}
    for line in freeze_output.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "==" not in line:
            continue
        name, _, version = line.partition("==")
        versions[name.lower().replace("_", "-")] = version
    return versions


# ---------------------------------------------------------------------------
# Command helpers
# ---------------------------------------------------------------------------


def _log(message: str) -> None:
    print(message, flush=True)


def run(cmd: list[str], *, cwd: Path = REPO_ROOT, check: bool = False) -> subprocess.CompletedProcess:
    """Run *cmd*, echoing it, returning the completed process."""
    _log(f"\n$ {shlex.join(cmd)}")
    return subprocess.run(cmd, cwd=str(cwd), check=check)


def capture(cmd: list[str], *, cwd: Path = REPO_ROOT) -> str:
    """Run *cmd* and return stdout (empty string on failure)."""
    result = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return result.stdout


def _latest_ruff_command() -> list[str]:
    """A command that runs the latest ruff, matching the CI ruff job."""
    if shutil.which("uvx"):
        return ["uvx", "ruff@latest"]
    if shutil.which("uv"):
        return ["uv", "tool", "run", "ruff@latest"]
    if shutil.which("ruff"):
        _log("warning: uv/uvx not found; falling back to the ruff on PATH (may be stale).")
        return ["ruff"]
    raise RuntimeError("Unable to locate ruff (install uv: https://docs.astral.sh/uv/).")


def _uv() -> str | None:
    return shutil.which("uv")


def untracked_paths() -> list[str]:
    """Return untracked, non-ignored paths.

    Ruff is run in directory mode (matching CI's ``ruff check .``) but these
    paths are excluded so stray files in a working copy (scratch documents,
    local experiments) do not produce false positives that a clean CI checkout,
    which only contains tracked files, would never report.  Stage new files
    before running the harness so they are linted.
    """
    output = capture(["git", "ls-files", "--others", "--exclude-standard", "-z"])
    return [path for path in output.split("\0") if path]


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------


@dataclass
class GateResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class Config:
    base_ref: str = "origin/develop"
    python: str = "3.11"
    project_target: float = 80.0
    patch_target: float = 80.0
    sensitive_packages: tuple[str, ...] = DEFAULT_SENSITIVE_PACKAGES
    extra_install: tuple[str, ...] = ("pytest-xdist", "pytest-json-report", "pytest-cov")


def load_config() -> Config:
    """Load ``[tool.ci-preflight]`` from pyproject.toml, falling back to defaults."""
    config = Config()
    pyproject = REPO_ROOT / "pyproject.toml"
    if not pyproject.exists():
        return config
    data = tomllib.loads(pyproject.read_text()).get("tool", {}).get("ci-preflight", {})
    if "base-ref" in data:
        config.base_ref = data["base-ref"]
    if "python" in data:
        config.python = str(data["python"])
    if "project-target" in data:
        config.project_target = float(data["project-target"])
    if "patch-target" in data:
        config.patch_target = float(data["patch-target"])
    if "sensitive-packages" in data:
        config.sensitive_packages = tuple(data["sensitive-packages"])
    return config


def gate_lint(config: Config) -> GateResult:
    """Run the latest ruff (lint + format check) exactly like the CI ruff job."""
    _log("\n=== Gate: lint (latest ruff, matches CI) ===")
    ruff = _latest_ruff_command()
    excludes: list[str] = []
    for path in untracked_paths():
        excludes += ["--exclude", path]
    check = run(ruff + ["check", "--force-exclude", *excludes, "."])
    if check.returncode != 0:
        return GateResult(
            "lint",
            False,
            "ruff check failed. Fix with: " + shlex.join(ruff + ["check", "--fix", "."]),
        )

    fmt = run(ruff + ["format", "--check", "--force-exclude", *excludes, "."])
    if fmt.returncode != 0:
        return GateResult(
            "lint",
            False,
            "ruff format --check failed. Fix with: " + shlex.join(ruff + ["format", "."]),
        )
    return GateResult("lint", True, "latest ruff check + format passed")


def gate_precommit() -> GateResult:
    """Run the pinned pre-commit hooks (must also stay green)."""
    _log("\n=== Gate: pre-commit (pinned hooks) ===")
    exe = shutil.which("pre-commit")
    if not exe:
        return GateResult("pre-commit", True, "pre-commit not installed; skipped")
    result = run([exe, "run", "--all-files"])
    if result.returncode != 0:
        return GateResult("pre-commit", False, "pre-commit hooks modified files or failed")
    return GateResult("pre-commit", True, "all hooks passed")


def ensure_env(config: Config, *, refresh: bool) -> Path:
    """Create/refresh an isolated env that resolves the latest allowed deps."""
    uv = _uv()
    if uv is None:
        raise RuntimeError(
            "uv is required for the isolated test env; install from https://docs.astral.sh/uv/"
        )

    if refresh and ENV_DIR.exists():
        shutil.rmtree(ENV_DIR)
    if not ENV_DIR.exists():
        run([uv, "venv", "--python", config.python, str(ENV_DIR)])

    install = [uv, "pip", "install", "--python", str(ENV_DIR)]
    if refresh:
        install.append("--upgrade")
    install += ["-e", ".[dev]", *config.extra_install]
    run(install, check=True)
    return ENV_DIR / "bin" / "python"


def gate_tests(config: Config, *, refresh: bool, compare_baseline: bool) -> GateResult:
    """Run the suite in an env with the latest allowed dependencies."""
    _log("\n=== Gate: tests (isolated env, latest allowed deps) ===")
    python = ensure_env(config, refresh=refresh)

    report = REPO_ROOT / ".ci_preflight" / "report.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    result = run(
        [
            str(python),
            "-m",
            "pytest",
            "-n",
            "auto",
            "-q",
            "--json-report",
            f"--json-report-file={report}",
        ]
    )

    detail = "unknown"
    final = {}
    if report.exists():
        final = parse_test_report(report)
        passed = sum(1 for outcome in final.values() if outcome == "passed")
        detail = f"{passed} passed ({len(final)} collected)"

    if result.returncode != 0:
        return GateResult("tests", False, f"pytest failed: {detail}")

    if compare_baseline:
        baseline_path = REPO_ROOT / ".test_baseline.json"
        if baseline_path.exists():
            failures = new_failures(parse_test_report(baseline_path), final)
            if failures:
                sample = ", ".join(sorted(failures)[:5])
                return GateResult(
                    "tests",
                    False,
                    f"{len(failures)} new failure(s) vs baseline: {sample}",
                )
            detail += "; no new failures vs baseline"

    return GateResult("tests", True, detail)


def resolved_version_summary(config: Config) -> str:
    """Return a short report of sensitive package versions in the test env."""
    python = ENV_DIR / "bin" / "python"
    if not python.exists():
        return "test env not created"
    uv = _uv()
    if uv is not None:
        freeze = capture([uv, "pip", "freeze", "--python", str(python)])
    else:
        freeze = capture([str(python), "-m", "pip", "freeze"])
    versions = parse_pip_versions(freeze)
    if not versions:
        return "could not determine versions"
    return ", ".join(f"{pkg}={versions.get(pkg, '?')}" for pkg in config.sensitive_packages)


def gate_coverage(config: Config) -> GateResult:
    """Compute project + patch coverage from coverage.xml."""
    _log("\n=== Gate: coverage (project + patch) ===")
    coverage_path = REPO_ROOT / "coverage.xml"
    if not coverage_path.exists():
        return GateResult("coverage", False, "coverage.xml not found; run tests first")

    coverage = parse_coverage_xml(coverage_path)
    project_covered, project_total = compute_project_coverage(coverage)
    project_pct = percentage(project_covered, project_total)

    changed = _changed_lines(config.base_ref)
    patch_covered, patch_total = compute_patch_coverage(changed, coverage)
    patch_pct = percentage(patch_covered, patch_total)

    _log(f"  project coverage: {project_pct:.2f}% ({project_covered}/{project_total})")
    _log(f"  patch coverage:   {patch_pct:.2f}% ({patch_covered}/{patch_total}) vs {config.base_ref}")

    problems = []
    if project_pct < config.project_target:
        problems.append(f"project {project_pct:.2f}% < target {config.project_target:.0f}%")
    if patch_total and patch_pct < config.patch_target:
        problems.append(f"patch {patch_pct:.2f}% < target {config.patch_target:.0f}%")

    if problems:
        return GateResult("coverage", False, "; ".join(problems))
    return GateResult("coverage", True, f"project {project_pct:.2f}%, patch {patch_pct:.2f}%")


def _changed_lines(base_ref: str) -> dict[str, set[int]]:
    """Added line numbers versus the merge base with *base_ref*."""
    merge_base = capture(["git", "merge-base", base_ref, "HEAD"]).strip()
    if not merge_base:
        _log(f"  warning: could not resolve merge-base with {base_ref}; comparing against HEAD~1")
        merge_base = "HEAD~1"
    diff = capture(["git", "diff", "-U0", merge_base, "HEAD", "--", "*.py"])
    return parse_changed_lines(diff)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


GATES = ("lint", "precommit", "tests", "coverage")


def main(argv: list[str] | None = None) -> int:
    config = load_config()
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--only", nargs="+", choices=GATES, help="run only these gates")
    parser.add_argument("--skip", nargs="+", choices=GATES, default=[], help="skip these gates")
    parser.add_argument("--base-ref", default=config.base_ref, help="base ref for patch coverage")
    parser.add_argument("--python", default=config.python, help="python version for the test env")
    parser.add_argument("--project-target", type=float, default=config.project_target)
    parser.add_argument("--patch-target", type=float, default=config.patch_target)
    parser.add_argument("--refresh", action="store_true", help="recreate the test env (fresh deps)")
    parser.add_argument(
        "--no-install",
        action="store_true",
        help="skip env creation; run tests with the current interpreter",
    )
    parser.add_argument(
        "--compare-baseline", action="store_true", help="diff failures vs .test_baseline.json"
    )
    args = parser.parse_args(argv)

    config.base_ref = args.base_ref
    config.python = args.python
    config.project_target = args.project_target
    config.patch_target = args.patch_target

    selected = list(args.only) if args.only else [g for g in GATES if g not in args.skip]

    results: list[GateResult] = []
    if "lint" in selected:
        results.append(gate_lint(config))
    if "precommit" in selected:
        results.append(gate_precommit())
    if "tests" in selected:
        if args.no_install:
            results.append(_gate_tests_current_interpreter(config, compare_baseline=args.compare_baseline))
        else:
            results.append(gate_tests(config, refresh=args.refresh, compare_baseline=args.compare_baseline))
        _log(f"\n  resolved versions: {resolved_version_summary(config)}")
    if "coverage" in selected:
        results.append(gate_coverage(config))

    _log("\n=== Summary ===")
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        _log(f"  [{status}] {result.name}: {result.detail}")

    failed = [result for result in results if not result.passed]
    if failed:
        _log("\nPreflight failed. Fix the gate(s) above before pushing.")
        return 1
    _log("\nPreflight passed.")
    return 0


def _gate_tests_current_interpreter(config: Config, *, compare_baseline: bool) -> GateResult:
    _log("\n=== Gate: tests (current interpreter) ===")
    report = REPO_ROOT / ".ci_preflight" / "report.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    result = run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--json-report",
            f"--json-report-file={report}",
        ]
    )
    final = parse_test_report(report) if report.exists() else {}
    passed = sum(1 for outcome in final.values() if outcome == "passed")
    detail = f"{passed} passed ({len(final)} collected)"
    if result.returncode != 0:
        return GateResult("tests", False, f"pytest failed: {detail}")
    if compare_baseline and (REPO_ROOT / ".test_baseline.json").exists():
        failures = new_failures(parse_test_report(REPO_ROOT / ".test_baseline.json"), final)
        if failures:
            return GateResult("tests", False, f"{len(failures)} new failure(s) vs baseline")
    return GateResult("tests", True, detail)


if __name__ == "__main__":
    raise SystemExit(main())
