from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[3]
LEGACY = ".github/workflows/capsule-customer-execution.yml"


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


@pytest.fixture(autouse=True)
def record_selector(request, record_property):
    record_property("specfact.selector", request.node.nodeid)


@pytest.fixture(name="repository")
def scope_repository(tmp_path: Path) -> Path:
    (tmp_path / "scripts").mkdir()
    for name in ("check-bundle-imports.py", "check_native_review_scope.py"):
        source = ROOT / "scripts" / name
        if source.exists():
            shutil.copyfile(source, tmp_path / "scripts" / name)
    legacy = tmp_path / LEGACY
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes((ROOT / LEGACY).read_bytes())
    runtime = tmp_path / "packages/specfact-code-review/src/specfact_code_review/run/runtime_builder.py"
    runtime.parent.mkdir(parents=True)
    runtime.write_text("VALUE = 1\n")
    test = tmp_path / "tests/unit/test_capsule_review_projection.py"
    test.parent.mkdir(parents=True)
    test.write_text("def test_existing():\n    assert True\n")
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.name", "scope-fixture")
    git(tmp_path, "config", "user.email", "scope-fixture@example.invalid")
    git(tmp_path, "config", "commit.gpgsign", "false")
    git(tmp_path, "config", "core.hooksPath", "/dev/null")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "baseline")
    policy = {
        "execution_backend": "trusted-local-native",
        "freeze_ref": git(tmp_path, "rev-parse", "HEAD"),
        "legacy_paths": [
            LEGACY,
            "packages/specfact-code-review/src/specfact_code_review/run/*",
            "tests/unit/test_capsule*",
        ],
        "baseline_files": {
            name: [mode, oid]
            for row in git(tmp_path, "ls-tree", "-r", "HEAD").splitlines()
            for metadata, name in [row.split("\t", 1)]
            for mode, _, oid in [metadata.split()]
        },
    }
    (tmp_path / "openspec").mkdir()
    policy_path = tmp_path / "openspec/native-review-policy.json"
    policy_path.write_text(json.dumps(policy))
    checker = tmp_path / "scripts/check_native_review_scope.py"
    if checker.exists():
        approved_digest = hashlib.sha256((ROOT / "openspec/native-review-policy.json").read_bytes()).hexdigest()
        fixture_digest = hashlib.sha256(policy_path.read_bytes()).hexdigest()
        checker.write_text(checker.read_text().replace(approved_digest, fixture_digest))
    return tmp_path


def check(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(root / "scripts/check-bundle-imports.py")],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def rewrite_reviewed_policy(root: Path, field: str, value: object) -> None:
    path = root / "openspec/native-review-policy.json"
    old_digest = hashlib.sha256(path.read_bytes()).hexdigest()
    policy = json.loads(path.read_text())
    policy[field] = value
    path.write_text(json.dumps(policy))
    checker = root / "scripts/check_native_review_scope.py"
    checker.write_text(checker.read_text().replace(old_digest, hashlib.sha256(path.read_bytes()).hexdigest()))


@pytest.mark.parametrize(
    "path",
    [
        LEGACY,
        "packages/specfact-code-review/src/specfact_code_review/run/runtime_builder.py",
        "tests/unit/test_capsule_review_projection.py",
        "packages/specfact-code-review/src/specfact_code_review/run/new_capsule.py",
    ],
    ids=["workflow", "runtime", "test", "untracked"],
)
def test_boundary_rejects_capsule_changes(repository: Path, path: str) -> None:
    target = repository / path
    target.write_text(target.read_text() + "# capsule repair\n" if target.exists() else "VALUE = 2\n")
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert path in result.stdout + result.stderr
    assert "native" in (result.stdout + result.stderr).lower()


@pytest.mark.parametrize("change", ["unchanged", "native", "retirement"])
def test_boundary_preserves_native_work_and_retirement(repository: Path, change: str) -> None:
    if change == "native":
        target = repository / "packages/specfact-codebase/src/specfact_codebase/project_runtime.py"
        target.parent.mkdir(parents=True)
        target.write_text("VALUE = 2\n")
    elif change == "retirement":
        (repository / LEGACY).unlink()
    result = check(repository)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("change", ["unchanged", "native", "retirement", "repair", "addition", "mode"])
def test_native_scope_survives_squash_only_checkout(repository: Path, tmp_path: Path, change: str) -> None:
    final_tree = tmp_path / "squashed"
    shutil.copytree(repository, final_tree, ignore=shutil.ignore_patterns(".git", "squashed"))
    git(final_tree, "init", "-q")
    git(final_tree, "config", "user.name", "scope-fixture")
    git(final_tree, "config", "user.email", "scope-fixture@example.invalid")
    git(final_tree, "config", "commit.gpgsign", "false")
    git(final_tree, "config", "core.hooksPath", "/dev/null")
    git(final_tree, "add", ".")
    git(final_tree, "commit", "-qm", "single retained final tree")
    frozen = json.loads((final_tree / "openspec/native-review-policy.json").read_text())["freeze_ref"]
    absent = subprocess.run(["git", "-C", str(final_tree), "cat-file", "-e", frozen], capture_output=True, check=False)
    assert absent.returncode != 0, "Fixture unexpectedly retained the pre-squash feature commit"
    apply_squash_change(final_tree, change)
    result = check(final_tree)
    assert result.returncode == (0 if change in {"unchanged", "native", "retirement"} else 1), (
        result.stdout + result.stderr
    )
    assert "freeze_ref comparison unavailable" not in result.stdout + result.stderr
    if change in {"repair", "addition", "mode"}:
        assert "capsule" in result.stdout + result.stderr


