"""Portable runtime scope selection and sealed-parent target-worker adapters."""

from __future__ import annotations

import fnmatch
import glob
import json
import os
import shlex
import subprocess
from collections import Counter
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, Literal

from icontract import ensure, require

from specfact_code_review._review_utils import tool_error
from specfact_code_review.run.findings import (
    PytestDiagnostic,
    PytestExceptionKind,
    PytestPhase,
    PytestStableCode,
    ReviewFinding,
)
from specfact_code_review.run.installed_coverage import (
    CoverageBridge,
    attribute_installed_coverage,
    plan_installed_coverage,
)
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


def _matching_source_tests(
    relative: str, candidates: set[str], explicit_tests: set[str], *, multiple_sources: bool
) -> set[str]:
    stem = Path(relative).stem
    matches = {candidate for candidate in candidates if Path(candidate).name in {f"test_{stem}.py", f"{stem}_test.py"}}
    if selected := matches & explicit_tests:
        if multiple_sources and selected != matches:
            raise ProjectRuntimeError(
                f"project_test_selection_ambiguous:{relative}; include all matching test paths or use full scope"
            )
        return selected
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


def _test_root_files(root: Path, norecursedirs: tuple[str, ...]) -> Iterator[Path]:
    """Explicit file roots and directory roots use the same Python-file boundary."""
    if root.is_file():
        if root.suffix == ".py":
            yield root
    else:
        yield from _candidate_test_files(root, norecursedirs)


def _contained_test_path(root: Path, relative: str) -> Path:
    """Check literal patterns and expanded paths before walking candidate roots."""
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise ProjectRuntimeError(f"project_test_path_escape:{relative}; keep testpaths inside the reviewed repository")
    return path


def _expanded_test_roots(plan: ProjectPlan, roots: tuple[str, ...]) -> tuple[Path, ...]:
    """Match native pytest's glob expansion and all-missing-path fallback."""
    expanded = set()
    for pattern in roots:
        _contained_test_path(plan.root, pattern)
        for relative in glob.iglob(pattern, root_dir=plan.root, recursive=True):
            expanded.add(_contained_test_path(plan.root, relative))
    return tuple(sorted(expanded)) or (plan.root,)


def _excluded_test_root(path: Path, project: Path) -> bool:
    """Expanded file roots must retain excluded-directory ancestry."""
    return any(is_excluded_source(entry) for entry in (path, *path.parents) if entry.is_relative_to(project))


def _test_candidates(plan: ProjectPlan, roots: tuple[str, ...], patterns: tuple[str, ...]) -> set[str]:
    recursion = plan.pytest_config.get("norecursedirs", DEFAULT_NORECURSEDIRS)
    norecursedirs = tuple(shlex.split(recursion)) if isinstance(recursion, str) else _strings(recursion)
    return {
        path.relative_to(plan.root).as_posix()
        for root in _expanded_test_roots(plan, roots)
        if not _excluded_test_root(root, plan.root)
        for path in _test_root_files(root, norecursedirs)
        if any(fnmatch.fnmatch(path.name, pattern) for pattern in patterns)
    }


def contract_inputs(plan: ProjectPlan) -> tuple[str, ...]:
    """Exclude declared test roots or actual default-discovery tests, never all source."""
    roots = _strings(plan.pytest_config.get("testpaths"))
    if not roots or "." in roots:
        patterns = _strings(plan.pytest_config.get("python_files", ["test_*.py", "*_test.py"]))
        roots = tuple(sorted(_test_candidates(plan, roots or (".",), patterns)))
    if not roots:
        return ("contract-inputs-v2",)  # Explicit empty test inventory: retain all production inputs.
    return ("contract-inputs-v1", *(value for root in roots for value in ("--test-root", root)))


