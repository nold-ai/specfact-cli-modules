from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal, cast

import pytest
from pytest import MonkeyPatch

from specfact_code_review.run.findings import ReviewFinding, ReviewReport
from specfact_code_review.run.runner import (
    _changed_lines_from_git,
    _coverage_findings,
    _preserve_reasons_for_finding,
    _pytest_python_executable,
    _pytest_targets,
    _run_pytest_with_coverage,
    run_review,
    run_tdd_gate,
)


def _finding(
    *,
    tool: str,
    rule: str,
    severity: Literal["error", "warning", "info"] = "warning",
    category: Literal[
        "clean_code",
        "security",
        "type_safety",
        "contracts",
        "testing",
        "style",
        "architecture",
        "tool_error",
        "naming",
        "kiss",
        "yagni",
        "dry",
        "solid",
        "ai_bloat",
    ] = "style",
) -> ReviewFinding:
    return ReviewFinding(
        category=category,
        severity=severity,
        tool=tool,
        rule=rule,
        file="packages/specfact-code-review/src/specfact_code_review/run/scorer.py",
        line=10,
        message=f"{tool} finding",
        fixable=False,
    )


def _synthetic_complete_profile_evidence(runner_api: Any) -> dict[str, dict[str, object]]:
    return {
        member_id: {
            "execution_state": "ran",
            "evidence_outcome": "PASS",
            "version": runner_api._C14_ANALYZER_VERSIONS[member_id],
        }
        for member_id in runner_api.default_pr_range_profile().all_ids
    }


def _synthetic_snapshot_context(runner_api: Any) -> Any:
    kinds = ("git_blob", "signed_module_payload", "generated_projection", "builtin_mode")
    identities = tuple(
        runner_api.GeneratedInputIdentity(kinds[index % len(kinds)], f"sha256:{index + 1:064x}")
        for index, _member_id in enumerate(runner_api.default_pr_range_profile().all_ids)
    )
    return runner_api.SyntheticSnapshotContext(identities, identities)


def _simplification_finding(
    *,
    category: Literal["ai_bloat", "dry", "kiss"] = "ai_bloat",
    confidence: Literal["low", "medium", "high"] = "high",
    guidance_kind: Literal["safe_mechanical", "needs_tests", "design_judgment", "preserve"] | None = None,
) -> ReviewFinding:
    guided_fields = (
        {
            "recommended_action": "keep" if guidance_kind == "preserve" else "collapse",
            "clean_code_principle": "kiss",
            "rationale": "The repeated loop shape can be expressed directly.",
            "safety_checks": ["targeted tests cover the surrounding behavior"],
            "action_status": "recommended",
            "preserve_reason": "The wrapper is a compatibility boundary." if guidance_kind == "preserve" else None,
        }
        if guidance_kind is not None
        else {}
    )
    return ReviewFinding(
        category=category,
        severity="info",
        tool="ast",
        rule="ai-bloat.manual-accumulator-loop",
        file="packages/specfact-code-review/src/specfact_code_review/run/scorer.py",
        line=10,
        message="Manual accumulator loop can be collapsed.",
        fixable=False,
        confidence=confidence,
        rewrite_hint="Replace the append loop with a list comprehension.",
        canonical_pattern="manual-accumulator-loop",
        intent_key="score-review",
        estimated_deletion_lines=3,
        guidance_kind=guidance_kind,
        **guided_fields,
    )


def _stub_review_tools(monkeypatch: MonkeyPatch, findings: list[ReviewFinding]) -> None:
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: findings)
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))


def test_run_review_changed_enforcement_reports_legacy_blockers_without_blocking(monkeypatch: MonkeyPatch) -> None:
    finding = _finding(tool="radon", rule="complexity", severity="error", category="kiss")
    _stub_review_tools(monkeypatch, [finding])
    monkeypatch.setattr("specfact_code_review.run.runner._changed_lines_from_git", lambda files: {finding.file: {99}})

    report = run_review([Path(finding.file)], no_tests=True, review_mode="changed")

    assert report.ci_exit_code == 0
    assert report.overall_verdict == "PASS_WITH_ADVISORY"
    assert report.enforcement_mode == "changed"
    assert "legacy blocking" in (report.enforcement_summary or "")


def test_run_review_changed_enforcement_blocks_changed_line_findings(monkeypatch: MonkeyPatch) -> None:
    finding = _finding(tool="radon", rule="complexity", severity="error", category="kiss")
    _stub_review_tools(monkeypatch, [finding])
    monkeypatch.setattr("specfact_code_review.run.runner._changed_lines_from_git", lambda files: {finding.file: {10}})

    report = run_review([Path(finding.file)], no_tests=True, review_mode="changed")

    assert report.ci_exit_code == 1
    assert report.overall_verdict == "FAIL"
    assert report.enforcement_mode == "changed"
    assert "changed lines" in (report.enforcement_summary or "")


def test_run_review_changed_enforcement_normalizes_absolute_finding_paths(monkeypatch: MonkeyPatch) -> None:
    relative = "packages/specfact-code-review/src/specfact_code_review/run/scorer.py"
    finding = _finding(tool="radon", rule="complexity", severity="error", category="kiss")
    finding = finding.model_copy(update={"file": str(Path.cwd() / relative)})
    _stub_review_tools(monkeypatch, [finding])
    monkeypatch.setattr("specfact_code_review.run.runner._changed_lines_from_git", lambda files: {relative: {10}})

    report = run_review([Path(finding.file)], no_tests=True, review_mode="changed")

    assert report.ci_exit_code == 1
    assert report.overall_verdict == "FAIL"
    assert report.enforcement_mode == "changed"
    assert "changed lines" in (report.enforcement_summary or "")


def test_run_review_shadow_enforcement_never_blocks(monkeypatch: MonkeyPatch) -> None:
    finding = _finding(tool="radon", rule="complexity", severity="error", category="kiss")
    _stub_review_tools(monkeypatch, [finding])

    report = run_review([Path(finding.file)], no_tests=True, review_mode="shadow")

    assert report.ci_exit_code == 0
    assert report.overall_verdict == "FAIL"
    assert report.enforcement_mode == "shadow"


