"""CI acceptance cannot omit required controls or overlap timed-out native suites."""

from __future__ import annotations

import ast
import importlib.machinery
import importlib.util
import json
from pathlib import Path
from types import CodeType

import pytest
import yaml


ROOT = Path(__file__).parents[2]


class _WorkflowDefinitionsLoader(importlib.machinery.SourceFileLoader):
    """Load actual CI definitions while excluding the workflow entry point."""

    def __init__(self, tree: ast.Module):
        super().__init__("boundary_ci_definitions", "code-review-macos-boundary.yml")
        self.tree = tree

    def get_code(self, fullname: str) -> CodeType:
        if fullname != self.name:
            raise ImportError("workflow definition identity mismatch")
        return compile(self.tree, self.path, "exec")


@pytest.fixture(name="boundary_ci")
def fixture_boundary_ci():
    workflow = yaml.safe_load((ROOT / ".github/workflows/code-review-macos-boundary.yml").read_text())
    code = workflow["jobs"]["native-boundary"]["steps"][-1]["run"]
    tree = ast.parse(code.split("python - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0])
    tree.body = [node for node in tree.body if not isinstance(node, ast.Raise)]
    loader = _WorkflowDefinitionsLoader(tree)
    spec = importlib.util.spec_from_file_location(loader.name, loader.path, loader=loader)
    assert spec
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    namespace = module.__dict__
    namespace["SOURCE"] = ROOT / "scripts/macos_managed_boundary"
    return namespace


@pytest.fixture(name="startup_receipt")
def fixture_startup_receipt(boundary_ci):
    sources = {"broker": "startup_broker.c", "worker": "startup_worker.c", "observer": "startup_observe.c"}
    trials = [{"mode": mode, "passed": True} for mode in boundary_ci["STARTUP_RACES"] for _ in range(100)]
    trials.extend(
        [
            {"mode": "normal", "passed": True},
            {"mode": "runtime-trap", "passed": True},
            {"mode": "pretrace", "passed": True, "abandon_process_group": True, "survived": True},
        ]
    )
    return {
        "schema_version": "specfact-managed-startup-experiment-v1",
        "architecture": "arm64",
        "os_build": "26A434",
        "repetitions": 100,
        "startup_subset_passed": True,
        "repetition_gate_passed": True,
        "production_approved": False,
        "signed_boundary_verified": False,
        "signing_mode": "ad-hoc",
        "hardened_runtime": True,
        "trials": trials,
        "completed_races": dict.fromkeys(boundary_ci["STARTUP_RACES"], 100),
        "probe_control": {"passed": True},
        "profile_sha256": boundary_ci["sha256"](boundary_ci["SOURCE"] / "fixture.sb"),
        "artifacts": [
            {
                "name": name,
                "source_sha256": boundary_ci["sha256"](boundary_ci["SOURCE"] / source),
                "sha256": "0" * 64,
                "signing": "flags=0x10002(adhoc,runtime)\nSignature=adhoc",
            }
            for name, source in sources.items()
        ],
    }


def test_complete_startup_controls_are_accepted(boundary_ci, startup_receipt):
    assert boundary_ci["checked_receipt"]("startup", startup_receipt, {"os_build": "26A434"})["result"] == "passed"


@pytest.mark.parametrize("mode", ["normal", "runtime-trap"])
def test_missing_mandatory_startup_control_is_rejected(boundary_ci, startup_receipt, mode):
    startup_receipt["trials"] = [item for item in startup_receipt["trials"] if item["mode"] != mode]
    with pytest.raises(AssertionError):
        boundary_ci["checked_receipt"]("startup", startup_receipt, {"os_build": "26A434"})


def test_timeout_never_starts_another_native_suite(boundary_ci, monkeypatch, tmp_path):
    root = tmp_path / "specfact-macos-boundary"
    root.mkdir()
    (root / "platform.json").write_text(json.dumps({"os_build": "26A434"}))
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary"))
    calls = []

    def timeout(name, *_args):
        calls.append(name)
        return {"suite": name, "result": "failed", "category": "helper_timeout"}

    monkeypatch.setitem(boundary_ci, "run_suite", timeout)
    assert boundary_ci["main"]() == 1
    assert calls == ["startup"]
