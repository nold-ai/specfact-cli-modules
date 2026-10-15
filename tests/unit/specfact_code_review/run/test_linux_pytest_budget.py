"""Operator budget admission and actual capsule routing contracts."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from specfact_code_review.run import runner


def test_legacy_budget_default():
    assert getattr(runner.ReviewOptions(), "linux_pytest_timeout_seconds", None) == 300


@pytest.mark.parametrize("budget", [1, 300, 600])
def test_bounded_budget_admitted(budget):
    options = runner.ReviewOptions(linux_pytest_timeout_seconds=budget)
    assert options.linux_pytest_timeout_seconds == budget


@pytest.mark.parametrize("budget", [False, True, 0, -1, 601, 1.5, "600", None])
def test_invalid_budget_rejected(budget):
    with pytest.raises(ValueError, match="linux_pytest_execution_budget_invalid"):
        runner.ReviewOptions(linux_pytest_timeout_seconds=budget)


@pytest.mark.parametrize("member, expected", [("targeted-pytest-coverage", 600), ("ruff", 300)])
def test_only_pytest_receives_selected_budget(tmp_path, monkeypatch, member, expected):
    source = tmp_path / "unit.py"
    source.write_text("value = 1\n")
    runtime = runner.CapsuleRuntime(
        tmp_path,
        "identity",
        "linux-x86_64-cp313",
        "/python",
        "/bootstrap",
        runner.BubblewrapIdentity("/bwrap", "ELF", "x86_64", "static", (), (), "a" * 64, "b" * 64),
    )
    options = runner.ReviewOptions(linux_pytest_timeout_seconds=600)
    observed = []
    monkeypatch.setattr(runner, "preflight_reserved_imports", lambda context: SimpleNamespace(status="PASS"))
    requests = []

    def plan(context):
        requests.append(json.loads((context.config_roots[0] / "request.json").read_text()))
        return object()

    monkeypatch.setattr(runner, "build_launch_plan", plan)

    def launch(plan, identity, **kwargs):
        observed.append(kwargs.get("timeout", 300))
        return SimpleNamespace(status="UNKNOWN", reason="sandbox_launch_failed:timeout")

    monkeypatch.setattr(runner, "execute_launch_plan", launch)
    response = runner._execute_capsule_member(
        runner.CapsuleMemberExecutionRequest(runtime, member, "test", tmp_path, [source], options)
    )
    assert observed == [expected]
    assert requests[0].get("linux_pytest_timeout_seconds") == (600 if member == "targeted-pytest-coverage" else None)
    assert response["execution_state"] == "error"
    assert response["evidence_outcome"] == "UNKNOWN"
    assert response["diagnostic"] == "sandbox_launch_failed:timeout"
    assert response["findings"] == []


def test_legacy_keyword_route_preserves_explicit_budget():
    options = runner._review_options_from_kwargs(None, {"linux_pytest_timeout_seconds": 600})
    assert options.linux_pytest_timeout_seconds == 600


def test_darwin_override_fails_closed_without_changing_default(tmp_path, monkeypatch):
    runtime = runner.CapsuleRuntime(
        tmp_path, "identity", "darwin-arm64-cp313", "/python", "/bootstrap", None, backend="darwin-arm64"
    )
    called = []
    monkeypatch.setattr(
        runner, "_execute_native_capsule_member", lambda request: called.append(request) or {"legacy": True}
    )
    default = runner.CapsuleMemberExecutionRequest(
        runtime, "targeted-pytest-coverage", "test", tmp_path, [], runner.ReviewOptions()
    )
    assert runner._execute_capsule_member(default) == {"legacy": True}
    override = runner.CapsuleMemberExecutionRequest(
        runtime,
        "targeted-pytest-coverage",
        "test",
        tmp_path,
        [],
        runner.ReviewOptions(linux_pytest_timeout_seconds=600),
    )
    response = runner._execute_capsule_member(override)
    assert len(called) == 1
    assert response["evidence_outcome"] == "UNKNOWN"
    assert response["diagnostic"] == "linux_pytest_execution_budget_unsupported_platform"


@pytest.mark.parametrize("cached", [False, True])
@pytest.mark.parametrize(
    "reason, backend, expected",
    [
        (
            "unsupported_controller_platform",
            "unsupported",
            "linux_pytest_execution_budget_unsupported_platform",
        ),
        (
            "oci_acquisition_failed:verified cache entry is missing",
            "linux-x86_64",
            "oci_acquisition_failed:verified cache entry is missing",
        ),
    ],
)
def test_nondefault_budget_never_enters_development_host_fallback(
    tmp_path, monkeypatch, cached, reason, backend, expected
):
    source = tmp_path / "app.py"
    source.write_text("value = 1\n")
    monkeypatch.setattr(runner, "_prepare_capsule_runtime", lambda: (None, reason))
    monkeypatch.setattr(runner, "_is_development_source_checkout", lambda: True)
    monkeypatch.setattr(
        runner.native_backend,
        "select_runtime_backend",
        lambda: SimpleNamespace(kind=backend, environment_id=None),
    )
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_DEV_HOST_COMPAT", "1")
    if cached:
        monkeypatch.setenv("SPECFACT_CODE_REVIEW_CHANGED_DIFF", "cached")
    monkeypatch.setattr(
        runner,
        "_run_cached_development_host_review",
        lambda *_args, **_kwargs: pytest.fail("nondefault Linux-only budget reached cached host fallback"),
    )
    monkeypatch.setattr(
        runner,
        "_run_worktree_development_host_review",
        lambda *_args, **_kwargs: pytest.fail("nondefault Linux-only budget reached worktree host fallback"),
    )

    report = runner.run_capsule_review(
        [source],
        runner.ReviewOptions(linux_pytest_timeout_seconds=600),
    )

    assert report.assurance_status == "UNKNOWN"
    assert report.ci_exit_code == 1
    assert report.analyzer_evidence is not None
    assert {item["diagnostic"] for item in report.analyzer_evidence} == {expected}
    assert report.scope_evidence is not None
    budget_evidence = report.scope_evidence["linux_pytest_execution_budget"]
    assert isinstance(budget_evidence, dict)
    assert budget_evidence["requested_seconds"] == 600


def test_budget_provenance_does_not_promote_unknown(monkeypatch):
    monkeypatch.setattr(
        runner.native_backend,
        "select_runtime_backend",
        lambda: SimpleNamespace(kind="linux-x86_64", environment_id="linux-x86_64-cp313"),
    )
    report = runner._unknown_capsule_report(
        "sandbox_launch_failed:timeout",
        options=runner.ReviewOptions(linux_pytest_timeout_seconds=600),
        scope_evidence={},
    )
    assert report.scope_evidence is not None
    assert report.scope_evidence["linux_pytest_execution_budget"] == {
        "requested_seconds": 600,
        "effective_seconds": 600,
        "platform": "linux-x86_64",
        "nonportable_inner_seconds": 600,
        "portable_inner_seconds": 1200,
        "authority": "operator-option",
    }
    assert report.assurance_status == "UNKNOWN"
    assert report.ci_exit_code == 1


@pytest.mark.parametrize("budget", [None, 300, 1, 600])
def test_private_request_applies_inner_budget(tmp_path, monkeypatch, budget):
    import json

    request = {"member": "targeted-pytest-coverage", "paths": ["source.py"]}
    if budget is not None:
        request["linux_pytest_timeout_seconds"] = budget
    path = tmp_path / "request.json"
    path.write_text(json.dumps(request))
    parsed = runner._load_capsule_request(path)
    assert parsed[-1] == (None if budget in (None, 300) else budget)


@pytest.mark.parametrize("budget", [False, True, 0, -1, 601, 1.5, "600", None])
def test_private_budget_rejects_invalid(tmp_path, budget):
    import json

    path = tmp_path / "request.json"
    path.write_text(
        json.dumps({"member": "targeted-pytest-coverage", "paths": [], "linux_pytest_timeout_seconds": budget})
    )
    with pytest.raises(ValueError, match="linux_pytest_execution_budget_invalid"):
        runner._load_capsule_request(path)


def test_private_budget_rejects_other_member(tmp_path):
    import json

    path = tmp_path / "request.json"
    path.write_text(json.dumps({"member": "ruff", "paths": [], "linux_pytest_timeout_seconds": 600}))
    with pytest.raises(ValueError, match="linux_pytest_execution_budget_invalid_member"):
        runner._load_capsule_request(path)


def test_inner_budget_is_nested_and_exception_safe():
    assert runner._PYTEST_EXECUTION_BUDGET.get() is None
    with runner._pytest_execution_budget(600):
        assert runner._PYTEST_EXECUTION_BUDGET.get() == 600
        with pytest.raises(RuntimeError), runner._pytest_execution_budget(1):
            assert runner._PYTEST_EXECUTION_BUDGET.get() == 1
            raise RuntimeError("controlled")
        assert runner._PYTEST_EXECUTION_BUDGET.get() == 600
    assert runner._PYTEST_EXECUTION_BUDGET.get() is None


def test_inner_budget_does_not_cross_threads():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    barrier = Barrier(2)

    def operation(budget):
        with runner._pytest_execution_budget(budget):
            barrier.wait(timeout=5)
            return runner._PYTEST_EXECUTION_BUDGET.get()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(operation, [1, 600]))
    assert results == [1, 600]
    assert runner._PYTEST_EXECUTION_BUDGET.get() is None


@pytest.mark.parametrize("budget, expected", [(None, 120), (600, 600)])
def test_actual_nonportable_subprocess_budget(tmp_path, monkeypatch, budget, expected):
    import subprocess

    captured = []

    def run(command, **kwargs):
        captured.append(kwargs["timeout"])
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(runner, "_pytest_python_executable", lambda: "python")
    monkeypatch.setattr(runner, "_pytest_env", dict)
    monkeypatch.setattr(runner, "_pytest_in_capsule", lambda: False)
    monkeypatch.setattr(runner.subprocess, "run", run)
    with runner._pytest_execution_budget(budget), pytest.raises(subprocess.TimeoutExpired):
        runner._run_pytest_selection_with_coverage((), coverage_source=tmp_path)
    assert captured == [expected]
    assert runner._PYTEST_EXECUTION_BUDGET.get() is None


@pytest.mark.parametrize("raises", [False, True])
def test_capsule_dispatch_budget_restores_after_member(tmp_path, monkeypatch, raises):
    result_path = tmp_path / "result.json"
    monkeypatch.setattr(
        runner,
        "_load_capsule_request",
        lambda path: ("targeted-pytest-coverage", [tmp_path / "source.py"], False, (), False, 600),
    )
    observed = []

    def member(*args, **kwargs):
        observed.append(runner._PYTEST_EXECUTION_BUDGET.get())
        if raises:
            raise ValueError("controlled incomplete member")
        return []

    monkeypatch.setattr(runner, "_member_findings", member)
    monkeypatch.setattr(
        runner,
        "Path",
        Mock(
            wraps=Path,
            side_effect=lambda value: result_path if str(value) == "/opt/specfact/output/result.json" else Path(value),
        ),
    )
    runner._capsule_process_request(tmp_path / "request.json")
    assert observed == [600]
    assert runner._PYTEST_EXECUTION_BUDGET.get() is None
    response = json.loads(result_path.read_text())
    assert response["evidence_outcome"] == ("UNKNOWN" if raises else "PASS")
