"""Tests for `specfact sync bridge --mode change-proposal`."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from specfact_cli.models.capabilities import ToolCapabilities

from specfact_project.sync import commands as sync_commands
from specfact_project.sync_runtime.bridge_probe import BridgeProbe


class _FakeAdapter:
    """Minimal adapter stub for sync bridge tests."""

    def get_capabilities(self, _repo: Path, _bridge_config: object | None = None) -> object:
        return SimpleNamespace(supported_sync_modes=["bidirectional"])


def _write_feature(feature_dir: Path) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text(
        """---
**Feature Branch**: `001-auth-sync`
**Created**: 2026-03-28
**Status**: Draft
---

# Feature Specification: Authentication Sync

## Functional Requirements

**FR-001**: System MUST sync authenticated sessions
""",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text("# Tasks\n\n- [ ] [T001] Build auth sync\n", encoding="utf-8")


def test_detect_sync_profile_defaults_to_solo(tmp_path: Path) -> None:
    """Missing profile metadata falls back to the solo behavior."""
    assert sync_commands._detect_sync_profile(tmp_path) == "solo"  # pylint: disable=protected-access


def test_detect_sync_profile_reads_repo_config(tmp_path: Path) -> None:
    """Profile metadata is read from .specfact/config.yaml when present."""
    config_path = tmp_path / ".specfact" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("profile: team\n", encoding="utf-8")

    assert sync_commands._detect_sync_profile(tmp_path) == "team"  # pylint: disable=protected-access


def test_sync_bridge_change_proposal_creates_single_change(tmp_path: Path, monkeypatch) -> None:
    """Direct sync bridge invocation creates an OpenSpec change proposal for one feature."""
    repo_path = tmp_path
    _write_feature(repo_path / "specs" / "001-auth-sync")
    monkeypatch.setattr(sync_commands.AdapterRegistry, "is_registered", lambda _: True)
    monkeypatch.setattr(sync_commands.AdapterRegistry, "get_adapter", lambda *_args, **_kwargs: _FakeAdapter())
    monkeypatch.setattr(
        BridgeProbe,
        "detect",
        lambda _self: ToolCapabilities(tool="speckit", supported_sync_modes=["bidirectional"]),
    )
    monkeypatch.setattr(BridgeProbe, "auto_generate_bridge", lambda _self, _caps: None)

    sync_commands.sync_bridge(
        repo=repo_path,
        bundle=None,
        bidirectional=False,
        mode="change-proposal",
        feature="001-auth-sync",
        all_features=False,
        overwrite=False,
        watch=False,
        ensure_compliance=False,
        adapter="speckit",
        repo_owner=None,
        repo_name=None,
        external_base_path=None,
        github_token=None,
        use_gh_cli=True,
        ado_org=None,
        ado_project=None,
        ado_base_url=None,
        ado_token=None,
        ado_work_item_type=None,
        sanitize=None,
        target_repo=None,
        interactive=False,
        change_ids=None,
        backlog_ids=None,
        backlog_ids_file=None,
        export_to_tmp=False,
        import_from_tmp=False,
        tmp_file=None,
        update_existing=False,
        track_code_changes=False,
        add_progress_comment=False,
        code_repo=None,
        include_archived=False,
        interval=5,
    )

    proposal_path = repo_path / "openspec" / "changes" / "auth-sync" / "proposal.md"
    assert proposal_path.exists()
    assert "<!-- speckit_feature: 001-auth-sync -->" in proposal_path.read_text(encoding="utf-8")


def test_sync_bridge_change_proposal_all_skips_tracked_features(tmp_path: Path, monkeypatch) -> None:
    """Bulk change-proposal sync skips features already tracked by an OpenSpec proposal marker."""
    repo_path = tmp_path
    _write_feature(repo_path / "specs" / "001-auth-sync")
    _write_feature(repo_path / "specs" / "002-payments")
    tracked_dir = repo_path / "openspec" / "changes" / "auth-sync"
    tracked_dir.mkdir(parents=True, exist_ok=True)
    (tracked_dir / "proposal.md").write_text(
        "# Change: Authentication Sync\n\n<!-- speckit_feature: 001-auth-sync -->\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sync_commands.AdapterRegistry, "is_registered", lambda _: True)
    monkeypatch.setattr(sync_commands.AdapterRegistry, "get_adapter", lambda *_args, **_kwargs: _FakeAdapter())
    monkeypatch.setattr(
        BridgeProbe,
        "detect",
        lambda _self: ToolCapabilities(tool="speckit", supported_sync_modes=["bidirectional"]),
    )
    monkeypatch.setattr(BridgeProbe, "auto_generate_bridge", lambda _self, _caps: None)

    sync_commands.sync_bridge(
        repo=repo_path,
        bundle=None,
        bidirectional=False,
        mode="change-proposal",
        feature=None,
        all_features=True,
        overwrite=False,
        watch=False,
        ensure_compliance=False,
        adapter="speckit",
        repo_owner=None,
        repo_name=None,
        external_base_path=None,
        github_token=None,
        use_gh_cli=True,
        ado_org=None,
        ado_project=None,
        ado_base_url=None,
        ado_token=None,
        ado_work_item_type=None,
        sanitize=None,
        target_repo=None,
        interactive=False,
        change_ids=None,
        backlog_ids=None,
        backlog_ids_file=None,
        export_to_tmp=False,
        import_from_tmp=False,
        tmp_file=None,
        update_existing=False,
        track_code_changes=False,
        add_progress_comment=False,
        code_repo=None,
        include_archived=False,
        interval=5,
    )

    assert (repo_path / "openspec" / "changes" / "payments" / "proposal.md").exists()
    assert not (repo_path / "openspec" / "changes" / "001-auth-sync" / "proposal.md").exists()
