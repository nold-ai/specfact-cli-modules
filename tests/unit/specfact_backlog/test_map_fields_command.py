from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import yaml
from typer.testing import CliRunner


runner = CliRunner()


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def test_map_fields_non_interactive_persists_required_and_allowed_value_metadata(monkeypatch, tmp_path: Path) -> None:
    backlog_commands = importlib.import_module("specfact_backlog.backlog.commands")
    backlog_app = backlog_commands.app
    monkeypatch.chdir(tmp_path)

    fields_payload = {
        "value": [
            {"referenceName": "System.Description", "name": "Description"},
            {"referenceName": "Microsoft.VSTS.Common.AcceptanceCriteria", "name": "Acceptance Criteria"},
            {"referenceName": "Microsoft.VSTS.Common.Priority", "name": "Priority"},
            {"referenceName": "Custom.FinOpsCategory", "name": "FinOps Category"},
        ]
    }
    work_item_types_payload = {"value": [{"name": "User Story"}]}
    work_item_type_fields_payload = {
        "value": [
            {
                "referenceName": "Custom.FinOpsCategory",
                "name": "FinOps Category",
                "alwaysRequired": True,
                "allowedValues": [],
            }
        ]
    }

    def fake_get(url: str, **_kwargs: Any) -> _FakeResponse:
        if "/_apis/wit/workitemtypes?" in url:
            return _FakeResponse(work_item_types_payload)
        if "/_apis/wit/workitemtypes/" in url and "/fields?" in url:
            return _FakeResponse(work_item_type_fields_payload)
        if "/_apis/wit/fields/Custom.FinOpsCategory?" in url:
            return _FakeResponse(
                {"allowedValues": [], "picklistId": "11111111-1111-1111-1111-111111111111", "isPicklist": True}
            )
        if "/_apis/work/processes/lists/11111111-1111-1111-1111-111111111111?api-version=7.1" in url:
            return _FakeResponse({"items": ["Business", "Compliance"]})
        if "/_apis/wit/fields?" in url:
            return _FakeResponse(fields_payload)
        msg = f"Unexpected URL: {url}"
        raise AssertionError(msg)

    monkeypatch.setattr("requests.get", fake_get)

    result = runner.invoke(
        backlog_app,
        [
            "map-fields",
            "--provider",
            "ado",
            "--ado-org",
            "noldai",
            "--ado-project",
            "specfact-cli",
            "--ado-token",
            "token",
            "--ado-framework",
            "scrum",
            "--non-interactive",
        ],
    )

    assert result.exit_code == 0, result.output

    mapping_path = tmp_path / ".specfact" / "templates" / "backlog" / "field_mappings" / "ado_custom.yaml"
    config_path = tmp_path / ".specfact" / "backlog-config.yaml"
    assert mapping_path.exists()
    assert config_path.exists()

    mapping_data = _load_yaml(mapping_path)
    field_mappings = mapping_data.get("field_mappings")
    assert isinstance(field_mappings, dict)
    assert "Custom.FinOpsCategory" in field_mappings

    cfg = _load_yaml(config_path)
    providers = cfg.get("backlog_config", {}).get("providers", {})
    ado_settings = providers.get("ado", {}).get("settings", {})
    required_by_type = ado_settings.get("required_fields_by_work_item_type", {})
    allowed_by_type = ado_settings.get("allowed_values_by_work_item_type", {})
    assert required_by_type.get("User Story") == ["Custom.FinOpsCategory"]
    assert allowed_by_type.get("User Story", {}).get("Custom.FinOpsCategory") == ["Business", "Compliance"]


def test_map_fields_reports_progress_for_selected_work_item_type_metadata(monkeypatch, tmp_path: Path) -> None:
    backlog_commands = importlib.import_module("specfact_backlog.backlog.commands")
    backlog_app = backlog_commands.app
    monkeypatch.chdir(tmp_path)

    fields_payload = {
        "value": [
            {"referenceName": "System.Description", "name": "Description"},
            {"referenceName": "Custom.FinOpsCategory", "name": "FinOps Category"},
        ]
    }
    work_item_types_payload = {"value": [{"name": "User Story"}]}
    work_item_type_fields_payload = {
        "value": [
            {
                "referenceName": "Custom.FinOpsCategory",
                "name": "FinOps Category",
                "alwaysRequired": True,
                "allowedValues": ["Business", "Compliance"],
            }
        ]
    }

    def fake_get(url: str, **_kwargs: Any) -> _FakeResponse:
        if "/_apis/wit/workitemtypes?" in url:
            return _FakeResponse(work_item_types_payload)
        if "/_apis/wit/workitemtypes/" in url and "/fields?" in url:
            return _FakeResponse(work_item_type_fields_payload)
        if "/_apis/wit/fields?" in url:
            return _FakeResponse(fields_payload)
        msg = f"Unexpected URL: {url}"
        raise AssertionError(msg)

    monkeypatch.setattr("requests.get", fake_get)

    result = runner.invoke(
        backlog_app,
        [
            "map-fields",
            "--provider",
            "ado",
            "--ado-org",
            "noldai",
            "--ado-project",
            "specfact-cli",
            "--ado-token",
            "token",
            "--ado-framework",
            "scrum",
            "--non-interactive",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Fetching required-field metadata for selected work item type: User Story" in result.output


def test_map_fields_non_interactive_fails_when_required_field_cannot_be_mapped(monkeypatch, tmp_path: Path) -> None:
    backlog_commands = importlib.import_module("specfact_backlog.backlog.commands")
    backlog_app = backlog_commands.app
    monkeypatch.chdir(tmp_path)

    fields_payload = {"value": [{"referenceName": "System.Description", "name": "Description"}]}
    work_item_types_payload = {"value": [{"name": "User Story"}]}
    # Missing/blank referenceName should be treated as unresolved required field metadata.
    work_item_type_fields_payload = {
        "value": [{"referenceName": "", "name": "FinOps Category", "alwaysRequired": True}]
    }

    def fake_get(url: str, **_kwargs: Any) -> _FakeResponse:
        if "/_apis/wit/workitemtypes?" in url:
            return _FakeResponse(work_item_types_payload)
        if "/_apis/wit/workitemtypes/" in url and "/fields?" in url:
            return _FakeResponse(work_item_type_fields_payload)
        if "/_apis/wit/fields/" in url and "?api-version=7.1" in url:
            return _FakeResponse({"allowedValues": []})
        if "/_apis/wit/fields?" in url:
            return _FakeResponse(fields_payload)
        msg = f"Unexpected URL: {url}"
        raise AssertionError(msg)

    monkeypatch.setattr("requests.get", fake_get)

    result = runner.invoke(
        backlog_app,
        [
            "map-fields",
            "--provider",
            "ado",
            "--ado-org",
            "noldai",
            "--ado-project",
            "specfact-cli",
            "--ado-token",
            "token",
            "--ado-framework",
            "scrum",
            "--non-interactive",
        ],
    )

    assert result.exit_code != 0
    assert "run interactive `specfact backlog map-fields`" in result.output.lower()
