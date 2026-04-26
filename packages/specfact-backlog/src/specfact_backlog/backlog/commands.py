"""
Backlog refinement commands.

This module provides the `specfact backlog refine` command for AI-assisted
backlog refinement with template detection and matching.

SpecFact CLI Architecture:
- SpecFact CLI generates prompts/instructions for IDE AI copilots
- IDE AI copilots execute those instructions using their native LLM
- IDE AI copilots feed results back to SpecFact CLI
- SpecFact CLI validates and processes the results
"""

from __future__ import annotations

import contextlib
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from importlib import import_module
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

import click
import typer
import yaml
from beartype import beartype
from icontract import ensure, require
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.prompt import Confirm
from rich.table import Table
from specfact_cli.adapters.registry import AdapterRegistry
from specfact_cli.models.backlog_item import BacklogItem
from specfact_cli.models.dor_config import DefinitionOfReady
from specfact_cli.models.plan import Product
from specfact_cli.models.project import BundleManifest, ProjectBundle
from specfact_cli.models.validation import ValidationReport
from specfact_cli.runtime import debug_log_operation
from typer.core import TyperGroup

from specfact_backlog.backlog.adapters.interface import BacklogAdapter
from specfact_backlog.backlog.ai_refiner import BacklogAIRefiner
from specfact_backlog.backlog.auth_commands import auth_app
from specfact_backlog.backlog.filters import BacklogFilters
from specfact_backlog.backlog.template_detector import TemplateDetector, get_effective_required_sections

# Import migrated backlog-core commands
from specfact_backlog.backlog_core.commands.add import add
from specfact_backlog.backlog_core.commands.analyze_deps import analyze_deps
from specfact_backlog.backlog_core.commands.delta import delta_app as _delta_app
from specfact_backlog.backlog_core.commands.diff import diff
from specfact_backlog.backlog_core.commands.promote import promote
from specfact_backlog.backlog_core.commands.sync import sync
from specfact_backlog.backlog_core.commands.verify import verify_readiness
from specfact_backlog.templates.registry import BacklogTemplate, TemplateRegistry


class _BacklogCommandGroup(TyperGroup):
    """Stable, impact-oriented ordering for backlog subcommands in help output."""

    _ORDER_PRIORITY: dict[str, int] = {
        # Ceremony and analytical groups first for discoverability.
        "ceremony": 10,
        "delta": 20,
        "auth": 25,
        # Core high-impact workflow actions.
        "sync": 30,
        "verify-readiness": 40,
        "analyze-deps": 50,
        "diff": 60,
        "promote": 70,
        "generate-release-notes": 80,
        "trace-impact": 90,
        # Compatibility / lower-frequency commands later.
        "refine": 100,
        "daily": 110,
        "init-config": 118,
        "map-fields": 120,
    }

    def list_commands(self, ctx: click.Context) -> list[str]:
        commands = list(super().list_commands(ctx))
        return sorted(commands, key=lambda name: (self._ORDER_PRIORITY.get(name, 1000), name))


def _is_interactive_tty() -> bool:
    """
    Return True when running in an interactive TTY suitable for rich Markdown rendering.

    CI and non-TTY environments should fall back to plain Markdown text to keep output machine-friendly.
    """
    try:
        return sys.stdout.isatty()
    except Exception:  # pragma: no cover - extremely defensive
        return False


class _CeremonyCommandGroup(TyperGroup):
    """Stable ordering for backlog ceremony subcommands."""

    _ORDER_PRIORITY: dict[str, int] = {
        "standup": 10,
        "refinement": 20,
        "planning": 30,
        "flow": 40,
        "pi-summary": 50,
    }

    def list_commands(self, ctx: click.Context) -> list[str]:
        commands = list(super().list_commands(ctx))
        return sorted(commands, key=lambda name: (self._ORDER_PRIORITY.get(name, 1000), name))


app = typer.Typer(
    name="backlog",
    help="Backlog refinement and template management",
    context_settings={"help_option_names": ["-h", "--help"]},
    cls=_BacklogCommandGroup,
)
ceremony_app = typer.Typer(
    name="ceremony",
    help="Ceremony-oriented backlog workflows",
    context_settings={"help_option_names": ["-h", "--help"]},
    cls=_CeremonyCommandGroup,
)
console = Console()

BundleMapperType = type[Any]
BundleMappingSaveFn = Callable[[BacklogItem, str, Path | None], None]
BundleMappingLoadFn = Callable[[Path | None], dict[str, Any]]
BundleMappingPromptFn = Callable[[Any, list[str]], str | None]
BundleMapperRuntimeDeps = tuple[
    BundleMapperType,
    BundleMappingSaveFn,
    BundleMappingLoadFn,
    BundleMappingPromptFn | None,
]


@dataclass(frozen=True)
class _AdapterContext:
    """Resolved adapter connection arguments shared across backlog command helpers."""

    adapter: str
    repo_owner: str | None = None
    repo_name: str | None = None
    github_token: str | None = None
    ado_org: str | None = None
    ado_project: str | None = None
    ado_team: str | None = None
    ado_token: str | None = None


@dataclass(frozen=True)
class _DailyScopeSummary:
    """Inputs for rendering a compact daily scope summary."""

    mode: str
    cli_state: str | None
    effective_state: str | None
    cli_assignee: str | None
    effective_assignee: str | None
    cli_limit: int | None
    effective_limit: int
    issue_id: str | None
    labels: list[str] | str | None
    sprint: str | None
    iteration: str | None
    release: str | None
    first_issues: int | None
    last_issues: int | None


@dataclass(frozen=True)
class _DailyInteractiveSession:
    """Runtime dependencies for the interactive standup navigator."""

    items: list[BacklogItem]
    questionary: Any
    adapter_instance: Any
    get_comments_fn: Callable[[BacklogItem], Any]
    suggest_next: bool
    first_comments: int | None
    last_comments: int | None


@beartype
@require(lambda source: source.exists(), "Source path must exist")
@ensure(lambda result: isinstance(result, ProjectBundle), "Must return ProjectBundle")
def import_to_bundle(source: Path, config: dict[str, Any]) -> ProjectBundle:
    """Convert external source artifacts into a ProjectBundle."""
    if source.is_dir() and (source / "bundle.manifest.yaml").exists():
        return ProjectBundle.load_from_directory(source)
    bundle_name = config.get("bundle_name", source.stem if source.suffix else source.name)
    return ProjectBundle(
        manifest=BundleManifest(schema_metadata=None, project_metadata=None),
        bundle_name=str(bundle_name),
        product=Product(),
    )


@beartype
@require(lambda target: target is not None, "Target path must be provided")
@ensure(lambda target: target.exists(), "Target must exist after export")
def export_from_bundle(bundle: ProjectBundle, target: Path, config: dict[str, Any]) -> None:
    """Export a ProjectBundle to target path."""
    if target.suffix:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
        return
    target.mkdir(parents=True, exist_ok=True)
    bundle.save_to_directory(target)


@beartype
@require(lambda external_source: len(external_source.strip()) > 0, "External source must be non-empty")
@ensure(lambda result: isinstance(result, ProjectBundle), "Must return ProjectBundle")
def sync_with_bundle(bundle: ProjectBundle, external_source: str, config: dict[str, Any]) -> ProjectBundle:
    """Synchronize an existing bundle with an external source."""
    source_path = Path(external_source)
    if source_path.exists() and source_path.is_dir() and (source_path / "bundle.manifest.yaml").exists():
        return ProjectBundle.load_from_directory(source_path)
    return bundle


@beartype
@ensure(lambda result: isinstance(result, ValidationReport), "Must return ValidationReport")
def validate_bundle(bundle: ProjectBundle, rules: dict[str, Any]) -> ValidationReport:
    """Validate bundle for module-specific constraints."""
    total_checks = max(len(rules), 1)
    report = ValidationReport(
        status="passed",
        violations=[],
        summary={"total_checks": total_checks, "passed": total_checks, "failed": 0, "warnings": 0},
    )
    if not bundle.bundle_name:
        report.status = "failed"
        report.violations.append(
            {
                "severity": "error",
                "message": "Bundle name is required",
                "location": "ProjectBundle.bundle_name",
            }
        )
        report.summary["failed"] += 1
        report.summary["passed"] = max(report.summary["passed"] - 1, 0)
    return report


@beartype
def _invoke_backlog_subcommand(subcommand_name: str, args: list[str]) -> None:
    """Invoke an existing backlog subcommand with forwarded args."""
    from typer.main import get_command

    click_group = get_command(app)
    if not isinstance(click_group, click.Group):
        raise typer.Exit(code=1)
    group_ctx = click.Context(click_group)
    subcommand = click_group.get_command(group_ctx, subcommand_name)
    if subcommand is None:
        raise typer.Exit(code=1)
    exit_code = subcommand.main(
        args=args,
        prog_name=f"specfact backlog {subcommand_name}",
        standalone_mode=False,
    )
    if exit_code and exit_code != 0:
        raise typer.Exit(code=int(exit_code))


@beartype
def _backlog_subcommand_exists(subcommand_name: str) -> bool:
    """Return True when a backlog subcommand is currently registered."""
    from typer.main import get_command

    click_group = get_command(app)
    if not isinstance(click_group, click.Group):
        return False
    group_ctx = click.Context(click_group)
    return click_group.get_command(group_ctx, subcommand_name) is not None


@beartype
def _forward_mode_if_supported(subcommand_name: str, mode: str, forwarded: list[str]) -> list[str]:
    """Append `--mode` only when delegated subcommand supports it."""
    from typer.main import get_command

    click_group = get_command(app)
    if not isinstance(click_group, click.Group):
        return forwarded
    group_ctx = click.Context(click_group)
    subcommand = click_group.get_command(group_ctx, subcommand_name)
    if subcommand is None:
        return forwarded
    supports_mode = any(
        isinstance(param, click.Option) and "--mode" in param.opts for param in getattr(subcommand, "params", [])
    )
    if supports_mode:
        return [*forwarded, "--mode", mode]
    return forwarded


@beartype
def _invoke_optional_ceremony_delegate(
    candidate_subcommands: list[str],
    args: list[str],
    *,
    ceremony_name: str,
) -> None:
    """Invoke first available delegate command, otherwise fail with a clear message."""
    for subcommand_name in candidate_subcommands:
        if _backlog_subcommand_exists(subcommand_name):
            _invoke_backlog_subcommand(subcommand_name, args)
            return
    targets = ", ".join(candidate_subcommands)
    console.print(
        f"[yellow]`backlog ceremony {ceremony_name}` requires an installed backlog module "
        f"providing one of: {targets}[/yellow]"
    )
    raise typer.Exit(code=2)


