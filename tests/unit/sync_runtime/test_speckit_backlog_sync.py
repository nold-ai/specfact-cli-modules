"""Tests for Spec-Kit backlog extension issue discovery."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from specfact_project.sync_runtime.speckit_backlog_sync import SpecKitBacklogSync


def _write_tasks(feature_dir: Path, content: str) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "tasks.md").write_text(content, encoding="utf-8")


def test_detect_issue_mappings_for_jira(tmp_path: Path) -> None:
    """Jira issue refs are discovered when the extension is active."""
    feature_dir = tmp_path / "specs" / "001-auth"
    _write_tasks(feature_dir, "# Tasks\n\n- [ ] [T001] Create ticket PROJ-123 before implementation\n")
    capabilities = SimpleNamespace(extensions=["jira"], extension_commands={"jira": ["/speckit.jira.push"]})

    mappings = SpecKitBacklogSync().detect_issue_mappings(feature_dir, capabilities)

    assert len(mappings) == 1
    assert mappings[0].tool == "jira"
    assert mappings[0].issue_ref == "PROJ-123"
    assert mappings[0].source == "speckit-extension"


def test_detect_issue_mappings_for_ado_and_github(tmp_path: Path) -> None:
    """ADO and GitHub patterns are both detected when their extensions are active."""
    feature_dir = tmp_path / "specs" / "001-auth"
    _write_tasks(
        feature_dir,
        "# Tasks\n\n- [ ] [T001] Track work in AB#456 and reference GitHub issue #89 for public visibility\n",
    )
    capabilities = SimpleNamespace(
        extensions=["azure-devops", "github"],
        extension_commands={"azure-devops": ["/speckit.ado.push"], "github": ["/speckit.github.push"]},
    )

    mappings = SpecKitBacklogSync().detect_issue_mappings(feature_dir, capabilities)

    refs = {(mapping.tool, mapping.issue_ref) for mapping in mappings}
    assert ("ado", "AB#456") in refs
    assert ("github", "#89") in refs


def test_detect_issue_mappings_returns_empty_without_backlog_extension(tmp_path: Path) -> None:
    """No active backlog extension means no scanning result."""
    feature_dir = tmp_path / "specs" / "001-auth"
    _write_tasks(feature_dir, "# Tasks\n\n- [ ] [T001] Mention PROJ-123 but do not import it\n")
    capabilities = SimpleNamespace(extensions=["reconcile"], extension_commands={"reconcile": ["/speckit.reconcile"]})

    mappings = SpecKitBacklogSync().detect_issue_mappings(feature_dir, capabilities)

    assert not mappings
