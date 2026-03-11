"""Regression tests for ADO provider field forwarding in backlog add."""

from __future__ import annotations

import importlib
import os
from pathlib import Path

from specfact_cli.adapters.registry import AdapterRegistry

from specfact_backlog.backlog_core.main import backlog_app
from tests.unit.specfact_backlog.unit.test_add_command import _FakeAdapter, runner


ADO_PROJECT_ID = "dominikusnold/Specfact CLI"


def _write_ado_custom_mapping(tmp_path: Path) -> None:
    custom_mapping_file = tmp_path / ".specfact" / "templates" / "backlog" / "field_mappings" / "ado_custom.yaml"
    custom_mapping_file.parent.mkdir(parents=True, exist_ok=True)
    custom_mapping_file.write_text(
        """
field_mappings:
  Custom.Description: description
  Custom.AcceptanceCriteria: acceptance_criteria
  Custom.StoryPoints: story_points
  Custom.Priority: priority
  Custom.BusinessValue: business_value
work_item_type_mappings:
  story: Product Backlog Item
""".strip(),
        encoding="utf-8",
    )


def _write_ado_backlog_config(tmp_path: Path, *, required_field_ref: str = "Custom.Risk") -> None:
    spec_dir = tmp_path / ".specfact"
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "backlog-config.yaml").write_text(
        f"""
backlog_config:
  providers:
    ado:
      adapter: ado
      project_id: {ADO_PROJECT_ID}
      settings:
        field_mapping_file: .specfact/templates/backlog/field_mappings/ado_custom.yaml
        selected_work_item_type: Product Backlog Item
        required_fields_by_work_item_type:
          Product Backlog Item:
            - {required_field_ref}
        allowed_values_by_work_item_type:
          Product Backlog Item:
            {required_field_ref}:
              - Medium
              - High
""".strip(),
        encoding="utf-8",
    )


def _build_ado_add_args(*extra: str) -> list[str]:
    return ["add", "--project-id", ADO_PROJECT_ID, "--adapter", "ado", *extra]


def _invoke_ado_add(
    monkeypatch, tmp_path: Path, created_payloads: list[dict], args: list[str], *, input_text: str | None = None
):
    adapter = _FakeAdapter(items=[], relationships=[], created=created_payloads)
    monkeypatch.setattr(AdapterRegistry, "get_adapter", lambda _adapter: adapter)
    monkeypatch.chdir(tmp_path)
    return runner.invoke(backlog_app, args, input=input_text)


def test_backlog_add_ado_forwards_mapped_business_value_for_create(monkeypatch, tmp_path: Path) -> None:
    """ADO add forwards only provider-only mapped values; core-mapped fields stay top-level."""
    _write_ado_custom_mapping(tmp_path)

    created_payloads: list[dict] = []
    result = _invoke_ado_add(
        monkeypatch,
        tmp_path,
        created_payloads,
        _build_ado_add_args(
            "--type",
            "story",
            "--title",
            "Implement X",
            "--body",
            "Body",
            "--acceptance-criteria",
            "Ready",
            "--priority",
            "1",
            "--story-points",
            "5",
            "--business-value",
            "89",
            "--non-interactive",
        ),
    )

    assert result.exit_code == 0
    assert created_payloads
    assert created_payloads[0].get("provider_fields") == {
        "fields": {
            "Custom.BusinessValue": 89,
        }
    }
    assert created_payloads[0].get("work_item_type") == "Product Backlog Item"


def test_backlog_add_ado_interactive_matches_non_interactive_business_value(monkeypatch, tmp_path: Path) -> None:
    """Interactive and non-interactive ADO add emit the same provider-only mapped fields."""
    add_module = importlib.import_module("specfact_backlog.backlog_core.commands.add")

    _write_ado_custom_mapping(tmp_path)

    created_payloads: list[dict] = []

    def _select(message: str, _choices: list[str], default: str | None = None) -> str:
        normalized = message.lower()
        responses = {
            "issue type": "story",
            "sprint/iteration": "(skip sprint/iteration)",
            "description format": "markdown",
            "acceptance criteria": "yes",
            "add parent issue": "no",
        }
        for fragment, response in responses.items():
            if fragment in normalized:
                return response
        return default or "markdown"

    monkeypatch.setattr(add_module, "_select_with_fallback", _select)

    interactive_result = _invoke_ado_add(
        monkeypatch,
        tmp_path,
        created_payloads,
        _build_ado_add_args(),
        input_text="Implement X\nBody\n::END::\nReady\n::END::\n1\n5\n89\n",
    )

    non_interactive_result = _invoke_ado_add(
        monkeypatch,
        tmp_path,
        created_payloads,
        _build_ado_add_args(
            "--type",
            "story",
            "--title",
            "Implement X",
            "--body",
            "Body",
            "--acceptance-criteria",
            "Ready",
            "--priority",
            "1",
            "--story-points",
            "5",
            "--business-value",
            "89",
            "--non-interactive",
        ),
    )

    assert interactive_result.exit_code == 0
    assert non_interactive_result.exit_code == 0
    assert len(created_payloads) == 2
    expected_provider_fields = {
        "fields": {
            "Custom.BusinessValue": 89,
        }
    }
    assert created_payloads[0].get("provider_fields") == expected_provider_fields
    assert created_payloads[1].get("provider_fields") == expected_provider_fields
    assert created_payloads[0].get("work_item_type") == created_payloads[1].get("work_item_type")


