"""AST-backed clean-code runner for governed review findings."""

from __future__ import annotations

import ast
import copy
from collections import defaultdict
from pathlib import Path

from beartype import beartype
from icontract import ensure, require

from specfact_code_review._review_utils import tool_error
from specfact_code_review.run.findings import ReviewFinding


_REPOSITORY_ROOTS = {"repo", "repository"}
_HTTP_ROOTS = {"client", "http_client", "requests", "session"}


class _ShapeNormalizer(ast.NodeTransformer):
    """Erase local naming details while preserving code structure."""

    @require(lambda node: isinstance(node, ast.Name))
    @ensure(lambda result: isinstance(result, ast.AST))
    def visit_Name(self, node: ast.Name) -> ast.AST:
        return ast.copy_location(ast.Name(id="VAR", ctx=node.ctx), node)

    @require(lambda node: isinstance(node, ast.arg))
    @ensure(lambda result: isinstance(result, ast.AST))
    def visit_arg(self, node: ast.arg) -> ast.AST:
        return ast.copy_location(ast.arg(arg="ARG", annotation=None, type_comment=None), node)

    @require(lambda node: isinstance(node, ast.Attribute))
    @ensure(lambda result: isinstance(result, ast.AST))
    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        normalized_value = self.visit(node.value)
        return ast.copy_location(ast.Attribute(value=normalized_value, attr="ATTR", ctx=node.ctx), node)

    @require(lambda node: isinstance(node, ast.Constant))
    @ensure(lambda result: isinstance(result, ast.AST))
    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        placeholder = node.value if isinstance(node.value, bool | type(None)) else "CONST"
        return ast.copy_location(ast.Constant(value=placeholder), node)

    @require(lambda node: isinstance(node, ast.FunctionDef))
    @ensure(lambda result: isinstance(result, ast.AST))
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        normalized = self.generic_visit(node)
        assert isinstance(normalized, ast.FunctionDef)
        normalized.name = "FUNC"
        return normalized

    @require(lambda node: isinstance(node, ast.AsyncFunctionDef))
    @ensure(lambda result: isinstance(result, ast.AST))
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        normalized = self.generic_visit(node)
        assert isinstance(normalized, ast.AsyncFunctionDef)
        normalized.name = "FUNC"
        return normalized


def _iter_functions(tree: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)]


def _module_level_functions(tree: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [node for node in tree.body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)]


def _loaded_names(tree: ast.AST) -> set[str]:
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)}


def _leftmost_name(node: ast.AST) -> str | None:
    current = node
    first_attribute: str | None = None
    while isinstance(current, ast.Attribute):
        first_attribute = current.attr
        current = current.value
    if isinstance(current, ast.Name):
        if current.id in {"self", "cls"} and first_attribute is not None:
            return first_attribute
        return current.id
    return None


def _call_roots(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue
        root = _leftmost_name(node.func)
        if root is not None:
            roots.add(root)
    return roots


def _duplicate_shape_id(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    normalized = _ShapeNormalizer().visit(
        ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(function_node)], type_ignores=[]))
    )
    return ast.dump(normalized, include_attributes=False)


def _yagni_findings(file_path: Path, tree: ast.Module) -> list[ReviewFinding]:
    loaded_names = _loaded_names(tree)
    findings: list[ReviewFinding] = []
    for function_node in _module_level_functions(tree):
        if not function_node.name.startswith("_") or function_node.name.startswith("__"):
            continue
        if function_node.name in loaded_names:
            continue
        findings.append(
            ReviewFinding(
                category="yagni",
                severity="warning",
                tool="ast",
                rule="yagni.unused-private-helper",
                file=str(file_path),
                line=function_node.lineno,
                message=f"Private helper `{function_node.name}` is not referenced in this module.",
                fixable=False,
            )
        )
    return findings


def _dry_findings(file_path: Path, tree: ast.Module) -> list[ReviewFinding]:
    functions = _module_level_functions(tree)
    grouped: dict[str, list[ast.FunctionDef | ast.AsyncFunctionDef]] = defaultdict(list)
    for function_node in functions:
        grouped[_duplicate_shape_id(function_node)].append(function_node)

    findings: list[ReviewFinding] = []
    for duplicates in grouped.values():
        if len(duplicates) < 2:
            continue
        for duplicate in duplicates[1:]:
            findings.append(
                ReviewFinding(
                    category="dry",
                    severity="warning",
                    tool="ast",
                    rule="dry.duplicate-function-shape",
                    file=str(file_path),
                    line=duplicate.lineno,
                    message=f"Function `{duplicate.name}` duplicates another function shape in this module.",
                    fixable=False,
                )
            )
    return findings


def _solid_findings(file_path: Path, tree: ast.Module) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    for function_node in _iter_functions(tree):
        roots = _call_roots(function_node)
        if roots.isdisjoint(_REPOSITORY_ROOTS) or roots.isdisjoint(_HTTP_ROOTS):
            continue
        findings.append(
            ReviewFinding(
                category="solid",
                severity="warning",
                tool="ast",
                rule="solid.mixed-dependency-role",
                file=str(file_path),
                line=function_node.lineno,
                message=(
                    f"Function `{function_node.name}` mixes repository-style and HTTP-style dependencies; "
                    "split the responsibility."
                ),
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
def run_ast_clean_code(files: list[Path]) -> list[ReviewFinding]:
    """Run Python-native AST checks for SOLID, YAGNI, and DRY findings."""
    findings: list[ReviewFinding] = []
    for file_path in files:
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        except (OSError, SyntaxError) as exc:
            findings.append(
                tool_error(tool="ast", file_path=file_path, message=f"Unable to parse Python source: {exc}")
            )
            continue

        findings.extend(_solid_findings(file_path, tree))
        findings.extend(_yagni_findings(file_path, tree))
        findings.extend(_dry_findings(file_path, tree))

    return findings
