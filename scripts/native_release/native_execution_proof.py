from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from icontract import require

import specfact_code_review.run.native_capsule
from scripts.native_release.boundary import COMPONENT_FILES, copy_component
from scripts.native_release.platforms import platform_context


ROOT = Path(__file__).resolve().parents[2]
PROOF = ROOT / "tests/native/proof_native_execution.py"
CORPUS = ROOT / "tests/fixtures/native-execution-proof/corpus.json"
SOURCE = ROOT / "packages/specfact-code-review/native/macos-arm64"
REPORT_LIMIT = 1024 * 1024


@dataclass(frozen=True)
class _ProofInputs:
    normal: Path
    stalled: Path
    normal_hashes: dict[str, str]
    stalled_hashes: dict[str, str]


def _read_report(junit: Path) -> bytes:
    try:
        with junit.open("rb") as stream:
            data = stream.read(REPORT_LIMIT + 1)
    except OSError as error:
        raise ValueError("native proof report is missing") from error
    if len(data) > REPORT_LIMIT:
        raise ValueError("native proof report exceeds bounds")
    return data


def _parse_report(data: bytes) -> ElementTree.Element:
    try:
        text = data.decode("utf-8")
        if "<!DOCTYPE" in text or "<!ENTITY" in text:
            raise ValueError("native proof report forbids declarations")
        return ElementTree.fromstring(text)
    except (UnicodeDecodeError, ElementTree.ParseError) as error:
        raise ValueError("native proof report is malformed") from error


def _outcome(case: ElementTree.Element) -> str:
    if any(
        child.tag not in {"error", "failure", "skipped", "system-out", "system-err", "properties"} for child in case
    ):
        return "invalid"
    return next((tag for tag in ("error", "failure", "skipped") if case.find(tag) is not None), "passed")


def _outcomes(document: ElementTree.Element) -> list[dict[str, str]]:
    return [
        {"case": case.get("name", ""), "owner": case.get("classname", ""), "outcome": _outcome(case)}
        for case in document.iter("testcase")
    ]


def _require_complete_results(junit: Path) -> list[str]:
    document = _parse_report(_read_report(junit))
    suites = document.findall("testsuite")
    if document.tag != "testsuites" or len(suites) != 1 or len(document) != 1:
        raise ValueError("native proof report requires one pytest suite")
    expected = json.loads(CORPUS.read_bytes())["collections"]["100"]["physical"]
    totals = {key: suites[0].get(key) for key in ("tests", "failures", "errors", "skipped")}
    if totals != {"tests": str(len(expected)), "failures": "0", "errors": "0", "skipped": "0"}:
        raise ValueError("native proof report has unsuccessful totals")
    observed = _outcomes(document)
    required = [
        {"case": name, "owner": "tests.native.proof_native_execution", "outcome": "passed"} for name in sorted(expected)
    ]
    if sorted(observed, key=lambda row: row["case"]) != required:
        raise ValueError("native proof report differs from the complete original successful corpus")
    return [row["case"] for row in observed]


def _group_exists(group: int) -> bool:
    try:
        os.killpg(group, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _cleanup_group(process: subprocess.Popen) -> None:
    for action in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(process.pid, action)
        except ProcessLookupError:
            process.wait(timeout=5)
            return
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            process.poll()
            if not _group_exists(process.pid):
                process.wait(timeout=max(0.01, deadline - time.monotonic()))
                return
            time.sleep(0.02)
    raise ValueError("native proof owned process group survived cleanup")


def _run_owned(command: list[str], *, cwd: Path, environment: dict[str, str], log: Path, timeout: float) -> None:
    with log.open("xb") as stream:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=stream,
            stderr=stream,
            start_new_session=True,
        )
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as error:
            raise ValueError("native proof process timeout") from error
        finally:
            if _group_exists(process.pid):
                _cleanup_group(process)
        if returncode != 0:
            raise ValueError(f"native proof process exit {returncode}")


def _install_provenance(component: Path) -> None:
    provenance = component / "provenance"
    provenance.mkdir(mode=0o700)
    metadata = provenance / "native-component.json"
    metadata.write_bytes((component / "component.json").read_bytes())
    metadata.chmod(0o400)


def _component_hashes(component: Path) -> dict[str, str]:
    if component.is_symlink() or not component.is_dir():
        raise ValueError("native proof fixture root is missing or unsafe")
    members = list(component.rglob("*"))
    expected = COMPONENT_FILES | {"component.json", "provenance/native-component.json"}
    actual = {path.relative_to(component).as_posix() for path in members if path.is_file()}
    if any(path.is_symlink() for path in members) or actual != expected:
        raise ValueError("native proof fixture file closure differs")
    metadata = (component / "component.json").read_bytes()
    if metadata != (component / "provenance/native-component.json").read_bytes():
        raise ValueError("native proof fixture provenance differs")
    hashes = json.loads(metadata)["files"]
    if set(hashes) != COMPONENT_FILES:
        raise ValueError("native proof fixture component closure differs")
    return hashes


