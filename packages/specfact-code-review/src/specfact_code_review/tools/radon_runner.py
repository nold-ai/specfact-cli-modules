# pylint: disable=line-too-long
"""Radon runner for governed code-review findings."""

from __future__ import annotations

import ast
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from beartype import beartype
from icontract import ensure, require

from specfact_code_review._review_utils import python_source_paths_for_tools
from specfact_code_review.run.findings import ReviewFinding
from specfact_code_review.tools.tool_availability import skip_if_tool_missing


_KISS_LOC_WARNING = 80
_KISS_LOC_ERROR = 120
_KISS_NESTING_WARNING = 3
_KISS_NESTING_ERROR = 5
_KISS_PARAMETER_WARNING = 5
_KISS_PARAMETER_ERROR = 7
_CONTROL_FLOW_NODES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith, ast.Match)


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


def _tool_error(file_path: Path, message: str) -> list[ReviewFinding]:
    return [
        ReviewFinding(
            category="tool_error",
            severity="error",
            tool="radon",
            rule="tool_error",
            file=str(file_path),
            line=1,
            message=message,
            fixable=False,
        )
    ]


def _iter_blocks(blocks: list[Any]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for block in blocks:
        if not isinstance(block, dict):
            raise ValueError("radon block must be an object")
        flattened.append(block)
        _extend_block_closures(flattened, block)
    return flattened


def _extend_block_closures(flattened: list[dict[str, Any]], block: dict[str, Any]) -> None:
    closures = block.get("closures", [])
    if not closures:
        return
    if not isinstance(closures, list):
        raise ValueError("radon closures must be a list")
    flattened.extend(_iter_blocks(closures))


def _control_flow_children(node: ast.AST) -> list[ast.AST]:
    return [child for child in ast.iter_child_nodes(node) if isinstance(child, _CONTROL_FLOW_NODES)]


def _nesting_depth(function_node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    def _depth(node: ast.AST, current: int) -> int:
        best = current
        for child in _control_flow_children(node):
            best = max(best, _depth(child, current + 1))
        return best

    return _depth(function_node, 0)


def _kiss_metric_findings(file_path: Path) -> list[ReviewFinding]:
    if not file_path.is_file():
        return []

    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    except (OSError, SyntaxError) as exc:
        return _tool_error(file_path, f"Unable to parse source for KISS metrics: {exc}")

    typer_command_targets = _typer_command_targets(tree)
    findings: list[ReviewFinding] = []
    for function_node in ast.walk(tree):
        if not isinstance(function_node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        findings.extend(_kiss_loc_findings(function_node, file_path))
        findings.extend(_kiss_nesting_findings(function_node, file_path))
        findings.extend(_kiss_parameter_findings(function_node, file_path, typer_command_targets))
    return findings


def _kiss_loc_findings(function_node: ast.FunctionDef | ast.AsyncFunctionDef, file_path: Path) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    loc = (function_node.end_lineno or function_node.lineno) - function_node.lineno + 1
    if loc <= _KISS_LOC_WARNING:
        return findings
    severity = "warning" if loc <= _KISS_LOC_ERROR else "error"
    suffix = "warning" if severity == "warning" else "error"
    findings.append(
        ReviewFinding(
            category="kiss",
            severity=severity,
            tool="radon-kiss",
            rule=f"kiss.loc.{suffix}",
            file=str(file_path),
            line=function_node.lineno,
            message=f"Function `{function_node.name}` spans {loc} lines; keep it under {_KISS_LOC_WARNING}.",
            fixable=False,
        )
    )
    return findings


def _kiss_nesting_findings(
    function_node: ast.FunctionDef | ast.AsyncFunctionDef, file_path: Path
) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    nesting = _nesting_depth(function_node)
    if nesting <= _KISS_NESTING_WARNING:
        return findings
    severity = "warning" if nesting <= _KISS_NESTING_ERROR else "error"
    suffix = "warning" if severity == "warning" else "error"
    findings.append(
        ReviewFinding(
            category="kiss",
            severity=severity,
            tool="radon-kiss",
            rule=f"kiss.nesting.{suffix}",
            file=str(file_path),
            line=function_node.lineno,
            message=(
                f"Function `{function_node.name}` nests control flow {nesting} levels deep;"
                f" keep it under {_KISS_NESTING_WARNING}."
            ),
            fixable=False,
        )
    )
    return findings


def _typer_cli_entrypoint_exempt(
    function_node: ast.FunctionDef | ast.AsyncFunctionDef, file_path: Path, typer_command_targets: set[str]
) -> bool:
    """Typer command callbacks legitimately take many injected options; skip parameter-count KISS on them."""
    normalized = str(file_path).replace("\\", "/")
    # Stable path suffix: matches in-repo and user-scoped installs (~/.specfact/modules/.../src/...).
    # Typer CLI handler `run(ctx: Context, ...)` in review.commands injects many option parameters by
    # design; Radon CC would flag it spuriously. Exempt only that callback so other `run` symbols
    # elsewhere still get complexity checks.
    if function_node.name == "run" and normalized.endswith("specfact_code_review/review/commands.py"):
        return True
    return _has_typer_command_decorator(function_node, typer_command_targets)


def _decorator_name_parts(decorator: ast.expr) -> tuple[str, ...]:
    if isinstance(decorator, ast.Call):
        return _decorator_name_parts(decorator.func)
    if isinstance(decorator, ast.Name):
        return (decorator.id,)
    if isinstance(decorator, ast.Attribute):
        return (*_decorator_name_parts(decorator.value), decorator.attr)
    return ()


def _typer_command_targets(tree: ast.Module) -> set[str]:
    """Return names that own Typer command or callback decorators in a module."""
    typer_module_names = _typer_module_names(tree)
    typer_constructor_names = _typer_constructor_names(tree)
    return typer_module_names | _typer_application_names(tree, typer_module_names, typer_constructor_names)


def _typer_module_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.Import):
            continue
        for alias in node.names:
            if alias.name == "typer":
                names.add(alias.asname or alias.name)
    return names


def _typer_constructor_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or node.module != "typer":
            continue
        for alias in node.names:
            if alias.name == "Typer":
                names.add(alias.asname or alias.name)
    return names


def _typer_application_names(
    tree: ast.Module, typer_module_names: set[str], typer_constructor_names: set[str]
) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign | ast.AnnAssign) and _is_typer_constructor(
            node.value, typer_module_names, typer_constructor_names
        ):
            names.update(_assignment_target_names(node))
    return names


def _is_typer_constructor(
    value: ast.expr | None, typer_module_names: set[str], typer_constructor_names: set[str]
) -> bool:
    if not isinstance(value, ast.Call):
        return False
    if isinstance(value.func, ast.Name):
        return value.func.id in typer_constructor_names
    return (
        isinstance(value.func, ast.Attribute)
        and isinstance(value.func.value, ast.Name)
        and value.func.value.id in typer_module_names
        and value.func.attr == "Typer"
    )


def _assignment_target_names(node: ast.Assign | ast.AnnAssign) -> set[str]:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    return {target.id for target in targets if isinstance(target, ast.Name)}


def _has_typer_command_decorator(
    function_node: ast.FunctionDef | ast.AsyncFunctionDef, typer_command_targets: set[str]
) -> bool:
    for decorator in function_node.decorator_list:
        parts = _decorator_name_parts(decorator)
        if len(parts) == 2 and parts[0] in typer_command_targets and parts[1] in {"command", "callback"}:
            return True
    return False


def _kiss_parameter_findings(
    function_node: ast.FunctionDef | ast.AsyncFunctionDef, file_path: Path, typer_command_targets: set[str]
) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    if _typer_cli_entrypoint_exempt(function_node, file_path, typer_command_targets):
        return findings
    parameter_count = len(function_node.args.posonlyargs)
    parameter_count += len(function_node.args.args)
    parameter_count += len(function_node.args.kwonlyargs)
    if function_node.args.vararg is not None:
        parameter_count += 1
    if function_node.args.kwarg is not None:
        parameter_count += 1
    if parameter_count <= _KISS_PARAMETER_WARNING:
        return findings
    severity = "warning" if parameter_count <= _KISS_PARAMETER_ERROR else "error"
    suffix = "warning" if severity == "warning" else "error"
    findings.append(
        ReviewFinding(
            category="kiss",
            severity=severity,
            tool="radon-kiss",
            rule=f"kiss.parameter-count.{suffix}",
            file=str(file_path),
            line=function_node.lineno,
            message=(
                f"Function `{function_node.name}` accepts {parameter_count} parameters;"
                f" keep it under {_KISS_PARAMETER_WARNING}."
            ),
            fixable=False,
        )
    )
    return findings


def _run_radon_command(files: list[Path]) -> dict[str, Any] | None:
    try:
        result = subprocess.run(
            ["radon", "cc", "-j", *(str(file_path) for file_path in files)],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict):
            raise ValueError("radon output must be an object")
        return payload
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired):
        return None


