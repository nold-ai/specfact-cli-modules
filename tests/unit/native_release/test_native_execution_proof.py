from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree

import pytest
import yaml

import specfact_code_review.run.native_capsule
import specfact_code_review.run.runtime_discovery
from scripts.native_release import acceptance, artifacts, boundary, native_execution_proof as proof
from scripts.native_release.boundary import COMPONENT_FILES
from scripts.native_release.native_execution_proof import (
    _admit_component,
    _cleanup_group,
    _prepare_inputs,
    _ProofInputs,
    _require_complete_results,
    _run_owned,
)


NAMES = json.loads(proof.CORPUS.read_bytes())["collections"]["100"]["physical"]


def _mutate_outcome(path, mutation):
    tree = ElementTree.parse(path)
    case = next(tree.iter("testcase"), None)
    if mutation in {"skipped", "failure", "error"}:
        assert case is not None
        ElementTree.SubElement(case, mutation)
    if mutation == "xfail":
        assert case is not None
        ElementTree.SubElement(case, "skipped", type="pytest.xfail")
    if mutation == "wrong-owner":
        assert case is not None
        case.set("classname", "other.owner")
    if mutation == "wrong-total":
        next(tree.iter("testsuite")).set("tests", "1")
    tree.write(path)


def _write_execution_fixture(path, execution):
    _junit(path, NAMES)
    if execution == "malformed":
        path.write_text("<broken")
    if execution == "oversized":
        path.write_bytes(b"x" * (1024 * 1024 + 1))
    if execution == "skipped":
        tree = ElementTree.parse(path)
        ElementTree.SubElement(next(tree.iter("testcase")), "skipped")
        tree.write(path)
    if execution == "nonzero":
        raise ValueError("native proof process exit 7")


def _assert_retained_result(output, execution):
    assert (output / "summary.json").is_file(), "Actual failure must retain a bounded failure summary"
    summary = json.loads((output / "summary.json").read_bytes())
    assert summary["status"] == ("PASS" if execution == "pass" else "FAIL")
    assert summary["source_sha"] == "a" * 40
    assert summary["production_eligible"] is False
    assert (output / "junit.xml").exists() is (execution != "oversized")
    if (output / "junit.xml").exists():
        assert (output / "junit.xml").read_bytes() == (output / "private/junit.xml").read_bytes()
    outcomes = json.loads((output / "outcomes.json").read_bytes())
    if execution in {"pass", "nonzero", "skipped"}:
        assert len(outcomes) == 702
        assert outcomes[0]["outcome"] == ("skipped" if execution == "skipped" else "passed")
    else:
        assert outcomes == []


def _junit(path: Path, names: list[str]) -> Path:
    root = ElementTree.Element("testsuites")
    suite = ElementTree.SubElement(root, "testsuite", tests=str(len(names)), failures="0", errors="0", skipped="0")
    for name in names:
        ElementTree.SubElement(
            suite, "testcase", classname="tests.native.proof_native_execution", name=name, time="0.1"
        )
    ElementTree.ElementTree(root).write(path)
    return path


def test_complete_original_results_are_admitted(tmp_path):
    assert _require_complete_results(_junit(tmp_path / "junit.xml", NAMES)) == NAMES


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "duplicate",
        "extra",
        "empty",
        "skipped",
        "xfail",
        "failure",
        "error",
        "wrong-owner",
        "wrong-total",
        "oversized",
    ],
)
def test_incomplete_or_unsuccessful_results_refuse(tmp_path, mutation):
    names = list(NAMES)
    if mutation == "missing":
        names.pop()
    if mutation == "duplicate":
        names[-1] = names[0]
    if mutation == "extra":
        names.append("test_extra")
    if mutation == "empty":
        names.clear()
    path = _junit(tmp_path / "junit.xml", names)
    _mutate_outcome(path, mutation)
    if mutation == "oversized":
        path.write_bytes(path.read_bytes() + b" " * (1024 * 1024))
    with pytest.raises(ValueError, match="native proof"):
        _require_complete_results(path)


