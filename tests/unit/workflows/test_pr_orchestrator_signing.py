from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_pr_orchestrator_verify_splits_signature_requirement_by_target_branch() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "pr-orchestrator.yml").read_text(encoding="utf-8")

    assert "verify-module-signatures" in workflow
    assert "scripts/verify-modules-signature.py" in workflow
    assert "--payload-from-filesystem" in workflow
    assert "--enforce-version-bump" in workflow
    assert "github.event.pull_request.base.ref" in workflow
    assert "TARGET_BRANCH" in workflow
    assert "GITHUB_REF#refs/heads/" in workflow or "${GITHUB_REF#refs/heads/}" in workflow
    branch_guard = 'if [ "$TARGET_BRANCH" = "main" ]; then'
    require_append = "VERIFY_CMD+=(--require-signature)"
    assert branch_guard in workflow
    assert require_append in workflow
    assert workflow.index(branch_guard) < workflow.index(require_append)
    assert "--require-signature" in workflow
    assert "VERIFY_CMD" in workflow
