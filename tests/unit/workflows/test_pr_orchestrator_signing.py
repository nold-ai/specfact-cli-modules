from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _workflow_text() -> str:
    return (REPO_ROOT / ".github" / "workflows" / "pr-orchestrator.yml").read_text(encoding="utf-8")


def test_pr_orchestrator_verify_has_core_verifier_flags() -> None:
    workflow = _workflow_text()
    assert "verify-module-signatures" in workflow
    assert "scripts/verify-modules-signature.py" in workflow
    assert "--payload-from-filesystem" in workflow
    assert "--enforce-version-bump" in workflow
    assert "github.event.pull_request.base.ref" in workflow
    assert "TARGET_BRANCH" in workflow
    assert "github.ref_name" in workflow
    assert "VERIFY_CMD" in workflow


def test_pr_orchestrator_pr_to_dev_verifier_omits_loose_integrity_mode() -> None:
    workflow = _workflow_text()
    assert "--metadata-only" not in workflow


def test_pr_orchestrator_push_uses_github_event_before_for_version_base() -> None:
    workflow = _workflow_text()
    assert 'BEFORE="${{ github.event.before }}"' in workflow
    assert 'VERIFY_CMD+=(--version-check-base "$BEFORE")' in workflow
    assert "0000000000000000000000000000000000000000" in workflow


def test_pr_orchestrator_installs_pinned_specfact_cli() -> None:
    workflow = _workflow_text()
    assert "actions/checkout@v4" in workflow
    assert "repository: nold-ai/specfact-cli" in workflow
    assert "id: core-ref" in workflow
    assert "git ls-remote --exit-code --heads https://github.com/nold-ai/specfact-cli.git" in workflow
    assert "FALLBACK_REF: ${{ github.base_ref || github.ref_name }}" in workflow
    assert 'echo "ref=$fallback" >> "$GITHUB_OUTPUT"' in workflow
    assert "ref: ${{ steps.core-ref.outputs.ref }}" in workflow
    assert "ref: dev" not in workflow
    assert "hatch run pip install -e ./specfact-cli" in workflow
    assert "hatch run python specfact-cli/scripts/runtime_discovery_smoke.py" in workflow


def test_pr_orchestrator_pins_exact_core_schema_smoke() -> None:
    workflow = _workflow_text()

    assert "exact-core-schema-compatibility" in workflow
    assert '["3.11", "3.12", "3.13"]' in workflow
    assert "refs/tags/v0.55.1" in workflow
    assert "b1e517e60e669eaba15a18ecfa83ef5a9df65276" in workflow
    assert "47984be5434d7ae65ed6908bf525a32053290337" in workflow
    assert "===0.55.1" in workflow
    assert "test_core_0_55_1_runtime_loads_schema_1_6_consumer_matrix" in workflow
    assert "pip install" in workflow
    assert "--no-cache-dir" in workflow


def test_pr_orchestrator_rejects_pep440_local_core_alias() -> None:
    workflow = _workflow_text()

    assert "0.55.1+vendor" in workflow
    assert "==0.55.1" in workflow
    assert "reject-core-version-alias" in workflow
    exact_job = workflow.split("exact-core-schema-compatibility:", maxsplit=1)[1]
    assert "ref: dev" not in exact_job
    assert "ref: main" not in exact_job
    assert "FALLBACK_REF" not in exact_job


def test_pr_orchestrator_has_single_full_pytest_owner() -> None:
    workflow = _workflow_text()
    assert "hatch run contract-test-contracts" in workflow
    assert "hatch run smart-test-check" in workflow
    assert "hatch run test" in workflow
    assert "hatch run contract-test\n" not in workflow
    assert "hatch run smart-test\n" not in workflow
    full_suite_runs = re.findall(r"run:\s+hatch run (test|smart-test(?:-full)?|contract-test)(?!-)\b", workflow)
    assert full_suite_runs == ["test"]


def test_pr_orchestrator_verify_require_signature_on_main_paths() -> None:
    workflow = _workflow_text()
    main_pr_guard = 'if [ "$TARGET_BRANCH" = "main" ]; then'
    main_ref_guard = '[ "${{ github.ref_name }}" = "main" ]; then'
    require_append = "VERIFY_CMD+=(--require-signature)"
    assert main_pr_guard in workflow
    assert main_ref_guard in workflow
    assert require_append in workflow
    assert workflow.count(require_append) == 2
    push_require_block = (
        'if [ "${{ github.ref_name }}" = "main" ]; then\n              VERIFY_CMD+=(--require-signature)'
    )
    assert push_require_block in workflow
    assert "--require-signature" in workflow