@ensure(lambda result, full: (full or bool(result)) and len(result) == len(set(result)))
def select_test_paths(plan: ProjectPlan, files: list[Path], *, full: bool) -> tuple[str, ...]:
    """Select real native test paths without rewriting the customer's pytest policy."""
    if full:
        # Let target pytest resolve testpaths, fallback discovery and positional addopts.
        return ()
    roots = _strings(plan.pytest_config.get("testpaths")) or (".",)
    patterns = _strings(plan.pytest_config.get("python_files", ["test_*.py", "*_test.py"]))
    candidates = _test_candidates(plan, roots, patterns)
    relative_paths = [path.resolve().relative_to(plan.root).as_posix() for path in files]
    explicit_tests = {
        relative
        for relative in relative_paths
        if any(fnmatch.fnmatch(Path(relative).name, pattern) for pattern in patterns)
    }
    source_modules = {
        Path(relative).with_suffix("")
        for relative in set(relative_paths) - explicit_tests
        if Path(relative).suffix in {".py", ".pyi"}
    }
    source_stems = Counter(path.name for path in source_modules)
    selected = set(explicit_tests)
    for relative in relative_paths:
        if relative not in explicit_tests and Path(relative).suffix in {".py", ".pyi"}:
            selected.update(
                _matching_source_tests(
                    relative, candidates, explicit_tests, multiple_sources=source_stems[Path(relative).stem] > 1
                )
            )
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


class _PytestValidationError(ProjectRuntimeError):
    def __init__(self, message: str, code: PytestStableCode | None) -> None:
        super().__init__(message)
        self.code: PytestStableCode | None = code


class _PytestOperationError(ValueError):
    def __init__(self, error: Exception, phase: PytestPhase, message: str | None = None) -> None:
        super().__init__(str(error) if message is None else message)
        self.error = error
        self.phase: PytestPhase = phase


@ensure(lambda result: isinstance(result, PytestDiagnostic))
def pytest_failure_diagnostic(
    error: Exception,
    *,
    phase: PytestPhase,
    child_returncode: int | None = None,
    observation_state: Literal["not_read", "read_failed", "decode_failed", "decoded"] = "not_read",
    stable_code: PytestStableCode | None = None,
) -> PytestDiagnostic:
    """Map actual exceptions in subtype order without reading private messages."""
    if isinstance(error, _PytestOperationError):
        phase, error = error.phase, error.error
        if phase == "request":
            stable_code = "project_pytest_request_invalid"
    classes: tuple[tuple[type[Exception], PytestExceptionKind], ...] = (
        (FileNotFoundError, "FileNotFoundError"),
        (PermissionError, "PermissionError"),
        (json.JSONDecodeError, "JSONDecodeError"),
        (UnicodeDecodeError, "UnicodeDecodeError"),
        (ProjectRuntimeError, "ProjectRuntimeError"),
        (subprocess.TimeoutExpired, "TimeoutExpired"),
        (subprocess.CalledProcessError, "CalledProcessError"),
        (subprocess.SubprocessError, "SubprocessError"),
        (OSError, "OSError"),
        (ValueError, "ValueError"),
        (TypeError, "TypeError"),
        (KeyError, "KeyError"),
    )
    kind: PytestExceptionKind = "other"
    for cls, name in classes:
        if isinstance(error, cls):
            kind = name
            break
    if isinstance(error, _PytestValidationError):
        stable_code = error.code
    return PytestDiagnostic(
        phase=phase,
        exception_kind=kind,
        stable_code=stable_code,
        child_returncode=child_returncode,
        observation_state=observation_state,
    )


def _pytest_tool_error(
    anchor: Path,
    error: Exception,
    *,
    phase: PytestPhase,
    child_returncode: int | None = None,
    observation_state: Literal["not_read", "read_failed", "decode_failed", "decoded"] = "not_read",
    stable_code: PytestStableCode | None = None,
    message: str | None = None,
) -> ReviewFinding:
    finding = tool_error(tool="pytest", file_path=anchor, message=str(error) if message is None else message)
    finding.native_diagnostic = pytest_failure_diagnostic(
        error,
        phase=phase,
        child_returncode=child_returncode,
        observation_state=observation_state,
        stable_code=stable_code,
    )
    return finding


