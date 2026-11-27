"""Verify that code import and enrichment preserve generated HTTP contracts."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from specfact_cli.utils.bundle_loader import load_project_bundle
from typer.testing import CliRunner, Result

from specfact_codebase.code.commands import app


@pytest.fixture(name="widget_api")
def make_widget_api(tmp_path_factory: pytest.TempPathFactory) -> Path:
    repo = tmp_path_factory.mktemp("widget-api")
    src = repo / "src"
    src.mkdir()
    (src / "widget.py").write_text(
        '''class WidgetService:
    """Manage the widget catalog."""

    def list_widgets(self) -> list[str]:
        """Read the widget catalog."""
        return ["small"]
''',
        encoding="utf-8",
    )
    return repo


def import_widgets(repo: Path, *options: str) -> Result:
    return CliRunner().invoke(
        app,
        ["import", "from-code", "--repo", str(repo), "--entry-point", "src", "--confidence", "0", *options, "widgets"],
    )


def test_code_import_generates_a_contract_and_report(widget_api: Path) -> None:
    report = widget_api / "reports" / "import.md"

    result = import_widgets(widget_api, "--report", str(report))

    assert result.exit_code == 0, result.output
    bundle = widget_api / ".specfact" / "projects" / "widgets"
    contract = bundle / "contracts" / "FEATURE-WIDGETSERVICE.openapi.yaml"
    operation = yaml.safe_load(contract.read_text(encoding="utf-8"))["paths"]["/widget-service/list-widgets"]
    assert "get" in operation
    assert "Widget Service" in report.read_text(encoding="utf-8")


def test_enrichment_adds_a_feature_and_keeps_the_existing_contract(widget_api: Path) -> None:
    initial = import_widgets(widget_api)
    assert initial.exit_code == 0, initial.output
    bundle = widget_api / ".specfact" / "projects" / "widgets"
    contract = bundle / "contracts" / "FEATURE-WIDGETSERVICE.openapi.yaml"
    original = contract.read_bytes()
    enrichment = widget_api / "enrichment.md"
    enrichment.write_text(
        """# Enrichment Report

## Missing Features

1. **Notifications** (Key: FEATURE-NOTIFICATIONS)
   - Confidence: 0.80
   - Outcomes: Sends notifications to users
   - Stories:
     1. Send a catalog update
        - Acceptance: The service publishes one notification
""",
        encoding="utf-8",
    )

    result = import_widgets(widget_api, "--enrichment", str(enrichment))

    assert result.exit_code == 0, result.output
    assert "FEATURE-NOTIFICATIONS" in load_project_bundle(bundle, validate_hashes=False).features
    assert contract.read_bytes() == original


def test_enrichment_requires_an_existing_import(widget_api: Path) -> None:
    enrichment = widget_api / "enrichment.md"
    enrichment.write_text("# Enrichment Report\n", encoding="utf-8")

    result = import_widgets(widget_api, "--enrichment", str(enrichment))

    assert result.exit_code == 1, result.output
    assert "No existing bundle found" in result.output
