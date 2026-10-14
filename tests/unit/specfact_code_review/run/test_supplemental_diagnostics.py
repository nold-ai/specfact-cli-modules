"""Supplemental evidence never leaks tool text or upgrades review authority."""

import hashlib
import json
from types import SimpleNamespace
from typing import Any, cast

import pytest

from specfact_code_review.run import supplemental_diagnostics as diagnostic
from specfact_code_review.run.findings import ReviewFinding, ReviewReport


def _finding(**updates):
    values = {
        "category": "security",
        "severity": "error",
        "tool": "semgrep",
        "rule": "specfact-bugs-eval-exec",
        "file": "sample.py",
        "line": 2,
        "message": "PRIVATE_SENTINEL",
        "differential_state": "introduced",
    }
    return ReviewFinding(**{**values, **updates})


def _inputs(findings=None):
    findings = [_finding()] if findings is None else findings
    source = b"def evaluate(value):\n    return eval(value)\n"
    entry = SimpleNamespace(
        git_mode="100644",
        object_type="blob",
        object_id=hashlib.sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest(),
    )
    snapshots = [
        SimpleNamespace(tree=tree, contents={"sample.py": source}, entries={"sample.py": entry})
        for tree in diagnostic.EXPECTED_TREES
    ]
    resolution = SimpleNamespace(base_snapshot=snapshots[0], head_snapshot=snapshots[1])
    results = [
        SimpleNamespace(findings_by_member={"semgrep-bugs": []}),
        SimpleNamespace(findings_by_member={"semgrep-bugs": findings}),
    ]
    report = ReviewReport(
        run_id="PRIVATE_SENTINEL",
        score=0,
        summary="PRIVATE_SENTINEL",
        findings=findings,
        ci_exit_code=1,
        assurance_status="UNKNOWN",
        has_unknown_required_evidence=True,
        analyzer_evidence=[
            {
                "id": "semgrep-bugs",
                "evidence_outcome": "FAIL",
                "diagnostic": "PRIVATE_SENTINEL",
                "base": {"evidence_outcome": "PASS"},
                "head": {"evidence_outcome": "FAIL"},
            }
        ],
    )
    return report, resolution, results


def test_source_checked_rule_and_location_without_private_text():
    payload = diagnostic.build_sidecar(*_inputs())
    assert "PRIVATE_SENTINEL" not in json.dumps(payload)
    record = payload["findings"][0]
    assert (record["side"], record["rule"], record["function"], record["line"]) == (
        "head",
        "specfact-bugs-eval-exec",
        "evaluate",
        2,
    )
    assert len(record["source_sha256"]) == 64
    assert payload["purpose"] == "SUPPLEMENTARY_DIAGNOSTIC_ONLY"
    assert payload["original_exit_code"] == 1
    assert payload["effective_deadline"] == "UNAVAILABLE"


@pytest.mark.parametrize(
    "updates", [{"file": "../private.py"}, {"file": "/private.py"}, {"line": 99}, {"rule": "PRIVATE_SENTINEL"}]
)
def test_invalid_location_or_catalog_rule_is_unavailable(updates):
    payload = diagnostic.build_sidecar(*_inputs([_finding(**updates)]))
    assert not payload["findings"]
    assert payload["omitted_findings"] == 1
    assert "PRIVATE_SENTINEL" not in json.dumps(payload)


def test_wrong_tree_and_symlink_never_emit_locations():
    inputs = _inputs()
    inputs[1].head_snapshot.tree = "0" * 40
    assert diagnostic.build_sidecar(*inputs)["status"] == "UNAVAILABLE"
    inputs = _inputs()
    inputs[1].head_snapshot.entries["sample.py"].git_mode = "120000"
    assert not diagnostic.build_sidecar(*inputs)["findings"]


def test_colliding_error_anchors_keep_actual_side():
    finding = _finding(
        category="tool_error",
        tool="crosshair",
        rule="CROSSHAIR_INCOMPLETE_EVIDENCE",
        differential_state="unknown",
        message="Unrecognized CrossHair output: PRIVATE_SENTINEL",
    )
    report, resolution, results = _inputs([])
    results[0].findings_by_member = {"contracts": [finding]}
    results[1].findings_by_member = {"contracts": [finding]}
    payload = diagnostic.build_sidecar(report, resolution, results)
    assert [item["side"] for item in payload["findings"]] == ["base", "head"]
    assert all(item["diagnostic"] == "crosshair_unrecognized_output" for item in payload["findings"])
    assert "PRIVATE_SENTINEL" not in json.dumps(payload)


