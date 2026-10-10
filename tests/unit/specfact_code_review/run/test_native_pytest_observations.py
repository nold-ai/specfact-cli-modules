from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specfact_code_review.run import native_worker, runner
from tests.unit.specfact_code_review.run.test_native_worker import _argv, _roots, _set_member


def _transport(tmp_path: Path) -> native_worker.ReplayTransport:
    capsule, project, output, temporary = _roots(tmp_path)
    del output
    return native_worker.ReplayTransport(
        member="targeted-pytest-coverage",
        tool="pytest",
        replies=[],
        capsule=capsule,
        project=project,
        temporary=temporary,
    )


@pytest.mark.parametrize("process_exit", [0, 1])
def test_real_pytest_adapter_preserves_artifacts_before_evaluator_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    process_exit: int,
) -> None:
    transport = _transport(tmp_path)
    observed = [
        {
            "nodeid": "tests/test_value.py::test_value",
            "phase": phase,
            "passed": process_exit == 0,
            "skipped": False,
            "wasxfail": "",
        }
        for phase in ("collection", "setup", "call", "teardown")
    ]
    coverage = {"files": {"pkg/example.py": {"summary": {"percent_covered": 100.0}}}}

    def execute(*_args, **_kwargs):
        paths = runner._temporary_pytest_evidence_paths()
        paths[0].write_text(json.dumps(coverage), encoding="utf-8")
        paths[1].write_text(json.dumps(observed), encoding="utf-8")
        paths[2].write_text(
            '<testsuite><testcase classname="tests.test_value" name="test_value"/></testsuite>', encoding="utf-8"
        )
        return subprocess.CompletedProcess([], process_exit, "", ""), *paths

    def evaluate(*_args, **_kwargs):
        result, *paths = runner._run_pytest_selection_with_coverage((), coverage_source=transport.project)
        assert result.returncode == process_exit
        for path in paths:
            path.unlink()
        return []

    monkeypatch.setattr(runner, "_run_pytest_selection_with_coverage", execute)
    monkeypatch.setattr(runner, "_member_findings", evaluate)
    assert native_worker._pytest_external_adapter([], transport.run, [], False, False) == []
    assert transport.target_execution == {
        "collected": ["tests/test_value.py::test_value"],
        "records": observed,
        "coverage": coverage,
        "process_exit": process_exit,
        "result_provenance": "project-origin-v1",
    }


def test_completed_worker_emits_observations_with_findings_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in native_worker._UNSAFE_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
    roots = _roots(tmp_path)
    _set_member(roots, "targeted-pytest-coverage")
    # This test targets completed response projection; fixed-plan argv validation
    # is already covered separately by the native worker contract suite.
    monkeypatch.setattr(native_worker, "_request_member", lambda _request: ("targeted-pytest-coverage", []))
    expected = {
        "collected": ["tests/test_value.py::test_value"],
        "records": [],
        "coverage": {"files": {}},
        "result_provenance": "project-origin-v1",
    }

    def adapter(_paths, run, *_args):
        run.__self__.target_execution = expected
        return []

    monkeypatch.setitem(native_worker.EXTERNAL_ADAPTERS, "targeted-pytest-coverage", adapter)
    monkeypatch.setattr(native_worker.sys, "argv", _argv(roots))
    assert native_worker.main() == native_worker.EXIT_COMPLETE
    response = json.loads((roots[2] / "result.json").read_text(encoding="utf-8"))
    assert response["target_execution"] == expected
    assert response["evidence_outcome"] == "PASS"
    assert response["findings"] == []


