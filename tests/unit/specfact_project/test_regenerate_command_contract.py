from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from typer.testing import CliRunner

from specfact_project.project import commands


runner = CliRunner()


class _ProjectMetadata:
    def get_extension(self, namespace: str, key: str) -> dict[str, str] | None:
        if namespace == "backlog_core" and key == "backlog_config":
            return {"adapter": "github", "project_id": "owner/repo", "template": "github_projects"}
        return None


@dataclass
class _Manifest:
    project_metadata: _ProjectMetadata


@dataclass
class _Bundle:
    manifest: _Manifest
    features: list[str]


def test_project_regenerate_reports_typed_null_backlog_graph(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Null backlog graph data should produce a typed diagnostic, not a raw NoneType crash."""
    monkeypatch.setattr(
        commands, "_resolve_bundle", lambda repo, bundle: ("demo", tmp_path / ".specfact/projects/demo")
    )
    monkeypatch.setattr(
        commands,
        "_load_bundle_with_progress",
        lambda bundle_dir, validate_hashes=False: _Bundle(_Manifest(_ProjectMetadata()), ["FEATURE-1"]),
    )
    monkeypatch.setattr(
        commands, "_resolve_linked_backlog_config", lambda bundle_obj: ("github", "owner/repo", "github_projects")
    )
    monkeypatch.setattr(commands, "_fetch_backlog_graph", lambda **kwargs: None)

    result = runner.invoke(commands.app, ["regenerate", "--repo", str(tmp_path), "--bundle", "demo"])

    assert result.exit_code == 1
    assert "Backlog graph data unavailable" in result.stdout
    assert "specfact backlog analyze-deps" in result.stdout
    assert "NoneType" not in result.stdout
    assert not isinstance(result.exception, AttributeError)
