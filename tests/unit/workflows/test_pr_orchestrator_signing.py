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
    assert '[ "$TARGET_BRANCH" = "main" ]' in workflow
    assert "--require-signature" in workflow
    # Dev (and non-main) path must omit full signature enforcement: script invoked without the flag
    # when targeting dev — enforced by pairing VERIFY_CMD construction with the branch check.
    assert "VERIFY_CMD" in workflow
    assert "VERIFY_CMD+=(--require-signature)" in workflow