def test_bounds_and_duplicates_account_for_omissions():
    inputs = _inputs([_finding()] * (diagnostic.MAX_RECORDS + 5))
    payload = diagnostic.build_sidecar(*inputs)
    assert len(payload["findings"]) == 1
    assert payload["omitted_findings"] == diagnostic.MAX_RECORDS + 4
    assert not payload["complete"]
    assert len(json.dumps(payload).encode()) <= diagnostic.MAX_BYTES


def test_disabled_and_failed_emission_leave_report_unchanged(tmp_path, monkeypatch):
    inputs = _inputs()
    before = inputs[0].model_dump()
    monkeypatch.delenv(diagnostic.OUTPUT_ENV, raising=False)
    assert diagnostic.emit_sidecar(*inputs) == "DISABLED"
    monkeypatch.setenv(diagnostic.OUTPUT_ENV, str(tmp_path / "missing" / "diagnostic.json"))
    assert diagnostic.emit_sidecar(*inputs) == "UNAVAILABLE"
    assert inputs[0].model_dump() == before


def test_emission_refuses_existing_file_and_symlink(tmp_path, monkeypatch):
    output = tmp_path / "diagnostic.json"
    output.write_text("keep")
    monkeypatch.setenv(diagnostic.OUTPUT_ENV, str(output))
    assert diagnostic.emit_sidecar(*_inputs()) == "UNAVAILABLE"
    assert output.read_text() == "keep"
    output.unlink()
    output.symlink_to(tmp_path / "elsewhere")
    assert diagnostic.emit_sidecar(*_inputs()) == "UNAVAILABLE"
    assert not (tmp_path / "elsewhere").exists()


def test_source_bytes_must_match_the_immutable_git_blob():
    inputs = _inputs()
    inputs[1].head_snapshot.contents["sample.py"] = b"def forged():\n    return 0\n"
    payload = diagnostic.build_sidecar(*inputs)
    assert payload["findings"] == []
    assert payload["omitted_findings"] == 1


def test_empty_or_partial_member_inventory_is_not_complete():
    report, resolution, results = _inputs([])
    report.analyzer_evidence = []
    payload = diagnostic.build_sidecar(report, resolution, results)
    assert payload["complete"] is False


def test_unknown_tool_cannot_borrow_an_error_rule():
    finding = _finding(tool="PRIVATE_SENTINEL", rule="tool_error", category="tool_error")
    payload = diagnostic.build_sidecar(*_inputs([finding]))
    assert payload["findings"] == []


def test_completeness_requires_all_member_outcomes_and_function_labels():
    report, resolution, results = _inputs([])
    report.analyzer_evidence = [
        {
            "id": member,
            "diagnostic": "snapshot_member_incomplete",
            "evidence_outcome": "UNKNOWN",
            "base": {"diagnostic": "snapshot_member_incomplete"},
            "head": {"diagnostic": "snapshot_member_incomplete"},
        }
        for member in diagnostic.MEMBERS
    ]
    assert diagnostic.build_sidecar(report, resolution, results)["complete"] is False


def test_introduced_identity_does_not_select_old_message_at_same_location():
    new = _finding(message="new observation")
    old = _finding(message="old observation", differential_state=None)
    report, _resolution, results = _inputs([new])
    results[1].findings_by_member["semgrep-bugs"] = [old, new]
    selected = diagnostic._selected_findings(report, results)
    assert len(selected) == 1
    assert selected[0][2].message == "new observation"


@pytest.mark.parametrize(
    "member,tool,rule",
    [
        ("semgrep-bugs", "pytest", "specfact-bugs-eval-exec"),
        ("contracts", "pylint", "CROSSHAIR_INCOMPLETE_EVIDENCE"),
        ("pylint", "pylint", "TEST_OUTCOME_NOT_PASS"),
    ],
)
def test_known_tokens_cannot_form_a_false_analyzer_identity(member, tool, rule):
    finding = _finding(tool=tool, rule=rule, category="tool_error")
    report, resolution, results = _inputs([finding])
    results[1].findings_by_member = {member: [finding]}
    assert diagnostic.build_sidecar(report, resolution, results)["findings"] == []


def test_emission_preserves_failed_report_and_private_file_permissions(tmp_path, monkeypatch):
    inputs = _inputs()
    before = inputs[0].model_dump()
    output = tmp_path / "diagnostic.json"
    monkeypatch.setenv(diagnostic.OUTPUT_ENV, str(output))
    assert diagnostic.emit_sidecar(*inputs) == "WRITTEN"
    assert output.stat().st_mode & 0o777 == 0o600
    assert output.stat().st_size <= diagnostic.MAX_BYTES
    assert json.loads(output.read_text())["original_exit_code"] == 1
    assert inputs[0].model_dump() == before