def _validate_collection_errors(observation: dict[str, Any]) -> None:
    """Keep collection/plugin errors visible even when other tests fail."""
    if observation.get("collection_errors"):
        raise _PytestValidationError(
            "project_pytest_collection_error; --continue-on-collection-errors cannot complete collection; "
            "inspect target_execution",
            "project_pytest_collection_error",
        )
    if observation.get("internal_errors"):
        raise _PytestValidationError(
            "project_pytest_internal_error; inspect target_execution and required plugin configuration",
            "project_pytest_internal_error",
        )


def _missing_coverage_diagnostic(observation: dict[str, Any]) -> str:
    """Preserve a specific worker remedy without coercing malformed diagnostic objects."""
    diagnostic = observation.get("coverage_diagnostic", "")
    if not isinstance(diagnostic, str):
        return "project_pytest_coverage_diagnostic_invalid; inspect target_execution coverage_diagnostic"
    return diagnostic or "project_pytest_coverage_missing; enable pytest-cov and remove --no-cov if configured"


@require(lambda exit_code: isinstance(exit_code, int))
def validate_observation(observation: dict[str, Any], exit_code: int) -> None:
    """Reject incomplete execution without discarding native pytest selection policy."""
    _validate_collection_errors(observation)
    if exit_code == 4:
        raise _PytestValidationError(
            "project_pytest_configuration_or_collection_failed:exit=4; inspect target_execution and pytest options",
            "project_pytest_configuration_or_collection_failed",
        )
    records = observation["records"]
    collected = set(observation["collected"])
    executed = {row["nodeid"] for row in records if row["phase"] == "call"}
    terminal = executed | {row["nodeid"] for row in records if row["outcome"] == "skipped"}
    if observation["exit_code"] != exit_code or not collected or not executed:
        raise _PytestValidationError(
            f"project_pytest_execution_incomplete:exit={exit_code}; check collection/selection options",
            "project_pytest_execution_incomplete",
        )
    if missing := collected - terminal:
        raise _PytestValidationError(
            f"project_pytest_unexecuted:{','.join(sorted(missing))}; check fixture setup and -x/--maxfail options",
            "project_pytest_unexecuted",
        )
    if exit_code not in {0, 1}:
        raise _PytestValidationError(
            f"project_pytest_configuration_or_collection_failed:exit={exit_code}",
            "project_pytest_configuration_or_collection_failed",
        )
    if not observation.get("coverage", {}).get("files"):
        code: PytestStableCode | None = None
        if not isinstance(observation.get("coverage_diagnostic", ""), str):
            code = "project_pytest_coverage_diagnostic_invalid"
        elif not observation.get("coverage_diagnostic"):
            code = "project_pytest_coverage_missing"
        raise _PytestValidationError(_missing_coverage_diagnostic(observation), code)


def _nonpassing_observation_findings(records: list[dict[str, Any]], pytest_root: Path) -> list[ReviewFinding]:
    findings = []
    for record in records:
        has_xfail = bool(record.get("has_xfail") or record.get("wasxfail"))
        if record["outcome"] != "passed" or has_xfail:
            findings.append(
                ReviewFinding(
                    category="testing",
                    severity="error",
                    tool="pytest",
                    rule="TEST_OUTCOME_NOT_PASS",
                    file=(pytest_root / str(record["nodeid"]).split("::", maxsplit=1)[0])
                    .resolve()
                    .relative_to(Path(".").resolve())
                    .as_posix(),
                    line=1,
                    message=(
                        f"Test {record['nodeid']} {record['outcome']} during {record['phase']}"
                        + (" with an xfail marker." if has_xfail else ".")
                    ),
                    fixable=False,
                )
            )
    return findings


def _coverage_percentage(value: object) -> bool:
    """Accept only finite native percentages, excluding Boolean integer subclasses."""
    return not isinstance(value, bool) and isinstance(value, int | float) and 0 <= value <= 100


