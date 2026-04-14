from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _workflow_text() -> str:
    path = REPO_ROOT / ".github" / "workflows" / "sign-modules-on-approval.yml"
    return path.read_text(encoding="utf-8")


def test_sign_modules_on_approval_trigger_and_job_filter() -> None:
    workflow = _workflow_text()
    assert "pull_request_review:" in workflow
    assert "types:" in workflow
    assert "submitted" in workflow
    assert "github.event.review.state == 'approved'" in workflow
    assert "github.event.pull_request.base.ref == 'dev'" in workflow
    assert "github.event.pull_request.base.ref == 'main'" in workflow
    assert "github.event.pull_request.head.repo.full_name == github.repository" in workflow


def test_sign_modules_on_approval_checkout_and_python() -> None:
    workflow = _workflow_text()
    assert "actions/checkout@v4" in workflow
    assert "github.event.pull_request.head.ref" in workflow
    assert "PR_HEAD_REF:" in workflow
    assert "PR_BASE_REF:" in workflow
    assert 'python-version: "3.12"' in workflow or "python-version: '3.12'" in workflow


def test_sign_modules_on_approval_dependencies_and_discover() -> None:
    workflow = _workflow_text()
    assert "beartype" in workflow and "icontract" in workflow
    assert "cryptography" in workflow and "cffi" in workflow
    assert "mapfile -t MANIFESTS" in workflow
    assert "find packages -name 'module-package.yaml'" in workflow
    assert "manifests_count=" in workflow
    assert "GITHUB_OUTPUT" in workflow
    assert "id: discover" in workflow


def test_sign_modules_on_approval_sign_and_secrets() -> None:
    workflow = _workflow_text()
    assert "Guard signing secrets" in workflow
    assert '[ -z "${SPECFACT_MODULE_PRIVATE_SIGN_KEY:-}" ]' in workflow
    assert "exit 1" in workflow
    assert "MERGE_BASE=" in workflow
    assert "git merge-base HEAD" in workflow
    assert 'git fetch origin "${PR_BASE_REF}"' in workflow
    assert "--no-tags" in workflow
    assert "scripts/sign-modules.py" in workflow
    assert "--changed-only" in workflow
    assert "--base-ref" in workflow
    assert '"$MERGE_BASE"' in workflow
    assert "--bump-version patch" in workflow
    assert "--payload-from-filesystem" in workflow
    assert "SPECFACT_MODULE_PRIVATE_SIGN_KEY" in workflow
    assert "SPECFACT_MODULE_PRIVATE_SIGN_KEY_PASSPHRASE" in workflow


def test_sign_modules_on_approval_commit_push_and_summary() -> None:
    workflow = _workflow_text()
    assert "github-actions[bot]" in workflow
    assert "chore(modules): ci sign changed modules [skip ci]" in workflow
    assert "HEAD:${PR_HEAD_REF}" in workflow
    assert "GITHUB_STEP_SUMMARY" in workflow
    assert "COMMIT_CHANGED:" in workflow
    assert "MANIFESTS_COUNT:" in workflow
    assert "steps.discover.outputs.manifests_count" in workflow
