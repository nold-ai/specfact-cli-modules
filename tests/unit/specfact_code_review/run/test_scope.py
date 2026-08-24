"""C14 red tests for immutable review-scope and target-policy resolution."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


_GIT_LOCAL_ENV_VARS = frozenset(
    {
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
        "GIT_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_PREFIX",
        "GIT_WORK_TREE",
    }
)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env={
            **{key: value for key, value in os.environ.items() if key not in _GIT_LOCAL_ENV_VARS},
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
        },
    )
    return result.stdout.strip()


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "C14 Tests")
    _git(repo, "config", "user.email", "c14@example.invalid")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "core.autocrlf", "false")
    _git(repo, "config", "core.symlinks", "true")
    (repo / "src").mkdir()
    (repo / "src/app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / "tests").mkdir()
    (repo / "tests/test_app.py").write_text("def test_value():\n    assert True\n", encoding="utf-8")
    _commit(repo, "base")
    return repo


@pytest.fixture
def scope_api() -> Any:
    from specfact_code_review.run import scope

    return scope


def _range_request(scope_api: Any, repo: Path, base_ref: str, head_ref: str, **updates: Any) -> Any:
    values = {
        "repository": repo,
        "scope": "range",
        "base_ref": base_ref,
        "head_ref": head_ref,
    }
    values.update(updates)
    return scope_api.ScopeRequest(**values)


def _make_range(git_repo: Path, *, path: str = "src/app.py", content: str = "VALUE = 2\n") -> tuple[str, str]:
    base = _git(git_repo, "rev-parse", "HEAD")
    target = git_repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    head = _commit(git_repo, "head")
    return base, head


def test_range_scope_includes_committed_files_on_clean_checkout(scope_api: Any, git_repo: Path) -> None:
    base, head = _make_range(git_repo)

    result = scope_api.resolve_scope(_range_request(scope_api, git_repo, base, head))

    assert result.status == "PASS"
    assert result.selected_paths == ("src/app.py",)
    assert _git(git_repo, "status", "--porcelain") == ""


def test_range_scope_uses_merge_base_not_head_worktree(scope_api: Any, git_repo: Path) -> None:
    base, head = _make_range(git_repo)
    (git_repo / "src/app.py").write_text("VALUE = 999\n", encoding="utf-8")

    result = scope_api.resolve_scope(_range_request(scope_api, git_repo, base, head))

    assert result.head_snapshot.read_bytes("src/app.py") == b"VALUE = 2\n"
    assert result.head_snapshot.content_digest("src/app.py") != scope_api.sha256_bytes(b"VALUE = 999\n")


def test_range_multiple_best_merge_bases_is_unknown(scope_api: Any, git_repo: Path, monkeypatch: Any) -> None:
    base, head = _make_range(git_repo)
    candidates = ("1" * 40, "2" * 40)
    monkeypatch.setattr(scope_api, "_best_merge_bases", lambda *_args, **_kwargs: candidates)

    result = scope_api.resolve_scope(_range_request(scope_api, git_repo, base, head))

    assert result.status == "UNKNOWN"
    assert result.reason == "ambiguous_merge_base"
    assert result.merge_base_candidates == tuple(sorted(candidates))
    assert result.merge_base_candidate_digest.startswith("sha256:")
    assert result.materialized is False


def test_scope_git_failure_is_unknown_and_blocks_enforcement(scope_api: Any, git_repo: Path, monkeypatch: Any) -> None:
    base, head = _make_range(git_repo)

    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise scope_api.GitResolutionError("simulated failure")

    monkeypatch.setattr(scope_api, "_resolve_commit", fail)
    result = scope_api.resolve_scope(_range_request(scope_api, git_repo, base, head))

    assert result.status == "UNKNOWN"
    assert result.ci_exit_code == 1
    assert "simulated failure" in result.diagnostics


def test_scope_git_subprocesses_ignore_inherited_repository_local_environment(
    scope_api: Any, git_repo: Path, tmp_path: Path, monkeypatch: Any
) -> None:
    base, head = _make_range(git_repo)
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "poison.git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "poison-worktree"))

    result = scope_api.resolve_scope(_range_request(scope_api, git_repo, base, head))

    assert result.status == "PASS"
    assert result.selected_paths == ("src/app.py",)


def test_range_policy_failure_removes_materialized_temporary_roots(
    scope_api: Any, git_repo: Path, tmp_path: Path, monkeypatch: Any
) -> None:
    base, head = _make_range(git_repo)
    created: list[Path] = []

    def tracked_mkdtemp(*, prefix: str) -> str:
        root = tmp_path / f"{prefix}{len(created)}"
        root.mkdir()
        created.append(root)
        return str(root)

    def fail_policy(*_args: Any, **_kwargs: Any) -> Any:
        raise scope_api.PolicyResolutionError("simulated policy failure")

    monkeypatch.setattr(scope_api.tempfile, "mkdtemp", tracked_mkdtemp)
    monkeypatch.setattr(scope_api, "_build_policy_bundle", fail_policy)

    result = scope_api.resolve_scope(_range_request(scope_api, git_repo, base, head))

    assert result.status == "UNKNOWN"
    assert result.reason == "policy_parse_failure"
    assert created
    assert all(not root.exists() for root in created)


def test_git_text_output_uses_reversible_surrogateescape(scope_api: Any, git_repo: Path, monkeypatch: Any) -> None:
    observed: dict[str, object] = {}

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed.update(kwargs)
        return subprocess.CompletedProcess(command, 0, "src/\udcff.py\0", "")

    monkeypatch.setattr(scope_api.subprocess, "run", run)

    result = scope_api._git(git_repo, ["ls-tree", "-z", "HEAD"])

    assert result.stdout == "src/\udcff.py\0"
    assert observed["encoding"] == "utf-8"
    assert observed["errors"] == "surrogateescape"


def test_empty_resolved_range_is_not_applicable(scope_api: Any, git_repo: Path) -> None:
    base, head = _make_range(git_repo, path="README.md", content="documentation only\n")

    result = scope_api.resolve_scope(_range_request(scope_api, git_repo, base, head))

    assert result.status == "NOT_APPLICABLE"
    assert result.selected_paths == ()
    assert result.reason == "no_governed_impact"


def test_range_scope_includes_changed_tests_by_default(scope_api: Any, git_repo: Path) -> None:
    base, head = _make_range(git_repo, path="tests/test_app.py", content="def test_value():\n    assert False\n")

    result = scope_api.resolve_scope(_range_request(scope_api, git_repo, base, head))

    assert result.status == "PASS"
    assert result.selected_paths == ("tests/test_app.py",)


def test_pr_assurance_rejects_positional_file_downgrade(scope_api: Any, git_repo: Path) -> None:
    result = scope_api.resolve_scope(
        scope_api.ScopeRequest(repository=git_repo, scope="explicit_files", files=(Path("src/app.py"),))
    )

    assert result.assurance_kind == "explicit_files"
    assert scope_api.verify_pr_assurance(result, envelope=None).status == "UNKNOWN"
    assert scope_api.local_enforcement_allowed(result) is True


def test_range_analysis_uses_materialized_commit_snapshots(scope_api: Any, git_repo: Path) -> None:
    base, head = _make_range(git_repo)
    result = scope_api.resolve_scope(_range_request(scope_api, git_repo, base, head))
    before = result.head_snapshot.content_digest("src/app.py")
    (git_repo / "src/app.py").write_text("VALUE = 3\n", encoding="utf-8")

    assert result.head_snapshot.content_digest("src/app.py") == before
    assert result.head_snapshot.root != git_repo


def test_range_rejects_symlinked_governed_python_input(scope_api: Any, git_repo: Path) -> None:
    base = _git(git_repo, "rev-parse", "HEAD")
    (git_repo / "src/app.py").unlink()
    (git_repo / "src/app.py").symlink_to("../README.md")
    head = _commit(git_repo, "symlink")

    result = scope_api.resolve_scope(_range_request(scope_api, git_repo, base, head))

    assert result.status == "UNKNOWN"
    assert result.reason == "unsafe_governed_input"
    assert result.input_manifest["src/app.py"].git_mode == "120000"


def test_range_mode_change_regular_to_symlink_is_unknown(scope_api: Any, git_repo: Path) -> None:
    base = _git(git_repo, "rev-parse", "HEAD")
    (git_repo / "src/app.py").unlink()
    (git_repo / "src/app.py").symlink_to("../README.md")
    head = _commit(git_repo, "mode change")

    result = scope_api.resolve_scope(_range_request(scope_api, git_repo, base, head))

    assert result.status == "UNKNOWN"
    assert (result.base_input_manifest["src/app.py"].git_mode, result.input_manifest["src/app.py"].git_mode) == (
        "100644",
        "120000",
    )


def test_index_rejects_symlinked_governed_input(scope_api: Any, git_repo: Path) -> None:
    (git_repo / "src/app.py").unlink()
    (git_repo / "src/app.py").symlink_to("../README.md")
    _git(git_repo, "add", "src/app.py")

    result = scope_api.resolve_scope(scope_api.ScopeRequest(repository=git_repo, scope="index"))

    assert result.status == "UNKNOWN"
    assert result.reason == "unsafe_governed_input"


def test_materialized_governed_input_uses_nofollow_regular_blob_identity(scope_api: Any, git_repo: Path) -> None:
    base, head = _make_range(git_repo)
    result = scope_api.resolve_scope(_range_request(scope_api, git_repo, base, head))
    identity = result.input_manifest["src/app.py"]

    assert identity.object_type == "blob"
    assert identity.git_mode in {"100644", "100755"}
    assert identity.open_policy == "descriptor-relative-nofollow"
    assert identity.content_digest == result.head_snapshot.content_digest("src/app.py")


@pytest.mark.parametrize("scope_name", ["index", "range"])
@pytest.mark.parametrize("option", ["fix", "preview_fixes", "with_mutation"])
def test_index_and_range_reject_fix_preview_and_mutation_options(
    scope_api: Any, git_repo: Path, scope_name: str, option: str
) -> None:
    base, head = _make_range(git_repo)
    kwargs: dict[str, Any] = {option: True}
    request = (
        _range_request(scope_api, git_repo, base, head, **kwargs)
        if scope_name == "range"
        else scope_api.ScopeRequest(repository=git_repo, scope="index", **kwargs)
    )

    with pytest.raises(scope_api.InvalidScopeOption, match=option):
        scope_api.resolve_scope(request)


def test_index_scope_reads_staged_blobs_not_unstaged_worktree(scope_api: Any, git_repo: Path) -> None:
    (git_repo / "src/app.py").write_text("VALUE = 2\n", encoding="utf-8")
    _git(git_repo, "add", "src/app.py")
    (git_repo / "src/app.py").write_text("VALUE = 3\n", encoding="utf-8")

    result = scope_api.resolve_scope(scope_api.ScopeRequest(repository=git_repo, scope="index"))

    assert result.head_snapshot.read_bytes("src/app.py") == b"VALUE = 2\n"


def test_index_scope_removes_captured_index_root_after_materialization(
    scope_api: Any, git_repo: Path, monkeypatch: Any
) -> None:
    real_mkdtemp = scope_api.tempfile.mkdtemp
    capture_roots: list[Path] = []

    def tracked_mkdtemp(*args: Any, **kwargs: Any) -> str:
        root = Path(real_mkdtemp(*args, **kwargs))
        if kwargs.get("prefix") == "specfact-index-":
            capture_roots.append(root)
        return str(root)

    monkeypatch.setattr(scope_api.tempfile, "mkdtemp", tracked_mkdtemp)
    (git_repo / "src/app.py").write_text("VALUE = 2\n", encoding="utf-8")
    _git(git_repo, "add", "src/app.py")

    result = scope_api.resolve_scope(scope_api.ScopeRequest(repository=git_repo, scope="index"))
    try:
        assert capture_roots
        assert all(not root.exists() for root in capture_roots)
    finally:
        scope_api.cleanup_scope_resolution(result)


def test_index_scope_imports_dependency_from_complete_index_tree(scope_api: Any, git_repo: Path) -> None:
    (git_repo / "src/dependency.py").write_text("TOKEN = 'committed'\n", encoding="utf-8")
    _commit(git_repo, "dependency")
    (git_repo / "src/app.py").write_text("from .dependency import TOKEN\nVALUE = TOKEN\n", encoding="utf-8")
    _git(git_repo, "add", "src/app.py")
    (git_repo / "src/dependency.py").write_text("TOKEN = 'unstaged'\n", encoding="utf-8")

    result = scope_api.resolve_scope(scope_api.ScopeRequest(repository=git_repo, scope="index"))

    assert result.head_snapshot.read_bytes("src/dependency.py") == b"TOKEN = 'committed'\n"


def test_index_scope_derives_selection_from_captured_tree_during_concurrent_index_mutation(
    scope_api: Any, git_repo: Path, monkeypatch: Any
) -> None:
    (git_repo / "src/app.py").write_text("VALUE = 2\n", encoding="utf-8")
    _git(git_repo, "add", "src/app.py")

    def mutate_after_capture() -> None:
        (git_repo / "src/app.py").write_text("VALUE = 4\n", encoding="utf-8")
        _git(git_repo, "add", "src/app.py")

    monkeypatch.setattr(scope_api, "_after_index_capture", mutate_after_capture)
    result = scope_api.resolve_scope(scope_api.ScopeRequest(repository=git_repo, scope="index"))

    assert result.head_snapshot.read_bytes("src/app.py") == b"VALUE = 2\n"
    assert result.index_tree == result.selection_tree


def test_index_intent_to_add_survives_captured_tree_omission(scope_api: Any, git_repo: Path) -> None:
    (git_repo / "src/new.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(git_repo, "add", "-N", "src/new.py")

    result = scope_api.resolve_scope(scope_api.ScopeRequest(repository=git_repo, scope="index"))

    assert result.status == "UNKNOWN"
    assert result.reason == "unsafe_governed_input"
    assert result.index_metadata["src/new.py"].intent_to_add is True


def test_range_scope_omitted_enforcement_defaults_to_full(scope_api: Any, git_repo: Path) -> None:
    base, head = _make_range(git_repo)

    normalized = scope_api.normalize_scope_request(_range_request(scope_api, git_repo, base, head))

    assert normalized.enforcement == "full"


def test_range_scope_allows_shadow_enforcement(scope_api: Any, git_repo: Path) -> None:
    base, head = _make_range(git_repo)

    result = scope_api.resolve_scope(_range_request(scope_api, git_repo, base, head, enforcement="shadow"))

    assert result.status == "PASS"


@pytest.mark.parametrize(
    "narrowing",
    [
        {"exclude_tests": True},
        {"focus": ("source",)},
        {"focus": ("tests",)},
        {"focus": ("docs",)},
        {"focus": ("simplify",)},
        {"path_filters": (Path("src"),)},
        {"no_tests": True},
        {"level": "error"},
    ],
)
def test_range_scope_rejects_narrowing_filters_before_analysis(
    scope_api: Any, git_repo: Path, narrowing: dict[str, Any]
) -> None:
    base, head = _make_range(git_repo)

    with pytest.raises(scope_api.InvalidScopeOption):
        scope_api.resolve_scope(_range_request(scope_api, git_repo, base, head, **narrowing))


def _write_context(
    path: Path,
    *,
    repository: str,
    base: str,
    head: str,
    target_tree: str,
    head_tree: str,
) -> None:
    path.write_text(
        json.dumps(
            {
                "schema": "github-actions-pr-v1",
                "provider": "github-actions",
                "repository": repository,
                "event": "pull_request",
                "pull_request": 416,
                "target_ref": "refs/heads/dev",
                "target_commit": base,
                "target_tree": target_tree,
                "head_ref": "refs/heads/feature/code-review-14-delivery",
                "head_commit": head,
                "head_tree": head_tree,
            }
        ),
        encoding="utf-8",
    )


def test_range_candidate_rejects_base_ref_mismatching_claimed_target_tip(
    scope_api: Any, git_repo: Path, tmp_path: Path
) -> None:
    base, head = _make_range(git_repo)
    context = tmp_path / "context.json"
    _write_context(
        context,
        repository="example/repo",
        base="f" * 40,
        head=head,
        target_tree="f" * 40,
        head_tree=_git(git_repo, "rev-parse", f"{head}^{{tree}}"),
    )

    result = scope_api.resolve_scope(
        _range_request(scope_api, git_repo, base, head, pr_context_file=context, repository_slug="example/repo")
    )

    assert result.status == "UNKNOWN"
    assert result.reason == "pr_context_identity_mismatch"


def test_producer_never_self_asserts_pr_range_from_context_file(scope_api: Any, git_repo: Path, tmp_path: Path) -> None:
    base, head = _make_range(git_repo)
    context = tmp_path / "context.json"
    _write_context(
        context,
        repository="example/repo",
        base=base,
        head=head,
        target_tree=_git(git_repo, "rev-parse", f"{base}^{{tree}}"),
        head_tree=_git(git_repo, "rev-parse", f"{head}^{{tree}}"),
    )

    result = scope_api.resolve_scope(
        _range_request(scope_api, git_repo, base, head, pr_context_file=context, repository_slug="example/repo")
    )

    assert result.status == "PASS"
    assert result.assurance_kind == "range_candidate"
    assert result.effective_assurance_kind != "pr_range"
    assert result.context_digest.startswith("sha256:")


def test_range_without_context_is_preview(scope_api: Any, git_repo: Path) -> None:
    base, head = _make_range(git_repo)

    result = scope_api.resolve_scope(_range_request(scope_api, git_repo, base, head))

    assert result.assurance_kind == "range_preview"
    assert result.effective_assurance_kind == "range_preview"


def test_policy_only_range_is_unknown_not_not_applicable(scope_api: Any, git_repo: Path) -> None:
    base, head = _make_range(git_repo, path="ruff.toml", content="line-length = 80\n")

    result = scope_api.resolve_scope(_range_request(scope_api, git_repo, base, head))

    assert result.status == "UNKNOWN"
    assert result.reason == "candidate_policy_change"
    assert result.policy_manifest_digest.startswith("sha256:")


def test_candidate_policy_change_cannot_self_authorize_pr_range(scope_api: Any, git_repo: Path) -> None:
    base, head = _make_range(git_repo, path="pyproject.toml", content="[tool.ruff]\nline-length = 80\n")

    result = scope_api.resolve_scope(_range_request(scope_api, git_repo, base, head))

    assert result.status == "UNKNOWN"
    assert result.effective_assurance_kind != "pr_range"


def test_pyproject_nonpolicy_change_can_remain_non_governed(scope_api: Any, git_repo: Path) -> None:
    base, head = _make_range(git_repo, path="pyproject.toml", content="[project]\nname = 'example'\n")

    result = scope_api.resolve_scope(_range_request(scope_api, git_repo, base, head))

    assert result.status == "NOT_APPLICABLE"


def test_coverage_config_only_range_is_governed_unknown(scope_api: Any, git_repo: Path) -> None:
    base, head = _make_range(git_repo, path=".coveragerc.toml", content="[run]\nbranch = true\n")

    result = scope_api.resolve_scope(_range_request(scope_api, git_repo, base, head))

    assert result.status == "UNKNOWN"
    assert ".coveragerc.toml" in result.policy_paths


@pytest.mark.parametrize(
    ("files", "selected"),
    [
        ({"pytest.toml": "", "pytest.ini": "[pytest]\n"}, "pytest.toml"),
        ({".pytest.toml": "", "tox.ini": "[pytest]\n"}, ".pytest.toml"),
        ({"pytest.ini": "", "setup.cfg": "[tool:pytest]\n"}, "pytest.ini"),
        ({".pytest.ini": "", "pyproject.toml": "[tool.pytest.ini_options]\n"}, ".pytest.ini"),
        ({"pyproject.toml": "[tool.pytest.ini_options]\n"}, "pyproject.toml"),
        ({"tox.ini": "[pytest]\n"}, "tox.ini"),
        ({"setup.cfg": "[tool:pytest]\n"}, "setup.cfg"),
    ],
)
def test_pytest_supported_config_sources_follow_pinned_precedence(
    scope_api: Any, tmp_path: Path, files: dict[str, str], selected: str
) -> None:
    for relative, content in files.items():
        (tmp_path / relative).write_text(content, encoding="utf-8")

    policy = scope_api.resolve_pytest_policy(tmp_path, expected_version="9.0.3")

    assert policy.selected_path == selected
    assert policy.loader_version == "9.0.3"


def test_pytest_empty_toml_overrides_lower_precedence_config(scope_api: Any, tmp_path: Path) -> None:
    (tmp_path / "pytest.toml").write_bytes(b"")
    (tmp_path / "pytest.ini").write_text("[pytest]\naddopts=-q\n", encoding="utf-8")

    policy = scope_api.resolve_pytest_policy(tmp_path, expected_version="9.0.3")

    assert policy.selected_path == "pytest.toml"
    assert "pytest.ini" in policy.ignored_paths


def test_pytest_empty_ini_overrides_lower_precedence_config(scope_api: Any, tmp_path: Path) -> None:
    (tmp_path / "pytest.ini").write_bytes(b"")
    (tmp_path / "setup.cfg").write_text("[tool:pytest]\naddopts=-q\n", encoding="utf-8")

    policy = scope_api.resolve_pytest_policy(tmp_path, expected_version="9.0.3")

    assert policy.selected_path == "pytest.ini"
    assert "setup.cfg" in policy.ignored_paths


def test_pytest_bare_pyproject_is_final_fallback(scope_api: Any, tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")

    policy = scope_api.resolve_pytest_policy(tmp_path, expected_version="9.0.3")

    assert policy.selected_path == "pyproject.toml"
    assert policy.selection_reason == "bare_pyproject_fallback"


@pytest.mark.parametrize("selected", [".coveragerc", ".coveragerc.toml", "setup.cfg", "tox.ini", "pyproject.toml"])
def test_coverage_supported_config_sources_follow_pinned_precedence(
    scope_api: Any, tmp_path: Path, selected: str
) -> None:
    content = "[run]\nbranch = true\n" if selected.startswith(".coverage") else "[coverage:run]\nbranch = true\n"
    if selected == "pyproject.toml":
        content = "[tool.coverage.run]\nbranch = true\n"
    (tmp_path / selected).write_text(content, encoding="utf-8")

    policy = scope_api.resolve_coverage_policy(tmp_path, expected_version="7.15.4")

    assert policy.selected_path == selected
    assert policy.loader_version == "7.15.4"


@pytest.mark.parametrize("source_name", ["pylintrc", ".pylintrc", "pyproject.toml", "setup.cfg", "tox.ini"])
def test_pylint_supported_config_sources_are_governed_and_explicit(
    scope_api: Any, tmp_path: Path, source_name: str
) -> None:
    content = "[pylint.main]\n" if source_name in {"setup.cfg", "tox.ini"} else "[MAIN]\n"
    (tmp_path / source_name).write_text(content, encoding="utf-8")

    policy = scope_api.resolve_pylint_policy(tmp_path, expected_version="4.0.7")

    assert policy.selected_path == source_name
    assert policy.projection["confidence"] == "HIGH,CONTROL_FLOW,INFERENCE,INFERENCE_FAILURE,UNDEFINED"
    assert policy.projection["errors-only"] is False


@pytest.mark.parametrize("option", ["init-hook", "load-plugins"])
def test_pylint_repository_plugin_or_init_hook_is_unknown(scope_api: Any, tmp_path: Path, option: str) -> None:
    (tmp_path / "pylintrc").write_text(f"[MAIN]\n{option}=candidate_plugin\n", encoding="utf-8")

    policy = scope_api.resolve_pylint_policy(tmp_path, expected_version="4.0.7")

    assert policy.status == "UNKNOWN"
    assert policy.reason == "pylint_extension_unsupported"


def test_pylint_extension_package_option_is_unknown_before_no_impact(scope_api: Any, tmp_path: Path) -> None:
    (tmp_path / "pylintrc").write_text("[MAIN]\nextension-pkg-allow-list=native_candidate\n", encoding="utf-8")

    policy = scope_api.resolve_pylint_policy(tmp_path, expected_version="4.0.7")

    assert policy.status == "UNKNOWN"


@pytest.mark.parametrize(
    "option",
    [
        "ignore",
        "ignore-patterns",
        "ignore-paths",
        "ignored-modules",
        "ignored-classes",
        "generated-members",
        "signature-mutators",
    ],
)
def test_pylint_ignore_options_cannot_drop_governed_input(scope_api: Any, tmp_path: Path, option: str) -> None:
    (tmp_path / "pylintrc").write_text(f"[MAIN]\n{option}=src/app.py\n", encoding="utf-8")

    policy = scope_api.resolve_pylint_policy(tmp_path, expected_version="4.0.7")

    assert policy.projection[option] == "" or policy.projection[option] == []


def test_pylint_no_member_exemptions_cannot_hide_renamed_module(scope_api: Any, tmp_path: Path) -> None:
    (tmp_path / "pylintrc").write_text("[TYPECHECK]\nignore-none=yes\nignore-mixin-members=yes\n", encoding="utf-8")

    policy = scope_api.resolve_pylint_policy(tmp_path, expected_version="4.0.7")

    assert policy.projection["ignore-none"] is False
    assert policy.projection["ignore-mixin-members"] is False


def test_pylint_confidence_filter_cannot_hide_inference_diagnostic(scope_api: Any, tmp_path: Path) -> None:
    (tmp_path / "pylintrc").write_text("[MESSAGES CONTROL]\nconfidence=HIGH\n", encoding="utf-8")

    policy = scope_api.resolve_pylint_policy(tmp_path, expected_version="4.0.7")

    assert "INFERENCE" in policy.projection["confidence"]


def test_pylint_errors_only_cannot_hide_warning_diagnostic(scope_api: Any, tmp_path: Path) -> None:
    (tmp_path / "pylintrc").write_text("[MAIN]\nerrors-only=yes\n", encoding="utf-8")

    policy = scope_api.resolve_pylint_policy(tmp_path, expected_version="4.0.7")

    assert policy.projection["errors-only"] is False


def test_pylint_from_stdin_cannot_replace_governed_input(scope_api: Any, tmp_path: Path) -> None:
    (tmp_path / "pylintrc").write_text("[MAIN]\nfrom-stdin=alias.py\nrecursive=yes\n", encoding="utf-8")

    policy = scope_api.resolve_pylint_policy(tmp_path, expected_version="4.0.7")

    assert policy.projection["from-stdin"] is False
    assert policy.projection["recursive"] is False
    assert policy.stdin_policy == "closed"


@pytest.mark.parametrize("source_name", [None, ".ruff.toml", "ruff.toml", "pyproject.toml"])
def test_ruff_config_zero_or_one_source_is_explicit(scope_api: Any, tmp_path: Path, source_name: str | None) -> None:
    if source_name:
        content = "[tool.ruff]\nline-length=80\n" if source_name == "pyproject.toml" else "line-length=80\n"
        (tmp_path / source_name).write_text(content, encoding="utf-8")

    policy = scope_api.resolve_ruff_policy(tmp_path, expected_version="0.15.12")

    assert policy.status == "PASS"
    assert policy.selected_path == source_name
    assert policy.isolated is (source_name is None)


def test_ruff_config_multiple_sources_is_unknown(scope_api: Any, tmp_path: Path) -> None:
    (tmp_path / ".ruff.toml").write_text("line-length=80\n", encoding="utf-8")
    (tmp_path / "ruff.toml").write_text("line-length=81\n", encoding="utf-8")

    policy = scope_api.resolve_ruff_policy(tmp_path, expected_version="0.15.12")

    assert policy.status == "UNKNOWN"
    assert policy.reason == "ruff_config_ambiguous"


def test_ruff_transitive_extend_policy_is_governed_and_sealed(scope_api: Any, tmp_path: Path) -> None:
    (tmp_path / "ruff.toml").write_text("extend='config/base.toml'\n", encoding="utf-8")
    (tmp_path / "config").mkdir()
    (tmp_path / "config/base.toml").write_text("line-length=80\n", encoding="utf-8")

    policy = scope_api.resolve_ruff_policy(tmp_path, expected_version="0.15.12")

    assert policy.closure_paths == ("config/base.toml", "ruff.toml")
    assert policy.closure_digest.startswith("sha256:")


def test_range_change_to_transitive_ruff_config_is_governed(scope_api: Any, git_repo: Path) -> None:
    (git_repo / "ruff.toml").write_text("extend='config/base.toml'\n", encoding="utf-8")
    (git_repo / "config").mkdir()
    (git_repo / "config/base.toml").write_text("line-length=80\n", encoding="utf-8")
    base = _commit(git_repo, "add ruff policy graph")
    (git_repo / "config/base.toml").write_text("line-length=88\n", encoding="utf-8")
    head = _commit(git_repo, "change transitive ruff policy")

    result = scope_api.resolve_scope(_range_request(scope_api, git_repo, base, head))

    assert result.status == "UNKNOWN"
    assert result.reason == "candidate_policy_change"
    assert result.selected_paths == ("config/base.toml",)


@pytest.mark.parametrize(
    ("primary_path", "primary_content", "referenced_path", "initial_content", "updated_content"),
    [
        ("ruff.toml", "extend='config/base.toml'\n", "config/base.toml", "line-length=80\n", "line-length=88\n"),
        (
            "pyrightconfig.json",
            '{"extends":"config/base.json"}\n',
            "config/base.json",
            '{"typeCheckingMode":"basic"}\n',
            '{"typeCheckingMode":"strict"}\n',
        ),
    ],
    ids=["ruff-extend", "basedpyright-reference"],
)
def test_index_change_to_transitive_policy_file_is_governed(
    scope_api: Any,
    git_repo: Path,
    primary_path: str,
    primary_content: str,
    referenced_path: str,
    initial_content: str,
    updated_content: str,
) -> None:
    primary = git_repo / primary_path
    referenced = git_repo / referenced_path
    referenced.parent.mkdir(parents=True, exist_ok=True)
    primary.write_text(primary_content, encoding="utf-8")
    referenced.write_text(initial_content, encoding="utf-8")
    _commit(git_repo, "add analyzer policy graph")
    referenced.write_text(updated_content, encoding="utf-8")
    _git(git_repo, "add", referenced_path)

    result = scope_api.resolve_scope(scope_api.ScopeRequest(repository=git_repo, scope="index"))

    assert result.status == "PASS"
    assert result.selected_paths == (referenced_path,)


@pytest.mark.parametrize(
    ("primary_path", "primary_content", "reference_path", "unsafe_path", "stage_graph_together"),
    [
        ("ruff.toml", "line-length=80\n", None, "ruff.toml", False),
        ("ruff.toml", "extend='config/base.toml'\n", "config/base.toml", "config/base.toml", False),
        ("ruff.toml", "extend='config/base.toml'\n", "config/base.toml", "config/base.toml", True),
        ("pyrightconfig.json", '{"typeCheckingMode":"basic"}\n', None, "pyrightconfig.json", False),
        (
            "pyrightconfig.json",
            '{"extends":"config/base.json"}\n',
            "config/base.json",
            "config/base.json",
            False,
        ),
        (
            "pyrightconfig.json",
            '{"extends":"config/base.json"}\n',
            "config/base.json",
            "config/base.json",
            True,
        ),
    ],
    ids=[
        "ruff-primary",
        "ruff-reference",
        "ruff-new-reference",
        "basedpyright-primary",
        "basedpyright-reference",
        "basedpyright-new-reference",
    ],
)
def test_index_unsafe_policy_entry_preserves_governed_evidence(
    scope_api: Any,
    git_repo: Path,
    primary_path: str,
    primary_content: str,
    reference_path: str | None,
    unsafe_path: str,
    stage_graph_together: bool,
) -> None:
    primary = git_repo / primary_path
    primary.write_text(primary_content, encoding="utf-8")
    if reference_path is not None:
        reference = git_repo / reference_path
        reference.parent.mkdir(parents=True, exist_ok=True)
        reference.write_text("line-length=80\n" if reference.suffix == ".toml" else "{}\n", encoding="utf-8")
    if not stage_graph_together:
        _commit(git_repo, "add analyzer policy graph")
    unsafe = git_repo / unsafe_path
    unsafe.unlink()
    unsafe.symlink_to("../README.md" if unsafe.parent != git_repo else "README.md")
    _git(git_repo, "add", primary_path, unsafe_path)

    result = scope_api.resolve_scope(scope_api.ScopeRequest(repository=git_repo, scope="index"))

    assert result.status == "UNKNOWN"
    assert result.reason == "unsafe_governed_input"
    expected_paths = {unsafe_path, primary_path} if stage_graph_together else {unsafe_path}
    assert set(result.selected_paths) == expected_paths
    assert result.index_tree
    assert result.index_metadata[unsafe_path].git_mode == "120000"
    assert result.input_manifest[unsafe_path].git_mode == "120000"
    assert unsafe_path in result.policy_paths


@pytest.mark.parametrize(
    ("primary_path", "initial_primary", "updated_primary", "reference_path", "reference_content"),
    [
        (
            "ruff.toml",
            "extend='config/base.toml'\n",
            "line-length=88\n",
            "config/base.toml",
            "line-length=80\n",
        ),
        (
            "pyrightconfig.json",
            '{"extends":"config/base.json"}\n',
            '{"typeCheckingMode":"strict"}\n',
            "config/base.json",
            "{}\n",
        ),
    ],
    ids=["ruff-deleted-reference", "basedpyright-deleted-reference"],
)
def test_index_deleted_policy_reference_preserves_governed_evidence(
    scope_api: Any,
    git_repo: Path,
    primary_path: str,
    initial_primary: str,
    updated_primary: str,
    reference_path: str,
    reference_content: str,
) -> None:
    primary = git_repo / primary_path
    reference = git_repo / reference_path
    reference.parent.mkdir(parents=True, exist_ok=True)
    primary.write_text(initial_primary, encoding="utf-8")
    reference.write_text(reference_content, encoding="utf-8")
    _commit(git_repo, "add analyzer policy graph")
    primary.write_text(updated_primary, encoding="utf-8")
    _git(git_repo, "add", primary_path)
    _git(git_repo, "rm", reference_path)

    result = scope_api.resolve_scope(scope_api.ScopeRequest(repository=git_repo, scope="index"))

    assert result.status == "UNKNOWN"
    assert result.reason == "unsafe_governed_input"
    assert set(result.selected_paths) == {primary_path, reference_path}
    assert result.index_tree
    assert result.base_input_manifest[reference_path].git_mode == "100644"
    assert reference_path not in result.input_manifest
    assert reference_path in result.policy_paths


@pytest.mark.parametrize(
    ("primary_path", "initial_primary", "updated_primary", "reference_path"),
    [
        (
            "ruff.toml",
            "line-length=80\n",
            "extend='config/unsafe.toml'\n",
            "config/unsafe.toml",
        ),
        (
            "pyrightconfig.json",
            '{"typeCheckingMode":"basic"}\n',
            '{"extends":"config/unsafe.json"}\n',
            "config/unsafe.json",
        ),
    ],
    ids=["ruff-newly-governed-symlink", "basedpyright-newly-governed-symlink"],
)
def test_index_unchanged_unsafe_reference_newly_governed_preserves_evidence(
    scope_api: Any,
    git_repo: Path,
    primary_path: str,
    initial_primary: str,
    updated_primary: str,
    reference_path: str,
) -> None:
    primary = git_repo / primary_path
    reference = git_repo / reference_path
    reference.parent.mkdir(parents=True, exist_ok=True)
    primary.write_text(initial_primary, encoding="utf-8")
    reference.symlink_to("../README.md")
    _commit(git_repo, "add dormant unsafe policy entry")
    primary.write_text(updated_primary, encoding="utf-8")
    _git(git_repo, "add", primary_path)

    result = scope_api.resolve_scope(scope_api.ScopeRequest(repository=git_repo, scope="index"))

    assert result.status == "UNKNOWN"
    assert result.reason == "unsafe_governed_input"
    assert set(result.selected_paths) == {primary_path, reference_path}
    assert result.index_tree
    assert result.index_metadata[reference_path].git_mode == "120000"
    assert result.input_manifest[reference_path].git_mode == "120000"
    assert reference_path in result.policy_paths


@pytest.mark.parametrize(
    "case",
    [
        {
            "valid_primary_path": "pyrightconfig.json",
            "valid_initial_primary": '{"extends":"config/base.json"}\n',
            "valid_updated_primary": '{"typeCheckingMode":"strict"}\n',
            "reference_path": "config/base.json",
            "reference_content": "{}\n",
            "invalid_primary_path": "ruff.toml",
            "invalid_initial_primary": "extend='missing.toml'\n",
            "invalid_updated_primary": "line-length=88\n",
        },
        {
            "valid_primary_path": "ruff.toml",
            "valid_initial_primary": "extend='config/base.toml'\n",
            "valid_updated_primary": "line-length=88\n",
            "reference_path": "config/base.toml",
            "reference_content": "line-length=80\n",
            "invalid_primary_path": "pyrightconfig.json",
            "invalid_initial_primary": '{"extends":"missing.json"}\n',
            "invalid_updated_primary": '{"typeCheckingMode":"strict"}\n',
        },
    ],
    ids=["valid-basedpyright-invalid-ruff", "valid-ruff-invalid-basedpyright"],
)
def test_index_valid_base_policy_closure_survives_other_invalid_policy(
    scope_api: Any,
    git_repo: Path,
    case: dict[str, str],
) -> None:
    valid_primary_path = case["valid_primary_path"]
    invalid_primary_path = case["invalid_primary_path"]
    reference_path = case["reference_path"]
    valid_primary = git_repo / valid_primary_path
    invalid_primary = git_repo / invalid_primary_path
    reference = git_repo / reference_path
    reference.parent.mkdir(parents=True, exist_ok=True)
    valid_primary.write_text(case["valid_initial_primary"], encoding="utf-8")
    invalid_primary.write_text(case["invalid_initial_primary"], encoding="utf-8")
    reference.write_text(case["reference_content"], encoding="utf-8")
    _commit(git_repo, "add mixed-validity analyzer policy graphs")
    valid_primary.write_text(case["valid_updated_primary"], encoding="utf-8")
    invalid_primary.write_text(case["invalid_updated_primary"], encoding="utf-8")
    _git(git_repo, "add", valid_primary_path, invalid_primary_path)
    _git(git_repo, "rm", reference_path)

    result = scope_api.resolve_scope(scope_api.ScopeRequest(repository=git_repo, scope="index"))

    assert result.status == "UNKNOWN"
    assert result.reason == "unsafe_governed_input"
    assert set(result.selected_paths) == {valid_primary_path, invalid_primary_path, reference_path}
    assert result.base_input_manifest[reference_path].git_mode == "100644"
    assert reference_path not in result.input_manifest
    assert reference_path in result.policy_paths


@pytest.mark.parametrize(
    ("primary_path", "initial_primary", "updated_primary", "missing_path"),
    [
        (
            "ruff.toml",
            "line-length=80\n",
            "extend='config/missing.toml'\n",
            "config/missing.toml",
        ),
        (
            "pyrightconfig.json",
            '{"typeCheckingMode":"basic"}\n',
            '{"extends":"config/missing.json"}\n',
            "config/missing.json",
        ),
    ],
    ids=["ruff-missing-reference", "basedpyright-missing-reference"],
)
def test_index_new_missing_policy_reference_preserves_governed_evidence(
    scope_api: Any,
    git_repo: Path,
    primary_path: str,
    initial_primary: str,
    updated_primary: str,
    missing_path: str,
) -> None:
    primary = git_repo / primary_path
    primary.write_text(initial_primary, encoding="utf-8")
    _commit(git_repo, "add analyzer primary policy")
    primary.write_text(updated_primary, encoding="utf-8")
    _git(git_repo, "add", primary_path)

    result = scope_api.resolve_scope(scope_api.ScopeRequest(repository=git_repo, scope="index"))

    assert result.status == "UNKNOWN"
    assert result.reason == "unsafe_governed_input"
    assert set(result.selected_paths) == {primary_path, missing_path}
    assert result.index_tree
    assert missing_path not in result.input_manifest
    assert missing_path in result.policy_paths


@pytest.mark.parametrize("extend", ["../escape.toml", "missing.toml", "ruff.toml"], ids=["escape", "missing", "cycle"])
def test_ruff_extend_rejects_escape_cycle_or_missing_input(scope_api: Any, tmp_path: Path, extend: str) -> None:
    (tmp_path / "ruff.toml").write_text(f"extend='{extend}'\n", encoding="utf-8")

    policy = scope_api.resolve_ruff_policy(tmp_path, expected_version="0.15.12")

    assert policy.status == "UNKNOWN"


def test_ruff_force_exclude_cannot_drop_governed_input(scope_api: Any, tmp_path: Path) -> None:
    (tmp_path / "ruff.toml").write_text("force-exclude=true\n", encoding="utf-8")

    projection = scope_api.project_ruff_policy(
        scope_api.resolve_ruff_policy(tmp_path, expected_version="0.15.12"),
        snapshot_root=tmp_path / "snapshot",
    )

    assert projection.argv_contains("--no-force-exclude")


@pytest.mark.parametrize("option", ["per-file-ignores", "extend-per-file-ignores"])
def test_ruff_per_file_ignores_cannot_silence_added_or_renamed_input(
    scope_api: Any, tmp_path: Path, option: str
) -> None:
    (tmp_path / "ruff.toml").write_text(f"[lint.{option}]\n'*.py'=['F401']\n", encoding="utf-8")

    projection = scope_api.project_ruff_policy(
        scope_api.resolve_ruff_policy(tmp_path, expected_version="0.15.12"),
        snapshot_root=tmp_path / "snapshot",
    )

    assert projection.values[option] == {}


def test_ruff_per_file_target_version_cannot_change_rules_across_rename(scope_api: Any, tmp_path: Path) -> None:
    (tmp_path / "ruff.toml").write_text("[per-file-target-version]\n'old.py'='py311'\n", encoding="utf-8")

    projection = scope_api.project_ruff_policy(
        scope_api.resolve_ruff_policy(tmp_path, expected_version="0.15.12"),
        snapshot_root=tmp_path / "snapshot",
    )

    assert projection.values["per-file-target-version"] == {}


def test_ruff_namespace_packages_cannot_change_rules_across_rename(scope_api: Any, tmp_path: Path) -> None:
    (tmp_path / "ruff.toml").write_text("namespace-packages=['src']\n", encoding="utf-8")

    projection = scope_api.project_ruff_policy(
        scope_api.resolve_ruff_policy(tmp_path, expected_version="0.15.12"),
        snapshot_root=tmp_path / "snapshot",
    )

    assert projection.values["namespace-packages"] == []


def test_ruff_projection_does_not_emit_invalid_flattened_pycodestyle_key(scope_api: Any, tmp_path: Path) -> None:
    policy = scope_api.RuffPolicy.default(version="0.15.12")

    projection = scope_api.project_ruff_policy(policy, snapshot_root=tmp_path / "snapshot")

    assert "lint.pycodestyle.ignore-overlong-task-comments" not in projection.values
    assert projection.values["lint"]["pycodestyle"]["ignore-overlong-task-comments"] is False


def test_basedpyright_referenced_policy_files_are_governed(scope_api: Any, tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.basedpyright]\nextends='base.json'\n", encoding="utf-8")
    (tmp_path / "base.json").write_text('{"baselineFile":"baseline.json"}', encoding="utf-8")
    (tmp_path / "baseline.json").write_text("{}", encoding="utf-8")

    policy = scope_api.resolve_basedpyright_policy(tmp_path, expected_version="1.39.10")

    assert policy.reference_paths == ("base.json", "baseline.json", "pyproject.toml")


def test_range_change_to_basedpyright_reference_is_governed(scope_api: Any, git_repo: Path) -> None:
    (git_repo / "pyrightconfig.json").write_text('{"extends":"config/base.json"}', encoding="utf-8")
    (git_repo / "config").mkdir()
    (git_repo / "config/base.json").write_text('{"baselineFile":"baseline.json"}', encoding="utf-8")
    (git_repo / "config/baseline.json").write_text("{}", encoding="utf-8")
    base = _commit(git_repo, "add basedpyright policy graph")
    (git_repo / "config/base.json").write_text('{"typeCheckingMode":"strict"}', encoding="utf-8")
    head = _commit(git_repo, "change basedpyright policy reference")

    result = scope_api.resolve_scope(_range_request(scope_api, git_repo, base, head))

    assert result.status == "UNKNOWN"
    assert result.reason == "candidate_policy_change"
    assert "config/base.json" in result.policy_paths


def test_basedpyright_include_exclude_cannot_drop_governed_input(scope_api: Any, tmp_path: Path) -> None:
    policy = scope_api.BasedPyrightPolicy(include=("one.py",), exclude=("two.py",), ignore=())

    projection = scope_api.project_basedpyright_policy(
        policy,
        snapshot_root=tmp_path,
        eligible_inputs=("one.py", "two.py"),
    )

    assert projection.values["include"] == [str(tmp_path / "one.py"), str(tmp_path / "two.py")]
    assert projection.values["exclude"] == []


def test_basedpyright_projection_exposes_flat_project_runtime_site_packages(scope_api: Any, tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot"
    runtime = tmp_path / "project-runtime/site-packages"
    snapshot.mkdir()
    (runtime / "consumer_dependency").mkdir(parents=True)
    (runtime / "consumer_dependency/__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (snapshot / "app.py").write_text("from consumer_dependency import VALUE\nRESULT = VALUE\n", encoding="utf-8")
    policy = scope_api.BasedPyrightPolicy(values={"extraPaths": ["candidate-controlled"]})

    projection = scope_api.project_basedpyright_policy(
        policy,
        snapshot_root=snapshot,
        eligible_inputs=("app.py",),
        project_runtime_site_packages=str(runtime),
    )
    result = subprocess.run(
        [sys.executable, "-m", "basedpyright", "--project", str(projection.config_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert projection.status == "PASS"
    assert projection.values["extraPaths"] == [str(runtime)]
    assert result.returncode == 0, result.stdout + result.stderr
    assert "reportMissingImports" not in result.stdout


def test_context_requires_target_and_head_tree_identities(scope_api: Any, git_repo: Path, tmp_path: Path) -> None:
    base, head = _make_range(git_repo)
    context = tmp_path / "context.json"
    context.write_text(
        json.dumps(
            {
                "schema": "github-actions-pr-v1",
                "provider": "github-actions",
                "repository": "example/repo",
                "event": "pull_request",
                "pull_request": 1,
                "target_ref": "refs/heads/main",
                "head_ref": "refs/heads/feature",
                "target_commit": base,
                "head_commit": head,
            }
        ),
        encoding="utf-8",
    )

    result = scope_api.resolve_scope(
        _range_request(scope_api, git_repo, base, head, pr_context_file=context, repository_slug="example/repo")
    )

    assert result.status == "UNKNOWN"
    assert result.reason == "unsafe_pr_context"


def test_context_declared_source_lock_change_is_governed(scope_api: Any, git_repo: Path, tmp_path: Path) -> None:
    lock = git_repo / "requirements.lock"
    lock.write_text("demo==1\n", encoding="utf-8")
    base = _commit(git_repo, "add runtime source lock")
    lock.write_text("demo==2\n", encoding="utf-8")
    head = _commit(git_repo, "change runtime source lock")
    context = tmp_path / "context.json"
    document = {
        "schema": "github-actions-pr-v1",
        "provider": "github-actions",
        "repository": "example/repo",
        "event": "pull_request",
        "pull_request": 1,
        "target_ref": "refs/heads/main",
        "head_ref": "refs/heads/feature",
        "target_commit": base,
        "target_tree": _git(git_repo, "rev-parse", f"{base}^{{tree}}"),
        "head_commit": head,
        "head_tree": _git(git_repo, "rev-parse", f"{head}^{{tree}}"),
        "project_runtime": {
            "descriptor_digest": "sha256:" + "a" * 64,
            "build_attestation_digest": "sha256:" + "b" * 64,
            "source_lock_paths": [
                {
                    "path": "requirements.lock",
                    "blob_sha": "c" * 40,
                    "content_sha256": "sha256:" + "d" * 64,
                }
            ],
        },
    }
    context.write_text(json.dumps(document), encoding="utf-8")

    result = scope_api.resolve_scope(
        _range_request(scope_api, git_repo, base, head, pr_context_file=context, repository_slug="example/repo")
    )

    assert result.status == "UNKNOWN"
    assert result.reason == "candidate_project_runtime_source_lock_change"
    assert result.selected_paths == ("requirements.lock",)


def test_local_discovery_preserves_nul_delimited_python_paths(
    scope_api: Any, git_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tracked = git_repo / "src/café.py"
    tracked.write_text("VALUE = 1\n", encoding="utf-8")
    _commit(git_repo, "add non-ascii path")
    tracked.write_text("VALUE = 2\n", encoding="utf-8")
    untracked = git_repo / "src/line\nbreak.py"
    untracked.write_text("VALUE = 3\n", encoding="utf-8")
    monkeypatch.chdir(git_repo)

    worktree = scope_api.discover_worktree_python_files(git_repo, include_tests=True)
    complete = scope_api.discover_full_python_files(git_repo, include_tests=True)

    assert Path("src/café.py") in worktree
    assert Path("src/line\nbreak.py") in worktree
    assert Path("src/café.py") in complete
    assert Path("src/line\nbreak.py") in complete


def test_ini_policy_projection_preserves_pytest_and_pylint_families(scope_api: Any) -> None:
    projection = scope_api._ini_policy_projection(
        b"[pytest]\naddopts=-q\n[pylint.main]\nignore=build\n[pylint.messages control]\ndisable=C0103\n"
    )

    assert set(projection) == {"pytest", "pylint.main", "pylint.messages control"}


def test_pylint_locator_ignores_unrelated_shared_config(scope_api: Any, tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (tmp_path / "pylintrc").write_text("[MAIN]\nignore=build\n", encoding="utf-8")

    policy = scope_api.resolve_pylint_policy(tmp_path, expected_version="4.0.7")

    assert policy.status == "PASS"
    assert policy.selected_path == "pylintrc"


def test_basedpyright_ignore_cannot_suppress_governed_input(scope_api: Any, tmp_path: Path) -> None:
    policy = scope_api.BasedPyrightPolicy(include=(), exclude=(), ignore=("src/app.py",))

    projection = scope_api.project_basedpyright_policy(policy, snapshot_root=tmp_path, eligible_inputs=("src/app.py",))

    assert projection.values["ignore"] == []


def test_basedpyright_baseline_cannot_suppress_relocated_diagnostic(scope_api: Any, tmp_path: Path) -> None:
    policy = scope_api.BasedPyrightPolicy(include=(), exclude=(), ignore=(), baseline_file="baseline.json")

    projection = scope_api.project_basedpyright_policy(policy, snapshot_root=tmp_path, eligible_inputs=("src/app.py",))

    assert "baselineFile" not in projection.values
    assert "--baselinefile" not in projection.argv


@pytest.mark.parametrize("field", ["strict", "executionEnvironments"])
def test_basedpyright_nonempty_strict_is_unknown_before_projection(scope_api: Any, tmp_path: Path, field: str) -> None:
    policy = scope_api.BasedPyrightPolicy(include=(), exclude=(), ignore=(), **{field: ("src",)})

    result = scope_api.project_basedpyright_policy(policy, snapshot_root=tmp_path, eligible_inputs=("src/app.py",))

    assert result.status == "UNKNOWN"


def test_basedpyright_strict_cannot_lower_severity_across_rename(scope_api: Any, tmp_path: Path) -> None:
    policy = scope_api.BasedPyrightPolicy(include=(), exclude=(), ignore=(), strict=())

    projection = scope_api.project_basedpyright_policy(policy, snapshot_root=tmp_path, eligible_inputs=("new.py",))

    assert projection.values["strict"] == []


def test_basedpyright_strict_path_diagnostics_cannot_disappear(scope_api: Any, tmp_path: Path) -> None:
    policy = scope_api.BasedPyrightPolicy(include=(), exclude=(), ignore=(), strict=("src/app.py",))

    result = scope_api.project_basedpyright_policy(policy, snapshot_root=tmp_path, eligible_inputs=("src/app.py",))

    assert result.status == "UNKNOWN"


def test_semgrep_ai_bloat_rule_pack_is_governed_and_sealed(scope_api: Any, tmp_path: Path) -> None:
    target = tmp_path / "target"
    module = tmp_path / "module"
    target.mkdir()
    (module / "resources/semgrep-rules").mkdir(parents=True)
    (module / ".semgrep").mkdir()
    (module / ".semgrep/clean_code.yaml").write_text("rules: []\n", encoding="utf-8")
    (module / "resources/semgrep-rules/ai-bloat.yaml").write_text("rules: []\n", encoding="utf-8")

    bundle = scope_api.resolve_semgrep_bundle(target, signed_module_root=module)

    assert bundle.status == "PASS"
    assert bundle.clean.identity_kind == "signed_module_payload"
    assert bundle.ai_bloat.identity_kind == "signed_module_payload"
    assert bundle.bundle_digest.startswith("sha256:")
