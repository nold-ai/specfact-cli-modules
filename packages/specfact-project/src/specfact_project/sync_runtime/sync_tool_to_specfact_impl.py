"""
Implementation helpers for sync.commands._sync_tool_to_specfact (cyclomatic complexity reduction).
"""

# pylint: disable=import-outside-toplevel,protected-access,broad-except,too-many-positional-arguments,too-many-locals,line-too-long,unused-argument,too-many-instance-attributes,cyclic-import,consider-using-in

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from specfact_cli.models.plan import Feature, PlanBundle
from specfact_cli.models.project import BundleManifest, BundleVersions, ProjectBundle
from specfact_cli.utils.bundle_loader import load_project_bundle, save_project_bundle
from specfact_cli.utils.structure import SpecFactStructure
from specfact_cli.validators.schema import validate_plan_bundle

from specfact_project.generators.plan_generator import PlanGenerator
from specfact_project.utils.feature_keys import normalize_feature_key


def _stsf_load_existing_plan_bundle(
    repo: Path,
    plan_path: Path,
    progress: Any,
    task: int | None,
) -> tuple[PlanBundle | None, bool]:
    """Load and optionally dedupe existing plan bundle from disk."""
    is_modular_bundle = (plan_path.exists() and plan_path.is_dir()) or (
        not plan_path.exists() and plan_path.parent.name == "projects"
    )
    existing_bundle: PlanBundle | None = None

    if not plan_path.exists():
        return None, is_modular_bundle

    if task is not None:
        progress.update(task, description="[cyan]Validating existing plan bundle...[/cyan]")

    if plan_path.is_dir():
        from specfact_cli.utils.bundle_converters import convert_project_bundle_to_plan_bundle
        from specfact_cli.utils.progress import load_bundle_with_progress

        is_modular_bundle = True
        project_bundle = load_bundle_with_progress(
            plan_path,
            validate_hashes=False,
            console_instance=progress.console if hasattr(progress, "console") else None,
        )
        bundle = convert_project_bundle_to_plan_bundle(project_bundle)
        is_valid = True
    else:
        validation_result = validate_plan_bundle(plan_path)
        if isinstance(validation_result, tuple):
            is_valid, _error, bundle = validation_result
        else:
            is_valid = False
            bundle = None

    if not is_valid or not bundle:
        return None, is_modular_bundle

    existing_bundle = bundle
    _stsf_deduplicate_features_inplace(
        existing_bundle=existing_bundle,
        plan_path=plan_path,
        is_modular_bundle=is_modular_bundle,
        progress=progress,
        task=task,
    )
    return existing_bundle, is_modular_bundle


def _stsf_deduplicate_features_inplace(
    *,
    existing_bundle: PlanBundle,
    plan_path: Path,
    is_modular_bundle: bool,
    progress: Any,
    task: int | None,
) -> None:
    seen_normalized_keys: set[str] = set()
    deduplicated_features: list[Feature] = []
    for existing_feature in existing_bundle.features:
        normalized_key = normalize_feature_key(existing_feature.key)
        if normalized_key not in seen_normalized_keys:
            seen_normalized_keys.add(normalized_key)
            deduplicated_features.append(existing_feature)

    duplicates_removed = len(existing_bundle.features) - len(deduplicated_features)
    if duplicates_removed <= 0:
        return

    existing_bundle.features = deduplicated_features
    if task is not None:
        progress.update(
            task,
            description=(
                f"[cyan]Deduplicating {duplicates_removed} duplicate features and writing cleaned plan...[/cyan]"
            ),
        )
    if not is_modular_bundle:
        generator = PlanGenerator()
        generator.generate(existing_bundle, plan_path)
    if task is not None:
        progress.update(
            task,
            description=f"[green]✓[/green] Removed {duplicates_removed} duplicates, cleaned plan saved",
        )


