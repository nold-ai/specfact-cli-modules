"""Portable runtime scope selection and sealed-parent target-worker adapters."""

from __future__ import annotations

import fnmatch
import json
import os
import shlex
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from icontract import ensure, require

from specfact_code_review._review_utils import tool_error
from specfact_code_review.run.findings import ReviewFinding
from specfact_code_review.run.runtime_models import ProjectPlan, ProjectRuntimeError
from specfact_code_review.run.runtime_sources import is_excluded_source
from specfact_code_review.run.target_launch import target_command


DEPENDENT_MEMBERS = frozenset({"basedpyright", "pylint", "contracts", "targeted-pytest-coverage"})
# Native pytest 9.1.1 defaults; explicit norecursedirs replaces this set.
DEFAULT_NORECURSEDIRS = ("*.egg", ".*", "_darcs", "build", "CVS", "dist", "node_modules", "venv", "{arch}")


def _strings(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(shlex.split(value))
    if isinstance(value, list | tuple):
        return tuple(str(item) for item in value)
    return ()


def _matching_source_tests(relative: str, candidates: set[str]) -> set[str]:
    stem = Path(relative).stem
    matches = {candidate for candidate in candidates if Path(candidate).name in {f"test_{stem}.py", f"{stem}_test.py"}}
    if len(matches) > 1:
        raise ProjectRuntimeError(f"project_test_selection_ambiguous:{relative}; include explicit test paths")
    return matches


def _matches_directory_pattern(path: Path, pattern: str) -> bool:
    """Match native pytest basename and relative/absolute directory patterns."""
    if os.sep != "/" and os.sep not in pattern:
        pattern = pattern.replace("/", os.sep)
    candidate = path.name
    if os.sep in pattern:
        candidate = str(path)
        if path.is_absolute() and not os.path.isabs(pattern):
            pattern = f"*{os.sep}{pattern}"
    return fnmatch.fnmatch(candidate, pattern)


def _candidate_test_files(root: Path, norecursedirs: tuple[str, ...]) -> Iterator[Path]:
    if is_excluded_source(root):
        return
    for directory, directories, files in os.walk(root, followlinks=False):
        directories[:] = [
            name
            for name in directories
            if not is_excluded_source(Path(directory) / name)
            and not any(_matches_directory_pattern(Path(directory) / name, pattern) for pattern in norecursedirs)
        ]
        for name in files:
            if name.endswith(".py"):
                yield Path(directory) / name


def _test_candidates(plan: ProjectPlan, roots: tuple[str, ...], patterns: tuple[str, ...]) -> set[str]:
    recursion = plan.pytest_config.get("norecursedirs", DEFAULT_NORECURSEDIRS)
    norecursedirs = tuple(shlex.split(recursion)) if isinstance(recursion, str) else _strings(recursion)
    return {
        path.relative_to(plan.root).as_posix()
        for root in roots
        for path in _candidate_test_files(plan.root / root, norecursedirs)
        if any(fnmatch.fnmatch(path.name, pattern) for pattern in patterns)
    }


@ensure(lambda result, full: (full or bool(result)) and len(result) == len(set(result)))
def select_test_paths(plan: ProjectPlan, files: list[Path], *, full: bool) -> tuple[str, ...]:
    """Select real native test paths without rewriting the customer's pytest policy."""
    if full:
        # Let target pytest resolve testpaths, fallback discovery and positional addopts.
        return ()
    roots = _strings(plan.pytest_config.get("testpaths")) or (".",)
    patterns = _strings(plan.pytest_config.get("python_files", ["test_*.py", "*_test.py"]))
    candidates = _test_candidates(plan, roots, patterns)
    selected = set()
    for path in files:
        relative = path.resolve().relative_to(plan.root).as_posix()
        if any(fnmatch.fnmatch(path.name, pattern) for pattern in patterns):
            selected.add(relative)
        else:
            selected.update(_matching_source_tests(relative, candidates))
    if not selected:
        raise ProjectRuntimeError("project_test_selection_empty: include corresponding test files")
    return tuple(sorted(selected))


@ensure(lambda result: set(result) == DEPENDENT_MEMBERS)
def preparation_failure_snapshot(reason: str) -> dict[str, dict[str, Any]]:
    """Reference one root cause without producing cascaded synthetic findings."""
    return {
        member: {
            "execution_state": "error",
            "evidence_outcome": "UNKNOWN",
            "diagnostic": "project_runtime_required",
            "runtime_diagnostic": reason,
        }
        for member in DEPENDENT_MEMBERS
    }


def _validate_collection_errors(observation: dict[str, Any]) -> None:
    """Keep collection/plugin errors visible even when other tests fail."""
    if observation.get("collection_errors"):
        raise ProjectRuntimeError(
            "project_pytest_collection_error; --continue-on-collection-errors cannot complete collection; "
            "inspect target_execution"
        )
    if observation.get("internal_errors"):
        raise ProjectRuntimeError(
            "project_pytest_internal_error; inspect target_execution and required plugin configuration"
        )


@require(lambda exit_code: isinstance(exit_code, int))
def validate_observation(observation: dict[str, Any], exit_code: int) -> None:
    """Reject incomplete execution without discarding native pytest selection policy."""
    _validate_collection_errors(observation)
    records = observation["records"]
    collected = set(observation["collected"])
    executed = {row["nodeid"] for row in records if row["phase"] == "call"}
    terminal = executed | {row["nodeid"] for row in records if row["outcome"] == "skipped"}
    if observation["exit_code"] != exit_code or not collected or not executed:
        raise ProjectRuntimeError(
            f"project_pytest_execution_incomplete:exit={exit_code}; check collection/selection options"
        )
    if missing := collected - terminal:
        raise ProjectRuntimeError(
            f"project_pytest_unexecuted:{','.join(sorted(missing))}; check fixture setup and -x/--maxfail options"
        )
    if exit_code not in {0, 1}:
        raise ProjectRuntimeError(f"project_pytest_configuration_or_collection_failed:exit={exit_code}")
    if not observation.get("coverage", {}).get("files"):
        raise ProjectRuntimeError(
            "project_pytest_coverage_missing; enable pytest-cov and remove --no-cov if configured"
        )


@ensure(lambda result: all(isinstance(finding, ReviewFinding) for finding in result))
def run_portable_pytest(files: list[Path], adapter_argv: tuple[str, ...]) -> list[ReviewFinding]:
    """Parse actual child observations while leaving project plugins out of this process."""
    anchor = files[0] if files else Path(".")
    if len(adapter_argv) != 2 or adapter_argv[0] != "portable-pytest-v2":
        return [tool_error(tool="pytest", file_path=anchor, message="project_pytest_request_invalid")]

    command = target_command("pytest-observe", [adapter_argv[1]])
    try:
        Path("/opt/specfact/tmp/pytest-observation.json").unlink(missing_ok=True)
        completed = subprocess.run(command, text=True, capture_output=True, check=False, timeout=1200)
        observation = json.loads(Path("/opt/specfact/tmp/pytest-observation.json").read_text(encoding="utf-8"))
        records = observation["records"]
        validation_error = ""
        try:
            validate_observation(observation, completed.returncode)
        except ProjectRuntimeError as exc:
            validation_error = str(exc)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        return [tool_error(tool="pytest", file_path=anchor, message=str(exc))]
    findings = []
    for record in records:
        if record["outcome"] == "failed":
            findings.append(
                ReviewFinding(
                    category="testing",
                    severity="error",
                    tool="pytest",
                    rule="TEST_OUTCOME_NOT_PASS",
                    file=str(record["nodeid"]).split("::", maxsplit=1)[0],
                    line=1,
                    message=f"Test {record['nodeid']} failed during {record['phase']}.",
                    fixable=False,
                )
            )
    if validation_error:
        findings.append(tool_error(tool="pytest", file_path=anchor, message=validation_error))
    if completed.returncode == 1 and not findings:
        return [tool_error(tool="pytest", file_path=anchor, message="project_pytest_failure_without_observed_test")]
    return findings
