"""Image handoff must precede initializers and preserve genuine traps."""

import importlib.util
import os
import tempfile
from pathlib import Path

import pytest


SOURCE = Path(__file__).parents[2] / "scripts/macos_managed_boundary/control.py"


@pytest.fixture(name="control")
def fixture_control():
    spec = importlib.util.spec_from_file_location("exec_control", SOURCE)
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_initializer_ordering_is_required(control):
    status = {
        "exit": 37,
        "signal": 0,
        "traced": True,
        "output": "target-initializer-ns=101\ntarget-entry\ntarget-denials-ok\n",
    }
    control.verify_exec_status(status, {"verified_ns": 100, "held": False}, 6)
    for output in (
        "target-entry\ntarget-denials-ok\n",
        status["output"].replace("101", "99"),
        status["output"] + "target-initializer-ns=102\n",
    ):
        with pytest.raises(RuntimeError):
            control.verify_exec_status({**status, "output": output}, {"verified_ns": 100, "held": False}, 6)


@pytest.mark.skipif(os.environ.get("SPECFACT_NATIVE_CONTROL") != "1", reason="explicit native fixture run")
def test_real_image_and_signal_handoff(control):
    with tempfile.TemporaryDirectory(dir="/private/tmp", prefix="sf-exec-test-") as temporary:
        root = Path(temporary).resolve()
        broker, observer, inventory = control.build(root)
        assert {item["name"] for item in inventory} == {"worker", "target", "observer", "broker"}
        trials = control.exec_trials(broker, observer, root)
        assert all(item["passed"] for item in trials)
        assert {item["case"] for item in trials} == set(control.EXEC_PROTOCOL_CASES)


@pytest.mark.skipif(os.environ.get("SPECFACT_NATIVE_CONTROL") != "1", reason="explicit native fixture run")
def test_real_exec_lifecycle_transitions(control):
    with tempfile.TemporaryDirectory(dir="/private/tmp", prefix="sf-exec-life-") as temporary:
        root = Path(temporary).resolve()
        broker, observer, _inventory = control.build(root)
        for case in control.EXEC_LIFECYCLE_CASES:
            result = control.lifecycle_trial(broker, observer, root, case)
            assert result["passed"]
            assert result["observation_seconds"] <= 5
