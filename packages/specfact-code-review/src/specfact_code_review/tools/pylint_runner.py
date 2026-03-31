"""pylint runner for governed code-review findings."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Literal

from beartype import beartype
from icontract import ensure, require

from specfact_code_review._review_utils import normalize_path_variants, tool_error
from specfact_code_review.run.findings import ReviewFinding


PYLINT_CATEGORY_MAP: dict[str, Literal["architecture"]] = {
    "W0702": "architecture",
    "W0703": "architecture",
    "T201": "architecture",
    "W1505": "architecture",
}


def _allowed_paths(files: list[Path]) -> set[str]:
    allowed: set[str] = set()
    for file_path in files:
        allowed.update(normalize_path_variants(file_path))
    return allowed


def _map_severity(message_id: str) -> Literal["error", "warning", "info"]:
    if message_id.startswith(("E", "F")):
        return "error"
    if message_id.startswith("I"):
        return "info"
    return "warning"


def _category_for_message_id(message_id: str) -> Literal["architecture", "style"]:
    if message_id in PYLINT_CATEGORY_MAP:
        return "architecture"
    return "style"


def _finding_from_item(item: object, *, allowed_paths: set[str]) -> ReviewFinding | None:
    if not isinstance(item, dict):
        raise ValueError("pylint finding must be an object")

    filename = item["path"]
    if not isinstance(filename, str):
        raise ValueError("pylint path must be a string")
    if normalize_path_variants(filename).isdisjoint(allowed_paths):
        return None

    message_id = item["message-id"]
    if not isinstance(message_id, str):
        raise ValueError("pylint message-id must be a string")
    line = item["line"]
    if not isinstance(line, int):
        raise ValueError("pylint line must be an integer")
    message = item["message"]
    if not isinstance(message, str):
        raise ValueError("pylint message must be a string")

    return ReviewFinding(
        category=_category_for_message_id(message_id),
        severity=_map_severity(message_id),
        tool="pylint",
        rule=message_id,
        file=filename,
        line=line,
        message=message,
        fixable=False,
    )


def _payload_from_output(stdout: str) -> list[object]:
    payload = json.loads(stdout)
    if not isinstance(payload, list):
        raise ValueError("pylint output must be a list")
    return payload


def _findings_from_payload(payload: list[object], *, allowed_paths: set[str]) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    for item in payload:
        finding = _finding_from_item(item, allowed_paths=allowed_paths)
        if finding is not None:
            findings.append(finding)
    return findings


def _result_is_review_findings(result: list[ReviewFinding]) -> bool:
    return all(isinstance(finding, ReviewFinding) for finding in result)


@beartype
@require(lambda files: isinstance(files, list), "files must be a list")
@require(lambda files: all(isinstance(file_path, Path) for file_path in files), "files must contain Path instances")
@ensure(lambda result: isinstance(result, list), "result must be a list")
@ensure(_result_is_review_findings, "result must contain ReviewFinding instances")
def run_pylint(files: list[Path]) -> list[ReviewFinding]:
    """Run pylint and map message IDs into ReviewFinding records."""
    if not files:
        return []

    try:
        result = subprocess.run(
            ["pylint", "--output-format", "json", *[str(file_path) for file_path in files]],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        payload = _payload_from_output(result.stdout)
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        return [tool_error(tool="pylint", file_path=files[0], message=f"Unable to parse pylint output: {exc}")]

    allowed_paths = _allowed_paths(files)
    try:
        return _findings_from_payload(payload, allowed_paths=allowed_paths)
    except (KeyError, TypeError, ValueError) as exc:
        return [
            tool_error(
                tool="pylint",
                file_path=files[0],
                message=f"Unable to parse pylint finding payload: {exc}",
            )
        ]
