"""AST-backed AI-bloat heuristics for governed review findings."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from beartype import beartype
from icontract import ensure, require

from specfact_code_review._review_utils import python_source_paths_for_tools, tool_error
from specfact_code_review.run.findings import ReviewFinding


_LOC_FLOOR = 40
_COMPLEXITY_CEILING = 4


@dataclass(frozen=True)
class _SimplificationCandidate:
    file_path: Path
    line: int
    rule: str
    message: str
    canonical_pattern: str
    rewrite_hint: str
    estimated_deletion_lines: int


def _iter_functions(tree: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)]


def _simplification_finding(candidate: _SimplificationCandidate) -> ReviewFinding:
    return ReviewFinding(
        category="ai_bloat",
        severity="info",
        tool="ast",
        rule=candidate.rule,
        file=str(candidate.file_path),
        line=candidate.line,
        message=candidate.message,
        fixable=False,
        confidence="high",
        rewrite_hint=candidate.rewrite_hint,
        canonical_pattern=candidate.canonical_pattern,
        estimated_deletion_lines=candidate.estimated_deletion_lines,
    )


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


def _assigned_empty_collection_name(stmt: ast.stmt) -> str | None:
    value: ast.AST | None = None
    target: ast.AST | None = None
    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
        target = stmt.targets[0]
        value = stmt.value
    elif isinstance(stmt, ast.AnnAssign):
        target = stmt.target
        value = stmt.value
    if not isinstance(target, ast.Name) or not isinstance(value, ast.List | ast.Dict | ast.Set):
        return None
    if isinstance(value, ast.List | ast.Set) and value.elts:
        return None
    if isinstance(value, ast.Dict) and value.keys:
        return None
    return target.id


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
            _simplification_finding(
                _SimplificationCandidate(
                    file_path=file_path,
                    line=stmt.lineno,
                    rule="ai-bloat.redundant-intermediate",
                    message=f"Variable `{name}` is assigned once and read only on the next statement; inline it.",
                    canonical_pattern="one-use-temporary",
                    rewrite_hint="Inline the one-use temporary into the return statement.",
                    estimated_deletion_lines=1,
                )
            )
        )
    return findings


def _manual_accumulator_loop_findings(
    file_path: Path, function_node: ast.FunctionDef | ast.AsyncFunctionDef
) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    for index, stmt in enumerate(function_node.body[:-1]):
        accumulator = _manual_accumulator_name(function_node, index)
        if accumulator is None:
            continue
        findings.append(
            _simplification_finding(
                _SimplificationCandidate(
                    file_path=file_path,
                    line=stmt.lineno,
                    rule="ai-bloat.manual-accumulator-loop",
                    message=f"Function `{function_node.name}` uses a manual accumulator loop that can likely collapse.",
                    canonical_pattern="manual-accumulator-loop",
                    rewrite_hint="Replace the accumulator loop with a comprehension or direct collection constructor.",
                    estimated_deletion_lines=3,
                )
            )
        )
    return findings


def _manual_accumulator_name(function_node: ast.FunctionDef | ast.AsyncFunctionDef, index: int) -> str | None:
    accumulator = _assigned_empty_collection_name(function_node.body[index])
    if accumulator is None:
        return None
    loop = function_node.body[index + 1]
    return_stmt = function_node.body[index + 2] if index + 2 < len(function_node.body) else None
    if not _returns_accumulator(return_stmt, accumulator):
        return None
    if not isinstance(loop, ast.For) or len(loop.body) != 1 or not isinstance(loop.body[0], ast.Expr):
        return None
    return accumulator if _loop_appends_to_accumulator(loop.body[0].value, accumulator) else None


def _returns_accumulator(stmt: ast.stmt | None, accumulator: str) -> bool:
    return isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Name) and stmt.value.id == accumulator


def _loop_appends_to_accumulator(node: ast.AST, accumulator: str) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"append", "add"}
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == accumulator
    )


def _return_constant_bool(stmt: ast.stmt) -> bool | None:
    if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, bool):
        return stmt.value.value
    return None


def _verbose_bool_return_findings(
    file_path: Path, function_node: ast.FunctionDef | ast.AsyncFunctionDef
) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    for index, stmt in enumerate(function_node.body[:-1]):
        next_stmt = function_node.body[index + 1]
        if not isinstance(stmt, ast.If) or len(stmt.body) != 1 or stmt.orelse:
            continue
        first_value = _return_constant_bool(stmt.body[0])
        second_value = _return_constant_bool(next_stmt)
        if first_value is None or second_value is None or first_value == second_value:
            continue
        findings.append(
            _simplification_finding(
                _SimplificationCandidate(
                    file_path=file_path,
                    line=stmt.lineno,
                    rule="ai-bloat.verbose-bool-return",
                    message=f"Function `{function_node.name}` returns explicit bool branches for one predicate.",
                    canonical_pattern="verbose-bool-return",
                    rewrite_hint="Return the predicate directly, negating it if needed.",
                    estimated_deletion_lines=2,
                )
            )
        )
    return findings


def _redundant_none_branch_findings(
    file_path: Path, function_node: ast.FunctionDef | ast.AsyncFunctionDef
) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    for index, stmt in enumerate(function_node.body[:-1]):
        if not isinstance(stmt, ast.If) or len(stmt.body) != 1 or stmt.orelse:
            continue
        if not (isinstance(stmt.body[0], ast.Return) and _is_none_constant(stmt.body[0].value)):
            continue
        if not isinstance(function_node.body[index + 1], ast.Return):
            continue
        findings.append(
            _simplification_finding(
                _SimplificationCandidate(
                    file_path=file_path,
                    line=stmt.lineno,
                    rule="ai-bloat.redundant-none-branch",
                    message=f"Function `{function_node.name}` has a pass-through None branch before a single return.",
                    canonical_pattern="redundant-none-branch",
                    rewrite_hint="Consider collapsing the None guard into the expression or caller contract.",
                    estimated_deletion_lines=2,
                )
            )
        )
    return findings


def _pass_through_try_except_findings(
    file_path: Path, function_node: ast.FunctionDef | ast.AsyncFunctionDef
) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    for stmt in function_node.body:
        if not isinstance(stmt, ast.Try) or stmt.orelse or stmt.finalbody or len(stmt.handlers) != 1:
            continue
        handler = stmt.handlers[0]
        if len(handler.body) != 1 or not isinstance(handler.body[0], ast.Raise) or handler.body[0].exc is not None:
            continue
        findings.append(
            _simplification_finding(
                _SimplificationCandidate(
                    file_path=file_path,
                    line=stmt.lineno,
                    rule="ai-bloat.pass-through-try-except",
                    message=(
                        f"Function `{function_node.name}` catches and immediately re-raises without adding context."
                    ),
                    canonical_pattern="pass-through-try-except",
                    rewrite_hint="Remove the pass-through try/except unless it adds domain context.",
                    estimated_deletion_lines=2,
                )
            )
        )
    return findings


def _constant_equality_return(stmt: ast.stmt) -> str | None:
    if not isinstance(stmt, ast.If) or len(stmt.body) != 1 or stmt.orelse:
        return None
    if not (isinstance(stmt.body[0], ast.Return) and isinstance(stmt.body[0].value, ast.Constant)):
        return None
    if not isinstance(stmt.test, ast.Compare) or len(stmt.test.ops) != 1:
        return None
    if not isinstance(stmt.test.ops[0], ast.Eq):
        return None
    if not isinstance(stmt.test.left, ast.Name) or len(stmt.test.comparators) != 1:
        return None
    if not isinstance(stmt.test.comparators[0], ast.Constant):
        return None
    return stmt.test.left.id


def _table_lookup_match_count(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    compared_name: str | None = None
    matches = 0
    for stmt in function_node.body:
        if isinstance(stmt, ast.Return):
            break
        current_name = _constant_equality_return(stmt)
        if current_name is None:
            return 0
        compared_name = compared_name or current_name
        if current_name != compared_name:
            return 0
        matches += 1
    return matches


def _table_lookup_candidate_findings(
    file_path: Path, function_node: ast.FunctionDef | ast.AsyncFunctionDef
) -> list[ReviewFinding]:
    matches = _table_lookup_match_count(function_node)
    if matches < 3:
        return []
    return [
        _simplification_finding(
            _SimplificationCandidate(
                file_path=file_path,
                line=function_node.lineno,
                rule="ai-bloat.table-lookup-candidate",
                message=f"Function `{function_node.name}` maps constants through repeated equality branches.",
                canonical_pattern="table-lookup-candidate",
                rewrite_hint="Consider replacing repeated equality returns with a lookup table plus default.",
                estimated_deletion_lines=max(1, matches - 1),
            )
        )
    ]


def _stdlib_replacement_candidate_findings(
    file_path: Path, function_node: ast.FunctionDef | ast.AsyncFunctionDef
) -> list[ReviewFinding]:
    candidate = _stdlib_replacement_candidate(function_node)
    if candidate is None:
        return []
    line, _initial_name = candidate
    return [
        _simplification_finding(
            _SimplificationCandidate(
                file_path=file_path,
                line=line,
                rule="ai-bloat.stdlib-replacement-candidate",
                message=(
                    f"Function `{function_node.name}` manually computes a value that may have a stdlib replacement."
                ),
                canonical_pattern="stdlib-replacement-candidate",
                rewrite_hint="Consider a standard helper such as max, min, any, all, sum, or dict.fromkeys.",
                estimated_deletion_lines=3,
            )
        )
    ]


def _stdlib_replacement_candidate(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[int, str] | None:
    if len(function_node.body) < 3:
        return None
    first_assign = function_node.body[0]
    initial_name = _none_initializer_name(first_assign)
    if initial_name is None:
        return None
    loop = function_node.body[1]
    terminal = function_node.body[2]
    if not _returns_accumulator(terminal, initial_name):
        return None
    if _loop_updates_name(loop, initial_name):
        return first_assign.lineno, initial_name
    return None


def _none_initializer_name(stmt: ast.stmt) -> str | None:
    name = _assigned_name(stmt)
    if name is None or not isinstance(stmt, ast.Assign) or not _is_none_constant(stmt.value):
        return None
    return name


def _loop_updates_name(stmt: ast.stmt, name: str) -> bool:
    if not isinstance(stmt, ast.For) or len(stmt.body) != 1 or not isinstance(stmt.body[0], ast.If):
        return False
    guard = stmt.body[0]
    return len(guard.body) == 1 and _assigned_name(guard.body[0]) == name


def _findings_for_function(
    file_path: Path, function_node: ast.FunctionDef | ast.AsyncFunctionDef
) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    findings.extend(_unused_optional_param_findings(file_path, function_node))
    findings.extend(_dead_branch_findings(file_path, function_node))
    findings.extend(_loc_vs_complexity_findings(file_path, function_node))
    findings.extend(_redundant_intermediate_findings(file_path, function_node))
    findings.extend(_manual_accumulator_loop_findings(file_path, function_node))
    findings.extend(_verbose_bool_return_findings(file_path, function_node))
    findings.extend(_redundant_none_branch_findings(file_path, function_node))
    findings.extend(_pass_through_try_except_findings(file_path, function_node))
    findings.extend(_table_lookup_candidate_findings(file_path, function_node))
    findings.extend(_stdlib_replacement_candidate_findings(file_path, function_node))
    return findings


def _single_call_return_name(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    if len(function_node.body) != 1 or not isinstance(function_node.body[0], ast.Return):
        return None
    value = function_node.body[0].value
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
        return value.func.id
    return None


def _wrapper_chain_findings(file_path: Path, tree: ast.Module) -> list[ReviewFinding]:
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)]
    wrappers = {function_node.name: _single_call_return_name(function_node) for function_node in functions}
    wrapper_names = {name for name, called in wrappers.items() if called is not None}
    findings: list[ReviewFinding] = []
    for function_node in functions:
        called = wrappers.get(function_node.name)
        if called is None or called not in wrapper_names:
            continue
        findings.append(
            _simplification_finding(
                _SimplificationCandidate(
                    file_path=file_path,
                    line=function_node.lineno,
                    rule="ai-bloat.wrapper-chain",
                    message=f"Function `{function_node.name}` is part of a pass-through wrapper chain.",
                    canonical_pattern="wrapper-chain",
                    rewrite_hint="Collapse the wrapper chain or keep only the compatibility boundary.",
                    estimated_deletion_lines=max(1, _function_loc(function_node) - 1),
                )
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
        findings.extend(_wrapper_chain_findings(file_path, tree))
        for function_node in _iter_functions(tree):
            findings.extend(_findings_for_function(file_path, function_node))
    return findings
