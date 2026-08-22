from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import pytest
import yaml
from typer.testing import CliRunner

from specfact_code_review.review.commands import app
from specfact_code_review.run import commands as run_commands, scope as review_scope
from specfact_code_review.run.findings import ReviewFinding, ReviewReport
from specfact_requirements.requirements.lifecycle import build_plan


runner = CliRunner()
REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_FILE = REPO_ROOT / "tests/fixtures/review/clean_module.py"
SafeMechanicalAction = Literal["remove", "inline", "collapse"]
SAFE_MECHANICAL_ACTIONS: dict[str, SafeMechanicalAction] = {
    "ai-bloat.dead-branch": "remove",
    "ai-bloat.pass-through-try-except": "remove",
    "ai-bloat.redundant-intermediate": "inline",
    "ai-bloat.verbose-bool-return": "collapse",
}
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def _report(*, score: int = 85) -> ReviewReport:
    return ReviewReport(
        run_id="review-run-001",
        timestamp=datetime(2026, 3, 16, tzinfo=UTC),
        score=score,
        findings=[],
        summary="Review command test report.",
    )


def _changed_enforcement_report() -> ReviewReport:
    blocking_finding = ReviewFinding(
        category="contracts",
        severity="error",
        tool="ast",
        rule="legacy-blocker",
        file="legacy.py",
        line=1,
        message="Legacy blocking finding retained as evidence.",
        fixable=False,
        confidence="high",
    )
    report = ReviewReport(
        run_id="review-changed-enforcement",
        timestamp=datetime(2026, 8, 4, tzinfo=UTC),
        score=85,
        findings=[blocking_finding],
        summary="Changed enforcement excludes the legacy blocker.",
    )
    return report.model_copy(
        update={
            "overall_verdict": "PASS_WITH_ADVISORY",
            "ci_exit_code": 0,
            "enforcement_mode": "changed",
            "enforcement_summary": "Changed enforcement excludes the legacy blocker.",
            "schema_version": "1.4",
        }
    )


def _finalized_requirements_proof(
    tmp_path: Path,
    *,
    decision: str = "fail",
    schema_version: str = "2",
    proof_basis: Literal["red-junit", "legacy-tdd-ledger"] = "red-junit",
) -> Path:
    mapping_digest = "sha256:" + "a" * 64
    selector = "tests/fixtures/review/clean_module.py::test_clean_module"
    plan = build_plan(mapping_digest, [{"case_id": "REQ-001", "method": "test", "node_id": selector}])
    plan_digest = plan["plan_digest"]
    proof_path = tmp_path / "requirements-proof.json"
    proof = {
        "schema_version": schema_version,
        "gate_decision": decision,
        "required_maturity": "verified",
        "observed_maturity": "verified" if decision == "pass" else "incomplete",
        "mapping_digest": mapping_digest,
        "plan_digest": plan_digest,
        "findings": [] if decision == "pass" else ["uncollected-selector:" + selector],
        "plan": plan,
        "execution_plan": plan,
        "execution_proof": {
            "run_stage": "final",
            "source_ref": "c" * 40,
            "selectors": [selector],
            "junit_digest": "sha256:" + "d" * 64,
        },
    }
    if decision == "pass":
        proof["execution_proof"]["proof_basis"] = proof_basis
        if proof_basis == "legacy-tdd-ledger":
            proof["legacy_tdd_evidence"] = {
                "schema_version": "1",
                "kind": "legacy-tdd-ledger",
                "change_id": "requirements-07-runtime-proof-delivery",
                "ledger_digest": "sha256:" + "e" * 64,
                "mapping_digest": mapping_digest,
                "plan_digest": plan_digest,
            }
    proof_path.write_text(json.dumps(proof), encoding="utf-8")
    return proof_path


def test_code_review_manifest_declares_requirements_runtime_dependency() -> None:
    """Keep Requirements-proof validation dependencies compatible at install time."""
    manifest_path = REPO_ROOT / "packages" / "specfact-code-review" / "module-package.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))

    assert "nold-ai/specfact-requirements" in manifest["bundle_dependencies"]
    assert manifest["core_compatibility"] == "===0.55.1"


def _safe_mechanical_finding(file_path: Path, *, line: int, rule: str) -> ReviewFinding:
    return ReviewFinding(
        category="ai_bloat",
        severity="info",
        tool="ast",
        rule=rule,
        file=str(file_path),
        line=line,
        message="Safe mechanical simplification.",
        fixable=True,
        confidence="high",
        rewrite_hint="Apply the local rewrite.",
        canonical_pattern="safe-mechanical",
        estimated_deletion_lines=1,
        guidance_kind="safe_mechanical",
        recommended_action=SAFE_MECHANICAL_ACTIONS[rule],
        clean_code_principle="kiss",
        rationale="The rewrite is local and behavior-preserving.",
        safety_checks=["pattern shape is exact"],
        action_status="recommended",
    )


def _safe_mechanical_report(file_path: Path, *, line: int, rule: str) -> ReviewReport:
    return ReviewReport(
        run_id="review-run-001",
        timestamp=datetime(2026, 3, 16, tzinfo=UTC),
        score=85,
        findings=[_safe_mechanical_finding(file_path, line=line, rule=rule)],
        summary="Review command test report.",
    )


def _write_repo_file(repo_root: Path, relative_path: str, *, content: str = "VALUE = 1\n") -> Path:
    file_path = repo_root / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return Path(relative_path)


def test_run_command_json_output_uses_review_report(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "specfact_code_review.run.commands.run_review",
        lambda files, **_kwargs: _report(),
    )
    out = tmp_path / "review-report.json"

    result = runner.invoke(
        app,
        [
            "review",
            "run",
            "--json",
            "--out",
            str(out),
            "tests/fixtures/review/clean_module.py",
        ],
    )

    assert result.exit_code == 0
    assert result.output.strip() == str(out)
    report = ReviewReport.model_validate_json(out.read_text(encoding="utf-8"))
    assert report.run_id == "review-run-001"


def test_run_command_default_json_output_path_uses_review_report(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "specfact_code_review.run.commands.run_review",
        lambda files, **_kwargs: _report(),
    )
    monkeypatch.chdir(tmp_path)

    exit_code, output = run_commands.run_command(
        [FIXTURE_FILE],
        json_output=True,
    )

    assert exit_code == 0
    assert output == "review-report.json"
    report = ReviewReport.model_validate_json((tmp_path / "review-report.json").read_text(encoding="utf-8"))
    assert report.run_id == "review-run-001"


