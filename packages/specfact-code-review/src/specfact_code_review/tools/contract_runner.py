"""Contract runner for governed code-review findings."""

from __future__ import annotations

import ast
import os
import re
import subprocess
from pathlib import Path

from beartype import beartype
from icontract import ensure, require

from specfact_code_review.run.findings import ReviewFinding


_CROSSHAIR_LINE_RE = re.compile(r"^(?P<file>.+?):(?P<line>\d+):\s*(?:error|warning|info):\s*(?P<message>.+)$")


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


def _tool_error(*, tool: str, file_path: Path, message: str, severity: str = "error") -> ReviewFinding:
    return ReviewFinding(
        category="tool_error",
        severity=severity,
        tool=tool,
        rule="tool_error",
        file=str(file_path),
        line=1,
        message=message,
        fixable=False,
    )


def _decorator_name(decorator: ast.expr) -> str | None:
    if isinstance(decorator, ast.Call):
        return _decorator_name(decorator.func)
    if isinstance(decorator, ast.Name):
        return decorator.id
    if isinstance(decorator, ast.Attribute):
        return decorator.attr
    return None


def _has_icontract(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(_decorator_name(decorator) in {"require", "ensure"} for decorator in node.decorator_list)


def _public_api_nodes(tree: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    public_nodes: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            public_nodes.append(node)
        if isinstance(node, ast.ClassDef):
            for class_node in ast.iter_child_nodes(node):
                if isinstance(class_node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not class_node.name.startswith(
                    "_"
                ):
                    public_nodes.append(class_node)
    return public_nodes


def _scan_file(file_path: Path) -> list[ReviewFinding]:
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        return [_tool_error(tool="contract_runner", file_path=file_path, message=f"Unable to parse AST: {exc}")]

    findings: list[ReviewFinding] = []
    for node in _public_api_nodes(tree):
        if _has_icontract(node):
            continue
        findings.append(
            ReviewFinding(
                category="contracts",
                severity="warning",
                tool="contract_runner",
                rule="MISSING_ICONTRACT",
                file=str(file_path),
                line=node.lineno,
                message=f"Public function '{node.name}' is missing @require/@ensure decorators.",
                fixable=False,
            )
        )
    return findings


def _run_crosshair(files: list[Path]) -> list[ReviewFinding]:
    if not files:
        return []

    try:
        result = subprocess.run(
            ["crosshair", "check", "--per_path_timeout", "2", *(str(file_path) for file_path in files)],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return []
    except (FileNotFoundError, OSError) as exc:
        return [
            _tool_error(
                tool="crosshair",
                file_path=files[0],
                message=f"Unable to execute CrossHair: {exc}",
                severity="warning",
            )
        ]

    allowed_paths = _allowed_paths(files)
    findings: list[ReviewFinding] = []
    for line in (result.stdout or "").splitlines():
        match = _CROSSHAIR_LINE_RE.match(line.strip())
        if match is None:
            continue
        filename = match.group("file")
        if _normalize_path_variants(filename).isdisjoint(allowed_paths):
            continue
        findings.append(
            ReviewFinding(
                category="contracts",
                severity="warning",
                tool="crosshair",
                rule="CROSSHAIR_COUNTEREXAMPLE",
                file=filename,
                line=int(match.group("line")),
                message=match.group("message"),
                fixable=False,
            )
        )
    return findings


@beartype
@require(lambda files: isinstance(files, list), "files must be a list")
@require(lambda files: all(isinstance(file_path, Path) for file_path in files), "files must contain Path instances")
@ensure(lambda result: isinstance(result, list), "result must be a list")
@ensure(
    lambda result: all(isinstance(finding, ReviewFinding) for finding in result),
    "result must contain ReviewFinding instances",
)
def run_contract_check(files: list[Path]) -> list[ReviewFinding]:
    """Run AST-based contract checks and a CrossHair fast pass for the provided files."""
    if not files:
        return []

    findings: list[ReviewFinding] = []
    for file_path in files:
        findings.extend(_scan_file(file_path))
    findings.extend(_run_crosshair(files))
    return findings
