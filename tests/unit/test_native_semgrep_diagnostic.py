"""Separate native diagnostic replay preserves errors without review authority."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


def _diagnostic():
    script = Path(__file__).resolve().parents[2] / "scripts/native_semgrep_diagnostic.py"
    assert script.is_file(), "sealed diagnostic replay is absent"
    spec = importlib.util.spec_from_file_location("native_semgrep_diagnostic", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("returncode", [0, 2])
def test_replay_retains_raw_error_and_isolation(tmp_path: Path, monkeypatch, returncode: int) -> None:
    diagnostic = _diagnostic()
    source = tmp_path / "source"
    source.mkdir()
    target = source / "app.py"
    target.write_text("VALUE = 1\n")
    capsule = tmp_path / "capsule"
    rules = capsule / "opt/specfact/builtin/specfact_code_review/.semgrep"
    rules.mkdir(parents=True)
    (rules / "clean_code.yaml").write_text("rules: []\n")
    ai = rules.parent / "resources/semgrep-rules/ai-bloat.yaml"
    ai.parent.mkdir(parents=True)
    ai.write_text("rules: []\n")
    runtime = SimpleNamespace(
        root=capsule,
        identity="signed-capsule",
        environment_id="linux-x86_64-cp312",
        interpreter="/opt/specfact/python/bin/python",
        bootstrap="/opt/specfact/bootstrap/sealed_bootstrap.py",
        bubblewrap="verified-launcher",
    )
    contexts = []

    def plan(context):
        contexts.append(context)
        return context

    def execute(context, launcher, *, extra_argv, timeout):
        assert launcher == "verified-launcher" and timeout == 90
        assert context.member == "semgrep-clean"
        assert extra_argv[0] == "semgrep.console_scripts.pysemgrep"
        assert "--disable-nosem" in extra_argv and "--metrics=off" in extra_argv
        assert extra_argv.count("--config") == 2
        assert extra_argv[-1] == "/opt/specfact/snapshot/app.py"
        return SimpleNamespace(
            status="PASS",
            returncode=returncode,
            stdout='{"results":[],"errors":[{"type":"ParseError","code":3}]}',
            stderr="actual stderr\n",
            reason="",
        )

    monkeypatch.setattr(diagnostic, "build_launch_plan", plan)
    monkeypatch.setattr(diagnostic, "execute_launch_plan", execute)
    evidence = tmp_path / "evidence"
    diagnostic.capture_replay(runtime, source, [target], evidence)
    receipt = json.loads((evidence / "semgrep-diagnostic.json").read_text())
    assert receipt["authority"] == "diagnostic-only" and receipt["acceptance"] is False
    assert receipt["returncode"] == returncode and "ParseError" in (evidence / "semgrep.stdout").read_text()
    assert receipt["stdout_sha256"] == hashlib.sha256((evidence / "semgrep.stdout").read_bytes()).hexdigest()
    assert receipt["source_sha256"]["app.py"] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert contexts[0].network == "none" and contexts[0].project_runtime_root is None
    assert contexts[0].import_domain == "portable" and receipt["startup_difference"]


def test_replay_refuses_missing_signed_rules(tmp_path: Path) -> None:
    diagnostic = _diagnostic()
    with pytest.raises(ValueError, match="signed default rule pack"):
        diagnostic.signed_configs(tmp_path)


def test_replay_does_not_launch_after_failed_preflight(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    diagnostic = _diagnostic()
    capsule = tmp_path / "capsule"
    rules = capsule / "opt/specfact/builtin/specfact_code_review/.semgrep"
    rules.mkdir(parents=True)
    (rules / "clean_code.yaml").write_text("rules: []\n")
    runtime = SimpleNamespace(root=capsule, interpreter="python", bootstrap="sealed", environment_id="cp312")
    monkeypatch.setattr(
        diagnostic, "preflight_reserved_imports", lambda _: SimpleNamespace(status="UNKNOWN", reason="boundary failed")
    )

    def unexpected(*_args, **_kwargs):
        pytest.fail("isolation rejection must precede execution")

    monkeypatch.setattr(diagnostic, "execute_launch_plan", unexpected)
    with pytest.raises(ValueError, match="boundary failed"):
        diagnostic.capture_replay(runtime, tmp_path, [], tmp_path / "evidence")
    assert not (tmp_path / "evidence/semgrep.stdout").exists()


def test_diagnostic_does_not_mutate_original_review(tmp_path: Path) -> None:
    diagnostic = _diagnostic()
    report = tmp_path / "code-review.json"
    original = '{"overall_verdict":"FAIL","analyzer_evidence":[{"id":"semgrep-clean","evidence_outcome":"UNKNOWN"}]}'
    report.write_text(original)
    assert diagnostic.needs_replay(tmp_path)
    assert report.read_text() == original
    report.write_text('{"analyzer_evidence":[{"id":"semgrep-clean","evidence_outcome":"PASS"}]}')
    assert not diagnostic.needs_replay(tmp_path)


def test_diagnostic_refuses_publisher_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    diagnostic = _diagnostic()
    monkeypatch.setattr(sys, "argv", ["diagnostic", "--checkout", str(tmp_path), "--evidence", str(tmp_path)])
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    with pytest.raises(ValueError, match="credential-free developer child"):
        diagnostic.main()
