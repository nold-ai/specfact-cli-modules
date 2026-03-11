from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import requests
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


class _FakeQuestionaryPrompt:
    def __init__(self, resolver: Any) -> None:
        self._resolver = resolver

    def ask(self) -> Any:
        return self._resolver()


class _FakeQuestionaryModule:
    def Choice(self, title: str, value: str) -> Any:  # noqa: N802
        return SimpleNamespace(title=title, value=value)

    def checkbox(self, _message: str, choices: list[Any]) -> _FakeQuestionaryPrompt:
        values = [getattr(choice, "value", choice) for choice in choices]
        return _FakeQuestionaryPrompt(lambda: values)

    def select(self, message: str, choices: list[Any], default: Any = None, **_kwargs: Any) -> _FakeQuestionaryPrompt:
        def _resolve() -> Any:
            normalized_message = message.lower()
            if "system.iterationid" in normalized_message or "system.areaid" in normalized_message:
                return "<no mapping>"
            if default is not None:
                return default
            if choices:
                first = choices[0]
                return getattr(first, "value", first)
            return None

        return _FakeQuestionaryPrompt(_resolve)


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
                "allowedValues": [],
            },
            {
                "referenceName": "Custom.ValueArea",
                "name": "Value Area",
                "alwaysRequired": False,
                "allowedValues": [],
            },
        ]
    }

    def fake_get(url: str, **_kwargs: Any) -> _FakeResponse:
        if "/_apis/wit/workitemtypes?" in url:
            return _FakeResponse(work_item_types_payload)
        if "/_apis/wit/workitemtypes/" in url and "/fields?" in url:
            return _FakeResponse(work_item_type_fields_payload)
        if "/_apis/wit/fields/Custom.FinOpsCategory?" in url:
            return _FakeResponse({"allowedValues": ["Business", "Compliance"]})
        if "/_apis/wit/fields/Custom.ValueArea?" in url:
            return _FakeResponse({"allowedValues": ["Architectural", "Business"]})
        if "/_apis/wit/fields?" in url:
            return _FakeResponse(
                {"value": fields_payload["value"] + [{"referenceName": "Custom.ValueArea", "name": "Value Area"}]}
            )
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
    assert "Fetching field metadata details 1/2" in result.output
    assert "Fetching field metadata details 2/2" in result.output


def test_map_fields_skips_allowed_values_when_picklist_metadata_fetch_fails(monkeypatch, tmp_path: Path) -> None:
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
            raise requests.exceptions.RequestException("transient picklist failure")
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

    cfg = _load_yaml(tmp_path / ".specfact" / "backlog-config.yaml")
    providers = cfg.get("backlog_config", {}).get("providers", {})
    ado_settings = providers.get("ado", {}).get("settings", {})
    required_by_type = ado_settings.get("required_fields_by_work_item_type", {})
    allowed_by_type = ado_settings.get("allowed_values_by_work_item_type", {})

    assert required_by_type.get("User Story") == ["Custom.FinOpsCategory"]
    assert allowed_by_type.get("User Story", {}) == {}


def test_map_fields_interactive_ignores_builtin_required_hierarchy_ids(monkeypatch, tmp_path: Path) -> None:
    backlog_commands = importlib.import_module("specfact_backlog.backlog.commands")
    backlog_app = backlog_commands.app
    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(sys.modules, "questionary", _FakeQuestionaryModule())

    fields_payload = {
        "value": [
            {"referenceName": "System.Description", "name": "Description"},
            {"referenceName": "System.Title", "name": "Title"},
            {"referenceName": "Custom.FinOpsCategory", "name": "FinOps Category"},
        ]
    }
    work_item_types_payload = {"value": [{"name": "User Story"}]}
    work_item_type_fields_payload = {
        "value": [
            {
                "referenceName": "System.IterationId",
                "name": "Iteration ID",
                "alwaysRequired": True,
                "allowedValues": [],
            },
            {"referenceName": "System.AreaId", "name": "Area ID", "alwaysRequired": True, "allowedValues": []},
            {"referenceName": "System.Title", "name": "Title", "alwaysRequired": True, "allowedValues": []},
            {
                "referenceName": "Custom.FinOpsCategory",
                "name": "FinOps Category",
                "alwaysRequired": True,
                "allowedValues": ["Business", "Compliance"],
            },
        ]
    }

    def fake_get(url: str, **_kwargs: Any) -> _FakeResponse:
        if "/_apis/wit/workitemtypes?" in url:
            return _FakeResponse(work_item_types_payload)
        if "/_apis/wit/workitemtypes/" in url and "/fields?" in url:
            return _FakeResponse(work_item_type_fields_payload)
        if "/_apis/wit/fields/System.Title?" in url:
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
            "agile",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "missing mapping for required field: System.IterationId" not in result.output
    assert "missing mapping for required field: System.AreaId" not in result.output

    config_path = tmp_path / ".specfact" / "backlog-config.yaml"
    cfg = _load_yaml(config_path)
    providers = cfg.get("backlog_config", {}).get("providers", {})
    ado_settings = providers.get("ado", {}).get("settings", {})
    required_by_type = ado_settings.get("required_fields_by_work_item_type", {})
    assert required_by_type.get("User Story") == ["System.Title", "Custom.FinOpsCategory"]


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


def test_map_fields_non_interactive_persists_required_field_types(monkeypatch, tmp_path: Path) -> None:
    backlog_commands = importlib.import_module("specfact_backlog.backlog.commands")
    backlog_app = backlog_commands.app
    monkeypatch.chdir(tmp_path)

    fields_payload = {
        "value": [
            {"referenceName": "Custom.Toggle", "name": "Toggle"},
        ]
    }
    work_item_types_payload = {"value": [{"name": "User Story"}]}
    work_item_type_fields_payload = {
        "value": [
            {
                "referenceName": "Custom.Toggle",
                "name": "Toggle",
                "alwaysRequired": True,
                "type": "boolean",
                "allowedValues": [],
            }
        ]
    }

    def fake_get(url: str, **_kwargs: Any) -> _FakeResponse:
        if "/_apis/wit/workitemtypes?" in url:
            return _FakeResponse(work_item_types_payload)
        if "/_apis/wit/workitemtypes/" in url and "/fields?" in url:
            return _FakeResponse(work_item_type_fields_payload)
        if "/_apis/wit/fields/Custom.Toggle?" in url:
            return _FakeResponse({"allowedValues": [], "type": "boolean"})
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

    config_path = tmp_path / ".specfact" / "backlog-config.yaml"
    cfg = _load_yaml(config_path)
    ado_settings = cfg.get("backlog_config", {}).get("providers", {}).get("ado", {}).get("settings", {})
    type_by_type = ado_settings.get("required_field_types_by_work_item_type", {})
    assert type_by_type.get("User Story", {}).get("Custom.Toggle") == "boolean"
