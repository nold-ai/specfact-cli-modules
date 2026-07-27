"""Integration tests for the requirements command app."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from specfact_cli.common.bundle_factory import create_empty_project_bundle
from specfact_cli.utils.bundle_loader import save_project_bundle
from typer.testing import CliRunner

from specfact_requirements.requirements.commands import app


runner = CliRunner()


def _bundle_dir(tmp_path: Path) -> Path:
    bundle_dir = tmp_path / "bundle"
    bundle = create_empty_project_bundle("bundle")
    save_project_bundle(bundle, bundle_dir, atomic=False)
    return bundle_dir


def _source_file(tmp_path: Path) -> Path:
    source = tmp_path / "requirements.json"
    source.write_text(
        json.dumps(
            [
                {
                    "schema_version": "1",
                    "requirement_id": "REQ-CLI",
                    "title": "CLI imports requirement context",
                    "sources": [
                        {
                            "source_type": "issue",
                            "locator": "https://github.com/nold-ai/specfact-cli-modules/issues/165",
                        }
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    return source


def _openspec_change(project_root: Path) -> Path:
    change_dir = project_root / "openspec" / "changes" / "widget-evidence"
    spec_path = change_dir / "specs" / "widgets" / "spec.md"
    spec_path.parent.mkdir(parents=True)
    spec_path.write_text(
        """## ADDED Requirements

### Requirement: Widget rendering

The system SHALL render a widget.

#### Scenario: Render a valid widget

- **GIVEN** a valid widget request
- **WHEN** rendering runs
- **THEN** the widget is returned
""",
        encoding="utf-8",
    )
    return change_dir


def _speckit_feature(project_root: Path, *, incomplete: bool = False) -> Path:
    feature_dir = project_root / "specs" / "001-widget-rendering"
    feature_dir.mkdir(parents=True)
    content = """# Feature Specification: Widget rendering

## User Scenarios & Testing

### User Story 1 - Render widgets (Priority: P1)

As a user, I want widgets rendered so that I can see them.

**Acceptance Scenarios**:

1. **Given** a valid widget request, **When** rendering runs, **Then** the widget is returned

## Requirements

- **FR-001**: System MUST render a widget
"""
    if incomplete:
        content += "\n**Feature Branch**: `[###-feature-name]`\n"
    (feature_dir / "spec.md").write_text(
        content,
        encoding="utf-8",
    )
    return feature_dir


@pytest.mark.integration
def test_command_module_exposes_typer_app() -> None:
    assert app is not None
    assert hasattr(app, "registered_commands")


@pytest.mark.integration
def test_command_module_import_does_not_require_core_requirements_context() -> None:
    code = """
import builtins

real_import = builtins.__import__

def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name.startswith("specfact_cli.requirements"):
        raise ModuleNotFoundError("blocked specfact_cli.requirements import")
    return real_import(name, globals, locals, fromlist, level)

builtins.__import__ = guarded_import

from specfact_requirements.requirements.commands import app