@pytest.mark.parametrize(
    "content", [None, b"", b"<broken", b"<!DOCTYPE testsuites [<!ENTITY x 'value'>]><testsuites/>"]
)
def test_missing_and_malformed_results_refuse(tmp_path, content):
    path = tmp_path / "junit.xml"
    if content is not None:
        path.write_bytes(content)
    with pytest.raises(ValueError, match="native proof"):
        _require_complete_results(path)


def test_owned_process_has_an_independent_group(tmp_path):
    log = tmp_path / "child.log"
    _run_owned(
        [sys.executable, "-c", "import os; print(os.getpid(), os.getpgrp())"],
        cwd=tmp_path,
        environment=dict(os.environ),
        log=log,
        timeout=5,
    )
    pid, group = map(int, log.read_text().split())
    assert pid == group
    with pytest.raises(ProcessLookupError):
        os.killpg(group, 0)


def test_nonzero_owned_process_never_qualifies(tmp_path):
    with pytest.raises(ValueError, match=r"native proof.*exit"):
        _run_owned(
            [sys.executable, "-c", "raise SystemExit(7)"],
            cwd=tmp_path,
            environment=dict(os.environ),
            log=tmp_path / "child.log",
            timeout=5,
        )


def test_timeout_reaps_owned_child_and_group(tmp_path, monkeypatch):
    children = {}
    timeouts = []
    wait = subprocess.Popen.wait

    def record(child, timeout=None):
        children[child.pid] = child
        timeouts.append(timeout)
        return wait(child, timeout=timeout)

    monkeypatch.setattr(subprocess.Popen, "wait", record)
    with pytest.raises(ValueError, match=r"native proof.*timeout"):
        _run_owned(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            cwd=tmp_path,
            environment=dict(os.environ),
            log=tmp_path / "child.log",
            timeout=0.1,
        )
    assert len(children) == 1
    child = next(iter(children.values()))
    assert child.poll() is not None
    assert timeouts[0] == 0.1 and all(timeout is not None for timeout in timeouts)
    with pytest.raises(ProcessLookupError):
        os.killpg(child.pid, 0)


def _component(root: Path) -> dict[str, str]:
    files = {}
    for name in COMPONENT_FILES:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(name.encode())
        target.chmod(0o500 if name.startswith("bin/") else 0o400)
        files[name] = hashlib.sha256(target.read_bytes()).hexdigest()
    metadata = json.dumps({"files": files, "broker_designated_requirement": "unit-only"}).encode()
    (root / "provenance").mkdir()
    (root / "provenance/native-component.json").write_bytes(metadata)
    return files


def test_preparation_preserves_normal_bytes_and_builds_private_stall(tmp_path, monkeypatch):
    delivered = tmp_path / "delivered"
    hashes = _component(delivered)
    work = tmp_path / "work"
    work.mkdir()
    builds = []

    def build(command, *, cwd, environment, log, timeout):
        builds.append(command)
        source = Path(command[0]).parent
        assert cwd == source
        assert log == work / "build.log"
        original = proof.SOURCE / "bootstrap.c"
        anchor = "    uint32_t marker = SPECFACT_MARKER_READY;"
        inserted = "    if (raise(SIGSTOP)) return 72; for (;;) pause();\n"
        assert (source / "bootstrap.c").read_bytes() == original.read_bytes().replace(
            anchor.encode(), (inserted + anchor).encode()
        )
        assert (source / "build.sh").read_bytes() == (proof.SOURCE / "build.sh").read_bytes()
        assert not (source / "build").exists()
        assert timeout == 120
        assert "SPECFACT_RUFF_REQUIREMENT_FILE" not in environment
        assert (
            Path(environment["SPECFACT_PYTHON_REQUIREMENT_FILE"]).read_text(encoding="utf-8")
            == 'cdhash H"0000000000000000000000000000000000000000"\n'
        )
        target = Path(environment["SPECFACT_NATIVE_BUILD_DIR"])
        _component(target)
        (target / "component.json").write_bytes((target / "provenance/native-component.json").read_bytes())
        (target / "provenance/native-component.json").unlink()
        (target / "provenance").rmdir()

    monkeypatch.setattr(proof, "_run_owned", build)
    monkeypatch.setattr(
        specfact_code_review.run.native_capsule, "inspect_native_signature", lambda _path: {"hardened_runtime": True}
    )
    monkeypatch.setenv("SPECFACT_RUFF_REQUIREMENT_FILE", "/unrelated")
    inputs = _prepare_inputs(delivered, work)
    assert len(builds) == 1
    assert inputs.normal_hashes == hashes
    assert inputs.stalled_hashes == hashes
    assert inputs.normal not in (inputs.stalled, delivered)
    for root in (inputs.normal, inputs.stalled):
        assert (root / "provenance/native-component.json").read_bytes() == (root / "component.json").read_bytes()
        for name, expected in hashes.items():
            assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected


