"""basedpyright runner for governed code-review findings."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from beartype import beartype
from icontract import ensure, require

from specfact_code_review.run.findings import ReviewFinding


def _normalize_path_variants(path_value: str | Path) -> set[str]:
    path = Path(path_value)
    variants = {
        os.path.normpath(str(path)),
        os.path.normpath(path.as_posix()),
    }
    try:
        resolved = path.resolve()
    except OSError:
        return variants
    variants.add(os.path.normpath(str(resolved)))
    variants.add(os.path.normpath(resolved.as_posix()))
    return variants


def _allowed_paths(files: list[Path]) -> set[str]:
    allowed: set[str] = set()
    for file_path in files:
        allowed.update(_normalize_path_variants(file_path))
    return allowed


def _map_severity(raw_severity: str) -> str:
    if raw_severity == "error":
        return "error"
    if raw_severity == "warning":
        return "warning"
    return "info"


def _tool_error(file_path: Path, message: str) -> list[ReviewFinding]:
    return [
        ReviewFinding(
            category="tool_error",
            severity="error",
            tool="basedpyright",
            rule="tool_error",
            file=str(file_path),
            line=1,
            message=message,
            fixable=False,
        )
    ]


@beartype
@require(lambda files: isinstance(files, list), "files must be a list")
@require(lambda files: all(isinstance(file_path, Path) for file_path in files), "files must contain Path instances")
@ensure(lambda result: isinstance(result, list), "result must be a list")
@ensure(
    lambda result: all(isinstance(finding, ReviewFinding) for finding in result),
    "result must contain ReviewFinding instances",
)
def run_basedpyright(files: list[Path]) -> list[ReviewFinding]:
    """Run basedpyright and map diagnostics into ReviewFinding records."""
    if not files:
        return []

    try:
        result = subprocess.run(
            ["basedpyright", "--outputjson", "--project", ".", *(str(file_path) for file_path in files)],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict):
            raise ValueError("basedpyright output must be an object")
        diagnostics = payload["generalDiagnostics"]
        if not isinstance(diagnostics, list):
            raise ValueError("generalDiagnostics must be a list")
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError, KeyError, subprocess.TimeoutExpired) as exc:
        return _tool_error(files[0], f"Unable to parse basedpyright output: {exc}")

    allowed_paths = _allowed_paths(files)
    findings: list[ReviewFinding] = []
    try:
        for diagnostic in diagnostics:
            if not isinstance(diagnostic, dict):
                raise ValueError("basedpyright diagnostic must be an object")
            filename = diagnostic["file"]
            if not isinstance(filename, str):
                raise ValueError("basedpyright filename must be a string")
            if _normalize_path_variants(filename).isdisjoint(allowed_paths):
                continue
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
            findings.append(
                ReviewFinding(
                    category="type_safety",
                    severity=_map_severity(raw_severity),
                    tool="basedpyright",
                    rule=rule or "basedpyright",
                    file=filename,
                    line=line + 1,
                    message=message,
                    fixable=False,
                )
            )
    except (KeyError, TypeError, ValueError) as exc:
        return _tool_error(files[0], f"Unable to parse basedpyright finding payload: {exc}")

    return findings
