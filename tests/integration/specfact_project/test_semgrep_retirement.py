"""Verify Project import artifacts with the retired scanner available as a sentinel."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml
from specfact_cli.models.plan import Feature, PlanBundle, Product
from specfact_cli.models.protocol import Protocol
from specfact_cli.models.source_tracking import SourceTracking
from typer.testing import CliRunner

from specfact_codebase.code.commands import app
from specfact_project.import_cmd import commands
from specfact_project.import_cmd.commands import _extract_contract_worker, _extract_contracts, _init_contract_worker
from specfact_project.importers.speckit_converter import SpecKitConverter
from specfact_project.sync_runtime.bridge_sync import BridgeSync


HTTP_SOURCE = """\
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Widget(BaseModel):
    name: str

@app.post("/widgets", status_code=201)
def post_widgets(body: Widget) -> dict:
    return {"id": 7, "name": body.name}
"""

HTTP_TEST = """\
def test_creates_widget(client):
    response = client.post("/widgets", json={"name": "example"})
    assert response.status_code == 201
    assert response.json() == {"id": 7, "name": "example"}
"""


@pytest.fixture(name="project_with_test")
def make_project_with_test(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo = tmp_path / "project"
    repo.mkdir()
    bin_path = tmp_path / "bin"
    bin_path.mkdir()
    semgrep = bin_path / "semgrep"
    semgrep.write_text('#!/bin/sh\ntouch "$SPECFACT_TEST_SEMGREP_MARKER"\nexit 1\n', encoding="utf-8")
    semgrep.chmod(0o755)
    monkeypatch.setenv("PATH", os.pathsep.join((str(bin_path), os.environ.get("PATH", ""))))
    monkeypatch.setenv("SPECFACT_TEST_SEMGREP_MARKER", str(repo / "semgrep-ran"))
    config = repo / "tools" / "semgrep" / "test-patterns.yml"
    config.parent.mkdir(parents=True)
    config.write_text("rules: []\n", encoding="utf-8")
    (repo / "service.py").write_text(HTTP_SOURCE, encoding="utf-8")
    (repo / "test_service.py").write_text(HTTP_TEST, encoding="utf-8")
    return repo


@pytest.mark.parametrize("test_mode", ["true", "false"], ids=["sequential", "workers"])
def test_project_contract_examples_keep_request_and_asserted_response(
    project_with_test: Path, monkeypatch: pytest.MonkeyPatch, test_mode: str
) -> None:
    monkeypatch.setenv("TEST_MODE", test_mode)
    monkeypatch.delenv("SPECFACT_CONTRACT_POOL", raising=False)
    source = SourceTracking(
        implementation_files=["service.py"], test_functions=["test_service.py::test_creates_widget"]
    )
    plan = PlanBundle(
        idea=None,
        business=None,
        product=Product(themes=["Core"]),
        features=[Feature(key=f"FEATURE-{index}", title="Widgets", source_tracking=source) for index in range(2)],
        metadata=None,
        clarifications=None,
    )
    bundle = project_with_test / "bundle"

    contracts = _extract_contracts(project_with_test, bundle, plan, True, lambda _: None, force=True)

    assert len(contracts) == 2
    assert not (project_with_test / "semgrep-ran").exists()
    for contract in contracts.values():
        operation = contract["paths"]["/widgets"]["post"]
        request = operation["requestBody"]["content"]["application/json"]["examples"]["test-example"]
        assert request["value"] == {"name": "example"}
        response = operation["responses"]["201"]["content"]["application/json"]["examples"]["test-example"]
        assert response["value"] == {"id": 7, "name": "example"}


@pytest.fixture(name="speckit_repo")
def make_speckit_repo(tmp_path: Path) -> Path:
    memory = tmp_path / ".specify" / "memory"
    memory.mkdir(parents=True)
    (memory / "constitution.md").write_text("# Project Constitution\n\nContract-first development.\n", encoding="utf-8")
    feature = tmp_path / "specs" / "001-widgets"
    feature.mkdir(parents=True)
    (feature / "spec.md").write_text("# Feature Specification: Widgets\n\nManage widgets.\n", encoding="utf-8")
    (feature / "plan.md").write_text("# Implementation Plan\n\nBuild a Widget API.\n", encoding="utf-8")
    return tmp_path


def test_speckit_import_keeps_protocol_and_workflow_without_scanner(speckit_repo: Path) -> None:
    report = speckit_repo / "import-report.md"
    result = CliRunner().invoke(
        app,
        [
            "import",
            "from-bridge",
            "--repo",
            str(speckit_repo),
            "--adapter",
            "speckit",
            "--write",
            "--report",
            str(report),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "semgrep" not in result.output.lower()
    assert not (speckit_repo / ".semgrep").exists()
    protocol_file = speckit_repo / ".specfact" / "protocols" / "workflow.protocol.yaml"
    protocol = Protocol.model_validate(yaml.safe_load(protocol_file.read_text(encoding="utf-8")))
    assert protocol.states and protocol.transitions == []
    workflow_file = speckit_repo / ".github" / "workflows" / "specfact-gate.yml"
    workflow = workflow_file.read_text(encoding="utf-8")
    steps = yaml.safe_load(workflow)["jobs"]["specfact"]["steps"]
    assert any("specfact project health-check" in step.get("run", "") for step in steps)
    assert "semgrep" not in workflow.lower()
    rendered_report = report.read_text(encoding="utf-8")
    assert "Features Extracted**: 1" in rendered_report
    assert "Widgets (" in rendered_report
    assert ".specfact/protocols/workflow.protocol.yaml" in rendered_report
    assert ".github/workflows/specfact-gate.yml" in rendered_report
    assert "semgrep" not in rendered_report.lower()


@pytest.mark.parametrize(
    ("options", "message"),
    [
        ([], "Use --write"),
        (["--dry-run"], "Features Found: 1"),
    ],
    ids=["preview", "dry-run"],
)
def test_speckit_import_preview_leaves_source_untouched(speckit_repo: Path, options: list[str], message: str) -> None:
    command = ["import", "from-bridge", "--repo", str(speckit_repo), *options]

    result = CliRunner().invoke(app, command)

    assert result.exit_code == 0, result.output
    assert message in result.output
    assert not (speckit_repo / ".specfact").exists()
    assert not (speckit_repo / ".github").exists()


@pytest.mark.parametrize(
    ("adapter", "message"),
    [("speckit", "Could not auto-detect adapter"), ("unknown-adapter", "Unsupported adapter")],
)
def test_bridge_import_rejects_unrecognized_sources(tmp_path: Path, adapter: str, message: str) -> None:
    result = CliRunner().invoke(
        app, ["import", "from-bridge", "--repo", str(tmp_path), "--adapter", adapter, "--write"]
    )

    assert result.exit_code == 1, result.output
    assert message in result.output
    assert not (tmp_path / ".specfact").exists()


@pytest.mark.parametrize("pool_mode", ["thread", "process"])
def test_contract_pool_omits_features_without_routes(
    project_with_test: Path, monkeypatch: pytest.MonkeyPatch, pool_mode: str
) -> None:
    monkeypatch.setenv("TEST_MODE", "false")
    monkeypatch.setenv("SPECFACT_CONTRACT_POOL", pool_mode)
    (project_with_test / "worker.py").write_text("def count() -> int:\n    return 1\n", encoding="utf-8")
    bundle = PlanBundle(
        idea=None,
        business=None,
        product=Product(themes=["Import"]),
        features=[
            Feature(
                key="FEATURE-HTTP-WIDGET",
                title="Widget HTTP API",
                source_tracking=SourceTracking(implementation_files=["service.py"]),
            ),
            Feature(
                key="FEATURE-WORKER",
                title="Count worker",
                source_tracking=SourceTracking(implementation_files=["worker.py"]),
            ),
        ],
        clarifications=None,
        metadata=None,
    )

    destination = project_with_test / "bundle"
    extracted = _extract_contracts(project_with_test, destination, bundle, True, lambda _: None)

    assert set(extracted) == {"FEATURE-HTTP-WIDGET"}
    assert (destination / "contracts" / "FEATURE-HTTP-WIDGET.openapi.yaml").is_file()
    assert not (destination / "contracts" / "FEATURE-WORKER.openapi.yaml").exists()


def test_contract_worker_returns_the_written_operation(
    project_with_test: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for binding in (
        "_CONTRACT_WORKER_REPO",
        "_CONTRACT_WORKER_CONTRACTS_DIR",
        "_CONTRACT_WORKER_EXTRACTOR",
        "_CONTRACT_WORKER_TEST_CONVERTER",
    ):
        monkeypatch.setattr(commands, binding, None)
    destination = project_with_test / "worker-output"
    destination.mkdir()
    feature = Feature(
        key="FEATURE-WORKER-HTTP",
        title="Widgets",
        source_tracking=SourceTracking(
            implementation_files=["service.py"],
            test_functions=["test_service.py::test_creates_widget"],
        ),
    )

    with pytest.raises(RuntimeError, match="not initialized"):
        _extract_contract_worker(feature.model_dump())
    with pytest.warns(UserWarning, match="test-pattern configuration is retired"):
        _init_contract_worker(str(project_with_test), str(destination))
    key, result = _extract_contract_worker(feature.model_dump())

    assert key == feature.key and result is not None
    path = destination / "FEATURE-WORKER-HTTP.openapi.yaml"
    saved = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert saved["paths"] == result["paths"]
    assert "201" in saved["paths"]["/widgets"]["post"]["responses"]


def test_repeated_speckit_import_preserves_existing_protocol_and_custom_rules(speckit_repo: Path) -> None:
    runner = CliRunner()
    args = ["import", "from-bridge", "--repo", str(speckit_repo), "--write"]
    first = runner.invoke(app, args)
    assert first.exit_code == 0, first.output
    protocol = speckit_repo / ".specfact" / "protocols" / "workflow.protocol.yaml"
    original = protocol.read_bytes()
    custom_rule = speckit_repo / ".semgrep" / "custom.yml"
    custom_rule.parent.mkdir()
    custom_rule.write_text("rules: []\n", encoding="utf-8")

    repeated = runner.invoke(app, args)

    assert repeated.exit_code == 0, repeated.output
    assert protocol.read_bytes() == original
    assert {path.name for path in custom_rule.parent.iterdir()} == {"custom.yml"}
    assert custom_rule.read_text(encoding="utf-8") == "rules: []\n"


def test_empty_speckit_repo_explains_what_is_required(speckit_repo: Path) -> None:
    (speckit_repo / "specs" / "001-widgets" / "spec.md").unlink()

    result = CliRunner().invoke(app, ["import", "from-bridge", "--repo", str(speckit_repo), "--write"])

    assert result.exit_code == 1, result.output
    assert "No features found" in result.output
    assert not (speckit_repo / ".github").exists()


@pytest.mark.parametrize(
    ("failed_generator", "message", "surviving_artifact"),
    [
        ("convert_protocol", "Protocol generation failed", ".github/workflows/specfact-gate.yml"),
        (
            "generate_github_action",
            "GitHub Action workflow generation failed",
            ".specfact/protocols/workflow.protocol.yaml",
        ),
    ],
)
def test_speckit_generation_reports_a_failed_artifact(
    speckit_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    failed_generator: str,
    message: str,
    surviving_artifact: str,
) -> None:
    def raise_write_error(*_args: object, **_kwargs: object) -> None:
        raise OSError("Fixture denied writing")

    monkeypatch.setattr(SpecKitConverter, failed_generator, raise_write_error)
    result = CliRunner().invoke(app, ["import", "from-bridge", "--repo", str(speckit_repo), "--write"])

    assert result.exit_code == 0, result.output
    assert message in result.output
    assert "Fixture denied writing" in result.output
    assert (speckit_repo / surviving_artifact).is_file()


def test_import_reports_an_invalid_existing_protocol(speckit_repo: Path) -> None:
    protocol = speckit_repo / ".specfact" / "protocols" / "workflow.protocol.yaml"
    protocol.parent.mkdir(parents=True)
    invalid_yaml = "state: [\n"
    protocol.write_text(invalid_yaml, encoding="utf-8")

    result = CliRunner().invoke(app, ["import", "from-bridge", "--repo", str(speckit_repo), "--write"])

    assert result.exit_code == 0, result.output
    assert "Protocol loading failed" in result.output
    assert protocol.read_text(encoding="utf-8") == invalid_yaml
    assert (speckit_repo / ".github" / "workflows" / "specfact-gate.yml").is_file()


def test_bridge_reports_missing_specifications_and_continues_the_summary(
    speckit_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = BridgeSync.resolve_artifact_path
    for index in range(2, 7):
        feature = speckit_repo / "specs" / f"{index:03d}-fixture"
        feature.mkdir()
        (feature / "spec.md").write_text("# Feature Specification: Import fixture\n", encoding="utf-8")

    def resolve(sync: BridgeSync, artifact_key: str, feature_id: str, bundle_name: str) -> Path:
        if artifact_key == "specification":
            if feature_id == "001-widgets":
                raise OSError("Could not resolve fixture path")
            return speckit_repo / "missing-specification.md"
        return original(sync, artifact_key, feature_id, bundle_name)

    monkeypatch.setattr(BridgeSync, "resolve_artifact_path", resolve)
    result = CliRunner().invoke(app, ["import", "from-bridge", "--repo", str(speckit_repo), "--write"])

    assert result.exit_code == 1, result.output
    assert "Could not resolve fixture path" in " ".join(result.output.split())
    assert "Artifact not found" in result.output
    assert "6 specification import(s) had issues" in result.output
    assert "and 1 more" in result.output
    assert "No specifications were imported successfully" in result.output


@pytest.mark.parametrize("existing_project", [False, True], ids=["unknown-project", "valid-project"])
def test_bridge_debug_events_record_the_import_outcome(
    tmp_path: Path, speckit_repo: Path, monkeypatch: pytest.MonkeyPatch, existing_project: bool
) -> None:
    events = []

    def record(_category: str, command: str, state: str, **_fields: object) -> None:
        events.append((command, state))

    monkeypatch.setattr(commands, "is_debug_mode", lambda: True)
    monkeypatch.setattr(commands, "debug_log_operation", record)
    repo = speckit_repo if existing_project else tmp_path / "empty"
    repo.mkdir(exist_ok=True)
    result = CliRunner().invoke(app, ["import", "from-bridge", "--repo", str(repo), "--write"])

    assert result.exit_code == (0 if existing_project else 1), result.output
    assert events == [
        ("import from-bridge", "started"),
        ("import from-bridge", "success" if existing_project else "failed"),
    ]
