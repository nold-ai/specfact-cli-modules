from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from pytest import MonkeyPatch
from specfact_cli.models.bridge import AdapterType

from specfact_project.sync_runtime.bridge_sync_export_ecd_prepare import ecd_resolve_adapter_instance
from specfact_project.sync_runtime.bridge_sync_parse_source_tracking_entry_impl import run_parse_source_tracking_entry
from specfact_project.sync_runtime.speckit_bridge_backlog import (
    detect_speckit_backlog_mappings,
    infer_backlog_repo_identifier,
)
from specfact_project.sync_runtime.sync_bridge_phases import _export_only_backlog_bundle
from specfact_project.sync_runtime.sync_command_common import is_test_mode
from specfact_project.sync_runtime.sync_perform_operation_impl import _pso_maybe_bootstrap_constitution


def test_parse_source_tracking_entry_only_uses_structured_source_repo_field() -> None:
    entry = run_parse_source_tracking_entry(
        bridge=object(),
        entry_content=(
            "- source_repo is mentioned in prose and should not be parsed\n"
            "source_repo: nold-ai/specfact-cli-modules\n"
            "- **GitHub Issue**: #116\n"
        ),
        repo_name=None,
    )

    assert entry is not None
    assert entry["source_repo"] == "nold-ai/specfact-cli-modules"


def test_is_test_mode_does_not_false_match_latest(monkeypatch) -> None:
    monkeypatch.delenv("TEST_MODE", raising=False)
    monkeypatch.setattr(sys, "argv", ["specfact", "--latest"])
    monkeypatch.delitem(sys.modules, "pytest", raising=False)

    assert is_test_mode() is False


def test_pso_maybe_bootstrap_constitution_reports_valid_file(tmp_path: Path) -> None:
    constitution_path = tmp_path / ".specify" / "memory" / "constitution.md"
    constitution_path.parent.mkdir(parents=True, exist_ok=True)
    constitution_path.write_text("# Constitution\n", encoding="utf-8")

    printed: list[str] = []
    console = SimpleNamespace(print=_append_message(printed))
    monkeypatch_target = "specfact_cli.utils.bundle_converters.is_constitution_minimal"

    monkeypatch = MonkeyPatch()
    monkeypatch.setattr(monkeypatch_target, _constitution_not_minimal)

    try:
        _pso_maybe_bootstrap_constitution(tmp_path, AdapterType.SPECKIT, console)
    finally:
        monkeypatch.undo()

    assert any("Constitution found and validated" in message for message in printed)


def test_ecd_resolve_adapter_instance_uses_registry_public_api(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_is_registered(adapter_name: str) -> bool:
        calls.append(("is_registered", adapter_name))
        return True

    def fake_get_adapter(adapter_name: str, **kwargs):
        calls.append(("get_adapter", adapter_name))
        return {"adapter_name": adapter_name, "kwargs": kwargs}

    monkeypatch.setattr("specfact_cli.adapters.registry.AdapterRegistry.is_registered", fake_is_registered)
    monkeypatch.setattr("specfact_cli.adapters.registry.AdapterRegistry.get_adapter", fake_get_adapter)

    adapter = ecd_resolve_adapter_instance(
        adapter_type="github",
        repo_owner="nold-ai",
        repo_name="specfact-cli-modules",
        api_token="token",
        use_gh_cli=False,
        ado_org=None,
        ado_project=None,
        ado_base_url=None,
        ado_work_item_type=None,
        errors=[],
    )

    assert calls == [("is_registered", "github"), ("get_adapter", "github")]
    assert adapter is not None
    assert adapter["kwargs"]["repo_owner"] == "nold-ai"


def test_infer_backlog_repo_identifier_supports_ado_https(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="https://dev.azure.com/org-name/project-name/_git/repo-name\n",
            stderr="",
        ),
    )

    assert infer_backlog_repo_identifier(tmp_path, "ado") == "org-name/project-name"


def test_detect_speckit_backlog_mappings_resolves_repo_identifier_once(monkeypatch, tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-auth-sync"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "tasks.md").write_text("# Tasks\n\n- [ ] [T001] Link to #123 and #456\n", encoding="utf-8")

    call_count = 0

    def fake_infer_repo_identifier(repo_path: Path, adapter_type: str) -> str:
        nonlocal call_count
        _ = repo_path
        _ = adapter_type
        call_count += 1
        return "nold-ai/specfact-cli-modules"

    monkeypatch.setattr(
        "specfact_project.sync_runtime.speckit_bridge_backlog.infer_backlog_repo_identifier",
        fake_infer_repo_identifier,
    )
    monkeypatch.setattr(
        "specfact_project.sync_runtime.speckit_bridge_backlog.BridgeProbe.detect",
        lambda _self: SimpleNamespace(
            tool="speckit",
            extensions=["github"],
            extension_commands={"github": ["/speckit.github.push"]},
        ),
    )

    mappings = detect_speckit_backlog_mappings(tmp_path, "auth-sync", "github")

    assert len(mappings) == 2
    assert all(mapping["source_repo"] == "nold-ai/specfact-cli-modules" for mapping in mappings)
    assert call_count == 1


def test_export_only_backlog_bundle_can_infer_bundle_name(monkeypatch, tmp_path: Path) -> None:
    printed: list[str] = []
    console = SimpleNamespace(print=_append_message(printed))
    monkeypatch.setattr("specfact_project.sync_runtime.sync_bridge_phases.console", console)
    monkeypatch.setattr(
        "specfact_project.sync_runtime.sync_bridge_phases.infer_bundle_name",
        _infer_demo_bundle_name,
    )

    class _FakeResult:
        success = True
        operations = [object()]
        warnings: list[str] = []
        errors: list[str] = []

    bridge_sync = cast(Any, SimpleNamespace(export_backlog_from_bundle=lambda **kwargs: _FakeResult()))

    handled = _export_only_backlog_bundle(
        repo=tmp_path,
        adapter_value="github",
        bundle=None,
        bridge_sync=bridge_sync,
        github_token=None,
        ado_token=None,
        repo_owner="nold-ai",
        repo_name="specfact-cli-modules",
        use_gh_cli=False,
        ado_org=None,
        ado_project=None,
        ado_base_url=None,
        ado_work_item_type=None,
        update_existing=False,
        change_ids_list=None,
    )

    assert handled is True
    assert any("demo-bundle" in message for message in printed)


def _constitution_not_minimal(path: Path) -> bool:
    _ = path
    return False


def _infer_demo_bundle_name(repo: Path) -> str:
    _ = repo
    return "demo-bundle"


def _append_message(messages: list[str]):
    def _record(message: str) -> None:
        messages.append(message)

    return _record
