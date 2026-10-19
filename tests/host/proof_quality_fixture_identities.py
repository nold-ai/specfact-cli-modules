"""Host-owned Bash proofs for quality fixture authentication."""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from importlib import import_module
from pathlib import Path

import pytest

from tests.support.capsule_review_fixtures import (
    _BLOCK2_HATCH_FIXTURE,
    _git,
    assert_block2_trace,
    deferral_policy_environment,
    deferral_worktree,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_smoke_lock(tmp_path: Path, invalid: str | None) -> dict[str, str]:
    lock: dict[str, str] = {
        "repository": "nold-ai/specfact-cli-modules",
        "commit": "a" * 40,
        "tree": "b" * 40,
    }
    if invalid in {"repository", "commit", "tree"}:
        lock[invalid] = "unexpected\nvalue"
    if invalid == "missing":
        del lock["tree"]
    lock_path = tmp_path / "specfact-cli/ci/runtime-smoke-fixture.lock.json"
    lock_path.parent.mkdir(parents=True)
    lock_path.write_text("{" if invalid == "json" else "[]" if invalid == "shape" else json.dumps(lock))
    return lock


@pytest.mark.parametrize("invalid", [None, "json", "repository", "commit", "tree", "missing", "shape"])
def test_quality_smoke_lock_is_validated_before_outputs(tmp_path: Path, invalid: str | None) -> None:
    yaml = import_module("yaml")
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/pr-orchestrator.yml").read_text())
    steps = {step.get("name"): step for step in workflow["jobs"]["quality"]["steps"]}
    assert "Read runtime smoke fixture identity" in steps, "quality job does not read the paired core smoke lock"
    reader = steps["Read runtime smoke fixture identity"]
    lock = _write_smoke_lock(tmp_path, invalid)
    output = tmp_path / "outputs"
    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", reader["run"]],
        cwd=tmp_path,
        env={**os.environ, "GITHUB_OUTPUT": str(output)},
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if invalid is not None:
        assert result.returncode != 0
        assert not output.exists() or not output.read_text()
    else:
        assert result.returncode == 0, result.stderr
        assert dict(line.split("=", 1) for line in output.read_text().splitlines()) == {
            "commit": lock["commit"],
            "tree": lock["tree"],
        }


def _smoke_checkout(tmp_path: Path, mismatch: str | None):
    fixture = tmp_path / "runtime-smoke-modules"
    fixture.mkdir()
    git_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Fixture",
        "GIT_AUTHOR_EMAIL": "fixture@example.test",
        "GIT_COMMITTER_NAME": "Fixture",
        "GIT_COMMITTER_EMAIL": "fixture@example.test",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }
    for args in (["init"], ["-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m", "fixture"]):
        subprocess.run(["git", *args], cwd=fixture, env=git_env, check=True, capture_output=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=fixture, text=True).strip()
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=fixture, text=True).strip()
    if mismatch == "tracked":
        (fixture / "staged.txt").write_text("dirty")
        subprocess.run(["git", "add", "staged.txt"], cwd=fixture, check=True, capture_output=True)
    if mismatch == "untracked":
        (fixture / "extra.txt").write_text("dirty")
    return fixture, git_env, commit, tree


@pytest.mark.parametrize("mismatch", [None, "commit", "tree", "tracked", "untracked"])
def test_quality_smoke_verifies_git_checkout_before_export(tmp_path: Path, mismatch: str | None) -> None:
    yaml = import_module("yaml")
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/pr-orchestrator.yml").read_text())
    steps = {step.get("name"): step for step in workflow["jobs"]["quality"]["steps"]}
    assert "Verify runtime smoke fixture" in steps, "quality job does not authenticate a separate smoke fixture"
    verification = steps["Verify runtime smoke fixture"]
    fixture, git_env, commit, tree = _smoke_checkout(tmp_path, mismatch)
    runner_temp = tmp_path / "runner-temp"
    runner_temp.mkdir()
    output = tmp_path / "environment"
    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", verification["run"]],
        cwd=tmp_path,
        env={
            **git_env,
            "GITHUB_WORKSPACE": str(tmp_path),
            "RUNNER_TEMP": str(runner_temp),
            "GITHUB_ENV": str(output),
            "FIXTURE_COMMIT": "0" * 40 if mismatch == "commit" else commit,
            "FIXTURE_TREE": "0" * 40 if mismatch == "tree" else tree,
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if mismatch is not None:
        assert result.returncode != 0
        assert not output.exists() or not output.read_text()
    else:
        assert result.returncode == 0, result.stderr
        _assert_authenticated_smoke_checkout(output, runner_temp, fixture, commit)


def _assert_authenticated_smoke_checkout(output, runner_temp, fixture, commit):
    relocated = runner_temp / "runtime-smoke-modules"
    assert output.read_text().strip() == f"SPECFACT_SMOKE_MODULES_REPO={relocated}"
    assert not fixture.exists()
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=relocated, text=True).strip() == commit
    assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=relocated, text=True).strip()


