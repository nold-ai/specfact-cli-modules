"""pylint runner for governed code-review findings."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from beartype import beartype
from icontract import ensure, require

from specfact_code_review.run.findings import ReviewFinding


PYLINT_CATEGORY_MAP = {
    "W0702": "architecture",
    "W0703": "architecture",
    "T201": "architecture",
    "W1505": "architecture",
}


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


def _map_severity(message_id: str) -> str:
    if message_id.startswith(("E", "F")):
        return "error"
    if message_id.startswith("I"):
        return "info"
    return "warning"


def _tool_error(file_path: Path, message: str) -> list[ReviewFinding]:
    return [
        ReviewFinding(
            category="tool_error",
            severity="error",
            tool="pylint",
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
def run_pylint(files: list[Path]) -> list[ReviewFinding]:
    """Run pylint and map message IDs into ReviewFinding records."""
    if not files:
        return []

    try:
        result = subprocess.run(
            ["pylint", "--output-format", "json", *(str(file_path) for file_path in files)],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        payload = json.loads(result.stdout)
        if not isinstance(payload, list):
            raise ValueError("pylint output must be a list")
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        return _tool_error(files[0], f"Unable to parse pylint output: {exc}")

    allowed_paths = _allowed_paths(files)
    findings: list[ReviewFinding] = []
    try:
        for item in payload:
            if not isinstance(item, dict):
                raise ValueError("pylint finding must be an object")
            filename = item["path"]
            if not isinstance(filename, str):
                raise ValueError("pylint path must be a string")
            if _normalize_path_variants(filename).isdisjoint(allowed_paths):
                continue
            message_id = item["message-id"]
            if not isinstance(message_id, str):
                raise ValueError("pylint message-id must be a string")
            line = item["line"]
            if not isinstance(line, int):
                raise ValueError("pylint line must be an integer")
            message = item["message"]
            if not isinstance(message, str):
                raise ValueError("pylint message must be a string")
            findings.append(
                ReviewFinding(
                    category=PYLINT_CATEGORY_MAP.get(message_id, "style"),
                    severity=_map_severity(message_id),
                    tool="pylint",
                    rule=message_id,
                    file=filename,
                    line=line,
                    message=message,
                    fixable=False,
                )
            )
    except (KeyError, TypeError, ValueError) as exc:
        return _tool_error(files[0], f"Unable to parse pylint finding payload: {exc}")

    return findings