def test_backlog_add_ado_uses_provider_field_override_for_required_custom_mapping(monkeypatch, tmp_path: Path) -> None:
    """ADO add uses explicit provider-field overrides for required custom mapped fields from backlog config."""
    _write_ado_custom_mapping(tmp_path)
    _write_ado_backlog_config(tmp_path)
    custom_mapping_file = tmp_path / ".specfact" / "templates" / "backlog" / "field_mappings" / "ado_custom.yaml"
    custom_mapping_file.write_text(
        """
field_mappings:
  Custom.Description: description
  Custom.Risk: risk
work_item_type_mappings:
  story: Product Backlog Item
""".strip(),
        encoding="utf-8",
    )

    created_payloads: list[dict] = []
    result = _invoke_ado_add(
        monkeypatch,
        tmp_path,
        created_payloads,
        _build_ado_add_args(
            "--type",
            "story",
            "--title",
            "Implement X",
            "--body",
            "Body",
            "--provider-field",
            "Custom.Risk=High",
            "--non-interactive",
            "--repo-path",
            str(tmp_path),
        ),
    )

    assert result.exit_code == 0
    assert created_payloads
    assert created_payloads[0].get("provider_fields") == {
        "fields": {
            "Custom.Risk": "High",
        }
    }


def test_backlog_add_ado_non_interactive_fails_when_required_custom_field_has_no_value(
    monkeypatch, tmp_path: Path
) -> None:
    """ADO add fails before create when persisted required field metadata cannot be satisfied."""
    _write_ado_custom_mapping(tmp_path)
    _write_ado_backlog_config(tmp_path)
    custom_mapping_file = tmp_path / ".specfact" / "templates" / "backlog" / "field_mappings" / "ado_custom.yaml"
    custom_mapping_file.write_text(
        """
field_mappings:
  Custom.Description: description
  Custom.Risk: risk
work_item_type_mappings:
  story: Product Backlog Item
""".strip(),
        encoding="utf-8",
    )

    created_payloads: list[dict] = []
    result = _invoke_ado_add(
        monkeypatch,
        tmp_path,
        created_payloads,
        _build_ado_add_args(
            "--type",
            "story",
            "--title",
            "Implement X",
            "--body",
            "Body",
            "--non-interactive",
            "--repo-path",
            str(tmp_path),
        ),
    )

    assert result.exit_code == 1
    assert not created_payloads
    assert "Missing required mapped provider fields" in result.stdout
    assert "Custom.Risk" in result.stdout


def test_backlog_add_ado_interactive_prompts_for_missing_required_custom_field(monkeypatch, tmp_path: Path) -> None:
    """ADO interactive add prompts for unresolved required custom mapped values from persisted metadata."""
    add_module = importlib.import_module("specfact_backlog.backlog_core.commands.add")

    _write_ado_custom_mapping(tmp_path)
    _write_ado_backlog_config(tmp_path)
    custom_mapping_file = tmp_path / ".specfact" / "templates" / "backlog" / "field_mappings" / "ado_custom.yaml"
    custom_mapping_file.write_text(
        """
field_mappings:
  Custom.Description: description
  Custom.Risk: risk
work_item_type_mappings:
  story: Product Backlog Item
""".strip(),
        encoding="utf-8",
    )

    created_payloads: list[dict] = []

    def _select(message: str, choices: list[str], default: str | None = None) -> str:
        normalized = message.lower()
        responses = {
            "issue type": "story",
            "sprint/iteration": "(skip sprint/iteration)",
            "description format": "markdown",
            "acceptance criteria": "no",
            "add parent issue": "no",
        }
        for fragment, response in responses.items():
            if fragment in normalized:
                return response
        if "value for required provider field" in normalized:
            assert choices == ["Medium", "High"]
            return "High"
        return default or "markdown"

    monkeypatch.setattr(add_module, "_select_with_fallback", _select)

    result = _invoke_ado_add(
        monkeypatch,
        tmp_path,
        created_payloads,
        _build_ado_add_args("--repo-path", str(tmp_path)),
        input_text="Implement X\nBody\n::END::\n\n\n\n",
    )

    assert result.exit_code == 0
    assert created_payloads
    assert created_payloads[0].get("provider_fields") == {
        "fields": {
            "Custom.Risk": "High",
        }
    }


