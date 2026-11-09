from __future__ import annotations

import re
from typing import TypedDict

from beartype import beartype
from icontract import ensure, require


__all__ = [
    "_strip_ansi_codes",
    "extract_basedpyright_findings",
    "extract_crosshair_findings",
    "extract_pytest_findings",
    "extract_ruff_findings",
    "extract_semgrep_findings",
]


class _RuffViolation(TypedDict):
    file: str
    line: int
    column: int
    code: str
    message: str


class _LocatedMessage(TypedDict):
    file: str
    line: int
    column: int
    message: str


class _Counterexample(TypedDict):
    file: str
    line: int
    type: str


class _RuffFindings(TypedDict):
    violations: list[_RuffViolation]
    total_violations: int
    files_checked: int


class _SemgrepFindings(TypedDict):
    findings: list[object]
    total_findings: int
    rules_run: int
    targets_scanned: int


class _BasedpyrightFindings(TypedDict):
    errors: list[_LocatedMessage]
    warnings: list[_LocatedMessage]
    total_errors: int
    total_warnings: int


class _CrosshairFindings(TypedDict):
    counterexamples: list[_Counterexample]
    total_counterexamples: int


class _PytestFindings(TypedDict):
    tests_run: int
    tests_passed: int
    tests_failed: int
    tests_skipped: int
    failures: list[object]


@beartype
@require(lambda text: isinstance(text, str), "Text must be string")
@ensure(lambda result: isinstance(result, str), "Must return string")
def _strip_ansi_codes(text: str) -> str:
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


@beartype
@require(lambda output: isinstance(output, str), "Output must be string")
@ensure(lambda result: isinstance(result, dict), "Must return dictionary")
@ensure(
    lambda result: "violations" in result and "total_violations" in result,
    "Must include violations and total_violations",
)
def extract_ruff_findings(output: str) -> dict[str, object]:
    findings: _RuffFindings = {"violations": [], "total_violations": 0, "files_checked": 0}
    clean_output = _strip_ansi_codes(output)
    lines = clean_output.split("\n")
    i = 0
    while i < len(lines):
        line_stripped = lines[i].strip()
        if not line_stripped:
            i += 1
            continue
        if line_stripped.startswith(("help:", "|", "    |")):
            i += 1
            continue
        code_match = re.match("^([A-Z]\\d+)\\s+\\[[^\\]]+\\]\\s+(.+)$", line_stripped)
        if code_match and i + 1 < len(lines):
            code = code_match.group(1)
            message = code_match.group(2)
            location_line = lines[i + 1].strip()
            location_match = re.match("-->\\s+([^:]+):(\\d+):(\\d+)", location_line)
            if location_match:
                file_path = location_match.group(1)
                line_num = int(location_match.group(2))
                col_num = int(location_match.group(3))
                findings["violations"].append(
                    {"file": file_path, "line": line_num, "column": col_num, "code": code, "message": message}
                )
                i += 2
                continue
        pattern = "^([^:]+):(\\d+):(\\d+):\\s+([A-Z]\\d+)\\s+(.+)$"
        match = re.match(pattern, line_stripped)
        if match:
            file_path, line_num, col_num, code, message = match.groups()
            findings["violations"].append(
                {"file": file_path, "line": int(line_num), "column": int(col_num), "code": code, "message": message}
            )
        i += 1
    findings["total_violations"] = len(findings["violations"])
    files_match = re.search("(\\d+)\\s+files?\\s+checked", clean_output, re.IGNORECASE)
    if files_match:
        findings["files_checked"] = int(files_match.group(1))
    return dict(findings)


@beartype
@require(lambda output: isinstance(output, str), "Output must be string")
@require(lambda error: isinstance(error, str), "Error must be string")
@ensure(lambda result: isinstance(result, dict), "Must return dictionary")
@ensure(lambda result: "total_findings" in result, "Must include total_findings")
def extract_semgrep_findings(output: str, error: str) -> dict[str, object]:
    findings: _SemgrepFindings = {
        "findings": [],
        "total_findings": 0,
        "rules_run": 0,
        "targets_scanned": 0,
    }

    # Combine output and error (semgrep uses stderr for status)
    combined = _strip_ansi_codes((output + "\n" + error).strip())

    findings_match = re.search(r"Findings:\s*(\d+)", combined, re.IGNORECASE)
    if findings_match:
        findings["total_findings"] = int(findings_match.group(1))

    rules_match = re.search(r"Rules\s+run:\s*(\d+)", combined, re.IGNORECASE)
    if rules_match:
        findings["rules_run"] = int(rules_match.group(1))

    targets_match = re.search(r"Targets\s+scanned:\s*(\d+)", combined, re.IGNORECASE)
    if targets_match:
        findings["targets_scanned"] = int(targets_match.group(1))

    return dict(findings)


