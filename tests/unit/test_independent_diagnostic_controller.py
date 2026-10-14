"""Exercise the inline diagnostic controller with controlled download bytes."""

from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
MARKER = "PY_DIAGNOSTIC_BOOTSTRAP"


@pytest.mark.parametrize("download", [b"print('SECRET_DOWNLOADED')", OSError("SECRET_NETWORK")])
def test_controller_rejects_unverified_bytes_before_execution(tmp_path, monkeypatch, capsys, download):
    import urllib.request

    steps = yaml.safe_load((ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())["jobs"][
        "independent-review"
    ]["steps"]
    step = next(item for item in steps if item.get("name") == "Observe failed independent review privately")
    trusted = tmp_path / "trusted"
    (trusted / "venv/bin").mkdir(parents=True)
    (trusted / "venv/bin/python").symlink_to(sys.executable)
    (trusted / "review-attempted").touch()
    candidate = tmp_path / "candidate"
    (candidate / "scripts").mkdir(parents=True)
    (candidate / "scripts/independent_review_diagnostic.py").write_text("print('SECRET_CANDIDATE')\n")
    assert MARKER in step["run"]

    def fetch(*_args, **_kwargs):
        if isinstance(download, OSError):
            raise download
        return io.BytesIO(download)

    executions = []
    monkeypatch.setattr(urllib.request, "urlopen", fetch)
    monkeypatch.setattr(os, "execve", lambda *_args: executions.append(True))
    monkeypatch.setattr(sys, "argv", ["-", str(trusted), str(candidate)])
    source = step["run"].split(f"<<'{MARKER}'\n", 1)[1].rsplit(MARKER, 1)[0]
    with pytest.raises(SystemExit) as stopped:
        exec(compile(source, "reviewed-controller", "exec"), {"__name__": "__main__"})
    assert stopped.value.code == 0
    assert executions == []
    output = capsys.readouterr()
    assert "SECRET" not in output.out + output.err
    assert json.loads(output.out)["status"] == "DIAGNOSTIC_UNAVAILABLE"


def test_controller_runs_after_both_projections_with_optional_cap():
    steps = yaml.safe_load((ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())["jobs"][
        "independent-review"
    ]["steps"]
    diagnostic = next(item for item in steps if item.get("name") == "Observe failed independent review privately")
    projection = next(item for item in steps if item.get("name") == "Project independent review failure privately")
    assert steps.index(diagnostic) > steps.index(projection)
    assert diagnostic["timeout-minutes"] == 15
    assert "github.event.pull_request.head.sha == '826948e710112a80b61c31c46ec8e57da5a25f22'" in diagnostic["if"]
    assert "$GITHUB_WORKSPACE/scripts/independent_review_diagnostic.py" not in diagnostic["run"]


def test_controller_executes_only_authenticated_private_copy(tmp_path, monkeypatch):
    import urllib.request

    steps = yaml.safe_load((ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())["jobs"][
        "independent-review"
    ]["steps"]
    step = next(item for item in steps if item.get("name") == "Observe failed independent review privately")
    payload = (ROOT / "scripts/independent_review_diagnostic.py").read_bytes()
    urls = []

    def fetch(url, **_kwargs):
        urls.append(url)
        return io.BytesIO(payload)

    executions = []
    monkeypatch.setattr(urllib.request, "urlopen", fetch)
    monkeypatch.setattr(os, "execve", lambda *args: executions.append(args))
    monkeypatch.setattr(sys, "argv", ["-", str(tmp_path), "/candidate"])
    source = step["run"].split(f"<<'{MARKER}'\n", 1)[1].rsplit(MARKER, 1)[0]
    exec(compile(source, "reviewed-controller", "exec"), {"__name__": "__main__"})
    assert len(executions) == 1
    executable, arguments, _environment = executions[0]
    assert executable == sys.executable
    assert arguments[:2] == [sys.executable, "-I"]
    copied = Path(arguments[2])
    assert copied.parent == tmp_path
    assert copied.read_bytes() == payload
    assert copied.stat().st_mode & 0o777 == 0o600
    assert urls == [
        "https://raw.githubusercontent.com/nold-ai/specfact-cli-modules/"
        "decb25a7b25536f127f7e7ecb89d6ea92264f7b8/scripts/independent_review_diagnostic.py"
    ]


def test_host_lifecycle_proofs_remain_required_in_both_test_routes():
    import tomllib

    proof = "tests/host/proof_independent_review_diagnostic.py"
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert proof in project["tool"]["hatch"]["envs"]["default"]["scripts"]["test"]
    assert proof in (ROOT / "tools/smart_test_coverage.py").read_text()
    workflow = (ROOT / ".github/workflows/pr-orchestrator.yml").read_text()
    assert "run: hatch run test" in workflow


def test_host_controller_cases_are_outside_sealed_subject_discovery():
    import ast

    expected = {
        "test_preparation_shell_preserves_failure_and_projects_incomplete": 9,
        "test_required_parent_preserves_leaf_budget_and_expiry": 2,
    }
    host = ast.parse((ROOT / "tests/host/proof_independent_review_diagnostic.py").read_text())
    functions = {node.name: node for node in host.body if isinstance(node, ast.FunctionDef)}
    for name, count in expected.items():
        function = functions[name]
        parametrization = next(node for node in function.decorator_list if isinstance(node, ast.Call))
        assert isinstance(parametrization.args[1], ast.List)
        assert len(parametrization.args[1].elts) == count
    for path in ("test_capsule_review_projection.py", "test_independent_diagnostic_controller.py"):
        unit = ast.parse((ROOT / "tests/unit" / path).read_text())
        names = {node.name for node in unit.body if isinstance(node, ast.FunctionDef)}
        assert names.isdisjoint(expected)
