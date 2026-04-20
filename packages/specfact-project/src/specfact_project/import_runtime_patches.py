"""Runtime patch helpers for code-import discovery policy."""

from __future__ import annotations

import importlib
import inspect
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from beartype import beartype
from icontract import ensure, require

from specfact_project.utils.import_path_policy import ImportDiscoveryResult, discover_code_files


_PATCH_APPLIED = False
_PATCH_APPLY_LOCK = threading.RLock()
_CONSOLE_PRINT_PATCH_LOCK = threading.RLock()
_rglob_patch_lock = threading.RLock()


def _pattern_to_extension(pattern: str) -> str | None:
    if pattern.startswith("*.") and all(ch not in pattern[2:] for ch in "*?[]/\\"):
        return pattern[1:]
    return None


def _build_discovery(
    repo_root: Path,
    *,
    entry_point: Path | None = None,
) -> ImportDiscoveryResult:
    return discover_code_files(repo_root, extensions={".py"}, entry_point=entry_point)


@dataclass(slots=True)
class _AnalyzeCodebaseArgs:
    repo: Path
    entry_point: Path | None
    bundle: str
    confidence: float
    key_format: str
    routing_result: Any
    incremental_callback: Any | None


@dataclass(slots=True)
class _RelationshipArgs:
    repo: Path
    entry_point: Path | None
    bundle_dir: Path
    incremental_changes: dict[str, bool] | None
    plan_bundle: Any
    should_regenerate_relationships: bool
    should_regenerate_graph: bool
    include_tests: bool


@contextmanager
def _patched_rglob(
    repo_root: Path,
    *,
    entry_point: Path | None = None,
    max_files: int | None = None,
) -> Iterator[None]:
    resolved_repo_root = repo_root.resolve()
    resolved_entry_point = entry_point.resolve() if entry_point else None

    with _rglob_patch_lock:
        original_rglob = Path.rglob

        def patched(self: Path, pattern: str):  # type: ignore[override]
            extension = _pattern_to_extension(pattern)
            if extension is None:
                return original_rglob(self, pattern)

            resolved_self = self.resolve()
            if resolved_self not in (resolved_repo_root, resolved_entry_point):
                return original_rglob(self, pattern)

            scoped_entry_point = None if resolved_self == resolved_repo_root else resolved_self
            discovery = discover_code_files(
                resolved_repo_root,
                extensions={extension},
                entry_point=scoped_entry_point,
                max_files=max_files,
            )
            return iter(discovery.files)

        Path.rglob = patched  # type: ignore[assignment]
        try:
            yield
        finally:
            Path.rglob = original_rglob  # type: ignore[assignment]


@contextmanager
def _patched_console_print(commands_module: Any) -> Iterator[None]:
    with _CONSOLE_PRINT_PATCH_LOCK:
        original_print = commands_module.console.print

        def patched(*args: Any, **kwargs: Any) -> None:
            if args and isinstance(args[0], str) and "typically takes 2-5 minutes" in args[0]:
                return
            original_print(*args, **kwargs)

        commands_module.console.print = patched
        try:
            yield
        finally:
            commands_module.console.print = original_print


def _emit_runtime_warnings(commands_module: Any, discovery: ImportDiscoveryResult) -> None:
    for warning in discovery.warnings:
        commands_module.console.print(f"[yellow]⚠ {warning}[/yellow]")
    message = (
        f"[yellow]⏱️  Provisional import estimate based on discovered work: about {discovery.provisional_eta}[/yellow]"
        if discovery.provisional_eta
        else "\n[yellow]⏱️  Import duration depends on discovered source files and repository artifacts; "
        "remaining time updates as work is processed.[/yellow]"
    )
    commands_module.console.print(message)


def _patch_code_analyzer(code_analyzer: Any) -> None:
    original_analyze = code_analyzer.CodeAnalyzer.analyze

    def patched_analyze(self: Any):
        with _patched_rglob(self.repo_path, entry_point=self.entry_point):
            return original_analyze(self)

    code_analyzer.CodeAnalyzer.analyze = patched_analyze


def _patch_count_python_files(commands: Any) -> None:
    def patched_count_python_files(repo: Path) -> int:
        return len(_build_discovery(repo).files)

    commands._count_python_files = patched_count_python_files


def _run_patched_analyze_codebase(original_analyze_codebase: Any, commands: Any, args: _AnalyzeCodebaseArgs):
    discovery = _build_discovery(args.repo, entry_point=args.entry_point)
    _emit_runtime_warnings(commands, discovery)
    with _patched_console_print(commands), _patched_rglob(args.repo, entry_point=args.entry_point):
        return original_analyze_codebase(
            args.repo,
            args.entry_point,
            args.bundle,
            args.confidence,
            args.key_format,
            args.routing_result,
            args.incremental_callback,
        )