def apply_squash_change(root: Path, change: str) -> None:
    if change == "native":
        (root / "native.py").write_text("VALUE = 1\n")
        return
    if change == "retirement":
        (root / LEGACY).unlink()
        return
    if change == "repair":
        (root / LEGACY).write_text("# capsule repair\n")
        return
    if change == "addition":
        (root / "tests/unit/test_capsule_new.py").write_text("VALUE = 1\n")
        return
    if change == "mode":
        (root / LEGACY).chmod(0o755)


def test_native_scope_preserves_git_checkout_normalization(repository: Path) -> None:
    git(repository, "config", "core.autocrlf", "true")
    path = repository / LEGACY
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert git(repository, "diff", "--name-only", "HEAD", "--", LEGACY) == ""
    result = check(repository)
    assert result.returncode == 0, result.stdout + result.stderr


def test_native_scope_rejects_staged_mode_when_filemode_disabled(repository: Path) -> None:
    git(repository, "config", "core.filemode", "false")
    git(repository, "update-index", "--chmod=+x", "--", LEGACY)
    assert LEGACY in git(repository, "diff", "--name-only", "HEAD", "--", LEGACY)
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert LEGACY in result.stdout


@pytest.mark.parametrize(
    "field,value",
    [("execution_backend", "capsule"), ("freeze_ref", "missing-revision")],
    ids=["backend", "revision"],
)
def test_boundary_rejects_invalid_policy(repository: Path, field: str, value: str) -> None:
    rewrite_reviewed_policy(repository, field, value)
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    expected = "execution_backend must remain" if field == "execution_backend" else "freeze_ref"
    assert expected in result.stdout + result.stderr


def test_boundary_rejects_actual_historical_capsule_repair(repository: Path) -> None:
    history = json.loads((ROOT / "tests/fixtures/native-review-scope-history.json").read_text())
    (repository / LEGACY).write_text(history["before"])
    git(repository, "add", LEGACY)
    git(repository, "commit", "-qm", "original historical excerpt")
    before = git(repository, "rev-parse", "HEAD")
    (repository / LEGACY).write_text(history["after"])
    git(repository, "add", LEGACY)
    git(repository, "commit", "-qm", "actual historical repair excerpt")
    after = git(repository, "rev-parse", "HEAD")
    result = subprocess.run(
        [
            sys.executable,
            str(repository / "scripts/check_native_review_scope.py"),
            f"--base-ref={before}",
            f"--head-ref={after}",
        ],
        cwd=repository,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert LEGACY in result.stdout + result.stderr


@pytest.mark.parametrize("weakening", ["baseline", "paths"])
def test_boundary_rejects_policy_weakening(repository: Path, weakening: str) -> None:
    (repository / LEGACY).write_text("# capsule repair\n")
    git(repository, "add", LEGACY)
    git(repository, "commit", "-qm", "capsule repair")
    path = repository / "openspec/native-review-policy.json"
    policy = json.loads(path.read_text())
    if weakening == "baseline":
        policy["freeze_ref"] = git(repository, "rev-parse", "HEAD")
    else:
        policy["legacy_paths"].remove(LEGACY)
    path.write_text(json.dumps(policy))
    result = check(repository)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "policy" in result.stdout + result.stderr


@pytest.mark.parametrize("source", ["policy", "head"])
def test_revision_options_cannot_write_files(repository: Path, source: str) -> None:
    output = repository / "unexpected-git-output"
    option = f"--output={output}"
    if source == "policy":
        rewrite_reviewed_policy(repository, "freeze_ref", option)
        result = check(repository)
    else:
        result = subprocess.run(
            [sys.executable, str(repository / "scripts/check_native_review_scope.py"), f"--head-ref={option}"],
            cwd=repository,
            capture_output=True,
            text=True,
            check=False,
        )
    assert result.returncode == 1, result.stdout + result.stderr
    assert not output.exists(), "Git interpreted a revision as a file-writing option"


def test_native_scope_ci_is_independent_and_read_only() -> None:
    path = ROOT / ".github/workflows/native-review-scope.yml"
    assert path.is_file(), "Required native scope CI job is missing"
    workflow = yaml.safe_load(path.read_text())
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["native-scope"]
    assert not job.get("needs")
    assert not job.get("continue-on-error", False)
    assert "python scripts/check_native_review_scope.py" in [step.get("run") for step in job["steps"]]
    checkout = checkout_step(job)
    assert checkout["with"] == {"fetch-depth": 0, "persist-credentials": False}
    assert_native_scope_prerequisite()


def assert_native_scope_prerequisite():
    orchestrator = yaml.safe_load((ROOT / ".github/workflows/pr-orchestrator.yml").read_text())
    assert "native-scope" in orchestrator["jobs"], "Required native scope prerequisite is missing"
    gate = orchestrator["jobs"]["native-scope"]
    assert gate["uses"] == "./.github/workflows/native-review-scope.yml"
    assert "native-scope" in orchestrator["jobs"]["quality"]["needs"]
    prerequisite = named_step(orchestrator["jobs"]["quality"], "Require native migration scope")
    assert prerequisite["env"]["NATIVE_SCOPE_RESULT"] == "${{ needs.native-scope.result }}"
    assert '"$NATIVE_SCOPE_RESULT" != "success"' in prerequisite["run"]


def checkout_step(job):
    return next(step for step in job["steps"] if step.get("uses", "").startswith("actions/checkout@"))


def named_step(job, name):
    return next(step for step in job["steps"] if step.get("name") == name)