def _admit_component(component: Path) -> dict[str, str]:
    hashes = _component_hashes(component)
    for name, digest in hashes.items():
        path = component / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("native proof fixture digest differs")
        if (
            name.startswith("bin/")
            and not specfact_code_review.run.native_capsule.inspect_native_signature(path)["hardened_runtime"]
        ):
            raise ValueError("native proof fixture lacks hardened runtime")
    return hashes


def _prepare_inputs(delivered: Path, private_work: Path) -> _ProofInputs:
    normal = private_work / "normal"
    copy_component(delivered, normal)
    _install_provenance(normal)
    normal_hashes = _admit_component(normal)
    source = private_work / "source"
    shutil.copytree(SOURCE, source, ignore=shutil.ignore_patterns("build", "__pycache__", "*.pyc"))
    bootstrap = source / "bootstrap.c"
    contents = bootstrap.read_bytes()
    anchor = b"    uint32_t marker = SPECFACT_MARKER_READY;"
    if contents.count(anchor) != 1:
        raise ValueError("native proof bootstrap READY anchor is not unique")
    bootstrap.write_bytes(contents.replace(anchor, b"    if (raise(SIGSTOP)) return 72; for (;;) pause();\n" + anchor))
    requirement = private_work / "python.requirement"
    requirement.write_text('cdhash H"0000000000000000000000000000000000000000"\n')
    build = private_work / "build"
    environment = {
        key: value
        for key, value in os.environ.items()
        if not (key.startswith("SPECFACT_") and key.endswith("_REQUIREMENT_FILE"))
    }
    environment.update(SPECFACT_NATIVE_BUILD_DIR=str(build), SPECFACT_PYTHON_REQUIREMENT_FILE=str(requirement))
    _run_owned(
        [str(source / "build.sh")], cwd=source, environment=environment, log=private_work / "build.log", timeout=120
    )
    _install_provenance(build)
    stalled = private_work / "stalled"
    copy_component(build, stalled)
    _install_provenance(stalled)
    return _ProofInputs(normal, stalled, normal_hashes, _admit_component(stalled))


@require(
    lambda delivered, output: not output.resolve().is_relative_to(delivered.resolve()),
    error=lambda output: (
        FileExistsError(str(output))
        if output.exists() or output.is_symlink()
        else ValueError("native proof output must be outside delivered input")
    ),
)
def require_native_execution_proof(delivered: Path, output: Path) -> None:
    context = platform_context(os.environ.get("PLATFORM_LABEL", "local"))
    output.mkdir(mode=0o700)
    private = output / "private"
    private.mkdir(mode=0o700)
    inputs = _prepare_inputs(delivered, private)
    environment = dict(os.environ)
    environment.pop("PYTEST_ADDOPTS", None)
    environment.update(
        SPECFACT_NATIVE_EXECUTION_BUILD=str(inputs.normal),
        SPECFACT_NATIVE_STALLED_STARTUP_BUILD=str(inputs.stalled),
        SPECFACT_NATIVE_EXECUTION_REPETITIONS="100",
        PYTHONDONTWRITEBYTECODE="1",
    )
    junit = private / "junit.xml"
    command = [sys.executable, "-m", "pytest", "-o", "addopts=", "-o", "xfail_strict=true", "-n", "0"]
    if environment.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD"):
        command.extend(["-p", "xdist.plugin"])
    command.extend([str(PROOF.relative_to(ROOT)), f"--junitxml={junit}"])
    passed = False
    try:
        _run_owned(command, cwd=ROOT, environment=environment, log=private / "pytest.log", timeout=1200)
        _require_complete_results(junit)
        passed = True
    finally:
        _retain_results(junit, output, inputs, context, passed=passed)


def _retain_results(junit: Path, output: Path, inputs: _ProofInputs, context: dict[str, str], *, passed: bool) -> None:
    outcomes: list[dict[str, str]] = []
    try:
        data = _read_report(junit)
    except ValueError as error:
        report_status = str(error)
    else:
        (output / "junit.xml").write_bytes(data)
        try:
            outcomes = _outcomes(_parse_report(data))
        except ValueError as error:
            report_status = str(error)
        else:
            report_status = "parsed"
    encoded = json.dumps(outcomes, sort_keys=True).encode()
    if len(encoded) > REPORT_LIMIT:
        report_status = "outcomes-oversized"
        encoded = b"[]"
    (output / "outcomes.json").write_bytes(encoded)
    (output / "summary.json").write_text(
        json.dumps(
            {
                "schema": "specfact-native-execution-proof-v1",
                "status": "PASS" if passed else "FAIL",
                "repetitions": 100,
                "cases": len(outcomes),
                "report_status": report_status,
                "source_sha": os.environ["SOURCE_SHA"],
                "proof_sha256": hashlib.sha256(PROOF.read_bytes()).hexdigest(),
                "corpus_sha256": hashlib.sha256(CORPUS.read_bytes()).hexdigest(),
                "adapter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "normal_files": inputs.normal_hashes,
                "stalled_files": inputs.stalled_hashes,
                "scope": "exact delivered normal bytes and separately compiled signed test-only stalled fixture",
                "production_eligible": False,
                "platform": context,
                "github_run_id": os.environ.get("GITHUB_RUN_ID"),
                "github_job": os.environ.get("GITHUB_JOB"),
            },
            sort_keys=True,
        )
    )
