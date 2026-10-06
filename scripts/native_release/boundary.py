"""Exercise lifecycle and kernel exception denial against delivered component bytes."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from tests.unit import test_macos_native_broker_wait as harness


COMPONENT_FILES = frozenset(
    {
        "bin/specfact-native-broker",
        "bin/specfact-native-bootstrap",
        "bin/specfact-native-verifier",
        "bin/specfact-native-self-test",
        "policy/profile.sb",
    }
)
REPETITIONS = 100


def copy_component(source: Path, destination: Path) -> None:
    """Relocate final bytes for the probe; never compile, patch or re-sign them."""
    metadata = (source / "provenance/native-component.json").read_bytes()
    document = json.loads(metadata)
    if set(document["files"]) != COMPONENT_FILES:
        raise ValueError("delivered component file closure differs")
    contents = {}
    for name in COMPONENT_FILES:
        path = source / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("delivered component path differs")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != document["files"][name]:
            raise ValueError("delivered component digest differs")
        contents[name] = data
    destination.mkdir(mode=0o700)
    for name, data in contents.items():
        output = destination / name
        output.parent.mkdir(mode=0o700, exist_ok=True)
        output.write_bytes(data)
        output.chmod(0o500 if name.startswith("bin/") else 0o400)
    metadata_path = destination / "component.json"
    metadata_path.write_bytes(metadata)
    metadata_path.chmod(0o400)


def _invocation(root: Path, *, exception_probe: bool) -> Path:
    invocation = root / "invocation"
    invocation.mkdir(mode=0o700)
    for name, mode in (("project", 0o500), ("output", 0o700), ("temporary", 0o700)):
        (invocation / name).mkdir(mode=mode)
    (invocation / "temporary/hold").touch()
    if exception_probe:
        (invocation / "temporary/exception-port-probe").touch()
    return invocation


def _positive_exception_probe(capsule: Path, root: Path) -> None:
    positive = root / "positive"
    positive.mkdir()
    (positive / "exception-port-probe").touch()
    result = subprocess.run(
        [str(capsule / "bin/specfact-native-self-test"), str(positive)], capture_output=True, check=False, timeout=5
    )
    if result.returncode != 37 or json.loads((positive / "exception-port-results.json").read_bytes()) != [0, 0, 0, 0]:
        raise ValueError("delivered exception-port positive control failed")


def _assert_worker_cleanup(controller, invocation: Path, *, exception_probe: bool) -> None:
    launched = json.loads(harness._line(controller, 20))
    identities = {pid: harness._identity(pid) for pid in (launched["worker"], launched["broker"])}
    if not all(identities.values()) or harness._line(controller, 5) != "WAIT_SENT":
        raise ValueError("delivered controller did not enter held WAIT")
    if exception_probe:
        values = json.loads((invocation / "temporary/exception-port-results.json").read_bytes())
        if len(values) != 4 or any(value == 0 for value in values):
            raise ValueError("delivered component allowed exception-port mutation")
    deadline = time.monotonic() + 5
    controller.kill()
    controller.wait(timeout=2)
    while time.monotonic() < deadline:
        disappeared = all(harness._identity(pid) != birth for pid, birth in identities.items())
        if disappeared and time.monotonic() <= deadline:
            return
        time.sleep(0.02)
    raise ValueError("delivered worker or broker survived controller loss")


def _controller_case(capsule: Path, root: Path, mode: str) -> None:
    exception_probe = mode == "exception-denial"
    invocation = _invocation(root, exception_probe=exception_probe)
    if exception_probe:
        _positive_exception_probe(capsule, root)
    option = "--failure-controller" if mode == "bootstrap-failure" else "--controller"
    controller = subprocess.Popen(
        [sys.executable, str(Path(harness.__file__).resolve()), option, str(capsule), str(invocation)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    try:
        if mode == "bootstrap-failure":
            if harness._line(controller, 20) != "REJECTED_BEFORE_READY" or controller.wait(timeout=5) != 0:
                raise ValueError("delivered failed bootstrap reached target")
        else:
            _assert_worker_cleanup(controller, invocation, exception_probe=exception_probe)
    finally:
        if controller.poll() is None:
            controller.kill()
            controller.wait(timeout=2)
        for stream in (controller.stdout, controller.stderr):
            if stream:
                stream.close()


def repeat_controller_case(component: Path, output: Path, mode: str) -> None:
    for _index in range(REPETITIONS):
        with tempfile.TemporaryDirectory(dir=output, prefix="probe-") as directory:
            _controller_case(component, Path(directory), mode)


def delivered_boundary(source: Path, output: Path) -> None:
    """Require 100 actual runs per delivered lifecycle case; no fixture compilation."""
    output.mkdir(mode=0o700)
    component = output / "component"
    copy_component(source, component)
    try:
        counts = {}
        for mode in ("controller-loss", "bootstrap-failure", "exception-denial"):
            repeat_controller_case(component, output, mode)
            counts[mode] = REPETITIONS
        (output / "delivered-boundary.json").write_text(
            json.dumps(
                {
                    "schema": "specfact-delivered-lifecycle-v1",
                    "counts": counts,
                    "component_files": json.loads((component / "component.json").read_bytes())["files"],
                    "production_eligible": False,
                },
                sort_keys=True,
            )
        )
    finally:
        shutil.rmtree(component)