@pytest.mark.parametrize("bad", ["missing", "symlink", "malformed", "oversized"])
def test_pytest_observations_reject_invalid_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bad: str,
) -> None:
    transport = _transport(tmp_path)

    def execute(*_args, **_kwargs):
        paths = runner._temporary_pytest_evidence_paths()
        paths[0].write_text('{"files": {}}', encoding="utf-8")
        paths[1].write_text("[]", encoding="utf-8")
        paths[2].write_text("<testsuite/>", encoding="utf-8")
        if bad == "missing":
            paths[1].unlink()
        elif bad == "symlink":
            outside = tmp_path / "outside.json"
            outside.write_text("[]", encoding="utf-8")
            paths[1].unlink()
            paths[1].symlink_to(outside)
        elif bad == "malformed":
            paths[0].write_text("[]", encoding="utf-8")
        else:
            paths[1].write_bytes(b" " * ((16 << 20) + 1))
        return subprocess.CompletedProcess([], 0, "", ""), *paths

    monkeypatch.setattr(runner, "_run_pytest_selection_with_coverage", execute)

    def evaluate(*_args, **_kwargs):
        return runner._evaluate_pytest_execution(
            [],
            lambda: runner._run_pytest_selection_with_coverage((), coverage_source=transport.project),
            fallback_anchor=transport.project,
        )[0]

    monkeypatch.setattr(runner, "_member_findings", evaluate)
    if bad in {"symlink", "oversized"}:
        with pytest.raises((OSError, ValueError), match=r"artifact|coverage"):
            native_worker._pytest_external_adapter([], transport.run, [], False, False)
    else:
        findings = native_worker._pytest_external_adapter([], transport.run, [], False, False)
        assert findings and all(finding.category == "tool_error" for finding in findings)
        assert transport.target_execution is None


@pytest.mark.parametrize("phase", ["setup", "call", "teardown"])
def test_native_pytest_records_bind_actual_selectors_without_collection_events(tmp_path: Path, phase: str) -> None:
    transport = _transport(tmp_path)
    coverage = transport.temporary / "coverage.json"
    observer = transport.temporary / "observer.json"
    junit = transport.temporary / "junit.xml"
    coverage.write_text('{"files": {"pkg/example.py": {}}}', encoding="utf-8")
    observer.write_text(json.dumps([{"nodeid": "tests/test_value.py::test_value", "phase": phase}]), encoding="utf-8")
    junit.write_text("<testsuite/>", encoding="utf-8")
    result = subprocess.CompletedProcess([], 0, "", ""), coverage, observer, junit
    observed = native_worker._capture_pytest_observation(result, transport)
    assert observed is not None
    assert observed["collected"] == ["tests/test_value.py::test_value"]
    observer.write_text("[]", encoding="utf-8")
    empty = native_worker._capture_pytest_observation(result, transport)
    assert empty is not None
    assert empty["collected"] == []


def _capture_result(transport, records):
    paths = [transport.temporary / name for name in ("coverage.json", "observer.json", "junit.xml")]
    paths[0].write_text('{"files": {"pkg/example.py": {}}}', encoding="utf-8")
    paths[1].write_text(json.dumps(records), encoding="utf-8")
    paths[2].write_text("<testsuite/>", encoding="utf-8")
    return subprocess.CompletedProcess([], 0, "", ""), *paths


@pytest.mark.parametrize(
    "record",
    [
        {"phase": "call"},
        {"nodeid": None, "phase": "call"},
        {"nodeid": True, "phase": "setup"},
        {"nodeid": 17, "phase": "collection"},
        {"nodeid": [], "phase": "teardown"},
        {"nodeid": {}, "phase": "custom"},
    ],
    ids=["missing", "null", "boolean", "integer", "list", "object"],
)
@pytest.mark.parametrize("other_artifact", [None, "missing-coverage", "missing-junit", "malformed-coverage"])
def test_native_pytest_observations_reject_malformed_node_identity(
    tmp_path: Path, record: dict, other_artifact: str | None
) -> None:
    transport = _transport(tmp_path)
    result = _capture_result(transport, [record])
    if other_artifact == "missing-coverage":
        result[1].unlink()
    elif other_artifact == "missing-junit":
        result[3].unlink()
    elif other_artifact == "malformed-coverage":
        result[1].write_text("[]", encoding="utf-8")
    with pytest.raises(native_worker.WorkerContractError, match=r"observer.*node"):
        native_worker._capture_pytest_observation(result, transport)


