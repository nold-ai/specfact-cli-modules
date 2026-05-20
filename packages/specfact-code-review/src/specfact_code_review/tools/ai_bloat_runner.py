"""AST-backed AI-bloat heuristics for governed review findings."""

from __future__ import annotations

import ast
from pathlib import Path

from beartype import beartype
from icontract import ensure, require

from specfact_code_review._review_utils import python_source_paths_for_tools, tool_error
from specfact_code_review.run.findings import ReviewFinding


_LOC_FLOOR = 40
_COMPLEXITY_CEILING = 4


def _iter_functions(tree: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)]


def _is_none_constant(node: ast.AST | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is None


def _annotation_is_optional(annotation: ast.AST | None) -> bool:
    if annotation is None:
        return False
    if isinstance(annotation, ast.Name):
        return annotation.id == "Optional"
    if isinstance(annotation, ast.Attribute):
        return annotation.attr == "Optional"
    if isinstance(annotation, ast.Subscript):
        return _annotation_is_optional(annotation.value)
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        return _annotation_is_none(annotation.left) or _annotation_is_none(annotation.right)
    return False


def _annotation_is_none(annotation: ast.AST) -> bool:
    if isinstance(annotation, ast.Constant):
        return annotation.value is None
    if isinstance(annotation, ast.Name):
        return annotation.id in {"None", "NoneType"}
    return False


def _optional_default_params(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.arg]:
    positional = [*function_node.args.posonlyargs, *function_node.args.args]
    defaults = [None] * (len(positional) - len(function_node.args.defaults)) + list(function_node.args.defaults)
    candidates = [
        arg
        for arg, default in zip(positional, defaults, strict=True)
        if _is_none_constant(default) and _annotation_is_optional(arg.annotation)
    ]
    candidates.extend(
        arg
        for arg, default in zip(function_node.args.kwonlyargs, function_node.args.kw_defaults, strict=True)
        if _is_none_constant(default) and _annotation_is_optional(arg.annotation)
    )
    return candidates


def _references_name(node: ast.AST, name: str) -> bool:
    return any(isinstance(child, ast.Name) and child.id == name for child in ast.walk(node))


def _is_none_check_for_name(node: ast.AST, name: str) -> bool:
    if not isinstance(node, ast.Compare):
        return False
    comparands = [node.left, *node.comparators]
    has_name = any(isinstance(item, ast.Name) and item.id == name for item in comparands)
    has_none = any(_is_none_constant(item) for item in comparands)
    has_none_operator = any(isinstance(op, ast.Is | ast.IsNot | ast.Eq | ast.NotEq) for op in node.ops)
    return has_name and has_none and has_none_operator


def _has_none_branch(function_node: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> bool:
    return any(_is_none_check_for_name(node, name) for node in ast.walk(function_node))


def _unused_optional_param_findings(
    file_path: Path, function_node: ast.FunctionDef | ast.AsyncFunctionDef
) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    for arg in _optional_default_params(function_node):
        if _has_none_branch(function_node, arg.arg) or _references_name(
            ast.Module(body=function_node.body, type_ignores=[]), arg.arg
        ):
            continue
        findings.append(
            ReviewFinding(
                category="ai_bloat",
                severity="info",
                tool="ast",
                rule="ai-bloat.unused-optional-param",
                file=str(file_path),
                line=arg.lineno,
                message=(
                    f"Optional parameter `{arg.arg}` defaults to None but is never checked for None; "
                    "remove the default or make the parameter required."
                ),
                fixable=False,
            )
        )
    return findings


def _terminal_return(body: list[ast.stmt]) -> bool:
    return bool(body) and isinstance(body[-1], ast.Return)


def _dead_branch_findings(
    file_path: Path, function_node: ast.FunctionDef | ast.AsyncFunctionDef
) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    prior_terminal_tests: set[str] = set()
    for stmt in function_node.body:
        if not isinstance(stmt, ast.If):
            continue
        test_key = ast.dump(stmt.test, include_attributes=False)
        if test_key in prior_terminal_tests:
            findings.append(
                ReviewFinding(
                    category="ai_bloat",
                    severity="info",
                    tool="ast",
                    rule="ai-bloat.dead-branch",
                    file=str(file_path),
                    line=stmt.lineno,
                    message="Branch duplicates a prior terminal guard and is unreachable in this local flow.",
                    fixable=False,
                )
            )
        if _terminal_return(stmt.body):
            prior_terminal_tests.add(test_key)
    return findings


def _function_loc(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    end_lineno = function_node.end_lineno or function_node.lineno
    return end_lineno - function_node.lineno + 1


def _local_branch_complexity(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    branches = (
        ast.If,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.Try,
        ast.BoolOp,
        ast.IfExp,
        ast.ExceptHandler,
        ast.Match,
    )
    return sum(1 for node in ast.walk(function_node) if isinstance(node, branches))


def _loc_vs_complexity_findings(
    file_path: Path, function_node: ast.FunctionDef | ast.AsyncFunctionDef
) -> list[ReviewFinding]:
    loc = _function_loc(function_node)
    complexity = _local_branch_complexity(function_node)
    if loc < _LOC_FLOOR or complexity > _COMPLEXITY_CEILING:
        return []
    return [
        ReviewFinding(
            category="ai_bloat",
            severity="info",
            tool="ast",
            rule="ai-bloat.loc-vs-complexity",
            file=str(file_path),
            line=function_node.lineno,
            message=(
                f"Function `{function_node.name}` is {loc} lines with low branch complexity; "
                "look for a stdlib or comprehension collapse."
            ),
            fixable=False,
        )
    ]


def _assigned_name(stmt: ast.stmt) -> str | None:
    if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
        return None
    target = stmt.targets[0]
    if isinstance(target, ast.Name):
        return target.id
    return None


def _loaded_name_count(node: ast.AST, name: str) -> int:
    return sum(
        1
        for child in ast.walk(node)
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load) and child.id == name
    )


def _redundant_intermediate_findings(
    file_path: Path, function_node: ast.FunctionDef | ast.AsyncFunctionDef
) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    for index, stmt in enumerate(function_node.body[:-1]):
        name = _assigned_name(stmt)
        if name is None:
            continue
        next_stmt = function_node.body[index + 1]
        if not (
            isinstance(next_stmt, ast.Return) and isinstance(next_stmt.value, ast.Name) and next_stmt.value.id == name
        ):
            continue
        if _loaded_name_count(next_stmt, name) != 1:
            continue
        later_uses = sum(_loaded_name_count(later_stmt, name) for later_stmt in function_node.body[index + 2 :])
        if later_uses != 0:
            continue
        findings.append(
            ReviewFinding(
                category="ai_bloat",
                severity="info",
                tool="ast",
                rule="ai-bloat.redundant-intermediate",
                file=str(file_path),
                line=stmt.lineno,
                message=f"Variable `{name}` is assigned once and read only on the next statement; inline it.",
                fixable=False,
            )
        )
    return findings


def _findings_for_function(
    file_path: Path, function_node: ast.FunctionDef | ast.AsyncFunctionDef
) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    findings.extend(_unused_optional_param_findings(file_path, function_node))
    findings.extend(_dead_branch_findings(file_path, function_node))
    findings.extend(_loc_vs_complexity_findings(file_path, function_node))
    findings.extend(_redundant_intermediate_findings(file_path, function_node))
    return findings


@beartype
@require(lambda files: isinstance(files, list), "files must be a list")
@require(lambda files: all(isinstance(file_path, Path) for file_path in files), "files must contain Path instances")
@ensure(lambda result: isinstance(result, list), "result must be a list")
@ensure(
    lambda result: all(isinstance(finding, ReviewFinding) for finding in result),
    "result must contain ReviewFinding instances",
)
def run_ai_bloat(files: list[Path]) -> list[ReviewFinding]:
    """Run conservative Python-native AST checks for AI-bloat findings."""
    findings: list[ReviewFinding] = []
    for file_path in python_source_paths_for_tools(files):
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        except (OSError, SyntaxError, UnicodeDecodeError) as exc:
            findings.append(
                tool_error(tool="ast", file_path=file_path, message=f"Unable to parse Python source: {exc}")
            )
            continue
        for function_node in _iter_functions(tree):
            findings.extend(_findings_for_function(file_path, function_node))
    return findings