def _coverage_policy_fields(policy: dict[str, Any]) -> dict[str, bool]:
    """Check the bounded native receipt's scalar types and percentage ranges."""
    precision = policy.get("precision")
    return {
        "mode": policy.get("mode") in ("native", "reviewer", "disabled"),
        "threshold": _coverage_percentage(policy.get("threshold")),
        "precision": isinstance(precision, int) and not isinstance(precision, bool) and 0 <= precision <= 9,
        "measured_total": "measured_total" in policy
        and (policy["measured_total"] is None or _coverage_percentage(policy["measured_total"])),
        "native_threshold_failed": isinstance(policy.get("native_threshold_failed"), bool),
    }


def _validate_coverage_policy(policy: object, exit_code: int) -> dict[str, Any]:
    """Validate the native receipt without duplicating Coverage's rounding policy."""
    if not isinstance(policy, dict):
        raise ValueError("expected coverage_policy object")
    if invalid := [field for field, valid in _coverage_policy_fields(policy).items() if not valid]:
        raise ValueError(f"invalid fields: {','.join(invalid)}")
    if policy["native_threshold_failed"] and (
        policy["mode"] != "native" or policy["measured_total"] is None or exit_code != 1
    ):
        raise ValueError("failed native threshold requires native mode, measured total and pytest exit 1")
    return policy


def _coverage_policy_findings(observation: dict[str, Any], exit_code: int, anchor: Path) -> list[ReviewFinding]:
    """Expose actual native aggregate failures separately from per-source review coverage."""
    if "coverage_policy" not in observation:
        return []
    try:
        policy = _validate_coverage_policy(observation["coverage_policy"], exit_code)
    except ValueError as exc:
        return [
            _pytest_tool_error(
                anchor,
                exc,
                phase="policy",
                child_returncode=exit_code,
                observation_state="decoded",
                stable_code="project_pytest_coverage_policy_invalid",
                message=f"project_pytest_coverage_policy_invalid:{exc}; inspect target_execution coverage_policy",
            )
        ]
    if not policy["native_threshold_failed"]:
        return []
    return [
        ReviewFinding(
            category="testing",
            severity="error",
            tool="pytest",
            rule="TEST_COVERAGE_POLICY_FAILED",
            file=str(anchor),
            line=1,
            message=(
                f"Native aggregate coverage {policy['measured_total']}% failed its configured "
                f"{policy['threshold']}% threshold (precision={policy['precision']}); "
                "increase coverage to satisfy the repository's native policy."
            ),
            fixable=False,
        )
    ]


def _installed_coverage_findings(
    files: list[Path],
    bridge: CoverageBridge,
    observation: dict[str, Any],
    evaluate: Callable[[list[Path], dict[str, Any]], list[ReviewFinding]],
    *,
    child_returncode: int,
) -> list[ReviewFinding]:
    """Retain native evidence and turn unavailable attribution into a named diagnostic."""
    try:
        coverage, attribution_errors = attribute_installed_coverage(
            bridge,
            observation["coverage"],
            snapshot=Path(".").resolve(),
            relocations=observation.get("coverage_relocations"),
        )
        if bridge.mappings or attribution_errors:
            observation["coverage_attribution"] = {
                "mappings": [
                    {
                        "source": str(row.source),
                        "installed": str(row.installed),
                        "sha256": row.digest,
                        "distribution": row.distribution,
                    }
                    for row in bridge.mappings
                ],
                "diagnostics": attribution_errors,
            }
            Path("/opt/specfact/tmp/pytest-observation.json").write_text(json.dumps(observation), encoding="utf-8")
        return evaluate(files, {**observation, "coverage": coverage, "coverage_attribution_errors": attribution_errors})
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return [
            _pytest_tool_error(
                files[0] if files else Path("."),
                exc,
                phase="installed_coverage",
                child_returncode=child_returncode,
                observation_state="decoded",
                stable_code="project_pytest_installed_coverage_unavailable",
                message=f"project_pytest_installed_coverage_unavailable:{exc}",
            )
        ]