def test_native_pytest_observations_preserve_exact_valid_node_identity(tmp_path: Path) -> None:
    transport = _transport(tmp_path)
    nodeid = "tests/test_value.py::test_value[parameter::nested]"
    records = [{"nodeid": nodeid, "phase": phase} for phase in ("collection", "setup", "call", "teardown")]
    observed = native_worker._capture_pytest_observation(_capture_result(transport, records), transport)
    assert observed is not None
    assert observed["collected"] == [nodeid]
    assert observed["records"] == records
    assert observed["result_provenance"] == "project-origin-v1"


@pytest.mark.parametrize(
    "failure",
    [
        "usage",
        "missing-coverage",
        "malformed-coverage",
        "missing-observer",
        "deep-coverage",
        "deep-observer",
        "missing-directory",
    ],
)
def test_native_pytest_failure_reaches_real_evaluator_with_incomplete_remedy(tmp_path, monkeypatch, failure):
    transport = _transport(tmp_path)
    source = transport.project / "example.py"
    transport.project.chmod(0o700)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    transport.project.chmod(0o500)
    records = [
        {"nodeid": "tests/test_value.py::test_value", "phase": phase, "passed": True, "skipped": False, "wasxfail": ""}
        for phase in ("collection", "setup", "call", "teardown")
    ]

    # Model the JSON decoder depth refusal on supported Python versions that
    # reject deeply nested inputs; healthy artifacts use the real decoder.
    if failure.startswith("deep-"):
        decode = json.loads

        def bounded_decode(payload, *args, **kwargs):
            if payload.startswith(b"[" * 2000) if isinstance(payload, bytes) else payload.startswith("[" * 2000):
                raise RecursionError("controlled decoder depth refusal")
            return decode(payload, *args, **kwargs)

        monkeypatch.setattr(json, "loads", bounded_decode)

    def execute(*_args, **_kwargs):
        paths = runner._temporary_pytest_evidence_paths()
        paths[0].write_text('{"files": {}}', encoding="utf-8")
        paths[1].write_text(json.dumps(records), encoding="utf-8")
        paths[2].write_text(
            '<testsuite><testcase classname="tests.test_value" name="test_value"/></testsuite>', encoding="utf-8"
        )
        if failure in {"usage", "missing-coverage"}:
            paths[0].unlink()
        elif failure == "malformed-coverage":
            paths[0].write_text("[]", encoding="utf-8")
        elif failure.startswith("deep-"):
            paths[0 if failure == "deep-coverage" else 1].write_text("[" * 2000 + "0" + "]" * 2000, encoding="utf-8")
        elif failure == "missing-directory":
            for path in paths:
                path.unlink()
            paths[0].parent.rmdir()
        else:
            paths[1].unlink()
        return subprocess.CompletedProcess([], 4 if failure == "usage" else 0, "", ""), *paths

    def evaluate(*_args, **_kwargs):
        findings, coverage = runner._evaluate_pytest_execution(
            [source], lambda: runner._run_pytest_selection_with_coverage((), coverage_source=transport.project)
        )
        assert coverage is None
        return findings

    monkeypatch.setattr(runner, "_run_pytest_selection_with_coverage", execute)
    monkeypatch.setattr(runner, "_member_findings", evaluate)
    findings = native_worker._pytest_external_adapter([source], transport.run, [], False, False)
    assert findings and all(f.category == "tool_error" for f in findings)
    assert transport.target_execution is None
    response = native_worker._completed_response(
        "targeted-pytest-coverage",
        findings,
        project=transport.project,
        selected={"example.py"},
        target_execution=transport.target_execution,
    )
    assert response["evidence_outcome"] == "UNKNOWN"
    diagnostic = findings[0].message
    if failure == "usage":
        assert "project_pytest_configuration_or_collection_failed:exit=4" in diagnostic
    elif failure == "missing-coverage":
        assert "project_pytest_coverage_missing" in diagnostic and "pytest-cov" in diagnostic
    else:
        assert "pytest" in diagnostic.lower() and ("evidence" in diagnostic or "artifact" in diagnostic)