@pytest.fixture(name="policy_candidate")
def fixture_policy_candidate(tmp_path: Path):
    scenario = ("Darwin", "", "github-linux", "packages/specfact-code-review/resources/example.py", False, True, 0)
    worktree = deferral_worktree(tmp_path, scenario)
    temporary = tmp_path / "policy-temporary"
    temporary.mkdir()
    environment = (
        os.environ
        | deferral_policy_environment(worktree)
        | {
            "FIXTURE_PLATFORM": "Darwin",
            "FIXTURE_CALLS": str(tmp_path / "calls"),
            "GITHUB_ACTIONS": "",
            "CI": "",
            "SPECFACT_CODE_REVIEW_DEFER_TO_CI": "github-linux",
            "TMPDIR": str(temporary),
        }
    )
    return worktree, environment


def _run_policy_candidate(candidate, shell_setup=""):
    worktree, environment = candidate
    payload = worktree / "packages/specfact-code-review/resources/example.py"
    payload.write_text("candidate invocation\n")
    _git(worktree, "add", str(payload))
    script = (REPO_ROOT / "scripts/pre-commit-quality-checks.sh").read_text().rsplit('main "$@"', 1)[0]
    result = subprocess.run(
        ["bash", "-c", script + shell_setup + _BLOCK2_HATCH_FIXTURE],
        timeout=20,
        cwd=worktree,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
    )
    assert not list(Path(environment["TMPDIR"]).iterdir()), "temporary policy checker was not cleaned"
    return result


def _change_policy_candidate(worktree: Path, mutation: str) -> Path:
    workflow = worktree / ".github/workflows/pr-orchestrator.yml"
    original = workflow.read_bytes()
    workflow.write_bytes(original + b"\n# Candidate-controlled routing change.\n")
    _git(worktree, "add", str(workflow))
    checker = worktree / "scripts/validate_capsule_ci_schedule.py"
    marker = worktree / "candidate-checker-executed"
    if mutation == "candidate-pin":
        checker.write_text(
            checker.read_text().replace(
                hashlib.sha256(original).hexdigest(), hashlib.sha256(workflow.read_bytes()).hexdigest()
            )
        )
        _git(worktree, "add", str(checker))
    else:
        checker.write_text(f"from pathlib import Path\nPath({str(marker)!r}).touch()\nraise SystemExit(0)\n")
    if mutation == "unstaged-restoration":
        workflow.write_bytes(original)
    return marker


@pytest.mark.parametrize("mutation", ["candidate-pin", "successful-canary", "unstaged-restoration"])
def test_immutable_policy_rejects_candidate_self_approval(policy_candidate, mutation: str) -> None:
    worktree, _environment = policy_candidate
    marker = _change_policy_candidate(worktree, mutation)
    result = _run_policy_candidate(policy_candidate)
    assert result.returncode == 1, result.stderr
    assert "indexed orchestrator bytes differ" in result.stderr
    assert "DEFERRED" not in result.stderr
    assert not marker.exists(), "candidate checker executed"


def test_immutable_policy_accepts_reviewed_index_and_retains_contracts(policy_candidate) -> None:
    result = _run_policy_candidate(policy_candidate)
    assert result.returncode == 0, result.stderr
    assert_block2_trace(Path(policy_candidate[1]["FIXTURE_CALLS"]).read_text(encoding="utf-8"), 0, result.stderr)


@pytest.mark.parametrize(
    "selection", ["missing", "short", "uppercase", "unknown", "blob", "missing-checker", "empty-checker"]
)
def test_immutable_policy_requires_available_commit_checker(policy_candidate, selection: str) -> None:
    worktree, environment = policy_candidate
    commit_key = "SPECFACT_CODE_REVIEW_POLICY_COMMIT"
    if selection in {"missing-checker", "empty-checker"}:
        checker = worktree / "scripts/validate_capsule_ci_schedule.py"
        if selection == "missing-checker":
            checker.unlink()
        else:
            checker.write_text("")
        _git(worktree, "add", str(checker))
        _git(worktree, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "unusable policy")
        environment[commit_key] = _git(worktree, "rev-parse", "HEAD")
    else:
        environment[commit_key] = {
            "missing": "",
            "short": "abc123",
            "uppercase": "A" * 40,
            "unknown": "0" * 40,
            "blob": _git(worktree, "rev-parse", "HEAD:scripts/validate_capsule_ci_schedule.py"),
        }[selection]
    result = _run_policy_candidate(policy_candidate)
    assert result.returncode != 0, result.stderr
    assert "DEFERRED" not in result.stderr