def _stsf_get_or_create_project_bundle(repo: Path) -> tuple[ProjectBundle, str, Path]:
    bundle_name = SpecFactStructure.get_active_bundle_name(repo) or SpecFactStructure.DEFAULT_PLAN_NAME
    bundle_dir = repo / SpecFactStructure.PROJECTS / bundle_name
    bundle_dir.mkdir(parents=True, exist_ok=True)

    project_bundle: ProjectBundle | None = None
    if bundle_dir.exists() and (bundle_dir / "bundle.manifest.yaml").exists():
        try:
            project_bundle = load_project_bundle(bundle_dir, validate_hashes=False)
        except Exception:
            project_bundle = None

    if project_bundle is not None:
        return project_bundle, bundle_name, bundle_dir

    from specfact_cli.models.plan import Product

    from specfact_project.migrations.plan_migrator import get_latest_schema_version

    manifest = BundleManifest(
        versions=BundleVersions(schema=get_latest_schema_version(), project="0.1.0"),
        schema_metadata=None,
        project_metadata=None,
    )
    project_bundle = ProjectBundle(
        manifest=manifest,
        bundle_name=bundle_name,
        product=Product(themes=[], releases=[]),
        features={},
        idea=None,
        business=None,
        clarifications=None,
    )
    return project_bundle, bundle_name, bundle_dir


def _stsf_discovered_feature_list(adapter_instance: Any, bridge_config: Any, bridge_sync: Any, repo: Path) -> list[Any]:
    if hasattr(adapter_instance, "discover_features"):
        return adapter_instance.discover_features(repo, bridge_config)
    feature_ids = bridge_sync._discover_feature_ids()
    return [{"feature_key": fid} for fid in feature_ids]


def _stsf_run_import_loop(
    bridge_sync: Any,
    bridge_config: Any,
    discovered_features: list[Any],
    bundle_name: str,
    progress: Any,
    task: int | None,
) -> None:
    artifact_order = ["specification", "plan", "tasks"]
    for feature_data in discovered_features:
        feature_id = feature_data.get("feature_key", "")
        if not feature_id:
            continue
        for artifact_key in artifact_order:
            if artifact_key not in bridge_config.artifacts:
                continue
            try:
                result = bridge_sync.import_artifact(artifact_key, feature_id, bundle_name)
                if not result.success and task is not None and artifact_key == "specification":
                    progress.update(
                        task,
                        description=(
                            f"[yellow]⚠[/yellow] Failed to import {artifact_key} for {feature_id}: "
                            f"{result.errors[0] if result.errors else 'Unknown error'}"
                        ),
                    )
            except Exception as e:
                if task is not None and artifact_key == "specification":
                    progress.update(
                        task,
                        description=f"[yellow]⚠[/yellow] Error importing {artifact_key} for {feature_id}: {e}",
                    )


def _stsf_reload_bundle(bundle_dir: Path, bundle_name: str) -> ProjectBundle:
    project_bundle: ProjectBundle | None = None
    try:
        project_bundle = load_project_bundle(bundle_dir, validate_hashes=False)
        save_project_bundle(project_bundle, bundle_dir, atomic=True)
    except Exception:
        project_bundle = None

    try:
        return load_project_bundle(bundle_dir, validate_hashes=False)
    except Exception:
        if project_bundle is None:
            from specfact_cli.models.plan import Product

            from specfact_project.migrations.plan_migrator import get_latest_schema_version

            manifest = BundleManifest(
                versions=BundleVersions(schema=get_latest_schema_version(), project="0.1.0"),
                schema_metadata=None,
                project_metadata=None,
            )
            project_bundle = ProjectBundle(
                manifest=manifest,
                bundle_name=bundle_name,
                product=Product(themes=[], releases=[]),
                features={},
                idea=None,
                business=None,
                clarifications=None,
            )
            save_project_bundle(project_bundle, bundle_dir, atomic=True)
        return project_bundle


