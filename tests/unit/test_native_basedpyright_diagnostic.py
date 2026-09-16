"""Basedpyright replay binds the failed review and preserves raw diagnostic evidence."""

from __future__ import annotations

import importlib.util
import json
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml


_SCRIPT = Path(__file__).resolve().parents[2] / "scripts/native_basedpyright_diagnostic.py"


def _diagnostic():
    assert _SCRIPT.is_file(), "basedpyright diagnostic is absent"
    spec = importlib.util.spec_from_file_location("native_basedpyright_diagnostic", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _identities():
    return {
        "project_identity": "project",
        "identity": "runtime",
        "environment_id": "cp312",
        "capsule_identity": "bound",
    }


@pytest.mark.parametrize("field", ["project_identity", "identity", "environment_id", "capsule_identity"])
def test_identity_mismatch_prevents_replay(field: str) -> None:
    diagnostic = _diagnostic()
    actual = _identities()
    actual[field] = "other"
    with pytest.raises(ValueError, match="identity mismatch"):
        diagnostic.validate_identities(_identities(), actual)


def test_report_requires_unknown_basedpyright_and_passed_runtime(tmp_path: Path) -> None:
    diagnostic = _diagnostic()
    report = {
        "scope_evidence": {"project_runtime": {"status": "PASS", **_identities()}},
        "analyzer_evidence": [{"id": "basedpyright", "evidence_outcome": "UNKNOWN", "capsule_identity": "bound"}],
    }
    (tmp_path / "code-review.json").write_text(json.dumps(report))
    assert diagnostic.failed_review_context(tmp_path) == _identities()
    report["scope_evidence"]["project_runtime"]["status"] = "UNKNOWN"
    (tmp_path / "code-review.json").write_text(json.dumps(report))
    with pytest.raises(ValueError, match="runtime"):
        diagnostic.failed_review_context(tmp_path)


@pytest.mark.parametrize("returncode", [0, 1, 78])
def test_raw_worker_replay_preserves_isolation_and_exit(tmp_path: Path, monkeypatch, returncode: int) -> None:
    diagnostic = _diagnostic()
    source = tmp_path / "source"
    source.mkdir()
    target = source / "app.py"
    target.write_text("VALUE = 1\n")
    runtime = SimpleNamespace(
        root=tmp_path / "capsule",
        identity="capsule",
        environment_id="cp312",
        interpreter="/opt/specfact/python/bin/python",
        bootstrap="/opt/specfact/bootstrap/sealed_bootstrap.py",
        bubblewrap="verified",
    )
    prepared = SimpleNamespace(
        root=tmp_path / "runtime", identity="runtime", descriptor={"project_identity": "project"}
    )
    seen = []
    monkeypatch.setattr(diagnostic, "document_digest", lambda value: "bound")
    monkeypatch.setattr(
        diagnostic, "preflight_reserved_imports", lambda context: SimpleNamespace(status="PASS", reason="")
    )

    def execute(plan, launcher, *, extra_argv, timeout):
        assert launcher == "verified" and extra_argv == () and timeout == 45
        assert plan.argv[:4] == (runtime.interpreter, "-I", "-S", "-c")
        assert "target_command" in plan.argv[4] and "subprocess.run" in plan.argv[4]
        arguments = json.loads(plan.argv[5])
        assert arguments == [
            "--outputjson",
            "--pythonpath",
            "/opt/specfact/project-runtime/bin/python",
            "/opt/specfact/snapshot/app.py",
        ]
        assert "--project" not in arguments
        assert any(mount.source == prepared.root and mount.read_only for mount in plan.mounts)
        assert plan.network == "none" and not plan.host_runtime_mounts
        seen.append(plan)
        return SimpleNamespace(
            status="PASS", returncode=returncode, stdout="", stderr="native loader diagnostic\n", reason=""
        )

    monkeypatch.setattr(diagnostic, "execute_launch_plan", execute)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    diagnostic.capture_replay(runtime, prepared, source, [target], evidence)
    receipt = json.loads((evidence / "basedpyright-diagnostic.json").read_text())
    assert seen and receipt["acceptance"] is False and receipt["authority"] == "diagnostic-only"
    assert receipt["returncode"] == returncode and receipt["review_context"] == _identities()
    assert (evidence / "basedpyright.stdout").read_bytes() == b""
    assert (evidence / "basedpyright.stderr").read_text() == "native loader diagnostic\n"
    assert "not recovered original" in receipt["startup_difference"]


def test_failed_preflight_never_executes(tmp_path: Path, monkeypatch) -> None:
    diagnostic = _diagnostic()
    source = tmp_path / "source"
    source.mkdir()
    runtime = SimpleNamespace(
        root=tmp_path, identity="capsule", environment_id="cp312", interpreter="python", bootstrap="sealed"
    )
    prepared = SimpleNamespace(root=tmp_path, identity="runtime", descriptor={"project_identity": "project"})
    monkeypatch.setattr(
        diagnostic, "preflight_reserved_imports", lambda _: SimpleNamespace(status="UNKNOWN", reason="unsafe")
    )
    monkeypatch.setattr(diagnostic, "execute_launch_plan", lambda *args, **kwargs: pytest.fail("must not execute"))
    with pytest.raises(ValueError, match="unsafe"):
        diagnostic.capture_replay(runtime, prepared, source, [], tmp_path)


def test_diagnostic_workflow_is_explicitly_opt_in() -> None:

    workflow = yaml.safe_load((_SCRIPT.parent.parent / ".github/workflows/capsule-customer-execution.yml").read_text())
    inputs = workflow.get("on", workflow.get(True))["workflow_dispatch"]["inputs"]
    assert inputs["basedpyright_diagnostic"]["default"] is False
    assert inputs["basedpyright_diagnostic"]["type"] == "boolean"


@pytest.mark.parametrize("mismatch", [False, True])
def test_replay_requires_offline_exact_snapshot_context(tmp_path: Path, monkeypatch, mismatch: bool) -> None:
    """No original report mismatch can reach the sandbox, even with a valid cache."""
    diagnostic = _diagnostic()
    repository = tmp_path / "repository"
    repository.mkdir()
    source = tmp_path / "snapshot"
    source.mkdir()
    target = source / "app.py"
    target.write_text("VALUE = 1\n")
    runtime = SimpleNamespace(environment_id="cp312", identity="capsule")
    prepared = SimpleNamespace(identity="other" if mismatch else "runtime", descriptor={"project_identity": "project"})
    snapshot = SimpleNamespace(root=source, files=[target])
    expected = _identities()
    calls = []
    monkeypatch.setattr(diagnostic.subprocess, "check_output", lambda *args, **kwargs: b"app.py\0")
    monkeypatch.setattr(diagnostic.runner, "_prepare_capsule_runtime", lambda **kwargs: (runtime, ""))
    monkeypatch.setattr(diagnostic.runner, "_cleanup_capsule_runtime", lambda _: calls.append("cleanup"))
    monkeypatch.setattr(diagnostic.runner, "_cached_analysis_snapshot", lambda *args: snapshot)

    def discover(root, *, config_path, source_snapshot):
        assert root == source and source_snapshot is snapshot and config_path is None
        return SimpleNamespace(identity="project")

    def prepare(plan, *, runtime, offline):
        assert offline is True and plan.identity == "project" and runtime.identity == "capsule"
        return prepared

    monkeypatch.setattr(diagnostic, "discover_snapshot", discover)
    monkeypatch.setattr(diagnostic, "project_worker", lambda runtime, plan: nullcontext(runtime))
    monkeypatch.setattr(diagnostic, "prepare_runtime", prepare)
    monkeypatch.setattr(diagnostic, "document_digest", lambda value: "bound")
    monkeypatch.setattr(diagnostic, "copy_project", lambda *args, **kwargs: None)
    monkeypatch.setattr(diagnostic, "capture_replay", lambda *args: calls.append("execute"))
    if mismatch:
        with pytest.raises(ValueError, match="identity mismatch"):
            diagnostic.replay(repository, tmp_path, expected)
        assert calls == ["cleanup"]
    else:
        diagnostic.replay(repository, tmp_path, expected)
        assert calls == ["execute", "cleanup"]
