"""Operator budget admission and actual capsule routing contracts."""

from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from specfact_code_review.review import commands as review_commands
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
    monkeypatch.setattr(runner, "build_launch_plan", lambda context: object())

    def launch(plan, identity, **kwargs):
        observed.append(kwargs.get("timeout", 300))
        return SimpleNamespace(status="UNKNOWN", reason="sandbox_launch_failed:timeout")

    monkeypatch.setattr(runner, "execute_launch_plan", launch)
    response = runner._execute_capsule_member(
        runner.CapsuleMemberExecutionRequest(runtime, member, "test", tmp_path, [source], options)
    )
    assert observed == [expected]
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
        "authority": "operator-option",
    }
    assert report.assurance_status == "UNKNOWN"
    assert report.ci_exit_code == 1


@pytest.mark.parametrize("budget", [1, 300, 600])
def test_public_cli_routes_selected_budget(monkeypatch, budget):
    captured = []

    def run(files, **kwargs):
        captured.append(kwargs["linux_pytest_timeout_seconds"])
        return 0, None

    monkeypatch.setattr(review_commands, "run_command", run)
    result = CliRunner().invoke(review_commands.app, ["review", "run", "--linux-pytest-timeout-seconds", str(budget)])
    assert result.exit_code == 0, result.output
    assert captured == [budget]


@pytest.mark.parametrize("budget", ["0", "601", "1.5", "false"])
def test_public_cli_rejects_invalid_budget_before_review(monkeypatch, budget):
    def run(files, **kwargs):
        raise AssertionError("invalid budget reached review")

    monkeypatch.setattr(review_commands, "run_command", run)
    result = CliRunner().invoke(review_commands.app, ["review", "run", "--linux-pytest-timeout-seconds", budget])
    assert result.exit_code == 2