@beartype
@ceremony_app.command(
    "standup",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def ceremony_standup(
    ctx: click.Context,
    adapter: str = typer.Argument(..., help="Backlog adapter name (github, ado, etc.)"),
    mode: str = typer.Option("scrum", "--mode", help="Ceremony mode (default: scrum)"),
) -> None:
    """Ceremony alias for `backlog daily`."""
    forwarded = _forward_mode_if_supported("daily", mode, [adapter])
    _invoke_backlog_subcommand("daily", [*forwarded, *ctx.args])


@beartype
@ceremony_app.command(
    "refinement",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def ceremony_refinement(
    ctx: click.Context,
    adapter: str = typer.Argument(..., help="Backlog adapter name (github, ado, etc.)"),
) -> None:
    """Ceremony alias for `backlog refine`."""
    _invoke_backlog_subcommand("refine", [adapter, *ctx.args])


@beartype
@ceremony_app.command(
    "planning",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def ceremony_planning(
    ctx: click.Context,
    adapter: str = typer.Argument(..., help="Backlog adapter name (github, ado, etc.)"),
    mode: str = typer.Option("scrum", "--mode", help="Ceremony mode (default: scrum)"),
) -> None:
    """Ceremony alias for backlog planning/sprint summary views."""
    delegate = "sprint-summary"
    forwarded = _forward_mode_if_supported(delegate, mode, [adapter])
    _invoke_optional_ceremony_delegate([delegate], [*forwarded, *ctx.args], ceremony_name="planning")


@beartype
@ceremony_app.command(
    "flow",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def ceremony_flow(
    ctx: click.Context,
    adapter: str = typer.Argument(..., help="Backlog adapter name (github, ado, etc.)"),
    mode: str = typer.Option("kanban", "--mode", help="Ceremony mode (default: kanban)"),
) -> None:
    """Ceremony alias for backlog flow-oriented views."""
    delegate = "flow"
    forwarded = _forward_mode_if_supported(delegate, mode, [adapter])
    _invoke_optional_ceremony_delegate([delegate], [*forwarded, *ctx.args], ceremony_name="flow")


@beartype
@ceremony_app.command(
    "pi-summary",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def ceremony_pi_summary(
    ctx: click.Context,
    adapter: str = typer.Argument(..., help="Backlog adapter name (github, ado, etc.)"),
    mode: str = typer.Option("safe", "--mode", help="Ceremony mode (default: safe)"),
) -> None:
    """Ceremony alias for backlog PI summary views."""
    delegate = "pi-summary"
    forwarded = _forward_mode_if_supported(delegate, mode, [adapter])
    _invoke_optional_ceremony_delegate([delegate], [*forwarded, *ctx.args], ceremony_name="pi-summary")


def _matches_labels(item: BacklogItem, labels: list[str]) -> bool:
    item_tags = [tag.lower() for tag in item.tags]
    return any(label.lower() in item_tags for label in labels)


def _matches_normalized_state(item: BacklogItem, normalized_state: str | None) -> bool:
    if normalized_state is None:
        return False
    return BacklogFilters.normalize_filter_value(item.state) == normalized_state


def _matches_normalized_assignee(item: BacklogItem, normalized_assignee: str | None) -> bool:
    if normalized_assignee is None or not item.assignees:
        return False
    return any(BacklogFilters.normalize_filter_value(a) == normalized_assignee for a in item.assignees if a)


def _matches_iteration(item: BacklogItem, normalized_iteration: str | None) -> bool:
    if normalized_iteration is None:
        return False
    return bool(item.iteration and BacklogFilters.normalize_filter_value(item.iteration) == normalized_iteration)


def _matches_sprint(item: BacklogItem, normalized_sprint: str | None) -> bool:
    if normalized_sprint is None:
        return False
    return bool(item.sprint and BacklogFilters.normalize_filter_value(item.sprint) == normalized_sprint)


def _matches_release(item: BacklogItem, normalized_release: str | None) -> bool:
    if normalized_release is None:
        return False
    return bool(item.release and BacklogFilters.normalize_filter_value(item.release) == normalized_release)


def _normalized_filter_value(value: str | None) -> str | None:
    return BacklogFilters.normalize_filter_value(value) if value else None


def _filter_items(items: list[BacklogItem], predicate: Callable[[BacklogItem], bool]) -> list[BacklogItem]:
    return [item for item in items if predicate(item)]


def _apply_filters(
    items: list[BacklogItem],
    labels: list[str] | None = None,
    state: str | None = None,
    assignee: str | None = None,
    iteration: str | None = None,
    sprint: str | None = None,
    release: str | None = None,
) -> list[BacklogItem]:
    """
    Apply post-fetch filters to backlog items.

    Args:
        items: List of BacklogItem instances to filter
        labels: Filter by labels/tags (any label must match)
        state: Filter by state (exact match)
        assignee: Filter by assignee (exact match)
        iteration: Filter by iteration path (exact match)
        sprint: Filter by sprint (exact match)
        release: Filter by release (exact match)

    Returns:
        Filtered list of BacklogItem instances
    """
    filtered = items
    normalized_state = _normalized_filter_value(state)
    normalized_assignee = _normalized_filter_value(assignee)
    normalized_iteration = _normalized_filter_value(iteration)
    normalized_sprint = _normalized_filter_value(sprint)
    normalized_release = _normalized_filter_value(release)

    predicates: list[Callable[[BacklogItem], bool]] = []
    if labels:
        predicates.append(lambda item, wanted=labels: _matches_labels(item, wanted))
    if normalized_state is not None:
        predicates.append(lambda item, value=normalized_state: _matches_normalized_state(item, value))
    if normalized_assignee is not None:
        predicates.append(lambda item, value=normalized_assignee: _matches_normalized_assignee(item, value))
    if normalized_iteration is not None:
        predicates.append(lambda item, value=normalized_iteration: _matches_iteration(item, value))
    if normalized_sprint is not None:
        predicates.append(lambda item, value=normalized_sprint: _matches_sprint(item, value))
    if normalized_release is not None:
        predicates.append(lambda item, value=normalized_release: _matches_release(item, value))

    for predicate in predicates:
        filtered = _filter_items(filtered, predicate)

    return filtered


def _parse_standup_from_body(body: str) -> tuple[str | None, str | None, str | None]:
    """Extract yesterday/today/blockers lines from body (standup format)."""
    yesterday: str | None = None
    today: str | None = None
    blockers: str | None = None
    if not body:
        return yesterday, today, blockers
    for line in body.splitlines():
        line_stripped = line.strip()
        if re.match(r"^\*\*[Yy]esterday(?:\*\*|:)\s*\*\*\s*", line_stripped):
            yesterday = re.sub(r"^\*\*[Yy]esterday(?:\*\*|:)\s*\*\*\s*", "", line_stripped).strip()
        elif re.match(r"^\*\*[Tt]oday(?:\*\*|:)\s*\*\*\s*", line_stripped):
            today = re.sub(r"^\*\*[Tt]oday(?:\*\*|:)\s*\*\*\s*", "", line_stripped).strip()
        elif re.match(r"^\*\*[Bb]lockers?(?:\*\*|:)\s*\*\*\s*", line_stripped):
            blockers = re.sub(r"^\*\*[Bb]lockers?(?:\*\*|:)\s*\*\*\s*", "", line_stripped).strip()
    return yesterday, today, blockers


def _load_standup_config() -> dict[str, Any]:
    """Load standup config from env and optional .specfact/standup.yaml. Env overrides file."""
    config: dict[str, Any] = {}
    config_dir = os.environ.get("SPECFACT_CONFIG_DIR")
    search_paths: list[Path] = []
    if config_dir:
        search_paths.append(Path(config_dir))
    search_paths.append(Path.cwd() / ".specfact")
    for base in search_paths:
        path = base / "standup.yaml"
        if path.is_file():
            try:
                with open(path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                config = dict(data.get("standup", data))
            except Exception as exc:
                debug_log_operation("config_load", str(path), "error", error=repr(exc))
            break
    if os.environ.get("SPECFACT_STANDUP_STATE"):
        config["default_state"] = os.environ["SPECFACT_STANDUP_STATE"]
    if os.environ.get("SPECFACT_STANDUP_LIMIT"):
        with contextlib.suppress(ValueError):
            config["limit"] = int(os.environ["SPECFACT_STANDUP_LIMIT"])
    if os.environ.get("SPECFACT_STANDUP_ASSIGNEE"):
        config["default_assignee"] = os.environ["SPECFACT_STANDUP_ASSIGNEE"]
    return config


def _load_backlog_config() -> dict[str, Any]:
    """Load project backlog context from .specfact/backlog.yaml (no secrets).
    Same search path as standup: SPECFACT_CONFIG_DIR then .specfact in cwd.
    When file has top-level 'backlog' key, that nested structure is returned.
    """
    config: dict[str, Any] = {}
    config_dir = os.environ.get("SPECFACT_CONFIG_DIR")
    search_paths: list[Path] = []
    if config_dir:
        search_paths.append(Path(config_dir))
    search_paths.append(Path.cwd() / ".specfact")
    for base in search_paths:
        path = base / "backlog.yaml"
        if path.is_file():
            try:
                with open(path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                if isinstance(data, dict) and "backlog" in data:
                    nested = data["backlog"]
                    config = dict(nested) if isinstance(nested, dict) else {}
                else:
                    config = dict(data) if isinstance(data, dict) else {}
            except Exception as exc:
                debug_log_operation("config_load", str(path), "error", error=repr(exc))
            break
    return config


@beartype
def _load_backlog_module_config_file() -> tuple[dict[str, Any], Path]:
    """Load canonical backlog module config from `.specfact/backlog-config.yaml`."""
    config_dir = os.environ.get("SPECFACT_CONFIG_DIR")
    search_paths: list[Path] = []
    if config_dir:
        search_paths.append(Path(config_dir))
    search_paths.append(Path.cwd() / ".specfact")

    for base in search_paths:
        path = base / "backlog-config.yaml"
        if path.is_file():
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                if isinstance(data, dict):
                    return data, path
            except Exception as exc:
                debug_log_operation("config_load", str(path), "error", error=repr(exc))
            return {}, path

    default_path = search_paths[-1] / "backlog-config.yaml"
    return {}, default_path


@beartype
def _load_owned_yaml_mapping_file(path: Path, *, artifact_name: str) -> dict[str, Any]:
    """Load a partially owned YAML mapping file and fail safe on unsupported shapes."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        msg = f"{artifact_name} is not valid YAML: {path} ({exc})"
        raise ValueError(msg) from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        msg = f"{artifact_name} must contain a top-level mapping: {path}"
        raise ValueError(msg)
    return data


@beartype
def _write_yaml_mapping_file(path: Path, payload: dict[str, Any]) -> None:
    """Persist a YAML mapping with stable key order for owned SpecFact artifacts."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


@beartype
def _save_backlog_module_config_file(config: dict[str, Any], path: Path) -> None:
    """Persist canonical backlog module config to `.specfact/backlog-config.yaml`."""
    _write_yaml_mapping_file(path, config)


class _ReplaceSettingValue:
    """Marker used to replace a config subtree atomically during provider setting updates."""

    def __init__(self, value: Any) -> None:
        self.value = value


@beartype
def _upsert_backlog_provider_settings(
    provider: str,
    settings_update: dict[str, Any],
    *,
    project_id: str | None = None,
    adapter: str | None = None,
) -> Path:
    """Merge provider settings into `.specfact/backlog-config.yaml` and save."""
    cfg, path = _load_backlog_module_config_file()
    backlog_config = cfg.get("backlog_config")
    if not isinstance(backlog_config, dict):
        backlog_config = {}
    providers = backlog_config.get("providers")
    if not isinstance(providers, dict):
        providers = {}

    provider_cfg = providers.get(provider)
    if not isinstance(provider_cfg, dict):
        provider_cfg = {}

    if adapter:
        provider_cfg["adapter"] = adapter
    if project_id:
        provider_cfg["project_id"] = project_id

    settings = provider_cfg.get("settings")
    if not isinstance(settings, dict):
        settings = {}

    def _deep_merge(dst: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
        for key, value in src.items():
            if isinstance(value, _ReplaceSettingValue):
                dst[key] = value.value
                continue
            if value is None:
                dst.pop(key, None)
                continue
            if isinstance(value, dict) and isinstance(dst.get(key), dict):
                _deep_merge(dst[key], value)
            else:
                dst[key] = value
        return dst

    _deep_merge(settings, settings_update)
    provider_cfg["settings"] = settings
    providers[provider] = provider_cfg
    backlog_config["providers"] = providers
    cfg["backlog_config"] = backlog_config

    _save_backlog_module_config_file(cfg, path)
    return path


@beartype
def _resolve_backlog_provider_framework(provider: str) -> str | None:
    """Resolve configured framework for a backlog provider from backlog-config and mapping files."""
    normalized_provider = provider.strip().lower()
    if not normalized_provider:
        return None

    cfg, _path = _load_backlog_module_config_file()
    backlog_config = cfg.get("backlog_config")
    if isinstance(backlog_config, dict):
        providers = backlog_config.get("providers")
        if isinstance(providers, dict):
            provider_cfg = providers.get(normalized_provider)
            if isinstance(provider_cfg, dict):
                settings = provider_cfg.get("settings")
                if isinstance(settings, dict):
                    configured = str(settings.get("framework") or "").strip().lower()
                    if configured:
                        return configured

    # ADO fallback: read framework from custom mapping file when provider settings are absent.
    if normalized_provider == "ado":
        mapping_path = Path.cwd() / ".specfact" / "templates" / "backlog" / "field_mappings" / "ado_custom.yaml"
        if mapping_path.exists():
            with contextlib.suppress(Exception):
                from specfact_backlog.backlog.mappers.template_config import FieldMappingConfig

                config = FieldMappingConfig.from_file(mapping_path)
                configured = str(config.framework or "").strip().lower()
                if configured:
                    return configured

    return None


@beartype
def _resolve_standup_options(
    cli_state: str | None,
    cli_limit: int | None,
    cli_assignee: str | None,
    config: dict[str, Any] | None,
    *,
    state_filter_disabled: bool = False,
    assignee_filter_disabled: bool = False,
) -> tuple[str | None, int, str | None]:
    """
    Resolve effective state, limit, assignee from CLI options and config.
    CLI options override config; config overrides built-in defaults.
    Returns (state, limit, assignee).
    """
    cfg = config or _load_standup_config()
    default_state = str(cfg.get("default_state", "open"))
    default_limit = int(cfg.get("limit", 20)) if cfg.get("limit") is not None else 20
    default_assignee = cfg.get("default_assignee")
    if default_assignee is not None:
        default_assignee = str(default_assignee)
    state = None if state_filter_disabled else (cli_state if cli_state is not None else default_state)
    limit = cli_limit if cli_limit is not None else default_limit
    assignee = None if assignee_filter_disabled else (cli_assignee if cli_assignee is not None else default_assignee)
    return (state, limit, assignee)


@beartype
def _resolve_post_fetch_assignee_filter(adapter: str, assignee: str | None) -> str | None:
    """
    Resolve assignee value for local post-fetch filtering.

    For GitHub, `me`/`@me` should be handled by adapter-side query semantics and
    not re-filtered locally as a literal username.
    """
    if not assignee:
        return assignee
    if adapter.lower() == "github":
        normalized = BacklogFilters.normalize_filter_value(assignee.lstrip("@"))
        if normalized == "me":
            return None
    return assignee


@beartype
def _normalize_state_filter_value(state: str | None) -> str | None:
    """Normalize state filter literals and map `any` to no-filter."""
    if state is None:
        return None
    normalized = BacklogFilters.normalize_filter_value(state)
    if normalized in {"any", "all", "*"}:
        return None
    return state


@beartype
def _normalize_assignee_filter_value(assignee: str | None) -> str | None:
    """Normalize assignee filter literals and map `any`/`@any` to no-filter."""
    if assignee is None:
        return None
    normalized = BacklogFilters.normalize_filter_value(assignee.lstrip("@"))
    if normalized in {"any", "all", "*"}:
        return None
    return assignee


@beartype
def _is_filter_disable_literal(value: str | None) -> bool:
    """Return True when CLI filter literal explicitly disables filtering."""
    if value is None:
        return False
    normalized = BacklogFilters.normalize_filter_value(value.lstrip("@"))
    return normalized in {"any", "all", "*"}


@beartype
def _split_assigned_unassigned(items: list[BacklogItem]) -> tuple[list[BacklogItem], list[BacklogItem]]:
    """Split items into assigned and unassigned (assignees empty or None)."""
    assigned: list[BacklogItem] = []
    unassigned: list[BacklogItem] = []
    for item in items:
        if item.assignees:
            assigned.append(item)
        else:
            unassigned.append(item)
    return (assigned, unassigned)


def _format_sprint_end_header(end_date: date) -> str:
    """Format sprint end date as 'Sprint ends: YYYY-MM-DD (N days)'."""
    today = date.today()
    delta = (end_date - today).days
    return f"Sprint ends: {end_date.isoformat()} ({delta} days)"


@beartype
def _sort_standup_rows_blockers_first(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort standup rows so items with non-empty blockers appear first."""
    with_blockers = [r for r in rows if (r.get("blockers") or "").strip()]
    without = [r for r in rows if not (r.get("blockers") or "").strip()]
    return with_blockers + without


@beartype
def _build_standup_rows(
    items: list[BacklogItem],
    include_priority: bool = False,
) -> list[dict[str, Any]]:
    """
    Build standup view rows from backlog items (id, title, status, last_updated, optional yesterday/today/blockers).
    When include_priority is True and item has priority/business_value, add to row.
    """
    rows: list[dict[str, Any]] = []
    for item in items:
        yesterday, today, blockers = _parse_standup_from_body(item.body_markdown or "")
        row: dict[str, Any] = {
            "id": item.id,
            "title": item.title,
            "status": item.state,
            "assignees": ", ".join(item.assignees) if item.assignees else "—",
            "last_updated": item.updated_at,
            "yesterday": yesterday or "",
            "today": today or "",
            "blockers": blockers or "",
        }
        if include_priority and item.priority is not None:
            row["priority"] = item.priority
        elif include_priority and item.business_value is not None:
            row["priority"] = item.business_value
        rows.append(row)
    return rows


@beartype
def _format_standup_comment(yesterday: str, today: str, blockers: str) -> str:
    """Format standup text as a comment (Yesterday / Today / Blockers) with date prefix."""
    prefix = f"Standup {date.today().isoformat()}"
    parts = [prefix, ""]
    if yesterday:
        parts.append(f"**Yesterday:** {yesterday}")
    if today:
        parts.append(f"**Today:** {today}")
    if blockers:
        parts.append(f"**Blockers:** {blockers}")
    return "\n".join(parts).strip()


@beartype
def _post_standup_comment_supported(adapter: BacklogAdapter, item: BacklogItem) -> bool:
    """Return True if the adapter supports adding comments (e.g. for standup post)."""
    return adapter.supports_add_comment()


@beartype
def _post_standup_to_item(adapter: BacklogAdapter, item: BacklogItem, body: str) -> bool:
    """Post standup comment to the linked issue via adapter. Returns True on success."""
    return adapter.add_comment(item, body)


@beartype
@ensure(
    lambda result: result is None or (isinstance(result, (int, float)) and result >= 0),
    "Value score is non-negative when present",
)
def _compute_value_score(item: BacklogItem) -> float | None:
    """
    Compute value score for next-best suggestion: business_value / max(1, story_points * priority).

    Returns None when any of story_points, business_value, or priority is missing.
    """
    if item.story_points is None or item.business_value is None or item.priority is None:
        return None
    denom = max(1, (item.story_points or 0) * (item.priority or 1))
    return item.business_value / denom


@beartype
def _format_daily_item_detail(
    item: BacklogItem,
    comments: list[str],
    *,
    show_all_provided_comments: bool = False,
    total_comments: int | None = None,
) -> str:
    """
    Format a single backlog item for interactive detail view (refine-like).

    Includes ID, title, status, assignees, last updated, description, acceptance criteria,
    standup fields (yesterday/today/blockers), and comments when provided.
    """
    parts: list[str] = []
    parts.append(f"## {item.id} - {item.title}")
    parts.append(f"- **Status:** {item.state}")
    assignee_str = ", ".join(item.assignees) if item.assignees else "—"
    parts.append(f"- **Assignees:** {assignee_str}")
    updated = (
        item.updated_at.strftime("%Y-%m-%d %H:%M") if hasattr(item.updated_at, "strftime") else str(item.updated_at)
    )
    parts.append(f"- **Last updated:** {updated}")
    if item.body_markdown:
        parts.append("\n**Description:**")
        parts.append(item.body_markdown.strip())
    if item.acceptance_criteria:
        parts.append("\n**Acceptance criteria:**")
        parts.append(item.acceptance_criteria.strip())
    yesterday, today, blockers = _parse_standup_from_body(item.body_markdown or "")
    if yesterday or today or blockers:
        parts.append("\n**Standup:**")
        if yesterday:
            parts.append(f"- Yesterday: {yesterday}")
        if today:
            parts.append(f"- Today: {today}")
        if blockers:
            parts.append(f"- Blockers: {blockers}")
    if item.story_points is not None:
        parts.append(f"\n- **Story points:** {item.story_points}")
    if item.business_value is not None:
        parts.append(f"- **Business value:** {item.business_value}")
    if item.priority is not None:
        parts.append(f"- **Priority:** {item.priority}")
    _ = (comments, show_all_provided_comments, total_comments)
    return "\n".join(parts)


@beartype
def _apply_comment_window(
    comments: list[str],
    *,
    first_comments: int | None = None,
    last_comments: int | None = None,
) -> list[str]:
    """Apply optional first/last comment window; default returns all comments."""
    if first_comments is not None and last_comments is not None:
        msg = "Use only one of --first-comments or --last-comments."
        raise ValueError(msg)
    if first_comments is not None:
        return comments[: max(first_comments, 0)]
    if last_comments is not None:
        return comments[-last_comments:] if last_comments > 0 else []
    return comments


@beartype
def _apply_issue_window(
    items: list[BacklogItem],
    *,
    first_issues: int | None = None,
    last_issues: int | None = None,
) -> list[BacklogItem]:
    """Apply optional first/last issue window to already-filtered items."""
    if first_issues is not None and last_issues is not None:
        msg = "Use only one of --first-issues or --last-issues."
        raise ValueError(msg)
    if first_issues is not None or last_issues is not None:

        def _issue_number(item: BacklogItem) -> int:
            if item.id.isdigit():
                return int(item.id)
            issue_match = re.search(r"/issues/(\d+)", item.url or "")
            if issue_match:
                return int(issue_match.group(1))
            ado_match = re.search(r"/(?:_workitems/edit|workitems)/(\d+)", item.url or "", re.IGNORECASE)
            if ado_match:
                return int(ado_match.group(1))
            return sys.maxsize

        sorted_items = sorted(items, key=_issue_number)
        if first_issues is not None:
            return sorted_items[: max(first_issues, 0)]
        if last_issues is not None:
            return sorted_items[-last_issues:] if last_issues > 0 else []
    return items


@beartype
def _apply_issue_id_filter(items: list[BacklogItem], issue_id: str | None) -> list[BacklogItem]:
    """Apply optional exact issue/work-item ID filter."""
    if issue_id is None:
        return items
    return [i for i in items if str(i.id) == str(issue_id)]


@beartype
def _resolve_refine_preview_comment_window(
    *,
    first_comments: int | None,
    last_comments: int | None,
) -> tuple[int | None, int | None]:
    """Resolve comment window for refine preview output."""
    if first_comments is not None:
        return first_comments, None
    if last_comments is not None:
        return None, last_comments
    # Keep preview concise by default while still showing current discussion.
    return None, 2


@beartype
def _resolve_refine_export_comment_window(
    *,
    first_comments: int | None,
    last_comments: int | None,
) -> tuple[int | None, int | None]:
    """Resolve comment window for refine export output (always full history)."""
    _ = (first_comments, last_comments)
    return None, None


@beartype
def _resolve_daily_issue_window(
    items: list[BacklogItem],
    *,
    first_issues: int | None,
    last_issues: int | None,
) -> list[BacklogItem]:
    """Resolve and apply daily issue-window options with refine-aligned semantics."""
    if first_issues is not None and last_issues is not None:
        msg = "Use only one of --first-issues or --last-issues"
        raise ValueError(msg)
    return _apply_issue_window(items, first_issues=first_issues, last_issues=last_issues)


@beartype
def _resolve_daily_fetch_limit(
    effective_limit: int,
    *,
    first_issues: int | None,
    last_issues: int | None,
) -> int | None:
    """Resolve pre-fetch limit for daily command."""
    if first_issues is not None or last_issues is not None:
        return None
    return effective_limit


@beartype
def _resolve_daily_display_limit(
    effective_limit: int,
    *,
    first_issues: int | None,
    last_issues: int | None,
) -> int | None:
    """Resolve post-window display limit for daily command."""
    if first_issues is not None or last_issues is not None:
        return None
    return effective_limit


@beartype
def _resolve_daily_mode_state(
    *,
    mode: str,
    cli_state: str | None,
    effective_state: str | None,
) -> str | None:
    """Resolve daily state behavior per mode while preserving explicit CLI state."""
    if cli_state is not None:
        return effective_state
    if mode == "kanban":
        return None
    return effective_state


@beartype
def _format_daily_scope_summary(summary: _DailyScopeSummary) -> str:
    """Build a compact scope summary for daily output with explicit/default source markers."""

    def _source(*, cli_value: object | None, disabled: bool = False) -> str:
        if disabled:
            return "disabled by --id"
        if cli_value is not None:
            return "explicit"
        return "default"

    scope_parts: list[str] = [f"mode={summary.mode} (explicit)"]

    state_disabled = summary.issue_id is not None and summary.cli_state is None
    state_value = summary.effective_state if summary.effective_state else "—"
    scope_parts.append(f"state={state_value} ({_source(cli_value=summary.cli_state, disabled=state_disabled)})")

    assignee_disabled = summary.issue_id is not None and summary.cli_assignee is None
    assignee_value = summary.effective_assignee if summary.effective_assignee else "—"
    scope_parts.append(
        f"assignee={assignee_value} ({_source(cli_value=summary.cli_assignee, disabled=assignee_disabled)})"
    )

    limit_source = _source(cli_value=summary.cli_limit)
    if summary.first_issues is not None or summary.last_issues is not None:
        limit_source = "disabled by issue window"
    scope_parts.append(f"limit={summary.effective_limit} ({limit_source})")

    if summary.issue_id is not None:
        scope_parts.append("id=" + summary.issue_id + " (explicit)")
    if summary.labels:
        labels_value = ", ".join(summary.labels) if isinstance(summary.labels, list) else summary.labels
        scope_parts.append("labels=" + labels_value + " (explicit)")
    if summary.sprint:
        scope_parts.append("sprint=" + summary.sprint + " (explicit)")
    if summary.iteration:
        scope_parts.append("iteration=" + summary.iteration + " (explicit)")
    if summary.release:
        scope_parts.append("release=" + summary.release + " (explicit)")
    if summary.first_issues is not None:
        scope_parts.append(f"first_issues={summary.first_issues} (explicit)")
    if summary.last_issues is not None:
        scope_parts.append(f"last_issues={summary.last_issues} (explicit)")

    return "Applied filters: " + ", ".join(scope_parts)


@beartype
def _has_policy_failure(row: dict[str, Any]) -> bool:
    """Return True when row indicates a policy failure signal."""
    policy_status = str(row.get("policy_status", "")).strip().lower()
    if policy_status in {"failed", "fail", "violation", "violated"}:
        return True
    failures = row.get("policy_failures")
    if isinstance(failures, list):
        return len(failures) > 0
    return bool(failures)


@beartype
def _has_aging_or_stalled_signal(row: dict[str, Any]) -> bool:
    """Return True when row indicates aging/stalled work."""
    stalled = row.get("stalled")
    if isinstance(stalled, bool):
        if stalled:
            return True
    elif str(stalled).strip().lower() in {"true", "yes", "1"}:
        return True
    days_stalled = row.get("days_stalled")
    if isinstance(days_stalled, (int, float)):
        return days_stalled > 0
    aging_days = row.get("aging_days")
    if isinstance(aging_days, (int, float)):
        return aging_days > 0
    return False


@beartype
def _exception_priority(row: dict[str, Any]) -> int:
    """Return exception priority rank: blockers, policy, aging, normal."""
    if str(row.get("blockers", "")).strip():
        return 0
    if _has_policy_failure(row):
        return 1
    if _has_aging_or_stalled_signal(row):
        return 2
    return 3


@beartype
def _split_exception_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split standup rows into exceptions-first and normal rows with stable ordering."""
    exceptions = sorted((row for row in rows if _exception_priority(row) < 3), key=_exception_priority)
    normal = [row for row in rows if _exception_priority(row) == 3]
    return exceptions, normal


@beartype
def _build_daily_patch_proposal(items: list[BacklogItem], *, mode: str) -> str:
    """Build a non-destructive patch proposal preview for standup notes."""
    lines: list[str] = []
    lines.append("# Patch Proposal")
    lines.append("")
    lines.append(f"- Mode: {mode}")
    lines.append(f"- Items in scope: {len(items)}")
    lines.append("- Action: Propose standup note/field updates only (no silent writes).")
    lines.append("")
    lines.append("## Candidate Items")
    for item in items[:10]:
        lines.append(f"- {item.id}: {item.title}")
    if len(items) > 10:
        lines.append(f"- ... and {len(items) - 10} more")
    return "\n".join(lines)


@beartype
def _is_patch_mode_available() -> bool:
    """Detect whether patch command group is available in current installation."""
    try:
        result = subprocess.run(
            ["specfact", "patch", "--help"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


@beartype
def _load_bundle_mapper_runtime_dependencies() -> BundleMapperRuntimeDeps | None:
    """Load optional bundle-mapper runtime dependencies."""
    try:
        bundle_mapper_cls = import_module("bundle_mapper.mapper.engine").BundleMapper
        history_module = import_module("bundle_mapper.mapper.history")
        interactive_module = import_module("bundle_mapper.ui.interactive")
        save_user_confirmed_mapping = history_module.save_user_confirmed_mapping
        load_bundle_mapping_config = history_module.load_bundle_mapping_config
        ask_bundle_mapping = getattr(interactive_module, "ask_bundle_mapping", None)
        return (bundle_mapper_cls, save_user_confirmed_mapping, load_bundle_mapping_config, ask_bundle_mapping)
    except ImportError:
        return None


@beartype
def _route_bundle_mapping_decision(
    mapping: Any,
    *,
    available_bundle_ids: list[str],
    auto_assign_threshold: float,
    confirm_threshold: float,
    prompt_callback: Callable[[Any, list[str]], str | None] | None,
) -> str | None:
    """Apply confidence routing rules to one computed mapping."""
    primary_bundle = getattr(mapping, "primary_bundle_id", None)
    confidence = float(getattr(mapping, "confidence", 0.0))

    if primary_bundle and confidence >= auto_assign_threshold:
        return str(primary_bundle)
    if prompt_callback is None:
        return str(primary_bundle) if primary_bundle else None
    if confidence >= confirm_threshold:
        return prompt_callback(mapping, available_bundle_ids)
    return prompt_callback(mapping, available_bundle_ids)


@beartype
def _derive_available_bundle_ids(bundle_path: Path | None) -> list[str]:
    """Derive available bundle IDs from explicit bundle path and local project bundles."""
    candidates: list[str] = []
    if bundle_path:
        if bundle_path.is_dir():
            candidates.append(bundle_path.name)
        else:
            # Avoid treating common manifest filenames (bundle.yaml) as bundle IDs.
            stem = bundle_path.stem.strip()
            if stem and stem.lower() != "bundle":
                candidates.append(stem)
            elif bundle_path.parent.name not in {".specfact", "projects", ""}:
                candidates.append(bundle_path.parent.name)

    projects_dir = Path.cwd() / ".specfact" / "projects"
    if projects_dir.exists():
        for child in sorted(projects_dir.iterdir()):
            if child.is_dir():
                candidates.append(child.name)

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = candidate.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


@beartype
def _resolve_bundle_mapping_config_path() -> Path | None:
    """Resolve mapping history/rules config path, separate from bundle manifest path."""
    config_dir = os.environ.get("SPECFACT_CONFIG_DIR")
    if config_dir:
        return Path(config_dir) / "config.yaml"
    if (Path.cwd() / ".specfact").exists():
        return Path.cwd() / ".specfact" / "config.yaml"
    return None


@beartype
def _apply_bundle_mappings_for_items(
    *,
    items: list[BacklogItem],
    available_bundle_ids: list[str],
    config_path: Path | None,
) -> dict[str, str]:
    """Execute bundle mapping flow for refined items and persist selected mappings."""
    runtime_deps = _load_bundle_mapper_runtime_dependencies()
    if runtime_deps is None:
        return {}

    bundle_mapper_cls, save_user_confirmed_mapping, load_bundle_mapping_config, ask_bundle_mapping = runtime_deps
    cfg = load_bundle_mapping_config(config_path)
    auto_assign_threshold = float(cfg.get("auto_assign_threshold", 0.8))
    confirm_threshold = float(cfg.get("confirm_threshold", 0.5))

    mapper = bundle_mapper_cls(
        available_bundle_ids=available_bundle_ids,
        config_path=config_path,
        bundle_spec_keywords={},
    )

    selected_by_item_id: dict[str, str] = {}
    for item in items:
        mapping = mapper.compute_mapping(item)
        selected = _route_bundle_mapping_decision(
            mapping,
            available_bundle_ids=available_bundle_ids,
            auto_assign_threshold=auto_assign_threshold,
            confirm_threshold=confirm_threshold,
            prompt_callback=ask_bundle_mapping,
        )
        if not selected:
            continue
        selected_by_item_id[str(item.id)] = selected
        save_user_confirmed_mapping(item, selected, config_path)

    return selected_by_item_id


@beartype
def _build_refine_preview_comment_panels(comments: list[str]) -> list[Panel]:
    """Render refine preview comments as scoped panel blocks."""
    total = len(comments)
    panels: list[Panel] = []
    for index, comment in enumerate(comments, 1):
        body = comment.strip() if comment.strip() else "[dim](empty comment)[/dim]"
        panels.append(Panel(body, title=f"Comment {index}/{total}", border_style="cyan"))
    return panels


@beartype
def _build_refine_preview_comment_empty_panel() -> Panel:
    """Render explicit empty-state panel when no comments are found."""
    return Panel("[dim](no comments found)[/dim]", title="Comments", border_style="dim")


@beartype
def _build_daily_interactive_comment_panels(
    comments: list[str],
    *,
    show_all_provided_comments: bool,
    total_comments: int,
) -> list[Panel]:
    """Render daily interactive comments with refine-like scoped panels."""
    if not comments:
        return [_build_refine_preview_comment_empty_panel()]

    if show_all_provided_comments:
        panels = _build_refine_preview_comment_panels(comments)
        omitted_count = max(total_comments - len(comments), 0)
        if omitted_count > 0:
            panels.append(
                Panel(
                    f"[dim]{omitted_count} additional comment(s) omitted by comment window.[/dim]\n"
                    "[dim]Hint: increase --first-comments/--last-comments or use export options for full history.[/dim]",
                    title="Comment Window",
                    border_style="dim",
                )
            )
        return panels

    latest = comments[-1].strip() if comments[-1].strip() else "[dim](empty comment)[/dim]"
    panels: list[Panel] = [Panel(latest, title="Latest Comment", border_style="cyan")]
    hidden_count = max(total_comments - 1, 0)
    if hidden_count > 0:
        panels.append(
            Panel(
                f"[dim]{hidden_count} older comment(s) hidden in interactive view.[/dim]\n"
                "[dim]Hint: use `specfact backlog refine --export-to-tmp` or "
                "`specfact backlog daily --copilot-export <path> --comments` for full history.[/dim]",
                title="Comments Hint",
                border_style="dim",
            )
        )
    return panels


@beartype
def _build_daily_navigation_choices(*, can_post_comment: bool) -> list[str]:
    """Build interactive daily navigation choices."""
    choices = ["Next story", "Previous story"]
    if can_post_comment:
        choices.append("Post standup update")
    choices.extend(["Back to list", "Exit"])
    return choices


@beartype
def _build_interactive_post_body(yesterday: str | None, today: str | None, blockers: str | None) -> str | None:
    """Build standup comment body from interactive inputs."""
    y = (yesterday or "").strip()
    t = (today or "").strip()
    b = (blockers or "").strip()
    if not y and not t and not b:
        return None
    return _format_standup_comment(y, t, b)


def _collect_comment_annotations(
    connection: _AdapterContext,
    items: list[BacklogItem],
    *,
    first_comments: int | None = None,
    last_comments: int | None = None,
    progress_callback: Callable[[int, int, BacklogItem], None] | None = None,
) -> dict[str, list[str]]:
    """
    Collect comment annotations for backlog items when the adapter supports get_comments().

    Returns a mapping of item ID -> list of comment strings. Returns empty dict if not supported.
    """
    comments_by_item_id: dict[str, list[str]] = {}
    try:
        adapter_kwargs = _build_adapter_kwargs(connection)
        registry = AdapterRegistry()
        adapter_instance = registry.get_adapter(connection.adapter, **adapter_kwargs)
        if not isinstance(adapter_instance, BacklogAdapter):
            return comments_by_item_id
        get_comments_fn = getattr(adapter_instance, "get_comments", None)
        if not callable(get_comments_fn):
            return comments_by_item_id
        total_items = len(items)
        for index, item in enumerate(items, 1):
            if progress_callback is not None:
                progress_callback(index, total_items, item)
            with contextlib.suppress(Exception):
                raw = get_comments_fn(item)
                comments = list(raw) if isinstance(raw, list) else []
                comments_by_item_id[item.id] = _apply_comment_window(
                    comments,
                    first_comments=first_comments,
                    last_comments=last_comments,
                )
    except Exception:
        return comments_by_item_id
    return comments_by_item_id


def _item_assignee_text(item: BacklogItem) -> str:
    return ", ".join(item.assignees) if item.assignees else "—"


def _item_updated_text(item: BacklogItem) -> str:
    return item.updated_at.strftime("%Y-%m-%d %H:%M") if hasattr(item.updated_at, "strftime") else str(item.updated_at)


def _truncated_body_text(body: str, *, normalize_markdown: bool) -> str:
    text = _normalize_markdown_text(body.strip()) if normalize_markdown else body.strip()
    if len(text) <= _SUMMARIZE_BODY_TRUNCATE:
        return text
    return text[:_SUMMARIZE_BODY_TRUNCATE] + "\n..."


def _append_item_metrics(lines: list[str], item: BacklogItem, *, include_value_score: bool) -> None:
    if item.story_points is not None:
        lines.append(f"- **Story points:** {item.story_points}")
    if item.priority is not None:
        lines.append(f"- **Priority:** {item.priority}")
    if not include_value_score:
        return
    score = _compute_value_score(item)
    if score is not None:
        lines.append(f"- **Value score:** {score:.2f}")


def _append_item_progress(lines: list[str], item: BacklogItem) -> None:
    yesterday, today, blockers = _parse_standup_from_body(item.body_markdown or "")
    if yesterday or today:
        lines.append(f"- **Progress:** Yesterday: {yesterday or '—'}; Today: {today or '—'}")
    if blockers:
        lines.append(f"- **Blockers:** {blockers}")


def _append_comment_lines(lines: list[str], comments: list[str], *, prefix: str) -> None:
    if not comments:
        return
    lines.append("- **Comments (annotations):**")
    for comment in comments:
        lines.append(f"{prefix}{_normalize_markdown_text(str(comment))}")


def _append_copilot_item_description(lines: list[str], item: BacklogItem) -> None:
    body = (item.body_markdown or "").strip()
    if not body:
        return
    lines.append("- **Description:**")
    for line in _truncated_body_text(body, normalize_markdown=False).splitlines():
        lines.append(f"  {line}" if line else "  ")


def _append_summarize_item_description(lines: list[str], item: BacklogItem) -> None:
    body = (item.body_markdown or "").strip()
    if not body:
        return
    lines.append("- **Description:**")
    lines.append(_truncated_body_text(body, normalize_markdown=True))
    lines.append("")


@beartype
def _build_copilot_export_content(
    items: list[BacklogItem],
    include_value_score: bool = False,
    include_comments: bool = False,
    comments_by_item_id: dict[str, list[str]] | None = None,
) -> str:
    """
    Build Markdown content for Copilot export: one section per item.

    Per item: ID, title, status, assignees, last updated, progress summary (standup fields),
    blockers, optional value score, and optionally description/comments when enabled.
    """
    lines: list[str] = ["# Daily standup – Copilot export", ""]
    comments_map = comments_by_item_id or {}
    for item in items:
        lines.append(f"## {item.id} - {item.title}")
        lines.append("")
        lines.append(f"- **Status:** {item.state}")
        lines.append(f"- **Assignees:** {_item_assignee_text(item)}")
        lines.append(f"- **Last updated:** {_item_updated_text(item)}")
        if include_comments:
            _append_copilot_item_description(lines, item)
        _append_item_progress(lines, item)
        if include_comments:
            _append_comment_lines(lines, comments_map.get(item.id, []), prefix="  - ")
        _append_item_metrics(lines, item, include_value_score=include_value_score)
        lines.append("")
    return "\n".join(lines).strip()


_SUMMARIZE_BODY_TRUNCATE = 1200


@beartype
def _build_summarize_prompt_content(
    items: list[BacklogItem],
    filter_context: dict[str, Any],
    include_value_score: bool = False,
    comments_by_item_id: dict[str, list[str]] | None = None,
    include_comments: bool = False,
) -> str:
    """
    Build prompt content for standup summary: instruction + filter context + per-item data.

    When include_comments is True, includes body (description) and annotations (comments) per item
    so an LLM can produce a meaningful summary. When False, only metadata (id, title, status,
    assignees, last updated) is included to avoid leaking sensitive or large context.
    For use with slash command (e.g. specfact.daily) or copy-paste to Copilot.
    """
    lines: list[str] = [
        "--- BEGIN STANDUP PROMPT ---",
        "Generate a concise daily standup summary from the following data.",
    ]
    if include_comments:
        lines.append(
            "Include: current focus, blockers, and pending items. Use each item's description and comments for context. Keep it short and actionable."
        )
    else:
        lines.append("Include: current focus and pending items from the metadata below. Keep it short and actionable.")
    lines.append("")
    lines.append("## Filter context")
    lines.append(f"- Adapter: {filter_context.get('adapter', '—')}")
    lines.append(f"- State: {filter_context.get('state', '—')}")
    lines.append(f"- Sprint: {filter_context.get('sprint', '—')}")
    lines.append(f"- Assignee: {filter_context.get('assignee', '—')}")
    lines.append(f"- Limit: {filter_context.get('limit', '—')}")
    lines.append("")
    data_header = "Standup data (with description and comments)" if include_comments else "Standup data (metadata only)"
    lines.append(f"## {data_header}")
    lines.append("")
    comments_map = comments_by_item_id or {}
    for item in items:
        lines.append(f"## {item.id} - {item.title}")
        lines.append("")
        lines.append(f"- **Status:** {item.state}")
        lines.append(f"- **Assignees:** {_item_assignee_text(item)}")
        lines.append(f"- **Last updated:** {_item_updated_text(item)}")
        if include_comments:
            _append_summarize_item_description(lines, item)
            _append_item_progress(lines, item)
            _append_comment_lines(lines, comments_map.get(item.id, []), prefix="  - ")
        _append_item_metrics(lines, item, include_value_score=include_value_score)
        lines.append("")
    lines.append("--- END STANDUP PROMPT ---")
    return "\n".join(lines).strip()


_HTML_TAG_RE = re.compile(r"<[A-Za-z/][^>]*>")

# Maximum input length to prevent ReDoS on regex processing (50KB)
_MAX_INPUT_LENGTH = 50 * 1024


@beartype
def _normalize_markdown_text(text: str) -> str:
    """
    Normalize provider-specific markup (HTML, entities) to Markdown-friendly text.

    This is intentionally conservative: plain Markdown is left as-is, while common HTML constructs from
    ADO-style bodies and comments are converted to readable Markdown and stripped of tags/entities.

    Includes safeguards against ReDoS (input length guard) and graceful fallback on errors.
    """
    if not text:
        return ""

    # ReDoS guard: truncate very long inputs before regex processing
    if len(text) > _MAX_INPUT_LENGTH:
        text = text[:_MAX_INPUT_LENGTH] + "\n... [truncated due to length]"

    # Fast path: if no obvious HTML markers, return as-is.
    if "<" not in text and "&" not in text:
        return text

    from html import unescape

    try:
        # Unescape HTML entities first so we can treat content uniformly.
        value = unescape(text)

        # Replace common block/linebreak tags with newlines before stripping other tags.
        # Handle several variants to cover typical ADO HTML.
        value = re.sub(r"<\s*br\s*/?\s*>", "\n", value, flags=re.IGNORECASE)
        value = re.sub(r"</\s*p\s*>", "\n\n", value, flags=re.IGNORECASE)
        value = re.sub(r"<\s*p[^>]*>", "", value, flags=re.IGNORECASE)

        # Turn list items into markdown bullets.
        value = re.sub(r"<\s*li[^>]*>", "- ", value, flags=re.IGNORECASE)
        value = re.sub(r"</\s*li\s*>", "\n", value, flags=re.IGNORECASE)
        value = re.sub(r"<\s*ul[^>]*>", "", value, flags=re.IGNORECASE)
        value = re.sub(r"</\s*ul\s*>", "\n", value, flags=re.IGNORECASE)
        value = re.sub(r"<\s*ol[^>]*>", "", value, flags=re.IGNORECASE)
        value = re.sub(r"</\s*ol\s*>", "\n", value, flags=re.IGNORECASE)

        # Drop any remaining tags conservatively.
        value = _HTML_TAG_RE.sub("", value)

        # Normalize whitespace: collapse excessive blank lines but keep paragraph structure.
        # First, normalize Windows-style newlines.
        value = value.replace("\r\n", "\n").replace("\r", "\n")
        # Collapse 3+ blank lines into 2.
        value = re.sub(r"\n{3,}", "\n\n", value)
        # Strip leading/trailing whitespace on each line.
        lines = [line.rstrip() for line in value.split("\n")]
        return "\n".join(lines).strip()
    except Exception:
        # Fallback: strip tags and unescape entities without complex processing
        # This handles malformed HTML or edge cases that break the main algorithm
        value = unescape(str(text))
        value = _HTML_TAG_RE.sub("", value)
        return value.strip()


@beartype
def _build_refine_export_content(
    adapter: str,
    items: list[BacklogItem],
    comments_by_item_id: dict[str, list[str]] | None = None,
    template_guidance_by_item_id: dict[str, dict[str, Any]] | None = None,
) -> str:
    """Build markdown export content for `backlog refine --export-to-tmp`."""
    sections = [_refine_export_header(adapter, item_count=len(items))]
    comments_map = comments_by_item_id or {}
    template_map = template_guidance_by_item_id or {}
    sections.extend(
        _refine_export_item_section(
            idx,
            item,
            comments=comments_map.get(item.id, []),
            template=item_template,
        )
        for idx, item in enumerate(items, 1)
        for item_template in [template_map.get(item.id, {})]
    )
    return "".join(sections).rstrip()


def _refine_export_header(adapter: str, *, item_count: int) -> str:
    return (
        "# SpecFact Backlog Refinement Export\n\n"
        f"**Export Date**: {datetime.now().isoformat()}\n"
        f"**Adapter**: {adapter}\n"
        f"**Items**: {item_count}\n\n"
        "## Copilot Instructions\n\n"
        "Use each `## Item N:` section below as refinement input. Preserve scope/intent and return improved markdown "
        "per item.\n\n"
        "For import readiness: the refined artifact (`--import-from-tmp`) must not include this instruction block; "
        "it should contain only the `## Item N:` sections and refined fields.\n\n"
        "Import contract: **ID** is mandatory in every item block and must remain unchanged from export; "
        "ID lookup drives update mapping during `--import-from-tmp`.\n\n"
        f"{_refine_export_rules()}"
        f"{_refine_export_scaffold()}"
        "---\n\n"
    )


def _refine_export_rules() -> str:
    rules = [
        "Preserve all original requirements, scope, and technical details",
        "Do NOT add new features or change the scope",
        "Do NOT summarize, shorten, or drop details; keep full detail and intent",
        "Transform content to match the target template structure",
        "Story text must be explicit, specific, and unambiguous (SMART-style)",
        "If required information is missing, use a Markdown checkbox: `- [ ] describe what's needed`",
        "If information is conflicting or ambiguous, add a `[NOTES]` section at the end explaining ambiguity",
        "Use markdown headings for sections (`## Section Name`)",
        "Include story points, business value, priority, and work item type when available",
        "For high-complexity stories, suggest splitting when appropriate",
        "Follow provider-aware formatting guidance listed per item",
    ]
    lines = ["**Refinement Rules (same as interactive mode):**"]
    lines.extend(f"{index}. {rule}" for index, rule in enumerate(rules, 1))
    return "\n".join(lines) + "\n\n"


def _refine_export_scaffold() -> str:
    return (
        "**Template Execution Rules (mandatory):**\n"
        "1. Use `Target Template`, `Required Sections`, and `Optional Sections` as the exact structure contract\n"
        "2. Keep all original requirements and constraints; do not silently drop details\n"
        "3. Improve specificity and testability; avoid generic summaries that lose intent\n\n"
        "**Expected Output Scaffold (ordered):**\n"
        "```markdown\n"
        "## Work Item Properties / Metadata\n"
        "- Story Points: <number, omit line if unknown>\n"
        "- Business Value: <number, omit line if unknown>\n"
        "- Priority: <number, omit line if unknown>\n"
        "- Work Item Type: <type, omit line if unknown>\n\n"
        "## Description\n"
        "<main story narrative/body only>\n\n"
        "## Acceptance Criteria\n"
        "- [ ] <criterion>\n\n"
        "## Notes\n"
        "<optional; include only for ambiguity/risk/dependency context>\n"
        "```\n\n"
        "Omit unknown metadata fields and never emit placeholders such as "
        "`(unspecified)`, `no info provided`, or `provide area path`.\n\n"
    )


def _refine_export_item_section(
    idx: int,
    item: BacklogItem,
    *,
    comments: list[str],
    template: dict[str, Any],
) -> str:
    lines = [
        f"## Item {idx}: {item.title}",
        "",
        f"**ID**: {item.id}",
        f"**URL**: {item.url}",
    ]
    if item.canonical_url:
        lines.append(f"**Canonical URL**: {item.canonical_url}")
    lines.extend([f"**State**: {item.state}", f"**Provider**: {item.provider}"])
    lines.extend(_refine_export_template_lines(template))
    lines.extend(_refine_export_metric_lines(item))
    if item.acceptance_criteria:
        lines.extend(["", "**Acceptance Criteria**:", item.acceptance_criteria])
    if comments:
        lines.extend(["", "**Comments (annotations):**", *(f"- {comment}" for comment in comments)])
    lines.extend(["", "**Body**:", "```markdown", str(item.body_markdown or ""), "```", "", "---", ""])
    return "\n".join(lines) + "\n"


def _refine_export_template_lines(template: dict[str, Any]) -> list[str]:
    if not template:
        return []
    lines = [
        "",
        f"**Target Template**: {template.get('name', 'N/A')}",
        f"**Template ID**: {template.get('template_id', 'N/A')}",
    ]
    template_desc = str(template.get("description", "")).strip()
    if template_desc:
        lines.append(f"**Template Description**: {template_desc}")
    lines.extend(_refine_export_section_list("Required Sections", template.get("required_sections", [])))
    lines.extend(_refine_export_section_list("Optional Sections", template.get("optional_sections", [])))
    lines.extend(
        [
            "",
            "**Provider-aware formatting**:",
            "- GitHub: Use markdown headings in body (`## Section Name`).",
            "- ADO: Keep metadata (Story Points/Business Value/Priority/Work Item Type) in `**Metrics**`; "
            "do not add those as body headings. Keep description narrative in body markdown.",
        ]
    )
    return lines


def _refine_export_section_list(title: str, sections: object) -> list[str]:
    lines = ["", f"**{title}**:"]
    if isinstance(sections, list) and sections:
        lines.extend(f"- {section}" for section in sections)
    else:
        lines.append("- None")
    return lines


def _refine_export_metric_lines(item: BacklogItem) -> list[str]:
    if item.story_points is None and item.business_value is None and item.priority is None:
        return []
    lines = ["", "**Metrics**:"]
    metric_values = (
        ("Story Points", item.story_points),
        ("Business Value", item.business_value),
        ("Priority", f"{item.priority} (1=highest)" if item.priority is not None else None),
        ("Value Points (SAFe)", item.value_points),
        ("Work Item Type", item.work_item_type),
    )
    lines.extend(f"- {label}: {value}" for label, value in metric_values if value is not None)
    return lines


def _collect_refine_template_tokens(item: BacklogItem, normalized_adapter: str | None) -> set[str]:
    normalized_tokens: set[str] = set()
    work_item_type = (item.work_item_type or "").strip()
    if work_item_type:
        normalized_tokens.add(work_item_type.lower())
    if normalized_adapter == "ado":
        provider_fields = item.provider_fields.get("fields")
        if isinstance(provider_fields, dict):
            provider_type = str(provider_fields.get("System.WorkItemType") or "").strip().lower()
            if provider_type:
                normalized_tokens.add(provider_type)
    elif normalized_adapter == "github":
        provider_issue_type = item.provider_fields.get("issue_type")
        if isinstance(provider_issue_type, str) and provider_issue_type.strip():
            normalized_tokens.add(provider_issue_type.strip().lower())
        normalized_tokens.update(tag.strip().lower() for tag in item.tags if isinstance(tag, str) and tag.strip())
    return normalized_tokens


def _resolve_user_story_target_template(
    registry: TemplateRegistry,
    *,
    normalized_tokens: set[str],
    normalized_framework: str | None,
) -> BacklogTemplate | None:
    if not normalized_tokens.intersection({"user story", "story", "product backlog item", "pbi"}):
        return None
    preferred_ids = (
        ["scrum_user_story_v1", "user_story_v1"]
        if normalized_framework == "scrum"
        else ["user_story_v1", "scrum_user_story_v1"]
    )
    for preferred_id in preferred_ids:
        preferred = registry.get_template(preferred_id)
        if preferred is not None:
            return preferred
    return None


@beartype
def _resolve_target_template_for_refine_item(
    item: BacklogItem,
    *,
    detector: TemplateDetector,
    registry: TemplateRegistry,
    template_id: str | None,
    normalized_adapter: str | None,
    normalized_framework: str | None,
    normalized_persona: str | None,
) -> BacklogTemplate | None:
    """Resolve target template for an item using the same precedence as refine flows."""
    if template_id:
        direct = registry.get_template(template_id)
        if direct is not None:
            return direct

    if normalized_adapter in {"ado", "github"}:
        story_target = _resolve_user_story_target_template(
            registry,
            normalized_tokens=_collect_refine_template_tokens(item, normalized_adapter),
            normalized_framework=normalized_framework,
        )
        if story_target is not None:
            return story_target

    detection_result = detector.detect_template(
        item,
        provider=normalized_adapter,
        framework=normalized_framework,
        persona=normalized_persona,
    )
    if detection_result.template_id:
        detected = registry.get_template(detection_result.template_id)
        if detected is not None:
            return detected
    resolved = registry.resolve_template(
        provider=normalized_adapter,
        framework=normalized_framework,
        persona=normalized_persona,
    )
    if resolved is not None:
        return resolved
    templates = registry.list_templates(scope="corporate")
    return templates[0] if templates else None


def _load_questionary_for_daily() -> Any:
    try:
        import questionary  # type: ignore[reportMissingImports]
    except ImportError:
        console.print(
            "[red]Interactive mode requires the 'questionary' package. Install with: pip install questionary[/red]"
        )
        raise typer.Exit(1) from None
    return questionary


def _create_daily_interactive_session(
    items: list[BacklogItem],
    suggest_next: bool,
    connection: _AdapterContext,
    first_comments: int | None,
    last_comments: int | None,
) -> _DailyInteractiveSession:
    questionary = _load_questionary_for_daily()
    adapter_kwargs = _build_adapter_kwargs(connection)
    registry = AdapterRegistry()
    adapter_instance = registry.get_adapter(connection.adapter, **adapter_kwargs)
    get_comments_fn = getattr(adapter_instance, "get_comments", lambda _: [])
    return _DailyInteractiveSession(
        items=items,
        questionary=questionary,
        adapter_instance=adapter_instance,
        get_comments_fn=get_comments_fn,
        suggest_next=suggest_next,
        first_comments=first_comments,
        last_comments=last_comments,
    )


def _daily_interactive_choices(items: list[BacklogItem]) -> list[str]:
    choices = [
        f"{item.id} - {item.title[:50]}{'...' if len(item.title) > 50 else ''} [{item.state}] ({', '.join(item.assignees) or '—'})"
        for item in items
    ]
    choices.append("Exit")
    return choices


def _load_daily_item_comments(session: _DailyInteractiveSession, item: BacklogItem) -> tuple[list[str], int]:
    if not callable(session.get_comments_fn):
        return [], 0
    with contextlib.suppress(Exception):
        raw = session.get_comments_fn(item)
        raw_comments = list(raw) if isinstance(raw, list) else []
        comments = _apply_comment_window(
            raw_comments,
            first_comments=session.first_comments,
            last_comments=session.last_comments,
        )
        return comments, len(raw_comments)
    return [], 0


def _print_daily_interactive_detail(
    session: _DailyInteractiveSession,
    item: BacklogItem,
    comments: list[str],
    total_comments: int,
) -> None:
    explicit_comment_window = session.first_comments is not None or session.last_comments is not None
    detail = _format_daily_item_detail(
        item,
        comments,
        show_all_provided_comments=explicit_comment_window,
        total_comments=total_comments,
    )
    console.print(Panel(detail, title=f"Story: {item.id}", border_style="cyan"))
    console.print("\n[bold]Comments:[/bold]")
    for panel in _build_daily_interactive_comment_panels(
        comments,
        show_all_provided_comments=explicit_comment_window,
        total_comments=total_comments,
    ):
        console.print(panel)


def _suggest_daily_next_item(session: _DailyInteractiveSession) -> None:
    if not session.suggest_next or len(session.items) <= 1:
        return
    scored = [
        (score, item)
        for item in session.items
        if (not item.assignees or item.story_points is not None)
        for score in [_compute_value_score(item)]
        if score is not None
    ]
    if not scored:
        return
    best_score, best = max(scored, key=lambda entry: entry[0])
    console.print(f"[dim]Suggested next (value score {best_score:.2f}): {best.id} - {best.title}[/dim]")


def _post_interactive_standup_update(session: _DailyInteractiveSession, item: BacklogItem) -> None:
    y = session.questionary.text("Yesterday (optional):").ask()
    t = session.questionary.text("Today (optional):").ask()
    b = session.questionary.text("Blockers (optional):").ask()
    body = _build_interactive_post_body(y, t, b)
    if body is None:
        console.print("[yellow]No standup text provided; nothing posted.[/yellow]")
        return
    if isinstance(session.adapter_instance, BacklogAdapter) and _post_standup_to_item(
        session.adapter_instance, item, body
    ):
        console.print(f"[green]✓ Standup comment posted to story {item.id}: {item.url}[/green]")
        return
    console.print("[red]Failed to post standup comment for selected story.[/red]")


def _run_daily_interactive_item_loop(session: _DailyInteractiveSession, start_idx: int) -> bool:
    current_idx = start_idx
    total_items = len(session.items)
    while True:
        item = session.items[current_idx]
        comments, total_comments = _load_daily_item_comments(session, item)
        _print_daily_interactive_detail(session, item, comments, total_comments)
        _suggest_daily_next_item(session)

        can_post_comment = isinstance(session.adapter_instance, BacklogAdapter) and _post_standup_comment_supported(
            session.adapter_instance, item
        )
        nav_choices = _build_daily_navigation_choices(can_post_comment=can_post_comment)
        nav = session.questionary.select("Navigation", choices=nav_choices).ask()
        if nav is None or nav == "Exit":
            return False
        if nav == "Post standup update":
            _post_interactive_standup_update(session, item)
            continue
        if nav == "Back to list":
            return True
        if nav == "Next story":
            current_idx = (current_idx + 1) % total_items
        elif nav == "Previous story":
            current_idx = (current_idx - 1) % total_items


def _run_interactive_daily(
    items: list[BacklogItem],
    suggest_next: bool,
    connection: _AdapterContext,
    first_comments: int | None = None,
    last_comments: int | None = None,
) -> None:
    """Run interactive step-by-step review: selection, detail view, and navigation."""
    session = _create_daily_interactive_session(
        items,
        suggest_next=suggest_next,
        connection=connection,
        first_comments=first_comments,
        last_comments=last_comments,
    )
    choices = _daily_interactive_choices(items)
    total_items = len(items)

    while True:
        selected = session.questionary.select("Select a story to review (or Exit)", choices=choices).ask()
        if selected is None or selected == "Exit":
            return
        try:
            idx = choices.index(selected)
        except ValueError:
            return
        if idx >= total_items:
            return
        if not _run_daily_interactive_item_loop(session, idx):
            return


def _extract_openspec_change_id(body: str) -> str | None:
    """
    Extract OpenSpec change proposal ID from issue body.

    Looks for patterns like:
    - *OpenSpec Change Proposal: `id`*
    - OpenSpec Change Proposal: `id`
    - OpenSpec.*proposal: `id`

    Args:
        body: Issue body text

    Returns:
        Change proposal ID if found, None otherwise
    """
    import re

    openspec_patterns = [
        r"OpenSpec Change Proposal[:\s]+`?([a-z0-9-]+)`?",
        r"\*OpenSpec Change Proposal:\s*`([a-z0-9-]+)`",
        r"OpenSpec.*proposal[:\s]+`?([a-z0-9-]+)`?",
    ]
    for pattern in openspec_patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _read_git_origin_url() -> str | None:
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return None
    if result.returncode != 0 or not result.stdout or not result.stdout.strip():
        return None
    return result.stdout.strip()


def _split_git_remote_path(url: str) -> list[str]:
    path = url.split(":", 1)[-1].strip() if url.startswith("git@") else urlparse(url).path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return path.split("/")


def _parse_github_owner_repo(url: str) -> tuple[str | None, str | None]:
    segments = _split_git_remote_path(url)
    if len(segments) < 2:
        return (None, None)
    if url.startswith("git@") and "github" not in url.lower():
        return (None, None)
    if not url.startswith("git@"):
        parsed = urlparse(url)
        if not parsed.hostname or "github" not in parsed.hostname.lower():
            return (None, None)
    return (segments[-2] or None, segments[-1] or None)


def _infer_github_repo_from_cwd() -> tuple[str | None, str | None]:
    """
    Infer repo_owner and repo_name from git remote origin when run inside a GitHub clone.
    Returns (owner, repo) or (None, None) if not a GitHub remote or git unavailable.
    """
    url = _read_git_origin_url()
    if not url:
        return (None, None)
    return _parse_github_owner_repo(url)


def _infer_ado_context_from_cwd() -> tuple[str | None, str | None]:
    """
    Infer org and project from git remote origin when run inside an Azure DevOps clone.
    Returns (org, project) or (None, None) if not an ADO remote or git unavailable.
    Supports:
    - HTTPS: https://dev.azure.com/org/project/_git/repo
    - SSH (keys): git@ssh.dev.azure.com:v3/<org>/<project>/<repo>
    - SSH (other): <user>@dev.azure.com:v3/<org>/<project>/<repo> (no ssh. subdomain)
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0 or not result.stdout or not result.stdout.strip():
            return (None, None)
        url = result.stdout.strip()
        org, project = None, None
        if "dev.azure.com" not in url.lower():
            return (None, None)
        if ":" in url and "v3/" in url:
            idx = url.find("v3/")
            if idx != -1:
                part = url[idx + 3 :].strip()
                segments = part.split("/")
                if len(segments) >= 2:
                    org, project = segments[0], segments[1]
        else:
            parsed = urlparse(url)
            if parsed.path:
                path = parsed.path.strip("/")
                segments = path.split("/")
                if len(segments) >= 2:
                    org, project = segments[0], segments[1]
        return (org or None, project or None)
    except Exception:
        return (None, None)


def _resolve_github_adapter_kwargs(cfg: dict[str, Any], connection: _AdapterContext) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    owner = (
        connection.repo_owner
        or os.environ.get("SPECFACT_GITHUB_REPO_OWNER")
        or (cfg.get("github") or {}).get("repo_owner")
    )
    name = (
        connection.repo_name
        or os.environ.get("SPECFACT_GITHUB_REPO_NAME")
        or (cfg.get("github") or {}).get("repo_name")
    )
    if not owner or not name:
        inferred_owner, inferred_name = _infer_github_repo_from_cwd()
        owner = owner or inferred_owner
        name = name or inferred_name
    if owner:
        kwargs["repo_owner"] = owner
    if name:
        kwargs["repo_name"] = name
    if connection.github_token:
        kwargs["api_token"] = connection.github_token
    return kwargs


def _resolve_ado_identifiers(
    cfg: dict[str, Any], connection: _AdapterContext
) -> tuple[str | None, str | None, str | None]:
    org = connection.ado_org or os.environ.get("SPECFACT_ADO_ORG") or (cfg.get("ado") or {}).get("org")
    project = connection.ado_project or os.environ.get("SPECFACT_ADO_PROJECT") or (cfg.get("ado") or {}).get("project")
    team = connection.ado_team or os.environ.get("SPECFACT_ADO_TEAM") or (cfg.get("ado") or {}).get("team")
    if org and project:
        return org, project, team
    inferred_org, inferred_project = _infer_ado_context_from_cwd()
    return org or inferred_org, project or inferred_project, team


def _set_adapter_kwarg(kwargs: dict[str, Any], key: str, value: str | None) -> None:
    if value:
        kwargs[key] = value


def _resolve_ado_adapter_kwargs(cfg: dict[str, Any], connection: _AdapterContext) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    org, project, team = _resolve_ado_identifiers(cfg, connection)
    _set_adapter_kwarg(kwargs, "org", org)
    _set_adapter_kwarg(kwargs, "project", project)
    _set_adapter_kwarg(kwargs, "team", team)
    _set_adapter_kwarg(kwargs, "api_token", connection.ado_token)
    return kwargs


def _build_adapter_kwargs(connection: _AdapterContext) -> dict[str, Any]:
    """
    Build adapter kwargs from CLI args, then env, then .specfact/backlog.yaml.
    Resolution order: explicit arg > env (SPECFACT_GITHUB_REPO_OWNER, etc.) > config.
    Tokens are never read from config; only from explicit args (env handled by caller).
    """
    cfg = _load_backlog_config()
    if connection.adapter.lower() == "github":
        return _resolve_github_adapter_kwargs(cfg, connection)
    if connection.adapter.lower() == "ado":
        return _resolve_ado_adapter_kwargs(cfg, connection)
    return {}


def _extract_body_from_block(block: str) -> str:
    """
    Extract **Body** content from a refined export block, handling nested fenced code.

    The body is wrapped in ```markdown ... ```. If the body itself contains fenced
    code blocks (e.g. ```python ... ```), the closing fence is matched by tracking
    depth: a line that is exactly ``` closes the current fence (body or inner).
    """
    start_marker = "**Body**:"
    fence_open = "```markdown"
    if start_marker not in block or fence_open not in block:
        return ""
    idx = block.find(start_marker)
    rest = block[idx + len(start_marker) :].lstrip()
    if not rest.startswith("```"):
        return ""
    if not rest.startswith(fence_open + "\n") and not rest.startswith(fence_open + "\r\n"):
        return ""
    after_open = rest[len(fence_open) :].lstrip("\n\r")
    if not after_open:
        return ""
    lines = after_open.split("\n")
    body_lines: list[str] = []
    depth = 1
    for line in lines:
        stripped = line.rstrip()
        if stripped == "```":
            if depth == 1:
                break
            depth -= 1
            body_lines.append(line)
        elif stripped.startswith("```") and stripped != "```":
            depth += 1
            body_lines.append(line)
        else:
            body_lines.append(line)
    return "\n".join(body_lines).strip()


def _parse_refined_export_markdown(content: str) -> dict[str, dict[str, Any]]:
    """
    Parse refined export markdown (same format as --export-to-tmp) into id -> fields.

    Splits by ## Item blocks, extracts **ID**, **Body** (from ```markdown ... ```),
    **Acceptance Criteria**, and optionally title and **Metrics** (story_points,
    business_value, priority). Body extraction is fence-aware so bodies containing
    nested code blocks are parsed correctly. Returns a dict mapping item id to
    parsed fields (body_markdown, acceptance_criteria, title?, story_points?,
    business_value?, priority?).
    """
    result: dict[str, dict[str, Any]] = {}
    item_block_pattern = re.compile(
        r"(?:^|\n)## Item \d+:\s*(?P<title>[^\n]*)\n(?P<body>.*?)(?=(?:\n## Item \d+:)|\Z)",
        re.DOTALL,
    )
    for match in item_block_pattern.finditer(content):
        block_title = match.group("title").strip()
        block = match.group("body").strip()
        if not block or "**ID**:" not in block:
            continue
        id_match = re.search(r"\*\*ID\*\*:\s*(.+?)(?:\n|$)", block)
        if not id_match:
            continue
        item_id = id_match.group(1).strip()
        fields: dict[str, Any] = {}

        fields["body_markdown"] = _extract_body_from_block(block)

        ac_match = re.search(r"\*\*Acceptance Criteria\*\*:\s*\n(.*?)(?=\n\*\*|\n---|\Z)", block, re.DOTALL)
        if ac_match:
            fields["acceptance_criteria"] = ac_match.group(1).strip() or None
        else:
            fields["acceptance_criteria"] = None

        if block_title:
            fields["title"] = block_title

        if "Story Points:" in block:
            sp_match = re.search(r"Story Points:\s*(\d+)", block)
            if sp_match:
                fields["story_points"] = int(sp_match.group(1))
        if "Business Value:" in block:
            bv_match = re.search(r"Business Value:\s*(\d+)", block)
            if bv_match:
                fields["business_value"] = int(bv_match.group(1))
        if "Priority:" in block:
            pri_match = re.search(r"Priority:\s*(\d+)", block)
            if pri_match:
                fields["priority"] = int(pri_match.group(1))

        result[item_id] = fields
    return result


_CONTENT_LOSS_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "into",
    "your",
    "you",
    "are",
    "was",
    "were",
    "will",
    "shall",
    "must",
    "can",
    "should",
    "have",
    "has",
    "had",
    "not",
    "but",
    "all",
    "any",
    "our",
    "out",
    "use",
    "using",
    "used",
    "need",
    "needs",
    "item",
    "story",
    "description",
    "acceptance",
    "criteria",
    "work",
    "points",
    "value",
    "priority",
}

_REFINEMENT_LABEL_ALIASES = {
    "description": "description",
    "acceptance criteria": "acceptance_criteria",
    "story points": "story_points",
    "business value": "business_value",
    "priority": "priority",
    "work item type": "work_item_type",
    "notes": "notes",
    "dependencies": "dependencies",
    "area path": "area_path",
    "iteration path": "iteration_path",
    "provider": "provider",
}
_REFINEMENT_HEADING_BOUNDARIES = {
    *_REFINEMENT_LABEL_ALIASES.keys(),
    "work item properties / metadata",
    "work item properties",
    "metadata",
}
_REFINEMENT_LABEL_PATTERN = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\*\*)?([A-Za-z][A-Za-z0-9 ()/_-]*?)(?:\*\*)?\s*:\s*(.*)\s*$"
)


@beartype
@require(lambda text: isinstance(text, str), "text must be string")
@ensure(lambda result: isinstance(result, set), "Must return set")
def _extract_content_terms(text: str) -> set[str]:
    """Extract meaningful lowercase terms from narrative text for loss checks."""
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}", text.lower())
    return {token for token in tokens if token not in _CONTENT_LOSS_STOPWORDS}


@beartype
@require(lambda original: isinstance(original, str), "original must be string")
@require(lambda refined: isinstance(refined, str), "refined must be string")
@ensure(lambda result: isinstance(result, tuple) and len(result) == 2, "Must return (bool, str)")
def _detect_significant_content_loss(original: str, refined: str) -> tuple[bool, str]:
    """
    Detect likely silent content loss (summarization/truncation) in refined body.

    Returns (has_loss, reason). Conservative thresholds aim to catch substantial
    detail drops while allowing normal structural cleanup.
    """
    original_text = original.strip()
    refined_text = refined.strip()
    if not original_text:
        return (False, "")
    if not refined_text:
        return (True, "refined description is empty")

    original_len = len(original_text)
    refined_len = len(refined_text)
    length_ratio = refined_len / max(1, original_len)

    original_terms = _extract_content_terms(original_text)
    if not original_terms:
        # If original has no meaningful terms, rely only on empty/non-empty check above.
        return (False, "")

    refined_terms = _extract_content_terms(refined_text)
    retained_terms = len(original_terms.intersection(refined_terms))
    retention_ratio = retained_terms / len(original_terms)

    # Strong signal of summarization/loss: body is much shorter and lost many terms.
    if length_ratio < 0.65 and retention_ratio < 0.60:
        reason = (
            f"length ratio {length_ratio:.2f} and content-term retention {retention_ratio:.2f} "
            "(likely summarized/truncated)"
        )
        return (True, reason)

    # Extremely aggressive shrink, even if wording changed heavily.
    if length_ratio < 0.45:
        reason = f"length ratio {length_ratio:.2f} (refined description is much shorter than original)"
        return (True, reason)

    return (False, "")


@beartype
@require(lambda content: isinstance(content, str), "Refinement output must be a string")
@ensure(lambda result: isinstance(result, dict), "Must return a dict")
def _parse_refinement_output_fields(content: str) -> dict[str, Any]:
    """
    Parse refinement output into canonical fields for provider-safe writeback.

    Supports both:
    - Markdown heading style (`## Acceptance Criteria`, `## Story Points`, ...)
    - Label style (`Acceptance Criteria:`, `Story Points:`, ...)
    """
    normalized = content.replace("\r\n", "\n").strip()
    if not normalized:
        return {}

    parsed = _parse_refinement_heading_fields(normalized)
    blocks = _parse_refinement_label_blocks(normalized)
    _merge_refinement_label_blocks(parsed, blocks, normalized)
    _merge_refinement_numeric_fields(parsed, blocks)
    _merge_refinement_body(parsed, blocks, normalized)

    return parsed


def _parse_refinement_heading_fields(normalized: str) -> dict[str, Any]:
    from specfact_backlog.backlog.mappers.github_mapper import GitHubFieldMapper

    heading_fields = GitHubFieldMapper().extract_fields({"body": normalized, "labels": []})
    parsed: dict[str, Any] = {}
    description = (heading_fields.get("description") or "").strip()
    if description:
        parsed["description"] = description
    acceptance = heading_fields.get("acceptance_criteria")
    if isinstance(acceptance, str) and acceptance.strip():
        parsed["acceptance_criteria"] = acceptance.strip()
    for key in ("story_points", "business_value", "priority"):
        value = heading_fields.get(key)
        if isinstance(value, int):
            parsed[key] = value
    heading_description = _extract_refinement_heading_section(normalized, "Description")
    if heading_description and not (parsed.get("description") or "").strip():
        parsed["description"] = heading_description
    return parsed


def _has_refinement_heading_section(normalized: str, section_name: str) -> bool:
    return bool(re.search(rf"^##+\s+{re.escape(section_name)}\s*$", normalized, re.MULTILINE | re.IGNORECASE))


def _extract_refinement_heading_section(normalized: str, section_name: str) -> str:
    pattern = rf"^##+\s+{re.escape(section_name)}\s*$\n(.*?)(?=^##|\Z)"
    match = re.search(pattern, normalized, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _is_refinement_heading_boundary(line: str) -> bool:
    heading_match = re.match(r"^\s*##+\s+(.+?)\s*$", line)
    if not heading_match:
        return False
    heading_name = re.sub(r"\s+", " ", heading_match.group(1).strip().strip("#")).lower()
    return heading_name in _REFINEMENT_HEADING_BOUNDARIES


def _parse_refinement_label_blocks(normalized: str) -> dict[str, str]:
    blocks: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []
    for line in normalized.splitlines():
        if current_key is not None and _is_refinement_heading_boundary(line):
            _store_refinement_block(blocks, current_key, current_lines)
            current_key, current_lines = None, []
            continue
        canonical = _canonical_refinement_label(_REFINEMENT_LABEL_PATTERN.match(line))
        if canonical:
            if current_key is not None:
                _store_refinement_block(blocks, current_key, current_lines)
            current_key = canonical
            match = _REFINEMENT_LABEL_PATTERN.match(line)
            first_value = (match.group(2) or "").strip() if match is not None else ""
            current_lines = [first_value] if first_value else []
            continue
        if current_key is not None:
            current_lines.append(line.rstrip())
    if current_key is not None:
        _store_refinement_block(blocks, current_key, current_lines)
    return blocks


def _canonical_refinement_label(match: re.Match[str] | None) -> str | None:
    if match is None:
        return None
    candidate = re.sub(r"\s+", " ", match.group(1).strip().lower())
    return _REFINEMENT_LABEL_ALIASES.get(candidate)


def _store_refinement_block(blocks: dict[str, str], key: str, lines: list[str]) -> None:
    blocks[key] = "\n".join(lines).strip()


def _merge_refinement_label_blocks(parsed: dict[str, Any], blocks: dict[str, str], normalized: str) -> None:
    if blocks and not blocks.get("description") and not _has_refinement_heading_section(normalized, "Description"):
        parsed.pop("description", None)
    if _has_refinement_heading_section(normalized, "Description") and not blocks.get("description"):
        _trim_refinement_description_suffix(parsed)
    for key in ("description", "acceptance_criteria", "work_item_type"):
        if blocks.get(key):
            parsed[key] = blocks[key]


def _trim_refinement_description_suffix(parsed: dict[str, Any]) -> None:
    description = parsed.get("description")
    if not description:
        return
    description_lines: list[str] = []
    for line in str(description).splitlines():
        canonical = _canonical_refinement_label(_REFINEMENT_LABEL_PATTERN.match(line))
        if canonical and canonical != "description":
            break
        description_lines.append(line.rstrip())
    cleaned = "\n".join(description_lines).strip()
    if cleaned:
        parsed["description"] = cleaned
    else:
        parsed.pop("description", None)


def _merge_refinement_numeric_fields(parsed: dict[str, Any], blocks: dict[str, str]) -> None:
    for key in ("story_points", "business_value", "priority"):
        parsed_value = _parse_refinement_int(blocks.get(key))
        if parsed_value is not None:
            parsed[key] = parsed_value


def _parse_refinement_int(raw: str | None) -> int | None:
    if not raw:
        return None
    match = re.search(r"\d+", raw)
    return int(match.group(0)) if match else None


def _merge_refinement_body(parsed: dict[str, Any], blocks: dict[str, str], normalized: str) -> None:
    cleaned_description = (parsed.get("description") or "").strip()
    body_parts = [cleaned_description] if cleaned_description else []
    for section_key, title in (("notes", "Notes"), ("dependencies", "Dependencies")):
        section_value = (blocks.get(section_key) or "").strip() or _extract_refinement_heading_section(
            normalized, title
        )
        if section_value:
            body_parts.append(f"## {title}\n\n{section_value}")
    cleaned_body = "\n\n".join(part for part in body_parts if part.strip()).strip()
    if cleaned_body:
        parsed["body_markdown"] = cleaned_body
    elif cleaned_description:
        parsed["body_markdown"] = cleaned_description
    else:
        parsed["body_markdown"] = "" if blocks else normalized


@beartype
def _item_needs_refinement(
    item: BacklogItem,
    detector: TemplateDetector,
    registry: TemplateRegistry,
    template_id: str | None,
    normalized_adapter: str | None,
    normalized_framework: str | None,
    normalized_persona: str | None,
) -> bool:
    """
    Return True if the item needs refinement (should be processed); False if already refined (skip).

    Mirrors the "already refined" skip logic used in the refine loop: checkboxes + all required
    sections, or high confidence with no missing fields.
    """
    detection_result = detector.detect_template(
        item,
        provider=normalized_adapter,
        framework=normalized_framework,
        persona=normalized_persona,
    )
    if detection_result.template_id:
        target = registry.get_template(detection_result.template_id) if detection_result.template_id else None
        if target and target.required_sections:
            required_sections = get_effective_required_sections(item, target)
            has_checkboxes = bool(
                re.search(r"^[\s]*- \[[ x]\]", item.body_markdown or "", re.MULTILINE | re.IGNORECASE)
            )
            all_present = all(
                bool(re.search(rf"^#+\s+{re.escape(s)}\s*$", item.body_markdown or "", re.MULTILINE | re.IGNORECASE))
                for s in required_sections
            )
            if has_checkboxes and all_present and not detection_result.missing_fields:
                return False
    already_refined = template_id is None and detection_result.confidence >= 0.8 and not detection_result.missing_fields
    return not already_refined


def _fetch_backlog_items(
    connection: _AdapterContext,
    filters: BacklogFilters,
) -> list[BacklogItem]:
    """
    Fetch backlog items using the specified adapter with filtering support.

    Args:
        connection: Adapter connection context
        filters: Resolved backlog filters to apply

    Returns:
        List of BacklogItem instances (filtered)
    """
    from specfact_backlog.backlog.adapters.interface import BacklogAdapter

    registry = AdapterRegistry()

    # Build adapter kwargs based on adapter type
    adapter_kwargs = _build_adapter_kwargs(connection)

    if connection.adapter.lower() == "github" and (
        not adapter_kwargs.get("repo_owner") or not adapter_kwargs.get("repo_name")
    ):
        console.print("[red]repo_owner and repo_name required for GitHub.[/red]")
        console.print(
            "Set via: [cyan]--repo-owner[/cyan]/[cyan]--repo-name[/cyan], "
            "env [cyan]SPECFACT_GITHUB_REPO_OWNER[/cyan]/[cyan]SPECFACT_GITHUB_REPO_NAME[/cyan], "
            "or [cyan].specfact/backlog.yaml[/cyan] (see docs/guides/devops-adapter-integration.md). "
            "When run from a GitHub clone, org/repo are auto-detected from git remote."
        )
        raise typer.Exit(1)
    if connection.adapter.lower() == "ado" and (not adapter_kwargs.get("org") or not adapter_kwargs.get("project")):
        console.print("[red]ado_org and ado_project required for Azure DevOps.[/red]")
        console.print(
            "Set via: [cyan]--ado-org[/cyan]/[cyan]--ado-project[/cyan], "
            "env [cyan]SPECFACT_ADO_ORG[/cyan]/[cyan]SPECFACT_ADO_PROJECT[/cyan], "
            "or [cyan].specfact/backlog.yaml[/cyan]. "
            "When run from an ADO clone, org/project are auto-detected from git remote."
        )
        raise typer.Exit(1)

    adapter = registry.get_adapter(connection.adapter, **adapter_kwargs)

    # Check if adapter implements BacklogAdapter interface
    if not isinstance(adapter, BacklogAdapter):
        msg = f"Adapter {connection.adapter} does not implement BacklogAdapter interface"
        raise NotImplementedError(msg)

    # Fetch items using the adapter
    items = adapter.fetch_backlog_items(filters)

    # Apply limit deterministically (slice after filtering)
    if filters.limit is not None and len(items) > filters.limit:
        items = items[: filters.limit]

    return items


@beartype
@require(lambda item: isinstance(item, BacklogItem), "Item must be BacklogItem")
@ensure(lambda result: isinstance(result, list), "Must return list")
def _build_refine_update_fields(item: BacklogItem) -> list[str]:
    """Build update field list for refine writeback based on populated canonical fields."""
    update_fields_list = ["title", "body_markdown"]
    if item.acceptance_criteria:
        update_fields_list.append("acceptance_criteria")
    if item.story_points is not None:
        update_fields_list.append("story_points")
    if item.business_value is not None:
        update_fields_list.append("business_value")
    if item.priority is not None:
        update_fields_list.append("priority")
    return update_fields_list


@beartype
def _maybe_add_refine_openspec_comment(
    adapter_instance: BacklogAdapter,
    updated_item: BacklogItem,
    item: BacklogItem,
    openspec_comment: bool,
) -> None:
    """Optionally add OpenSpec reference comment after successful writeback."""
    if not openspec_comment:
        return

    original_body = item.body_markdown or ""
    openspec_change_id = _extract_openspec_change_id(original_body)
    change_id = openspec_change_id or f"backlog-refine-{item.id}"
    comment_text = (
        f"## OpenSpec Change Proposal Reference\n\n"
        f"This backlog item was refined using SpecFact CLI template-driven refinement.\n\n"
        f"- **Change ID**: `{change_id}`\n"
        f"- **Template**: `{item.detected_template or 'auto-detected'}`\n"
        f"- **Confidence**: `{item.template_confidence or 0.0:.2f}`\n"
        f"- **Refined**: {item.refinement_timestamp or 'N/A'}\n\n"
        f"*Note: Original body preserved. "
        f"This comment provides OpenSpec reference for cross-sync.*"
    )
    if adapter_instance.add_comment(updated_item, comment_text):
        console.print("[green]✓ Added OpenSpec reference comment[/green]")
    else:
        console.print("[yellow]⚠ Failed to add comment (adapter may not support comments)[/yellow]")


@beartype
def _write_refined_backlog_item(
    adapter_registry: AdapterRegistry,
    connection: _AdapterContext,
    item: BacklogItem,
    openspec_comment: bool,
) -> bool:
    """Write a refined item back to adapter and optionally add OpenSpec comment."""
    writeback_kwargs = _build_adapter_kwargs(connection)

    adapter_instance = adapter_registry.get_adapter(connection.adapter, **writeback_kwargs)
    if not isinstance(adapter_instance, BacklogAdapter):
        console.print("[yellow]⚠ Adapter does not support backlog updates[/yellow]")
        return False

    update_fields_list = _build_refine_update_fields(item)
    updated_item = adapter_instance.update_backlog_item(item, update_fields=update_fields_list)
    console.print(f"[green]✓ Updated backlog item: {updated_item.url}[/green]")
    _maybe_add_refine_openspec_comment(adapter_instance, updated_item, item, openspec_comment)
    return True


@beartype
@ensure(lambda result: isinstance(result, str), "Must return string")
def _read_refined_content_from_stdin() -> str:
    """Read multiline refined content with sentinel commands from stdin."""
    refined_content_lines: list[str] = []
    console.print("[bold]Paste refined content below (type 'END' on a new line when done):[/bold]")
    console.print("[dim]Commands: :skip (skip this item), :quit or :abort (cancel session)[/dim]")

    while True:
        try:
            line = input()
            line_upper = line.strip().upper()
            if line_upper == "END":
                break
            if line_upper in (":SKIP", ":QUIT", ":ABORT"):
                return line_upper
            refined_content_lines.append(line)
        except EOFError:
            break
    return "\n".join(refined_content_lines).strip()


# fmt: off
@beartype
@app.command()
@require(lambda adapter: isinstance(adapter, str) and len(adapter) > 0, "Adapter must be non-empty string")
def daily(
    ctx: click.Context,
    adapter: str = typer.Argument(..., help="Backlog adapter name (github, ado, etc.)"),
    assignee: str | None = typer.Option(None, "--assignee",
        help="Filter by assignee (e.g. 'me' or username). Use 'any' to disable assignee filtering."),
    search: str | None = typer.Option(None, "--search", "-s",
        help="Search query to filter backlog items (provider-specific syntax)"),
    state: str | None = typer.Option(None, "--state",
        help="Filter by state (e.g. open, closed, Active). Use 'any' to disable state filtering."),
    labels: list[str] | None = typer.Option(None, "--labels", "--tags", help="Filter by labels/tags"),
    release: str | None = typer.Option(None, "--release", help="Filter by release identifier"),
    issue_id: str | None = typer.Option(None, "--id",
        help="Show only this backlog item (issue or work item ID). Other items are ignored."),
    limit: int | None = typer.Option(None, "--limit", help="Maximum number of items to show"),
    first_issues: int | None = typer.Option(None, "--first-issues", min=1,
        help="Show only the first N backlog items after filters (lowest numeric issue/work-item IDs)."),
    last_issues: int | None = typer.Option(None, "--last-issues", min=1,
        help="Show only the last N backlog items after filters (highest numeric issue/work-item IDs)."),
    iteration: str | None = typer.Option(None, "--iteration",
        help="Filter by iteration (e.g. 'current' or literal path). ADO: full path; adapter must support."),
    sprint: str | None = typer.Option(None, "--sprint",
        help="Filter by sprint (e.g. 'current' or name). Adapter must support iteration/sprint."),
    show_unassigned: bool = typer.Option(True, "--show-unassigned/--no-show-unassigned",
        help="Show unassigned/pending items in a second table (default: true)."),
    unassigned_only: bool = typer.Option(False, "--unassigned-only", help="Show only unassigned items (single table)."),
    blockers_first: bool = typer.Option(False, "--blockers-first",
        help="Sort so items with non-empty blockers appear first."),
    mode: str = typer.Option("scrum", "--mode", help="Standup mode defaults: scrum|kanban|safe."),
    interactive: bool = typer.Option(False, "--interactive",
        help="Step-by-step review: select items with arrow keys and view full detail (refine-like) and comments."),
    copilot_export: str | None = typer.Option(None, "--copilot-export",
        help="Write summarized progress per story to a file for Copilot slash-command use during standup."),
    include_comments: bool = typer.Option(False, "--comments", "--annotations",
        help="Include item comments/annotations in summarize/copilot export (adapter must support get_comments)."),
    first_comments: int | None = typer.Option(None, "--first-comments", min=1,
        help="Include only the first N comments per item (optional; default includes all comments)."),
    last_comments: int | None = typer.Option(None, "--last-comments", min=1,
        help="Include only the last N comments per item (optional; default includes all comments)."),
    summarize: bool = typer.Option(False, "--summarize",
        help="Output a prompt (instruction + filter context + standup data) for slash command or Copilot (prints to stdout)."),
    summarize_to: str | None = typer.Option(None, "--summarize-to",
        help="Write the summarize prompt to this file (alternative to --summarize stdout)."),
    suggest_next: bool = typer.Option(False, "--suggest-next",
        help="In interactive mode, show suggested next item by value score (business value / (story points * priority))."),
    patch: bool = typer.Option(False, "--patch",
        help="Emit a patch proposal preview for standup notes/missing fields when patch-mode is available (no silent writes)."),
    post: bool = typer.Option(False, "--post",
        help="Post standup comment to the first item's issue. Requires --yesterday, --today, or --blockers (adapter must support comments)."),
    yesterday: str | None = typer.Option(None, "--yesterday",
        help='Standup: what was done yesterday (used when posting with --post; e.g. --yesterday "Worked on X").'),
    today: str | None = typer.Option(None, "--today",
        help='Standup: what will be done today (used when posting with --post; e.g. --today "Will do Y").'),
    blockers: str | None = typer.Option(None, "--blockers",
        help='Standup: blockers (used when posting with --post; e.g. --blockers "None").'),
    repo_owner: str | None = typer.Option(None, "--repo-owner", help="GitHub repository owner"),
    repo_name: str | None = typer.Option(None, "--repo-name", help="GitHub repository name"),
    github_token: str | None = typer.Option(None, "--github-token", help="GitHub API token"),
    ado_org: str | None = typer.Option(None, "--ado-org", help="Azure DevOps organization"),
    ado_project: str | None = typer.Option(None, "--ado-project", help="Azure DevOps project"),
    ado_team: str | None = typer.Option(None, "--ado-team", help="ADO team for current iteration (when --sprint current)"),
    ado_token: str | None = typer.Option(None, "--ado-token", help="Azure DevOps PAT"),
) -> None:
    # fmt: on
    """Show daily standup view: list my/filtered backlog items with status and last activity."""
    options = locals()
    options.pop("ctx", None)
    _run_daily_command(options)


def _run_daily_command(options: dict[str, Any]) -> None:
    state = _prepare_daily_scope(options)
    if not state["filtered"]:
        console.print("[yellow]No backlog items found.[/yellow]")
        return
    _validate_daily_comment_window(options)
    comments_by_item_id = _daily_comments_by_item_id(options, state)
    if _handle_daily_export(options, state, comments_by_item_id):
        return
    if _handle_daily_summarize(options, state, comments_by_item_id):
        return
    if _handle_daily_interactive(options, state):
        return
    rows_state = _build_daily_rows(options, state)
    if not rows_state:
        return
    if _handle_daily_post(options, state):
        return
    _print_daily_sprint_header(options, state)
    _render_daily_tables(options, rows_state)
    _render_daily_patch_preview(options, state)


def _prepare_daily_scope(options: dict[str, Any]) -> dict[str, Any]:
    standup_config = _load_standup_config()
    normalized_mode = str(options["mode"]).lower().strip()
    if normalized_mode not in {"scrum", "kanban", "safe"}:
        console.print("[red]Invalid --mode. Use one of: scrum, kanban, safe.[/red]")
        raise typer.Exit(1)
    normalized_cli_state = _normalize_state_filter_value(options["state"])
    normalized_cli_assignee = _normalize_assignee_filter_value(options["assignee"])
    effective_state, effective_limit, effective_assignee = _resolve_standup_options(
        normalized_cli_state,
        options["limit"],
        normalized_cli_assignee,
        standup_config,
        state_filter_disabled=_is_filter_disable_literal(options["state"]),
        assignee_filter_disabled=_is_filter_disable_literal(options["assignee"]),
    )
    effective_state = _resolve_daily_mode_state(
        mode=normalized_mode,
        cli_state=normalized_cli_state,
        effective_state=effective_state,
    )
    if options["issue_id"] is not None:
        if normalized_cli_state is None:
            effective_state = None
        if normalized_cli_assignee is None:
            effective_assignee = None
    connection = _daily_adapter_context(options)
    filtered = _fetch_daily_filtered_items(
        connection,
        options,
        assignee=effective_assignee,
        state=effective_state,
        limit=_resolve_daily_fetch_limit(
            effective_limit,
            first_issues=options["first_issues"],
            last_issues=options["last_issues"],
        ),
    )
    _print_daily_scope(options, normalized_mode, effective_state, effective_limit, effective_assignee)
    display_limit = _resolve_daily_display_limit(
        effective_limit,
        first_issues=options["first_issues"],
        last_issues=options["last_issues"],
    )
    if display_limit is not None and len(filtered) > display_limit:
        filtered = filtered[:display_limit]
    return {
        "standup_config": standup_config,
        "normalized_mode": normalized_mode,
        "effective_state": effective_state,
        "effective_limit": effective_limit,
        "effective_assignee": effective_assignee,
        "connection": connection,
        "filtered": filtered,
    }


def _daily_adapter_context(options: dict[str, Any]) -> _AdapterContext:
    return _AdapterContext(
        adapter=options["adapter"],
        repo_owner=options["repo_owner"],
        repo_name=options["repo_name"],
        github_token=options["github_token"],
        ado_org=options["ado_org"],
        ado_project=options["ado_project"],
        ado_team=options["ado_team"],
        ado_token=options["ado_token"],
    )


def _fetch_daily_filtered_items(
    connection: _AdapterContext,
    options: dict[str, Any],
    *,
    assignee: str | None,
    state: str | None,
    limit: int | None,
) -> list[BacklogItem]:
    filters = BacklogFilters(
        assignee=assignee,
        state=state,
        labels=options["labels"],
        search=options["search"],
        iteration=options["iteration"],
        sprint=options["sprint"],
        release=options["release"],
        issue_id=options["issue_id"],
        limit=limit,
    )
    items = _fetch_backlog_items(connection, filters)
    filtered = _apply_filters(
        items,
        labels=options["labels"],
        state=state,
        assignee=_resolve_post_fetch_assignee_filter(options["adapter"], assignee),
        iteration=options["iteration"],
        sprint=options["sprint"],
        release=options["release"],
    )
    filtered = _apply_issue_id_filter(filtered, options["issue_id"])
    if options["issue_id"] is not None and not filtered:
        console.print(
            f"[bold red]✗[/bold red] No backlog item with id {options['issue_id']!r} found. "
            "Check filters and adapter configuration."
        )
        raise typer.Exit(1)
    try:
        return _resolve_daily_issue_window(
            filtered,
            first_issues=options["first_issues"],
            last_issues=options["last_issues"],
        )
    except ValueError as exc:
        console.print(f"[red]{exc}.[/red]")
        raise typer.Exit(1) from exc


def _print_daily_scope(
    options: dict[str, Any],
    normalized_mode: str,
    effective_state: str | None,
    effective_limit: int,
    effective_assignee: str | None,
) -> None:
    summary = _DailyScopeSummary(
        mode=normalized_mode,
        cli_state=options["state"],
        effective_state=effective_state,
        cli_assignee=options["assignee"],
        effective_assignee=effective_assignee,
        cli_limit=options["limit"],
        effective_limit=effective_limit,
        issue_id=options["issue_id"],
        labels=options["labels"],
        sprint=options["sprint"],
        iteration=options["iteration"],
        release=options["release"],
        first_issues=options["first_issues"],
        last_issues=options["last_issues"],
    )
    console.print("[dim]" + _format_daily_scope_summary(summary) + "[/dim]")


def _validate_daily_comment_window(options: dict[str, Any]) -> None:
    if options["first_comments"] is not None and options["last_comments"] is not None:
        console.print("[red]Use only one of --first-comments or --last-comments.[/red]")
        raise typer.Exit(1)


def _daily_comments_by_item_id(options: dict[str, Any], state: dict[str, Any]) -> dict[str, list[str]]:
    if not options["include_comments"]:
        return {}
    if not (options["copilot_export"] is not None or options["summarize"] or options["summarize_to"] is not None):
        return {}
    return _collect_comment_annotations(
        state["connection"],
        state["filtered"],
        first_comments=options["first_comments"],
        last_comments=options["last_comments"],
    )


def _handle_daily_export(
    options: dict[str, Any],
    state: dict[str, Any],
    comments_by_item_id: dict[str, list[str]],
) -> bool:
    if options["copilot_export"] is None:
        return False
    filtered = state["filtered"]
    include_score = options["suggest_next"] or bool(state["standup_config"].get("suggest_next"))
    export_path = Path(options["copilot_export"])
    content = _build_copilot_export_content(
        filtered,
        include_value_score=include_score,
        include_comments=options["include_comments"],
        comments_by_item_id=comments_by_item_id or None,
    )
    export_path.write_text(content, encoding="utf-8")
    console.print(f"[dim]Exported {len(filtered)} item(s) to {export_path}[/dim]")
    return False


def _handle_daily_summarize(
    options: dict[str, Any],
    state: dict[str, Any],
    comments_by_item_id: dict[str, list[str]],
) -> bool:
    if not (options["summarize"] or options["summarize_to"] is not None):
        return False
    filtered = state["filtered"]
    include_score = options["suggest_next"] or bool(state["standup_config"].get("suggest_next"))
    content = _build_summarize_prompt_content(
        filtered,
        filter_context=_daily_summarize_filter_context(options, state),
        include_value_score=include_score,
        comments_by_item_id=comments_by_item_id or None,
        include_comments=options["include_comments"],
    )
    if options["summarize_to"]:
        Path(options["summarize_to"]).write_text(content, encoding="utf-8")
        console.print(f"[dim]Summarize prompt written to {options['summarize_to']} ({len(filtered)} item(s))[/dim]")
    elif _is_interactive_tty() and not os.environ.get("CI"):
        console.print(Markdown(content))
    else:
        console.print(content)
    return True


def _daily_summarize_filter_context(options: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    return {
        "adapter": options["adapter"],
        "state": state["effective_state"] or "—",
        "sprint": options["sprint"] or options["iteration"] or "—",
        "assignee": state["effective_assignee"] or "—",
        "limit": state["effective_limit"],
    }


def _handle_daily_interactive(options: dict[str, Any], state: dict[str, Any]) -> bool:
    if not options["interactive"]:
        return False
    _run_interactive_daily(
        state["filtered"],
        suggest_next=options["suggest_next"],
        connection=state["connection"],
        first_comments=options["first_comments"],
        last_comments=options["last_comments"],
    )
    return True


def _build_daily_rows(options: dict[str, Any], state: dict[str, Any]) -> dict[str, Any] | None:
    filtered = state["filtered"]
    include_priority = bool(state["standup_config"].get("show_priority") or state["standup_config"].get("show_value"))
    rows_unassigned: list[dict[str, Any]] = []
    if options["unassigned_only"]:
        _, filtered = _split_assigned_unassigned(filtered)
        if not filtered:
            console.print("[yellow]No unassigned items in scope.[/yellow]")
            return None
        rows = _build_standup_rows(filtered, include_priority=include_priority)
    else:
        assigned, unassigned = _split_assigned_unassigned(filtered)
        rows = _build_standup_rows(assigned, include_priority=include_priority)
        if options["show_unassigned"] and unassigned:
            rows_unassigned = _build_standup_rows(unassigned, include_priority=include_priority)
    if options["blockers_first"]:
        rows = _sort_standup_rows_blockers_first(rows)
    return {
        "filtered": filtered,
        "rows": rows,
        "rows_unassigned": rows_unassigned,
        "include_priority": include_priority,
    }


def _handle_daily_post(options: dict[str, Any], state: dict[str, Any]) -> bool:
    if not options["post"]:
        return False
    y = (options["yesterday"] or "").strip()
    t = (options["today"] or "").strip()
    b = (options["blockers"] or "").strip()
    if not y and not t and not b:
        console.print("[yellow]Use --yesterday, --today, and/or --blockers with values when using --post.[/yellow]")
        console.print('[dim]Example: --yesterday "Worked on X" --today "Will do Y" --blockers "None" --post[/dim]')
        return True
    item = state["filtered"][0]
    adapter_instance = AdapterRegistry().get_adapter(options["adapter"], **_build_adapter_kwargs(state["connection"]))
    if not isinstance(adapter_instance, BacklogAdapter):
        console.print("[red]Adapter does not implement BacklogAdapter.[/red]")
        raise typer.Exit(1)
    if not _post_standup_comment_supported(adapter_instance, item):
        console.print("[yellow]Posting comments is not supported for this adapter.[/yellow]")
        return True
    if _post_standup_to_item(adapter_instance, item, _format_standup_comment(y, t, b)):
        console.print(f"[green]✓ Standup comment posted to {item.url}[/green]")
        return True
    console.print("[red]Failed to post standup comment.[/red]")
    raise typer.Exit(1)


def _print_daily_sprint_header(options: dict[str, Any], state: dict[str, Any]) -> None:
    sprint_end = state["standup_config"].get("sprint_end_date") or os.environ.get("SPECFACT_STANDUP_SPRINT_END")
    if not sprint_end or not (options["sprint"] or options["iteration"]):
        return
    try:
        end_date = datetime.strptime(str(sprint_end)[:10], "%Y-%m-%d").date()
        console.print(f"[dim]{_format_sprint_end_header(end_date)}[/dim]")
    except (ValueError, TypeError):
        console.print("[dim]Sprint end date could not be parsed; header skipped.[/dim]")


def _add_standup_rows_to_table(tbl: Table, row_list: list[dict[str, Any]], include_pri: bool) -> None:
    for r in row_list:
        cells: list[Any] = [
            str(r["id"]),
            str(r["title"])[:50],
            str(r["status"]),
            str(r.get("assignees", "—"))[:30],
            r["last_updated"].strftime("%Y-%m-%d %H:%M")
            if hasattr(r["last_updated"], "strftime")
            else str(r["last_updated"]),
            (r.get("yesterday") or "")[:30],
            (r.get("today") or "")[:30],
            (r.get("blockers") or "")[:20],
        ]
        if include_pri and "priority" in r:
            cells.append(str(r["priority"]))
        tbl.add_row(*cells)


def _make_standup_table(title: str, include_priority: bool) -> Table:
    table_obj = Table(title=title, show_header=True, header_style="bold cyan")
    table_obj.add_column("ID", style="dim")
    table_obj.add_column("Title")
    table_obj.add_column("Status")
    table_obj.add_column("Assignee", style="dim", max_width=30)
    table_obj.add_column("Last updated")
    table_obj.add_column("Yesterday", style="dim", max_width=30)
    table_obj.add_column("Today", style="dim", max_width=30)
    table_obj.add_column("Blockers", style="dim", max_width=20)
    if include_priority:
        table_obj.add_column("Priority", style="dim")
    return table_obj


def _render_daily_table(title: str, rows: list[dict[str, Any]], include_priority: bool) -> None:
    table = _make_standup_table(title, include_priority)
    _add_standup_rows_to_table(table, rows, include_priority)
    console.print(table)


def _render_daily_tables(options: dict[str, Any], rows_state: dict[str, Any]) -> None:
    rows = rows_state["rows"]
    include_priority = rows_state["include_priority"]
    exceptions_rows, normal_rows = _split_exception_rows(rows)
    if exceptions_rows:
        _render_daily_table("Exceptions", exceptions_rows, include_priority)
    if normal_rows:
        _render_daily_table("Daily standup", normal_rows, include_priority)
    if not exceptions_rows and not normal_rows:
        console.print(_make_standup_table("Daily standup", include_priority))
    if not options["unassigned_only"] and options["show_unassigned"] and rows_state["rows_unassigned"]:
        _render_daily_table("Pending / open for commitment", rows_state["rows_unassigned"], include_priority)


def _render_daily_patch_preview(options: dict[str, Any], state: dict[str, Any]) -> None:
    if not options["patch"]:
        return
    if _is_patch_mode_available():
        proposal = _build_daily_patch_proposal(state["filtered"], mode=state["normalized_mode"])
        console.print("\n[bold]Patch proposal preview:[/bold]")
        console.print(Panel(proposal, border_style="yellow"))
        console.print("[dim]No changes applied. Review/apply explicitly via patch workflow.[/dim]")
        return
    console.print(
        "[dim]Patch proposal requested, but patch-mode is not available yet. Continuing without patch output.[/dim]"
    )


app.add_typer(ceremony_app, name="ceremony", help="Ceremony-oriented backlog workflows")
app.add_typer(auth_app, name="auth", help="Authenticate backlog providers")

# Register migrated backlog-core commands
app.command("add")(add)
app.command("analyze-deps")(analyze_deps)
app.command("sync")(sync)
app.command("diff")(diff)
app.command("promote")(promote)
app.command("verify-readiness")(verify_readiness)
app.add_typer(_delta_app, name="delta", help="Backlog delta analysis and impact tracking")


@beartype
@app.command()
@require(lambda adapter: isinstance(adapter, str) and len(adapter) > 0, "Adapter must be non-empty string")
def refine(
    ctx: click.Context,
    adapter: str = typer.Argument(..., help="Backlog adapter name (github, ado, etc.)"),
    labels: list[str] | None = typer.Option(
        None, "--labels", "--tags", help="Filter by labels/tags (can specify multiple)"
    ),
    state: str | None = typer.Option(
        None,
        "--state",
        help="Filter by state (case-insensitive, e.g., 'open', 'closed', 'Active', 'New'). Use 'any' to disable state filtering.",
    ),
    assignee: str | None = typer.Option(
        None,
        "--assignee",
        help="Filter by assignee (case-insensitive). GitHub: login or @username. ADO: displayName, uniqueName, or mail. Use 'any' to disable assignee filtering.",
    ),
    iteration: str | None = typer.Option(
        None,
        "--iteration",
        help="Filter by iteration path (ADO format: 'Project\\Sprint 1' or 'current' for current iteration). Must be exact full path from ADO.",
    ),
    sprint: str | None = typer.Option(
        None,
        "--sprint",
        help="Filter by sprint (case-insensitive). ADO: use full iteration path to avoid ambiguity. If omitted, defaults to current active iteration.",
    ),
    release: str | None = typer.Option(None, "--release", help="Filter by release identifier"),
    persona: str | None = typer.Option(
        None, "--persona", help="Filter templates by persona (product-owner, architect, developer)"
    ),
    framework: str | None = typer.Option(
        None, "--framework", help="Filter templates by framework (agile, scrum, safe, kanban)"
    ),
    search: str | None = typer.Option(
        None, "--search", "-s", help="Search query to filter backlog items (provider-specific syntax)"
    ),
    limit: int | None = typer.Option(
        None, "--limit", help="Maximum number of items to process in this refinement session."
    ),
    first_issues: int | None = typer.Option(
        None, "--first-issues", min=1, help="Process only the first N backlog items after filters/refinement checks."
    ),
    last_issues: int | None = typer.Option(
        None, "--last-issues", min=1, help="Process only the last N backlog items after filters/refinement checks."
    ),
    ignore_refined: bool = typer.Option(
        True, "--ignore-refined/--no-ignore-refined", help="Exclude already-refined items before applying limits."
    ),
    issue_id: str | None = typer.Option(None, "--id", help="Refine only this backlog item (issue or work item ID)."),
    template_id: str | None = typer.Option(None, "--template", "-t", help="Target template ID (default: auto-detect)"),
    auto_accept_high_confidence: bool = typer.Option(
        False, "--auto-accept-high-confidence", help="Auto-accept refinements with confidence >= 0.85"
    ),
    bundle: str | None = typer.Option(None, "--bundle", "-b", help="OpenSpec bundle path to import refined items"),
    auto_bundle: bool = typer.Option(False, "--auto-bundle", help="Auto-import refined items to OpenSpec bundle"),
    openspec_comment: bool = typer.Option(
        False, "--openspec-comment", help="Add OpenSpec change proposal reference as comment"
    ),
    preview: bool = typer.Option(
        True, "--preview/--no-preview", help="Preview mode: show what will be written without updating backlog"
    ),
    write: bool = typer.Option(False, "--write", help="Write mode: explicitly opt-in to update remote backlog"),
    export_to_tmp: bool = typer.Option(
        False, "--export-to-tmp", help="Export backlog items to temporary file for copilot processing"
    ),
    import_from_tmp: bool = typer.Option(
        False, "--import-from-tmp", help="Import refined content from temporary file after copilot processing"
    ),
    tmp_file: Path | None = typer.Option(None, "--tmp-file", help="Custom temporary file path"),
    first_comments: int | None = typer.Option(
        None, "--first-comments", min=1, help="Include only the first N comments per item."
    ),
    last_comments: int | None = typer.Option(
        None, "--last-comments", min=1, help="Include only the last N comments per item."
    ),
    check_dor: bool = typer.Option(
        False, "--check-dor", help="Check Definition of Ready (DoR) rules before refinement"
    ),
    repo_owner: str | None = typer.Option(None, "--repo-owner", help="GitHub repository owner"),
    repo_name: str | None = typer.Option(None, "--repo-name", help="GitHub repository name"),
    github_token: str | None = typer.Option(None, "--github-token", help="GitHub API token"),
    ado_org: str | None = typer.Option(None, "--ado-org", help="Azure DevOps organization"),
    ado_project: str | None = typer.Option(None, "--ado-project", help="Azure DevOps project"),
    ado_team: str | None = typer.Option(None, "--ado-team", help="Azure DevOps team name for iteration lookup"),
    ado_token: str | None = typer.Option(None, "--ado-token", help="Azure DevOps PAT"),
    custom_field_mapping: str | None = typer.Option(
        None, "--custom-field-mapping", help="Path to custom ADO field mapping YAML file"
    ),
) -> None:
    # fmt: on
    """Refine backlog items using AI-assisted template matching."""
    options = locals()
    options.pop("ctx", None)
    _run_refine_command(options)


def _run_refine_command(options: dict[str, Any]) -> None:
    try:
        state = _initialize_refine_state(options)
        items = _fetch_and_filter_refine_items(options, state)
        if _handle_refine_export(options, state, items) or _handle_refine_import(options, state, items):
            return
        items = _apply_refine_limit(options, items)
        result = _process_refine_items(options, state, items)
        _handle_refine_bundle_import(options, result["refined_items"])
        _print_refine_summary(options, result)
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc


def _initialize_refine_state(options: dict[str, Any]) -> dict[str, Any]:
    connection = _refine_adapter_context(options)
    normalized_adapter = str(options["adapter"]).lower() if options["adapter"] else None
    normalized_framework = str(options["framework"]).lower() if options["framework"] else None
    if normalized_adapter and not normalized_framework:
        normalized_framework = _resolve_backlog_provider_framework(normalized_adapter)
    state = {
        "connection": connection,
        "normalized_state_filter": _normalize_state_filter_value(options["state"]),
        "normalized_assignee_filter": _normalize_assignee_filter_value(options["assignee"]),
        "normalized_adapter": normalized_adapter,
        "normalized_framework": normalized_framework,
        "normalized_persona": str(options["persona"]).lower() if options["persona"] else None,
    }
    state.update(_initialize_refine_runtime(options, state))
    return state


def _refine_adapter_context(options: dict[str, Any]) -> _AdapterContext:
    return _AdapterContext(
        adapter=options["adapter"],
        repo_owner=options["repo_owner"],
        repo_name=options["repo_name"],
        github_token=options["github_token"],
        ado_org=options["ado_org"],
        ado_project=options["ado_project"],
        ado_team=options["ado_team"],
        ado_token=options["ado_token"],
    )


def _initialize_refine_runtime(options: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        registry = _load_refine_template_registry(progress)
        detector_task = progress.add_task("[cyan]Initializing template detector...[/cyan]", total=None)
        detector = TemplateDetector(registry)
        progress.update(detector_task, description="[green]✓[/green] Template detector ready")
        refiner_task = progress.add_task("[cyan]Initializing AI refiner...[/cyan]", total=None)
        refiner = BacklogAIRefiner()
        progress.update(refiner_task, description="[green]✓[/green] AI refiner ready")
        adapter_task = progress.add_task("[cyan]Initializing adapter...[/cyan]", total=None)
        adapter_registry = AdapterRegistry()
        progress.update(adapter_task, description="[green]✓[/green] Adapter registry ready")
        dor_config = _load_refine_dor_config(options, progress)
        _validate_refine_configuration(options, state, progress)
    return {
        "registry": registry,
        "detector": detector,
        "refiner": refiner,
        "adapter_registry": adapter_registry,
        "dor_config": dor_config,
    }


def _load_refine_template_registry(progress: Progress) -> TemplateRegistry:
    task = progress.add_task("[cyan]Initializing templates...[/cyan]", total=None)
    registry = TemplateRegistry()
    loaded = _load_builtin_refine_templates(registry)
    project_templates_dir = Path.cwd() / ".specfact" / "templates" / "backlog"
    if project_templates_dir.exists():
        registry.load_templates_from_directory(project_templates_dir)
    if not loaded:
        console.print("[yellow]⚠ No built-in backlog templates found; continuing with custom templates only.[/yellow]")
    progress.update(task, description="[green]✓[/green] Templates initialized")
    return registry


def _load_builtin_refine_templates(registry: TemplateRegistry) -> bool:
    from specfact_cli.utils.ide_setup import find_package_resources_path

    candidates = [find_package_resources_path("specfact_cli", "resources/templates/backlog")]
    repo_root = Path(__file__).parent.parent.parent.parent.parent.parent
    candidates.append(repo_root / "resources" / "templates" / "backlog")
    candidates.append(Path(__file__).parent.parent.parent.parent / "templates")
    for candidate in candidates:
        if candidate and candidate.exists():
            registry.load_templates_from_directory(candidate)
            return True
    return False


def _load_refine_dor_config(options: dict[str, Any], progress: Progress) -> DefinitionOfReady | None:
    if not options["check_dor"]:
        return None
    task = progress.add_task("[cyan]Loading DoR configuration...[/cyan]", total=None)
    dor_config = DefinitionOfReady.load_from_repo(Path("."))
    if dor_config:
        progress.update(task, description="[green]✓[/green] DoR configuration loaded")
        return dor_config
    progress.update(task, description="[yellow]⚠[/yellow] Using default DoR rules")
    return DefinitionOfReady(
        rules={
            "story_points": True,
            "value_points": False,
            "priority": True,
            "business_value": True,
            "acceptance_criteria": True,
            "dependencies": False,
        }
    )


def _validate_refine_configuration(options: dict[str, Any], state: dict[str, Any], progress: Progress) -> None:
    task = progress.add_task("[cyan]Validating adapter configuration...[/cyan]", total=None)
    kwargs = _build_adapter_kwargs(state["connection"])
    if state["normalized_adapter"] == "github" and (not kwargs.get("repo_owner") or not kwargs.get("repo_name")):
        progress.stop()
        console.print("[red]repo_owner and repo_name required for GitHub.[/red]")
        raise typer.Exit(1)
    if state["normalized_adapter"] == "ado" and (not kwargs.get("org") or not kwargs.get("project")):
        progress.stop()
        console.print("[red]ado_org and ado_project required for Azure DevOps.[/red]")
        raise typer.Exit(1)
    _validate_refine_custom_mapping(options, progress, task)


def _validate_refine_custom_mapping(options: dict[str, Any], progress: Progress, task: Any) -> None:
    if not options["custom_field_mapping"]:
        progress.update(task, description="[green]✓[/green] Configuration validated")
        return
    mapping_path = Path(options["custom_field_mapping"])
    if not mapping_path.exists() or not mapping_path.is_file():
        progress.stop()
        console.print(f"[red]Error:[/red] Custom field mapping file not found: {mapping_path}")
        raise typer.Exit(1)
    from specfact_backlog.backlog.mappers.template_config import FieldMappingConfig

    try:
        FieldMappingConfig.from_file(mapping_path)
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        progress.stop()
        console.print(f"[red]Error:[/red] Invalid custom field mapping file: {exc}")
        raise typer.Exit(1) from exc
    os.environ["SPECFACT_ADO_CUSTOM_MAPPING"] = str(mapping_path.absolute())
    progress.update(task, description="[green]✓[/green] Field mapping validated")


def _fetch_and_filter_refine_items(options: dict[str, Any], state: dict[str, Any]) -> list[BacklogItem]:
    _validate_refine_windows(options)
    items = _fetch_refine_items(options, state)
    if not items:
        _print_refine_no_items(options, state)
        return []
    items = _filter_refine_issue_id(options, items)
    if options["ignore_refined"]:
        items = _filter_refine_needed_items(options, state, items)
    return _apply_issue_window(items, first_issues=options["first_issues"], last_issues=options["last_issues"])


def _validate_refine_windows(options: dict[str, Any]) -> None:
    if options["export_to_tmp"] and options["import_from_tmp"]:
        console.print("[bold red]✗[/bold red] --export-to-tmp and --import-from-tmp are mutually exclusive")
        raise typer.Exit(1)
    if options["first_comments"] is not None and options["last_comments"] is not None:
        console.print("[bold red]✗[/bold red] Use only one of --first-comments or --last-comments")
        raise typer.Exit(1)
    if options["first_issues"] is not None and options["last_issues"] is not None:
        console.print("[bold red]✗[/bold red] Use only one of --first-issues or --last-issues")
        raise typer.Exit(1)


def _fetch_refine_items(options: dict[str, Any], state: dict[str, Any]) -> list[BacklogItem]:
    fetch_limit = options["limit"] * 5 if options["ignore_refined"] and options["limit"] else options["limit"]
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task(f"[cyan]Fetching backlog items from {options['adapter']}...[/cyan]", total=None)
        filters = BacklogFilters(
            assignee=state["normalized_assignee_filter"],
            state=state["normalized_state_filter"],
            labels=options["labels"],
            search=options["search"],
            iteration=options["iteration"],
            sprint=options["sprint"],
            release=options["release"],
            issue_id=options["issue_id"],
            limit=fetch_limit,
        )
        items = _fetch_backlog_items(state["connection"], filters)
        progress.update(task, description="[green]✓[/green] Fetched backlog items")
        return items


def _print_refine_no_items(options: dict[str, Any], state: dict[str, Any]) -> None:
    filter_info = _refine_filter_info(options, state)
    if not filter_info:
        console.print("[yellow]No backlog items found.[/yellow]")
        return
    console.print(
        f"[yellow]No backlog items found with the specified filters:[/yellow] {', '.join(filter_info)}\n"
        f"[cyan]Tips:[/cyan]\n  • Verify the iteration path exists in Azure DevOps\n"
        f"  • Try using [bold]--iteration current[/bold] to use the current active iteration\n"
        f"  • Try using [bold]--sprint[/bold] with just the sprint name for automatic matching\n"
        f"  • Check that items exist in the specified iteration/sprint"
    )


def _refine_filter_info(options: dict[str, Any], state: dict[str, Any]) -> list[str]:
    pairs = [
        ("state", state["normalized_state_filter"]),
        ("assignee", state["normalized_assignee_filter"]),
        ("iteration", options["iteration"]),
        ("sprint", options["sprint"]),
        ("release", options["release"]),
    ]
    return [f"{name}={value}" for name, value in pairs if value]


def _filter_refine_issue_id(options: dict[str, Any], items: list[BacklogItem]) -> list[BacklogItem]:
    if options["issue_id"] is None:
        return items
    filtered = [item for item in items if str(item.id) == str(options["issue_id"])]
    if not filtered:
        console.print(
            f"[bold red]✗[/bold red] No backlog item with id {options['issue_id']!r} found. Check filters and adapter configuration."
        )
        raise typer.Exit(1)
    return filtered


def _filter_refine_needed_items(
    options: dict[str, Any], state: dict[str, Any], items: list[BacklogItem]
) -> list[BacklogItem]:
    filtered = [
        item
        for item in items
        if _item_needs_refinement(
            item,
            state["detector"],
            state["registry"],
            options["template_id"],
            state["normalized_adapter"],
            state["normalized_framework"],
            state["normalized_persona"],
        )
    ]
    if (
        options["limit"] is not None
        or options["issue_id"] is not None
        or options["first_issues"] is not None
        or options["last_issues"] is not None
    ):
        suffix = f" (limit {options['limit']})" if options["limit"] is not None else ""
        console.print(f"[dim]Filtered to {len(filtered)} item(s) needing refinement{suffix}[/dim]")
    return filtered


def _apply_refine_limit(options: dict[str, Any], items: list[BacklogItem]) -> list[BacklogItem]:
    if options["limit"] is not None and len(items) > options["limit"]:
        console.print(f"[dim]Limiting refinement batch to {options['limit']} item(s)[/dim]")
        return items[: options["limit"]]
    return items


def _handle_refine_export(options: dict[str, Any], state: dict[str, Any], items: list[BacklogItem]) -> bool:
    if not options["export_to_tmp"]:
        return False
    export_file = options["tmp_file"] or (
        Path(tempfile.gettempdir()) / f"specfact-backlog-refine-{datetime.now():%Y%m%d-%H%M%S}.md"
    )
    console.print(f"[bold cyan]Exporting {len(items)} backlog item(s) to: {export_file}[/bold cyan]")
    first_comments, last_comments = _resolve_refine_export_comment_window(
        first_comments=options["first_comments"],
        last_comments=options["last_comments"],
    )
    comments = _collect_comment_annotations(
        state["connection"],
        items,
        first_comments=first_comments,
        last_comments=last_comments,
    )
    guidance = _refine_template_guidance_by_item_id(options, state, items)
    content = _build_refine_export_content(
        options["adapter"], items, comments_by_item_id=comments or None, template_guidance_by_item_id=guidance or None
    )
    export_file.write_text(content, encoding="utf-8")
    console.print(f"[green]✓ Exported to: {export_file}[/green]")
    console.print("[dim]Process items with copilot, then use --import-from-tmp to import refined content[/dim]")
    return True


def _refine_template_guidance_by_item_id(
    options: dict[str, Any], state: dict[str, Any], items: list[BacklogItem]
) -> dict[str, dict[str, Any]]:
    guidance: dict[str, dict[str, Any]] = {}
    for item in items:
        template = _resolve_target_template_for_refine_item(
            item,
            detector=state["detector"],
            registry=state["registry"],
            template_id=options["template_id"],
            normalized_adapter=state["normalized_adapter"],
            normalized_framework=state["normalized_framework"],
            normalized_persona=state["normalized_persona"],
        )
        if template is not None:
            guidance[item.id] = _refine_template_guidance(item, template)
    return guidance


def _refine_template_guidance(item: BacklogItem, template: BacklogTemplate) -> dict[str, Any]:
    optional_sections = list(template.optional_sections or [])
    if item.provider.lower() == "ado":
        optional_sections = [section for section in optional_sections if section not in {"Area Path", "Iteration Path"}]
    return {
        "template_id": template.template_id,
        "name": template.name,
        "description": template.description,
        "required_sections": list(get_effective_required_sections(item, template)),
        "optional_sections": optional_sections,
    }


def _handle_refine_import(options: dict[str, Any], state: dict[str, Any], items: list[BacklogItem]) -> bool:
    if not options["import_from_tmp"]:
        return False
    import_file = options["tmp_file"] or (
        Path(tempfile.gettempdir()) / f"specfact-backlog-refine-{datetime.now():%Y%m%d-%H%M%S}-refined.md"
    )
    if not import_file.exists():
        console.print(f"[bold red]✗[/bold red] Import file not found: {import_file}")
        raise typer.Exit(1)
    parsed_by_id = _parse_refined_export_markdown(import_file.read_text(encoding="utf-8"))
    updated_items = _apply_refine_import_data(items, parsed_by_id)
    if not updated_items:
        console.print("[bold red]✗[/bold red] None of the refined item IDs matched fetched backlog items")
        raise typer.Exit(1)
    _write_refine_import_updates(options, state, updated_items)
    return True


def _apply_refine_import_data(items: list[BacklogItem], parsed_by_id: dict[str, dict[str, Any]]) -> list[BacklogItem]:
    updated_items: list[BacklogItem] = []
    for item in items:
        data = parsed_by_id.get(item.id)
        if not data:
            continue
        refined_body = data.get("body_markdown", item.body_markdown or "") or ""
        has_loss, loss_reason = _detect_significant_content_loss(item.body_markdown or "", refined_body)
        if has_loss:
            console.print(
                f"[bold red]✗[/bold red] Refined content for item {item.id} appears to drop important detail ({loss_reason})."
            )
            raise typer.Exit(1)
        _apply_refine_import_fields(item, data, refined_body)
        updated_items.append(item)
    return updated_items


def _apply_refine_import_fields(item: BacklogItem, data: dict[str, Any], refined_body: str) -> None:
    item.body_markdown = refined_body
    for attr, key in [
        ("acceptance_criteria", "acceptance_criteria"),
        ("title", "title"),
        ("story_points", "story_points"),
        ("business_value", "business_value"),
        ("priority", "priority"),
    ]:
        if key in data and data[key] is not None:
            setattr(item, attr, data[key])


def _write_refine_import_updates(
    options: dict[str, Any], state: dict[str, Any], updated_items: list[BacklogItem]
) -> None:
    if not options["write"]:
        console.print(
            "[yellow]Preview mode: imported refinements were validated but not written. Use --write to update backlog.[/yellow]"
        )
        return
    for item in updated_items:
        _write_refined_backlog_item(
            adapter_registry=state["adapter_registry"],
            connection=state["connection"],
            item=item,
            openspec_comment=options["openspec_comment"],
        )
    console.print(f"[green]✓ Imported {len(updated_items)} refined item(s)[/green]")


def _process_refine_items(options: dict[str, Any], state: dict[str, Any], items: list[BacklogItem]) -> dict[str, Any]:
    result: dict[str, Any] = {"refined_count": 0, "skipped_count": 0, "cancelled": False, "refined_items": []}
    comments = _preview_refine_comments(options, state, items)
    for idx, item in enumerate(items, 1):
        status = _process_one_refine_item(options, state, item, idx, len(items), comments)
        result["refined_count"] += status.get("refined", 0)
        result["skipped_count"] += status.get("skipped", 0)
        if status.get("item") is not None:
            result["refined_items"].append(status["item"])
        if status.get("cancelled"):
            result["cancelled"] = True
            break
    return result


def _preview_refine_comments(
    options: dict[str, Any], state: dict[str, Any], items: list[BacklogItem]
) -> dict[str, list[str]]:
    if not (options["preview"] and not options["write"]):
        return {}
    first_comments, last_comments = _resolve_refine_preview_comment_window(
        first_comments=options["first_comments"], last_comments=options["last_comments"]
    )
    return _collect_comment_annotations(
        state["connection"], items, first_comments=first_comments, last_comments=last_comments
    )


def _process_one_refine_item(
    options: dict[str, Any],
    state: dict[str, Any],
    item: BacklogItem,
    idx: int,
    total: int,
    comments: dict[str, list[str]],
) -> dict[str, Any]:
    console.print(f"\n[bold]Processing item {idx}/{total}: {item.title}[/bold]")
    target_template = _resolve_refine_target_template(options, state, item)
    if target_template is None:
        console.print("[yellow]No template available for refinement[/yellow]")
        return {"skipped": 1}
    if options["preview"] and not options["write"]:
        _print_refine_item_preview(item, target_template, comments.get(item.id, []))
        return {"skipped": 1}
    return _interactive_refine_item(options, state, item, target_template, comments.get(item.id, []))


def _resolve_refine_target_template(
    options: dict[str, Any], state: dict[str, Any], item: BacklogItem
) -> BacklogTemplate | None:
    detection = state["detector"].detect_template(
        item,
        provider=state["normalized_adapter"],
        framework=state["normalized_framework"],
        persona=state["normalized_persona"],
    )
    if options["template_id"]:
        template = state["registry"].get_template(options["template_id"])
        if template is None:
            console.print(f"[yellow]Template {options['template_id']} not found, using auto-detection[/yellow]")
        return template or _resolve_target_template_for_refine_item(
            item,
            detector=state["detector"],
            registry=state["registry"],
            template_id=None,
            normalized_adapter=state["normalized_adapter"],
            normalized_framework=state["normalized_framework"],
            normalized_persona=state["normalized_persona"],
        )
    if detection.template_id:
        template = state["registry"].get_template(detection.template_id)
        if template is not None:
            return template
    return _resolve_target_template_for_refine_item(
        item,
        detector=state["detector"],
        registry=state["registry"],
        template_id=None,
        normalized_adapter=state["normalized_adapter"],
        normalized_framework=state["normalized_framework"],
        normalized_persona=state["normalized_persona"],
    )


def _print_refine_item_preview(item: BacklogItem, template: BacklogTemplate, comments: list[str]) -> None:
    console.print("\n[bold]Preview Mode: Full Item Details[/bold]")
    console.print(f"[bold]Title:[/bold] {item.title}")
    console.print(f"[bold]URL:[/bold] {item.url}")
    console.print(f"[bold]State:[/bold] {item.state}")
    console.print(f"[bold]Provider:[/bold] {item.provider}")
    console.print(f"[bold]Assignee:[/bold] {', '.join(item.assignees) if item.assignees else 'Unassigned'}")
    _print_refine_metrics(item)
    _print_refine_acceptance_criteria(item, template)
    _print_refine_body_preview(item)
    console.print("\n[bold]Comments:[/bold]")
    panels = (
        _build_refine_preview_comment_panels(comments) if comments else [_build_refine_preview_comment_empty_panel()]
    )
    for panel in panels:
        console.print(panel)
    console.print(f"\n[bold]Target Template:[/bold] {template.name} (ID: {template.template_id})")
    console.print(f"[bold]Template Description:[/bold] {template.description}")
    console.print("\n[yellow]⚠ Preview mode: Item needs refinement but interactive prompts are skipped[/yellow]")


def _print_refine_metrics(item: BacklogItem) -> None:
    if item.story_points is None and item.business_value is None and item.priority is None:
        return
    console.print("\n[bold]Story Metrics:[/bold]")
    for label, value in [
        ("Story Points", item.story_points),
        ("Business Value", item.business_value),
        ("Priority", item.priority),
        ("Value Points (SAFe)", item.value_points),
        ("Work Item Type", item.work_item_type),
    ]:
        if value is not None:
            console.print(f"  - {label}: {value}")


def _print_refine_acceptance_criteria(item: BacklogItem, template: BacklogTemplate) -> None:
    required = get_effective_required_sections(item, template)
    if "Acceptance Criteria" not in required and not item.acceptance_criteria:
        return
    console.print("\n[bold]Acceptance Criteria:[/bold]")
    console.print(
        Panel(
            item.acceptance_criteria or "[dim](empty - required field)[/dim]",
            border_style="dim" if not item.acceptance_criteria else "cyan",
        )
    )


def _print_refine_body_preview(item: BacklogItem) -> None:
    console.print("\n[bold]Body:[/bold]")
    body_content = item.body_markdown[:1000] + "..." if len(item.body_markdown) > 1000 else item.body_markdown
    console.print(
        Panel(
            body_content if body_content.strip() else "[dim](empty - required field)[/dim]",
            border_style="dim" if not body_content.strip() else "cyan",
        )
    )


def _interactive_refine_item(
    options: dict[str, Any], state: dict[str, Any], item: BacklogItem, template: BacklogTemplate, comments: list[str]
) -> dict[str, Any]:
    prompt = state["refiner"].generate_refinement_prompt(item, template, comments=comments)
    console.print(f"[bold]Generating refinement prompt for template: {template.name}...[/bold]")
    console.print("\n[bold]Refinement Prompt for IDE AI Copilot:[/bold]")
    console.print(Panel(prompt, title="Copy this prompt to your IDE AI copilot"))
    refined_content = _read_refined_content_from_stdin()
    if refined_content == ":SKIP" or not refined_content.strip():
        console.print("[yellow]Skipping current item[/yellow]")
        return {"skipped": 1}
    if refined_content in (":QUIT", ":ABORT"):
        console.print("[yellow]Cancelling refinement session[/yellow]")
        return {"cancelled": True}
    try:
        refinement_result = state["refiner"].validate_and_score_refinement(
            refined_content, item.body_markdown, template, item
        )
    except ValueError as exc:
        console.print(f"[red]Validation failed: {exc}[/red]")
        return {"skipped": 1}
    _apply_refinement_result_to_item(item, refinement_result.refined_body)
    if _should_write_refined_item(options, refinement_result.confidence):
        item.apply_refinement()
        _write_refined_backlog_item(
            adapter_registry=state["adapter_registry"],
            connection=state["connection"],
            item=item,
            openspec_comment=options["openspec_comment"],
        )
    return {"refined": 1, "item": item}


def _apply_refinement_result_to_item(item: BacklogItem, refined_body: str) -> None:
    parsed = _parse_refinement_output_fields(refined_body)
    item.refined_body = parsed.get("body_markdown", refined_body)
    for attr in ("acceptance_criteria", "story_points", "business_value", "priority", "work_item_type"):
        if parsed.get(attr) is not None:
            setattr(item, attr, parsed[attr])


def _should_write_refined_item(options: dict[str, Any], confidence: float) -> bool:
    if not options["write"]:
        console.print("[yellow]Preview mode: Use --write to update backlog[/yellow]")
        return False
    if options["auto_accept_high_confidence"] and confidence >= 0.85:
        console.print("[green]Auto-accepting high-confidence refinement and writing to backlog[/green]")
        return True
    console.print()
    return Confirm.ask("Accept refinement and write to backlog?", default=False)


def _handle_refine_bundle_import(options: dict[str, Any], refined_items: list[BacklogItem]) -> None:
    if not (options["bundle"] or options["auto_bundle"]) or not refined_items:
        return
    console.print("\n[bold]OpenSpec Bundle Import:[/bold]")
    try:
        bundle_path = _resolve_refine_bundle_path(options)
        config_path = _resolve_bundle_mapping_config_path()
        available_ids = _derive_available_bundle_ids(bundle_path if bundle_path and bundle_path.exists() else None)
        mapped = _apply_bundle_mappings_for_items(
            items=refined_items, available_bundle_ids=available_ids, config_path=config_path
        )
        if mapped:
            console.print(
                f"[green]Mapped {len(mapped)}/{len(refined_items)} refined item(s) using confidence routing.[/green]"
            )
            for item_id, selected_bundle in mapped.items():
                console.print(f"[dim]- {item_id} -> {selected_bundle}[/dim]")
        elif _load_bundle_mapper_runtime_dependencies() is None:
            console.print("[yellow]⚠ bundle-mapper module not available; skipping runtime mapping flow.[/yellow]")
        else:
            console.print("[yellow]⚠ No bundle assignments were selected.[/yellow]")
    except Exception as exc:
        console.print(f"[yellow]⚠ Failed to import to OpenSpec bundle: {exc}[/yellow]")


def _resolve_refine_bundle_path(options: dict[str, Any]) -> Path | None:
    if options["bundle"]:
        return Path(options["bundle"])
    path = Path.cwd() / ".specfact" / "bundle.yaml"
    return path if path.exists() else Path.cwd() / "bundle.yaml"


def _print_refine_summary(options: dict[str, Any], result: dict[str, Any]) -> None:
    console.print("\n[bold]Summary:[/bold]")
    if result["cancelled"]:
        console.print("[yellow]Session cancelled by user[/yellow]")
    if options["limit"]:
        console.print(f"[dim]Limit applied: {options['limit']} items[/dim]")
    if options["first_issues"] is not None:
        console.print(f"[dim]Issue window applied: first {options['first_issues']} items[/dim]")
    if options["last_issues"] is not None:
        console.print(f"[dim]Issue window applied: last {options['last_issues']} items[/dim]")
    console.print(f"[green]Refined: {result['refined_count']}[/green]")
    console.print(f"[yellow]Skipped: {result['skipped_count']}[/yellow]")


@app.command("init-config")
@beartype
def init_config(
    force: bool = typer.Option(False, "--force", help="Overwrite existing .specfact/backlog-config.yaml"),
) -> None:
    """Scaffold `.specfact/backlog-config.yaml` with default backlog provider config structure."""
    cfg, path = _load_backlog_module_config_file()
    if path.exists() and not force:
        console.print(f"[yellow]⚠[/yellow] Config already exists: {path}")
        console.print("[dim]Use --force to overwrite or run `specfact backlog map-fields` to update mappings.[/dim]")
        return

    default_config: dict[str, Any] = {
        "backlog_config": {
            "providers": {
                "github": {
                    "adapter": "github",
                    "project_id": "",
                    "settings": {
                        "github_issue_types": {
                            "type_ids": {},
                        }
                    },
                },
                "ado": {
                    "adapter": "ado",
                    "project_id": "",
                    "settings": {
                        "framework": "default",
                        "field_mapping_file": ".specfact/templates/backlog/field_mappings/ado_custom.yaml",
                    },
                },
            }
        }
    }

    if cfg and not force:
        # unreachable due earlier return, keep for safety
        default_config = cfg

    _save_backlog_module_config_file(default_config if force or not cfg else cfg, path)
    console.print(f"[green]✓[/green] Backlog config initialized: {path}")
    console.print("[dim]Next: run `specfact backlog map-fields` to configure provider mappings.[/dim]")


@app.command("map-fields")
@beartype
def map_fields(
    ctx: click.Context,
    ado_org: str | None = typer.Option(None, "--ado-org", help="Azure DevOps organization"),
    ado_project: str | None = typer.Option(None, "--ado-project", help="Azure DevOps project"),
    ado_token: str | None = typer.Option(None, "--ado-token", help="Azure DevOps PAT"),
    ado_base_url: str | None = typer.Option(None, "--ado-base-url", help="Azure DevOps base URL"),
    ado_framework: str | None = typer.Option(None, "--ado-framework", help="ADO process style/framework"),
    provider: list[str] = typer.Option(
        [], "--provider", help="Provider(s) to configure: ado, github", show_default=False
    ),
    github_project_id: str | None = typer.Option(None, "--github-project-id", help="GitHub owner/repo context"),
    github_project_v2_id: str | None = typer.Option(None, "--github-project-v2-id", help="GitHub ProjectV2 node ID"),
    github_type_field_id: str | None = typer.Option(
        None, "--github-type-field-id", help="GitHub ProjectV2 Type field ID"
    ),
    github_type_option: list[str] = typer.Option(
        [], "--github-type-option", help="Type mapping '<type>=<option-id>'", show_default=False
    ),
    reset: bool = typer.Option(False, "--reset", help="Reset custom field mapping to defaults"),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Auto-map fields without prompts"),
) -> None:
    # fmt: on
    """Configure backlog provider field mappings."""
    options = locals()
    options.pop("ctx", None)
    _run_map_fields_command(options)


def _run_map_fields_command(options: dict[str, Any]) -> None:
    selected = _normalize_map_field_providers(options)
    if "github" in selected and "ado" not in selected:
        console.print(
            "[yellow]GitHub field mapping setup is currently handled by repository issue type metadata.[/yellow]"
        )
        return
    _run_ado_map_fields(options)


def _normalize_map_field_providers(options: dict[str, Any]) -> list[str]:
    selected = _normalize_provider_values(options.get("provider") or [])
    if selected:
        return selected
    if options.get("github_project_id") or options.get("github_project_v2_id") or options.get("github_type_field_id"):
        return ["github"]
    if options.get("ado_org") or options.get("ado_project") or options.get("ado_token"):
        return ["ado"]
    if options.get("non_interactive"):
        console.print(
            "[red]Error:[/red] Non-interactive mode requires explicit provider selection (for example: --provider ado)."
        )
        raise typer.Exit(1)
    return ["ado"]


def _normalize_provider_values(raw_values: Any) -> list[str]:
    aliases = {"ado": "ado", "azure devops": "ado", "azure dev ops": "ado", "github": "github"}
    values = raw_values if isinstance(raw_values, list) else [raw_values]
    normalized: list[str] = []
    for raw in values:
        text = str(getattr(raw, "value", raw) or "").strip().lower().replace("-", " ").replace("_", " ")
        mapped = aliases.get(" ".join(text.split()))
        if mapped and mapped not in normalized:
            normalized.append(mapped)
    return normalized


def _run_ado_map_fields(options: dict[str, Any]) -> None:
    import base64

    import requests

    from specfact_backlog.backlog.auth_tokens import get_token

    token, auth_scheme = _resolve_ado_map_token(options, get_token)
    ado_org, ado_project = _resolve_ado_map_context(options)
    base_url = (options.get("ado_base_url") or "https://dev.azure.com").rstrip("/")
    headers = _ado_auth_headers(token, auth_scheme, base64)
    custom_mapping_file = Path.cwd() / ".specfact" / "templates" / "backlog" / "field_mappings" / "ado_custom.yaml"
    if _handle_ado_mapping_reset(options, custom_mapping_file):
        return
    existing_payload = _load_ado_existing_mapping(custom_mapping_file)
    fields = _fetch_ado_relevant_fields(requests, base_url, ado_org, ado_project, headers)
    work_item_types = _fetch_ado_work_item_types(requests, base_url, ado_org, ado_project, headers)
    selected_framework = _resolve_ado_map_framework(options, work_item_types)
    selected_type = _select_ado_work_item_type(options, work_item_types)
    metadata = _fetch_ado_work_item_metadata(requests, base_url, ado_org, ado_project, headers, selected_type)
    field_mappings = _build_ado_field_mappings(options, existing_payload, fields, metadata)
    _write_ado_custom_mapping(custom_mapping_file, existing_payload, selected_framework, field_mappings)
    _persist_ado_mapping_config(ado_org, ado_project, selected_framework, selected_type, metadata)
    console.print(f"[green]✓[/green] ADO field mapping saved to {custom_mapping_file}")


def _resolve_ado_map_token(options: dict[str, Any], get_token: Callable[..., Any]) -> tuple[str, str]:
    if options.get("ado_token"):
        return str(options["ado_token"]), "basic"
    if os.environ.get("AZURE_DEVOPS_TOKEN"):
        return str(os.environ["AZURE_DEVOPS_TOKEN"]), "basic"
    stored = get_token("azure-devops", allow_expired=False) or get_token("azure-devops", allow_expired=True)
    if isinstance(stored, dict) and stored.get("access_token"):
        token_type = str(stored.get("token_type") or "bearer").lower()
        return str(stored["access_token"]), "bearer" if token_type == "bearer" else "basic"
    console.print("[red]Error:[/red] Azure DevOps token required")
    raise typer.Exit(1)


def _resolve_ado_map_context(options: dict[str, Any]) -> tuple[str, str]:
    ado_org = options.get("ado_org") or typer.prompt("Azure DevOps organization", default="").strip() or None
    ado_project = options.get("ado_project") or typer.prompt("Azure DevOps project", default="").strip() or None
    if not ado_org or not ado_project:
        console.print("[red]Error:[/red] Azure DevOps organization and project are required when configuring ado")
        raise typer.Exit(1)
    return str(ado_org), str(ado_project)


def _ado_auth_headers(token: str, auth_scheme: str, base64_module: Any) -> dict[str, str]:
    if auth_scheme == "bearer":
        return {"Authorization": f"Bearer {token}"}
    encoded = base64_module.b64encode(f":{token}".encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


def _handle_ado_mapping_reset(options: dict[str, Any], custom_mapping_file: Path) -> bool:
    if not options.get("reset"):
        return False
    if custom_mapping_file.exists():
        custom_mapping_file.unlink()
        console.print(f"[green]✓[/green] Reset custom field mapping (deleted {custom_mapping_file})")
    else:
        console.print("[yellow]⚠[/yellow] No custom mapping file found. Nothing to reset.")
    return True


def _load_ado_existing_mapping(custom_mapping_file: Path) -> dict[str, Any]:
    if not custom_mapping_file.exists():
        return {}
    try:
        payload = _load_owned_yaml_mapping_file(custom_mapping_file, artifact_name="ADO custom mapping file")
        console.print(f"[green]✓[/green] Loaded existing mapping from {custom_mapping_file}")
        return payload
    except ValueError as exc:
        console.print(f"[red]Error:[/red] Failed to load existing mapping safely: {exc}")
        raise typer.Exit(1) from exc


def _fetch_ado_relevant_fields(
    requests_module: Any, base_url: str, ado_org: str, ado_project: str, headers: dict[str, str]
) -> list[dict[str, Any]]:
    console.print("[cyan]Fetching fields from Azure DevOps...[/cyan]")
    url = f"{base_url}/{ado_org}/{ado_project}/_apis/wit/fields?api-version=7.1"
    response = requests_module.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    nodes = response.json().get("value", [])
    fields = [field for field in nodes if isinstance(field, dict) and _is_ado_relevant_field(field)]
    return sorted(fields, key=lambda field: field.get("referenceName", ""))


def _is_ado_relevant_field(field: dict[str, Any]) -> bool:
    ref_name = str(field.get("referenceName") or "")
    return (
        ref_name not in _ADO_SYSTEM_ONLY_FIELDS
        and not ref_name.startswith("System.History")
        and not ref_name.startswith("System.Watermark")
    )


def _fetch_ado_work_item_types(
    requests_module: Any, base_url: str, ado_org: str, ado_project: str, headers: dict[str, str]
) -> list[str]:
    url = f"{base_url}/{ado_org}/{ado_project}/_apis/wit/workitemtypes?api-version=7.1"
    response = requests_module.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return [
        str(node.get("name") or "").strip()
        for node in response.json().get("value", [])
        if isinstance(node, dict) and str(node.get("name") or "").strip()
    ]


def _resolve_ado_map_framework(options: dict[str, Any], work_item_types: list[str]) -> str:
    allowed = {"scrum", "agile", "safe", "kanban", "default"}
    selected = str(options.get("ado_framework") or "").strip().lower()
    if selected and selected not in allowed:
        console.print(
            f"[red]Error:[/red] Invalid --ado-framework '{selected}'. Expected one of: {', '.join(sorted(allowed))}"
        )
        raise typer.Exit(1)
    if selected:
        return selected
    names = {name.lower() for name in work_item_types}
    if "product backlog item" in names:
        return "scrum"
    if "capability" in names:
        return "safe"
    if "user story" in names:
        return "agile"
    return "default"


def _select_ado_work_item_type(options: dict[str, Any], work_item_types: list[str]) -> str:
    if not work_item_types:
        console.print("[red]Error:[/red] No Azure DevOps work item types were discovered")
        raise typer.Exit(1)
    if options.get("non_interactive"):
        return work_item_types[0]
    import questionary  # type: ignore[reportMissingImports]

    selected = questionary.select(
        "Select work item type for required-field metadata", choices=work_item_types, default=work_item_types[0]
    ).ask()
    return str(selected or work_item_types[0])


_ADO_SYSTEM_ONLY_FIELDS = {
    "System.Id",
    "System.Rev",
    "System.ChangedDate",
    "System.CreatedDate",
    "System.ChangedBy",
    "System.CreatedBy",
    "System.AreaId",
    "System.IterationId",
    "System.TeamProject",
    "System.NodeName",
    "System.AreaLevel1",
    "System.AreaLevel2",
    "System.AreaLevel3",
    "System.AreaLevel4",
    "System.AreaLevel5",
    "System.AreaLevel6",
    "System.AreaLevel7",
    "System.AreaLevel8",
    "System.AreaLevel9",
    "System.AreaLevel10",
    "System.IterationLevel1",
    "System.IterationLevel2",
    "System.IterationLevel3",
    "System.IterationLevel4",
    "System.IterationLevel5",
    "System.IterationLevel6",
    "System.IterationLevel7",
    "System.IterationLevel8",
    "System.IterationLevel9",
    "System.IterationLevel10",
}


def _fetch_ado_work_item_metadata(
    requests_module: Any, base_url: str, ado_org: str, ado_project: str, headers: dict[str, str], work_item_type: str
) -> dict[str, Any]:
    console.print(f"[cyan]Fetching required-field metadata for selected work item type: {work_item_type}[/cyan]")
    encoded_type = quote(work_item_type, safe="")
    url = f"{base_url}/{ado_org}/{ado_project}/_apis/wit/workitemtypes/{encoded_type}/fields?api-version=7.1"
    response = requests_module.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    nodes = response.json().get("value", [])
    return _collect_ado_work_item_metadata(requests_module, base_url, ado_org, ado_project, headers, nodes)


def _collect_ado_work_item_metadata(
    requests_module: Any, base_url: str, ado_org: str, ado_project: str, headers: dict[str, str], nodes: Any
) -> dict[str, Any]:
    metadata = {"required_refs": [], "allowed_values": {}, "field_types": {}, "unresolved_required": []}
    valid_nodes = [node for node in nodes if isinstance(node, dict)] if isinstance(nodes, list) else []
    follow_up_refs = [
        str(node.get("referenceName") or "").strip() for node in valid_nodes if _needs_ado_field_follow_up(node)
    ]
    request_context = {
        "requests": requests_module,
        "base_url": base_url,
        "ado_org": ado_org,
        "ado_project": ado_project,
        "headers": headers,
    }
    for node in valid_nodes:
        _collect_one_ado_work_item_field(request_context, node, metadata, follow_up_refs)
    return metadata


def _needs_ado_field_follow_up(node: dict[str, Any]) -> bool:
    ref_name = str(node.get("referenceName") or "").strip()
    return bool(
        ref_name
        and ref_name not in _ADO_SYSTEM_ONLY_FIELDS
        and not _extract_ado_allowed_values(node.get("allowedValues"))
    )


def _collect_one_ado_work_item_field(
    request_context: dict[str, Any], node: dict[str, Any], metadata: dict[str, Any], follow_up_refs: list[str]
) -> None:
    ref_name = str(node.get("referenceName") or "").strip()
    display_name = str(node.get("name") or ref_name or "<unknown>").strip()
    if bool(node.get("alwaysRequired")) and not ref_name:
        metadata["unresolved_required"].append(display_name)
    if not ref_name or ref_name in _ADO_SYSTEM_ONLY_FIELDS:
        return
    allowed_values = _extract_ado_allowed_values(node.get("allowedValues"))
    field_type = str(node.get("type") or "").strip().lower()
    if not allowed_values:
        allowed_values, resolved_type = _fetch_ado_field_details(
            request_context, ref_name, display_name, follow_up_refs
        )
        field_type = field_type or resolved_type
    if allowed_values:
        metadata["allowed_values"][ref_name] = allowed_values
    if field_type:
        metadata["field_types"][ref_name] = field_type
    if bool(node.get("alwaysRequired")):
        metadata["required_refs"].append(ref_name)


def _fetch_ado_field_details(
    request_context: dict[str, Any], ref_name: str, display_name: str, follow_up_refs: list[str]
) -> tuple[list[str], str]:
    index = follow_up_refs.index(ref_name) + 1 if ref_name in follow_up_refs else len(follow_up_refs)
    console.print(f"[cyan]Fetching field metadata details {index}/{len(follow_up_refs)}: {display_name}[/cyan]")
    base_url = str(request_context["base_url"])
    ado_org = str(request_context["ado_org"])
    ado_project = str(request_context["ado_project"])
    url = f"{base_url}/{ado_org}/{ado_project}/_apis/wit/fields/{quote(ref_name, safe='')}?api-version=7.1"
    try:
        response = request_context["requests"].get(url, headers=request_context["headers"], timeout=30)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return [], ""
    values = _extract_ado_allowed_values(payload.get("allowedValues"))
    if values:
        return values, str(payload.get("type") or "").strip().lower()
    picklist_id = str(payload.get("picklistId") or "").strip()
    return _fetch_ado_picklist_values(
        request_context["requests"], base_url, ado_org, request_context["headers"], picklist_id
    ), str(payload.get("type") or "").strip().lower()


def _fetch_ado_picklist_values(
    requests_module: Any, base_url: str, ado_org: str, headers: dict[str, str], picklist_id: str
) -> list[str]:
    if not picklist_id:
        return []
    url = f"{base_url}/{ado_org}/_apis/work/processes/lists/{quote(picklist_id, safe='')}?api-version=7.1"
    try:
        response = requests_module.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return _extract_ado_allowed_values(response.json().get("items"))
    except Exception:
        return []


def _extract_ado_allowed_values(raw_allowed: Any) -> list[str]:
    if not isinstance(raw_allowed, list):
        return []
    values: list[str] = []
    for entry in raw_allowed:
        value = str(entry.get("value") or entry.get("name") if isinstance(entry, dict) else entry or "").strip()
        if value and value not in values:
            values.append(value)
    return values


def _build_ado_field_mappings(
    options: dict[str, Any], existing_payload: dict[str, Any], fields: list[dict[str, Any]], metadata: dict[str, Any]
) -> dict[str, str]:
    if options.get("non_interactive") and metadata["unresolved_required"]:
        console.print(
            "Error: Non-interactive mode cannot map required field metadata; "
            "run interactive `specfact backlog map-fields`.",
            markup=False,
            soft_wrap=True,
        )
        raise typer.Exit(1)
    raw_existing = existing_payload.get("field_mappings")
    existing = raw_existing if isinstance(raw_existing, dict) else {}
    mappings = {str(key): str(value) for key, value in existing.items()}
    for field in fields:
        ref_name = str(field.get("referenceName") or "").strip()
        if ref_name and ref_name not in mappings:
            mappings[ref_name] = _ado_canonical_key(str(field.get("name") or ""), ref_name, mappings)
    return mappings


def _ado_canonical_key(field_name: str, fallback_ref: str, existing: dict[str, str]) -> str:
    source = (field_name or fallback_ref.split(".")[-1] or fallback_ref).strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", source).strip("_") or "custom_field"
    candidate = normalized
    index = 2
    while candidate in set(existing.values()):
        candidate = f"{normalized}_{index}"
        index += 1
    return candidate


def _write_ado_custom_mapping(
    custom_mapping_file: Path, existing_payload: dict[str, Any], framework: str, field_mappings: dict[str, str]
) -> None:
    payload = dict(existing_payload)
    payload["framework"] = framework
    payload["field_mappings"] = field_mappings
    payload.setdefault("work_item_type_mappings", existing_payload.get("work_item_type_mappings", {}))
    _write_yaml_mapping_file(custom_mapping_file, payload)


def _persist_ado_mapping_config(
    ado_org: str, ado_project: str, framework: str, selected_type: str, metadata: dict[str, Any]
) -> None:
    cfg, _path = _load_backlog_module_config_file()
    settings = (((cfg.get("backlog_config") or {}).get("providers") or {}).get("ado") or {}).get("settings") or {}
    allowed_by_type = dict(settings.get("allowed_values_by_work_item_type") or {})
    required_by_type = dict(settings.get("required_fields_by_work_item_type") or {})
    types_by_type = dict(settings.get("required_field_types_by_work_item_type") or {})
    allowed_by_type[selected_type] = {
        ref: values for ref, values in metadata["allowed_values"].items() if ref in metadata["required_refs"]
    }
    required_by_type[selected_type] = list(metadata["required_refs"])
    selected_types = {ref: value for ref, value in metadata["field_types"].items() if ref in metadata["required_refs"]}
    if selected_types:
        types_by_type[selected_type] = selected_types
    else:
        types_by_type.pop(selected_type, None)
    settings_update = {
        "framework": framework,
        "field_mapping_file": ".specfact/templates/backlog/field_mappings/ado_custom.yaml",
        "selected_work_item_type": selected_type,
        "required_fields_by_work_item_type": required_by_type,
        "allowed_values_by_work_item_type": _ReplaceSettingValue(allowed_by_type),
        "required_field_types_by_work_item_type": _ReplaceSettingValue(types_by_type),
    }
    _upsert_backlog_provider_settings("ado", settings_update, project_id=f"{ado_org}/{ado_project}", adapter="ado")