def test_backlog_add_ado_preserves_string_provider_override_values(monkeypatch, tmp_path: Path) -> None:
    """ADO add keeps string provider overrides unchanged even when they look numeric."""
    _write_ado_custom_mapping(tmp_path)
    _write_ado_backlog_config(tmp_path, required_field_ref="Custom.ExternalId")
    custom_mapping_file = tmp_path / ".specfact" / "templates" / "backlog" / "field_mappings" / "ado_custom.yaml"
    custom_mapping_file.write_text(
        """
field_mappings:
  Custom.Description: description
  Custom.ExternalId: external_id
work_item_type_mappings:
  story: Product Backlog Item
""".strip(),
        encoding="utf-8",
    )

    created_payloads: list[dict] = []
    result = _invoke_ado_add(
        monkeypatch,
        tmp_path,
        created_payloads,
        _build_ado_add_args(
            "--type",
            "story",
            "--title",
            "Implement X",
            "--body",
            "Body",
            "--provider-field",
            "Custom.ExternalId=0012",
            "--non-interactive",
            "--repo-path",
            str(tmp_path),
        ),
    )

    assert result.exit_code == 0
    assert created_payloads[0].get("provider_fields") == {
        "fields": {
            "Custom.ExternalId": "0012",
        }
    }


def test_backlog_add_ado_resolves_required_fields_for_created_work_item_type(monkeypatch, tmp_path: Path) -> None:
    """ADO add should enforce requirements for the resolved create work item type, not the last mapped type."""
    _write_ado_custom_mapping(tmp_path)
    spec_dir = tmp_path / ".specfact"
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "backlog-config.yaml").write_text(
        f"""
backlog_config:
  providers:
    ado:
      adapter: ado
      project_id: {ADO_PROJECT_ID}
      settings:
        field_mapping_file: .specfact/templates/backlog/field_mappings/ado_custom.yaml
        selected_work_item_type: Bug
        required_fields_by_work_item_type:
          Product Backlog Item:
            - Custom.StoryRisk
          Bug:
            - Custom.BugSeverity
        allowed_values_by_work_item_type:
          Product Backlog Item:
            Custom.StoryRisk:
              - Medium
              - High
          Bug:
            Custom.BugSeverity:
              - Sev1
              - Sev2
""".strip(),
        encoding="utf-8",
    )
    custom_mapping_file = spec_dir / "templates" / "backlog" / "field_mappings" / "ado_custom.yaml"
    custom_mapping_file.parent.mkdir(parents=True, exist_ok=True)
    custom_mapping_file.write_text(
        """
field_mappings:
  Custom.Description: description
  Custom.StoryRisk: story_risk
  Custom.BugSeverity: bug_severity
work_item_type_mappings:
  story: Product Backlog Item
  bug: Bug
""".strip(),
        encoding="utf-8",
    )

    created_payloads: list[dict] = []
    result = _invoke_ado_add(
        monkeypatch,
        tmp_path,
        created_payloads,
        _build_ado_add_args(
            "--type",
            "story",
            "--title",
            "Implement X",
            "--body",
            "Body",
            "--provider-field",
            "Custom.StoryRisk=High",
            "--non-interactive",
            "--repo-path",
            str(tmp_path),
        ),
    )

    assert result.exit_code == 0
    assert created_payloads
    assert created_payloads[0].get("provider_fields") == {
        "fields": {
            "Custom.StoryRisk": "High",
        }
    }
    assert created_payloads[0].get("work_item_type") == "Product Backlog Item"


def test_backlog_add_ado_exports_custom_mapping_for_adapter_create(monkeypatch, tmp_path: Path) -> None:
    """ADO add should export the resolved custom mapping file for the adapter create call."""
    _write_ado_custom_mapping(tmp_path)

    observed_mapping: list[str | None] = []

    class _EnvAwareAdapter(_FakeAdapter):
        def create_issue(self, project_id: str, payload: dict) -> dict:
            observed_mapping.append(os.environ.get("SPECFACT_ADO_CUSTOM_MAPPING"))
            return super().create_issue(project_id, payload)

    created_payloads: list[dict] = []
    adapter = _EnvAwareAdapter(items=[], relationships=[], created=created_payloads)
    monkeypatch.setattr(AdapterRegistry, "get_adapter", lambda _adapter: adapter)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        backlog_app,
        _build_ado_add_args(
            "--type",
            "story",
            "--title",
            "Implement X",
            "--body",
            "Body",
            "--non-interactive",
        ),
    )

    assert result.exit_code == 0
    assert observed_mapping == [
        str(tmp_path / ".specfact" / "templates" / "backlog" / "field_mappings" / "ado_custom.yaml")
    ]
    assert os.environ.get("SPECFACT_ADO_CUSTOM_MAPPING") is None
