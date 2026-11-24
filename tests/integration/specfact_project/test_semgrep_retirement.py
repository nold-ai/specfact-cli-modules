"""Verify Project import artifacts with the retired scanner available as a sentinel."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from specfact_cli.models.plan import Feature, PlanBundle, Product
from specfact_cli.models.source_tracking import SourceTracking

from specfact_project.import_cmd.commands import _extract_contracts


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
