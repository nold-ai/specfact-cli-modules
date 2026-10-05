"""Native admission must close identity races before target initializers."""

import importlib.util
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest


SOURCE = Path(__file__).parents[2] / "scripts/macos_managed_boundary/control.py"


@pytest.fixture(name="control")
def fixture_control():
    spec = importlib.util.spec_from_file_location("admission_control", SOURCE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.skipif(os.environ.get("SPECFACT_NATIVE_CONTROL") != "1", reason="explicit native acceptance")
def test_signed_target_swap_after_launch_is_rejected_before_initializers(control):
    # sockaddr_un is bounded; pytest roots are not guaranteed to fit.
    with TemporaryDirectory(prefix="sf-admit-", dir="/private/tmp") as directory:
        root = Path(directory)
        broker, observer, _inventory = control.build(root)
        result = control.identity_swap_trial(broker, observer, root)
    assert result["passed"] is True
    assert result["image_rejection"]["stage"] == "foreign"
    assert result["image_rejection"]["exec_identity_failure"] == result["worker_identity"]["pid"]
    assert result["observation_seconds"] <= 5
    assert result["job_removed"] is True
    assert result["image_rejection"]["output_complete"] is True
    assert result["image_rejection"]["initializer_seen"] is False


@pytest.mark.skipif(os.environ.get("SPECFACT_NATIVE_CONTROL") != "1", reason="explicit native acceptance")
@pytest.mark.parametrize("kind", ["task", "thread"])
def test_confined_target_cannot_replace_broker_exception_endpoint(control, kind):
    with TemporaryDirectory(prefix="sf-port-", dir="/private/tmp") as directory:
        root = Path(directory)
        broker, observer, _inventory = control.build(root)
        result = control.exception_port_trial(broker, observer, root, kind)
    assert result["passed"] is True
    assert result["status"]["exit"] == 37
    assert result["installed"] is False


@pytest.mark.skipif(os.environ.get("SPECFACT_NATIVE_CONTROL") != "1", reason="explicit native acceptance")
def test_worker_identity_is_verified_while_spawn_suspended(control):
    with TemporaryDirectory(prefix="sf-bootstrap-", dir="/private/tmp") as directory:
        root = Path(directory)
        broker, observer, _inventory = control.build(root)
        with control.Invocation(broker, observer, root) as invocation:
            client = invocation.connect()
            launched = client.launch(1)
            marker = invocation.wait_event("bootstrap_identity", launched["pid"])
            trace = invocation.wait_event("trace", launched["pid"])
            status = client.request(2, handle=launched["handle"])
    assert marker == {
        "bootstrap_identity": launched["pid"],
        "suspended": True,
        "output_empty": True,
    }
    assert trace["trace"] == launched["pid"]
    assert status["exit"] == 37