def _prefix_merge_feature(
    normalized_key: str,
    feature: Feature,
    normalized_key_map: dict[str, tuple[int, str]],
    existing_bundle: PlanBundle,
) -> bool:
    """Try prefix-based merge for Spec-Kit style keys. Returns True if merged."""
    for existing_norm_key, (existing_idx, original_key) in normalized_key_map.items():
        shorter = min(normalized_key, existing_norm_key, key=len)
        longer = max(normalized_key, existing_norm_key, key=len)
        has_speckit_key = bool(re.match(r"^\d{3}[_-]", feature.key) or re.match(r"^\d{3}[_-]", original_key))
        length_diff = len(longer) - len(shorter)
        length_ratio = len(shorter) / len(longer) if len(longer) > 0 else 1.0
        if (
            has_speckit_key
            and len(shorter) >= 10
            and longer.startswith(shorter)
            and length_diff >= 6
            and length_ratio < 0.75
        ):
            if len(existing_norm_key) >= len(normalized_key):
                feature.key = original_key
            else:
                existing_bundle.features[existing_idx].key = feature.key
            existing_bundle.features[existing_idx] = feature
            return True
    return False


def _stsf_merge_with_existing(
    converted_bundle: PlanBundle,
    existing_bundle: PlanBundle,
    plan_path: Path,
    is_modular_bundle: bool,
    progress: Any,
    task: int | None,
) -> tuple[PlanBundle, int, int]:
    if task is not None:
        progress.update(task, description="[cyan]Merging with existing plan bundle...[/cyan]")

    normalized_key_map: dict[str, tuple[int, str]] = {}
    for idx, existing_feature in enumerate(existing_bundle.features):
        nk = normalize_feature_key(existing_feature.key)
        if nk not in normalized_key_map:
            normalized_key_map[nk] = (idx, existing_feature.key)

    features_updated = 0
    features_added = 0
    for feature in converted_bundle.features:
        normalized_key = normalize_feature_key(feature.key)
        matched = False
        if normalized_key in normalized_key_map:
            existing_idx, original_key = normalized_key_map[normalized_key]
            feature.key = original_key
            existing_bundle.features[existing_idx] = feature
            features_updated += 1
            matched = True
        elif _prefix_merge_feature(normalized_key, feature, normalized_key_map, existing_bundle):
            features_updated += 1
            matched = True

        if not matched:
            existing_bundle.features.append(feature)
            features_added += 1

    themes_existing = set(existing_bundle.product.themes)
    themes_new = set(converted_bundle.product.themes)
    existing_bundle.product.themes = list(themes_existing | themes_new)

    if not is_modular_bundle:
        if task is not None:
            progress.update(task, description="[cyan]Writing plan bundle to disk...[/cyan]")
        generator = PlanGenerator()
        generator.generate(existing_bundle, plan_path)
    return existing_bundle, features_updated, features_added


def run_sync_tool_to_specfact(
    repo: Path,
    adapter_instance: Any,
    bridge_config: Any,
    bridge_sync: Any,
    progress: Any,
    task: int | None = None,
) -> tuple[PlanBundle, int, int]:
    """Sync tool artifacts to SpecFact format (adapter registry pattern)."""
    plan_path = SpecFactStructure.get_default_plan_path(repo)
    is_modular_bundle = (plan_path.exists() and plan_path.is_dir()) or (
        not plan_path.exists() and plan_path.parent.name == "projects"
    )

    existing_bundle, loaded_modular = _stsf_load_existing_plan_bundle(repo, plan_path, progress, task)
    is_modular_bundle = loaded_modular or is_modular_bundle

    if task is not None:
        progress.update(task, description="[cyan]Converting tool artifacts to SpecFact format...[/cyan]")

    project_bundle, bundle_name, bundle_dir = _stsf_get_or_create_project_bundle(repo)
    discovered = _stsf_discovered_feature_list(adapter_instance, bridge_config, bridge_sync, repo)
    _stsf_run_import_loop(bridge_sync, bridge_config, discovered, bundle_name, progress, task)

    project_bundle = _stsf_reload_bundle(bundle_dir, bundle_name)

    from specfact_cli.utils.bundle_converters import convert_project_bundle_to_plan_bundle

    converted_bundle = convert_project_bundle_to_plan_bundle(project_bundle)

    if existing_bundle:
        return _stsf_merge_with_existing(
            converted_bundle, existing_bundle, plan_path, is_modular_bundle, progress, task
        )

    if not is_modular_bundle:
        generator = PlanGenerator()
        generator.generate(converted_bundle, plan_path)
    return converted_bundle, 0, len(converted_bundle.features)