def _map_radon_complexity_findings(payload: dict[str, Any], allowed_paths: set[str]) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    for filename, blocks in payload.items():
        if not isinstance(filename, str):
            raise ValueError("radon filename must be a string")
        if _normalize_path_variants(filename).isdisjoint(allowed_paths):
            continue
        if not isinstance(blocks, list):
            raise ValueError("radon file payload must be a list")
        findings.extend(_map_radon_blocks(blocks, filename))
    return findings


def _map_radon_blocks(blocks: list[Any], filename: str) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    for block in _iter_blocks(blocks):
        complexity = block["complexity"]
        line = block["lineno"]
        name = block["name"]
        if not isinstance(complexity, int):
            raise ValueError("radon complexity must be an integer")
        if complexity <= 12:
            continue
        if not isinstance(line, int):
            raise ValueError("radon line must be an integer")
        if not isinstance(name, str):
            raise ValueError("radon name must be a string")
        severity = "warning" if complexity <= 15 else "error"
        findings.append(
            ReviewFinding(
                category="clean_code",
                severity=severity,
                tool="radon",
                rule=f"CC{complexity}",
                file=filename,
                line=line,
                message=f"Cyclomatic complexity for {name} is {complexity}.",
                fixable=False,
            )
        )
    return findings


def _ensure_review_findings(result: list[ReviewFinding]) -> bool:
    return all(isinstance(finding, ReviewFinding) for finding in result)


@beartype
@require(lambda files: isinstance(files, list), "files must be a list")
@require(lambda files: all(isinstance(file_path, Path) for file_path in files), "files must contain Path instances")
@ensure(lambda result: isinstance(result, list), "result must be a list")
@ensure(
    _ensure_review_findings,
    "result must contain ReviewFinding instances",
)
def run_radon(files: list[Path]) -> list[ReviewFinding]:
    """Run Radon for the provided files and map complexity findings into ReviewFinding records."""
    files = python_source_paths_for_tools(files)
    if not files:
        return []

    skipped = skip_if_tool_missing("radon", files[0])
    if skipped:
        return skipped

    payload = _run_radon_command(files)
    findings: list[ReviewFinding] = []
    if payload is None:
        findings.extend(_tool_error(files[0], "Unable to execute Radon"))
    else:
        allowed_paths = _allowed_paths(files)
        try:
            findings.extend(_map_radon_complexity_findings(payload, allowed_paths))
        except ValueError as exc:
            findings.extend(_tool_error(files[0], str(exc)))

    for file_path in files:
        findings.extend(_kiss_metric_findings(file_path))
    return findings