def test_changed_delivered_bytes_refuse_before_build(tmp_path, monkeypatch):
    delivered = tmp_path / "delivered"
    _component(delivered)
    (delivered / "bin/specfact-native-bootstrap").chmod(0o700)
    (delivered / "bin/specfact-native-bootstrap").write_bytes(b"changed")
    monkeypatch.setattr(proof, "_run_owned", lambda *_args, **_kwargs: pytest.fail("changed bytes reached build"))
    with pytest.raises(ValueError, match="digest differs"):
        _prepare_inputs(delivered, tmp_path)


def test_missing_stalled_root_refuses_before_signature_inspection(tmp_path, monkeypatch):
    monkeypatch.setattr(
        specfact_code_review.run.native_capsule,
        "inspect_native_signature",
        lambda _path: pytest.fail("missing fixture reached signature inspection"),
    )
    with pytest.raises(ValueError, match="fixture root is missing"):
        _admit_component(tmp_path / "missing-stall")


def test_existing_output_cannot_reuse_a_success_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(proof, "platform_context", lambda _label: {})
    monkeypatch.setattr(proof, "_prepare_inputs", lambda *_args: pytest.fail("stale output reached preparation"))
    output = tmp_path / "existing"
    output.mkdir()
    (output / "summary.json").write_text('{"status":"PASS"}')
    with pytest.raises(FileExistsError):
        proof.require_native_execution_proof(tmp_path / "delivered", output)


@contextmanager
def _sleeping_child() -> Iterator[subprocess.Popen]:
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
    try:
        yield child
    finally:
        child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)


def test_timeout_cleans_real_descendant_group_without_signalling_unrelated_child(tmp_path, monkeypatch):
    children = {}
    timeouts = []
    wait = subprocess.Popen.wait

    def record(child, timeout=None):
        children[child.pid] = child
        timeouts.append(timeout)
        return wait(child, timeout=timeout)

    script = tmp_path / "tree.py"
    script.write_text(
        "import os, signal, subprocess, sys, time\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        "def terminate(_signum, _frame):\n"
        "    child.wait(timeout=2)\n"
        "signal.signal(signal.SIGTERM, terminate)\n"
        "print(child.pid, os.getpgrp(), flush=True)\n"
        "while True: time.sleep(1)\n"
    )
    log = tmp_path / "tree.log"
    with _sleeping_child() as unrelated:
        monkeypatch.setattr(subprocess.Popen, "wait", record)
        with pytest.raises(ValueError, match=r"native proof.*timeout"):
            _run_owned([sys.executable, str(script)], cwd=tmp_path, environment=dict(os.environ), log=log, timeout=1)
        descendant, group = map(int, log.read_text().split())
        assert len(children) == 1 and group in children
        assert children[group].returncode == -9
        assert timeouts[0] == 1 and all(timeout is not None for timeout in timeouts)
        with pytest.raises(ProcessLookupError):
            os.kill(descendant, 0)
        with pytest.raises(ProcessLookupError):
            os.killpg(group, 0)
        assert unrelated.poll() is None
    assert unrelated.poll() is not None


