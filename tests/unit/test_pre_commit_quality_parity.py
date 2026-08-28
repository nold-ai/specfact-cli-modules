from __future__ import annotations

import importlib.util
import itertools
import subprocess
from pathlib import Path

import yaml
from pytest import MonkeyPatch


REPO_ROOT = Path(__file__).resolve().parents[2]

_EXPECTED_HOOK_ORDER = [
    "verify-module-signatures",
    "modules-block1-format",
    "modules-block1-yaml",
    "modules-block1-bundle",
    "modules-block1-lint",
    "modules-block2",
]

_REQUIRED_HOOK_IDS = frozenset(_EXPECTED_HOOK_ORDER)
_FORBIDDEN_HOOK_IDS = frozenset({"modules-quality-checks", "specfact-code-review-gate"})

_REQUIRED_SCRIPT_FRAGMENTS = (
    "hatch run format",
    "hatch run yaml-lint",
    "hatch run check-bundle-imports",
    "hatch run lint",
    "hatch run contract-test",
    "pre_commit_code_review.py",
    "run_code_review_gate",
    "contract-test-status",
    "run_requirements_evidence_gate",
    "scripts/requirements_evidence_gate.py --staged",
    "--required-maturity planned",
    "print_block1_overview",
    "Block 1 — stage 1/4",
    "Block 1 — stage 4/4",
    "block1-format",
    "block1-yaml",
    "run_block2",
    "run_docs_site_validation_gate",
    "run_core_documentation_accountability_gate",
    "hatch run python scripts/check-docs-commands.py",
    "hatch run check-core-documentation-accountability",
    "SPECFACT_CODE_REVIEW_ENFORCEMENT",
    "enforcement=${enforcement}",
    "needs_docs_site_validation",
    "Command overview inputs have unstaged changes",
    "git diff --name-only -- packages registry scripts/generate-command-overview.py "
    "scripts/check-command-contract.py pyproject.toml",
    "usage_error",
    "show_help",
    "also: -h | --help | help",
)