def test_host_checkpoint_precedes_blocking_first_member(monkeypatch, tmp_path):
    from specfact_code_review.run import runner

    observed = []
    monkeypatch.setattr(
        diagnostic, "host_checkpoint", lambda stage, **fields: observed.append((stage, fields)), raising=False
    )

    def blocked_dispatch(*args, **kwargs):
        assert observed and observed[-1] == ("member_dispatch", {"member": "ruff"}), (
            "host must persist member_dispatch before entering the blocking member"
        )
        raise RuntimeError("synthetic member blocked")

    monkeypatch.setattr(runner, "_dispatch_capsule_member", blocked_dispatch)
    with pytest.raises(RuntimeError, match="synthetic member blocked"):
        runner._run_capsule_snapshot(
            cast(Any, SimpleNamespace(identity="fixture", environment_id="fixture")),
            snapshot_root=tmp_path,
            files=[],
            options=runner.ReviewOptions(),
        )


def test_host_checkpoint_precedes_blocking_snapshot(monkeypatch, tmp_path):
    from dataclasses import dataclass

    from specfact_code_review.run import portable_snapshot, runner

    @dataclass
    class Options:
        project_runtime: object = None

    observed = []
    monkeypatch.setattr(
        diagnostic, "host_checkpoint", lambda stage, **fields: observed.append((stage, fields)), raising=False
    )
    monkeypatch.setattr(runner, "_snapshot_python_files", lambda *_: [])

    def blocked_snapshot(*args, **kwargs):
        assert observed and observed[-1] == ("snapshot_start", {"side": "base"}), (
            "host must persist snapshot_start before entering the blocking snapshot"
        )
        raise RuntimeError("synthetic snapshot blocked")

    monkeypatch.setattr(portable_snapshot, "run_project_snapshot", blocked_snapshot)
    snapshot = SimpleNamespace(root=tmp_path)
    with pytest.raises(RuntimeError, match="synthetic snapshot blocked"):
        portable_snapshot.run_project_scope_pair(
            SimpleNamespace(base_snapshot=snapshot, head_snapshot=snapshot, selected_paths=[]),
            runtime=SimpleNamespace(),
            options=Options(),
            scope_evidence={},
        )


@pytest.fixture
def host_progress(monkeypatch, tmp_path):
    import importlib
    from pathlib import Path

    from specfact_cli.registry import module_installer

    home = tmp_path / "home"
    package = home / ".specfact/modules/specfact-code-review"
    directory = tmp_path / "observations"
    directory.mkdir(mode=0o700)
    modules = package / "src/specfact_code_review/run"
    modules.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv(diagnostic.PROGRESS_ENV, str(directory))
    for name in diagnostic.PRODUCER_MODULES:
        module = importlib.import_module(f"specfact_code_review.run.{name}")
        target = modules / f"{name}.py"
        assert module.__file__ is not None
        target.write_bytes(Path(module.__file__).read_bytes())
        monkeypatch.setattr(module, "__file__", str(target))
    monkeypatch.setattr(module_installer, "_module_artifact_payload_stable", lambda _: b"verified-test-payload")
    binding: dict[str, str] = dict(zip(("base_commit", "head_commit"), diagnostic.EXPECTED_COMMITS, strict=True))
    binding.update(zip(("base_tree", "head_tree"), diagnostic.EXPECTED_TREES, strict=True))
    binding.update(
        mode="full",
        nonce="a" * 64,
        producer_commit="b" * 40,
        payload_sha256=hashlib.sha256(b"verified-test-payload").hexdigest(),
        workflow_sha256="c" * 64,
        supervisor_sha256="d" * 64,
    )
    diagnostic.verified_review_entry(package, binding)
    yield directory, package, binding
    monkeypatch.setattr(diagnostic, "_PROGRESS", None)


def test_durable_progress_exists_inside_blocked_real_host_dispatch(host_progress, monkeypatch, tmp_path):
    from specfact_code_review.run import runner

    directory, _, binding = host_progress
    assert diagnostic.host_checkpoint("snapshot_start", side="base") == "WRITTEN"

    def block(*_args, **_kwargs):
        record = diagnostic.read_record(directory, "progress.json", diagnostic.PROGRESS_LIMIT)
        diagnostic.validate_progress(record, binding)
        assert (record["stage"], record["member"], record["side"]) == ("member_dispatch", "ruff", "base")
        assert record["members"]["base:ruff"]["stage"] == "member_dispatch"
        assert record["producer"]["modules"]
        raise RuntimeError("blocked")

    monkeypatch.setattr(runner, "_dispatch_capsule_member", block)
    with pytest.raises(RuntimeError, match="blocked"):
        runner._run_capsule_snapshot(
            cast(Any, SimpleNamespace(identity="fixture")),
            snapshot_root=tmp_path,
            files=[],
            options=runner.ReviewOptions(),
        )
    assert diagnostic.collect_host_summary(directory, binding)["progress_state"] == "observed"