def _portable_pytest_command(files: list[Path], encoded: str) -> tuple[CoverageBridge, list[str]]:
    """Bind native measurement inputs to controller-verified installed ownership."""
    try:
        request = json.loads(encoded)
    except ValueError as exc:
        raise _PytestOperationError(exc, "request", "project_pytest_request_invalid") from exc
    if not isinstance(request, dict):
        raise _PytestOperationError(ValueError("project_pytest_request_invalid"), "request")
    selectors = request.get("selectors")
    if not isinstance(selectors, list) or any(not isinstance(value, str) or not value for value in selectors):
        raise _PytestOperationError(ValueError("project_pytest_request_invalid"), "request")
    try:
        bridge = plan_installed_coverage(
            files, snapshot=Path(".").resolve(), site_packages=Path("/opt/specfact/project-runtime/site-packages")
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise _PytestOperationError(exc, "coverage_plan") from exc
    request["coverage_directories"] = [str(path) for path in bridge.directories]
    request["coverage_modules"] = list(bridge.modules)
    request["coverage_candidates"] = sorted(
        {path for paths in bridge.candidates.values() for path in paths} | set(bridge.measured_origins)
    )
    try:
        command = target_command("pytest-observe", [json.dumps(request)])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise _PytestOperationError(exc, "target_command") from exc
    return bridge, command


@ensure(lambda result: all(isinstance(finding, ReviewFinding) for finding in result))
def run_portable_pytest(files: list[Path], adapter_argv: tuple[str, ...]) -> list[ReviewFinding]:
    """Parse actual child observations while leaving project plugins out of this process."""
    anchor = files[0] if files else Path(".")
    if len(adapter_argv) != 2 or adapter_argv[0] != "portable-pytest-v2":
        return [
            _pytest_tool_error(
                anchor,
                ValueError("project_pytest_request_invalid"),
                phase="request",
                stable_code="project_pytest_request_invalid",
            )
        ]
    phase: PytestPhase = "observation_cleanup"
    returncode: int | None = None
    observation_state: Literal["not_read", "read_failed", "decode_failed", "decoded"] = "not_read"
    try:
        Path("/opt/specfact/tmp/pytest-observation.json").unlink(missing_ok=True)
        phase = "request"
        bridge, command = _portable_pytest_command(files, adapter_argv[1])
        phase = "child_execution"
        completed = subprocess.run(command, text=True, capture_output=True, check=False, timeout=1200)
        returncode = completed.returncode
        phase, observation_state = "observation_read", "read_failed"
        raw = Path("/opt/specfact/tmp/pytest-observation.json").read_text(encoding="utf-8")
        phase, observation_state = "observation_decode", "decode_failed"
        observation = json.loads(raw)
        phase, observation_state = "observation_records", "decoded"
        records = observation["records"]
        phase = "policy"
        policy_findings = _coverage_policy_findings(observation, completed.returncode, anchor)
        validation_finding = None
        phase = "validation"
        try:
            validate_observation(observation, completed.returncode)
        except ProjectRuntimeError as exc:
            validation_finding = _pytest_tool_error(
                anchor, exc, phase=phase, child_returncode=returncode, observation_state=observation_state
            )
        if validation_finding is not None and not records:
            return [*policy_findings, validation_finding]
        from specfact_code_review.run.runner import evaluate_portable_pytest_coverage, resolve_portable_pytest_root

        phase = "root"
        pytest_root = resolve_portable_pytest_root(observation)
        phase = "findings"
        findings = [*policy_findings, *_nonpassing_observation_findings(records, pytest_root)]
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        return [
            _pytest_tool_error(
                anchor, exc, phase=phase, child_returncode=returncode, observation_state=observation_state
            )
        ]
    if validation_finding is not None:
        findings.append(validation_finding)
    else:
        findings.extend(
            _installed_coverage_findings(
                files, bridge, observation, evaluate_portable_pytest_coverage, child_returncode=completed.returncode
            )
        )
    if completed.returncode == 1 and not findings:
        return [
            _pytest_tool_error(
                anchor,
                ValueError("project_pytest_failure_without_observed_test"),
                phase="findings",
                child_returncode=returncode,
                observation_state="decoded",
                stable_code="project_pytest_failure_without_observed_test",
            )
        ]
    return findings
