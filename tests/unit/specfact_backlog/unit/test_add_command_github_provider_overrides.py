"""Regression tests for GitHub provider-field overrides in backlog add."""

from __future__ import annotations

from pathlib import Path

from specfact_cli.adapters.registry import AdapterRegistry

from specfact_backlog.backlog_core.main import backlog_app
from tests.unit.specfact_backlog.unit.test_add_command import _FakeAdapter, runner


GITHUB_PROJECT_ID = "nold-ai/specfact-demo-repo"


def _write_github_backlog_config(tmp_path: Path) -> None:
    spec_dir = tmp_path / ".specfact"
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "backlog-config.yaml").write_text(
        """
backlog_config:
  providers:
    github:
      adapter: github
      project_id: nold-ai/specfact-demo-repo
      settings:
        provider_fields:
          github_project_v2:
            project_id: PVT_PROJECT_SPEC
            type_field_id: PVT_FIELD_TYPE_SPEC
            type_option_ids:
              task: PVT_OPTION_TASK_SPEC
        github_issue_types:
          type_ids:
            task: IT_TASK_SPEC
""".strip(),
        encoding="utf-8",
    )


def _build_github_add_args(*extra: str) -> list[str]:
    return [
        "add",
        "--project-id",
        GITHUB_PROJECT_ID,
        "--adapter",
        "github",
        "--template",
        "github_projects",
        "--type",
        "task",
        "--title",
        "Implement task",
        "--body",
        "Body",
        *extra,
    ]


def _invoke_github_add(monkeypatch, tmp_path: Path, args: list[str]) -> list[dict]:
    created_payloads: list[dict] = []
    adapter = _FakeAdapter(items=[], relationships=[], created=created_payloads)
    monkeypatch.setattr(AdapterRegistry, "get_adapter", lambda _adapter: adapter)
    result = runner.invoke(backlog_app, args)
    assert result.exit_code == 0
    assert created_payloads
    return created_payloads


def test_backlog_add_github_provider_field_override_replaces_issue_type_mapping(monkeypatch, tmp_path: Path) -> None:
    """GitHub add should let CLI provider-field overrides replace resolved issue type metadata."""
    _write_github_backlog_config(tmp_path)

    created_payloads = _invoke_github_add(
        monkeypatch,
        tmp_path,
        _build_github_add_args(
            "--provider-field",
            "github_issue_types.type_ids.task=IT_TASK_OVERRIDE",
            "--non-interactive",
            "--repo-path",
            str(tmp_path),
        ),
    )
    provider_fields = created_payloads[0].get("provider_fields")
    assert isinstance(provider_fields, dict)
    github_issue_types = provider_fields.get("github_issue_types")
    assert isinstance(github_issue_types, dict)
    assert github_issue_types.get("type_ids", {}).get("task") == "IT_TASK_OVERRIDE"


def test_backlog_add_github_provider_field_override_replaces_project_type_option(monkeypatch, tmp_path: Path) -> None:
    """GitHub add should let CLI provider-field overrides replace resolved ProjectV2 type option metadata."""
    _write_github_backlog_config(tmp_path)

    created_payloads = _invoke_github_add(
        monkeypatch,
        tmp_path,
        _build_github_add_args(
            "--provider-field",
            "github_project_v2.type_option_ids.task=PVT_OPTION_TASK_OVERRIDE",
            "--non-interactive",
            "--repo-path",
            str(tmp_path),
        ),
    )
    provider_fields = created_payloads[0].get("provider_fields")
    assert isinstance(provider_fields, dict)
    github_project_v2 = provider_fields.get("github_project_v2")
    assert isinstance(github_project_v2, dict)
    assert github_project_v2.get("type_option_ids", {}).get("task") == "PVT_OPTION_TASK_OVERRIDE"
