"""Sealed analyzer evidence cannot confuse launch failure with a clean scan."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import plistlib
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture(name="analyzer")
def fixture_analyzer():
    path = Path(__file__).parents[2] / "scripts/macos_managed_boundary/analyzer.py"
    spec = importlib.util.spec_from_file_location("sealed_analyzer", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("code", [2, 7, -9])
def test_failed_execution_is_not_clean(analyzer, code):
    assert (
        analyzer.scan_passed(
            {"version": analyzer.PARITY.VERSION, "results": [], "errors": [], "paths": {"scanned": ["fixture.py"]}},
            code,
            None,
        )
        is False
    )


def test_empty_defective_evidence_is_rejected(analyzer):
    assert (
        analyzer.scan_passed(
            {"version": analyzer.PARITY.VERSION, "results": [], "errors": [], "paths": {"scanned": ["fixture.py"]}},
            0,
            "print-in-src",
        )
        is False
    )


def test_scan_errors_prevent_pass(analyzer):
    assert (
        analyzer.scan_passed(
            {
                "version": analyzer.PARITY.VERSION,
                "results": [],
                "errors": [{"type": "Syntax error"}],
                "paths": {"scanned": ["fixture.py"]},
            },
            0,
            None,
        )
        is False
    )


def test_missing_target_prevents_pass(analyzer):
    assert (
        analyzer.scan_passed(
            {"version": analyzer.PARITY.VERSION, "results": [], "errors": [], "paths": {"scanned": []}}, 0, None
        )
        is False
    )


@pytest.mark.parametrize("content", ["", "sealed-boundary-established", "sealed-profile-probes-ok"])
def test_missing_boundary_or_negative_probes_prevents_acceptance(analyzer, content):
    payload = {"version": analyzer.PARITY.VERSION, "results": [], "errors": [], "paths": {"scanned": ["fixture.py"]}}
    assert analyzer.case_passed(content, payload, 0, None) is False


def test_corrupt_bundled_library_is_rejected(analyzer, tmp_path, monkeypatch):
    core = tmp_path / "semgrep-core"
    core.write_bytes(b"core")
    (tmp_path / "libs").mkdir()
    (tmp_path / "libs" / "fixture.dylib").write_bytes(b"corrupted")
    monkeypatch.setattr(analyzer, "LIBRARY_PINS", {"fixture.dylib": "0" * 64})
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        analyzer.verify_libraries(core)


def test_uninventoried_library_is_rejected(analyzer, tmp_path, monkeypatch):
    core = tmp_path / "semgrep-core"
    core.write_bytes(b"core")
    (tmp_path / "libs").mkdir()
    (tmp_path / "libs" / "extra.dylib").write_bytes(b"extra")
    monkeypatch.setattr(analyzer, "LIBRARY_PINS", {})
    with pytest.raises(ValueError, match="library inventory"):
        analyzer.verify_libraries(core)


def test_valid_positive_and_clean_controls(analyzer):
    clean = {"version": analyzer.PARITY.VERSION, "results": [], "errors": [], "paths": {"scanned": ["fixture.py"]}}
    assert analyzer.scan_passed(clean, 0, None) is True
    defect = {**clean, "results": [{"check_id": "print-in-src", "path": "fixture.py", "start": {"line": 2}}]}
    assert analyzer.scan_passed(defect, 0, "print-in-src") is True


def test_wrong_native_version_prevents_acceptance(analyzer):
    clean = {"version": "0.0.0", "results": [], "errors": [], "paths": {"scanned": ["fixture.py"]}}
    assert analyzer.scan_passed(clean, 0, None) is False


@pytest.mark.parametrize(
    "change", [{"check_id": "unapproved.print-in-src"}, {"path": "host.py"}, {"start": {"line": 3}}]
)
def test_wrong_finding_identity_prevents_acceptance(analyzer, change):
    item = {"check_id": "print-in-src", "path": "fixture.py", "start": {"line": 2}, **change}
    payload = {
        "version": analyzer.PARITY.VERSION,
        "results": [item],
        "errors": [],
        "paths": {"scanned": ["fixture.py"]},
    }
    assert analyzer.scan_passed(payload, 0, "print-in-src") is False


@pytest.mark.parametrize("signal", [5, 6, 9, 11])
def test_terminal_signal_identity_is_preserved(analyzer, signal):
    assert analyzer.completed_scan(f"worker-signal={signal}\n") == -signal


@pytest.fixture(name="sealed_assets")
def fixture_sealed_assets(tmp_path):
    assets = {"clean_code": tmp_path / "rules", "ca_bundle": tmp_path / "ca"}
    for name, path in assets.items():
        path.write_text(f"approved {name}")
    return assets


def test_exercised_profile_is_the_supplied_snapshot(analyzer, monkeypatch, tmp_path, sealed_assets):

    source = tmp_path / "source"
    source.mkdir()
    (source / "analyzer.sb").write_text("concurrently changed profile")
    monkeypatch.setattr(analyzer, "HERE", source)
    actual_job = analyzer.STARTUP.create_job

    def create(*args):
        result = actual_job(*args)
        (args[1] / "errors").write_text("")
        return result

    monkeypatch.setattr(analyzer.STARTUP, "create_job", create)
    profiles = []

    def command(args):
        profiles.append(plistlib.loads(Path(args[-1]).read_bytes())["ProgramArguments"][3])

    monkeypatch.setattr(analyzer.STARTUP, "command", command)
    payload = {"version": analyzer.PARITY.VERSION, "results": [], "errors": [], "paths": {"scanned": ["fixture.py"]}}
    monkeypatch.setattr(
        analyzer,
        "wait_scan",
        lambda *_args: ("sealed-boundary-established\nsealed-profile-probes-ok\n" + json.dumps(payload), 0),
    )
    monkeypatch.setattr(analyzer.STARTUP, "remove_job", lambda *_args: None)
    analyzer.run_case(
        analyzer.STARTUP.NativeBinaries(Path("/broker"), Path("/worker"), Path("/observer")),
        tmp_path / "case",
        {"source": "safe", "pack": "clean_code", "expected_rule": None},
        sealed_assets,
        "approved profile snapshot",
    )
    assert profiles == ["approved profile snapshot"]


def test_missing_sealed_case_cannot_produce_pass(analyzer, monkeypatch):

    monkeypatch.setattr(analyzer.STARTUP, "command", lambda *_args: SimpleNamespace(stdout="26A434"))
    report = analyzer.analyzer_receipt(
        {},
        {"assets": {}, "libraries": {}, "bootstrap_sha256": "0" * 64, "signed_fixtures": [], "source_sha256": {}},
        b"profile",
    )
    assert report["passed"] is False
    assert report["production_approved"] is False


def test_wrapper_compiles_and_records_one_source_snapshot(analyzer, monkeypatch, tmp_path):

    source = tmp_path / "sources"
    source.mkdir()
    original = source / "analyzer_worker.c"
    original.write_bytes(b"approved native source")
    build = tmp_path / "build"
    build.mkdir()
    monkeypatch.setattr(analyzer, "HERE", source)
    compiled = []

    def command(args):
        if "clang" in args:
            original.write_bytes(b"changed after snapshot")
            compiled.append(Path(args[args.index("-o") - 1]).read_bytes())
            Path(args[-1]).write_bytes(b"compiled binary")
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr(analyzer.STARTUP, "command", command)
    target, source_digest = analyzer.build_wrapper(build, Path("/approved/core"))
    assert target == build / "sealed-worker"
    assert compiled == [b"approved native source"]
    assert source_digest == hashlib.sha256(compiled[0]).hexdigest()


def test_receipt_uses_compiled_source_provenance(analyzer, monkeypatch, tmp_path):

    monkeypatch.setattr(analyzer, "HERE", tmp_path)
    monkeypatch.setattr(analyzer.STARTUP, "command", lambda *_args: SimpleNamespace(stdout="26A434"))
    payload = {
        "assets": {},
        "libraries": {},
        "bootstrap_sha256": "0" * 64,
        "signed_fixtures": [],
        "source_sha256": {"analyzer_worker.c": "1" * 64},
    }
    report = analyzer.analyzer_receipt({}, payload, b"profile")
    assert report["source_sha256"] == payload["source_sha256"]


def test_helper_executes_the_hashed_snapshot(analyzer, tmp_path):

    script = tmp_path / "helper.py"
    raw = b"VALUE = 'snapshot'\n"
    script.write_bytes(raw)
    helper = analyzer.load_script(script, "test_snapshot_helper")
    script.write_bytes(b"VALUE = 'changed'\n")
    assert helper.VALUE == "snapshot"
    assert helper.loaded_source_sha256 == hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("stderr", [None, "error-start" + "x" * 5000 + "error-end"])
def test_scan_timeout_preserves_service_and_available_diagnostic_tails(analyzer, monkeypatch, tmp_path, stderr):
    events = tmp_path / "events"
    content = "event-start" + "y" * 5000 + "event-end"
    events.write_text(content)
    if stderr is not None:
        (tmp_path / "errors").write_text(stderr)
    clock = iter((0, 1, 31))
    monkeypatch.setattr(analyzer.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(analyzer.time, "sleep", lambda _interval: None)
    with pytest.raises(RuntimeError, match="sealed analyzer timeout") as caught:
        analyzer.wait_scan(events, Path("/observer"), [], "gui/501/sealed-test")
    assert str(caught.value) == (
        f"sealed analyzer timeout: gui/501/sealed-test: {content[-4000:]}: {(stderr or '')[-4000:]}"
    )


@pytest.mark.parametrize("completed", [False, True])
def test_missing_stderr_preserves_scan_outcome_and_job_cleanup(
    analyzer, monkeypatch, tmp_path, sealed_assets, completed
):
    payload = {"version": analyzer.PARITY.VERSION, "results": [], "errors": [], "paths": {"scanned": ["fixture.py"]}}
    content = "sealed-boundary-established\nsealed-profile-probes-ok\n" + json.dumps(payload) + "\nworker-exit=0\n"
    directory = tmp_path / "case"
    actual_job = analyzer.STARTUP.create_job
    services = []

    def create(*args):
        service, plist = actual_job(*args)
        services.append(service)
        if completed:
            (args[1] / "events").write_text(content)
        return service, plist

    monkeypatch.setattr(analyzer.STARTUP, "create_job", create)
    monkeypatch.setattr(analyzer.STARTUP, "command", lambda _args: None)
    removed = []
    monkeypatch.setattr(analyzer.STARTUP, "remove_job", lambda *args: removed.append(args))
    clock = iter((0, 1, 31))
    monkeypatch.setattr(analyzer.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(analyzer.time, "sleep", lambda _interval: None)
    binaries = analyzer.STARTUP.NativeBinaries(Path("/broker"), Path("/worker"), Path("/observer"))
    case = {"source": "safe", "pack": "clean_code", "expected_rule": None}
    if completed:
        result = analyzer.run_case(binaries, directory, case, sealed_assets, "approved profile")
        assert result["passed"] is True
        assert result["tool_exit"] == 0
        assert result["tool_payload"] == payload
        assert result["stderr"] == ""
    else:
        with pytest.raises(RuntimeError, match="sealed analyzer timeout"):
            analyzer.run_case(binaries, directory, case, sealed_assets, "approved profile")
    assert removed == [(binaries.observer, [], services[0])]
    assert not (directory / "errors").exists()