def test_run_command_retains_finalized_requirements_provenance_without_verdict_fusion(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "specfact_code_review.run.commands.run_review",
        lambda files, **_kwargs: _report(),
    )
    proof_path = _finalized_requirements_proof(tmp_path, decision="fail")
    out = tmp_path / "review-report.json"

    exit_code, output = run_commands.run_command(
        [FIXTURE_FILE],
        json_output=True,
        out=out,
        requirements_evidence=proof_path,
    )

    report = ReviewReport.model_validate_json(out.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert output == str(out)
    assert report.requirements_evidence.gate_decision == "fail"  # type: ignore[union-attr]
    assert report.requirements_evidence.source_ref == "c" * 40  # type: ignore[union-attr]


def test_requirements_evidence_context_canonicalizes_equivalent_json(tmp_path: Path) -> None:
    formatted_path = _finalized_requirements_proof(tmp_path, decision="pass")
    proof = json.loads(formatted_path.read_text(encoding="utf-8"))
    reordered_proof = dict(reversed(list(proof.items())))
    compact_path = tmp_path / "compact-proof.json"
    compact_path.write_text(json.dumps(reordered_proof, separators=(",", ":")), encoding="utf-8")

    formatted_context = run_commands._requirements_evidence_context(formatted_path)
    compact_context = run_commands._requirements_evidence_context(compact_path)
    canonical_payload = json.dumps(proof, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")

    assert formatted_context.content_digest == compact_context.content_digest
    assert formatted_context.content_digest == f"sha256:{hashlib.sha256(canonical_payload).hexdigest()}"


def test_requirements_evidence_attachment_preserves_schema_1_6_assurance_status(tmp_path: Path) -> None:
    proof_path = _finalized_requirements_proof(tmp_path, decision="pass")
    context = run_commands._requirements_evidence_context(proof_path)
    report = ReviewReport(
        schema_version="1.6",
        assurance_status="UNKNOWN",
        run_id="unknown-review",
        timestamp=datetime(2026, 8, 19, tzinfo=UTC),
        score=100,
        findings=[],
        summary="Analyzer identity mismatch.",
        overall_verdict="FAIL",
        ci_exit_code=1,
        scope_evidence={"assurance_kind": "range_candidate"},
        analyzer_evidence=[{"id": "ruff", "evidence_outcome": "UNKNOWN"}],
    )

    attached = run_commands._attach_requirements_evidence(report, context)

    assert attached.requirements_evidence == context
    assert attached.schema_version == "1.6"
    assert attached.assurance_status == "UNKNOWN"
    assert attached.ci_exit_code == 1
    assert attached.scope_evidence == report.scope_evidence
    assert attached.analyzer_evidence == report.analyzer_evidence


def test_index_scope_evidence_serializes_captured_identity() -> None:
    identity = review_scope.InputIdentity("blob", "100644", "a" * 40, "sha256:" + "b" * 64)
    metadata = review_scope.IndexMetadata("100644", "a" * 40, 0, False, "H")
    resolution = review_scope.ScopeResolution(
        status="PASS",
        reason="resolved",
        selected_paths=("src/app.py",),
        assurance_kind="index",
        effective_assurance_kind="index",
        ci_exit_code=0,
        input_manifest={"src/app.py": identity},
        index_metadata={"src/app.py": metadata},
        index_tree="c" * 40,
        selection_tree="c" * 40,
    )

    evidence = run_commands._scope_evidence(resolution)

    assert evidence["index_tree"] == "c" * 40
    assert evidence["selection_tree"] == "c" * 40
    input_manifest = evidence["input_manifest"]
    index_metadata = evidence["index_metadata"]
    assert isinstance(input_manifest, dict)
    assert isinstance(index_metadata, dict)
    assert input_manifest["src/app.py"]["blob_sha"] == "a" * 40
    assert index_metadata["src/app.py"]["flag_tag"] == "H"


def test_immutable_scope_report_cleans_materialized_roots(monkeypatch: Any, tmp_path: Path) -> None:
    base_root = tmp_path / "base"
    head_root = tmp_path / "head"
    policy_root = tmp_path / "policy"
    for root in (base_root, head_root, policy_root):
        root.mkdir()

    def snapshot(root: Path, commit: str) -> review_scope.Snapshot:
        return review_scope.Snapshot(root, commit, "b" * 40, {}, {})

    resolution = review_scope.ScopeResolution(
        status="PASS",
        reason="resolved",
        selected_paths=("src/app.py",),
        assurance_kind="range_preview",
        effective_assurance_kind="range_preview",
        ci_exit_code=0,
        base_snapshot=snapshot(base_root, "a" * 40),
        head_snapshot=snapshot(head_root, "c" * 40),
        materialized=True,
        policy_bundle=review_scope.PolicyBundle(policy_root, "a" * 40, "b" * 40, (), "sha256:" + "d" * 64),
    )
    monkeypatch.setattr(run_commands, "resolve_scope", lambda _request: resolution)

    run_commands._immutable_scope_report(
        run_commands.ReviewRunRequest(files=[], scope="range", base_ref="a" * 40, head_ref="c" * 40)
    )

    assert not base_root.exists()
    assert not head_root.exists()
    assert not policy_root.exists()


def test_resolved_immutable_scope_executes_capsule_review_before_cleanup(monkeypatch: Any, tmp_path: Path) -> None:
    base_root = tmp_path / "base"
    head_root = tmp_path / "head"
    for root in (base_root, head_root):
        root.mkdir()
    resolution = review_scope.ScopeResolution(
        status="PASS",
        reason="resolved",
        selected_paths=("src/app.py",),
        assurance_kind="range_preview",
        effective_assurance_kind="range_preview",
        ci_exit_code=0,
        base_snapshot=review_scope.Snapshot(base_root, "a" * 40, "b" * 40, {}, {}),
        head_snapshot=review_scope.Snapshot(head_root, "c" * 40, "d" * 40, {}, {}),
        materialized=True,
    )
    expected = _report()
    observed: dict[str, object] = {}

    def execute(resolved: review_scope.ScopeResolution, **_kwargs: object) -> ReviewReport:
        observed["resolution"] = resolved
        observed["roots_existed"] = base_root.exists() and head_root.exists()
        return expected

    monkeypatch.setattr(run_commands, "resolve_scope", lambda _request: resolution)
    monkeypatch.setattr(run_commands, "run_immutable_scope_review", execute)

    actual = run_commands._immutable_scope_report(
        run_commands.ReviewRunRequest(files=[], scope="range", base_ref="a" * 40, head_ref="c" * 40)
    )

    assert actual is expected
    assert observed == {"resolution": resolution, "roots_existed": True}
    assert not base_root.exists()
    assert not head_root.exists()


def test_command_layer_uses_capsule_gateway_for_legacy_scopes() -> None:
    from specfact_code_review.run import runner as runner_api

    assert run_commands.run_review is runner_api.run_capsule_review


def test_immutable_scope_request_propagates_repository_identity(monkeypatch: Any) -> None:
    captured: dict[str, object] = {}

    def resolve(request: object) -> review_scope.ScopeResolution:
        captured["request"] = request
        return review_scope.ScopeResolution(
            status="UNKNOWN",
            reason="test",
            selected_paths=(),
            assurance_kind="range_preview",
            effective_assurance_kind="range_preview",
            ci_exit_code=1,
        )

    monkeypatch.setattr(run_commands, "resolve_scope", resolve)
    monkeypatch.setattr(run_commands, "_repository_slug", lambda _root: "nold-ai/specfact-cli-modules")

    run_commands._immutable_scope_report(
        run_commands.ReviewRunRequest(files=[], scope="range", base_ref="a" * 40, head_ref="b" * 40)
    )

    request = captured["request"]
    assert isinstance(request, review_scope.ScopeRequest)
    assert request.repository_slug == "nold-ai/specfact-cli-modules"


def test_repository_slug_accepts_authenticated_github_origin(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        run_commands.subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(
            command,
            0,
            "git@github.com:nold-ai/specfact-cli-modules.git\n",
            "",
        ),
    )

    assert run_commands._repository_slug(Path.cwd()) == "nold-ai/specfact-cli-modules"


def test_run_command_rejects_incomplete_requirements_evidence_before_review(monkeypatch: Any, tmp_path: Path) -> None:
    def unexpected_review(*_args: Any, **_kwargs: Any) -> ReviewReport:
        pytest.fail("Requirements evidence validation must run before review execution.")

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", unexpected_review)
    proof_path = tmp_path / "incomplete-requirements-proof.json"
    proof_path.write_text(
        json.dumps(
            {
                "schema_version": "2",
                "gate_decision": "pass",
                "mapping_digest": "sha256:" + "a" * 64,
                "plan_digest": "sha256:" + "b" * 64,
                "execution_proof": {"run_stage": "final", "source_ref": "c" * 40},
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "review",
            "run",
            "--requirements-evidence",
            str(proof_path),
            "tests/fixtures/review/clean_module.py",
        ],
    )

    assert result.exit_code != 0


def test_requirements_evidence_context_rejects_tampered_plan_digest(tmp_path: Path) -> None:
    proof_path = _finalized_requirements_proof(tmp_path, decision="pass")
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    proof["plan"]["cases"][0]["case_id"] = "FORGED-001"
    proof_path.write_text(json.dumps(proof), encoding="utf-8")

    with pytest.raises(run_commands.RunCommandError, match="complete final Requirements proof"):
        run_commands._requirements_evidence_context(proof_path)


def test_requirements_evidence_context_rejects_passing_proof_without_basis(tmp_path: Path) -> None:
    proof_path = _finalized_requirements_proof(tmp_path, decision="pass")
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    del proof["execution_proof"]["proof_basis"]
    proof_path.write_text(json.dumps(proof), encoding="utf-8")

    with pytest.raises(run_commands.RunCommandError, match="complete final Requirements proof"):
        run_commands._requirements_evidence_context(proof_path)


def test_requirements_evidence_context_accepts_legacy_tdd_ledger_basis(tmp_path: Path) -> None:
    proof_path = _finalized_requirements_proof(tmp_path, decision="pass", proof_basis="legacy-tdd-ledger")

    context = run_commands._requirements_evidence_context(proof_path)

    assert context.gate_decision == "pass"


def test_requirements_evidence_context_rejects_legacy_basis_without_ledger(tmp_path: Path) -> None:
    proof_path = _finalized_requirements_proof(tmp_path, decision="pass", proof_basis="legacy-tdd-ledger")
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    del proof["legacy_tdd_evidence"]
    proof_path.write_text(json.dumps(proof), encoding="utf-8")

    with pytest.raises(run_commands.RunCommandError, match="complete final Requirements proof"):
        run_commands._requirements_evidence_context(proof_path)


def test_run_command_preserves_changed_enforcement_when_attaching_requirements_evidence(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "specfact_code_review.run.commands.run_review",
        lambda files, **_kwargs: _changed_enforcement_report(),
    )
    out = tmp_path / "review-report.json"

    exit_code, _ = run_commands.run_command(
        [FIXTURE_FILE],
        json_output=True,
        out=out,
        requirements_evidence=_finalized_requirements_proof(tmp_path),
    )

    report = ReviewReport.model_validate_json(out.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert report.overall_verdict == "PASS_WITH_ADVISORY"
    assert report.ci_exit_code == 0
    assert report.enforcement_mode == "changed"
    assert report.requirements_evidence is not None


def test_run_command_rejects_nonfinal_requirements_evidence_before_review(monkeypatch: Any, tmp_path: Path) -> None:
    def unexpected_review(*_args: Any, **_kwargs: Any) -> ReviewReport:
        pytest.fail("Requirements evidence validation must run before review execution.")

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", unexpected_review)
    proof_path = _finalized_requirements_proof(tmp_path)
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    proof["execution_proof"]["run_stage"] = "red"
    proof_path.write_text(json.dumps(proof), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "review",
            "run",
            "--requirements-evidence",
            str(proof_path),
            "tests/fixtures/review/clean_module.py",
        ],
    )

    assert result.exit_code != 0
    assert "finalized Requirements evidence" in result.output


@pytest.mark.parametrize("schema_version", ["1", "3"])
def test_run_command_rejects_non_v2_requirements_evidence_before_review(
    monkeypatch: Any, tmp_path: Path, schema_version: str
) -> None:
    def unexpected_review(*_args: Any, **_kwargs: Any) -> ReviewReport:
        pytest.fail("Requirements evidence validation must run before review execution.")

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", unexpected_review)
    proof_path = _finalized_requirements_proof(tmp_path, schema_version=schema_version)

    result = runner.invoke(
        app,
        [
            "review",
            "run",
            "--requirements-evidence",
            str(proof_path),
            "tests/fixtures/review/clean_module.py",
        ],
    )

    assert result.exit_code != 0
    assert "schema_version=2" in result.output


def test_run_command_score_only_prints_reward_delta(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "specfact_code_review.run.commands.run_review",
        lambda files, **_kwargs: _report(score=92),
    )

    result = runner.invoke(app, ["review", "run", "--score-only", "tests/fixtures/review/clean_module.py"])

    assert result.exit_code == 0
    assert result.output == "92\n"


def test_run_command_uses_git_diff_when_files_are_omitted(monkeypatch: Any, tmp_path: Path) -> None:
    recorded: dict[str, list[Path]] = {}
    out = tmp_path / "review-report.json"

    monkeypatch.setattr(
        "specfact_code_review.run.commands._changed_files_from_git_diff",
        lambda *, include_tests: [Path("tests/fixtures/review/clean_module.py")],
    )

    def fake_run_review(files: list[Path], **_kwargs: Any) -> ReviewReport:
        recorded["files"] = files
        return _report()

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", fake_run_review)

    result = runner.invoke(app, ["review", "run", "--json", "--out", str(out)])

    assert result.exit_code == 0
    assert recorded["files"] == [Path("tests/fixtures/review/clean_module.py")]
    assert out.exists()


def test_run_command_supports_full_scope_and_path_filters(monkeypatch: Any, tmp_path: Path) -> None:
    package_file = _write_repo_file(
        tmp_path,
        "packages/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    _write_repo_file(tmp_path, "packages/specfact-backlog/src/specfact_backlog/commands.py")
    monkeypatch.chdir(tmp_path)

    recorded: dict[str, list[Path]] = {}
    monkeypatch.setattr(
        "specfact_code_review.run.commands._all_python_files_from_git",
        lambda: [package_file, Path("packages/specfact-backlog/src/specfact_backlog/commands.py")],
        raising=False,
    )

    def fake_run_review(files: list[Path], **_kwargs: Any) -> ReviewReport:
        recorded["files"] = files
        return _report()

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", fake_run_review)

    result = runner.invoke(
        app,
        [
            "review",
            "run",
            "--scope",
            "full",
            "--path",
            "packages/specfact-code-review",
            "--json",
            "--out",
            "review-report.json",
        ],
    )

    assert result.exit_code == 0
    assert recorded["files"] == [package_file]


def test_run_command_supports_changed_scope_with_repeatable_path_filters(monkeypatch: Any, tmp_path: Path) -> None:
    package_file = _write_repo_file(
        tmp_path,
        "packages/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    test_file = _write_repo_file(
        tmp_path,
        "tests/unit/specfact_code_review/run/test_commands.py",
        content="def test_scope_paths() -> None:\n    assert True\n",
    )
    _write_repo_file(tmp_path, "packages/specfact-backlog/src/specfact_backlog/commands.py")
    monkeypatch.chdir(tmp_path)

    recorded: dict[str, list[Path]] = {}
    monkeypatch.setattr(
        "specfact_code_review.run.commands._changed_files_from_git_diff",
        lambda *, include_tests: [
            package_file,
            test_file,
            Path("packages/specfact-backlog/src/specfact_backlog/commands.py"),
        ],
    )

    def fake_run_review(files: list[Path], **_kwargs: Any) -> ReviewReport:
        recorded["files"] = files
        return _report()

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", fake_run_review)

    result = runner.invoke(
        app,
        [
            "review",
            "run",
            "--scope",
            "changed",
            "--path",
            "packages/specfact-code-review",
            "--path",
            "tests/unit/specfact_code_review",
            "--json",
            "--out",
            "review-report.json",
        ],
    )

    assert result.exit_code == 0
    assert recorded["files"] == [package_file, test_file]


def test_run_command_passes_simplify_focus_after_scope_resolution(monkeypatch: Any, tmp_path: Path) -> None:
    package_file = _write_repo_file(
        tmp_path,
        "packages/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    monkeypatch.chdir(tmp_path)
    recorded: dict[str, object] = {}
    monkeypatch.setattr(
        "specfact_code_review.run.commands._changed_files_from_git_diff",
        lambda *, include_tests: [package_file],
    )

    def fake_run_review(files: list[Path], **kwargs: Any) -> ReviewReport:
        recorded["files"] = files
        recorded["focus"] = kwargs.get("focus")
        return _report()

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", fake_run_review)

    result = runner.invoke(
        app,
        [
            "review",
            "run",
            "--scope",
            "changed",
            "--path",
            "packages/specfact-code-review",
            "--focus",
            "simplify",
            "--json",
            "--out",
            "review-report.json",
        ],
    )

    assert result.exit_code == 0
    assert recorded == {"files": [package_file], "focus": "simplify"}


def test_run_command_passes_enforcement_mode_to_review_runtime(monkeypatch: Any, tmp_path: Path) -> None:
    package_file = _write_repo_file(
        tmp_path,
        "packages/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    monkeypatch.chdir(tmp_path)
    recorded: dict[str, object] = {}

    def fake_run_review(files: list[Path], **kwargs: Any) -> ReviewReport:
        recorded["files"] = files
        recorded["review_mode"] = kwargs.get("review_mode")
        return _report()

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", fake_run_review)

    result = runner.invoke(
        app,
        [
            "review",
            "run",
            "--enforcement",
            "shadow",
            "--json",
            "--out",
            "review-report.json",
            str(package_file),
        ],
    )

    assert result.exit_code == 0
    assert recorded == {"files": [package_file], "review_mode": "shadow"}


def test_run_command_maps_legacy_enforce_mode_to_full_enforcement(monkeypatch: Any, tmp_path: Path) -> None:
    package_file = _write_repo_file(
        tmp_path,
        "packages/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    monkeypatch.chdir(tmp_path)
    recorded: dict[str, object] = {}

    def fake_run_review(files: list[Path], **kwargs: Any) -> ReviewReport:
        recorded["review_mode"] = kwargs.get("review_mode")
        return _report()

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", fake_run_review)

    result = runner.invoke(app, ["review", "run", "--mode", "enforce", "--json", str(package_file)])

    assert result.exit_code == 0
    assert recorded == {"review_mode": "full"}


def test_run_command_normalizes_simplify_focus_on_direct_request(monkeypatch: Any, tmp_path: Path) -> None:
    package_file = _write_repo_file(
        tmp_path,
        "packages/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    monkeypatch.chdir(tmp_path)
    recorded: dict[str, object] = {}

    def fake_run_review(files: list[Path], **kwargs: Any) -> ReviewReport:
        recorded["files"] = files
        recorded["focus"] = kwargs.get("focus")
        return _report()

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", fake_run_review)

    exit_code, output = run_commands.run_command(
        run_commands.ReviewRunRequest(
            files=[package_file],
            json_output=True,
            out=Path("review-report.json"),
            focus_facets=("simplify",),
            review_focus=None,
        )
    )

    assert exit_code == 0
    assert output == "review-report.json"
    assert recorded == {"files": [package_file], "focus": "simplify"}


def test_run_command_rejects_preview_fixes_with_fix() -> None:
    result = runner.invoke(
        app,
        [
            "review",
            "run",
            "--focus",
            "simplify",
            "--preview-fixes",
            "--fix",
            "tests/fixtures/review/clean_module.py",
        ],
    )

    assert result.exit_code == 2
    assert "Cannot combine --preview-fixes with --fix" in _strip_ansi(result.output)


def test_run_command_rejects_preview_fixes_without_simplify_focus() -> None:
    result = runner.invoke(
        app,
        ["review", "run", "--preview-fixes", "tests/fixtures/review/clean_module.py"],
    )

    assert result.exit_code == 2
    assert "Use --preview-fixes only with --focus simplify" in _strip_ansi(result.output)


def test_run_command_rejects_with_mutation_without_simplify_focus() -> None:
    result = runner.invoke(
        app,
        ["review", "run", "--with-mutation", "tests/fixtures/review/clean_module.py"],
    )

    assert result.exit_code == 2
    assert "Use --with-mutation only with --focus simplify" in _strip_ansi(result.output)


def test_preview_fixes_adds_patch_forecast_without_mutating_tracked_file(monkeypatch: Any, tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    source = "def total(values: list[int]) -> int:\n    result = sum(values)\n    return result\n"
    target.write_text(source, encoding="utf-8")
    report = _safe_mechanical_report(target, line=2, rule="ai-bloat.redundant-intermediate")
    monkeypatch.setattr("specfact_code_review.run.commands.run_review", lambda files, **kwargs: report)

    exit_code, output = run_commands.run_command(
        run_commands.ReviewRunRequest(
            files=[target],
            json_output=True,
            out=tmp_path / "review-report.json",
            focus_facets=("simplify",),
            preview_fixes=True,
            review_mode="full",
        )
    )

    assert exit_code == 1
    assert output == str(tmp_path / "review-report.json")
    assert target.read_text(encoding="utf-8") == source
    previewed = ReviewReport.model_validate_json((tmp_path / "review-report.json").read_text(encoding="utf-8"))
    assert previewed.cleanup_forecast is not None
    assert previewed.cleanup_forecast.preview_evidence_count == 1
    assert previewed.findings[0].remediation_packet is not None
    assert previewed.findings[0].remediation_packet.patch_forecast_refs == [f"preview:{target}:2"]


def test_with_mutation_records_inconclusive_evidence_for_missing_tool(monkeypatch: Any, tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text(
        "def total(values: list[int]) -> int:\n    result = sum(values)\n    return result\n", encoding="utf-8"
    )
    report = _safe_mechanical_report(target, line=2, rule="ai-bloat.redundant-intermediate")
    monkeypatch.setattr("specfact_code_review.run.commands.run_review", lambda files, **kwargs: report)
    monkeypatch.setattr("specfact_code_review.run.cleanup_evidence._mutation_tool_available", lambda: False)

    exit_code, output = run_commands.run_command(
        run_commands.ReviewRunRequest(
            files=[target],
            json_output=True,
            out=tmp_path / "review-report.json",
            focus_facets=("simplify",),
            with_mutation=True,
            review_mode="full",
        )
    )

    assert exit_code == 1
    assert output == str(tmp_path / "review-report.json")
    mutation_report = ReviewReport.model_validate_json((tmp_path / "review-report.json").read_text(encoding="utf-8"))
    assert mutation_report.findings[0].signal_trace is not None
    assert mutation_report.findings[0].signal_trace[-1].source == "mutation"
    assert mutation_report.findings[0].signal_trace[-1].value == "inconclusive: mutmut unavailable"


def _blocking_shadow_report(target: Path) -> ReviewReport:
    return ReviewReport(
        run_id="review-run-001",
        timestamp=datetime(2026, 3, 16, tzinfo=UTC),
        score=85,
        findings=[
            ReviewFinding(
                category="tool_error",
                severity="error",
                tool="ast",
                rule="tool_error",
                file=str(target),
                line=1,
                message="Unable to parse Python source.",
                fixable=False,
            )
        ],
        summary="Shadow-mode report with blocking finding.",
    ).model_copy(update={"ci_exit_code": 0})


@pytest.mark.parametrize("evidence_flag", ["preview_fixes", "with_mutation"])
def test_cleanup_evidence_preserves_shadow_mode_ci_exit(
    monkeypatch: Any,
    tmp_path: Path,
    evidence_flag: str,
) -> None:
    target = tmp_path / "sample.py"
    target.write_text("def total(values: list[int]) -> int:\n    return sum(values)\n", encoding="utf-8")
    monkeypatch.setattr(
        "specfact_code_review.run.commands.run_review", lambda files, **kwargs: _blocking_shadow_report(target)
    )
    monkeypatch.setattr("specfact_code_review.run.cleanup_evidence._mutation_tool_available", lambda: False)

    request = run_commands.ReviewRunRequest(
        files=[target],
        json_output=True,
        out=tmp_path / "review-report.json",
        focus_facets=("simplify",),
        review_mode="shadow",
    )
    if evidence_flag == "preview_fixes":
        request = run_commands.ReviewRunRequest(**{**request.__dict__, "preview_fixes": True})
    else:
        request = run_commands.ReviewRunRequest(**{**request.__dict__, "with_mutation": True})

    exit_code, output = run_commands.run_command(request)

    assert exit_code == 0
    assert output == str(tmp_path / "review-report.json")
    report_payload = json.loads((tmp_path / "review-report.json").read_text(encoding="utf-8"))
    assert report_payload["ci_exit_code"] == 0


def test_apply_simplification_fixes_inlines_redundant_intermediate(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text(
        "def total(values: list[int]) -> int:\n    result = sum(values)\n    return result\n",
        encoding="utf-8",
    )

    applied = run_commands._apply_simplification_fixes(
        _safe_mechanical_report(target, line=2, rule="ai-bloat.redundant-intermediate")
    )

    assert len(applied) == 1
    assert target.read_text(encoding="utf-8") == "def total(values: list[int]) -> int:\n    return sum(values)\n"


def test_apply_simplification_fixes_skips_non_safe_guidance(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    source = "def total(values: list[int]) -> int:\n    result = []\n    return result\n"
    target.write_text(source, encoding="utf-8")
    report = _safe_mechanical_report(target, line=2, rule="ai-bloat.redundant-intermediate")
    report.findings[0].guidance_kind = "needs_tests"

    applied = run_commands._apply_simplification_fixes(report)

    assert len(applied) == 0
    assert target.read_text(encoding="utf-8") == source


def test_apply_simplification_fixes_collapses_verbose_bool_return(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text(
        "def allowed(role: str) -> bool:\n    if role == 'admin':\n        return True\n    return False\n",
        encoding="utf-8",
    )

    applied = run_commands._apply_simplification_fixes(
        _safe_mechanical_report(target, line=2, rule="ai-bloat.verbose-bool-return")
    )

    assert len(applied) == 1
    assert target.read_text(encoding="utf-8") == "def allowed(role: str) -> bool:\n    return role == 'admin'\n"


def test_apply_simplification_fixes_removes_dead_branch(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text(
        "def classify(value: int) -> str:\n"
        "    if value > 10:\n"
        "        return 'large'\n"
        "    if value > 10:\n"
        "        return 'still large'\n"
        "    return 'small'\n",
        encoding="utf-8",
    )

    applied = run_commands._apply_simplification_fixes(
        _safe_mechanical_report(target, line=4, rule="ai-bloat.dead-branch")
    )

    assert len(applied) == 1
    assert target.read_text(encoding="utf-8") == (
        "def classify(value: int) -> str:\n    if value > 10:\n        return 'large'\n    return 'small'\n"
    )


def test_apply_simplification_fixes_keeps_dead_branch_with_else(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    source = (
        "def classify(value: int) -> str:\n"
        "    if value > 10:\n"
        "        return 'large'\n"
        "    if value > 10:\n"
        "        return 'still large'\n"
        "    else:\n"
        "        return 'fallback'\n"
        "    return 'small'\n"
    )
    target.write_text(source, encoding="utf-8")

    applied = run_commands._apply_simplification_fixes(
        _safe_mechanical_report(target, line=4, rule="ai-bloat.dead-branch")
    )

    assert len(applied) == 0
    assert target.read_text(encoding="utf-8") == source


def test_apply_simplification_fixes_keeps_impure_duplicate_guard(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    source = (
        "def classify(value: object) -> str:\n"
        "    if value.ready():\n"
        "        return 'ready'\n"
        "    if value.ready():\n"
        "        return 'still ready'\n"
        "    return 'not ready'\n"
    )
    target.write_text(source, encoding="utf-8")

    applied = run_commands._apply_simplification_fixes(
        _safe_mechanical_report(target, line=4, rule="ai-bloat.dead-branch")
    )

    assert len(applied) == 0
    assert target.read_text(encoding="utf-8") == source


def test_apply_simplification_fixes_keeps_dead_branch_after_assignment(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    source = (
        "def classify(value: int) -> str:\n"
        "    if value > 10:\n"
        "        return 'large'\n"
        "    value = 12\n"
        "    if value > 10:\n"
        "        return 'now large'\n"
        "    return 'small'\n"
    )
    target.write_text(source, encoding="utf-8")

    applied = run_commands._apply_simplification_fixes(
        _safe_mechanical_report(target, line=5, rule="ai-bloat.dead-branch")
    )

    assert len(applied) == 0
    assert target.read_text(encoding="utf-8") == source


def test_apply_simplification_fixes_removes_pass_through_try_except(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text(
        "def parse(raw: str) -> object:\n"
        "    try:\n"
        "        return parse_json(raw)\n"
        "    except Exception:\n"
        "        raise\n",
        encoding="utf-8",
    )

    applied = run_commands._apply_simplification_fixes(
        _safe_mechanical_report(target, line=2, rule="ai-bloat.pass-through-try-except")
    )

    assert len(applied) == 1
    assert target.read_text(encoding="utf-8") == "def parse(raw: str) -> object:\n    return parse_json(raw)\n"


def test_apply_simplification_fixes_uses_bottom_up_line_order(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text(
        "def total(values: list[int]) -> int:\n"
        "    result = sum(values)\n"
        "    return result\n"
        "\n"
        "def classify(value: int) -> str:\n"
        "    if value > 10:\n"
        "        return 'large'\n"
        "    if value > 10:\n"
        "        return 'still large'\n"
        "    return 'small'\n",
        encoding="utf-8",
    )
    report = ReviewReport(
        run_id="review-run-001",
        timestamp=datetime(2026, 3, 16, tzinfo=UTC),
        score=85,
        findings=[
            _safe_mechanical_finding(target, line=2, rule="ai-bloat.redundant-intermediate"),
            _safe_mechanical_finding(target, line=8, rule="ai-bloat.dead-branch"),
        ],
        summary="Review command test report.",
    )

    applied = run_commands._apply_simplification_fixes(report)

    assert len(applied) == 2
    assert target.read_text(encoding="utf-8") == (
        "def total(values: list[int]) -> int:\n"
        "    return sum(values)\n"
        "\n"
        "def classify(value: int) -> str:\n"
        "    if value > 10:\n"
        "        return 'large'\n"
        "    return 'small'\n"
    )


def test_apply_simplification_fixes_skips_when_source_no_longer_matches(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    source = "def total(values: list[int]) -> int:\n    result = sum(values)\n    return result + 1\n"
    target.write_text(source, encoding="utf-8")

    applied = run_commands._apply_simplification_fixes(
        _safe_mechanical_report(target, line=2, rule="ai-bloat.redundant-intermediate")
    )

    assert len(applied) == 0
    assert target.read_text(encoding="utf-8") == source


def test_run_review_once_applies_simplification_fixes_before_rerun(monkeypatch: Any, tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text(
        "def total(values: list[int]) -> int:\n    result = sum(values)\n    return result\n",
        encoding="utf-8",
    )
    reports = [
        _safe_mechanical_report(target, line=2, rule="ai-bloat.redundant-intermediate"),
        _report(),
    ]
    monkeypatch.setattr("specfact_code_review.run.commands.run_review", lambda files, **kwargs: reports.pop(0))
    monkeypatch.setattr("specfact_code_review.run.commands._apply_fixes", lambda files: None)

    report = run_commands._run_review_once(
        [target],
        run_commands._ReviewLoopFlags(
            no_tests=True,
            include_noise=False,
            fix=True,
            preview_fixes=False,
            with_mutation=False,
            progress_callback=None,
            bug_hunt=False,
            review_mode="full",
            review_level=None,
            review_focus="simplify",
        ),
    )

    assert len(report.findings) == 1
    assert report.findings[0].action_status == "applied"
    assert report.findings[0].before_ref is not None
    assert report.findings[0].after_ref is not None
    assert report.findings[0].improvement is not None
    assert target.read_text(encoding="utf-8") == "def total(values: list[int]) -> int:\n    return sum(values)\n"


def test_run_command_rejects_unknown_keyword_override() -> None:
    with pytest.raises(run_commands.RunCommandError, match="Unexpected keyword arguments: unknown"):
        run_commands.run_command([], unknown=True)


def test_run_command_rejects_focus_with_no_matching_files(monkeypatch: Any, tmp_path: Path) -> None:
    docs_file = _write_repo_file(tmp_path, "docs/helpers/example.py")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(run_commands.NoReviewableFilesError, match="No reviewable Python files matched"):
        run_commands.run_command(
            run_commands.ReviewRunRequest(
                files=[docs_file],
                focus_facets=("source",),
            )
        )


def test_filter_files_by_focus_unions_source_tests_and_docs() -> None:
    source_file = Path("packages/specfact-code-review/src/specfact_code_review/run/commands.py")
    test_file = Path("tests/unit/specfact_code_review/run/test_commands.py")
    docs_file = Path("docs/tools/example.py")
    text_file = Path("docs/readme.md")

    assert run_commands._filter_files_by_focus(
        [source_file, test_file, docs_file, text_file],
        ("source", "tests", "docs"),
    ) == [source_file, test_file, docs_file]


def test_run_command_ignores_dot_specfact_in_changed_scope(monkeypatch: Any, tmp_path: Path) -> None:
    package_file = _write_repo_file(
        tmp_path,
        "packages/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    ignored_file = _write_repo_file(
        tmp_path,
        ".specfact/modules/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    monkeypatch.chdir(tmp_path)

    recorded: dict[str, list[Path]] = {}
    monkeypatch.setattr(
        "specfact_code_review.run.commands._changed_files_from_git_diff",
        lambda *, include_tests: [ignored_file, package_file],
    )

    def fake_run_review(files: list[Path], **_kwargs: Any) -> ReviewReport:
        recorded["files"] = files
        return _report()

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", fake_run_review)

    result = runner.invoke(app, ["review", "run", "--json", "--out", "review-report.json"])

    assert result.exit_code == 0
    assert recorded["files"] == [package_file]


def test_run_command_ignores_hidden_directory_in_changed_scope(monkeypatch: Any, tmp_path: Path) -> None:
    package_file = _write_repo_file(
        tmp_path,
        "packages/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    ignored_file = _write_repo_file(
        tmp_path,
        ".cache/review-work/specfact_code_review/run/commands.py",
    )
    monkeypatch.chdir(tmp_path)

    recorded: dict[str, list[Path]] = {}
    monkeypatch.setattr(
        "specfact_code_review.run.commands._changed_files_from_git_diff",
        lambda *, include_tests: [ignored_file, package_file],
    )

    def fake_run_review(files: list[Path], **_kwargs: Any) -> ReviewReport:
        recorded["files"] = files
        return _report()

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", fake_run_review)

    result = runner.invoke(app, ["review", "run", "--json", "--out", "review-report.json"])

    assert result.exit_code == 0
    assert recorded["files"] == [package_file]


def test_run_command_ignores_dot_specfact_in_full_scope(monkeypatch: Any, tmp_path: Path) -> None:
    package_file = _write_repo_file(
        tmp_path,
        "packages/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    ignored_file = _write_repo_file(
        tmp_path,
        ".specfact/modules/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    monkeypatch.chdir(tmp_path)

    recorded: dict[str, list[Path]] = {}
    monkeypatch.setattr(
        "specfact_code_review.run.commands._all_python_files_from_git",
        lambda: [ignored_file, package_file],
        raising=False,
    )

    def fake_run_review(files: list[Path], **_kwargs: Any) -> ReviewReport:
        recorded["files"] = files
        return _report()

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", fake_run_review)

    result = runner.invoke(
        app,
        ["review", "run", "--scope", "full", "--json", "--out", "review-report.json"],
    )

    assert result.exit_code == 0
    assert recorded["files"] == [package_file]


def test_run_command_ignores_hidden_directory_in_full_scope(monkeypatch: Any, tmp_path: Path) -> None:
    package_file = _write_repo_file(
        tmp_path,
        "packages/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    ignored_file = _write_repo_file(
        tmp_path,
        ".cache/review-work/specfact_code_review/run/commands.py",
    )
    monkeypatch.chdir(tmp_path)

    recorded: dict[str, list[Path]] = {}
    monkeypatch.setattr(
        "specfact_code_review.run.commands._all_python_files_from_git",
        lambda: [ignored_file, package_file],
        raising=False,
    )

    def fake_run_review(files: list[Path], **_kwargs: Any) -> ReviewReport:
        recorded["files"] = files
        return _report()

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", fake_run_review)

    result = runner.invoke(
        app,
        ["review", "run", "--scope", "full", "--json", "--out", "review-report.json"],
    )

    assert result.exit_code == 0
    assert recorded["files"] == [package_file]


def test_run_command_ignores_dot_specfact_positional_file(monkeypatch: Any, tmp_path: Path) -> None:
    project_file = _write_repo_file(
        tmp_path,
        ".specfact/modules/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "specfact_code_review.run.commands.run_review",
        lambda files, **_kwargs: _report(),
    )

    result = runner.invoke(app, ["review", "run", str(project_file)])

    assert result.exit_code == 2
    assert "no python files to review" in result.output.lower()


def test_run_command_ignores_hidden_directory_positional_file(monkeypatch: Any, tmp_path: Path) -> None:
    project_file = _write_repo_file(
        tmp_path,
        ".cache/review-work/specfact_code_review/run/commands.py",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "specfact_code_review.run.commands.run_review",
        lambda files, **_kwargs: _report(),
    )

    result = runner.invoke(app, ["review", "run", str(project_file)])

    assert result.exit_code == 2
    assert "no python files to review" in result.output.lower()


def test_run_command_rejects_out_without_json(tmp_path: Path) -> None:
    out = tmp_path / "review-report.json"
    result = runner.invoke(app, ["review", "run", "--out", str(out), "tests/fixtures/review/clean_module.py"])

    assert result.exit_code == 2
    assert "Use " in result.output
    assert "out" in result.output
    assert "json" in result.output


def test_run_help_does_not_render_nested_command_suffix() -> None:
    result = runner.invoke(app, ["review", "run", "--help"])

    assert result.exit_code == 0
    assert "COMMAND [ARGS]" not in result.output


def test_run_command_rejects_json_and_score_only_together() -> None:
    result = runner.invoke(
        app,
        [
            "review",
            "run",
            "--json",
            "--score-only",
            "tests/fixtures/review/clean_module.py",
        ],
    )

    assert result.exit_code == 2
    assert "Use either " in result.output
    assert "json" in result.output
    assert "score" in result.output
    assert "not both" in result.output


def test_run_command_rejects_scope_mixed_with_positional_files() -> None:
    result = runner.invoke(
        app,
        [
            "review",
            "run",
            "tests/fixtures/review/clean_module.py",
            "--scope",
            "full",
        ],
    )

    assert result.exit_code == 2
    assert "choose positional files or auto-scope controls" in result.output.lower()


def test_run_command_rejects_path_mixed_with_positional_files() -> None:
    result = runner.invoke(
        app,
        [
            "review",
            "run",
            "tests/fixtures/review/clean_module.py",
            "--path",
            "tests/fixtures/review",
        ],
    )

    assert result.exit_code == 2
    assert "choose positional files or auto-scope controls" in result.output.lower()


def test_run_command_fix_mode_applies_fixes_before_second_run(monkeypatch: Any) -> None:
    calls: list[str] = []

    def fake_run_review(_files: list[Path], **_kwargs: Any) -> ReviewReport:
        calls.append("run_review")
        return _report()

    monkeypatch.setattr("specfact_code_review.run.commands.run_review", fake_run_review)
    monkeypatch.setattr(
        "specfact_code_review.run.commands._apply_fixes",
        lambda files: calls.append("apply_fixes"),
    )

    result = runner.invoke(app, ["review", "run", "--fix", "tests/fixtures/review/clean_module.py"])

    assert result.exit_code == 0
    assert calls == ["run_review", "apply_fixes", "run_review"]


def test_run_command_default_output_renders_findings(monkeypatch: Any) -> None:
    report = ReviewReport(
        run_id="review-run-002",
        timestamp=datetime(2026, 3, 16, tzinfo=UTC),
        score=70,
        findings=[
            ReviewFinding(
                category="style",
                severity="warning",
                tool="ruff",
                rule="F401",
                file="tests/fixtures/review/clean_module.py",
                line=1,
                message="Unused import.",
                fixable=True,
            )
        ],
        summary="Rendered output report.",
    )
    monkeypatch.setattr("specfact_code_review.run.commands.run_review", lambda files, **_kwargs: report)

    result = runner.invoke(app, ["review", "run", "tests/fixtures/review/clean_module.py"])

    assert result.exit_code == 0
    assert "Code Review: style" in result.output
    assert "Rendered output report." in result.output


def test_run_command_fails_when_scope_and_paths_match_no_files(monkeypatch: Any, tmp_path: Path) -> None:
    package_file = _write_repo_file(
        tmp_path,
        "packages/specfact-code-review/src/specfact_code_review/run/commands.py",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "specfact_code_review.run.commands._all_python_files_from_git",
        lambda: [package_file],
        raising=False,
    )

    result = runner.invoke(
        app,
        [
            "review",
            "run",
            "--scope",
            "full",
            "--path",
            "packages/specfact-backlog",
        ],
    )

    assert result.exit_code == 2
    assert "no reviewable files" in result.output.lower()
    assert "scope" in result.output.lower()
    assert "full" in result.output.lower()


def test_changed_files_from_git_diff_filters_python_files(monkeypatch: Any, tmp_path: Path) -> None:
    python_file = tmp_path / "example.py"
    python_file.write_text("VALUE = 1\n", encoding="utf-8")
    text_file = tmp_path / "README.md"
    text_file.write_text("hi\n", encoding="utf-8")

    def _fake_run(*args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        command = args[0]
        if command[:3] == ["git", "diff", "HEAD"]:
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout=f"{python_file}\0{text_file}\0missing.py\0",
                stderr="",
            )
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    changed_files_from_git_diff = vars(run_commands)["_changed_files_from_git_diff"]

    assert changed_files_from_git_diff(include_tests=False) == [python_file]


def test_changed_files_from_git_diff_excludes_test_files_by_default(monkeypatch: Any, tmp_path: Path) -> None:
    source_file = tmp_path / "example.py"
    source_file.write_text("VALUE = 1\n", encoding="utf-8")
    test_file = tmp_path / "tests/unit/test_example.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    def _fake_run(*args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        command = args[0]
        if command[:3] == ["git", "diff", "HEAD"]:
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout=f"{source_file}\0{test_file}\0",
                stderr="",
            )
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    changed_files_from_git_diff = vars(run_commands)["_changed_files_from_git_diff"]

    assert changed_files_from_git_diff(include_tests=False) == [source_file]
    assert changed_files_from_git_diff(include_tests=True) == [source_file, test_file]


def test_changed_files_from_git_diff_includes_untracked_python_files(monkeypatch: Any, tmp_path: Path) -> None:
    tracked_file = tmp_path / "tracked.py"
    tracked_file.write_text("VALUE = 1\n", encoding="utf-8")
    untracked_file = tmp_path / "new_file.py"
    untracked_file.write_text("VALUE = 2\n", encoding="utf-8")

    def _fake_run(*args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        command = args[0]
        if command[:3] == ["git", "diff", "HEAD"]:
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout=f"{tracked_file}\0",
                stderr="",
            )
        if command[:4] == ["git", "ls-files", "--others", "--exclude-standard"]:
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout=f"{untracked_file}\0",
                stderr="",
            )
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    changed_files_from_git_diff = vars(run_commands)["_changed_files_from_git_diff"]

    assert changed_files_from_git_diff(include_tests=False) == [tracked_file, untracked_file]


def test_apply_fixes_raises_when_format_command_fails(monkeypatch: Any) -> None:
    calls = {"count": 0}

    def _fake_run(*args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls["count"] += 1
        if calls["count"] == 1:
            return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")
        return subprocess.CompletedProcess(args=args[0], returncode=2, stdout="", stderr="format failed")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    apply_fixes = vars(run_commands)["_apply_fixes"]

    with pytest.raises(RuntimeError, match="format failed"):
        apply_fixes([Path("tests/fixtures/review/clean_module.py")])


def test_run_command_rejects_missing_files() -> None:
    result = runner.invoke(app, ["review", "run", "tests/fixtures/review/missing.py"])

    assert result.exit_code == 2
    assert "not found" in result.output.lower()