@beartype
@require(lambda output: isinstance(output, str), "Output must be string")
@ensure(lambda result: isinstance(result, dict), "Must return dictionary")
@ensure(lambda result: "errors" in result and "warnings" in result, "Must include errors and warnings")
def extract_basedpyright_findings(output: str) -> dict[str, object]:
    findings: _BasedpyrightFindings = {
        "errors": [],
        "warnings": [],
        "total_errors": 0,
        "total_warnings": 0,
    }

    clean_output = _strip_ansi_codes(output)

    patterns = [
        r"^([^:]+):(\d+):(\d+):\s+(error|warning):\s+(.+)$",
        r"^\s*([^:]+):(\d+):(\d+)\s+-\s+(error|warning):\s+(.+)$",
    ]
    for line in clean_output.split("\n"):
        line_stripped = line.strip()
        if not line_stripped:
            continue
        match = None
        for pattern in patterns:
            match = re.match(pattern, line_stripped)
            if match:
                break
        if match:
            file_path, line_num, col_num, level, message = match.groups()
            finding: _LocatedMessage = {
                "file": file_path,
                "line": int(line_num),
                "column": int(col_num),
                "message": message,
            }
            if level == "error":
                findings["errors"].append(finding)
                findings["total_errors"] += 1
            else:
                findings["warnings"].append(finding)
                findings["total_warnings"] += 1

    if findings["total_errors"] == 0 and findings["total_warnings"] == 0:
        summary_match = re.search(r"(\d+)\s+errors?,\s+(\d+)\s+warnings?", clean_output, re.IGNORECASE)
        if summary_match:
            findings["total_errors"] = int(summary_match.group(1))
            findings["total_warnings"] = int(summary_match.group(2))

    return dict(findings)


@beartype
@require(lambda output: isinstance(output, str), "Output must be string")
@ensure(lambda result: isinstance(result, dict), "Must return dictionary")
@ensure(lambda result: "counterexamples" in result, "Must include counterexamples")
def extract_crosshair_findings(output: str) -> dict[str, object]:
    findings: _CrosshairFindings = {
        "counterexamples": [],
        "total_counterexamples": 0,
    }

    clean_output = _strip_ansi_codes(output)

    # CrossHair typically outputs counterexamples
    # Format varies, but we can extract basic info
    if "counterexample" in clean_output.lower() or "failed" in clean_output.lower():
        pattern = r"([^:]+):(\d+):.*?(counterexample|failed)"
        matches = re.finditer(pattern, clean_output, re.IGNORECASE)
        for match in matches:
            findings["counterexamples"].append(
                {
                    "file": match.group(1),
                    "line": int(match.group(2)),
                    "type": match.group(3).lower(),
                }
            )
            findings["total_counterexamples"] += 1

    return dict(findings)


@beartype
@require(lambda output: isinstance(output, str), "Output must be string")
@ensure(lambda result: isinstance(result, dict), "Must return dictionary")
@ensure(lambda result: "tests_run" in result, "Must include tests_run")
@ensure(lambda result: result["tests_run"] >= 0, "tests_run must be non-negative")
def extract_pytest_findings(output: str) -> dict[str, object]:
    findings: _PytestFindings = {
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "tests_skipped": 0,
        "failures": [],
    }

    clean_output = _strip_ansi_codes(output)

    summary_match = re.search(r"(\d+)\s+passed", clean_output, re.IGNORECASE)
    if summary_match:
        findings["tests_passed"] = int(summary_match.group(1))

    failed_match = re.search(r"(\d+)\s+failed", clean_output, re.IGNORECASE)
    if failed_match:
        findings["tests_failed"] = int(failed_match.group(1))

    skipped_match = re.search(r"(\d+)\s+skipped", clean_output, re.IGNORECASE)
    if skipped_match:
        findings["tests_skipped"] = int(skipped_match.group(1))

    findings["tests_run"] = findings["tests_passed"] + findings["tests_failed"] + findings["tests_skipped"]

    return dict(findings)