@pytest.mark.parametrize("unsafe", ["symlink", "fifo", "oversized"])
def test_missing_coverage_does_not_skip_later_artifact_safety(tmp_path, unsafe):
    transport = _transport(tmp_path)
    coverage = transport.temporary / "coverage.json"
    observer = transport.temporary / "observer.json"
    junit = transport.temporary / "junit.xml"
    junit.write_text("<testsuite/>", encoding="utf-8")
    if unsafe == "symlink":
        outside = tmp_path / "outside.json"
        outside.write_text("[]", encoding="utf-8")
        observer.symlink_to(outside)
    elif unsafe == "fifo":
        import os

        os.mkfifo(observer)
    else:
        observer.write_bytes(b" " * ((16 << 20) + 1))
    result = subprocess.CompletedProcess([], 4, "", ""), coverage, observer, junit
    with pytest.raises(native_worker.WorkerContractError, match="artifact"):
        native_worker._capture_pytest_observation(result, transport)


@pytest.mark.parametrize("missing", ["coverage.json", "junit.xml"])
def test_valid_node_identity_with_missing_artifact_remains_incomplete(tmp_path, missing):
    transport = _transport(tmp_path)
    result = _capture_result(transport, [{"nodeid": "tests/test_value.py::test_value", "phase": "call"}])
    (transport.temporary / missing).unlink()
    assert native_worker._capture_pytest_observation(result, transport) is None


@pytest.mark.parametrize("parent_kind", ["absent", "dangling-symlink", "symlink", "file"])
def test_pytest_artifact_parent_boundary_distinguishes_absence_from_substitution(tmp_path, parent_kind):
    transport = _transport(tmp_path)
    parent = transport.temporary / "evidence-parent"
    outside = tmp_path / "outside"
    if parent_kind == "symlink":
        outside.mkdir()
        (outside / "coverage.json").write_text("private outside bytes", encoding="utf-8")
        parent.symlink_to(outside, target_is_directory=True)
    elif parent_kind == "dangling-symlink":
        parent.symlink_to(outside, target_is_directory=True)
    elif parent_kind == "file":
        parent.write_text("ordinary file", encoding="utf-8")
    path = parent / "coverage.json"
    if parent_kind == "absent":
        assert native_worker._read_pytest_artifact(path, transport.temporary) is None
    else:
        with pytest.raises(native_worker.WorkerContractError, match="artifact"):
            native_worker._read_pytest_artifact(path, transport.temporary)


