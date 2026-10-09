"""Retired sampler metadata cannot alter ordinary production dispatch."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from specfact_code_review.run import runner, target_launch
from specfact_code_review.run.sandbox import BubblewrapIdentity


MARKER = "SPECFACT_CODE_REVIEW_CROSSHAIR_STACK_SAMPLES"


@pytest.mark.parametrize("value", [True, False, "1", 1, None, [], {}])
def test_retired_request_fields_cannot_enable_diagnosis(tmp_path, value):
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"member": "contracts", "paths": ["source.py"], "stack_samples": value}))
    assert runner._load_capsule_request(request) == (
        "contracts",
        [Path("/opt/specfact/snapshot/source.py")],
        False,
        (),
        False,
    )


@pytest.mark.parametrize("module", ["crosshair", "pylint", "pytest-observe"])
def test_retired_marker_is_not_forwarded(monkeypatch, module):
    monkeypatch.setenv(MARKER, "1")
    monkeypatch.setattr(target_launch, "member_mounts", lambda domain: [])
    monkeypatch.setattr(target_launch, "interpreter_command", lambda arguments: ["python", *arguments])
    command = target_launch.target_command(module, ["check", "--per_path_timeout", "2", "source.py"])
    assert MARKER not in command
    assert "--clearenv" in command and "--unshare-all" in command
    assert command[-5:] == [module, "check", "--per_path_timeout", "2", "source.py"]


@pytest.fixture
def capsule_runtime(tmp_path):
    capsule = tmp_path / "capsule"
    capsule.mkdir()
    return runner.CapsuleRuntime(
        root=capsule,
        identity="sha256:" + "a" * 64,
        interpreter="/opt/specfact/python/bin/python",
        bootstrap="/opt/specfact/bootstrap/runner.py",
        bubblewrap=BubblewrapIdentity(
            path="/fixture/bwrap",
            format="ELF",
            architecture="x86_64",
            linkage="static",
            interpreter=(),
            needed=(),
            sha256="a" * 64,
            descriptor_digest="b" * 64,
        ),
        environment_id="test-environment",
    )


@pytest.fixture
def captured_request(monkeypatch):
    monkeypatch.setattr(runner, "preflight_reserved_imports", lambda context: SimpleNamespace(status="PASS"))
    observed = {}

    def execute(plan, bubblewrap, *, extra_argv):
        observed.update(json.loads((plan.mount_for("policy").source / "request.json").read_text()))
        (plan.mount_for("output").source / "result.json").write_text(
            json.dumps(
                {
                    "member": observed["member"],
                    "execution_state": "ran",
                    "evidence_outcome": "PASS",
                    "findings": [],
                    "diagnostic": "",
                }
            )
        )
        return SimpleNamespace(status="PASS")

    monkeypatch.setattr(runner, "execute_launch_plan", execute)
    return observed


@pytest.mark.parametrize("member,enabled", [("ruff", False), ("ruff", True), ("contracts", False), ("contracts", True)])
def test_retired_marker_cannot_change_private_request(monkeypatch, capsule_runtime, captured_request, member, enabled):
    snapshot = capsule_runtime.root.parent / "snapshot"
    snapshot.mkdir()
    source = snapshot / "source.py"
    source.write_text("value = 1\n")
    monkeypatch.setenv(MARKER, "1" if enabled else "0")
    response = runner._execute_capsule_member(
        runner.CapsuleMemberExecutionRequest(
            runtime=capsule_runtime,
            member=member,
            invocation_id="diagnostic-fixture",
            snapshot_root=snapshot,
            files=[source],
            options=runner.ReviewOptions(),
        )
    )
    assert response["evidence_outcome"] == "PASS"
    expected = {
        "adapter_argv": [],
        "bug_hunt": False,
        "complete_pytest_inventory": False,
        "member": member,
        "paths": ["source.py"],
    }
    assert captured_request == expected