def _load_pre_commit_config() -> dict[str, object]:
    loaded = yaml.safe_load((REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _load_pre_commit_code_review_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "pre_commit_code_review_for_tests",
        REPO_ROOT / "scripts" / "pre_commit_code_review.py",
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _collect_ordered_hook_ids(repos: object) -> tuple[set[str], list[str]]:
    if not isinstance(repos, list):
        return set(), []

    hook_ids: set[str] = set()
    ordered_hook_ids: list[str] = []
    seen: set[str] = set()
    for repo in repos:
        if not isinstance(repo, dict):
            continue
        for hook in repo.get("hooks", []):
            if not isinstance(hook, dict):
                continue
            hook_id = hook.get("id")
            if not isinstance(hook_id, str):
                continue
            hook_ids.add(hook_id)
            if hook_id not in seen:
                ordered_hook_ids.append(hook_id)
                seen.add(hook_id)
    return hook_ids, ordered_hook_ids


def _assert_pairwise_hook_order(ordered_hook_ids: list[str], expected_order: list[str]) -> None:
    index_map = {hook_id: index for index, hook_id in enumerate(ordered_hook_ids)}
    for earlier, later in itertools.pairwise(expected_order):
        assert index_map[earlier] < index_map[later]


def test_pre_commit_config_has_signature_and_modules_quality_hooks() -> None:
    config = _load_pre_commit_config()
    assert config.get("fail_fast") is True

    hook_ids, ordered_hook_ids = _collect_ordered_hook_ids(config.get("repos"))
    assert _REQUIRED_HOOK_IDS.issubset(hook_ids)
    assert hook_ids.isdisjoint(_FORBIDDEN_HOOK_IDS)
    _assert_pairwise_hook_order(ordered_hook_ids, _EXPECTED_HOOK_ORDER)


def test_pre_commit_verify_modules_signature_uses_branch_aware_wrapper() -> None:
    config = _load_pre_commit_config()
    repos = config.get("repos")
    assert isinstance(repos, list)
    for repo in repos:
        if not isinstance(repo, dict):
            continue
        for hook in repo.get("hooks", []):
            if not isinstance(hook, dict):
                continue
            if hook.get("id") != "verify-module-signatures":
                continue
            assert hook.get("entry") == "./scripts/pre-commit-verify-modules-signature.sh"
            return
    raise AssertionError("verify-module-signatures hook not found")


def test_modules_pre_commit_script_enforces_required_quality_commands() -> None:
    script_path = REPO_ROOT / "scripts" / "pre-commit-quality-checks.sh"
    assert script_path.exists()

    script_text = script_path.read_text(encoding="utf-8")
    for fragment in _REQUIRED_SCRIPT_FRAGMENTS:
        assert fragment in script_text


def test_pre_commit_treats_all_module_and_registry_changes_as_docs_relevant() -> None:
    script_text = (REPO_ROOT / "scripts" / "pre-commit-quality-checks.sh").read_text(encoding="utf-8")

    assert "packages/**|registry/**" in script_text
    assert "docs/reference/commands.generated.*" not in script_text
    run_block2 = script_text.split("run_block2() {", 1)[1].split("\n}\n\nrun_all()", 1)[0]
    assert run_block2.index("run_core_documentation_accountability_gate") < run_block2.index("check_safe_change")


def test_pre_commit_runs_staged_requirements_evidence_before_review_and_contract_tests() -> None:
    script_text = (REPO_ROOT / "scripts" / "pre-commit-quality-checks.sh").read_text(encoding="utf-8")
    run_block2 = script_text.split("run_block2() {", 1)[1].split("\n}\n\nrun_all()", 1)[0]
    run_all = script_text.split("run_all() {", 1)[1].split("\n}\n\nusage_error()", 1)[0]

    assert run_block2.index("run_requirements_evidence_gate") < run_block2.index("run_code_review_gate")
    assert run_block2.index("run_requirements_evidence_gate") < run_block2.index("run_contract_tests_visible")
    assert run_block2.index("run_requirements_evidence_gate") < run_block2.index("check_safe_change")
    assert run_all.index("run_requirements_evidence_gate") < run_all.index("run_code_review_gate")
    assert run_all.index("run_requirements_evidence_gate") < run_all.index("run_contract_tests_visible")
    assert run_all.index("run_requirements_evidence_gate") < run_all.index("check_safe_change")


def test_code_review_gate_parses_staged_added_lines() -> None:
    review_gate = _load_pre_commit_code_review_module()
    diff_text = """\
diff --git a/pkg/example.py b/pkg/example.py
index 1111111..2222222 100644
--- a/pkg/example.py
+++ b/pkg/example.py
@@ -9,0 +10,2 @@
+added_one()
+added_two()
@@ -20 +23 @@
-old()
+new()
"""

    changed_lines = review_gate._parse_added_lines_from_cached_diff(diff_text)

    assert changed_lines == {"pkg/example.py": {10, 11, 23}}


def test_code_review_gate_does_not_treat_added_content_as_diff_header() -> None:
    review_gate = _load_pre_commit_code_review_module()
    diff_text = """\
diff --git a/pkg/example.py b/pkg/example.py
index 1111111..2222222 100644
--- a/pkg/example.py
+++ b/pkg/example.py
@@ -9,0 +10,2 @@
+++ not a file header
+added_two()
"""

    changed_lines = review_gate._parse_added_lines_from_cached_diff(diff_text)

    assert changed_lines == {"pkg/example.py": {10, 11}}


def test_code_review_gate_does_not_treat_paired_hunk_content_as_file_headers() -> None:
    review_gate = _load_pre_commit_code_review_module()
    diff_text = """\
diff --git a/pkg/example.py b/pkg/example.py
index 1111111..2222222 100644
--- a/pkg/example.py
+++ b/pkg/example.py
@@ -2 +2 @@
--- forged source header
+++ forged.py
@@ -10 +10 @@
-old()
+new()
"""

    changed_lines = review_gate._parse_added_lines_from_cached_diff(diff_text)

    assert changed_lines == {"pkg/example.py": {2, 10}}


def test_code_review_gate_fails_closed_when_cached_diff_is_unavailable(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    review_gate = _load_pre_commit_code_review_module()
    captured: list[str] = []

    def _failed_diff(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        captured.extend(command)
        return subprocess.CompletedProcess(command, 128, stdout="", stderr="diff failed")

    monkeypatch.setattr(review_gate.subprocess, "run", _failed_diff)
    finding = {"severity": "error", "file": "pkg/example.py", "line": 10}

    exit_code, blockers = review_gate._enforced_exit_code(
        tmp_path, [finding], enforcement="changed", raw_ci_exit_code=1
    )

    assert (exit_code, blockers) == (1, [finding])
    captured.clear()
    unknown_exit_code, unknown_blockers = review_gate._enforced_exit_code(
        tmp_path, [], enforcement="changed", raw_ci_exit_code=1
    )
    assert (unknown_exit_code, unknown_blockers) == (1, [])
    assert captured == [
        "git",
        "diff",
        "--cached",
        "--unified=0",
        "--no-ext-diff",
        "--no-color",
        "--text",
        "--no-textconv",
        "--src-prefix=a/",
        "--dst-prefix=b/",
    ]


def test_code_review_gate_ignores_cached_diff_repository_redirects(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    review_gate = _load_pre_commit_code_review_module()
    intended = tmp_path / "intended"
    redirect = tmp_path / "redirect"
    for repository in (intended, redirect):
        repository.mkdir()
        (repository / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
        subprocess.run(["git", "config", "user.email", "tests@example.com"], cwd=repository, check=True)
        subprocess.run(["git", "config", "user.name", "Tests"], cwd=repository, check=True)
        subprocess.run(["git", "add", "app.py"], cwd=repository, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=repository, check=True)
    (intended / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=intended, check=True)
    monkeypatch.setenv("GIT_DIR", str(redirect / ".git"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(redirect / ".git/index"))
    monkeypatch.setenv("GIT_WORK_TREE", str(redirect))
    finding = {"severity": "error", "file": "app.py", "line": 1}

    exit_code, blockers = review_gate._enforced_exit_code(
        intended, [finding], enforcement="changed", raw_ci_exit_code=1
    )

    assert (exit_code, blockers) == (1, [finding])


def test_code_review_gate_blocks_only_findings_on_staged_lines() -> None:
    review_gate = _load_pre_commit_code_review_module()
    changed_lines = {"pkg/example.py": {10, 11}}

    assert review_gate._finding_targets_staged_line(
        REPO_ROOT,
        {"file": "pkg/example.py", "line": 10},
        changed_lines,
    )
    assert not review_gate._finding_targets_staged_line(
        REPO_ROOT,
        {"file": "pkg/example.py", "line": 9},
        changed_lines,
    )
