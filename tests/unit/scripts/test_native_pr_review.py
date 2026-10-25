from __future__ import annotations

import importlib.util
import tomllib
from copy import deepcopy
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/native_pr_review.py"
COVERAGE_ROOTS = tuple(tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["coverage"]["run"]["source"])


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


def test_semgrep_dependencies_are_separate_from_signed_controller(tmp_path):
    import subprocess
    import sys

    workflow = yaml.safe_load((ROOT / ".github/workflows/native-pr-review.yml").read_text())
    steps = workflow["jobs"]["independent-review"]["steps"]
    install = _step_named(steps, "Install independent signed reviewer")["run"]
    program = install.split("<<'PYTHON'\n", 1)[1].split("\nPYTHON", 1)[0]
    (tmp_path / "base-pyproject.toml").write_bytes((ROOT / "pyproject.toml").read_bytes())
    lock = (
        ROOT
        / "packages/specfact-code-review/src/specfact_code_review/resources/contracts/pr-range-v1-toolchain-lock.json"
    )
    (tmp_path / "analyzer-lock.json").write_bytes(lock.read_bytes())
    subprocess.run([sys.executable, "-I", "-c", program, str(tmp_path)], check=True)
    requirements = (tmp_path / "requirements.txt").read_text().splitlines()
    assert not any(item.startswith("semgrep") for item in requirements), (
        "Semgrep and core require incompatible Click versions"
    )
    assert (tmp_path / "semgrep-requirement.txt").read_text().strip() == "semgrep==1.144.0"
    assert '"$trusted/semgrep/bin/python" -I -m pip install -r "$trusted/semgrep-requirement.txt"' in install
    constraints = (tmp_path / "semgrep-constraints.txt").read_text().splitlines()
    assert "pydantic==2.13.4" in constraints
    assert "mcp==1.16.0" in constraints
    assert '-c "$trusted/semgrep-constraints.txt"' in install
    review = _step_named(steps, "Run complete independent native review")["run"]
    assert 'PATH="$trusted/venv/bin:$trusted/semgrep/bin:' in review


def test_semgrep_version_comes_from_selected_executable(native_review, monkeypatch):
    import subprocess

    def version(command, **kwargs):
        assert command == ["semgrep", "--version"]
        assert kwargs["check"] and kwargs["timeout"] == 30
        return subprocess.CompletedProcess(command, 0, "1.144.0\n", "")

    monkeypatch.setattr(native_review.subprocess, "run", version)
    monkeypatch.setattr(native_review.importlib.metadata, "version", lambda name: "controller-version")
    versions = native_review._tool_versions()
    assert versions["semgrep"] == "1.144.0"
    assert versions["specfact-cli"] == "controller-version"


def test_semgrep_startup_failure_preserves_bounded_stderr(native_review, monkeypatch):
    import subprocess

    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(
            1, ["semgrep", "--version"], stderr="x" * 3000 + "missing dependency symbol"
        )

    monkeypatch.setattr(native_review.subprocess, "run", fail)
    monkeypatch.setattr(native_review.importlib.metadata, "version", lambda name: "controller-version")
    with pytest.raises(ValueError, match="missing dependency symbol") as error:
        native_review._tool_versions()
    assert len(str(error.value)) < 2100


@pytest.mark.parametrize("commit", ["046d366c190af7a188d6f48953a96edb65e766db", "0" * 40])
def test_runtime_smoke_rejects_unreviewed_fixture_identity(tmp_path, commit):
    import json
    import subprocess
    import sys

    jobs = yaml.safe_load((ROOT / ".github/workflows/pr-orchestrator.yml").read_text())["jobs"]
    verify = _step_named(jobs["quality"]["steps"], "Verify reviewed runtime smoke fixture")
    program = verify["run"].split("<<'PYTHON'\n", 1)[1].split("\nPYTHON", 1)[0]
    lock = tmp_path / "specfact-cli/ci/runtime-smoke-fixture.lock.json"
    lock.parent.mkdir(parents=True)
    lock.write_text(
        json.dumps(
            {
                "repository": "nold-ai/specfact-cli-modules",
                "commit": commit,
                "tree": "c5b44db3477d1c9ea8dae1dceab2af276d265353",
            }
        )
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", program], cwd=tmp_path, capture_output=True, text=True, check=False
    )
    assert (result.returncode == 0) == (commit != "0" * 40), result.stderr


def test_runtime_smoke_preserves_launchers_and_isolates_dependencies():
    jobs = yaml.safe_load((ROOT / ".github/workflows/pr-orchestrator.yml").read_text())["jobs"]
    steps = jobs["quality"]["steps"]
    checkout = _step_named(steps, "Checkout reviewed runtime smoke fixture")
    assert checkout["with"]["ref"] == "046d366c190af7a188d6f48953a96edb65e766db"
    assert checkout["with"]["persist-credentials"] is False
    smoke = _step_named(steps, "Runtime discovery smoke across package managers")
    assert steps.index(checkout) < steps.index(smoke)
    for launcher in ("direct", "hatch-source", "pip-editable", "pipx", "uv-run", "uvx"):
        assert "--launcher " + launcher in smoke["run"]
    assert 'python -m venv "$launchers"' in smoke["run"]
    assert '"$launchers/bin/python" -m pip install uv' in smoke["run"]
    assert '--modules-repo "$GITHUB_WORKSPACE/specfact-cli/runtime-smoke-modules"' in smoke["run"]


def test_runtime_smoke_seeds_frozen_cache_before_offline_execution():
    jobs = yaml.safe_load((ROOT / ".github/workflows/pr-orchestrator.yml").read_text())["jobs"]
    command = _step_named(jobs["quality"]["steps"], "Runtime discovery smoke across package managers")["run"]
    assert "check_dependency_trust_exceptions.py" in command
    assert "sync --locked --all-extras --no-install-project --project specfact-cli" in command
    assert (
        command.index("check_dependency_trust_exceptions.py")
        < command.index("sync --locked")
        < command.index("runtime_discovery_smoke.py")
    )
    assert 'UV_PROJECT_ENVIRONMENT="$RUNNER_TEMP/runtime-smoke-seed"' in command
    assert 'PATH="$RUNNER_TEMP/runtime-smoke-seed/bin:$launchers/bin:$PATH"' in command
    assert "virtualenv<21" not in command


def test_existing_nonmirrored_package_tests_are_selected(native_review):
    inventory = native_review._test_inventory(
        ROOT, [Path("packages/specfact-codebase/src/specfact_codebase/import_cmd/commands.py")], roots=COVERAGE_ROOTS
    )
    assert "tests/unit/specfact_codebase/test_import_command_contract.py" in inventory
    assert all((ROOT / path).is_file() for path in inventory)


def test_missing_package_tests_cannot_pass_selection(native_review, tmp_path):
    with pytest.raises(ValueError, match="test"):
        native_review._test_inventory(
            tmp_path,
            [Path("packages/specfact-codebase/src/specfact_codebase/import_cmd/commands.py")],
            roots=COVERAGE_ROOTS,
        )


@pytest.mark.parametrize(
    "source,expected",
    [
        ("tools/contract_first_smart_test.py", "tests/unit/tools/test_contract_first_smart_test.py"),
        ("src/specfact_cli_modules/dev_bootstrap.py", "tests/unit/test_dev_bootstrap.py"),
    ],
    ids=["tool", "top-level-src"],
)
def test_coverage_roots_select_existing_source_tests(native_review, source, expected):
    inventory = native_review._test_inventory(ROOT, [Path(source)], roots=COVERAGE_ROOTS)
    assert expected in inventory


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