@pytest.mark.parametrize("selection", ["missing", "relative", "nonexistent", "failure"])
def test_immutable_policy_requires_explicit_working_host_python(policy_candidate, selection: str) -> None:
    worktree, environment = policy_candidate
    failing = worktree.parent / "failed-python"
    failing.write_text("#!/bin/sh\nexit 73\n")
    failing.chmod(0o700)
    environment["SPECFACT_CODE_REVIEW_POLICY_PYTHON"] = {
        "missing": "",
        "relative": "python3",
        "nonexistent": str(worktree.parent / "absent"),
        "failure": str(failing),
    }[selection]
    result = _run_policy_candidate(policy_candidate)
    assert result.returncode != 0, result.stderr
    assert "DEFERRED" not in result.stderr


def test_immutable_policy_refuses_git_extraction_failure(policy_candidate) -> None:
    result = _run_policy_candidate(
        policy_candidate,
        '\ngit() { if [[ "$1 $2" == "--no-replace-objects show" ]]; then return 74; fi; command git "$@"; }\n',
    )
    assert result.returncode != 0, result.stderr
    assert "DEFERRED" not in result.stderr


def test_immutable_policy_ignores_git_replacement(policy_candidate) -> None:
    worktree, environment = policy_candidate
    marker = _change_policy_candidate(worktree, "successful-canary")
    _git(worktree, "add", "scripts/validate_capsule_ci_schedule.py")
    _git(worktree, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "candidate replacement")
    replacement = _git(worktree, "commit-tree", "HEAD^{tree}", "-m", "replacement without ancestry cycle")
    _git(worktree, "replace", environment["SPECFACT_CODE_REVIEW_POLICY_COMMIT"], replacement)
    result = _run_policy_candidate(policy_candidate)
    assert result.returncode == 1, result.stderr
    assert "indexed orchestrator bytes differ" in result.stderr
    assert not marker.exists(), "replacement policy executed"


def test_immutable_policy_isolates_python_imports(policy_candidate) -> None:
    worktree, environment = policy_candidate
    marker = worktree / "candidate-import-executed"
    poison = f"from pathlib import Path\nPath({str(marker)!r}).touch()\nraise SystemExit(0)\n"
    for name in ("hashlib.py", "sitecustomize.py"):
        (worktree / name).write_text(poison)
    environment["PYTHONPATH"] = str(worktree)
    result = _run_policy_candidate(policy_candidate)
    assert result.returncode == 0, result.stderr
    assert not marker.exists(), "candidate Python import executed"


@pytest.mark.parametrize("selection", ["direct", "external-link", "parent-link", "checkout-alias"])
def test_immutable_policy_rejects_candidate_interpreter_before_execution(policy_candidate, selection: str) -> None:
    worktree, environment = policy_candidate
    _change_policy_candidate(worktree, "successful-canary")
    interpreter = worktree / ".venv/bin/python"
    interpreter.parent.mkdir(parents=True)
    marker = worktree / "candidate-interpreter-executed"
    interpreter.write_text(f"#!/bin/sh\ntouch {shlex.quote(str(marker))}\nexit 0\n")
    interpreter.chmod(0o700)
    selected = interpreter
    if selection == "external-link":
        selected = worktree.parent / "external-python"
        selected.symlink_to(interpreter)
    elif selection == "parent-link":
        alias = worktree.parent / "external-bin"
        alias.symlink_to(interpreter.parent, target_is_directory=True)
        selected = alias / "python"
    elif selection == "checkout-alias":
        alias = worktree.parent / "checkout-alias"
        alias.symlink_to(worktree, target_is_directory=True)
        selected = alias / ".venv/bin/python"
        policy_candidate = alias, environment
    environment["SPECFACT_CODE_REVIEW_POLICY_PYTHON"] = str(selected)
    result = _run_policy_candidate(policy_candidate)
    assert result.returncode != 0, result.stderr
    assert "outside the candidate repository" in result.stderr
    assert "DEFERRED" not in result.stderr
    assert not marker.exists(), "candidate interpreter executed"