@pytest.mark.parametrize("execution", ["pass", "nonzero", "skipped", "malformed", "oversized"])
def test_operation_retains_bounded_actual_results_and_failure(tmp_path, monkeypatch, execution):
    monkeypatch.setattr(proof, "platform_context", lambda _label: {"runner": "unit"})
    inputs = _ProofInputs(tmp_path / "normal", tmp_path / "stalled", {}, {})
    monkeypatch.setattr(proof, "_prepare_inputs", lambda *_args: inputs)
    monkeypatch.setenv("SOURCE_SHA", "a" * 40)
    monkeypatch.setenv("PYTEST_ADDOPTS", "--maxfail=1 --collect-only")
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")

    def execute(command, *, cwd, environment, log, timeout):
        assert cwd == proof.ROOT
        assert log == output / "private/pytest.log"
        assert "PYTEST_ADDOPTS" not in environment
        assert "xdist.plugin" in command and "addopts=" in command and "xfail_strict=true" in command
        assert command[command.index("-n") + 1] == "0"
        assert environment["SPECFACT_NATIVE_EXECUTION_REPETITIONS"] == "100"
        assert environment["SPECFACT_NATIVE_EXECUTION_BUILD"] == str(inputs.normal)
        assert environment["SPECFACT_NATIVE_STALLED_STARTUP_BUILD"] == str(inputs.stalled)
        assert timeout == 1200
        path = Path(next(arg.removeprefix("--junitxml=") for arg in command if arg.startswith("--junitxml=")))
        _write_execution_fixture(path, execution)

    monkeypatch.setattr(proof, "_run_owned", execute)
    output = tmp_path / "proof"
    if execution == "pass":
        proof.require_native_execution_proof(tmp_path / "delivered", output)
    else:
        with pytest.raises(ValueError, match="native proof"):
            proof.require_native_execution_proof(tmp_path / "delivered", output)
    _assert_retained_result(output, execution)


@pytest.mark.parametrize("placement", ["outside-suite", "nested-case"])
def test_hidden_extra_outcomes_refuse(tmp_path, placement):
    path = _junit(tmp_path / "junit.xml", NAMES)
    tree = ElementTree.parse(path)
    parent = tree.getroot() if placement == "outside-suite" else next(tree.iter("testcase"))
    ElementTree.SubElement(parent, "testcase", name="test_extra", classname="tests.native.proof_native_execution")
    tree.write(path)
    with pytest.raises(ValueError, match="native proof"):
        _require_complete_results(path)


def test_workflow_transports_only_bounded_proof_files_even_on_acceptance_failure():
    workflow = yaml.safe_load((proof.ROOT / ".github/workflows/native-capsule-release.yml").read_text())
    steps = workflow["jobs"]["execute"]["steps"]
    proof_artifacts = [step for step in steps if step.get("with", {}).get("name", "").startswith("native-execution-")]
    assert len(proof_artifacts) == 1
    assert proof_artifacts[0].get("if") == "always()"
    assert proof_artifacts[0]["with"]["path"].splitlines() == [
        "${{ runner.temp }}/acceptance/native-execution/junit.xml",
        "${{ runner.temp }}/acceptance/native-execution/outcomes.json",
        "${{ runner.temp }}/acceptance/native-execution/summary.json",
    ]
    receipt = next(step for step in steps if step.get("with", {}).get("name", "").startswith("receipt-"))
    assert receipt["with"]["path"] == "${{ runner.temp }}/acceptance/receipt.json"
    assert not receipt.get("if")