assert app is not None
"""
    source_path = Path(__file__).resolve().parents[3] / "packages" / "specfact-requirements" / "src"
    env = os.environ | {"PYTHONPATH": os.pathsep.join([source_path.as_posix(), os.environ.get("PYTHONPATH", "")])}

    result = subprocess.run([sys.executable, "-c", code], capture_output=True, check=False, text=True, env=env)

    assert result.returncode == 0, result.stderr


@pytest.mark.integration
def test_requirements_import_list_and_validate_commands_emit_json(tmp_path: Path) -> None:
    bundle_dir = _bundle_dir(tmp_path)
    source = _source_file(tmp_path)

    import_result = runner.invoke(
        app,
        ["import", "--from-file", str(source), "--bundle", str(bundle_dir), "--format", "json"],
    )

    assert import_result.exit_code == 0, import_result.output
    assert json.loads(import_result.output)["imported"] == 1

    list_result = runner.invoke(app, ["list", "--bundle", str(bundle_dir), "--show-coverage", "--format", "json"])

    assert list_result.exit_code == 0, list_result.output
    list_payload = json.loads(list_result.output)
    assert list_payload["requirements"][0]["requirement_id"] == "REQ-CLI"
    assert list_payload["coverage"]["missing_evidence_requirement_ids"] == ["REQ-CLI"]

    validate_result = runner.invoke(
        app,
        ["validate", "--bundle", str(bundle_dir), "--profile", "enterprise-full-stack", "--format", "json"],
    )

    assert validate_result.exit_code == 1
    assert json.loads(validate_result.output)["status"] == "failed"


@pytest.mark.integration
def test_requirements_help_exposes_no_author_command() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "import" in result.output
    assert "validate" in result.output
    assert "coverage" in result.output
    assert "author" not in result.output


@pytest.mark.integration
def test_requirements_evidence_requires_exactly_one_source_selection_mode(tmp_path: Path) -> None:
    output_path = tmp_path / "requirements-evidence.json"

    result = runner.invoke(app, ["evidence", "--output", str(output_path)])

    assert result.exit_code == 2
    assert "exactly one of --base-ref or --staged" in result.output
    assert not output_path.exists()

    result = runner.invoke(
        app,
        ["evidence", "--base-ref", "origin/dev", "--staged", "--output", str(output_path)],
    )

    assert result.exit_code == 2
    assert "exactly one of --base-ref or --staged" in result.output
    assert not output_path.exists()


@pytest.mark.integration
def test_requirements_evidence_reports_aliased_destinations_as_usage_error(tmp_path: Path) -> None:
    output_path = tmp_path / "requirements-evidence.json"
    summary_path = tmp_path / "requirements-evidence.md"
    output_path.write_text('{"verdict": "previous"}\n', encoding="utf-8")
    summary_path.hardlink_to(output_path)

    result = runner.invoke(
        app,
        ["evidence", "--base-ref", "HEAD", "--output", str(output_path), "--summary", str(summary_path)],
    )

    assert result.exit_code == 2
    assert "different destinations" in result.output


@pytest.mark.integration
def test_requirements_import_help_exposes_optional_native_source_path() -> None:
    result = runner.invoke(app, ["import", "--help"])

    assert result.exit_code == 0
    assert "[source_path]" in result.output.lower()


@pytest.mark.integration
def test_requirements_import_openspec_accepts_explicit_and_auto_detected_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root = tmp_path / "project"
    change_dir = _openspec_change(project_root)
    explicit_bundle = _bundle_dir(tmp_path / "explicit")

    explicit_result = runner.invoke(
        app,
        ["import", "--from-openspec", str(change_dir), "--bundle", str(explicit_bundle), "--format", "json"],
    )

    assert explicit_result.exit_code == 0, explicit_result.output
    assert json.loads(explicit_result.output)["imported"] == 1

    auto_bundle = _bundle_dir(tmp_path / "auto")
    (project_root / "openspec" / "changes" / "archive" / "2026-07-14-widget-evidence").mkdir(parents=True)
    monkeypatch.chdir(project_root)
    auto_result = runner.invoke(
        app,
        ["import", "--from-openspec", "--bundle", str(auto_bundle), "--format", "json"],
    )

    assert auto_result.exit_code == 0, auto_result.output
    assert json.loads(auto_result.output)["imported"] == 1


@pytest.mark.integration
def test_requirements_import_speckit_accepts_explicit_source(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    feature_dir = _speckit_feature(project_root)
    bundle_dir = _bundle_dir(tmp_path)

    result = runner.invoke(
        app,
        ["import", "--from-speckit", str(feature_dir), "--bundle", str(bundle_dir), "--format", "json"],
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["imported"] == 1


@pytest.mark.integration
def test_requirements_import_rejects_incomplete_speckit_source_without_persistence(tmp_path: Path) -> None:
    feature_dir = _speckit_feature(tmp_path / "project", incomplete=True)
    source_before = (feature_dir / "spec.md").read_bytes()
    bundle_dir = _bundle_dir(tmp_path / "bundle")

    result = runner.invoke(
        app,
        ["import", "--from-speckit", str(feature_dir), "--bundle", str(bundle_dir), "--format", "json"],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["imported"] == 0
    assert payload["diagnostics"] == [
        {
            "code": "incomplete-source-template",
            "message": "Spec Kit source still contains a supported official scaffold placeholder.",
            "record_index": None,
            "requirement_id": None,
            "severity": "error",
            "source_locator": (feature_dir / "spec.md").as_posix(),
        }
    ]
    assert not (bundle_dir / "reports" / "requirements" / "inputs.yaml").exists()
    assert (feature_dir / "spec.md").read_bytes() == source_before


@pytest.mark.integration
def test_requirements_import_rejects_non_directory_native_source_path(tmp_path: Path) -> None:
    bundle_dir = _bundle_dir(tmp_path)
    source_file = tmp_path / "source.md"
    source_file.write_text("not a source directory\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["import", "--from-openspec", str(source_file), "--bundle", str(bundle_dir), "--format", "json"],
    )

    assert result.exit_code == 2
    assert "Invalid value" in result.output


@pytest.mark.integration
def test_requirements_import_surfaces_core_schema_rejection_without_persistence(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    change_dir = _openspec_change(project_root)
    (project_root / "openspec" / "config.yaml").write_text("schema: company-custom\n", encoding="utf-8")
    bundle_dir = _bundle_dir(tmp_path)

    result = runner.invoke(
        app,
        ["import", "--from-openspec", str(change_dir), "--bundle", str(bundle_dir), "--format", "json"],
    )

    assert result.exit_code == 1
    assert json.loads(result.output)["diagnostics"][0]["code"] == "unsupported-source-schema"
    assert not (bundle_dir / "reports" / "requirements" / "inputs.yaml").exists()
