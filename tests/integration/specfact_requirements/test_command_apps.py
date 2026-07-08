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
