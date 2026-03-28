"""Setup helpers for `sync bridge` (cyclomatic complexity reduction)."""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
from specfact_cli.adapters.registry import AdapterRegistry
from specfact_cli.models.bridge import AdapterType

from specfact_project.sync_runtime.bridge_probe import BridgeProbe
from specfact_project.sync_runtime.sync_command_common import parse_backlog_selection


def maybe_auto_detect_adapter(repo: Path, adapter: str) -> str:
    if adapter not in ("speckit", "auto"):
        return adapter
    probe = BridgeProbe(repo)
    detected_capabilities = probe.detect()
    if detected_capabilities.tool != "unknown":
        return detected_capabilities.tool
    return "unknown"


def ensure_adapter_detected_or_exit(repo: Path, adapter: str) -> str:
    detected = maybe_auto_detect_adapter(repo, adapter)
    if detected != "unknown":
        return detected
    from specfact_cli.runtime import get_configured_console

    console = get_configured_console()
    console.print("[bold red]✗[/bold red] Could not auto-detect adapter")
    console.print("[dim]No registered adapter detected this repository structure[/dim]")
    registered = AdapterRegistry.list_adapters()
    console.print(f"[dim]Registered adapters: {', '.join(registered)}[/dim]")
    console.print("[dim]Tip: Specify adapter explicitly with --adapter <adapter>[/dim]")
    raise typer.Exit(1)


def ensure_registered_adapter_or_exit(adapter: str) -> str:
    from specfact_cli.runtime import get_configured_console

    adapter_lower = adapter.lower()
    if AdapterRegistry.is_registered(adapter_lower):
        return adapter_lower
    console = get_configured_console()
    console.print(f"[bold red]✗[/bold red] Unsupported adapter: {adapter}")
    registered = AdapterRegistry.list_adapters()
    console.print(f"[dim]Registered adapters: {', '.join(registered)}[/dim]")
    raise typer.Exit(1)


def adapter_type_from_lower(adapter_lower: str) -> AdapterType | None:
    try:
        return AdapterType(adapter_lower)
    except ValueError:
        return None


def probe_capabilities(repo: Path, adapter_lower: str) -> tuple[Any | None, Any | None]:
    adapter_instance = AdapterRegistry.get_adapter(adapter_lower)
    if not adapter_instance:
        return None, None
    probe = BridgeProbe(repo)
    capabilities = probe.detect()
    bridge_config = probe.auto_generate_bridge(capabilities) if capabilities.tool != "unknown" else None
    caps = adapter_instance.get_capabilities(repo, bridge_config)
    return adapter_instance, caps


def infer_default_sync_mode(
    bidirectional: bool,
    repo_owner: str | None,
    repo_name: str | None,
    supported_sync_modes: list[str] | None,
) -> str:
    if not supported_sync_modes:
        return "bidirectional" if bidirectional else "unidirectional"
    if "export-only" in supported_sync_modes and (repo_owner or repo_name):
        return "export-only"
    if "read-only" in supported_sync_modes:
        return "read-only"
    if "bidirectional" in supported_sync_modes:
        return "bidirectional" if bidirectional else "unidirectional"
    return "unidirectional"


def resolve_sync_mode(
    mode: str | None,
    bidirectional: bool,
    repo: Path,
    adapter_lower: str,
    repo_owner: str | None,
    repo_name: str | None,
) -> str:
    if mode is not None:
        return mode.lower()
    _ai, caps = probe_capabilities(repo, adapter_lower)
    if not caps:
        return "bidirectional" if bidirectional else "unidirectional"
    return infer_default_sync_mode(bidirectional, repo_owner, repo_name, caps.supported_sync_modes)


def validate_sync_mode_for_adapter_or_exit(
    sync_mode: str,
    adapter_lower: str,
    repo: Path,
) -> Any | None:
    from specfact_cli.runtime import get_configured_console

    console = get_configured_console()
    _ai, adapter_capabilities = probe_capabilities(repo, adapter_lower)
    if not adapter_capabilities:
        return None
    supported = adapter_capabilities.supported_sync_modes
    speckit_exception = adapter_lower == "speckit" and sync_mode == "change-proposal"
    if supported and sync_mode not in supported and not speckit_exception:
        console.print(f"[bold red]✗[/bold red] Sync mode '{sync_mode}' not supported by adapter '{adapter_lower}'")
        console.print(f"[dim]Supported modes: {', '.join(supported)}[/dim]")
        raise typer.Exit(1)
    return adapter_capabilities


def validate_tmp_flags_or_exit(export_to_tmp: bool, import_from_tmp: bool) -> None:
    from specfact_cli.runtime import get_configured_console

    if export_to_tmp and import_from_tmp:
        console = get_configured_console()
        console.print("[bold red]✗[/bold red] --export-to-tmp and --import-from-tmp are mutually exclusive")
        raise typer.Exit(1)


def parse_change_and_backlog_ids(
    change_ids: str | None,
    backlog_ids: str | None,
    backlog_ids_file: Path | None,
) -> tuple[list[str] | None, list[str]]:
    change_ids_list: list[str] | None = None
    if change_ids:
        change_ids_list = [cid.strip() for cid in change_ids.split(",") if cid.strip()]
    backlog_items: list[str] = []
    if backlog_ids:
        backlog_items.extend(parse_backlog_selection(backlog_ids))
    if backlog_ids_file:
        backlog_items.extend(parse_backlog_selection(backlog_ids_file.read_text(encoding="utf-8")))
    if backlog_items:
        backlog_items = list(dict.fromkeys(backlog_items))
    return change_ids_list, backlog_items