def test_changed_lines_from_git_skips_unreadable_untracked_files(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    untracked_file = tmp_path / "binary.py"
    untracked_file.write_bytes(b"\xff\xfe")

    def _fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if command[:3] == ["git", "diff", "--unified=0"]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        if command[:3] == ["git", "ls-files", "--others"]:
            return subprocess.CompletedProcess(command, 0, stdout=f"{untracked_file}\n", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    assert _changed_lines_from_git([untracked_file]) == {}


def test_run_review_calls_runners_in_order(monkeypatch: MonkeyPatch) -> None:
    calls: list[str] = []

    def _record(name: str) -> list[ReviewFinding]:
        calls.append(name)
        return []

    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: _record("ruff"))
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: _record("radon"))
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: _record("semgrep"))
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: _record("semgrep_bugs"))
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: _record("ai_bloat"))
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: _record("ast"))
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: _record("basedpyright"))
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: _record("pylint"))
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_contract_check",
        lambda files, **_: _record("contracts"),
    )
    monkeypatch.setattr(
        "specfact_code_review.run.runner._evaluate_tdd_gate",
        lambda files: (
            _record("testing"),
            {"packages/specfact-code-review/src/specfact_code_review/run/scorer.py": 95.0},
        ),
    )

    report = run_review([Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")])

    assert isinstance(report, ReviewReport)
    assert calls == [
        "ruff",
        "radon",
        "semgrep",
        "semgrep_bugs",
        "ai_bloat",
        "ast",
        "basedpyright",
        "pylint",
        "contracts",
        "testing",
    ]


def test_capsule_review_launches_each_active_member_in_a_fresh_sandbox(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    runner_api = _c14_runner()
    source = tmp_path / "src/app.py"
    source.parent.mkdir()
    source.write_text("VALUE = 1\n", encoding="utf-8")
    runtime = SimpleNamespace(identity="sha256:" + "a" * 64)
    launches: list[tuple[str, str]] = []

    monkeypatch.setattr(runner_api, "_prepare_capsule_runtime", lambda: (runtime, ""))

    def execute_member(request: Any) -> dict[str, object]:
        launches.append((request.member, request.invocation_id))
        return {
            "execution_state": "ran",
            "evidence_outcome": "PASS",
            "findings": [],
            "diagnostic": "",
        }

    monkeypatch.setattr(runner_api, "_execute_capsule_member", execute_member)

    report = runner_api.run_capsule_review([source], no_tests=False, bug_hunt=True)

    assert [member for member, _invocation in launches] == list(runner_api.default_pr_range_profile().all_ids)
    assert len({invocation for _member, invocation in launches}) == len(launches)
    assert report.schema_version == "1.6"
    assert report.assurance_status == "PASS"


def test_capsule_member_passes_explicit_target_policy_to_adapter(monkeypatch: MonkeyPatch) -> None:
    runner_api = _c14_runner()
    observed: dict[str, object] = {}

    def run_ruff_with_policy(files: list[Path], *, extra_args: tuple[str, ...] = ()) -> list[ReviewFinding]:
        observed["files"] = files
        observed["extra_args"] = extra_args
        return []

    monkeypatch.setattr(runner_api, "run_ruff", run_ruff_with_policy)

    findings = runner_api._member_findings(
        "ruff",
        [Path("/opt/specfact/snapshot/src/app.py")],
        bug_hunt=False,
        adapter_argv=("--config", "/opt/specfact/config/1/ruff.toml", "--no-cache"),
    )

    assert findings == []
    assert observed["extra_args"] == ("--config", "/opt/specfact/config/1/ruff.toml", "--no-cache")


def test_capsule_radon_member_activates_bound_full_result_contract(monkeypatch: MonkeyPatch) -> None:
    runner_api = _c14_runner()
    observed: dict[str, object] = {}

    def run_radon_with_contract(files: list[Path], *, full_result: bool = False) -> list[ReviewFinding]:
        observed["files"] = files
        observed["full_result"] = full_result
        return []

    monkeypatch.setattr(runner_api, "run_radon", run_radon_with_contract)

    findings = runner_api._member_findings(
        "radon",
        [Path("/opt/specfact/snapshot/src/app.py")],
        bug_hunt=False,
        adapter_argv=("radon-full-result-v1",),
    )

    assert findings == []
    assert observed == {
        "files": [Path("/opt/specfact/snapshot/src/app.py")],
        "full_result": True,
    }


def test_capsule_contract_member_routes_static_and_crosshair_input_manifests(monkeypatch: MonkeyPatch) -> None:
    runner_api = _c14_runner()
    files = [
        Path("/opt/specfact/snapshot/src/app.py"),
        Path("/opt/specfact/snapshot/src/types.pyi"),
        Path("/opt/specfact/snapshot/tests/test_app.py"),
        Path("/opt/specfact/snapshot/tests/helpers.py"),
    ]
    observed: dict[str, object] = {}

    def run_contracts(static_files: list[Path], **kwargs: object) -> list[ReviewFinding]:
        observed["static"] = static_files
        observed.update(kwargs)
        return []

    monkeypatch.setattr(runner_api, "run_contract_check", run_contracts)

    assert (
        runner_api._member_findings(
            "contracts",
            files,
            bug_hunt=False,
            adapter_argv=("contract-inputs-v1", "--test-root", "tests"),
        )
        == []
    )
    assert observed["static"] == files
    assert observed["crosshair_files"] == [Path("/opt/specfact/snapshot/src/app.py")]


def test_capsule_targeted_pytest_executes_supplied_complete_inventory(monkeypatch: MonkeyPatch) -> None:
    runner_api = _c14_runner()
    observed: list[tuple[str, ...]] = []
    selectors = (
        "tests/test_a.py::test_a",
        "tests/nonconventional/test_b.py::TestB::test_b",
    )
    monkeypatch.setattr(
        runner_api,
        "_evaluate_tdd_gate",
        lambda *_args: pytest.fail("immutable capsule execution must not use source-to-test mapping"),
    )
    monkeypatch.setattr(
        runner_api,
        "_evaluate_complete_tdd_gate",
        lambda _files, supplied: (observed.append(supplied) or [], None),
        raising=False,
    )

    findings = runner_api._member_findings(
        "targeted-pytest-coverage",
        [Path("/opt/specfact/snapshot/src/app.py")],
        bug_hunt=False,
        adapter_argv=("--", *selectors),
        complete_pytest_inventory=True,
    )

    assert findings == []
    assert observed == [("--", *selectors)]


def test_complete_tdd_gate_excludes_sealed_custom_test_root_from_coverage(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    runner_api = _c14_runner()
    pytest_config = tmp_path / "pytest.ini"
    pytest_config.write_text(
        "[pytest]\ntestpaths = /opt/specfact/snapshot/integration\n",
        encoding="utf-8",
    )
    coverage_config = tmp_path / "coveragerc"
    coverage_config.write_text("[report]\nfail_under = 80\n", encoding="utf-8")
    observed: list[Path] = []
    observed_plans: list[tuple[str, ...]] = []
    observed_omission_policies: list[bool] = []

    def evaluate(
        source_files: list[Path], _execute: object, **kwargs: object
    ) -> tuple[list[ReviewFinding], dict[str, float]]:
        observed.extend(source_files)
        observed_plans.append(cast(tuple[str, ...], kwargs["planned"]))
        observed_omission_policies.append(cast(bool, kwargs["allow_project_omitted_initializers"]))
        return [], {}

    monkeypatch.setattr(runner_api, "_evaluate_pytest_execution", evaluate)

    findings, coverage = runner_api._evaluate_complete_tdd_gate(
        [
            Path("/opt/specfact/snapshot/src/app.py"),
            Path("/opt/specfact/snapshot/integration/test_app.py"),
            Path("/opt/specfact/snapshot/integration/helpers.py"),
        ],
        (
            "-c",
            str(pytest_config),
            "--cov-config",
            str(coverage_config),
            "--",
            "integration/test_app.py::test_app",
        ),
    )

    assert findings == []
    assert coverage == {}
    assert observed == [Path("/opt/specfact/snapshot/src/app.py")]
    assert observed_plans == [("integration/test_app.py::test_app",)]
    assert observed_omission_policies == [False]


def test_complete_tdd_gate_preserves_sources_when_discovering_from_snapshot_root(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    runner_api = _c14_runner()
    pytest_config = tmp_path / "pytest.ini"
    pytest_config.write_text("[pytest]\ntestpaths = /opt/specfact/snapshot\n", encoding="utf-8")
    coverage_config = tmp_path / "coveragerc"
    coverage_config.write_text("[report]\nfail_under = 80\n", encoding="utf-8")
    source_file = Path("/opt/specfact/snapshot/src/app.py")
    test_file = Path("/opt/specfact/snapshot/tests/test_app.py")
    support_file = Path("/opt/specfact/snapshot/tests/helpers.py")
    observed: list[Path] = []

    def evaluate(
        source_files: list[Path], _execute: object, **_kwargs: object
    ) -> tuple[list[ReviewFinding], dict[str, float]]:
        observed.extend(source_files)
        return [], {}

    monkeypatch.setattr(runner_api, "_evaluate_pytest_execution", evaluate)

    findings, coverage = runner_api._evaluate_complete_tdd_gate(
        [source_file, test_file, support_file],
        (
            "-c",
            str(pytest_config),
            "--cov-config",
            str(coverage_config),
            "--",
            "tests/test_app.py::test_app",
        ),
    )

    assert findings == []
    assert coverage == {}
    assert observed == [source_file]


def test_complete_tdd_gate_keeps_colocated_production_file_in_coverage_scope(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    runner_api = _c14_runner()
    pytest_config = tmp_path / "pytest.ini"
    pytest_config.write_text("[pytest]\ntestpaths = /opt/specfact/snapshot\n", encoding="utf-8")
    coverage_config = tmp_path / "coveragerc"
    coverage_config.write_text("[report]\nfail_under = 80\n", encoding="utf-8")
    source_file = Path("/opt/specfact/snapshot/pkg/app.py")
    test_file = Path("/opt/specfact/snapshot/pkg/test_app.py")
    observed: list[Path] = []

    def evaluate(
        source_files: list[Path], _execute: object, **_kwargs: object
    ) -> tuple[list[ReviewFinding], dict[str, float]]:
        observed.extend(source_files)
        return [], {}

    monkeypatch.setattr(runner_api, "_evaluate_pytest_execution", evaluate)

    findings, coverage = runner_api._evaluate_complete_tdd_gate(
        [source_file, test_file],
        (
            "-c",
            str(pytest_config),
            "--cov-config",
            str(coverage_config),
            "--",
            "pkg/test_app.py::test_app",
        ),
    )

    assert findings == []
    assert coverage == {}
    assert observed == [source_file]


def test_sealed_target_bugs_policy_activates_semgrep_bugs_without_bug_hunt(monkeypatch: MonkeyPatch) -> None:
    runner_api = _c14_runner()
    observed: list[str] = []

    def execute(request: object) -> dict[str, object]:
        observed.append(cast(str, request.member))
        return {
            "execution_state": "ran",
            "evidence_outcome": "PASS",
            "findings": [],
            "diagnostic": "",
        }

    monkeypatch.setattr(runner_api, "_execute_capsule_member", execute)

    result = runner_api._run_capsule_snapshot(
        SimpleNamespace(identity="sha256:" + "a" * 64),
        snapshot_root=Path("/snapshot"),
        files=[Path("/snapshot/src/app.py")],
        options=runner_api.ReviewOptions(bug_hunt=False),
        member_argv={"semgrep-bugs": ("/opt/specfact/config/0",)},
    )

    assert "semgrep-bugs" in observed
    assert result.evidence["semgrep-bugs"]["evidence_outcome"] == "PASS"


def test_empty_capsule_snapshot_marks_every_member_not_applicable(monkeypatch: MonkeyPatch) -> None:
    runner_api = _c14_runner()
    monkeypatch.setattr(
        runner_api,
        "_execute_capsule_member",
        lambda *_args, **_kwargs: pytest.fail("empty snapshot must not launch an analyzer"),
    )

    result = runner_api._run_capsule_snapshot(
        SimpleNamespace(identity="sha256:" + "a" * 64),
        snapshot_root=Path("/snapshot"),
        files=[],
        options=runner_api.ReviewOptions(),
    )

    assert set(result.evidence) == set(runner_api.default_pr_range_profile().all_ids)
    assert {item["evidence_outcome"] for item in result.evidence.values()} == {"NOT_APPLICABLE"}


def test_deleted_python_head_runs_complete_pytest_inventory(monkeypatch: MonkeyPatch) -> None:
    runner_api = _c14_runner()
    launched: list[str] = []

    def execute(request: Any) -> dict[str, object]:
        launched.append(request.member)
        return {
            "execution_state": "ran",
            "evidence_outcome": "PASS",
            "findings": [],
            "diagnostic": "",
        }

    monkeypatch.setattr(runner_api, "_execute_capsule_member", execute)

    result = runner_api._run_capsule_snapshot(
        SimpleNamespace(identity="sha256:" + "a" * 64),
        snapshot_root=Path("/snapshot"),
        files=[],
        options=runner_api.ReviewOptions(),
        member_argv={"targeted-pytest-coverage": ("--", "tests/test_app.py::test_app")},
        scope_paths=("src/deleted.py",),
    )

    assert launched == ["targeted-pytest-coverage"]
    assert result.evidence["targeted-pytest-coverage"]["evidence_outcome"] == "PASS"


def test_snapshot_policy_bindings_use_generated_target_tip_projections(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    policy_root = tmp_path / "policy"
    snapshot_root = tmp_path / "snapshot"
    policy_root.mkdir()
    (snapshot_root / "src").mkdir(parents=True)
    (policy_root / "ruff.toml").write_text("target-version = 'py311'\n", encoding="utf-8")
    source = snapshot_root / "src/app.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")

    bindings = runner_api._snapshot_policy_bindings(
        SimpleNamespace(root=policy_root),
        snapshot_root=snapshot_root,
        files=[source],
    )

    try:
        assert bindings.member_argv["ruff"][0] == "--config"
        assert bindings.member_argv["ruff"][1].endswith("/ruff.toml")
        assert bindings.member_argv["basedpyright"][0] == "--project"
        assert bindings.member_argv["basedpyright"][1].endswith("/basedpyright.json")
        assert bindings.member_argv["pylint"][0] == "--rcfile"
        assert bindings.member_argv["pylint"][1].endswith("/pylintrc")
        assert bindings.member_argv["radon"] == ("radon-full-result-v1",)
        assert all(
            not argument.startswith(str(snapshot_root)) for argv in bindings.member_argv.values() for argument in argv
        )
    finally:
        for root in bindings.cleanup_roots:
            shutil.rmtree(root, ignore_errors=True)


def test_snapshot_policy_bindings_apply_sealed_pytest_and_coverage_projections(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    policy_root = tmp_path / "policy"
    snapshot_root = tmp_path / "snapshot"
    policy_root.mkdir()
    snapshot_root.mkdir()
    (policy_root / "pytest.ini").write_text(
        "[pytest]\ntestpaths = target_tests\npython_files = check_*.py\n",
        encoding="utf-8",
    )
    (policy_root / ".coveragerc").write_text("[run]\nbranch = true\n", encoding="utf-8")

    bindings = runner_api._with_pytest_inventory(
        runner_api._snapshot_policy_bindings(
            SimpleNamespace(root=policy_root),
            snapshot_root=snapshot_root,
            files=[],
        ),
        ("target_tests/check_app.py::test_app",),
    )

    try:
        argv = bindings.member_argv["targeted-pytest-coverage"]
        assert argv[argv.index("-c") + 1].startswith("/opt/specfact/config/")
        assert argv[argv.index("--cov-config") + 1].startswith("/opt/specfact/config/")
        assert argv[argv.index("--rootdir") + 1] == "/opt/specfact/snapshot"
        assert argv[-2:] == ("--", "target_tests/check_app.py::test_app")
        projected_payloads = [
            path.read_text(encoding="utf-8") for root in bindings.config_roots for path in root.iterdir()
        ]
        assert any("/opt/specfact/snapshot/target_tests" in payload for payload in projected_payloads)
        assert any("exclude_lines" in payload for payload in projected_payloads)
    finally:
        for root in bindings.cleanup_roots:
            shutil.rmtree(root, ignore_errors=True)


def test_capsule_policy_outputs_use_the_mounted_private_temp_root(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    policy_root = tmp_path / "policy"
    policy_root.mkdir()
    (policy_root / "pytest.ini").write_text(
        "[pytest]\ncache_dir = .cache\nlog_file = pytest.log\n",
        encoding="utf-8",
    )
    (policy_root / ".coveragerc").write_text(
        "[run]\ndata_file = .coverage\n[html]\ndirectory = htmlcov\n[xml]\noutput = coverage.xml\n",
        encoding="utf-8",
    )
    builder = runner_api._PolicyBindingBuilder()

    runner_api._bind_pytest_coverage_policy(builder, SimpleNamespace(root=policy_root))
    bindings = builder.result()

    try:
        payload = "\n".join(
            path.read_text(encoding="utf-8") for root in bindings.config_roots for path in root.iterdir()
        )
        assert "/opt/specfact/tmp/pytest" in payload
        assert "/opt/specfact/tmp/coverage" in payload
        assert "/opt/specfact/temporary" not in payload
    finally:
        for root in bindings.cleanup_roots:
            shutil.rmtree(root, ignore_errors=True)


def test_capsule_empty_policies_redirect_default_pytest_and_coverage_outputs() -> None:
    runner_api = _c14_runner()
    builder = runner_api._PolicyBindingBuilder()

    runner_api._bind_pytest_coverage_policy(builder, None)
    bindings = builder.result()

    try:
        payload = "\n".join(
            path.read_text(encoding="utf-8") for root in bindings.config_roots for path in root.iterdir()
        )
        assert "cache_dir = /opt/specfact/tmp/pytest/cache-dir" in payload
        assert "data_file = /opt/specfact/tmp/coverage/run-data_file" in payload
    finally:
        for root in bindings.cleanup_roots:
            shutil.rmtree(root, ignore_errors=True)


def test_capsule_scratch_layout_includes_projected_pytest_and_coverage_roots(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    _request_root, _output_root, scratch_root, _control_root = runner_api._prepare_capsule_process_roots(tmp_path)

    assert (scratch_root / "pytest").is_dir()
    assert (scratch_root / "coverage").is_dir()


def test_immutable_review_reuses_authenticated_project_runtime_for_both_snapshots(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    runner_api = _c14_runner()
    runtime_root = tmp_path / "project-runtime"
    runtime_root.mkdir()
    capsule = SimpleNamespace(identity="sha256:" + "a" * 64)
    descriptor = {"schema": "project-runtime-layer-v1"}
    observed_roots: list[Path | None] = []
    monkeypatch.setattr(runner_api, "_prepare_capsule_runtime", lambda **_kwargs: (capsule, ""))
    monkeypatch.setattr(
        runner_api.toolchain,
        "validate_project_runtime_layer",
        lambda *_args, **_kwargs: SimpleNamespace(status="PASS", reason="", pytest_plugins=()),
        raising=False,
    )
    monkeypatch.setattr(
        runner_api.toolchain,
        "materialize_project_runtime",
        lambda *_args, **_kwargs: SimpleNamespace(
            status="PASS", root=runtime_root, identity="sha256:" + "b" * 64, reason=""
        ),
        raising=False,
    )

    def run_snapshot(*_args: object, **kwargs: object) -> Any:
        observed_roots.append(cast(Path | None, kwargs.get("project_runtime_root")))
        return runner_api.CapsuleSnapshotResult(_synthetic_complete_profile_evidence(runner_api), {})

    monkeypatch.setattr(runner_api, "_run_capsule_snapshot", run_snapshot)
    monkeypatch.setattr(runner_api, "_classify_range_findings", lambda *_args: ({}, {}))
    monkeypatch.setattr(
        runner_api,
        "_capsule_report",
        lambda *_args, **_kwargs: ReviewReport(run_id="runtime", score=100, findings=[], summary="complete"),
    )
    snapshot = SimpleNamespace(root=tmp_path, contents={})
    resolution = SimpleNamespace(
        base_snapshot=snapshot,
        head_snapshot=snapshot,
        selected_paths=(),
        policy_bundle=None,
        resolved_target_commit="1" * 40,
        claimed_context={"project_runtime": descriptor},
    )

    runner_api.run_immutable_scope_review(
        resolution,
        options=runner_api.ReviewOptions(no_tests=False),
        scope_evidence={"assurance_kind": "range_candidate"},
    )

    assert observed_roots == [runtime_root, runtime_root]


def test_project_runtime_validation_binds_resolved_target_tree(monkeypatch: MonkeyPatch) -> None:
    runner_api = _c14_runner()
    observed: list[dict[str, object]] = []

    def validate(*_args: object, **kwargs: object) -> object:
        observed.append(kwargs)
        return SimpleNamespace(status="UNKNOWN", reason="stop", pytest_plugins=())

    monkeypatch.setattr(runner_api.toolchain, "validate_project_runtime_layer", validate)
    resolution = SimpleNamespace(
        claimed_context={"project_runtime": {"schema": "project-runtime-layer-v1"}},
        resolved_target_commit="1" * 40,
        resolved_target_tree="2" * 40,
    )

    materialized, plugins, reason = runner_api._materialize_claimed_project_runtime(resolution)

    assert materialized is None
    assert plugins == ()
    assert reason == "stop"
    assert observed == [{"expected_target": "1" * 40, "expected_tree": "2" * 40}]


def test_immutable_review_explicitly_loads_only_authenticated_project_pytest_plugins(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    runner_api = _c14_runner()
    runtime_root = tmp_path / "project-runtime"
    runtime_root.mkdir()
    capsule = SimpleNamespace(identity="sha256:" + "a" * 64)
    descriptor = {"schema": "project-runtime-layer-v1"}
    observed_argv: list[tuple[str, ...]] = []
    monkeypatch.setattr(runner_api, "_prepare_capsule_runtime", lambda **_kwargs: (capsule, ""))
    monkeypatch.setattr(
        runner_api.toolchain,
        "validate_project_runtime_layer",
        lambda *_args, **_kwargs: SimpleNamespace(
            status="PASS",
            reason="",
            pytest_plugins=(SimpleNamespace(entry_point="fixture_plugin"),),
        ),
        raising=False,
    )
    monkeypatch.setattr(
        runner_api.toolchain,
        "materialize_project_runtime",
        lambda *_args, **_kwargs: SimpleNamespace(
            status="PASS", root=runtime_root, identity="sha256:" + "b" * 64, reason=""
        ),
        raising=False,
    )
    monkeypatch.setattr(
        runner_api,
        "_reconcile_immutable_pytest_inventory",
        lambda *_args, **_kwargs: runner_api.ImmutablePytestInventory(
            runner_api.CandidateReconciliation("PASS"),
            ("tests/test_app.py::test_app",),
            ("tests/test_app.py::test_app",),
        ),
    )
    monkeypatch.setattr(
        runner_api,
        "_preflight_project_runtime_pytest_plugins",
        lambda *_args, **_kwargs: runner_api.CandidateReconciliation("PASS"),
    )

    def run_snapshot(*_args: object, **kwargs: object) -> Any:
        observed_argv.append(cast(dict[str, tuple[str, ...]], kwargs["member_argv"])["targeted-pytest-coverage"])
        return runner_api.CapsuleSnapshotResult(_synthetic_complete_profile_evidence(runner_api), {})

    monkeypatch.setattr(runner_api, "_run_capsule_snapshot", run_snapshot)
    monkeypatch.setattr(runner_api, "_classify_range_findings", lambda *_args: ({}, {}))
    monkeypatch.setattr(
        runner_api,
        "_capsule_report",
        lambda *_args, **_kwargs: ReviewReport(run_id="plugins", score=100, findings=[], summary="complete"),
    )
    snapshot = SimpleNamespace(root=tmp_path, contents={})
    resolution = SimpleNamespace(
        base_snapshot=snapshot,
        head_snapshot=snapshot,
        selected_paths=(),
        policy_bundle=None,
        resolved_target_commit="1" * 40,
        claimed_context={"project_runtime": descriptor},
    )

    runner_api.run_immutable_scope_review(
        resolution,
        options=runner_api.ReviewOptions(no_tests=False),
        scope_evidence={"assurance_kind": "range_candidate"},
    )

    assert len(observed_argv) == 2
    assert all(argv.count("-p") == 1 for argv in observed_argv)
    assert all(argv[argv.index("-p") + 1] == "fixture_plugin" for argv in observed_argv)


def test_immutable_review_rejects_plugin_preflight_before_snapshot_execution(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    runner_api = _c14_runner()
    runtime_root = tmp_path / "project-runtime"
    runtime_root.mkdir()
    capsule = SimpleNamespace(identity="sha256:" + "a" * 64)
    descriptor = {"schema": "project-runtime-layer-v1"}
    plugin = SimpleNamespace(entry_point="fixture_plugin")
    monkeypatch.setattr(runner_api, "_prepare_capsule_runtime", lambda **_kwargs: (capsule, ""))
    monkeypatch.setattr(
        runner_api.toolchain,
        "validate_project_runtime_layer",
        lambda *_args, **_kwargs: SimpleNamespace(status="PASS", reason="", pytest_plugins=(plugin,)),
    )
    monkeypatch.setattr(
        runner_api.toolchain,
        "materialize_project_runtime",
        lambda *_args, **_kwargs: SimpleNamespace(
            status="PASS", root=runtime_root, identity="sha256:" + "b" * 64, reason=""
        ),
    )
    monkeypatch.setattr(
        runner_api,
        "_preflight_project_runtime_pytest_plugins",
        lambda *_args, **_kwargs: runner_api.CandidateReconciliation("UNKNOWN", "pytest_plugin_capability_mismatch"),
        raising=False,
    )
    monkeypatch.setattr(
        runner_api,
        "_run_capsule_snapshot",
        lambda *_args, **_kwargs: pytest.fail("snapshot analyzers must not run after plugin preflight failure"),
    )
    snapshot = SimpleNamespace(root=tmp_path, contents={})
    resolution = SimpleNamespace(
        base_snapshot=snapshot,
        head_snapshot=snapshot,
        policy_bundle=None,
        resolved_target_commit="1" * 40,
        claimed_context={"project_runtime": descriptor},
    )

    report = runner_api.run_immutable_scope_review(
        resolution,
        options=runner_api.ReviewOptions(no_tests=False),
        scope_evidence={"assurance_kind": "range_candidate"},
    )

    assert report.assurance_status == "UNKNOWN"
    assert {item["diagnostic"] for item in report.analyzer_evidence} == {"pytest_plugin_capability_mismatch"}


def test_plugin_preflight_uses_snapshot_free_dedicated_capsule_member(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    runner_api = _c14_runner()
    runtime = SimpleNamespace()
    project_runtime = SimpleNamespace(root=tmp_path / "project-runtime")
    plugin = runner_api.toolchain.PytestPluginIdentity(
        distribution="fixture-plugin",
        version="1.0",
        entry_point="fixture_plugin",
        options=(),
        ini_fields=(),
        hooks=("pytest_fixture_setup",),
        parser_catalog_digest=runner_api.toolchain.pytest_parser_catalog_digest(options=(), ini_fields=()),
        hook_capability_digest=runner_api.toolchain.pytest_hook_capability_digest(("pytest_fixture_setup",)),
    )
    observed: list[Any] = []

    def execute(request: Any) -> dict[str, object]:
        observed.append(request)
        return {"evidence_outcome": "PASS"}

    monkeypatch.setattr(runner_api, "_execute_capsule_member", execute)

    result = runner_api._preflight_project_runtime_pytest_plugins(runtime, project_runtime, (plugin,))

    assert result.status == "PASS"
    assert len(observed) == 1
    assert observed[0].member == "targeted-pytest-plugin-preflight"
    assert observed[0].files == []
    assert observed[0].project_runtime_root == project_runtime.root


def test_index_review_uses_head_policy_for_both_immutable_snapshots(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    runner_api = _c14_runner()
    base_root = tmp_path / "base"
    head_root = tmp_path / "index"
    base_root.mkdir()
    head_root.mkdir()
    (base_root / "pytest.ini").write_text("[pytest]\ntestpaths = trusted_tests\n", encoding="utf-8")
    (head_root / "pytest.ini").write_text("[pytest]\ntestpaths = staged_tests\n", encoding="utf-8")
    observed_configs: list[str] = []
    monkeypatch.setattr(
        runner_api,
        "_prepare_capsule_runtime",
        lambda **_kwargs: (SimpleNamespace(identity="sha256:" + "a" * 64), ""),
    )
    monkeypatch.setattr(
        runner_api,
        "_reconcile_immutable_pytest_inventory",
        lambda *_args, **_kwargs: runner_api.ImmutablePytestInventory(
            runner_api.CandidateReconciliation("PASS"),
            ("trusted_tests/test_app.py::test_app",),
            ("trusted_tests/test_app.py::test_app",),
        ),
    )

    def run_snapshot(*_args: object, **kwargs: object) -> Any:
        config_roots = cast(tuple[Path, ...], kwargs["config_roots"])
        pytest_config = next(path for root in config_roots for path in root.iterdir() if path.name == "pytest.ini")
        observed_configs.append(pytest_config.read_text(encoding="utf-8"))
        return runner_api.CapsuleSnapshotResult(_synthetic_complete_profile_evidence(runner_api), {})

    monkeypatch.setattr(runner_api, "_run_capsule_snapshot", run_snapshot)
    monkeypatch.setattr(runner_api, "_classify_range_findings", lambda *_args: ({}, {}))
    monkeypatch.setattr(
        runner_api,
        "_capsule_report",
        lambda *_args, **_kwargs: ReviewReport(run_id="index-policy", score=100, findings=[], summary="complete"),
    )
    resolution = SimpleNamespace(
        assurance_kind="index",
        base_snapshot=SimpleNamespace(root=base_root, contents={}),
        head_snapshot=SimpleNamespace(root=head_root, contents={}),
        selected_paths=(),
        policy_bundle=None,
        claimed_context=None,
    )

    runner_api.run_immutable_scope_review(
        resolution,
        options=runner_api.ReviewOptions(no_tests=False),
        scope_evidence={"assurance_kind": "index"},
    )

    assert len(observed_configs) == 2
    assert all("/opt/specfact/snapshot/trusted_tests" in payload for payload in observed_configs)
    assert all("staged_tests" not in payload for payload in observed_configs)


def test_immutable_review_binds_each_complete_pytest_inventory_to_its_snapshot(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    runner_api = _c14_runner()
    base_root = tmp_path / "base"
    head_root = tmp_path / "head"
    for root in (base_root, head_root):
        (root / "tests").mkdir(parents=True)
        (root / "tests/test_a.py").write_text("def test_a():\n    assert True\n", encoding="utf-8")
    (head_root / "tests/test_b.py").write_text("def test_b():\n    assert True\n", encoding="utf-8")
    capsule = SimpleNamespace(identity="sha256:" + "a" * 64)
    observed_argv: list[dict[str, tuple[str, ...]]] = []
    monkeypatch.setattr(runner_api, "_prepare_capsule_runtime", lambda **_kwargs: (capsule, ""))

    def run_snapshot(*_args: object, **kwargs: object) -> Any:
        observed_argv.append(cast(dict[str, tuple[str, ...]], kwargs["member_argv"]))
        return runner_api.CapsuleSnapshotResult(_synthetic_complete_profile_evidence(runner_api), {})

    monkeypatch.setattr(runner_api, "_run_capsule_snapshot", run_snapshot)
    monkeypatch.setattr(runner_api, "_classify_range_findings", lambda *_args: ({}, {}))
    monkeypatch.setattr(
        runner_api,
        "_capsule_report",
        lambda *_args, **_kwargs: ReviewReport(run_id="inventory", score=100, findings=[], summary="complete"),
    )
    resolution = SimpleNamespace(
        base_snapshot=SimpleNamespace(root=base_root, contents={"tests/test_a.py": b""}),
        head_snapshot=SimpleNamespace(
            root=head_root,
            contents={"tests/test_a.py": b"", "tests/test_b.py": b""},
        ),
        selected_paths=("src/app.py",),
        policy_bundle=None,
        path_statuses={"src/app.py": "M"},
        exact_renames=(),
        claimed_context=None,
    )

    runner_api.run_immutable_scope_review(
        resolution,
        options=runner_api.ReviewOptions(no_tests=False),
        scope_evidence={"assurance_kind": "range_candidate"},
    )

    assert [runner_api._split_pytest_adapter_argv(argv["targeted-pytest-coverage"])[1] for argv in observed_argv] == [
        ("tests/test_a.py::test_a",),
        ("tests/test_a.py::test_a", "tests/test_b.py::test_b"),
    ]


def test_immutable_range_reconciles_removed_pytest_selector_before_execution(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    runner_api = _c14_runner()
    base_root = tmp_path / "base"
    head_root = tmp_path / "head"
    for root in (base_root, head_root):
        (root / "tests").mkdir(parents=True)
    (base_root / "tests/test_app.py").write_text("def test_visible():\n    assert True\n", encoding="utf-8")
    (head_root / "tests/test_app.py").write_text(
        "__test__ = False\n\ndef test_visible():\n    assert True\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        runner_api,
        "_prepare_capsule_runtime",
        lambda: (SimpleNamespace(identity="sha256:" + "a" * 64), ""),
    )
    monkeypatch.setattr(
        runner_api,
        "_run_capsule_snapshot",
        lambda *_args, **_kwargs: pytest.fail("removed selector must fail closed before analyzer execution"),
    )
    resolution = SimpleNamespace(
        base_snapshot=SimpleNamespace(root=base_root, contents={"tests/test_app.py": b""}),
        head_snapshot=SimpleNamespace(root=head_root, contents={"tests/test_app.py": b""}),
        policy_bundle=None,
        path_statuses={"tests/test_app.py": "M"},
        exact_renames=(),
        claimed_context=None,
    )

    report = runner_api.run_immutable_scope_review(
        resolution,
        options=runner_api.ReviewOptions(no_tests=False),
        scope_evidence={"assurance_kind": "range_preview"},
    )

    assert report.assurance_status == "UNKNOWN"
    assert {item["diagnostic"] for item in report.analyzer_evidence} == {"uncollected_changed_test"}


def test_marketplace_capsule_failure_never_falls_back_to_host_analyzers(monkeypatch: MonkeyPatch) -> None:
    runner_api = _c14_runner()
    monkeypatch.setattr(runner_api, "_prepare_capsule_runtime", lambda: (None, "unsupported_controller_platform"))
    monkeypatch.setattr(runner_api, "_is_development_source_checkout", lambda: False, raising=False)
    monkeypatch.setattr(
        runner_api,
        "run_review",
        lambda *_args, **_kwargs: pytest.fail("marketplace review must not use host analyzers"),
    )

    report = runner_api.run_capsule_review([Path("src/app.py")], no_tests=True)

    assert report.schema_version == "1.6"
    assert report.assurance_status == "UNKNOWN"
    assert report.ci_exit_code == 1


def test_capsule_runtime_loads_the_packaged_signed_lock_before_materialization(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    runner_api = _c14_runner()
    from specfact_code_review.run import toolchain

    captured: dict[str, object] = {}
    monkeypatch.setattr(runner_api.platform, "system", lambda: "Linux")
    monkeypatch.setattr(runner_api.platform, "machine", lambda: "x86_64")
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_CAPSULE_CACHE", str(tmp_path / "cache"))

    def materialize(lock: dict[str, object], **kwargs: object) -> SimpleNamespace:
        captured["lock"] = lock
        captured["environment_id"] = kwargs["environment_id"]
        return SimpleNamespace(status="UNKNOWN", reason="stop_after_lock")

    monkeypatch.setattr(toolchain, "materialize_capsule", materialize)

    runtime, reason = runner_api._prepare_capsule_runtime()

    assert runtime is None
    assert reason == "stop_after_lock"
    assert isinstance(captured["lock"], dict)
    assert captured["lock"]["schema"] == "toolchain-lock-schema-1"
    assert captured["environment_id"] == runner_api._capsule_environment_id()


def test_protected_pr_candidate_payload_is_reconstructed_from_verified_git_bytes(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    runner_api = _c14_runner()
    repo_root = tmp_path / "repo"
    package_root = repo_root / "packages/specfact-code-review"
    runner_file = package_root / "src/specfact_code_review/run/runner.py"
    runner_file.parent.mkdir(parents=True)
    runner_file.write_text("VALUE = 'committed'\n", encoding="utf-8")
    (runner_file.parents[1] / "__init__.py").write_text("", encoding="utf-8")
    (package_root / "module-package.yaml").write_text(
        "name: nold-ai/specfact-code-review\nversion: 0.49.4\n",
        encoding="utf-8",
    )
    git_env = runner_api._candidate_git_environment()
    subprocess.run(["git", "init", "-q", str(repo_root)], check=True, env=git_env)
    subprocess.run(["git", "-C", str(repo_root), "config", "user.name", "C14 Test"], check=True, env=git_env)
    subprocess.run(
        ["git", "-C", str(repo_root), "config", "user.email", "c14@example.invalid"],
        check=True,
        env=git_env,
    )
    subprocess.run(["git", "-C", str(repo_root), "add", "."], check=True, env=git_env)
    subprocess.run(["git", "-C", str(repo_root), "commit", "-qm", "candidate"], check=True, env=git_env)
    commit_sha = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        env=git_env,
    ).stdout.strip()
    monkeypatch.setattr(runner_api, "__file__", str(runner_file))
    candidate_env = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_REPOSITORY": "nold-ai/specfact-cli-modules",
        "GITHUB_EVENT_NAME": "pull_request",
        "GITHUB_SHA": commit_sha,
        "GITHUB_WORKFLOW": "PR Orchestrator",
        "GITHUB_WORKFLOW_REF": "nold-ai/specfact-cli-modules/.github/workflows/pr-orchestrator.yml@refs/pull/418/merge",
        "GITHUB_RUN_ID": "1234",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_JOB": "exact-core-compatibility",
    }
    for name, value in candidate_env.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "poison.git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "poison-worktree"))

    selected = runner_api._protected_candidate_payload()

    try:
        assert selected.reason == ""
        assert selected.payload.status == "PASS"
        assert selected.payload.identity.loader_origin == "verified-candidate"
        assert selected.payload.identity.artifact_verification_result is False
        assert selected.staged_source is not None
        staged_runner = Path(selected.staged_source.name) / "specfact_code_review/run/runner.py"
        assert staged_runner.read_text(encoding="utf-8") == "VALUE = 'committed'\n"
    finally:
        if selected.staged_source is not None:
            selected.staged_source.cleanup()


def test_github_candidate_context_failure_never_uses_stale_official_payload(monkeypatch: MonkeyPatch) -> None:
    runner_api = _c14_runner()
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REPOSITORY", "nold-ai/specfact-cli-modules")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    monkeypatch.setattr(
        runner_api,
        "_official_installed_payload",
        lambda: pytest.fail("protected workflow must not fall back to an installed release"),
    )

    selected = runner_api._selected_module_payload()

    assert selected.payload is None
    assert selected.reason == "untrusted_candidate_workflow_context"


def test_source_checkout_legacy_scope_uses_bounded_host_compatibility(monkeypatch: MonkeyPatch) -> None:
    runner_api = _c14_runner()
    expected = ReviewReport(run_id="dev-host", score=100, findings=[], summary="complete")
    monkeypatch.setattr(runner_api, "_prepare_capsule_runtime", lambda: (None, "unsupported_controller_platform"))
    monkeypatch.setattr(runner_api, "_is_development_source_checkout", lambda: True, raising=False)
    monkeypatch.setattr(runner_api, "run_review", lambda *_args, **_kwargs: expected)

    assert runner_api.run_capsule_review([Path("src/app.py")], no_tests=True) is expected


def test_source_checkout_legacy_scope_explicitly_opts_into_linux_cache_miss_compatibility(
    monkeypatch: MonkeyPatch,
) -> None:
    runner_api = _c14_runner()
    expected = ReviewReport(run_id="dev-host", score=100, findings=[], summary="complete")
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_DEV_HOST_COMPAT", "1")
    monkeypatch.setattr(
        runner_api,
        "_prepare_capsule_runtime",
        lambda: (None, "oci_acquisition_failed:verified cache entry is missing"),
    )
    monkeypatch.setattr(runner_api, "_is_development_source_checkout", lambda: True, raising=False)
    monkeypatch.setattr(runner_api, "run_review", lambda *_args, **_kwargs: expected)

    assert runner_api.run_capsule_review([Path("src/app.py")], no_tests=True) is expected


def test_source_checkout_linux_cache_miss_without_opt_in_fails_closed(monkeypatch: MonkeyPatch) -> None:
    runner_api = _c14_runner()
    monkeypatch.delenv("SPECFACT_CODE_REVIEW_DEV_HOST_COMPAT", raising=False)
    monkeypatch.setattr(
        runner_api,
        "_prepare_capsule_runtime",
        lambda: (None, "oci_acquisition_failed:verified cache entry is missing"),
    )
    monkeypatch.setattr(runner_api, "_is_development_source_checkout", lambda: True, raising=False)
    monkeypatch.setattr(
        runner_api,
        "run_review",
        lambda *_args, **_kwargs: pytest.fail("Linux cache miss must be explicit opt-in for legacy source scope"),
    )

    report = runner_api.run_capsule_review([Path("src/app.py")], no_tests=True)

    assert report.assurance_status == "UNKNOWN"


def test_immutable_scope_never_uses_source_checkout_host_compatibility(monkeypatch: MonkeyPatch) -> None:
    runner_api = _c14_runner()
    monkeypatch.setattr(runner_api, "_prepare_capsule_runtime", lambda: (None, "unsupported_controller_platform"))
    monkeypatch.setattr(runner_api, "_is_development_source_checkout", lambda: True, raising=False)
    monkeypatch.setattr(
        runner_api,
        "run_review",
        lambda *_args, **_kwargs: pytest.fail("immutable scope must never use host analyzers"),
    )

    report = runner_api.run_immutable_scope_review(
        SimpleNamespace(base_snapshot=object(), head_snapshot=object()),
        options=runner_api.ReviewOptions(no_tests=True),
        scope_evidence={"assurance_kind": "pr_range"},
    )

    assert report.schema_version == "1.6"
    assert report.assurance_status == "UNKNOWN"
    assert report.ci_exit_code == 1


def test_immutable_range_classifies_introduced_findings_with_existing_differential_contract(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    base_root = tmp_path / "base"
    head_root = tmp_path / "head"
    (base_root / "src").mkdir(parents=True)
    (head_root / "src").mkdir(parents=True)
    (base_root / "src/app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (head_root / "src/app.py").write_text("VALUE = eval('1')\n", encoding="utf-8")
    base_evidence = _synthetic_complete_profile_evidence(runner_api)
    head_evidence = _synthetic_complete_profile_evidence(runner_api)
    head_evidence["ruff"]["evidence_outcome"] = "FAIL"
    introduced = ReviewFinding(
        category="security",
        severity="error",
        tool="ruff",
        rule="S307",
        file="src/app.py",
        line=1,
        message="Use of eval detected",
        fixable=False,
    )
    resolution = SimpleNamespace(
        base_snapshot=SimpleNamespace(root=base_root, contents={"src/app.py": b"VALUE = 1\n"}),
        head_snapshot=SimpleNamespace(root=head_root, contents={"src/app.py": b"VALUE = eval('1')\n"}),
        exact_renames=(),
        path_statuses={"src/app.py": "M"},
    )

    evidence, findings = runner_api._classify_range_findings(
        resolution,
        runner_api.CapsuleSnapshotResult(base_evidence, {}),
        runner_api.CapsuleSnapshotResult(head_evidence, {"ruff": [introduced]}),
    )

    assert evidence["ruff"]["evidence_outcome"] == "FAIL"
    assert evidence["ruff"]["differential_counts"] == {
        "fixed": 0,
        "introduced": 1,
        "unchanged": 0,
        "unknown": 0,
    }
    assert findings["ruff"][0].differential_state == "introduced"


def test_immutable_range_blocks_introduced_suppression_even_when_analyzers_report_no_findings(
    tmp_path: Path,
) -> None:
    runner_api = _c14_runner()
    base_root = tmp_path / "base"
    head_root = tmp_path / "head"
    (base_root / "src").mkdir(parents=True)
    (head_root / "src").mkdir(parents=True)
    base_source = b"import os\n"
    head_source = b"import os  # noqa: F401\n"
    (base_root / "src/app.py").write_bytes(base_source)
    (head_root / "src/app.py").write_bytes(head_source)
    resolution = SimpleNamespace(
        base_snapshot=SimpleNamespace(root=base_root, contents={"src/app.py": base_source}),
        head_snapshot=SimpleNamespace(root=head_root, contents={"src/app.py": head_source}),
        exact_renames=(),
        path_statuses={"src/app.py": "M"},
    )

    evidence, findings = runner_api._classify_range_findings(
        resolution,
        runner_api.CapsuleSnapshotResult(_synthetic_complete_profile_evidence(runner_api), {}),
        runner_api.CapsuleSnapshotResult(_synthetic_complete_profile_evidence(runner_api), {}),
    )

    assert evidence["ruff"]["evidence_outcome"] == "FAIL"
    assert evidence["ruff"]["diagnostic"] == "introduced_inline_suppression"
    assert findings["ruff"][0].rule == "introduced_inline_suppression"
    assert findings["ruff"][0].differential_state == "introduced"
    assert findings["ruff"][0].is_blocking() is True


def test_immutable_range_preserves_fixed_findings_without_blocking(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    base_root = tmp_path / "base"
    head_root = tmp_path / "head"
    (base_root / "src").mkdir(parents=True)
    (head_root / "src").mkdir(parents=True)
    (base_root / "src/app.py").write_text("VALUE = eval('1')\n", encoding="utf-8")
    (head_root / "src/app.py").write_text("VALUE = 1\n", encoding="utf-8")
    base_evidence = _synthetic_complete_profile_evidence(runner_api)
    head_evidence = _synthetic_complete_profile_evidence(runner_api)
    base_evidence["ruff"]["evidence_outcome"] = "FAIL"
    fixed = ReviewFinding(
        category="security",
        severity="error",
        tool="ruff",
        rule="S307",
        file="src/app.py",
        line=1,
        message="Use of eval detected",
        fixable=False,
    )
    resolution = SimpleNamespace(
        base_snapshot=SimpleNamespace(root=base_root, contents={"src/app.py": b"VALUE = eval('1')\n"}),
        head_snapshot=SimpleNamespace(root=head_root, contents={"src/app.py": b"VALUE = 1\n"}),
        exact_renames=(),
        path_statuses={"src/app.py": "M"},
    )

    evidence, findings = runner_api._classify_range_findings(
        resolution,
        runner_api.CapsuleSnapshotResult(base_evidence, {"ruff": [fixed]}),
        runner_api.CapsuleSnapshotResult(head_evidence, {}),
    )

    assert evidence["ruff"]["evidence_outcome"] == "PASS"
    assert findings["ruff"][0].differential_state == "fixed"
    assert findings["ruff"][0].status == "fixed"
    assert findings["ruff"][0].is_blocking() is False


def test_run_review_merges_findings_from_all_runners(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [_finding(tool="ruff", rule="E501")])
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_radon", lambda files: [_finding(tool="radon", rule="CC13")]
    )
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_semgrep",
        lambda files: [_finding(tool="semgrep", rule="cross-layer-call", category="architecture")],
    )
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_semgrep_bugs",
        lambda files: [_finding(tool="semgrep", rule="specfact-bugs-eval-exec", category="security")],
    )
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_ai_bloat",
        lambda files: [
            _finding(tool="ast", rule="ai-bloat.redundant-intermediate", category="ai_bloat", severity="info")
        ],
    )
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_ast_clean_code",
        lambda files: [_finding(tool="ast", rule="dry.duplicate-function-shape", category="dry")],
    )
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_basedpyright",
        lambda files: [_finding(tool="basedpyright", rule="reportArgumentType", category="type_safety")],
    )
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_pylint",
        lambda files: [_finding(tool="pylint", rule="W0702", category="architecture")],
    )
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_contract_check",
        lambda files, **_: [_finding(tool="contract_runner", rule="MISSING_ICONTRACT", category="contracts")],
    )
    monkeypatch.setattr(
        "specfact_code_review.run.runner._evaluate_tdd_gate",
        lambda files: (
            [_finding(tool="pytest", rule="TEST_COVERAGE_LOW", category="testing")],
            {"packages/specfact-code-review/src/specfact_code_review/run/scorer.py": 65.0},
        ),
    )

    report = run_review([Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")])

    assert [finding.tool for finding in report.findings] == [
        "ruff",
        "radon",
        "semgrep",
        "semgrep",
        "ast",
        "ast",
        "basedpyright",
        "pylint",
        "contract_runner",
        "pytest",
    ]


def test_run_review_simplify_focus_keeps_only_simplification_queue(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [_finding(tool="ruff", rule="E501")])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_ai_bloat",
        lambda files: [_simplification_finding(category="ai_bloat")],
    )
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_ast_clean_code",
        lambda files: [
            _simplification_finding(category="dry"),
            _simplification_finding(category="kiss", confidence="medium"),
            _finding(tool="ast", rule="solid.mixed-dependency-role", category="solid"),
        ],
    )
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review(
        [Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")],
        no_tests=True,
        focus="simplify",
    )

    assert [(finding.category, finding.confidence) for finding in report.findings] == [
        ("ai_bloat", "high"),
        ("dry", "high"),
    ]
    assert report.schema_version == "1.3"
    assert report.overall_verdict == "PASS"


def test_run_review_simplify_enforce_fails_only_safe_mechanical_recommendations(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_ai_bloat",
        lambda files: [
            _simplification_finding(category="ai_bloat", guidance_kind="safe_mechanical"),
            _simplification_finding(category="ai_bloat", guidance_kind="needs_tests"),
            _simplification_finding(category="ai_bloat", guidance_kind="preserve"),
        ],
    )
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review(
        [Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")],
        no_tests=True,
        focus="simplify",
        review_mode="enforce",
    )

    assert report.schema_version == "1.3"
    assert report.overall_verdict == "FAIL"
    assert report.ci_exit_code == 1
    assert report.simplification_summary is not None
    assert report.simplification_summary.blocking_simplification_count == 1
    assert report.cleanup_forecast is not None
    assert report.cleanup_forecast.by_guidance_kind["safe_mechanical"].count == 1
    assert report.cleanup_forecast.by_guidance_kind["needs_tests"].count == 1
    assert report.cleanup_forecast.by_guidance_kind["preserve"].count == 1
    assert report.cleanup_forecast.ai_bloat_index.weighted_bloat_points_per_kloc >= 0.0


def test_run_review_simplify_forecast_counts_loc_and_weighted_bloat(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    source = Path("src/example.py")
    source.parent.mkdir(parents=True)
    source.write_text(
        "def one() -> int:\n"
        "    value = 1\n"
        "    return value\n"
        "\n"
        "# ignored comment\n"
        "def two() -> bool:\n"
        "    if True:\n"
        "        return True\n"
        "    return False\n",
        encoding="utf-8",
    )
    test_file = Path("tests/test_example.py")
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_example() -> None:\n    assert True\n", encoding="utf-8")
    safe = _simplification_finding(category="ai_bloat", guidance_kind="safe_mechanical")
    needs_tests = _simplification_finding(category="ai_bloat", guidance_kind="needs_tests")
    design = _simplification_finding(category="ai_bloat", guidance_kind="design_judgment")
    preserve = _simplification_finding(category="ai_bloat", guidance_kind="preserve")
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [safe, needs_tests])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [design, preserve])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review([source, test_file], no_tests=True, focus="simplify")

    assert report.cleanup_forecast is not None
    assert report.cleanup_forecast.reviewed_loc.production == 7
    assert report.cleanup_forecast.reviewed_loc.tests == 2
    assert report.cleanup_forecast.estimated_deletion_lines.low == 3
    assert report.cleanup_forecast.estimated_deletion_lines.expected == 6
    assert report.cleanup_forecast.estimated_deletion_lines.high == 9
    assert report.cleanup_forecast.ai_bloat_index.findings_per_kloc == pytest.approx(444.444, abs=0.001)
    assert report.cleanup_forecast.ai_bloat_index.weighted_bloat_points_per_kloc == pytest.approx(205.556, abs=0.001)
    assert report.cleanup_forecast.ai_bloat_index.cleanup_yield_loc_per_kloc == pytest.approx(666.667, abs=0.001)


def test_run_review_simplify_enforce_passes_design_and_preserve_guidance(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_ai_bloat",
        lambda files: [
            _simplification_finding(category="ai_bloat", guidance_kind="design_judgment"),
            _simplification_finding(category="ai_bloat", guidance_kind="preserve"),
        ],
    )
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review(
        [Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")],
        no_tests=True,
        focus="simplify",
        review_mode="enforce",
    )

    assert report.overall_verdict == "PASS"
    assert report.simplification_summary is not None
    assert report.simplification_summary.blocking_simplification_count == 0


def test_preserve_detection_covers_contract_public_protocol_cli_compat_and_load_bearing(tmp_path: Path) -> None:
    source = tmp_path / "api.py"
    source_text = (
        "from typing import Protocol\n"
        "import typer\n"
        "from abc import ABC, abstractmethod\n"
        "\n"
        "__all__ = ['exported']\n"
        "app = typer.Typer()\n"
        "\n"
        "@icontract.require(lambda value: value > 0)\n"
        "def contracted(value: int) -> int:\n"
        "    return value\n"
        "\n"
        "def exported() -> None:\n"
        "    return None\n"
        "\n"
        "class Handler(Protocol):\n"
        "    def handle(self, payload: str) -> str: ...\n"
        "\n"
        "class BaseHandler(ABC):\n"
        "    @abstractmethod\n"
        "    def abstract_handle(self, payload: str) -> str:\n"
        "        raise NotImplementedError\n"
        "\n"
        "    def concrete_helper(self, payload: str) -> str:\n"
        "        result = payload.strip()\n"
        "        return result\n"
        "\n"
        "@app.command()\n"
        "def cli_main() -> None:\n"
        "    return None\n"
        "\n"
        "# specfact: preserve(compat)\n"
        "def shim() -> None:\n"
        "    return None\n"
    )
    source.write_text(source_text, encoding="utf-8")

    def line_containing(text: str) -> int:
        return next(index for index, line in enumerate(source_text.splitlines(), start=1) if text in line)

    finding_lines = {
        "contract_lambda": line_containing("return value"),
        "public_api": line_containing("return None"),
        "protocol_member": line_containing("def handle"),
        "cli_callback": line_containing("def cli_main"),
        "compat_shim": line_containing("def shim"),
    }

    for expected_reason, line in finding_lines.items():
        finding = _simplification_finding(category="ai_bloat", guidance_kind="safe_mechanical").model_copy(
            update={"file": str(source), "line": line}
        )
        reasons = _preserve_reasons_for_finding(finding, load_bearing=False)
        assert expected_reason in {reason.reason for reason in reasons}

    abstract_finding = _simplification_finding(category="ai_bloat", guidance_kind="safe_mechanical").model_copy(
        update={"file": str(source), "line": line_containing("raise NotImplementedError")}
    )
    abstract_reasons = _preserve_reasons_for_finding(abstract_finding, load_bearing=False)
    assert "protocol_member" in {reason.reason for reason in abstract_reasons}

    concrete_finding = _simplification_finding(category="ai_bloat", guidance_kind="safe_mechanical").model_copy(
        update={"file": str(source), "line": line_containing("return result")}
    )
    concrete_reasons = _preserve_reasons_for_finding(concrete_finding, load_bearing=False)
    assert "protocol_member" not in {reason.reason for reason in concrete_reasons}

    load_bearing_finding = _simplification_finding(category="ai_bloat", guidance_kind="safe_mechanical").model_copy(
        update={"file": str(source), "line": line_containing("def exported")}
    )
    reasons = _preserve_reasons_for_finding(load_bearing_finding, load_bearing=True)
    assert "load_bearing" in {reason.reason for reason in reasons}


def test_preserve_detection_treats_docstring_only_protocol_method_as_stub(tmp_path: Path) -> None:
    source = tmp_path / "api.py"
    source_text = (
        "from typing import Protocol\n"
        "\n"
        "class Handler(Protocol):\n"
        "    def handle(self, payload: str) -> str:\n"
        '        """Handle the payload."""\n'
    )
    source.write_text(source_text, encoding="utf-8")

    finding = _simplification_finding(category="ai_bloat", guidance_kind="safe_mechanical").model_copy(
        update={"file": str(source), "line": 4}
    )
    reasons = _preserve_reasons_for_finding(finding, load_bearing=False)

    assert "protocol_member" in {reason.reason for reason in reasons}


def test_preserve_detection_reloads_source_after_file_mutation(tmp_path: Path) -> None:
    source = tmp_path / "api.py"
    source.write_text(
        "from typing import Protocol\n\nclass Handler(Protocol):\n    def handle(self, payload: str) -> str: ...\n",
        encoding="utf-8",
    )
    finding = _simplification_finding(category="ai_bloat", guidance_kind="safe_mechanical").model_copy(
        update={"file": str(source), "line": 4}
    )
    reasons = _preserve_reasons_for_finding(finding, load_bearing=False)
    assert "protocol_member" in {reason.reason for reason in reasons}

    source.write_text(
        "def helper(payload: str) -> str:\n    result = payload.strip()\n    return result\n",
        encoding="utf-8",
    )
    changed_finding = finding.model_copy(update={"line": 3})

    changed_reasons = _preserve_reasons_for_finding(changed_finding, load_bearing=False)

    assert "protocol_member" not in {reason.reason for reason in changed_reasons}


def test_run_review_simplify_focus_preserves_tool_errors(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_ai_bloat",
        lambda files: [
            ReviewFinding(
                category="tool_error",
                severity="error",
                tool="ast",
                rule="tool_error",
                file="packages/specfact-code-review/src/specfact_code_review/run/scorer.py",
                line=1,
                message="Unable to parse Python source.",
                fixable=False,
            ),
        ],
    )
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review(
        [Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")],
        no_tests=True,
        focus="simplify",
    )

    assert [finding.category for finding in report.findings] == ["tool_error"]
    assert report.overall_verdict == "FAIL"


def test_run_review_simplify_focus_excludes_partial_metadata_clean_code_findings(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_ast_clean_code",
        lambda files: [
            ReviewFinding(
                category="dry",
                severity="warning",
                tool="ast",
                rule="dry.duplicate-intent",
                file="packages/specfact-code-review/src/specfact_code_review/run/scorer.py",
                line=10,
                message="Partial metadata must not enter simplify focus.",
                fixable=False,
                confidence="high",
            ),
        ],
    )
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review(
        [Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")],
        no_tests=True,
        focus="simplify",
    )

    assert report.findings == []


def test_run_review_suppresses_cli_wrapper_noise_for_windows_style_paths(monkeypatch: MonkeyPatch) -> None:
    finding = ReviewFinding(
        category="style",
        severity="warning",
        tool="pylint",
        rule="R0914",
        file="packages\\specfact-code-review\\src\\specfact_code_review\\review\\commands.py",
        line=95,
        message="Too many local variables (24/20)",
        fixable=False,
    )
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [finding])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review(
        [Path("packages/specfact-code-review/src/specfact_code_review/review/commands.py")], no_tests=True
    )

    assert report.findings == []


def test_run_review_keeps_r0902_for_non_dataclass_in_mixed_file(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "mixed.py"
    source.write_text(
        "from dataclasses import dataclass\n"
        "\n"
        "@dataclass\n"
        "class Payload:\n"
        "    value: str\n"
        "\n"
        "class Stateful:\n"
        "    pass\n",
        encoding="utf-8",
    )
    finding = ReviewFinding(
        category="style",
        severity="warning",
        tool="pylint",
        rule="R0902",
        file=str(source),
        line=7,
        message="Too many instance attributes (9/7)",
        fixable=False,
    )
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [finding])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review([source], no_tests=True)

    assert [finding.rule for finding in report.findings] == ["R0902"]


def test_run_review_suppresses_r0902_for_dataclass_target(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "payload.py"
    source.write_text(
        "from dataclasses import dataclass\n\n@dataclass\nclass Payload:\n    value: str\n",
        encoding="utf-8",
    )
    finding = ReviewFinding(
        category="style",
        severity="warning",
        tool="pylint",
        rule="R0902",
        file=str(source),
        line=4,
        message="Too many instance attributes (9/7)",
        fixable=False,
    )
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [finding])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review([source], no_tests=True)

    assert report.findings == []


def test_run_review_rejects_unknown_override_key() -> None:
    try:
        run_review([], unknown=True)
    except TypeError as exc:
        assert "unknown" in str(exc)
    else:
        raise AssertionError("run_review accepted an unknown override")


def test_run_review_rejects_invalid_override_type() -> None:
    try:
        run_review([], no_tests="yes")
    except TypeError as exc:
        assert "no_tests" in str(exc)
    else:
        raise AssertionError("run_review accepted an invalid boolean override")


def test_run_tdd_gate_reports_missing_test_file() -> None:
    findings = run_tdd_gate([Path("packages/specfact-code-review/src/specfact_code_review/rules/commands.py")])

    assert len(findings) == 1
    assert findings[0].category == "testing"
    assert findings[0].severity == "error"
    assert findings[0].rule == "TEST_FILE_MISSING"


def test_run_review_skips_tdd_gate_when_no_tests_is_true(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr(
        "specfact_code_review.run.runner._evaluate_tdd_gate",
        lambda files: (_ for _ in ()).throw(AssertionError("_evaluate_tdd_gate should not be called")),
    )

    report = run_review(
        [Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")],
        no_tests=True,
    )

    assert report.findings == []


def test_run_review_returns_review_report(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr(
        "specfact_code_review.run.runner._evaluate_tdd_gate",
        lambda files: ([], {"packages/specfact-code-review/src/specfact_code_review/run/scorer.py": 95.0}),
    )

    report = run_review([Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")])

    assert isinstance(report, ReviewReport)
    assert report.summary


def test_run_review_suppresses_known_test_noise_by_default(monkeypatch: MonkeyPatch) -> None:
    noisy_findings = [
        ReviewFinding(
            category="contracts",
            severity="warning",
            tool="contract_runner",
            rule="MISSING_ICONTRACT",
            file="tests/unit/specfact_code_review/run/test_commands.py",
            line=10,
            message="test noise",
            fixable=False,
        ),
        ReviewFinding(
            category="style",
            severity="warning",
            tool="pylint",
            rule="W0212",
            file="tests/unit/specfact_code_review/run/test_commands.py",
            line=11,
            message="protected helper access",
            fixable=False,
        ),
        ReviewFinding(
            category="style",
            severity="warning",
            tool="ruff",
            rule="F821",
            file="tests/unit/specfact_code_review/run/test_commands.py",
            line=12,
            message="real test issue",
            fixable=False,
        ),
    ]
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: noisy_findings[2:])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: noisy_findings[1:2])
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_contract_check",
        lambda files, **_: noisy_findings[:1],
    )
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review([Path("tests/unit/specfact_code_review/run/test_commands.py")], no_tests=True)

    assert [finding.rule for finding in report.findings] == ["F821"]


def test_run_review_can_include_known_test_noise(monkeypatch: MonkeyPatch) -> None:
    noisy_findings = [
        ReviewFinding(
            category="contracts",
            severity="warning",
            tool="contract_runner",
            rule="MISSING_ICONTRACT",
            file="tests/unit/specfact_code_review/run/test_commands.py",
            line=10,
            message="test noise",
            fixable=False,
        ),
        ReviewFinding(
            category="style",
            severity="warning",
            tool="pylint",
            rule="W0212",
            file="tests/unit/specfact_code_review/run/test_commands.py",
            line=11,
            message="protected helper access",
            fixable=False,
        ),
    ]
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: noisy_findings[1:])
    monkeypatch.setattr(
        "specfact_code_review.run.runner.run_contract_check",
        lambda files, **_: noisy_findings[:1],
    )
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review(
        [Path("tests/unit/specfact_code_review/run/test_commands.py")],
        no_tests=True,
        include_noise=True,
    )

    assert [finding.rule for finding in report.findings] == ["W0212", "MISSING_ICONTRACT"]


def test_run_review_emits_advisory_checklist_finding_in_pr_mode(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_PR_MODE", "true")
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_PR_TITLE", "Expand code review coverage")
    monkeypatch.setenv(
        "SPECFACT_CODE_REVIEW_PR_BODY", "Adds new review runners without documenting the clean-code rationale."
    )

    report = run_review([Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")], no_tests=True)

    assert [finding.rule for finding in report.findings] == ["clean-code.pr-checklist-missing-rationale"]
    assert report.findings[0].severity == "info"
    assert report.overall_verdict == "PASS"


def test_run_review_requires_explicit_pr_mode_token_for_clean_code_reasoning(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_PR_MODE", "true")
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_PR_TITLE", "Expand code review coverage")
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_PR_BODY", "We are renaming helper functions for clarity.")
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_PR_PROPOSAL", "")

    report = run_review([Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")], no_tests=True)

    assert [finding.rule for finding in report.findings] == ["clean-code.pr-checklist-missing-rationale"]


def test_run_review_suppresses_global_duplicate_code_noise_by_default(monkeypatch: MonkeyPatch) -> None:
    duplicate_code_finding = ReviewFinding(
        category="style",
        severity="warning",
        tool="pylint",
        rule="R0801",
        file="scripts/link_dev_module.py",
        line=1,
        message="Similar lines in 2 files",
        fixable=False,
    )
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [duplicate_code_finding])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review([Path("scripts/link_dev_module.py")], no_tests=True)

    assert report.findings == []


def test_pytest_targets_collapses_only_specific_subdirectories(tmp_path: Path) -> None:
    run_tests = tmp_path / "tests/unit/specfact_code_review/run"
    run_tests.mkdir(parents=True)
    first = run_tests / "test_commands.py"
    second = run_tests / "test_runner.py"
    first.write_text("def test_one():\n    assert True\n", encoding="utf-8")
    second.write_text("def test_two():\n    assert True\n", encoding="utf-8")

    assert _pytest_targets([first.relative_to(tmp_path), second.relative_to(tmp_path)]) == [
        Path("tests/unit/specfact_code_review/run")
    ]


def test_pytest_targets_keeps_files_when_common_root_is_too_broad(tmp_path: Path) -> None:
    run_tests = tmp_path / "tests/unit/specfact_code_review/run"
    review_tests = tmp_path / "tests/unit/specfact_code_review/review"
    run_tests.mkdir(parents=True)
    review_tests.mkdir(parents=True)
    first = run_tests / "test_commands.py"
    second = review_tests / "test_commands.py"
    first.write_text("def test_one():\n    assert True\n", encoding="utf-8")
    second.write_text("def test_two():\n    assert True\n", encoding="utf-8")

    assert _pytest_targets([first.relative_to(tmp_path), second.relative_to(tmp_path)]) == [
        Path("tests/unit/specfact_code_review/run/test_commands.py"),
        Path("tests/unit/specfact_code_review/review/test_commands.py"),
    ]


def test_run_review_can_include_global_duplicate_code_noise(monkeypatch: MonkeyPatch) -> None:
    duplicate_code_finding = ReviewFinding(
        category="style",
        severity="warning",
        tool="pylint",
        rule="R0801",
        file="scripts/link_dev_module.py",
        line=1,
        message="Similar lines in 2 files",
        fixable=False,
    )
    monkeypatch.setattr("specfact_code_review.run.runner.run_ruff", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_radon", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_semgrep_bugs", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ai_bloat", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_ast_clean_code", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_basedpyright", lambda files: [])
    monkeypatch.setattr("specfact_code_review.run.runner.run_pylint", lambda files: [duplicate_code_finding])
    monkeypatch.setattr("specfact_code_review.run.runner.run_contract_check", lambda files, **_: [])
    monkeypatch.setattr("specfact_code_review.run.runner._evaluate_tdd_gate", lambda files: ([], None))

    report = run_review([Path("scripts/link_dev_module.py")], no_tests=True, include_noise=True)

    assert [finding.rule for finding in report.findings] == ["R0801"]


def test_run_tdd_gate_warns_when_coverage_is_below_threshold(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    source_file = Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")
    coverage_payload = {
        "files": {
            str(source_file): {
                "summary": {
                    "percent_covered": 65.0,
                }
            }
        }
    }

    def _fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        coverage_arg = next(arg for arg in command if arg.startswith("--cov-report=json:"))
        coverage_path = Path(coverage_arg.split(":", 1)[1])
        coverage_path.write_text(json.dumps(coverage_payload), encoding="utf-8")
        Path(command[3]).write_text(
            json.dumps([{"nodeid": "tests/test_scorer.py::test_placeholder", "phase": "call", "passed": True}]),
            encoding="utf-8",
        )
        junit_arg = next(arg for arg in command if arg.startswith("--junitxml="))
        Path(junit_arg.split("=", 1)[1]).write_text(
            '<testsuites><testsuite><testcase classname="tests.test_scorer" name="test_placeholder" />'
            "</testsuite></testsuites>",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tests/unit/specfact_code_review/run").mkdir(parents=True)
    (tmp_path / "tests/unit/specfact_code_review/run/test_scorer.py").write_text(
        "def test_placeholder():\n    assert True\n"
    )

    findings = run_tdd_gate([source_file])

    assert len(findings) == 1
    assert findings[0].rule == "TEST_COVERAGE_LOW"
    assert findings[0].severity == "warning"


def test_run_tdd_gate_maps_absolute_source_paths(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    source_file = tmp_path / "packages/specfact-code-review/src/specfact_code_review/review/commands.py"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("def command() -> None:\n    pass\n", encoding="utf-8")

    findings = run_tdd_gate([source_file.resolve()])

    assert len(findings) == 1
    assert findings[0].rule == "TEST_FILE_MISSING"
    assert findings[0].file == str(source_file.resolve())


def test_run_tdd_gate_returns_no_finding_for_passing_tests_with_sufficient_coverage(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    source_file = Path("packages/specfact-code-review/src/specfact_code_review/run/scorer.py")
    coverage_payload = {
        "files": {
            str(source_file): {
                "summary": {
                    "percent_covered": 85.0,
                }
            }
        }
    }

    def _fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        coverage_arg = next(arg for arg in command if arg.startswith("--cov-report=json:"))
        coverage_path = Path(coverage_arg.split(":", 1)[1])
        coverage_path.write_text(json.dumps(coverage_payload), encoding="utf-8")
        Path(command[3]).write_text(
            json.dumps([{"nodeid": "tests/test_scorer.py::test_placeholder", "phase": "call", "passed": True}]),
            encoding="utf-8",
        )
        junit_arg = next(arg for arg in command if arg.startswith("--junitxml="))
        Path(junit_arg.split("=", 1)[1]).write_text(
            '<testsuites><testsuite><testcase classname="tests.test_scorer" name="test_placeholder" />'
            "</testsuite></testsuites>",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tests/unit/specfact_code_review/run").mkdir(parents=True)
    (tmp_path / "tests/unit/specfact_code_review/run/test_scorer.py").write_text(
        "def test_placeholder():\n    assert True\n"
    )

    findings = run_tdd_gate([source_file])

    assert findings == []


def test_coverage_findings_skips_package_initializers_without_coverage_data() -> None:
    source_file = Path("packages/specfact-code-review/src/specfact_code_review/review/__init__.py")

    findings, coverage_by_source = _coverage_findings([source_file], {"files": {}})

    assert not findings
    assert coverage_by_source == {}


def test_coverage_findings_skips_package_initializers_omitted_from_coverage_reports() -> None:
    """``packages/**/__init__.py`` is omitted in coverage config; JSON has no per-file summary."""
    source_file = Path("packages/specfact-code-review/src/specfact_code_review/tools/__init__.py")

    findings, coverage_by_source = _coverage_findings([source_file], {"files": {}})

    assert not findings
    assert coverage_by_source == {}


def test_complete_coverage_requires_nonempty_package_initializer_record(tmp_path: Path) -> None:
    source_file = tmp_path / "packages/example/src/example/__init__.py"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("VERSION = '1.0'\n", encoding="utf-8")

    findings, coverage_by_source = _coverage_findings(
        [source_file],
        {"files": {}},
        allow_project_omitted_initializers=False,
    )

    assert coverage_by_source is None
    assert [finding.category for finding in findings] == ["tool_error"]


def test_run_pytest_with_coverage_disables_global_fail_under(monkeypatch: MonkeyPatch) -> None:
    recorded: dict[str, object] = {}

    def _fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        recorded["command"] = command
        recorded["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    _run_pytest_with_coverage([Path("tests/unit/specfact_code_review/run/test_commands.py")])

    command = recorded["command"]
    assert isinstance(command, list)
    assert command[0] == _pytest_python_executable()
    assert command[1] == "-c"
    assert "import specfact_code_review" in command[2]
    assert "--import-mode=importlib" in command
    assert "--cov-fail-under=0" in command


def test_run_complete_pytest_inventory_preserves_exact_node_ids(monkeypatch: MonkeyPatch) -> None:
    runner_api = _c14_runner()
    recorded: dict[str, object] = {}
    selectors = (
        "tests/test_a.py::test_a",
        "tests/nonconventional/test_b.py::TestB::test_b",
    )

    def _fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        recorded["command"] = command
        recorded["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    _result, coverage_path, observer_path, junit_path = runner_api._run_pytest_inventory_with_coverage(selectors)

    try:
        command = cast(list[str], recorded["command"])
        assert command[-2:] == list(selectors)
        assert command[command.index("--cov") + 1] == "/opt/specfact/snapshot"
    finally:
        coverage_path.unlink(missing_ok=True)
        observer_path.unlink(missing_ok=True)
        junit_path.unlink(missing_ok=True)


def test_run_complete_pytest_inventory_applies_sealed_policy_argv(monkeypatch: MonkeyPatch) -> None:
    runner_api = _c14_runner()
    recorded: dict[str, object] = {}
    policy_argv = (
        "-c",
        "/opt/specfact/config/1/pytest.ini",
        "--rootdir",
        "/opt/specfact/snapshot",
        "--cov-config",
        "/opt/specfact/config/2/coveragerc",
    )

    def _fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        recorded["command"] = command
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    _result, coverage_path, observer_path, junit_path = runner_api._run_pytest_inventory_with_coverage(
        ("tests/test_a.py::test_a",),
        policy_argv=policy_argv,
    )

    try:
        command = cast(list[str], recorded["command"])
        assert command[4 : 4 + len(policy_argv)] == list(policy_argv)
        assert command[-1] == "tests/test_a.py::test_a"
    finally:
        coverage_path.unlink(missing_ok=True)
        observer_path.unlink(missing_ok=True)
        junit_path.unlink(missing_ok=True)


def test_pytest_python_executable_uses_current_interpreter() -> None:
    assert _pytest_python_executable() == sys.executable


def test_pytest_targets_collapse_multi_file_batch_to_common_test_directory() -> None:
    test_files = [
        Path("tests/unit/specfact_code_review/run/test_commands.py"),
        Path("tests/unit/specfact_code_review/run/test_runner.py"),
    ]

    assert _pytest_targets(test_files) == [Path("tests/unit/specfact_code_review/run")]


def test_run_pytest_with_coverage_propagates_pythonpath(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    recorded: dict[str, object] = {}
    bundle_root = tmp_path / "bundle-src"
    bundle_root.mkdir()
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    monkeypatch.chdir(workspace_root)
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "existing"))
    monkeypatch.setattr(sys, "path", [str(bundle_root), "", str(tmp_path / "missing")])

    def _fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        recorded["command"] = command
        recorded["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    _run_pytest_with_coverage([Path("tests/unit/specfact_code_review/run/test_commands.py")])

    kwargs = recorded["kwargs"]
    assert isinstance(kwargs, dict)
    env = kwargs["env"]
    assert isinstance(env, dict)
    assert env["PYTHONPATH"].split(os.pathsep) == [
        str(Path("packages/specfact-code-review/src").resolve()),
        str(workspace_root.resolve()),
        str(tmp_path / "existing"),
        str(bundle_root.resolve()),
    ]


def _c14_runner() -> Any:
    from specfact_code_review.run import runner

    return runner


def test_default_pr_range_analyzer_profile_has_closed_membership() -> None:
    runner_api = _c14_runner()
    profile = runner_api.default_pr_range_profile()

    assert profile.required_ids == (
        "ruff",
        "radon",
        "semgrep-clean",
        "ai-bloat-ast",
        "ast-clean-code",
        "basedpyright",
        "pylint",
        "contracts",
    )
    assert profile.conditional_ids == ("semgrep-bugs", "targeted-pytest-coverage")
    assert profile.id == "pr-range-v1"


def test_complete_capsule_report_carries_activated_suppression_catalog_digest() -> None:
    runner_api = _c14_runner()
    resource, _checkpoint = runner_api.differential.load_suppression_catalog_and_checkpoint()

    report = runner_api._capsule_report(
        _synthetic_complete_profile_evidence(runner_api),
        {},
        options=runner_api.ReviewOptions(no_tests=True),
        scope_evidence={"assurance_kind": "pr_range"},
    )

    assert report.assurance_status == "PASS"
    assert report.suppression_catalog_digest == resource.digest


def test_suppression_catalog_activation_drift_forces_unknown_report(monkeypatch: MonkeyPatch) -> None:
    runner_api = _c14_runner()
    monkeypatch.setattr(
        runner_api.differential,
        "activate_packaged_suppression_catalog",
        lambda: SimpleNamespace(
            status="UNKNOWN",
            profile_activated=False,
            digest=None,
            reason="suppression_catalog_identity_mismatch",
        ),
        raising=False,
    )

    report = runner_api._capsule_report(
        _synthetic_complete_profile_evidence(runner_api),
        {},
        options=runner_api.ReviewOptions(no_tests=True),
        scope_evidence={"assurance_kind": "pr_range"},
    )

    assert report.assurance_status == "UNKNOWN"
    assert report.has_unknown_required_evidence is True
    assert report.suppression_catalog_digest is None


def test_immutable_review_analyzes_only_selected_snapshot_python_files(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    runner_api = _c14_runner()
    base_root = tmp_path / "base"
    head_root = tmp_path / "head"
    observed: list[list[str]] = []
    monkeypatch.setattr(runner_api, "_prepare_capsule_runtime", lambda **_kwargs: (SimpleNamespace(), ""))

    def run_snapshot(*_args: object, **kwargs: object) -> Any:
        snapshot_root = cast(Path, kwargs["snapshot_root"])
        files = cast(list[Path], kwargs["files"])
        observed.append([path.relative_to(snapshot_root).as_posix() for path in files])
        return runner_api.CapsuleSnapshotResult(_synthetic_complete_profile_evidence(runner_api), {})

    monkeypatch.setattr(runner_api, "_run_capsule_snapshot", run_snapshot)
    monkeypatch.setattr(runner_api, "_classify_range_findings", lambda *_args: ({}, {}))
    monkeypatch.setattr(
        runner_api,
        "_capsule_report",
        lambda *_args, **_kwargs: ReviewReport(run_id="selected", score=100, summary="complete"),
    )
    contents = {
        "src/changed.py": b"VALUE = 1\n",
        "src/unrelated_blocker.py": b"VALUE = eval('1')\n",
    }
    resolution = SimpleNamespace(
        base_snapshot=SimpleNamespace(root=base_root, contents=contents),
        head_snapshot=SimpleNamespace(root=head_root, contents=contents),
        selected_paths=("src/changed.py",),
        policy_bundle=None,
        claimed_context=None,
    )

    runner_api.run_immutable_scope_review(
        resolution, options=runner_api.ReviewOptions(no_tests=True), scope_evidence={"assurance_kind": "pr_range"}
    )

    assert observed == [["src/changed.py"], ["src/changed.py"]]


def test_report_exposes_mandatory_analyzer_coverage() -> None:
    runner_api = _c14_runner()
    report = runner_api.aggregate_profile_evidence(_synthetic_complete_profile_evidence(runner_api))

    assert {member.id for member in report.analyzer_evidence} == set(runner_api.default_pr_range_profile().all_ids)
    assert all(member.execution_state in {"ran", "not_applicable"} for member in report.analyzer_evidence)


def test_analyzer_identity_mismatch_is_unknown() -> None:
    runner_api = _c14_runner()
    evidence = _synthetic_complete_profile_evidence(runner_api)
    evidence["ruff"]["version"] = "0.0.0"

    report = runner_api.aggregate_profile_evidence(evidence)

    assert report.assurance_status == "UNKNOWN"
    assert report.has_unknown_required_evidence is True


def test_required_analyzer_infrastructure_error_is_unknown_not_fail() -> None:
    runner_api = _c14_runner()
    evidence = _synthetic_complete_profile_evidence(runner_api)
    evidence["contracts"] = {"execution_state": "error", "evidence_outcome": "UNKNOWN", "diagnostic": "timeout"}

    report = runner_api.aggregate_profile_evidence(evidence)

    assert report.assurance_status == "UNKNOWN"
    assert report.overall_verdict == "FAIL"
    assert report.has_unknown_required_evidence is True


def test_active_conditional_analyzer_infrastructure_error_is_unknown() -> None:
    runner_api = _c14_runner()
    evidence = _synthetic_complete_profile_evidence(runner_api)
    evidence["semgrep-bugs"] = {
        "execution_state": "error",
        "evidence_outcome": "UNKNOWN",
        "version": runner_api._C14_ANALYZER_VERSIONS["semgrep-bugs"],
        "diagnostic": "launch failed",
    }

    report = runner_api.aggregate_profile_evidence(evidence)

    assert report.assurance_status == "UNKNOWN"
    assert report.has_unknown_required_evidence is True


def test_generated_analyzer_inputs_use_typed_provenance(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    context = _synthetic_snapshot_context(runner_api)

    assert {identity.kind for identity in context.inputs} <= {
        "git_blob",
        "signed_module_payload",
        "generated_projection",
        "builtin_mode",
    }
    assert all(identity.digest.startswith("sha256:") for identity in context.inputs)


def test_head_config_cannot_suppress_introduced_finding() -> None:
    runner_api = _c14_runner()
    result = runner_api.apply_target_policy(
        target_policy={"ruff": {"ignore": []}},
        candidate_policy={"ruff": {"ignore": ["F401"]}},
        base_findings=(),
        head_findings=({"rule": "F401", "path": "src/app.py", "blocking": True},),
    )

    assert result.assurance_status == "UNKNOWN"
    assert result.reason == "candidate_policy_change"


def test_mandatory_analyzer_eligible_and_invoked_input_manifests_match(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    context = _synthetic_snapshot_context(runner_api)
    result = runner_api.validate_invocation_manifests(context)

    assert result.status == "PASS"
    assert all(member.eligible_digest == member.invoked_digest for member in result.members)


def test_invocation_manifest_digest_mismatch_is_unknown() -> None:
    runner_api = _c14_runner()
    eligible = _synthetic_snapshot_context(runner_api).inputs
    invoked = list(eligible)
    invoked[0] = runner_api.GeneratedInputIdentity(invoked[0].kind, "sha256:" + "f" * 64)
    context = runner_api.SyntheticSnapshotContext(eligible, invoked_inputs=tuple(invoked))

    result = runner_api.validate_invocation_manifests(context)

    assert result.status == "UNKNOWN"
    assert result.members[0].eligible_digest != result.members[0].invoked_digest


def test_incomplete_invocation_manifest_is_unknown() -> None:
    runner_api = _c14_runner()
    incomplete = (runner_api.GeneratedInputIdentity("git_blob", "sha256:" + "a" * 64),)
    context = runner_api.SyntheticSnapshotContext(incomplete, incomplete)

    result = runner_api.validate_invocation_manifests(context)

    assert result.status == "UNKNOWN"
    assert {member.id for member in result.members} == set(runner_api.default_pr_range_profile().all_ids)


def test_range_uses_authorized_base_tip_policy_when_target_advanced() -> None:
    runner_api = _c14_runner()
    result = runner_api.select_range_policy(
        merge_base="1" * 40,
        target_tip="2" * 40,
        head="3" * 40,
        context_target_tip="2" * 40,
    )

    assert result.source_baseline == "1" * 40
    assert result.policy_commit == "2" * 40
    assert result.applies_to == ("merge_base", "head")


def _suite_policy(**updates: object) -> dict[str, object]:
    policy: dict[str, object] = {
        "version": "9.0.3",
        "testpaths": ["tests"],
        "python_files": ["test_*.py", "*_test.py"],
        "python_classes": ["Test*"],
        "python_functions": ["test_*"],
        "addopts": [],
        "config": {},
    }
    policy.update(updates)
    return policy


def test_pr_range_collects_complete_pytest_suite_for_production_change(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_a.py").write_text("def test_a(): pass\n", encoding="utf-8")
    (tmp_path / "tests/test_b.py").write_text("def test_b(): pass\n", encoding="utf-8")

    plan = runner_api.plan_complete_pytest_suite(
        snapshot_root=tmp_path,
        policy=_suite_policy(),
        changed_paths=("src/app.py",),
    )

    assert plan.selectors == ("tests/test_a.py::test_a", "tests/test_b.py::test_b")
    assert plan.source_heuristics_used is False


def test_complete_suite_includes_multiple_nonconventional_related_tests(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/behavior_test.py").write_text("def test_behavior(): pass\n", encoding="utf-8")
    (tmp_path / "tests/test_unrelated_name.py").write_text("def test_other(): pass\n", encoding="utf-8")

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/widget.py",))

    assert len(plan.selectors) == 2


def test_targeted_pytest_runs_complete_suite_in_test_only_range(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_a.py").write_text("def test_a(): pass\n", encoding="utf-8")
    (tmp_path / "tests/test_b.py").write_text("def test_b(): pass\n", encoding="utf-8")

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("tests/test_a.py",))

    assert plan.selectors == ("tests/test_a.py::test_a", "tests/test_b.py::test_b")


def test_targeted_pytest_reconciles_removed_baseline_selectors() -> None:
    runner_api = _c14_runner()
    result = runner_api.reconcile_pytest_inventories(base=("tests/test_a.py::test_a",), head=(), rename_facts={})

    assert result.status == "UNKNOWN"
    assert result.reason == "removed_selector"


def test_targeted_pytest_delete_only_production_runs_complete_head_suite(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_a.py").write_text("def test_a(): pass\n", encoding="utf-8")

    plan = runner_api.plan_complete_pytest_suite(
        tmp_path, _suite_policy(), changed_paths=("src/deleted.py",), deleted_paths=("src/deleted.py",)
    )

    assert plan.selectors == ("tests/test_a.py::test_a",)


def test_changed_test_not_collected_by_sealed_policy_is_unknown(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_new.py").write_text("", encoding="utf-8")

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("tests/test_new.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "uncollected_changed_test"


def test_unchanged_test_candidate_without_selector_is_unknown(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_active.py").write_text("def test_active(): pass\n", encoding="utf-8")
    (tmp_path / "tests/test_placeholder.py").write_text("", encoding="utf-8")

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "uncollected_test_candidate"


def test_complete_suite_collects_inherited_unittest_selector(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    test_file = tmp_path / "tests/test_inherited.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "import unittest\n\n"
        "class SharedCase(unittest.TestCase):\n"
        "    def test_inherited(self):\n"
        "        pass\n\n"
        "class TestChild(SharedCase):\n"
        "    pass\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "PASS"
    assert plan.selectors == (
        "tests/test_inherited.py::SharedCase::test_inherited",
        "tests/test_inherited.py::TestChild::test_inherited",
    )


def test_complete_suite_uses_unittest_loader_method_prefix_independently_of_pytest_policy(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    test_file = tmp_path / "tests/test_mixed.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "import unittest\n\n"
        "def check_smoke():\n"
        "    pass\n\n"
        "class RegressionCase(unittest.TestCase):\n"
        "    def test_failure(self):\n"
        "        pass\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(
        tmp_path,
        _suite_policy(python_functions=["check_*"]),
        changed_paths=("src/app.py",),
    )

    assert plan.status == "PASS"
    assert plan.selectors == (
        "tests/test_mixed.py::check_smoke",
        "tests/test_mixed.py::RegressionCase::test_failure",
    )


def test_complete_suite_rejects_unittest_execution_override(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    test_file = tmp_path / "tests/test_override.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "import unittest\n\n"
        "class TestBypass(unittest.TestCase):\n"
        "    def run(self, result=None):\n"
        "        return result\n\n"
        "    def test_failure(self):\n"
        "        assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "unittest_execution_override"


def test_complete_suite_collects_imported_pytest_and_unittest_objects(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "__init__.py").write_text("", encoding="utf-8")
    (tests_root / "support.py").write_text(
        "import unittest\n\n"
        "class SharedCase(unittest.TestCase):\n"
        "    def test_inherited(self):\n"
        "        pass\n\n"
        "def test_imported():\n"
        "    pass\n",
        encoding="utf-8",
    )
    (tests_root / "test_imported.py").write_text(
        "from tests.support import SharedCase, test_imported\n\n"
        "def test_smoke():\n"
        "    pass\n\n"
        "class TestChild(SharedCase):\n"
        "    pass\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "PASS"
    assert plan.selectors == (
        "tests/test_imported.py::SharedCase::test_inherited",
        "tests/test_imported.py::test_imported",
        "tests/test_imported.py::test_smoke",
        "tests/test_imported.py::TestChild::test_inherited",
    )


def test_complete_suite_resolves_imported_class_sibling_base(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "__init__.py").write_text("", encoding="utf-8")
    (tests_root / "support.py").write_text(
        "class Base:\n    def test_inherited(self):\n        assert False\n\nclass TestChild(Base):\n    pass\n",
        encoding="utf-8",
    )
    (tests_root / "test_case.py").write_text(
        "from tests.support import TestChild\n\ndef test_smoke():\n    pass\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "PASS"
    assert plan.selectors == (
        "tests/test_case.py::TestChild::test_inherited",
        "tests/test_case.py::test_smoke",
    )


def test_complete_suite_resolves_transitive_imported_test_definition(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "__init__.py").write_text("", encoding="utf-8")
    (tests_root / "leaf.py").write_text("def test_imported():\n    assert False\n", encoding="utf-8")
    (tests_root / "support.py").write_text("from tests.leaf import test_imported\n", encoding="utf-8")
    (tests_root / "test_case.py").write_text(
        "from tests.support import test_imported\n\ndef test_smoke():\n    pass\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "PASS"
    assert plan.selectors == (
        "tests/test_case.py::test_imported",
        "tests/test_case.py::test_smoke",
    )


def test_complete_suite_rejects_dynamically_exported_imported_test(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "__init__.py").write_text("", encoding="utf-8")
    (tests_root / "support.py").write_text(
        "def failing():\n"
        "    assert False\n\n"
        "def __getattr__(name):\n"
        "    if name == 'test_failure':\n"
        "        return failing\n"
        "    raise AttributeError(name)\n",
        encoding="utf-8",
    )
    (tests_root / "test_case.py").write_text(
        "from tests.support import test_failure\n\ndef test_smoke():\n    pass\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "dynamic_imported_test_export_unsupported"


def test_complete_suite_resolves_imported_test_through_project_pythonpath(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    support_root = tests_root / "support"
    support_root.mkdir(parents=True)
    (tmp_path / "shared.py").write_text("def helper():\n    pass\n", encoding="utf-8")
    (support_root / "shared.py").write_text("def test_failure():\n    assert False\n", encoding="utf-8")
    (tests_root / "test_case.py").write_text(
        "from shared import test_failure\n\ndef test_smoke():\n    pass\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(
        tmp_path,
        _suite_policy(config={"pythonpath": ["tests/support"]}),
        changed_paths=("src/app.py",),
    )

    assert plan.status == "PASS"
    assert plan.selectors == (
        "tests/test_case.py::test_failure",
        "tests/test_case.py::test_smoke",
    )


def test_complete_suite_resolves_imported_test_through_project_runtime(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    runtime_root = tmp_path / "project-runtime"
    site_packages = runtime_root / "site-packages"
    tests_root.mkdir()
    site_packages.mkdir(parents=True)
    (site_packages / "runtime_dep.py").write_text("def test_failure():\n    assert False\n", encoding="utf-8")
    (tests_root / "test_case.py").write_text(
        "from runtime_dep import test_failure\n\ndef test_smoke():\n    pass\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(
        tmp_path,
        _suite_policy(),
        changed_paths=("src/app.py",),
        project_runtime_root=runtime_root,
    )

    assert plan.status == "PASS"
    assert plan.selectors == (
        "tests/test_case.py::test_failure",
        "tests/test_case.py::test_smoke",
    )


def test_complete_suite_rejects_test_body_replacing_decorator(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    test_file = tmp_path / "tests/test_decorated.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "def replace(function):\n"
        "    del function\n"
        "    def passing():\n"
        "        pass\n"
        "    return passing\n\n"
        "@replace\n"
        "def test_failure():\n"
        "    assert False\n\n"
        "def test_smoke():\n"
        "    pass\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "test_execution_decorator_unsupported"


def test_complete_suite_rejects_rebound_pytest_decorator_alias(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    test_file = tmp_path / "tests/test_decorated.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "from pytest import mark\n\n"
        "class FakeMark:\n"
        "    def __getattr__(self, name):\n"
        "        del name\n"
        "        def replace(function):\n"
        "            del function\n"
        "            return lambda: None\n"
        "        return replace\n\n"
        "mark = FakeMark()\n\n"
        "@mark.bodyless\n"
        "def test_failure():\n"
        "    assert False\n\n"
        "def test_smoke():\n"
        "    pass\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "test_execution_decorator_unsupported"


def test_complete_suite_rejects_mutated_pytest_mark_attribute(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    test_file = tmp_path / "tests/test_decorated.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "import pytest\n\n"
        "class FakeMark:\n"
        "    def __getattr__(self, name):\n"
        "        del name\n"
        "        def replace(function):\n"
        "            del function\n"
        "            return lambda: None\n"
        "        return replace\n\n"
        "pytest.mark = FakeMark()\n\n"
        "@pytest.mark.bodyless\n"
        "def test_failure():\n"
        "    assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "test_execution_decorator_unsupported"


def test_complete_suite_rejects_pytest_mark_mutated_through_setattr(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    test_file = tmp_path / "tests/test_decorated.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "import pytest\n\n"
        "class FakeMark:\n"
        "    def __getattr__(self, name):\n"
        "        del name\n"
        "        def replace(function):\n"
        "            del function\n"
        "            return lambda: None\n"
        "        return replace\n\n"
        "setattr(pytest, 'mark', FakeMark())\n\n"
        "@pytest.mark.bodyless\n"
        "def test_failure():\n"
        "    assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan == runner_api.PytestSuitePlan(
        selectors=("tests/test_decorated.py::test_failure",),
        source_heuristics_used=False,
        status="UNKNOWN",
        reason="test_execution_decorator_unsupported",
    )


def test_complete_suite_accepts_stable_pytest_decorator_alias(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    test_file = tmp_path / "tests/test_decorated.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "from pytest import mark\n\n"
        "@mark.parametrize('value', [1, 2])\n"
        "def test_value(value):\n"
        "    assert value in {1, 2}\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "PASS"
    assert plan.selectors == ("tests/test_decorated.py::test_value",)


def test_complete_suite_rejects_imported_test_body_replacing_decorator(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "__init__.py").write_text("", encoding="utf-8")
    (tests_root / "support.py").write_text(
        "def replace(function):\n"
        "    del function\n"
        "    return lambda: None\n\n"
        "@replace\n"
        "def test_failure():\n"
        "    assert False\n",
        encoding="utf-8",
    )
    (tests_root / "test_case.py").write_text(
        "from tests.support import test_failure\n\ndef test_smoke():\n    pass\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "test_execution_decorator_unsupported"


def test_complete_suite_fails_closed_for_wildcard_imported_tests(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "__init__.py").write_text("", encoding="utf-8")
    (tests_root / "support.py").write_text(
        '__all__ = ["test_imported"]\n\ndef test_imported():\n    assert False\n',
        encoding="utf-8",
    )
    (tests_root / "test_imported.py").write_text(
        "from tests.support import *\n\ndef test_smoke():\n    pass\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "wildcard_import_unsupported"


def test_complete_suite_rejects_repository_pytest_execution_hook(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "conftest.py").write_text(
        "def pytest_pyfunc_call(pyfuncitem):\n    del pyfuncitem\n    return True\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text("def test_failure():\n    assert False\n", encoding="utf-8")

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "pytest_plugin_capability_unsupported"


def test_complete_suite_rejects_conditional_repository_pytest_execution_hook(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "conftest.py").write_text(
        "if True:\n    def pytest_pyfunc_call(pyfuncitem):\n        del pyfuncitem\n        return True\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text("def test_failure():\n    assert False\n", encoding="utf-8")

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan == runner_api.PytestSuitePlan(
        selectors=(),
        source_heuristics_used=False,
        status="UNKNOWN",
        reason="pytest_plugin_capability_unsupported",
    )


def test_complete_suite_rejects_conditional_imported_pytest_execution_hook(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "__init__.py").write_text("", encoding="utf-8")
    (tests_root / "support.py").write_text(
        "def pytest_pyfunc_call(pyfuncitem):\n    del pyfuncitem\n    return True\n",
        encoding="utf-8",
    )
    (tests_root / "conftest.py").write_text(
        "if True:\n    from tests.support import pytest_pyfunc_call\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text("def test_failure():\n    assert False\n", encoding="utf-8")

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan == runner_api.PytestSuitePlan(
        selectors=(),
        source_heuristics_used=False,
        status="UNKNOWN",
        reason="pytest_plugin_capability_unsupported",
    )


def test_complete_suite_rejects_repository_pytest_execution_hook_specname(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "conftest.py").write_text(
        "import pytest\n\n"
        '@pytest.hookimpl(specname="pytest_pyfunc_call")\n'
        "def forge_passing_call(pyfuncitem):\n"
        "    del pyfuncitem\n"
        "    return True\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text("def test_failure():\n    assert False\n", encoding="utf-8")

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "pytest_plugin_capability_unsupported"


def test_complete_suite_rejects_execution_shaping_autouse_fixture(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "conftest.py").write_text(
        "import pytest\n\n@pytest.fixture(autouse=True)\ndef bypass(request):\n    request.node.obj = lambda: None\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text("def test_failure():\n    assert False\n", encoding="utf-8")

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "pytest_plugin_capability_unsupported"


def test_complete_suite_rejects_test_module_autouse_fixture(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    test_file = tmp_path / "tests/test_failure.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "import pytest\n\n"
        "@pytest.fixture(autouse=True)\n"
        "def bypass(request):\n"
        "    request.node.obj = lambda: None\n\n"
        "def test_failure():\n"
        "    assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "pytest_plugin_capability_unsupported"


def test_complete_suite_rejects_requested_execution_shaping_fixture(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "conftest.py").write_text(
        "import pytest\n\n@pytest.fixture\ndef bypass(request):\n    request.node.obj = lambda **kwargs: None\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text(
        "def test_failure(bypass):\n    del bypass\n    assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "pytest_plugin_capability_unsupported"


def test_complete_suite_rejects_requested_fixture_registering_pytest_hook_plugin(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "conftest.py").write_text(
        "import pytest\n\n"
        "class BypassPlugin:\n"
        "    def pytest_pyfunc_call(self, pyfuncitem):\n"
        "        del pyfuncitem\n"
        "        return True\n\n"
        "@pytest.fixture\n"
        "def bypass(request):\n"
        "    request.config.pluginmanager.register(BypassPlugin())\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text(
        "def test_failure(bypass):\n    del bypass\n    assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan == runner_api.PytestSuitePlan(
        selectors=(),
        source_heuristics_used=False,
        status="UNKNOWN",
        reason="pytest_plugin_capability_unsupported",
    )


def test_complete_suite_rejects_requested_fixture_using_session_plugin_manager(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "conftest.py").write_text(
        "import pytest\n\n"
        "class BypassPlugin:\n"
        "    def pytest_pyfunc_call(self, pyfuncitem):\n"
        "        del pyfuncitem\n"
        "        return True\n\n"
        "@pytest.fixture\n"
        "def bypass(request):\n"
        "    request.session.config.pluginmanager.register(BypassPlugin())\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text(
        "def test_failure(bypass):\n    del bypass\n    assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan == runner_api.PytestSuitePlan(
        selectors=(),
        source_heuristics_used=False,
        status="UNKNOWN",
        reason="pytest_plugin_capability_unsupported",
    )


def test_complete_suite_rejects_requested_fixture_using_aliased_session_plugin_manager(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "conftest.py").write_text(
        "import pytest\n\n"
        "class BypassPlugin:\n"
        "    def pytest_pyfunc_call(self, pyfuncitem):\n"
        "        del pyfuncitem\n"
        "        return True\n\n"
        "@pytest.fixture\n"
        "def bypass(request):\n"
        "    session = request.session\n"
        "    session.config.pluginmanager.register(BypassPlugin())\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text(
        "def test_failure(bypass):\n    del bypass\n    assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan == runner_api.PytestSuitePlan(
        selectors=(),
        source_heuristics_used=False,
        status="UNKNOWN",
        reason="pytest_plugin_capability_unsupported",
    )


def test_complete_suite_rejects_requested_fixture_using_destructured_session_plugin_manager(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "conftest.py").write_text(
        "import pytest\n\n"
        "class BypassPlugin:\n"
        "    def pytest_pyfunc_call(self, pyfuncitem):\n"
        "        del pyfuncitem\n"
        "        return True\n\n"
        "@pytest.fixture\n"
        "def bypass(request):\n"
        "    session, = (request.session,)\n"
        "    session.config.pluginmanager.register(BypassPlugin())\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text(
        "def test_failure(bypass):\n    del bypass\n    assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan == runner_api.PytestSuitePlan(
        selectors=(),
        source_heuristics_used=False,
        status="UNKNOWN",
        reason="pytest_plugin_capability_unsupported",
    )


def test_complete_suite_rejects_requested_fixture_delegating_request_capability(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "conftest.py").write_text(
        "import pytest\n\n"
        "class BypassPlugin:\n"
        "    def pytest_pyfunc_call(self, pyfuncitem):\n"
        "        del pyfuncitem\n"
        "        return True\n\n"
        "def install_bypass(request):\n"
        "    request.config.pluginmanager.register(BypassPlugin())\n\n"
        "@pytest.fixture\n"
        "def bypass(request):\n"
        "    install_bypass(request)\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text(
        "def test_failure(bypass):\n    del bypass\n    assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan == runner_api.PytestSuitePlan(
        selectors=(),
        source_heuristics_used=False,
        status="UNKNOWN",
        reason="pytest_plugin_capability_unsupported",
    )


def test_complete_suite_rejects_requested_fixture_using_pytestconfig_plugin_manager(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "conftest.py").write_text(
        "import pytest\n\n"
        "class BypassPlugin:\n"
        "    def pytest_pyfunc_call(self, pyfuncitem):\n"
        "        del pyfuncitem\n"
        "        return True\n\n"
        "@pytest.fixture\n"
        "def bypass(pytestconfig):\n"
        "    pytestconfig.pluginmanager.register(BypassPlugin())\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text(
        "def test_failure(bypass):\n    del bypass\n    assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan == runner_api.PytestSuitePlan(
        selectors=(),
        source_heuristics_used=False,
        status="UNKNOWN",
        reason="pytest_plugin_capability_unsupported",
    )


def test_complete_suite_rejects_aliased_requested_execution_shaping_fixture(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "conftest.py").write_text(
        "import pytest\n\n"
        "@pytest.fixture\n"
        "def bypass(request):\n"
        "    node = request.node\n"
        "    node.obj = lambda **kwargs: None\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text(
        "def test_failure(bypass):\n    del bypass\n    assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "pytest_plugin_capability_unsupported"


def test_complete_suite_rejects_requested_fixture_replacing_runtest_dispatch(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "conftest.py").write_text(
        "import pytest\n\n@pytest.fixture\ndef bypass(request):\n    request.node.runtest = lambda: None\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text(
        "def test_failure(bypass):\n    del bypass\n    assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "pytest_plugin_capability_unsupported"


def test_complete_suite_rejects_requested_fixture_replacing_class_runtest_dispatch(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "conftest.py").write_text(
        "import pytest\n\n"
        "@pytest.fixture\n"
        "def bypass(request):\n"
        "    request.node.__class__.runtest = lambda self: None\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text(
        "def test_failure(bypass):\n    del bypass\n    assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "pytest_plugin_capability_unsupported"
    assert not plan.selectors
    assert plan.source_heuristics_used is False


def test_complete_suite_rejects_requested_fixture_replacing_cached_callable(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "conftest.py").write_text(
        "import pytest\n\n@pytest.fixture\ndef bypass(request):\n    request.node._obj = lambda **kwargs: None\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text(
        "def test_failure(bypass):\n    del bypass\n    assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "pytest_plugin_capability_unsupported"


def test_complete_suite_rejects_requested_fixture_rewriting_collected_callable_code(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "conftest.py").write_text(
        "import pytest\n\n"
        "@pytest.fixture\n"
        "def bypass(request):\n"
        "    request.node.obj.__code__ = (lambda **kwargs: None).__code__\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text(
        "def test_failure(bypass):\n    del bypass\n    assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "pytest_plugin_capability_unsupported"
    assert not plan.selectors


def test_complete_suite_rejects_requested_fixture_replacing_dispatch_through_namespace(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "conftest.py").write_text(
        "import pytest\n\n@pytest.fixture\ndef bypass(request):\n    request.node.__dict__['runtest'] = lambda: None\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text(
        "def test_failure(bypass):\n    del bypass\n    assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "pytest_plugin_capability_unsupported"


def test_complete_suite_rejects_requested_fixture_replacing_dispatch_through_namespace_alias(
    tmp_path: Path,
) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "conftest.py").write_text(
        "import pytest\n\n"
        "@pytest.fixture\n"
        "def bypass(request):\n"
        "    namespace = request.node.__dict__\n"
        "    namespace['runtest'] = lambda: None\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text(
        "def test_failure(bypass):\n    del bypass\n    assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "pytest_plugin_capability_unsupported"


def test_complete_suite_rejects_requested_fixture_using_qualified_setattr(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "conftest.py").write_text(
        "import pytest\n\n"
        "@pytest.fixture\n"
        "def bypass(request):\n"
        "    object.__setattr__(request.node, 'runtest', lambda: None)\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text(
        "def test_failure(bypass):\n    del bypass\n    assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "pytest_plugin_capability_unsupported"


def test_complete_suite_rejects_imported_execution_shaping_fixture(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "__init__.py").write_text("", encoding="utf-8")
    (tests_root / "support.py").write_text(
        "import pytest\n\n@pytest.fixture\ndef bypass(request):\n    request.node.runtest = lambda: None\n",
        encoding="utf-8",
    )
    (tests_root / "conftest.py").write_text("from tests.support import bypass\n", encoding="utf-8")
    (tests_root / "test_failure.py").write_text(
        "def test_failure(bypass):\n    del bypass\n    assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "pytest_plugin_capability_unsupported"


def test_complete_suite_rejects_conditionally_imported_execution_shaping_fixture(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "__init__.py").write_text("", encoding="utf-8")
    (tests_root / "support.py").write_text(
        "import pytest\n\n@pytest.fixture\ndef bypass(request):\n    request.node.runtest = lambda: None\n",
        encoding="utf-8",
    )
    (tests_root / "conftest.py").write_text(
        "if True:\n    from tests.support import bypass\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text(
        "def test_failure(bypass):\n    del bypass\n    assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "pytest_plugin_capability_unsupported"
    assert not plan.selectors
    assert plan.source_heuristics_used is False


def test_complete_suite_rejects_assigned_imported_execution_shaping_fixture(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "__init__.py").write_text("", encoding="utf-8")
    (tests_root / "support.py").write_text(
        "import pytest\n\n@pytest.fixture\ndef bypass(request):\n    request.node.runtest = lambda: None\n",
        encoding="utf-8",
    )
    (tests_root / "conftest.py").write_text(
        "from tests import support\n\nbypass = support.bypass\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text(
        "def test_failure(bypass):\n    del bypass\n    assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan == runner_api.PytestSuitePlan(
        selectors=(),
        source_heuristics_used=False,
        status="UNKNOWN",
        reason="pytest_plugin_capability_unsupported",
    )


def test_complete_suite_rejects_requested_fixture_delegating_item_mutation(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "conftest.py").write_text(
        "import pytest\n\n"
        "def mutate(node):\n"
        "    node.runtest = lambda: None\n\n"
        "@pytest.fixture\n"
        "def bypass(request):\n"
        "    mutate(request.node)\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text(
        "def test_failure(bypass):\n    del bypass\n    assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "pytest_plugin_capability_unsupported"


def test_complete_suite_rejects_unittest_method_dispatch_override(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    test_file = tmp_path / "tests/test_override.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "import unittest\n\n"
        "class TestBypass(unittest.TestCase):\n"
        "    def _callTestMethod(self, method):\n"
        "        del method\n\n"
        "    def test_failure(self):\n"
        "        assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "unittest_execution_override"


def test_complete_suite_rejects_dynamic_test_member_assignment(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    test_file = tmp_path / "tests/test_dynamic.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "def failing_function(self):\n"
        "    assert False\n\n"
        "class TestDynamic:\n"
        "    pass\n\n"
        "TestDynamic.test_failure = failing_function\n\n"
        "def test_smoke():\n"
        "    pass\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "dynamic_test_assignment_unsupported"


def test_complete_suite_rejects_assigned_pytest_hook_alias(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tmp_path / "conftest.py").write_text(
        "def bypass(pyfuncitem):\n    del pyfuncitem\n    return True\n\npytest_pyfunc_call = bypass\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text("def test_failure():\n    assert False\n", encoding="utf-8")

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "pytest_plugin_capability_unsupported"


def test_complete_suite_rejects_destructured_pytest_hook_alias(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tmp_path / "conftest.py").write_text(
        "def bypass(pyfuncitem):\n    del pyfuncitem\n    return True\n\npytest_pyfunc_call, = (bypass,)\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text("def test_failure():\n    assert False\n", encoding="utf-8")

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "pytest_plugin_capability_unsupported"


def test_complete_suite_rejects_named_expression_pytest_hook_alias(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tmp_path / "conftest.py").write_text(
        "def bypass(pyfuncitem):\n    del pyfuncitem\n    return True\n\n(pytest_pyfunc_call := bypass)\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text("def test_failure():\n    assert False\n", encoding="utf-8")

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "pytest_plugin_capability_unsupported"


@pytest.mark.parametrize(
    "declaration",
    [
        "(pytest_plugins := ['tests.evil'])\n",
        "if True:\n    pytest_plugins = ['tests.evil']\n",
    ],
    ids=["named-expression", "module-control-flow"],
)
def test_complete_suite_rejects_every_pytest_plugins_binding(tmp_path: Path, declaration: str) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "__init__.py").write_text("", encoding="utf-8")
    (tests_root / "evil.py").write_text(
        "def pytest_pyfunc_call(pyfuncitem):\n    del pyfuncitem\n    return True\n",
        encoding="utf-8",
    )
    (tests_root / "conftest.py").write_text(declaration, encoding="utf-8")
    (tests_root / "test_failure.py").write_text("def test_failure():\n    assert False\n", encoding="utf-8")

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "pytest_plugin_capability_unsupported"


def test_complete_suite_rejects_subscript_assigned_pytest_hook_alias(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tmp_path / "conftest.py").write_text(
        'def bypass(pyfuncitem):\n    del pyfuncitem\n    return True\n\nglobals()["pytest_pyfunc_call"] = bypass\n',
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text("def test_failure():\n    assert False\n", encoding="utf-8")

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "pytest_plugin_capability_unsupported"


def test_complete_suite_rejects_namespace_update_pytest_hook_alias(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tmp_path / "conftest.py").write_text(
        "def bypass(pyfuncitem):\n    del pyfuncitem\n    return True\n\nglobals().update(pytest_pyfunc_call=bypass)\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text("def test_failure():\n    assert False\n", encoding="utf-8")

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "pytest_plugin_capability_unsupported"


def test_complete_suite_rejects_aliased_namespace_update_pytest_hook(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tmp_path / "conftest.py").write_text(
        "def bypass(pyfuncitem):\n"
        "    del pyfuncitem\n"
        "    return True\n\n"
        "namespace = globals()\n"
        "namespace.update(pytest_pyfunc_call=bypass)\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text("def test_failure():\n    assert False\n", encoding="utf-8")

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "pytest_plugin_capability_unsupported"


def test_complete_suite_rejects_dynamic_module_attribute_pytest_hook(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tmp_path / "conftest.py").write_text(
        "def bypass(pyfuncitem):\n"
        "    del pyfuncitem\n"
        "    return True\n\n"
        "def __dir__():\n"
        "    return ['pytest_pyfunc_call']\n\n"
        "def __getattr__(name):\n"
        "    if name == 'pytest_pyfunc_call':\n"
        "        return bypass\n"
        "    raise AttributeError(name)\n",
        encoding="utf-8",
    )
    (tests_root / "test_failure.py").write_text("def test_failure():\n    assert False\n", encoding="utf-8")

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "pytest_plugin_capability_unsupported"


def test_complete_suite_rejects_module_test_callable_alias(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    test_file = tmp_path / "tests/test_dynamic.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "def failing_function():\n    assert False\n\ntest_failure = failing_function\n\ndef test_smoke():\n    pass\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "dynamic_test_assignment_unsupported"


def test_complete_suite_rejects_destructured_test_callable_alias(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    test_file = tmp_path / "tests/test_dynamic.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "def failing_function():\n"
        "    assert False\n\n"
        "test_failure, = (failing_function,)\n\n"
        "def test_smoke():\n"
        "    pass\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "dynamic_test_assignment_unsupported"


def test_complete_suite_rejects_named_expression_test_callable_alias(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    test_file = tmp_path / "tests/test_dynamic.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "def failing_function():\n"
        "    assert False\n\n"
        "(test_failure := failing_function)\n\n"
        "def test_smoke():\n"
        "    pass\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "dynamic_test_assignment_unsupported"


def test_complete_suite_rejects_test_binding_in_module_control_flow(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "__init__.py").write_text("", encoding="utf-8")
    (tests_root / "shared.py").write_text("def test_failure():\n    assert False\n", encoding="utf-8")
    (tests_root / "test_dynamic.py").write_text(
        "if True:\n    from .shared import test_failure\n\ndef test_smoke():\n    pass\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "dynamic_test_assignment_unsupported"


def test_complete_suite_rejects_test_method_in_class_control_flow(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    test_file = tmp_path / "tests/test_dynamic.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "class TestConditional:\n"
        "    if True:\n"
        "        def test_failure(self):\n"
        "            assert False\n\n"
        "def test_smoke():\n"
        "    pass\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "dynamic_test_assignment_unsupported"


def test_complete_suite_rejects_module_level_exec_test_generation(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    test_file = tmp_path / "tests/test_dynamic.py"
    test_file.parent.mkdir()
    test_file.write_text(
        'exec("def test_failure():\\n    assert False")\n\ndef test_smoke():\n    pass\n',
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "dynamic_test_assignment_unsupported"


def test_complete_suite_rejects_module_level_eval_compile_test_generation(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    test_file = tmp_path / "tests/test_dynamic.py"
    test_file.parent.mkdir()
    test_file.write_text(
        'eval(compile("def test_failure():\\n    assert False", "<dynamic>", "exec"))\n\ndef test_smoke():\n    pass\n',
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "dynamic_test_assignment_unsupported"


def test_complete_suite_rejects_subscript_injected_test_callable(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    test_file = tmp_path / "tests/test_dynamic.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "def failing_function():\n"
        "    assert False\n\n"
        "globals()['test_failure'] = failing_function\n\n"
        "def test_smoke():\n"
        "    pass\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "dynamic_test_assignment_unsupported"


def test_complete_suite_rejects_transitive_imported_class_base(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "__init__.py").write_text("", encoding="utf-8")
    (tests_root / "base.py").write_text(
        "class Base:\n    def test_inherited(self):\n        assert False\n",
        encoding="utf-8",
    )
    (tests_root / "shared.py").write_text(
        "from .base import Base\n\nclass TestChild(Base):\n    pass\n",
        encoding="utf-8",
    )
    (tests_root / "test_candidate.py").write_text(
        "from .shared import TestChild\n\ndef test_smoke():\n    pass\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "imported_test_base_unsupported"


def test_complete_suite_preserves_local_base_when_imported_module_reuses_name(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "__init__.py").write_text("", encoding="utf-8")
    (tests_root / "shared.py").write_text(
        "class Base:\n    pass\n\nclass TestImported(Base):\n    def test_imported(self):\n        pass\n",
        encoding="utf-8",
    )
    (tests_root / "test_collision.py").write_text(
        "from .shared import TestImported\n\n"
        "class Base:\n"
        "    def test_inherited(self):\n"
        "        assert False\n\n"
        "class TestLocal(Base):\n"
        "    pass\n\n"
        "def test_smoke():\n"
        "    pass\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "PASS"
    assert plan.selectors == (
        "tests/test_collision.py::TestImported::test_imported",
        "tests/test_collision.py::TestLocal::test_inherited",
        "tests/test_collision.py::test_smoke",
    )


def test_complete_suite_rejects_dynamic_test_class_factory(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    test_file = tmp_path / "tests/test_dynamic.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "def failing_function(self):\n"
        "    assert False\n\n"
        "TestDynamic = type(\n"
        "    'TestDynamic',\n"
        "    (),\n"
        "    {'__module__': __name__, 'test_failure': failing_function},\n"
        ")\n\n"
        "def test_smoke():\n"
        "    pass\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "dynamic_test_assignment_unsupported"


def test_complete_suite_rejects_unittest_attribute_dispatch_override(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    test_file = tmp_path / "tests/test_override.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "import unittest\n\n"
        "class TestBypass(unittest.TestCase):\n"
        "    def __getattribute__(self, name):\n"
        "        if name.startswith('test_'):\n"
        "            return lambda: None\n"
        "        return super().__getattribute__(name)\n\n"
        "    def test_failure(self):\n"
        "        assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "unittest_execution_override"


def test_complete_suite_rejects_native_pytest_attribute_dispatch_override(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    test_file = tmp_path / "tests/test_override.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "class TestBypass:\n"
        "    def __getattribute__(self, name):\n"
        "        if name == 'test_failure':\n"
        "            return lambda: None\n"
        "        return object.__getattribute__(self, name)\n\n"
        "    def test_failure(self):\n"
        "        assert False\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(tmp_path, _suite_policy(), changed_paths=("src/app.py",))

    assert plan.status == "UNKNOWN"
    assert plan.reason == "unittest_execution_override"


def test_config_free_pytest_policy_discovers_from_repository_root(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    unit = tmp_path / "tests/test_smoke.py"
    integration = tmp_path / "integration/test_outside.py"
    unit.parent.mkdir()
    integration.parent.mkdir()
    unit.write_text("def test_smoke():\n    pass\n", encoding="utf-8")
    integration.write_text("def test_outside():\n    assert False\n", encoding="utf-8")

    plan = runner_api.plan_complete_pytest_suite(
        tmp_path,
        runner_api._pytest_policy_values(None),
        changed_paths=("src/app.py",),
    )

    assert plan.status == "PASS"
    assert plan.selectors == (
        "integration/test_outside.py::test_outside",
        "tests/test_smoke.py::test_smoke",
    )


def test_complete_suite_matches_path_qualified_python_file_patterns(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    smoke = tmp_path / "tests/test_smoke.py"
    nested = tmp_path / "tests/unit/check_case.py"
    nested.parent.mkdir(parents=True)
    smoke.write_text("def test_smoke():\n    pass\n", encoding="utf-8")
    nested.write_text("def test_nested():\n    pass\n", encoding="utf-8")
    policy = _suite_policy(python_files=["test_*.py", "tests/**/check_*.py"])

    plan = runner_api.plan_complete_pytest_suite(tmp_path, policy, changed_paths=("src/app.py",))

    assert plan.status == "PASS"
    assert plan.selectors == (
        "tests/test_smoke.py::test_smoke",
        "tests/unit/check_case.py::test_nested",
    )


def test_empty_merge_base_input_class_is_not_applicable_for_that_side() -> None:
    runner_api = _c14_runner()
    result = runner_api.classify_snapshot_applicability(base_inputs=(), head_inputs=("src/new.py",))

    assert result.base == "NOT_APPLICABLE"
    assert result.head != "NOT_APPLICABLE"


def test_test_role_is_frozen_before_collection() -> None:
    runner_api = _c14_runner()
    role = runner_api.classify_pytest_input_role(
        "tests/unit/test_new.py",
        policy=_suite_policy(testpaths=["tests/unit"], python_files=["test_*.py"]),
    )

    assert role.kind == "test_candidate"
    assert role.inputs == ("path", "testpaths", "python_files", "pytest_version")


def test_test_shaped_path_outside_collection_roots_is_not_support() -> None:
    runner_api = _c14_runner()
    role = runner_api.classify_pytest_input_role(
        "integration/test_new.py",
        policy=_suite_policy(testpaths=["tests"], python_files=["test_*.py"]),
    )

    assert role.kind == "test_candidate_outside_root"


def test_previously_collected_test_file_becoming_empty_is_unknown() -> None:
    runner_api = _c14_runner()
    result = runner_api.reconcile_test_candidate(
        role="test_candidate", base_selectors=("tests/test_a.py::test_a",), head_selectors=()
    )

    assert result.status == "UNKNOWN"


def test_new_test_candidate_without_head_selectors_is_unknown() -> None:
    runner_api = _c14_runner()
    result = runner_api.reconcile_test_candidate(role="test_candidate", base_selectors=(), head_selectors=())

    assert result.status == "UNKNOWN"
    assert result.reason == "uncollected_test_candidate"


def test_candidate_test_file_disabled_by_dunder_test_is_unknown() -> None:
    runner_api = _c14_runner()
    result = runner_api.validate_pytest_item_controls(
        candidate_path="tests/test_a.py", namespace={"__test__": False}, collected=()
    )

    assert result.status == "UNKNOWN"
    assert result.reason == "pytest_item_control_unsupported"


def test_test_candidate_to_support_rename_is_unknown() -> None:
    runner_api = _c14_runner()
    result = runner_api.reconcile_test_roles(
        base={"tests/test_a.py": "test_candidate"},
        head={"tests/helper.py": "test_support"},
        rename_facts={"tests/test_a.py": "tests/helper.py"},
    )

    assert result.status == "UNKNOWN"


@pytest.mark.parametrize(
    ("pattern", "path", "expected"),
    [
        ("test_*.py", "/repo/tests/unit/test_a.py", True),
        ("tests/unit/test_*.py", "/repo/tests/unit/test_a.py", True),
        ("tests/**/test_*.py", "/repo/tests/unit/test_a.py", True),
        ("test_*.py", "/repo/tests/unit/helper.py", False),
    ],
    ids=["basename-match", "rooted-match", "recursive-match", "basename-miss"],
)
def test_pytest_input_role_uses_pinned_fnmatch_ex_for_path_patterns(pattern: str, path: str, expected: bool) -> None:
    runner_api = _c14_runner()

    assert runner_api.pytest_path_matches_pattern(Path(path), pattern, platform="linux") is expected


def test_pytest_projection_rebases_relative_paths_per_snapshot(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    policy = _suite_policy(config={"pythonpath": ["src"], "testpaths": ["tests"]})
    base = runner_api.project_pytest_policy(policy, snapshot_root=tmp_path / "base", output_root=tmp_path / "out-base")
    head = runner_api.project_pytest_policy(policy, snapshot_root=tmp_path / "head", output_root=tmp_path / "out-head")

    assert base.values["pythonpath"] == [str(tmp_path / "base/src")]
    assert head.values["pythonpath"] == [str(tmp_path / "head/src")]
    assert base.logical_policy_digest == head.logical_policy_digest


def test_pytest_projection_rejects_unbound_paths(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    result = runner_api.project_pytest_policy(
        _suite_policy(config={"pythonpath": ["../escape"]}), snapshot_root=tmp_path, output_root=tmp_path / "out"
    )

    assert result.status == "UNKNOWN"


def test_pytest_projection_redirects_all_writable_paths_to_private_roots(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    projection = runner_api.project_pytest_policy(
        _suite_policy(config={"cache_dir": ".cache", "log_file": "pytest.log"}),
        snapshot_root=tmp_path / "snapshot",
        output_root=tmp_path / "output",
    )

    assert all(str(value).startswith(str(tmp_path / "output")) for value in projection.writable_paths)
    assert all(not str(value).startswith(str(tmp_path / "snapshot")) for value in projection.writable_paths)


@pytest.mark.parametrize("option", ["-k", "-m", "--ignore", "--deselect", "--lf"])
def test_sealed_pytest_policy_rejects_selection_filters(option: str) -> None:
    runner_api = _c14_runner()
    result = runner_api.validate_pytest_selection_controls(_suite_policy(addopts=[option, "value"]))

    assert result.status == "UNKNOWN"


def test_sealed_pytest_policy_rejects_doctest_modules_collection() -> None:
    runner_api = _c14_runner()
    result = runner_api.validate_pytest_selection_controls(_suite_policy(addopts=["--doctest-modules"]))

    assert result.status == "UNKNOWN"
    assert result.reason == "pytest_selection_policy_unsupported"


def test_production_change_cannot_hide_failing_test_with_authorized_ignore() -> None:
    runner_api = _c14_runner()
    result = runner_api.validate_pytest_selection_controls(_suite_policy(addopts=["--ignore", "tests/test_fail.py"]))

    assert result.status == "UNKNOWN"


@pytest.mark.parametrize(
    "option",
    ["--lf", "--last-failed", "-x", "--maxfail=1", "--stepwise"],
    ids=["lf", "last-failed", "exit-first", "maxfail-one", "stepwise"],
)
def test_pytest_cache_and_short_circuit_controls_are_unknown(option: str) -> None:
    runner_api = _c14_runner()
    assert runner_api.validate_pytest_selection_controls(_suite_policy(addopts=[option])).status == "UNKNOWN"


@pytest.mark.parametrize(
    "option",
    [
        "--cache-clear",
        "--collect-only",
        "--cov=src",
        "--cov-fail-under=0",
        "--cov-report=term",
        "--exitfirst",
        "--ff",
        "--ignore-glob=tests/*",
        "--new-first",
        "--no-cov",
        "--noconftest",
        "--stepwise-skip",
        "-qx",
    ],
)
def test_pytest_all_collection_and_execution_overrides_are_unknown(option: str) -> None:
    runner_api = _c14_runner()

    assert runner_api.validate_pytest_selection_controls(_suite_policy(addopts=[option])).status == "UNKNOWN"


def test_pytest_selection_option_catalog_covers_pinned_help() -> None:
    runner_api = _c14_runner()
    catalog = runner_api.pytest_selection_option_catalog(version="9.0.3", pytest_cov_version="7.1.0")

    assert catalog.unclassified_help_options == ()
    assert set(catalog.options) == {
        "--cache-clear",
        "--collect-only",
        "--confcutdir",
        "--cov",
        "--cov-config",
        "--cov-fail-under",
        "--cov-report",
        "--deselect",
        "--doctest-modules",
        "--exitfirst",
        "--ff",
        "--ignore",
        "--ignore-glob",
        "--lf",
        "--last-failed",
        "--maxfail",
        "--new-first",
        "--no-cov",
        "--noconftest",
        "--override-ini",
        "--pyargs",
        "--rootdir",
        "--stepwise",
        "--stepwise-skip",
        "-c",
        "-k",
        "-m",
        "-p",
        "-x",
    }


def test_sealed_pytest_policy_rejects_norecursedirs() -> None:
    runner_api = _c14_runner()
    result = runner_api.validate_pytest_selection_controls(_suite_policy(config={"norecursedirs": ["tests/hidden"]}))

    assert result.status == "UNKNOWN"


def test_pytest_configuration_control_catalog_covers_pinned_ini() -> None:
    runner_api = _c14_runner()
    catalog = runner_api.pytest_configuration_catalog(version="9.0.3", pytest_cov_version="7.1.0")

    assert catalog.unclassified_fields == ()
    assert set(catalog.classifications) == set(catalog.fields)


def test_pytest_hook_disposition_catalog_covers_execution_and_report_hooks() -> None:
    runner_api = _c14_runner()
    catalog = runner_api.pytest_hook_disposition_catalog(version="9.0.3")

    assert catalog.unclassified_hooks == ()
    assert len(catalog.hooks) == 52
    assert {"pytest_addhooks", "pytest_collectstart", "pytest_runtest_protocol", "pytest_warning_recorded"} <= set(
        catalog.hooks
    )


def test_pytest_builtin_collector_decision_catalog_covers_pinned_branches() -> None:
    runner_api = _c14_runner()
    catalog = runner_api.pytest_builtin_collector_decision_catalog(version="9.0.3")

    assert catalog.unclassified_branches == ()
    assert {"PyCollector.collect", "istestclass", "istestfunction", "UnitTestCase.collect"} <= set(catalog.branches)


@pytest.mark.parametrize(
    "control",
    [
        {"module": {"__test__": False}},
        {"class": {"__test__": False}},
        {"function": {"__test__": False}},
        {"class": {"__init__": object()}},
    ],
)
def test_native_pytest_raw_namespace_cannot_hide_failing_candidate(control: dict[str, object]) -> None:
    runner_api = _c14_runner()
    result = runner_api.validate_native_pytest_namespace(control)

    assert result.status == "UNKNOWN"


def test_same_file_builtin_pycollect_filter_is_unknown() -> None:
    runner_api = _c14_runner()
    assert runner_api.validate_native_pytest_namespace({"function": {"__test__": False}}).status == "UNKNOWN"


def test_same_file_constructor_suppressed_test_class_is_unknown() -> None:
    runner_api = _c14_runner()
    assert runner_api.validate_native_pytest_namespace({"class": {"__init__": object()}}).status == "UNKNOWN"


def test_same_file_item_level_dunder_test_false_is_unknown() -> None:
    runner_api = _c14_runner()
    assert runner_api.validate_native_pytest_namespace({"item": {"__test__": False}}).status == "UNKNOWN"


def test_same_unittest_class_method_dunder_test_false_is_unknown() -> None:
    runner_api = _c14_runner()
    assert runner_api.validate_unittest_controls({"method": {"__test__": False}}).status == "UNKNOWN"


def test_unittest_metaclass_dir_cannot_hide_failing_method() -> None:
    runner_api = _c14_runner()
    assert runner_api.validate_unittest_controls({"metaclass": {"__dir__": "override"}}).status == "UNKNOWN"


def test_unittest_run_or_call_override_cannot_bypass_failing_method() -> None:
    runner_api = _c14_runner()
    for method in ("run", "__call__"):
        assert runner_api.validate_unittest_controls({"class": {method: "override"}}).status == "UNKNOWN"


def test_collection_shaping_repository_hook_is_unknown_before_collection() -> None:
    runner_api = _c14_runner()
    result = runner_api.validate_pytest_plugins(({"origin": "repository", "hooks": ["pytest_collection_modifyitems"]},))
    assert result.status == "UNKNOWN"


def test_plugin_collection_shaping_hook_is_unknown() -> None:
    runner_api = _c14_runner()
    result = runner_api.validate_pytest_plugins(
        ({"origin": "attested-project", "hooks": ["pytest_collection_modifyitems"]},)
    )
    assert result.status == "UNKNOWN"


@pytest.mark.parametrize(
    "hook",
    ["pytest_ignore_collect", "pytest_pycollect_makeitem", "pytest_runtest_call"],
)
def test_every_collection_or_execution_shaping_plugin_hook_is_unknown(hook: str) -> None:
    runner_api = _c14_runner()
    result = runner_api.validate_pytest_plugins(({"origin": "attested-project", "hooks": [hook]},))

    assert result.status == "UNKNOWN"


def test_report_shaping_repository_hook_is_unknown_before_execution() -> None:
    runner_api = _c14_runner()
    result = runner_api.validate_pytest_plugins(({"origin": "repository", "hooks": ["pytest_runtest_makereport"]},))
    assert result.status == "UNKNOWN"


def test_changed_test_cannot_be_selectively_deselected_by_conftest() -> None:
    runner_api = _c14_runner()
    result = runner_api.validate_pytest_plugins(
        ({"origin": "repository", "hooks": ["pytest_collection_modifyitems"], "path": "tests/conftest.py"},)
    )
    assert result.status == "UNKNOWN"


def test_every_test_candidate_must_collect_even_when_unchanged() -> None:
    runner_api = _c14_runner()
    result = runner_api.reconcile_test_candidates(
        candidates=("tests/test_a.py", "tests/test_b.py"), collected_paths=("tests/test_a.py",)
    )
    assert result.status == "UNKNOWN"
    assert result.missing == ("tests/test_b.py",)


def test_non_strict_xpass_is_fail_despite_passing_junit_testcase() -> None:
    runner_api = _c14_runner()
    result = runner_api.reconcile_pytest_outcomes(
        observer=({"nodeid": "tests/test_a.py::test_a", "phase": "call", "passed": True, "wasxfail": "reason"},),
        junit=({"nodeid": "tests/test_a.py::test_a", "outcome": "passed"},),
        process_exit=0,
    )
    assert result.status == "FAIL"
    assert result.outcomes[0].kind == "XPASS"


def test_targeted_pytest_disables_ambient_plugin_autoload_and_loads_controller_coverage() -> None:
    runner_api = _c14_runner()

    assert runner_api._pytest_env()["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
    assert "pytest_cov.plugin" in runner_api._pytest_observer_script()


def test_failed_pytest_call_cannot_reconcile_as_pass() -> None:
    runner_api = _c14_runner()
    result = runner_api.reconcile_pytest_outcomes(
        observer=({"nodeid": "tests/test_a.py::test_a", "phase": "call", "passed": False},),
        junit=({"nodeid": "tests/test_a.py::test_a", "outcome": "failed"},),
        process_exit=1,
    )

    assert result.status == "FAIL"
    assert result.outcomes[0].kind == "FAILED"


def test_pytest_outcome_signal_disagreement_is_unknown() -> None:
    runner_api = _c14_runner()
    result = runner_api.reconcile_pytest_outcomes(
        observer=({"nodeid": "tests/test_a.py::test_a", "phase": "call", "passed": True},),
        junit=({"nodeid": "tests/test_a.py::test_a", "outcome": "failed"},),
        process_exit=0,
    )

    assert result.status == "UNKNOWN"


def test_pytest_outcome_reconciliation_rejects_missing_planned_selector() -> None:
    runner_api = _c14_runner()
    result = runner_api.reconcile_pytest_outcomes(
        observer=({"nodeid": "tests/test_app.py::test_visible", "phase": "call", "passed": True},),
        junit=({"nodeid": "tests/test_app.py::test_visible", "outcome": "passed"},),
        process_exit=0,
        planned=("tests/test_app.py::test_visible", "tests/test_app.py::test_hidden_by_conftest"),
    )

    assert result.status == "UNKNOWN"


def test_pytest_outcome_reconciliation_accepts_complete_parametrized_expansion() -> None:
    runner_api = _c14_runner()
    result = runner_api.reconcile_pytest_outcomes(
        observer=(
            {"nodeid": "tests/test_app.py::test_value[one]", "phase": "call", "passed": True},
            {"nodeid": "tests/test_app.py::test_value[two]", "phase": "call", "passed": True},
        ),
        junit=(
            {"nodeid": "tests/test_app.py::test_value[one]", "outcome": "passed"},
            {"nodeid": "tests/test_app.py::test_value[two]", "outcome": "passed"},
        ),
        process_exit=0,
        planned=("tests/test_app.py::test_value",),
    )

    assert result.status == "PASS"


def test_partial_parametrized_deselection_is_unknown_from_real_pytest(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "conftest.py").write_text(
        "def pytest_collection_modifyitems(config, items):\n"
        "    del config\n"
        "    items[:] = [item for item in items if item.callspec.params['value'] == 1]\n",
        encoding="utf-8",
    )
    test_file = tests_root / "test_param.py"
    test_file.write_text(
        "import pytest\n\n@pytest.mark.parametrize('value', [1, 2])\ndef test_value(value):\n    assert value == 1\n",
        encoding="utf-8",
    )

    process, coverage_path, observer_path, junit_path = runner_api._run_pytest_selection_with_coverage(
        (f"{test_file}::test_value",),
        coverage_source=tmp_path,
        policy_argv=("--rootdir", str(tmp_path)),
    )
    try:
        observer, junit = runner_api._load_pytest_outcome_evidence(observer_path, junit_path)
        result = runner_api.reconcile_pytest_outcomes(
            observer=observer,
            junit=junit,
            process_exit=process.returncode,
            planned=("tests/test_param.py::test_value",),
        )
    finally:
        coverage_path.unlink(missing_ok=True)
        observer_path.unlink(missing_ok=True)
        junit_path.unlink(missing_ok=True)

    assert process.returncode == 0
    assert result.status == "UNKNOWN"


def test_pytest_outcome_reconciliation_rejects_unrelated_parameterized_prefix() -> None:
    runner_api = _c14_runner()
    result = runner_api.reconcile_pytest_outcomes(
        observer=({"nodeid": "tests/test_app.py::test_value_extra[one]", "phase": "call", "passed": True},),
        junit=({"nodeid": "tests/test_app.py::test_value_extra[one]", "outcome": "passed"},),
        process_exit=0,
        planned=("tests/test_app.py::test_value",),
    )

    assert result.status == "UNKNOWN"


def _write_complete_pytest_evidence(
    tmp_path: Path,
    source_file: Path,
    observer: list[dict[str, object]],
    junit: str,
) -> tuple[Path, Path, Path]:
    coverage_path = tmp_path / "coverage.json"
    coverage_path.write_text(
        json.dumps({"files": {str(source_file): {"summary": {"percent_covered": 100.0}}}}),
        encoding="utf-8",
    )
    observer_path = tmp_path / "observer.json"
    observer_path.write_text(json.dumps(observer), encoding="utf-8")
    junit_path = tmp_path / "junit.xml"
    junit_path.write_text(junit, encoding="utf-8")
    return coverage_path, observer_path, junit_path


def test_complete_pytest_execution_rejects_non_strict_xpass_before_coverage(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    source_file = tmp_path / "src/app.py"
    source_file.parent.mkdir()
    source_file.write_text("VALUE = 1\n", encoding="utf-8")
    coverage_path, observer_path, junit_path = _write_complete_pytest_evidence(
        tmp_path,
        source_file,
        [
            {
                "nodeid": "tests/test_app.py::test_app",
                "phase": "call",
                "passed": True,
                "skipped": False,
                "wasxfail": "known bug",
            }
        ],
        '<testsuites><testsuite><testcase classname="tests.test_app" name="test_app" /></testsuite></testsuites>',
    )

    findings, coverage = runner_api._evaluate_pytest_execution(
        [source_file],
        lambda: (
            subprocess.CompletedProcess(["pytest"], 0, "", ""),
            coverage_path,
            observer_path,
            junit_path,
        ),
    )

    assert coverage is None
    assert [finding.rule for finding in findings] == ["TEST_OUTCOME_NOT_PASS"]


def test_complete_pytest_execution_observes_non_strict_xpass_from_real_pytest(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    source_file = tmp_path / "src/app.py"
    source_file.parent.mkdir()
    source_file.write_text("VALUE = 1\n", encoding="utf-8")
    test_file = tmp_path / "tests/test_app.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "import pytest\n\n@pytest.mark.xfail(reason='known bug', strict=False)\ndef test_app():\n    assert True\n",
        encoding="utf-8",
    )

    findings, coverage = runner_api._evaluate_pytest_execution(
        [source_file],
        lambda: runner_api._run_pytest_selection_with_coverage(
            (f"{test_file}::test_app",),
            coverage_source=tmp_path,
            policy_argv=("--rootdir", str(tmp_path)),
        ),
    )

    assert coverage is None
    assert [finding.rule for finding in findings] == ["TEST_OUTCOME_NOT_PASS"]


def test_complete_pytest_coverage_uses_sealed_fail_under_as_blocking_threshold(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    runner_api = _c14_runner()
    source_file = tmp_path / "src/app.py"
    source_file.parent.mkdir()
    source_file.write_text("VALUE = 1\n", encoding="utf-8")
    pytest_config = tmp_path / "pytest.ini"
    pytest_config.write_text("[pytest]\ntestpaths = /opt/specfact/snapshot/tests\n", encoding="utf-8")
    coverage_config = tmp_path / "coveragerc"
    coverage_config.write_text("[report]\nfail_under = 95\n", encoding="utf-8")
    coverage_path, observer_path, junit_path = _write_complete_pytest_evidence(
        tmp_path,
        source_file,
        [{"nodeid": "tests/test_app.py::test_app", "phase": "call", "passed": True}],
        '<testsuites><testsuite><testcase classname="tests.test_app" name="test_app" /></testsuite></testsuites>',
    )
    coverage_path.write_text(
        json.dumps({"files": {str(source_file): {"summary": {"percent_covered": 90.0}}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        runner_api,
        "_run_pytest_inventory_with_coverage",
        lambda *_args, **_kwargs: (
            subprocess.CompletedProcess(["pytest"], 0, "", ""),
            coverage_path,
            observer_path,
            junit_path,
        ),
    )

    findings, coverage = runner_api._evaluate_complete_tdd_gate(
        [source_file],
        (
            "-c",
            str(pytest_config),
            "--cov-config",
            str(coverage_config),
            "--",
            "tests/test_app.py::test_app",
        ),
    )

    response = runner_api._capsule_member_response("targeted-pytest-coverage", findings)
    assert coverage == {str(source_file): 90.0}
    assert [finding.rule for finding in findings] == ["TEST_COVERAGE_LOW"]
    assert findings[0].severity == "error"
    assert response["evidence_outcome"] == "FAIL"


def test_complete_suite_discovers_async_and_class_test_selectors(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    test_file = tmp_path / "tests/test_shapes.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "async def test_async_case():\n    pass\n\n"
        "class TestCases:\n"
        "    def test_method(self):\n        pass\n"
        "    async def test_async_method(self):\n        pass\n",
        encoding="utf-8",
    )

    plan = runner_api.plan_complete_pytest_suite(
        tmp_path,
        _suite_policy(),
        changed_paths=("tests/test_shapes.py",),
    )

    assert plan.status == "PASS"
    assert set(plan.selectors) == {
        "tests/test_shapes.py::test_async_case",
        "tests/test_shapes.py::TestCases::test_method",
        "tests/test_shapes.py::TestCases::test_async_method",
    }


@pytest.mark.parametrize("outcome", ["skip", "xfail", "xpass", "deselected"])
def test_targeted_pytest_rejects_head_skip_xfail_xpass_and_deselection(outcome: str) -> None:
    runner_api = _c14_runner()
    result = runner_api.classify_targeted_pytest(base_outcome="pass", head_outcome=outcome)
    expected_status = "UNKNOWN" if outcome == "deselected" else "FAIL"
    assert result.status == expected_status


def test_targeted_pytest_baseline_failure_head_pass_is_fixed() -> None:
    runner_api = _c14_runner()
    result = runner_api.classify_targeted_pytest(base_outcome="fail", head_outcome="pass")
    assert result.status == "PASS"
    assert result.disposition == "fixed"


@pytest.mark.parametrize(
    ("head_outcome", "expected"),
    [("assertion-fail", "FAIL"), ("timeout", "UNKNOWN"), ("collection-error", "UNKNOWN")],
)
def test_targeted_pytest_coverage_classifies_failure_vs_unknown(head_outcome: str, expected: str) -> None:
    runner_api = _c14_runner()
    assert runner_api.classify_targeted_pytest(base_outcome="pass", head_outcome=head_outcome).status == expected


def test_targeted_pytest_imports_attested_external_dependency() -> None:
    runner_api = _c14_runner()
    result = runner_api.build_pytest_import_order(
        snapshot_root="/snapshot", project_runtime="/project/site-packages", attested=True
    )
    assert result.status == "PASS"
    assert result.search_order == ("/snapshot", "/project/site-packages")


def test_coverage_projection_redirects_all_writable_paths_to_output_root(tmp_path: Path) -> None:
    runner_api = _c14_runner()
    projection = runner_api.project_coverage_policy(
        {"run:data_file": ".coverage", "html:directory": "htmlcov", "xml:output": "coverage.xml"},
        snapshot_root=tmp_path / "snapshot",
        output_root=tmp_path / "output",
    )
    assert all(str(path).startswith(str(tmp_path / "output")) for path in projection.writable_paths)


def test_coverage_repository_plugin_is_unknown() -> None:
    runner_api = _c14_runner()
    assert runner_api.project_coverage_policy({"run:plugins": ["candidate_plugin"]}).status == "UNKNOWN"


def test_targeted_coverage_clears_default_exclusion_registry() -> None:
    runner_api = _c14_runner()
    projection = runner_api.project_coverage_policy({})
    assert projection.values["report:exclude_lines"] == []
    assert projection.values["report:partial_branches"] == []


def test_targeted_coverage_rejects_custom_exclusion_regexes() -> None:
    runner_api = _c14_runner()
    result = runner_api.project_coverage_policy({"report:exclude_lines": ["pragma: custom"]})
    assert result.status == "UNKNOWN"


def test_targeted_coverage_uses_sealed_target_config_and_rejects_candidate_suppression() -> None:
    runner_api = _c14_runner()
    result = runner_api.select_coverage_policy(target={"run:branch": True}, candidate={"report:exclude_lines": [".*"]})
    assert result.status == "UNKNOWN"
    assert result.policy_source == "target_tip"


def test_targeted_coverage_rejects_missing_runtime_measurable_production_path() -> None:
    runner_api = _c14_runner()
    result = runner_api.reconcile_coverage_manifest(required=("src/a.py", "src/b.py"), observed=("src/a.py",))
    assert result.status == "UNKNOWN"


def test_targeted_coverage_threshold_failure_is_fail_not_unknown() -> None:
    runner_api = _c14_runner()
    result = runner_api.classify_coverage(base=90, head=79, threshold=80)
    assert result.status == "FAIL"
    assert result.execution_state == "ran"


def test_targeted_coverage_baseline_threshold_failure_head_pass_is_fixed() -> None:
    runner_api = _c14_runner()
    result = runner_api.classify_coverage(base=70, head=90, threshold=80)
    assert result.status == "PASS"
    assert result.disposition == "fixed"


def test_coverage_manifest_excludes_pyi_but_static_analyzers_include_it() -> None:
    runner_api = _c14_runner()
    manifests = runner_api.classify_analyzer_input_kinds(("src/a.py", "src/a.pyi"))
    assert manifests["targeted-pytest-coverage"] == ("src/a.py",)
    assert "src/a.pyi" in manifests["ruff"]
    assert "src/a.pyi" in manifests["contracts.icontract-static-scan"]


def test_stub_only_range_is_static_and_coverage_not_applicable() -> None:
    runner_api = _c14_runner()
    result = runner_api.classify_snapshot_input_kinds(("src/a.pyi",))
    assert result.member("targeted-pytest-coverage").status == "NOT_APPLICABLE"
    assert result.member("ruff").status != "NOT_APPLICABLE"


def test_capsule_snapshot_does_not_launch_targeted_pytest_for_stub_only_input(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner_api = _c14_runner()
    stub = tmp_path / "src/app.pyi"
    stub.parent.mkdir()
    stub.write_text("VALUE: int\n", encoding="utf-8")
    launched: list[str] = []

    def execute(request: Any) -> dict[str, object]:
        launched.append(request.member)
        return {"execution_state": "ran", "evidence_outcome": "PASS", "findings": [], "diagnostic": ""}

    monkeypatch.setattr(runner_api, "_execute_capsule_member", execute)
    result = runner_api._run_capsule_snapshot(
        SimpleNamespace(identity="sha256:" + "a" * 64),
        snapshot_root=tmp_path,
        files=[stub],
        options=runner_api.ReviewOptions(),
        member_argv={"targeted-pytest-coverage": ("--",)},
    )

    assert "targeted-pytest-coverage" not in launched
    assert "ruff" in launched
    assert result.evidence["targeted-pytest-coverage"]["evidence_outcome"] == "NOT_APPLICABLE"
    assert result.evidence["targeted-pytest-coverage"]["diagnostic"] == "member_input_not_applicable"


def test_stub_only_range_excludes_crosshair_but_requires_stub_capable_static_members() -> None:
    runner_api = _c14_runner()
    result = runner_api.classify_snapshot_input_kinds(("src/a.pyi",))
    assert result.member("contracts.crosshair").status == "NOT_APPLICABLE"
    assert result.member("basedpyright").required is True


def test_stub_only_contracts_keeps_activated_static_scan_and_marks_only_crosshair_not_applicable() -> None:
    runner_api = _c14_runner()
    result = runner_api.classify_contract_components(("src/a.pyi",), icontract_usage=True)
    assert result.static_scan.status != "NOT_APPLICABLE"
    assert result.crosshair.status == "NOT_APPLICABLE"
    assert result.parent.status != "NOT_APPLICABLE"


def test_contract_static_activation_preserves_existing_icontract_usage_boundary() -> None:
    runner_api = _c14_runner()
    result = runner_api.icontract_static_activation(b"from icontract import require\n")
    assert result.active is True
    assert result.contract == "icontract-static-activation-v1"


def test_required_analyzers_structurally_empty_snapshot_is_not_applicable() -> None:
    runner_api = _c14_runner()
    result = runner_api.classify_snapshot_input_kinds(())
    assert all(member.status == "NOT_APPLICABLE" for member in result.members)


def test_adversarial_runtime_policy_is_unknown() -> None:
    runner_api = _c14_runner()
    result = runner_api.evaluate_runtime_policy(candidate_python_executes=True, hostile_candidate_claim=True)
    assert result.status == "UNKNOWN"
    assert result.assumption == "non_adversarial_candidate_runtime"
