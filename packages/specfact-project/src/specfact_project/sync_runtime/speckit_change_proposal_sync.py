"""Helpers for syncing Spec-Kit features into OpenSpec change proposals."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import typer
from beartype import beartype
from icontract import ensure

from specfact_project.importers.speckit_converter import SpecKitConverter


@beartype
@ensure(lambda result: isinstance(result, str), "Must return string")
def detect_sync_profile(repo: Path) -> str:
    """Detect the lightweight sync profile for Spec-Kit proposal import."""
    profile_path = repo / ".specfact" / "config.yaml"
    if not profile_path.exists():
        return "solo"

    content = profile_path.read_text(encoding="utf-8")
    match = re.search(r"^\s*profile:\s*(\w+)\s*$", content, re.MULTILINE)
    return match.group(1).strip().lower() if match else "solo"


@beartype
@ensure(lambda result: isinstance(result, list), "Must return list")
def iter_speckit_feature_dirs(repo: Path) -> list[Path]:
    """Return Spec-Kit feature directories containing a spec.md file."""
    specs_dir = repo / "specs"
    if not specs_dir.exists():
        return []
    return sorted(path for path in specs_dir.iterdir() if path.is_dir() and (path / "spec.md").exists())


@beartype
@ensure(lambda result: isinstance(result, set), "Must return set")
def existing_speckit_change_sources(repo: Path) -> set[str]:
    """Collect already tracked Spec-Kit features from existing OpenSpec changes."""
    changes_dir = repo / "openspec" / "changes"
    if not changes_dir.exists():
        return set()

    tracked: set[str] = set()
    for proposal_path in changes_dir.glob("*/proposal.md"):
        tracked.add(proposal_path.parent.name.lower())
        tracked.update(_extract_proposal_markers(proposal_path))
    return tracked


@beartype
@ensure(lambda result: isinstance(result, str), "Must return string")
def derive_change_name_from_feature_dir(feature_dir: Path) -> str:
    """Convert a numbered Spec-Kit feature directory into an OpenSpec change id."""
    return re.sub(r"^\d+-", "", feature_dir.name.lower())


@beartype
@ensure(lambda result: isinstance(result, list), "Must return list")
def sync_speckit_change_proposals(
    repo: Path,
    feature: str | None,
    all_features: bool,
    console: Any,
) -> list[Path]:
    """Create OpenSpec change proposals from one or more Spec-Kit features."""
    feature_dirs = iter_speckit_feature_dirs(repo)
    if not feature_dirs:
        console.print("[bold red]✗[/bold red] No Spec-Kit features found under specs/")
        raise typer.Exit(1)

    tracked_sources = existing_speckit_change_sources(repo)
    selected_features = _select_features(feature_dirs, tracked_sources, feature, all_features, console)
    if not selected_features:
        console.print("[yellow]⚠[/yellow] No untracked Spec-Kit features found")
        return []

    converter = SpecKitConverter(repo)
    created_changes = _create_changes(repo, converter, selected_features, tracked_sources)
    skipped_features = [path.name for path in selected_features if path not in {item[0] for item in created_changes}]

    _print_profile_notice(repo, skipped_features, console)
    if not created_changes:
        console.print("[yellow]⚠[/yellow] No new change proposals were created")
        return []

    created_paths = [change_dir for _, change_dir in created_changes]
    console.print(f"[bold green]✓[/bold green] Created {len(created_paths)} OpenSpec change proposal(s) from Spec-Kit")
    for change_dir in created_paths:
        console.print(f"[dim]  - {change_dir.relative_to(repo)}[/dim]")
    if skipped_features:
        console.print(f"[yellow]⚠[/yellow] Skipped already tracked features: {', '.join(skipped_features)}")
    return created_paths


@beartype
@ensure(lambda result: isinstance(result, set), "Must return set")
def _extract_proposal_markers(proposal_path: Path) -> set[str]:
    """Extract tracked Spec-Kit feature markers from an OpenSpec proposal."""
    content = proposal_path.read_text(encoding="utf-8")
    marker_match = re.search(r"<!--\s*speckit_feature:\s*(.+?)\s*-->", content)
    return {marker_match.group(1).strip().lower()} if marker_match else set()


@beartype
@ensure(lambda result: isinstance(result, list), "Must return list")
def _select_features(
    feature_dirs: list[Path],
    tracked_sources: set[str],
    feature: str | None,
    all_features: bool,
    console: Any,
) -> list[Path]:
    """Resolve the requested Spec-Kit features to convert."""
    if feature:
        selected = [path for path in feature_dirs if path.name == feature]
        if not selected:
            console.print(f"[bold red]✗[/bold red] Spec-Kit feature not found: {feature}")
            raise typer.Exit(1)
        return selected

    if not all_features:
        console.print("[bold red]✗[/bold red] Provide either --feature or --all with --mode change-proposal")
        raise typer.Exit(1)

    return [
        path
        for path in feature_dirs
        if path.name.lower() not in tracked_sources and derive_change_name_from_feature_dir(path) not in tracked_sources
    ]


@beartype
@ensure(lambda result: isinstance(result, list), "Must return list")
def _create_changes(
    repo: Path,
    converter: SpecKitConverter,
    selected_features: list[Path],
    tracked_sources: set[str],
) -> list[tuple[Path, Path]]:
    """Create change proposals for the selected feature directories."""
    changes_root = repo / "openspec" / "changes"
    created: list[tuple[Path, Path]] = []
    for feature_dir in selected_features:
        feature_source = feature_dir.name.lower()
        change_name = derive_change_name_from_feature_dir(feature_dir)
        if feature_source in tracked_sources or change_name in tracked_sources:
            continue
        change_dir = converter.convert_to_change_proposal(
            feature_path=feature_dir,
            change_name=change_name,
            output_dir=changes_root,
        )
        created.append((feature_dir, change_dir))
    return created


@beartype
def _print_profile_notice(repo: Path, skipped_features: list[str], console: Any) -> None:
    """Print a non-solo profile notice for skipped features."""
    profile = detect_sync_profile(repo)
    if profile == "solo" or not skipped_features:
        return
    console.print(
        "[yellow]⚠[/yellow] "
        f"Profile '{profile}' may require divergence review for skipped features: {', '.join(skipped_features)}"
    )