@pytest.mark.parametrize("large_part", ["combined", "collected", "findings"])
def test_completed_result_bounds_whole_utf8_evidence(tmp_path: Path, large_part: str) -> None:
    transport = _transport(tmp_path)
    member = "targeted-pytest-coverage"
    raw_findings = []
    evidence: dict[str, object] | None
    if large_part == "combined":
        # Both actual artifact files fit their independent 16 MiB limits.
        coverage = transport.temporary / "coverage.json"
        observer = transport.temporary / "observer.json"
        junit = transport.temporary / "junit.xml"
        padding = "x" * (9 << 20)
        coverage.write_text(json.dumps({"files": {}, "metadata": padding}), encoding="utf-8")
        observer.write_text(
            json.dumps([{"nodeid": "tests/test_value.py::test_value", "phase": "call", "detail": padding}]),
            encoding="utf-8",
        )
        junit.write_text("<testsuite/>", encoding="utf-8")
        assert all(path.stat().st_size <= 16 << 20 for path in (coverage, observer, junit))
        evidence = native_worker._capture_pytest_observation(
            (subprocess.CompletedProcess([], 0, "", ""), coverage, observer, junit), transport
        )
        assert evidence is not None
    else:
        evidence = {"collected": ["é" * (9 << 20)]} if large_part == "collected" else None
        if large_part == "findings":
            raw_findings = [
                {
                    "file": "value.py",
                    "line": 1,
                    "severity": "warning",
                    "category": "style",
                    "tool": "ruff",
                    "rule": "F401",
                    "message": "é" * (9 << 20),
                }
            ]
    response = native_worker._completed_response(
        member, raw_findings, project=transport.project, selected={"value.py"}, target_execution=evidence
    )
    assert response == native_worker._unknown_response(member, "native_worker_result_size_exceeded")
    output = tmp_path / "bounded"
    output.mkdir()
    native_worker._write_result(output, response)
    assert (output / "result.json").stat().st_size <= 16 << 20
    assert json.loads((output / "result.json").read_text(encoding="utf-8")) == response


@pytest.mark.parametrize("extra_bytes", [0, -1])
def test_completed_result_budget_includes_utf8_envelope_and_newline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, extra_bytes: int
) -> None:
    transport = _transport(tmp_path)
    evidence = {"collected": ["tests/test_é.py::test_é"], "records": [], "coverage": {"files": {}}}
    baseline = native_worker._completed_response(
        "targeted-pytest-coverage", [], project=transport.project, selected=set(), target_execution=evidence
    )
    wire = (json.dumps(baseline, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")
    monkeypatch.setattr(native_worker, "_MAX_RESULT_BYTES", len(wire) + extra_bytes, raising=False)
    response = native_worker._completed_response(
        "targeted-pytest-coverage", [], project=transport.project, selected=set(), target_execution=evidence
    )
    if extra_bytes == 0:
        assert response == baseline
    else:
        assert response == native_worker._unknown_response(
            "targeted-pytest-coverage", "native_worker_result_size_exceeded"
        )


def test_oversized_evidence_never_bypasses_finding_identity(tmp_path: Path) -> None:
    transport = _transport(tmp_path)
    with pytest.raises(native_worker.WorkerContractError, match="outside selected"):
        native_worker._completed_response(
            "targeted-pytest-coverage",
            [
                {
                    "file": "../outside.py",
                    "line": 1,
                    "severity": "error",
                    "category": "style",
                    "tool": "ruff",
                    "rule": "F401",
                    "message": "bad",
                }
            ],
            project=transport.project,
            selected={"value.py"},
            target_execution={"records": ["x" * (17 << 20)]},
        )


def test_completed_worker_publishes_bounded_unknown_for_combined_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in native_worker._UNSAFE_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
    roots = _roots(tmp_path)
    _set_member(roots, "targeted-pytest-coverage")
    monkeypatch.setattr(native_worker, "_request_member", lambda _request: ("targeted-pytest-coverage", []))

    def adapter(_paths, run, *_args):
        run.__self__.target_execution = {
            "collected": ["tests/test_value.py::test_value"],
            "records": [{"nodeid": "tests/test_value.py::test_value", "phase": "call", "detail": "x" * (9 << 20)}],
            "coverage": {"files": {}, "metadata": "x" * (9 << 20)},
        }
        return []

    monkeypatch.setitem(native_worker.EXTERNAL_ADAPTERS, "targeted-pytest-coverage", adapter)
    monkeypatch.setattr(native_worker.sys, "argv", _argv(roots))
    assert native_worker.main() == native_worker.EXIT_COMPLETE
    result = roots[2] / "result.json"
    assert result.stat().st_size <= 16 << 20
    assert json.loads(result.read_text(encoding="utf-8")) == native_worker._unknown_response(
        "targeted-pytest-coverage", "native_worker_result_size_exceeded"
    )
