"""Helpers for commands.sync_intelligent (cyclomatic complexity reduction)."""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

from pathlib import Path
from typing import Any


def _intelligent_report_changes(changeset: Any, console: Any) -> bool:
    if not any([changeset.code_changes, changeset.spec_changes, changeset.test_changes]):
        console.print("[dim]No changes detected[/dim]")
        return False
    if changeset.code_changes:
        console.print(f"[cyan]Code changes:[/cyan] {len(changeset.code_changes)}")
    if changeset.spec_changes:
        console.print(f"[cyan]Spec changes:[/cyan] {len(changeset.spec_changes)}")
    if changeset.test_changes:
        console.print(f"[cyan]Test changes:[/cyan] {len(changeset.test_changes)}")
    if changeset.conflicts:
        console.print(f"[yellow]⚠ Conflicts:[/yellow] {len(changeset.conflicts)}")
    return True


def _intelligent_run_code_to_spec(
    code_to_spec: str, changeset: Any, bundle: str, code_to_spec_sync: Any, console: Any
) -> None:
    if code_to_spec != "auto" or not changeset.code_changes:
        return
    console.print("\n[cyan]Syncing code→spec (AST-based)...[/cyan]")
    try:
        code_to_spec_sync.sync(changeset.code_changes, bundle)
        console.print("[green]✓[/green] Code→spec sync complete")
    except Exception as e:
        console.print(f"[red]✗[/red] Code→spec sync failed: {e}")


def _intelligent_run_spec_to_code(
    spec_to_code: str, changeset: Any, bundle: str, spec_to_code_sync: Any, repo_path: Path, console: Any
) -> None:
    if spec_to_code != "llm-prompt" or not changeset.spec_changes:
        return
    console.print("\n[cyan]Preparing LLM prompts for spec→code...[/cyan]")
    try:
        context = spec_to_code_sync.prepare_llm_context(changeset.spec_changes, repo_path)
        prompt = spec_to_code_sync.generate_llm_prompt(context)
        prompts_dir = repo_path / ".specfact" / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        prompt_file = prompts_dir / f"{bundle}-code-generation-{len(changeset.spec_changes)}.md"
        prompt_file.write_text(prompt, encoding="utf-8")
        console.print(f"[green]✓[/green] LLM prompt generated: {prompt_file}")
        console.print("[yellow]Execute this prompt with your LLM to generate code[/yellow]")
    except Exception as e:
        console.print(f"[red]✗[/red] LLM prompt generation failed: {e}")


def _intelligent_run_spec_to_tests(
    tests: str, changeset: Any, bundle: str, spec_to_tests_sync: Any, console: Any
) -> None:
    if tests != "specmatic" or not changeset.spec_changes:
        return
    console.print("\n[cyan]Generating tests via Specmatic...[/cyan]")
    try:
        spec_to_tests_sync.sync(changeset.spec_changes, bundle)
        console.print("[green]✓[/green] Test generation complete")
    except Exception as e:
        console.print(f"[red]✗[/red] Test generation failed: {e}")


def make_intelligent_cycle_runner(
    *,
    change_detector: Any,
    project_bundle: Any,
    code_to_spec: str,
    spec_to_code: str,
    tests: str,
    bundle: str,
    repo_path: Path,
    code_to_spec_sync: Any,
    spec_to_code_sync: Any,
    spec_to_tests_sync: Any,
    console: Any,
) -> Any:
    """Return a callable that runs one intelligent sync cycle."""

    def run() -> None:
        run_intelligent_sync_cycle(
            change_detector=change_detector,
            project_bundle=project_bundle,
            code_to_spec=code_to_spec,
            spec_to_code=spec_to_code,
            tests=tests,
            bundle=bundle,
            repo_path=repo_path,
            code_to_spec_sync=code_to_spec_sync,
            spec_to_code_sync=spec_to_code_sync,
            spec_to_tests_sync=spec_to_tests_sync,
            console=console,
        )

    return run


def run_intelligent_sync_cycle(
    *,
    change_detector: Any,
    project_bundle: Any,
    code_to_spec: str,
    spec_to_code: str,
    tests: str,
    bundle: str,
    repo_path: Path,
    code_to_spec_sync: Any,
    spec_to_code_sync: Any,
    spec_to_tests_sync: Any,
    console: Any,
) -> None:
    """Perform one intelligent sync cycle (replaces nested perform_sync)."""
    console.print("\n[cyan]Detecting changes...[/cyan]")
    changeset = change_detector.detect_changes(project_bundle.features)
    if not _intelligent_report_changes(changeset, console):
        return
    _intelligent_run_code_to_spec(code_to_spec, changeset, bundle, code_to_spec_sync, console)
    _intelligent_run_spec_to_code(spec_to_code, changeset, bundle, spec_to_code_sync, repo_path, console)
    _intelligent_run_spec_to_tests(tests, changeset, bundle, spec_to_tests_sync, console)