def test_local_acceptance_does_not_review_or_write_receipt_after_proof_failure(tmp_path, monkeypatch):
    exited = []

    @contextmanager
    def runtime(*_args):
        try:
            yield SimpleNamespace(root=tmp_path / "delivered")
        finally:
            exited.append(True)

    def refuse(*_args):
        raise ValueError("native proof refused")

    monkeypatch.setattr(acceptance, "platform_context", lambda _label: {"runner": "local"})
    monkeypatch.setattr(acceptance, "flask_project", lambda _work: (tmp_path, tmp_path / "config", []))
    monkeypatch.setattr(artifacts, "inspect_archive", lambda _path: object())
    monkeypatch.setattr(acceptance, "candidate_runtime", runtime)
    monkeypatch.setattr(boundary, "delivered_boundary", lambda *_args: None)
    monkeypatch.setattr(proof, "require_native_execution_proof", refuse)
    monkeypatch.setattr(
        specfact_code_review.run.runtime_discovery,
        "discover_project",
        lambda *_args, **_kwargs: pytest.fail("failed physical proof reached project preparation"),
    )
    monkeypatch.setattr(
        acceptance, "write_candidate_receipt", lambda *_args: pytest.fail("failed proof reached receipt")
    )
    output = tmp_path / "acceptance"
    with pytest.raises(ValueError, match="native proof refused"):
        acceptance.candidate_acceptance(tmp_path / "archive", output, "local")
    assert exited == [True]
    assert not (output / "receipt.json").exists()


@pytest.mark.parametrize("alias", [False, True])
def test_output_inside_delivered_refuses_before_writing(tmp_path, monkeypatch, alias):
    delivered = tmp_path / "delivered"
    delivered.mkdir()
    parent = delivered
    if alias:
        parent = tmp_path / "alias"
        parent.symlink_to(delivered, target_is_directory=True)
    output = parent / "proof"
    monkeypatch.setattr(proof, "platform_context", lambda _label: {})
    monkeypatch.setattr(proof, "_prepare_inputs", lambda *_args: pytest.fail("overlapping output reached preparation"))
    with pytest.raises(ValueError, match="output must be outside delivered input"):
        proof.require_native_execution_proof(delivered, output)
    assert not output.exists()
    assert not list(delivered.iterdir())


def test_existing_output_inside_delivered_keeps_file_exists_error(tmp_path, monkeypatch):
    monkeypatch.setattr(proof, "platform_context", lambda _label: {})
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(FileExistsError):
        proof.require_native_execution_proof(tmp_path, output)
    assert not list(output.iterdir())


@pytest.mark.parametrize("probe_denied", [False, True])
def test_cleanup_requires_real_disappearance_after_transient_probe_denial(monkeypatch, probe_denied):
    killpg = os.killpg
    observations = []
    denied = False

    def observe(group, action):
        nonlocal denied
        if action == 0 and probe_denied and not denied:
            denied = True
            observations.append("permission denied")
            raise PermissionError("group observation during exit")
        try:
            return killpg(group, action)
        except ProcessLookupError:
            observations.append("absent")
            raise

    with _sleeping_child() as child:
        monkeypatch.setattr(os, "killpg", observe)
        _cleanup_group(child)
        assert child.returncode == -signal.SIGTERM
        assert denied is probe_denied
        assert observations[-1] == "absent"
    assert child.poll() is not None


def test_permission_denied_cleanup_signal_never_qualifies(monkeypatch):
    def deny(_group, _action):
        raise PermissionError("cleanup authority denied")

    with _sleeping_child() as child:
        monkeypatch.setattr(os, "killpg", deny)
        with pytest.raises(PermissionError, match="cleanup authority denied"):
            _cleanup_group(child)
        assert child.poll() is None
    assert child.poll() is not None


def test_permanent_group_uncertainty_exhausts_original_cleanup_bounds(monkeypatch):
    ticks = iter([0, 1, 6, 7, 8, 13])
    actions = []

    def uncertain(_group, action):
        actions.append(action)
        if action == 0:
            raise PermissionError("synthetic persistent observation refusal")

    with _sleeping_child() as child:
        with monkeypatch.context() as controlled:
            controlled.setattr(os, "killpg", uncertain)
            controlled.setattr(proof.time, "monotonic", lambda: next(ticks))
            controlled.setattr(proof.time, "sleep", lambda _seconds: None)
            with pytest.raises(ValueError, match="owned process group survived cleanup"):
                _cleanup_group(child)
        assert child.poll() is None
        assert actions == [signal.SIGTERM, 0, signal.SIGKILL, 0]
    assert child.poll() is not None
