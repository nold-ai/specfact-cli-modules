from __future__ import annotations

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


def test_pr_orchestrator_verify_pr_to_dev_passes_integrity_shape_flag() -> None:
    workflow = _workflow_text()
    assert "--metadata-only" in workflow
    assert '[ "$TARGET_BRANCH" = "dev" ]' in workflow
    dev_guard = 'if [ "$TARGET_BRANCH" = "dev" ]; then'
    metadata_append = "VERIFY_CMD+=(--metadata-only)"
    assert dev_guard in workflow
    assert metadata_append in workflow
    assert workflow.index(dev_guard) < workflow.index(metadata_append)


def test_pr_orchestrator_verify_require_signature_on_main_paths() -> None:
    workflow = _workflow_text()
    main_pr_guard = 'elif [ "$TARGET_BRANCH" = "main" ]; then'
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