def _build_analyze_args(args: tuple[Any, ...]) -> _AnalyzeCodebaseArgs:
    repo, entry_point, bundle, confidence, key_format, routing_result, *rest = args
    incremental_callback = rest[0] if rest else None
    return _AnalyzeCodebaseArgs(
        repo=repo,
        entry_point=entry_point,
        bundle=bundle,
        confidence=confidence,
        key_format=key_format,
        routing_result=routing_result,
        incremental_callback=incremental_callback,
    )


def _build_analyze_args_from_mapping(arguments: dict[str, Any]) -> _AnalyzeCodebaseArgs:
    return _AnalyzeCodebaseArgs(
        repo=arguments["repo"],
        entry_point=arguments["entry_point"],
        bundle=arguments["bundle"],
        confidence=arguments["confidence"],
        key_format=arguments["key_format"],
        routing_result=arguments["routing_result"],
        incremental_callback=arguments.get("incremental_callback"),
    )


def _install_patch(target: Any, attr_name: str, runner: Any, args_builder: Any, context: Any) -> None:
    original = getattr(target, attr_name)
    signature = inspect.signature(original)

    def patched(*args: Any, **kwargs: Any) -> Any:
        bound = signature.bind_partial(*args, **kwargs)
        built = args_builder(dict(bound.arguments))
        if kwargs:
            built = replace(built, **kwargs)
        return runner(original, context, built)

    setattr(target, attr_name, patched)


def _run_patched_extract_relationships(original_extract_relationships: Any, commands: Any, args: _RelationshipArgs):
    discovery = _build_discovery(args.repo, entry_point=args.entry_point)
    for warning in discovery.warnings:
        commands.console.print(f"[yellow]⚠ {warning}[/yellow]")
    with _patched_rglob(args.repo, entry_point=args.entry_point):
        return original_extract_relationships(
            args.repo,
            args.entry_point,
            args.bundle_dir,
            args.incremental_changes,
            args.plan_bundle,
            args.should_regenerate_relationships,
            args.should_regenerate_graph,
            args.include_tests,
        )


def _build_relationship_args(args: tuple[Any, ...]) -> _RelationshipArgs:
    (
        repo,
        entry_point,
        bundle_dir,
        incremental_changes,
        plan_bundle,
        should_regenerate_relationships,
        should_regenerate_graph,
        *rest,
    ) = args
    include_tests = bool(rest[0]) if rest else False
    return _RelationshipArgs(
        repo=repo,
        entry_point=entry_point,
        bundle_dir=bundle_dir,
        incremental_changes=incremental_changes,
        plan_bundle=plan_bundle,
        should_regenerate_relationships=should_regenerate_relationships,
        should_regenerate_graph=should_regenerate_graph,
        include_tests=include_tests,
    )


def _build_relationship_args_from_mapping(arguments: dict[str, Any]) -> _RelationshipArgs:
    return _RelationshipArgs(
        repo=arguments["repo"],
        entry_point=arguments["entry_point"],
        bundle_dir=arguments["bundle_dir"],
        incremental_changes=arguments["incremental_changes"],
        plan_bundle=arguments["plan_bundle"],
        should_regenerate_relationships=arguments["should_regenerate_relationships"],
        should_regenerate_graph=arguments["should_regenerate_graph"],
        include_tests=bool(arguments.get("include_tests", False)),
    )


def _patch_load_codebase_context(analyze_agent: Any) -> None:
    original_load_codebase_context = analyze_agent.AnalyzeAgent._load_codebase_context

    def patched_load_codebase_context(self: Any, repo_path: Path) -> dict[str, Any]:
        with _patched_rglob(repo_path, max_files=100):
            return original_load_codebase_context(self, repo_path)

    analyze_agent.AnalyzeAgent._load_codebase_context = patched_load_codebase_context


@beartype
@require(lambda: True, "Patch application has no runtime preconditions")
@ensure(lambda: _PATCH_APPLIED is True, "Patches must be marked applied after execution")
def apply_import_runtime_patches(*, commands_module: Any | None = None) -> None:
    """Patch import-runtime entrypoints without modifying legacy high-complexity files."""
    global _PATCH_APPLIED
    with _PATCH_APPLY_LOCK:
        if _PATCH_APPLIED:
            return

        from specfact_project.agents import analyze_agent
        from specfact_project.analyzers import code_analyzer

        commands = commands_module
        if commands is None:
            commands = importlib.import_module("specfact_project.import_cmd.commands")

        _patch_code_analyzer(code_analyzer)
        _patch_count_python_files(commands)
        _install_patch(
            commands,
            "_analyze_codebase",
            _run_patched_analyze_codebase,
            _build_analyze_args_from_mapping,
            commands,
        )
        _install_patch(
            commands,
            "_extract_relationships_and_graph",
            _run_patched_extract_relationships,
            _build_relationship_args_from_mapping,
            commands,
        )
        _patch_load_codebase_context(analyze_agent)
        _PATCH_APPLIED = True
