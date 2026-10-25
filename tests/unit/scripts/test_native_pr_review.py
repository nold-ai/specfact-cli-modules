from __future__ import annotations

import importlib.util
from copy import deepcopy
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/native_pr_review.py"


def _step_named(steps, name):
    return next(step for step in steps if step.get("name") == name)


@pytest.fixture(autouse=True)
def record_selector(request):
    request.node.user_properties.append(("specfact.selector", request.node.nodeid))


@pytest.fixture
def native_review():
    spec = importlib.util.spec_from_file_location("native_pr_review", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def complete(native_review):
    return {
        "head": "a" * 40,
        "source_before": "b" * 40,
        "source_after": "b" * 40,
        "members": [{"id": member, "outcome": "COMPLETE", "findings": []} for member in native_review.REQUIRED_MEMBERS],
        "policy_exit": 0,
    }


def test_complete_native_review_accepts_exact_head(native_review, complete):
    native_review._validate_receipt(complete, expected_head="a" * 40)


@pytest.mark.parametrize("fault", ["missing", "duplicate", "unknown", "stale", "source", "policy", "malformed"])
def test_incomplete_native_review_cannot_pass(native_review, complete, fault):
    receipt = deepcopy(complete)
    if fault == "missing":
        receipt["members"].pop()
    if fault == "duplicate":
        receipt["members"].append(receipt["members"][0])
    if fault == "unknown":
        receipt["members"][0]["outcome"] = "UNKNOWN"
    if fault == "stale":
        receipt["head"] = "c" * 40
    if fault == "source":
        receipt["source_after"] = "d" * 40
    if fault == "policy":
        receipt["policy_exit"] = 1
    if fault == "malformed":
        receipt["members"][0]["findings"] = None
    with pytest.raises(ValueError):
        native_review._validate_receipt(receipt, expected_head="a" * 40)


@pytest.mark.parametrize(
    "finding",
    [
        {"category": "tool_error", "severity": "warning"},
        {"category": "contracts", "evidence_outcome": "UNKNOWN"},
        {"category": "testing", "execution_state": "skipped"},
    ],
)
def test_raw_incomplete_findings_block_even_when_policy_exit_is_zero(native_review, complete, finding):
    complete["members"][0]["findings"] = [finding]
    with pytest.raises(ValueError, match="incomplete"):
        native_review._validate_receipt(complete, expected_head="a" * 40)


def test_required_signed_rule_pack_cannot_silently_disappear(native_review, tmp_path):
    with pytest.raises(ValueError, match="rule"):
        native_review._rule_identities(tmp_path)


def test_quality_requires_native_review_without_capsule_prerequisite():
    jobs = yaml.safe_load((ROOT / ".github/workflows/pr-orchestrator.yml").read_text())["jobs"]
    assert "customer-capsules" not in jobs
    required = {"verify-module-signatures", "native-scope", "native-hatch", "native-review"}
    assert required <= set(jobs["quality"]["needs"])
    gate = next(step for step in jobs["quality"]["steps"] if step.get("name") == "Require independent native review")
    assert gate["env"]["NATIVE_REVIEW_RESULT"] == "${{ needs.native-review.result }}"
    assert '!= "success"' in gate["run"]
    assert not gate.get("continue-on-error", False)


def _assert_native_review_environment(review):
    assert "env -i" in review["run"]
    assert 'python" -I ' in review["run"]
    assert "native_pr_review.py" in review["run"]
    assert "GITHUB_TOKEN" not in review.get("env", {})
    assert "SPECFACT_HATCH_PROOF_WORKSPACE=" in review["run"]
    assert '$(dirname "$SPECFACT_HATCH_PROJECT_PYTHON")' in review["run"]


def test_independent_native_job_uses_signed_reviewer_and_exact_subject():
    workflow = yaml.safe_load((ROOT / ".github/workflows/native-pr-review.yml").read_text())
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["independent-review"]
    assert not job.get("continue-on-error", False)
    steps = job["steps"]
    checkout = _step_named(steps, "Checkout exact head")
    assert checkout["with"]["ref"] == "${{ github.event.pull_request.head.sha || github.sha }}"
    assert checkout["with"]["persist-credentials"] is False
    install = _step_named(steps, "Install independent signed reviewer")
    assert "specfact-cli==0.55.4" in install["run"]
    assert "--version 0.51.2 --source marketplace" in install["run"]
    review = _step_named(steps, "Run complete independent native review")
    _assert_native_review_environment(review)


def test_all_signed_semgrep_passes_are_required(native_review, tmp_path):
    rules = tmp_path / ".semgrep"
    rules.mkdir()
    for name in ("clean_code.yaml", "bugs.yaml"):
        (rules / name).write_text("rules:\n  - id: example\n")
    with pytest.raises(ValueError, match="ai-bloat"):
        native_review._rule_identities(tmp_path)


def test_native_tools_are_installed_from_base_before_project_bootstrap():
    workflow = yaml.safe_load((ROOT / ".github/workflows/native-pr-review.yml").read_text())
    steps = workflow["jobs"]["independent-review"]["steps"]
    install = _step_named(steps, "Install independent signed reviewer")
    bootstrap = _step_named(steps, "Bootstrap native repository environment")
    assert steps.index(install) < steps.index(bootstrap)
    assert 'git show "$base:pyproject.toml"' in install["run"]
    review = _step_named(steps, "Run complete independent native review")
    assert 'PATH="$trusted/venv/bin:' in review["run"]


def test__native_test_command_uses_trusted_config(native_review, tmp_path):
    command = native_review._native_test_command(
        python=Path("/project/python"),
        config=tmp_path / "pyproject.toml",
        output=tmp_path,
    )
    assert command[:3] == ["/project/python", "-m", "pytest"]
    assert "--rootdir=." in command
    assert command[command.index("-c") + 1] == str(tmp_path / "pyproject.toml")
    assert f"--cov-config={tmp_path / 'pyproject.toml'}" in command
    assert "tests/host/proof_capsule_deferred_review_ci.py" in command
    assert "tests" not in command, "A parent directory can discard explicitly selected proof files"


def test_darwin_deferral_requires_indexed_native_replacement(tmp_path):
    import os
    import subprocess

    from tests.support.capsule_review_fixtures import (
        _BLOCK2_HATCH_FIXTURE,
        _git,
        deferral_worktree,
    )

    scenario = ("Darwin", "", "github-linux", "specfact-code-review", False, True, 0)
    worktree = deferral_worktree(tmp_path, scenario)
    workflow = worktree / ".github/workflows/native-pr-review.yml"
    workflow.write_text("name: missing-independent-native-review\n")
    _git(worktree, "add", ".")
    calls = tmp_path / "calls"
    script = (ROOT / "scripts/pre-commit-quality-checks.sh").read_text().rsplit('main "$@"', 1)[0]
    result = subprocess.run(
        ["bash", "-c", script + _BLOCK2_HATCH_FIXTURE],
        cwd=worktree,
        env=os.environ
        | {
            "FIXTURE_PLATFORM": "Darwin",
            "FIXTURE_CALLS": str(calls),
            "GITHUB_ACTIONS": "",
            "CI": "",
            "SPECFACT_CODE_REVIEW_DEFER_TO_CI": "github-linux",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stderr
    assert "native" in result.stderr.lower()


def test_project_tests_do_not_inherit_controller_diff_mode(native_review, monkeypatch):
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_CHANGED_DIFF", "cached")
    monkeypatch.setenv("SPECFACT_HATCH_PROJECT_PYTHON", "/project/python")
    environment = native_review._native_test_environment()
    assert "SPECFACT_CODE_REVIEW_CHANGED_DIFF" not in environment
    assert environment["SPECFACT_HATCH_PROJECT_PYTHON"] == "/project/python"


def test_subject_detects_assume_unchanged_mutation(native_review, tmp_path, monkeypatch):
    import subprocess

    def git(*args):
        return subprocess.check_output(["git", "-C", str(tmp_path), *args], text=True).strip()

    git("init", "-q")
    git("config", "user.name", "native-ci-fixture")
    git("config", "user.email", "native-ci@example.invalid")
    git("config", "commit.gpgsign", "false")
    git("config", "core.hooksPath", "/dev/null")
    source = tmp_path / "app.py"
    source.write_text("VALUE = 1\n")
    git("add", ".")
    git("commit", "-qm", "base")
    base = git("rev-parse", "HEAD")
    source.write_text("VALUE = 2\n")
    git("add", ".")
    git("commit", "-qm", "head")
    head = git("rev-parse", "HEAD")
    git("reset", "--soft", base)
    monkeypatch.chdir(tmp_path)
    before, _ = native_review._subject(tmp_path, head, base)
    git("update-index", "--assume-unchanged", "--", "app.py")
    source.write_text("VALUE = 3\n")
    after, _ = native_review._subject(tmp_path, head, base)
    assert before != after, "Git assume-unchanged hid a real source mutation"


def test_no_python_sources_requires_positive_applicability(native_review, complete):
    complete["files"] = {}
    for member in complete["members"][:-1]:
        member.update(outcome="NOT_APPLICABLE", reason="no_changed_python_sources")
    native_review._validate_receipt(complete, expected_head="a" * 40)
    complete["files"] = {"changed.py": "hash"}
    with pytest.raises(ValueError):
        native_review._validate_receipt(complete, expected_head="a" * 40)


def test_boundary_script_imports_through_native_contract_analyzer():
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from crosshair.util import load_file; from pathlib import Path; "
            'load_file(Path("scripts/check-bundle-imports.py"))',
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_targeted_source_test_skip_is_incomplete(native_review, tmp_path):
    report = tmp_path / "tests.xml"
    report.write_text("""<testsuite>
      <testcase classname="host.proof_capsule_deferred_review_ci" name="required"/>
      <testcase classname="integration.test_hatch_project_runtime" name="required"/>
      <testcase classname="unit.test_changed_source" name="required"><skipped/></testcase>
    </testsuite>""")
    with pytest.raises(ValueError, match="skipped"):
        native_review._require_native_test_evidence(report)


def test_selected_test_file_cannot_disappear_from_evidence(native_review, tmp_path):
    report = tmp_path / "tests.xml"
    report.write_text("""<testsuite>
      <testcase classname="host.proof_capsule_deferred_review_ci" name="required"
        file="tests/host/proof_capsule_deferred_review_ci.py"/>
      <testcase classname="integration.test_hatch_project_runtime" name="required"
        file="tests/integration/test_hatch_project_runtime.py"/>
    </testsuite>""")
    with pytest.raises(ValueError, match="test_changed_source"):
        native_review._require_native_test_evidence(report, selectors=("tests/unit/test_changed_source.py",))
