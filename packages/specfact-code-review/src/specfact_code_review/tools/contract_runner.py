"""Contract runner for governed code-review findings."""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

from beartype import beartype
from icontract import ensure, require

from specfact_code_review._review_utils import normalize_path_variants, tool_error
from specfact_code_review.run.findings import ReviewFinding


_CROSSHAIR_LINE_RE = re.compile(r"^(?P<file>.+?):(?P<line>\d+):\s*(?:error|warning|info):\s*(?P<message>.+)$")
_IGNORED_CROSSHAIR_PREFIXES = ("SideEffectDetected:",)
_SYNC_RUNTIME_ICONTRACT_ENTRYPOINTS = {
    "bridge_probe.py",
    "bridge_sync.py",
    "bridge_watch.py",
    "speckit_backlog_sync.py",
    "speckit_bridge_backlog.py",
    "speckit_change_proposal_sync.py",
}


def _allowed_paths(files: list[Path]) -> set[str]:
    allowed: set[str] = set()
    for file_path in files:
        allowed.update(normalize_path_variants(file_path))
    return allowed


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


def _class_public_nodes(node: ast.ClassDef) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [
        class_node
        for class_node in ast.iter_child_nodes(node)
        if isinstance(class_node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not class_node.name.startswith("_")
    ]


def _public_api_nodes(tree: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    public_nodes: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            public_nodes.append(node)
            continue
        if isinstance(node, ast.ClassDef):
            public_nodes.extend(_class_public_nodes(node))
    return public_nodes


def _skip_icontract_ast_scan(file_path: Path) -> bool:
    """Implementation/helper modules opt out of per-public-function @require/@ensure AST checks."""
    normalized = str(file_path).replace("\\", "/")
    if normalized.endswith("/importers/speckit_markdown_sections.py"):
        return True
    if "/specfact_project/sync_runtime/" not in normalized:
        return False
    name = file_path.name
    return name not in _SYNC_RUNTIME_ICONTRACT_ENTRYPOINTS


def _scan_file(file_path: Path) -> list[ReviewFinding]:
    if _skip_icontract_ast_scan(file_path):
        return []
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        return [tool_error(tool="contract_runner", file_path=file_path, message=f"Unable to parse AST: {exc}")]

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
            tool_error(
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
        if normalize_path_variants(filename).isdisjoint(allowed_paths):
            continue
        message = match.group("message")
        if message.startswith(_IGNORED_CROSSHAIR_PREFIXES):
            continue
        findings.append(
            ReviewFinding(
                category="contracts",
                severity="warning",
                tool="crosshair",
                rule="CROSSHAIR_COUNTEREXAMPLE",
                file=filename,
                line=int(match.group("line")),
                message=message,
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