@pytest.mark.parametrize("inside", [False, True])
def test_immutable_policy_checks_external_interpreter_symlink_location(policy_candidate, inside: bool) -> None:
    worktree, environment = policy_candidate
    selected = (worktree if inside else worktree.parent) / "host-python-link"
    selected.symlink_to(environment["SPECFACT_CODE_REVIEW_POLICY_PYTHON"])
    environment["SPECFACT_CODE_REVIEW_POLICY_PYTHON"] = str(selected)
    result = _run_policy_candidate(policy_candidate)
    if inside:
        assert result.returncode != 0, result.stderr
        assert "outside the candidate repository" in result.stderr
        assert "DEFERRED" not in result.stderr
    else:
        assert result.returncode == 0, result.stderr
        assert_block2_trace(Path(environment["FIXTURE_CALLS"]).read_text(encoding="utf-8"), 0, result.stderr)


@pytest.fixture(name="portable_policy_candidate")
def fixture_portable_policy_candidate(policy_candidate):
    worktree, environment = policy_candidate
    commands = worktree.parent / "host-commands-without-realpath"
    commands.mkdir()
    for name in ("bash", "git", "dirname", "grep", "mktemp", "rm", "readlink", "mkdir", "sort"):
        executable = "/bin/bash" if name == "bash" and sys.platform == "darwin" else shutil.which(name)
        assert executable is not None, f"required host fixture command is missing: {name}"
        (commands / name).symlink_to(executable)
    environment["PATH"] = str(commands)
    assert shutil.which("realpath", path=environment["PATH"]) is None
    unavailable = subprocess.run(
        [str(commands / "bash"), "-c", "command -v realpath"],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert unavailable.returncode == 1 and not unavailable.stdout, unavailable.stderr
    return policy_candidate


def _write_interpreter_canary(path: Path, marker: Path, host_python: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    invocation = f'exec {shlex.quote(host_python)} "$@"' if host_python else "exit 0"
    path.write_text(f"#!/bin/sh\nprintf '%s' \"$0\" > {shlex.quote(str(marker))}\n{invocation}\n", encoding="utf-8")
    path.chmod(0o700)


@pytest.mark.parametrize(
    "selection",
    [
        "direct",
        "absolute-link",
        "relative-chain",
        "absolute-chain",
        "parent-alias",
        "parent-alias-dotdot",
        "spaces-and-glob",
        "prefix-sibling",
        "native-limit-chain",
        "intermediate-candidate-link",
    ],
)
def test_immutable_policy_accepts_external_python_without_realpath(portable_policy_candidate, selection: str) -> None:
    worktree, environment = portable_policy_candidate
    host_python = Path(environment["SPECFACT_CODE_REVIEW_POLICY_PYTHON"])
    external = worktree.parent / "external host [python]"
    external.mkdir()
    paths = {
        "direct": host_python,
        "absolute-link": external / "python",
        "spaces-and-glob": external / "python * [host]",
        "prefix-sibling": worktree.with_name(worktree.name + "-other") / "python",
    }
    for name in ("absolute-link", "spaces-and-glob", "prefix-sibling"):
        paths[name].parent.mkdir(exist_ok=True)
        paths[name].symlink_to(host_python)
    physical_child = external / "child"
    physical_child.mkdir()
    alias = worktree.parent / "host-parent-alias"
    alias.symlink_to(external, target_is_directory=True)
    child_alias = worktree.parent / "host-child-alias"
    child_alias.symlink_to(physical_child, target_is_directory=True)
    paths["parent-alias"] = alias / "python"
    paths["parent-alias-dotdot"] = child_alias / "../python"
    for name, count, absolute in (
        ("relative-chain", 3, False),
        ("absolute-chain", 3, True),
        ("native-limit-chain", 32 if sys.platform == "darwin" else 40, False),
    ):
        directory = external / name
        directory.mkdir()
        previous = directory / "python-0"
        previous.symlink_to(host_python)
        for index in range(1, count):
            link = directory / f"python-{index}"
            link.symlink_to(previous if absolute else previous.name)
            previous = link
        paths[name] = previous
    intermediate = worktree / "intermediate-link"
    intermediate.symlink_to(paths["relative-chain"])
    paths["intermediate-candidate-link"] = external / "external-selection"
    paths["intermediate-candidate-link"].symlink_to(intermediate)
    selected = paths[selection]
    assert selected.is_file() and os.access(selected, os.X_OK), "fixture exceeded the host's executable link limit"
    environment["SPECFACT_CODE_REVIEW_POLICY_PYTHON"] = str(selected)
    result = _run_policy_candidate(portable_policy_candidate)
    assert result.returncode == 0, result.stderr
    assert_block2_trace(Path(environment["FIXTURE_CALLS"]).read_text(encoding="utf-8"), 0, result.stderr)


@pytest.mark.parametrize(
    "selection", ["direct", "external-link", "relative-chain", "parent-link", "checkout-alias", "inside-to-host"]
)
def test_immutable_policy_refuses_candidate_python_without_realpath(portable_policy_candidate, selection: str) -> None:
    worktree, environment = portable_policy_candidate
    marker = worktree / "candidate-interpreter-executed"
    interpreter = worktree / ".venv/bin/python"
    _write_interpreter_canary(interpreter, marker)
    selected = interpreter
    if selection in {"external-link", "relative-chain"}:
        selected = worktree.parent / "external-python"
        selected.symlink_to(interpreter)
        if selection == "relative-chain":
            outer = worktree.parent / "relative-python"
            outer.symlink_to(selected.name)
            selected = outer
    elif selection in {"parent-link", "checkout-alias"}:
        alias = worktree.parent / "candidate-alias"
        alias.symlink_to(interpreter.parent if selection == "parent-link" else worktree, target_is_directory=True)
        selected = alias / "python" if selection == "parent-link" else alias / ".venv/bin/python"
        if selection == "checkout-alias":
            portable_policy_candidate = alias, environment
    elif selection == "inside-to-host":
        host = worktree.parent / "external-python-canary"
        _write_interpreter_canary(host, marker, environment["SPECFACT_CODE_REVIEW_POLICY_PYTHON"])
        selected = worktree / "host-python-link"
        selected.symlink_to(host)
    environment["SPECFACT_CODE_REVIEW_POLICY_PYTHON"] = str(selected)
    result = _run_policy_candidate(portable_policy_candidate)
    assert result.returncode == 1, result.stderr
    assert "Capsule review deferral" in result.stderr
    assert "DEFERRED" not in result.stderr
    assert not marker.exists(), "candidate-owned selected location or target executed"


@pytest.mark.parametrize("failure", ["broken-link", "cycle", "readlink-failure"])
def test_immutable_policy_refuses_unresolved_python_without_realpath(portable_policy_candidate, failure: str) -> None:
    worktree, environment = portable_policy_candidate
    marker = worktree / "unresolved-interpreter-executed"
    host = worktree.parent / "external-python-canary"
    _write_interpreter_canary(host, marker, environment["SPECFACT_CODE_REVIEW_POLICY_PYTHON"])
    selected = worktree.parent / "selected-python"
    selected.symlink_to(host if failure == "readlink-failure" else selected.name if failure == "cycle" else "absent")
    environment["SPECFACT_CODE_REVIEW_POLICY_PYTHON"] = str(selected)
    shell_setup = "\nreadlink() { return 74; }\n" if failure == "readlink-failure" else ""
    result = _run_policy_candidate(portable_policy_candidate, shell_setup)
    assert result.returncode == 1, result.stderr
    assert "Capsule review deferral" in result.stderr
    assert "DEFERRED" not in result.stderr
    assert not marker.exists(), "unresolved interpreter executed"


@pytest.mark.parametrize("selection", ["direct", "relative-link", "absolute-link", "parent-newlines"])
def test_immutable_policy_preserves_host_path_bytes_without_realpath(portable_policy_candidate, selection: str) -> None:
    worktree, environment = portable_policy_candidate
    external = worktree.parent / "external host"
    marker = worktree.parent / "intended-host-executed"
    wrong_marker = worktree.parent / "wrong-host-executed"
    host_python = environment["SPECFACT_CODE_REVIEW_POLICY_PYTHON"]
    target = external / "python\n\n"
    if selection == "parent-newlines":
        target = external / "directory\n\n" / "python"
        wrong_target = external / "directory" / "python"
    else:
        wrong_target = external / "python"
    _write_interpreter_canary(target, marker, host_python)
    _write_interpreter_canary(wrong_target, wrong_marker)
    selected = target
    if selection in {"relative-link", "absolute-link"}:
        selected = external / "selected-python"
        selected.symlink_to(target.name if selection == "relative-link" else target)
    environment["SPECFACT_CODE_REVIEW_POLICY_PYTHON"] = str(selected)
    result = _run_policy_candidate(portable_policy_candidate)
    assert not wrong_marker.exists(), "newline-stripped sibling executed"
    assert result.returncode == 0, result.stderr
    assert marker.read_text(encoding="utf-8") == str(target.resolve()), "the exact external executable was not invoked"
    assert_block2_trace(Path(environment["FIXTURE_CALLS"]).read_text(encoding="utf-8"), 0, result.stderr)