def test_twenty_finite_cells_and_no_private_text(host_progress):
    directory, _, binding = host_progress
    for side in ("base", "head"):
        diagnostic.host_checkpoint("snapshot_start", side=side)
        for member in diagnostic.MEMBERS:
            assert diagnostic.host_checkpoint("member_dispatch", member=member) == "WRITTEN"
            assert diagnostic.host_checkpoint("member_return", member=member) == "WRITTEN"
    value = diagnostic.read_record(directory, "progress.json", diagnostic.PROGRESS_LIMIT)
    assert len(value["members"]) == 20
    assert value["actual_loaded_guest_adapter"] == value["effective_guest_deadline"] == "UNAVAILABLE"
    old = (directory / "progress.json").read_bytes()
    assert diagnostic.host_checkpoint("PRIVATE_SENTINEL") == "UNAVAILABLE"
    assert (directory / "progress.json").read_bytes() == old
    assert "PRIVATE_SENTINEL" not in json.dumps(diagnostic.collect_host_summary(directory, binding))


@pytest.mark.parametrize("mutation", ["nonce", "unknown", "sequence", "private", "nan", "cells"])
def test_progress_rejects_forged_records(host_progress, mutation):
    directory, _, binding = host_progress
    value = diagnostic.read_record(directory, "progress.json", diagnostic.PROGRESS_LIMIT)
    if mutation == "nonce":
        value["binding"]["nonce"] = "0" * 64
    elif mutation == "unknown":
        value["unknown"] = "PRIVATE_SENTINEL"
    elif mutation == "sequence":
        value["sequence"] = -1
    elif mutation == "private":
        value["producer"]["python"] = "PRIVATE_SENTINEL"
    elif mutation == "nan":
        value["elapsed_ms"] = float("nan")
    else:
        value["members"] = {"base:PRIVATE_SENTINEL": {"stage": "member_dispatch", "elapsed_ms": 0}}
    (directory / "progress.json").write_text(json.dumps(value))
    summary = diagnostic.collect_host_summary(directory, binding)
    assert summary["progress_state"] == "rejected"
    assert summary["progress"] == "UNAVAILABLE"
    assert "PRIVATE_SENTINEL" not in json.dumps(summary)


def test_atomic_write_failure_preserves_previous_checkpoint(host_progress, monkeypatch):
    directory, _, _ = host_progress
    old = (directory / "progress.json").read_bytes()
    monkeypatch.setattr(
        diagnostic.os, "replace", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("interrupted"))
    )
    assert diagnostic.host_checkpoint("scope_resolved") == "UNAVAILABLE"
    assert (directory / "progress.json").read_bytes() == old
    assert not (directory / "progress.json.tmp").exists()


def test_oversized_atomic_payload_is_rejected_before_replacement(host_progress):
    directory, _, _ = host_progress
    old = (directory / "progress.json").read_bytes()
    with pytest.raises(ValueError, match="oversized"):
        diagnostic.atomic_record(directory, "progress.json", {"private": "x" * 20000}, diagnostic.PROGRESS_LIMIT)
    assert (directory / "progress.json").read_bytes() == old


@pytest.mark.parametrize("kind", ["missing", "oversized", "malformed", "symlink", "duplicate", "depth", "extra"])
def test_collector_rejects_unsafe_files(host_progress, kind, tmp_path):
    directory, _, binding = host_progress
    path = directory / "progress.json"
    if kind == "missing":
        path.unlink()
    elif kind == "oversized":
        path.write_bytes(b"x" * 17000)
    elif kind == "malformed":
        path.write_text("{")
    elif kind == "symlink":
        path.unlink()
        target = tmp_path / "private"
        target.write_text("PRIVATE_SENTINEL")
        path.symlink_to(target)
    elif kind == "duplicate":
        path.write_text('{"schema":1,"schema":2}')
    elif kind == "depth":
        path.write_text("[" * 2000 + "0" + "]" * 2000)
    else:
        (directory / "unexpected").write_text("PRIVATE_SENTINEL")
    summary = diagnostic.collect_host_summary(directory, binding)
    assert summary["progress"] == "UNAVAILABLE"
    assert "PRIVATE_SENTINEL" not in json.dumps(summary)


