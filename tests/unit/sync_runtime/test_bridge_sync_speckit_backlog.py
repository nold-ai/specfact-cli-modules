"""Speckit-specific bridge sync tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from specfact_cli.models.bridge import AdapterType, BridgeConfig
from specfact_cli.models.change import ChangeProposal, ChangeTracking
from specfact_cli.models.plan import Product
from specfact_cli.models.project import BundleManifest, BundleVersions, ProjectBundle
from specfact_cli.models.source_tracking import SourceTracking
from specfact_cli.utils.bundle_loader import save_project_bundle
from specfact_cli.utils.structure import SpecFactStructure

from specfact_project.sync_runtime.bridge_probe import BridgeProbe
from specfact_project.sync_runtime.bridge_sync import BridgeSync


def test_parse_source_tracking_entry_supports_ado_ref(tmp_path: Path) -> None:
    """ADO work item refs are parsed from markdown source-tracking entries."""
    sync = BridgeSync(tmp_path, bridge_config=BridgeConfig(adapter=AdapterType.SPECKIT, artifacts={}))

    entry = sync._parse_source_tracking_entry(  # pylint: disable=protected-access
        """- **Ado Issue**: AB#456
- **Issue URL**: https://dev.azure.com/example/project/_workitems/edit/456
""",
        repo_name=None,
    )

    assert entry is not None
    assert entry["source_id"] == "AB#456"
    assert entry["source_ref"] == "AB#456"


def test_detect_speckit_backlog_mappings_for_proposal(tmp_path: Path, monkeypatch) -> None:
    """Bridge sync imports issue refs from matching Spec-Kit features."""
    feature_dir = tmp_path / "specs" / "001-auth-sync"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "tasks.md").write_text("# Tasks\n\n- [ ] [T001] Link to AB#456\n", encoding="utf-8")
    sync = BridgeSync(tmp_path, bridge_config=BridgeConfig(adapter=AdapterType.SPECKIT, artifacts={}))
    monkeypatch.setattr(
        BridgeProbe,
        "detect",
        lambda _self: SimpleNamespace(
            tool="speckit",
            supported_sync_modes=["bidirectional"],
            extensions=["azure-devops"],
            extension_commands={"azure-devops": ["/speckit.ado.push"]},
        ),
    )

    mappings = sync._detect_speckit_backlog_mappings_for_proposal("auth-sync", "ado")  # pylint: disable=protected-access

    assert len(mappings) == 1
    assert mappings[0]["source_type"] == "ado"
    assert mappings[0]["source_ref"] == "AB#456"
    assert mappings[0]["source_metadata"]["speckit_feature"] == "001-auth-sync"


def test_export_backlog_from_bundle_skips_duplicate_creation_from_speckit_mapping(tmp_path: Path, monkeypatch) -> None:
    """Imported Spec-Kit backlog mappings prevent duplicate backlog creation."""
    bundle_dir = SpecFactStructure.project_dir(base_path=tmp_path, bundle_name="demo")
    manifest = BundleManifest(
        versions=BundleVersions(schema="1.1", project="0.1.0"),
        schema_metadata=None,
        project_metadata=None,
    )
    project_bundle = ProjectBundle(
        manifest=manifest,
        bundle_name="demo",
        product=Product(),
        change_tracking=ChangeTracking(
            proposals={
                "auth-sync": ChangeProposal(
                    name="auth-sync",
                    title="Auth Sync",
                    description="Sync auth state",
                    rationale="Needed for bridge tests",
                    timeline=None,
                    owner=None,
                    created_at="2026-03-28T00:00:00+00:00",
                    applied_at=None,
                    archived_at=None,
                    source_tracking=SourceTracking(tool="github", source_metadata={}),
                )
            }
        ),
    )
    save_project_bundle(project_bundle, bundle_dir, atomic=True)

    fake_adapter = MagicMock()
    fake_adapter.repo_owner = "octo"
    fake_adapter.repo_name = "repo"
    fake_adapter.generate_bridge_config.return_value = BridgeConfig(adapter=AdapterType.GITHUB, artifacts={})
    monkeypatch.setattr(
        "specfact_project.sync_runtime.bridge_sync.AdapterRegistry.get_adapter", lambda *_args, **_kwargs: fake_adapter
    )

    sync = BridgeSync(tmp_path, bridge_config=BridgeConfig(adapter=AdapterType.SPECKIT, artifacts={}))
    monkeypatch.setattr(
        sync,
        "_detect_speckit_backlog_mappings_for_proposal",
        lambda _proposal_name, _adapter_type: [
            {
                "source_type": "github",
                "source_id": "123",
                "source_ref": "#123",
                "source_repo": "octo/repo",
                "source_metadata": {"last_synced_status": "proposed"},
            }
        ],
    )

    result = sync.export_backlog_from_bundle(adapter_type="github", bundle_name="demo")

    assert result.success is True
    assert not result.operations
    fake_adapter.export_artifact.assert_not_called()
