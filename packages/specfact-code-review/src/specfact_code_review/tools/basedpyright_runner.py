"""basedpyright runner for governed code-review findings."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Literal

from beartype import beartype
from icontract import require

from specfact_code_review._review_utils import normalize_path_variants, python_source_paths_for_tools, tool_error
from specfact_code_review.run.findings import ReviewFinding
from specfact_code_review.tools.tool_availability import skip_if_tool_missing


_COMPLETED_EXIT_CODES = frozenset({0, 1})
_STDERR_SNIP_MAX = 4000


def _allowed_paths(files: list[Path]) -> set[str]:
    allowed: set[str] = set()
    for file_path in files:
        allowed.update(normalize_path_variants(file_path))
    return allowed


def _map_severity(raw_severity: str) -> Literal["error", "warning", "info"]:
    if raw_severity == "error":
        return "error"
    if raw_severity == "warning":
        return "warning"
    return "info"


def _finding_from_diagnostic(diagnostic: object, *, allowed_paths: set[str]) -> ReviewFinding | None:
    if not isinstance(diagnostic, dict):
        raise ValueError("basedpyright diagnostic must be an object")

    filename = diagnostic["file"]
    if not isinstance(filename, str):
        raise ValueError("basedpyright filename must be a string")
    if normalize_path_variants(filename).isdisjoint(allowed_paths):
        return None

    raw_severity = diagnostic["severity"]
    if not isinstance(raw_severity, str):
        raise ValueError("basedpyright severity must be a string")
    message = diagnostic["message"]
    if not isinstance(message, str):
        raise ValueError("basedpyright message must be a string")
    line = diagnostic["range"]["start"]["line"]
    if not isinstance(line, int):
        raise ValueError("basedpyright line must be an integer")
    rule = diagnostic.get("rule")
    if rule is not None and not isinstance(rule, str):
        raise ValueError("basedpyright rule must be a string when present")

    return ReviewFinding(
        category="type_safety",
        severity=_map_severity(raw_severity),
        tool="basedpyright",
        rule=rule or "basedpyright",
        file=filename,
        line=line + 1,
        message=message,
        fixable=False,
    )


def _diagnostics_from_output(stdout: str) -> list[object]:
    payload = json.loads(stdout)
    if not isinstance(payload, dict):
        raise ValueError("basedpyright output must be an object")
    diagnostics = payload["generalDiagnostics"]
    if not isinstance(diagnostics, list):
        raise ValueError("generalDiagnostics must be a list")
    return diagnostics


def _validate_process_completion(result: subprocess.CompletedProcess[str]) -> None:
    """Reject fatal/configuration/argument exits even when stdout parses."""

    if result.returncode in _COMPLETED_EXIT_CODES:
        return
    stderr = result.stderr.strip()
    if len(stderr) > _STDERR_SNIP_MAX:
        stderr = "…" + stderr[-_STDERR_SNIP_MAX:]
    raise ValueError(f"basedpyright process failed (returncode={result.returncode}); stderr={stderr!r}")


def _findings_from_diagnostics(diagnostics: list[object], *, allowed_paths: set[str]) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    for diagnostic in diagnostics:
        finding = _finding_from_diagnostic(diagnostic, allowed_paths=allowed_paths)
        if finding is not None:
            findings.append(finding)
    return findings


@beartype
@require(lambda files: isinstance(files, list), "files must be a list")
@require(lambda files: all(isinstance(file_path, Path) for file_path in files), "files must contain Path instances")
def run_basedpyright(files: list[Path], *, extra_args: tuple[str, ...] = ()) -> list[ReviewFinding]:
    """Run basedpyright and map diagnostics into ReviewFinding records."""
    files = python_source_paths_for_tools(files)
    if not files:
        return []

    skipped = skip_if_tool_missing("basedpyright", files[0])
    if skipped:
        return skipped

    try:
        projected_source_args = () if extra_args else tuple(str(file_path) for file_path in files)
        result = subprocess.run(
            [
                "basedpyright",
                "--outputjson",
                *(extra_args or ("--project", ".")),
                *projected_source_args,
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        _validate_process_completion(result)
        diagnostics = _diagnostics_from_output(result.stdout)
    except (OSError, ValueError, json.JSONDecodeError, KeyError, subprocess.TimeoutExpired) as exc:
        return [
            tool_error(
                tool="basedpyright",
                file_path=files[0],
                message=f"Unable to parse basedpyright output: {exc}",
            )
        ]

    allowed_paths = _allowed_paths(files)
    try:
        return _findings_from_diagnostics(diagnostics, allowed_paths=allowed_paths)
    except (KeyError, TypeError, ValueError) as exc:
        return [
            tool_error(
                tool="basedpyright",
                file_path=files[0],
                message=f"Unable to parse basedpyright finding payload: {exc}",
            )
        ]