@pytest.mark.parametrize("mismatch", ["payload", "origin", "checkout"])
def test_actual_entry_rejects_unverified_identity(host_progress, monkeypatch, mismatch, tmp_path):
    directory, package, binding = host_progress
    (directory / "progress.json").unlink()
    if mismatch == "payload":
        binding["payload_sha256"] = "0" * 64
    elif mismatch == "origin":
        monkeypatch.setattr(diagnostic, "__file__", str(tmp_path / "checkout.py"))
    else:
        package = tmp_path
    with pytest.raises(ValueError, match="producer_"):
        diagnostic.verified_review_entry(package, binding)
    assert not (directory / "progress.json").exists()
    assert diagnostic.host_checkpoint("scope_resolved") == "UNAVAILABLE"


def test_disabled_progress_performs_no_io(monkeypatch):
    monkeypatch.delenv(diagnostic.PROGRESS_ENV, raising=False)
    monkeypatch.setattr(diagnostic, "atomic_record", lambda *_: pytest.fail("disabled write"))
    assert diagnostic.host_checkpoint("member_dispatch", member="ruff") == "DISABLED"


def test_interrupted_owner_temp_preserves_last_checkpoint(host_progress):
    directory, _, binding = host_progress
    path = directory / "progress.json.tmp"
    path.write_text("{")
    path.chmod(0o600)
    assert diagnostic.collect_host_summary(directory, binding)["progress_state"] == "observed"


def test_forged_module_hash_is_rejected(host_progress):
    directory, _, binding = host_progress
    value = diagnostic.read_record(directory, "progress.json", diagnostic.PROGRESS_LIMIT)
    value["producer"]["modules"] = dict.fromkeys(value["producer"]["modules"], "0" * 64)
    diagnostic.atomic_record(directory, "progress.json", value, diagnostic.PROGRESS_LIMIT)
    assert diagnostic.collect_host_summary(directory, binding)["progress_state"] == "rejected"


@pytest.mark.parametrize(
    "category,code",
    [
        ("child_exit", None),
        ("child_exit", -9),
        ("signal_termination", 0),
        ("wrapper_expired", 124),
        ("supervisor_error", 0),
    ],
)
def test_incoherent_terminal_is_rejected(host_progress, category, code):
    _, _, binding = host_progress
    value = {
        "schema": "supplemental-host-terminal-v1",
        "purpose": "SUPPLEMENTARY_DIAGNOSTIC_ONLY",
        "binding": binding,
        "category": category,
        "child_returncode": code,
        "elapsed_ms": 1,
        "cleanup": "complete",
        "capsule_process_observed": False,
    }
    with pytest.raises(ValueError):
        diagnostic.validate_terminal(value, binding)


@pytest.mark.parametrize("kind", ["symlink", "oversized", "world-readable"])
def test_unsafe_owner_temp_is_rejected(host_progress, kind, tmp_path):
    directory, _, binding = host_progress
    path = directory / "progress.json.tmp"
    if kind == "symlink":
        path.symlink_to(tmp_path / "private")
    else:
        path.write_bytes(b"x" * (17000 if kind == "oversized" else 1))
        path.chmod(0o644 if kind == "world-readable" else 0o600)
    assert diagnostic.collect_host_summary(directory, binding)["progress_state"] == "rejected"


def test_process_death_during_atomic_update_retains_complete_checkpoint(host_progress, tmp_path):
    import os
    import signal
    import subprocess
    import sys
    import time

    directory, _, binding = host_progress
    ready = tmp_path / "ready"
    program = """import json,sys,time
from pathlib import Path
sys.path[:0] = json.loads(sys.argv[1])
from specfact_code_review.run import supplemental_diagnostics as d
def stop(*args, **kwargs):
    Path(sys.argv[3]).write_text('ready')
    time.sleep(30)
d.os.replace = stop
d.atomic_record(Path(sys.argv[2]), 'progress.json', {'partial': True}, d.PROGRESS_LIMIT)
"""
    child = subprocess.Popen(
        [sys.executable, "-c", program, json.dumps(sys.path), str(directory), str(ready)], start_new_session=True
    )
    try:
        deadline = time.monotonic() + 5
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert ready.exists()
        os.killpg(child.pid, signal.SIGKILL)
        child.wait(timeout=5)
        assert (directory / "progress.json.tmp").is_file()
        assert diagnostic.collect_host_summary(directory, binding)["progress_state"] == "observed"
    finally:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=5)
