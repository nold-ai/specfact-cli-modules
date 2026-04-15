from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]


def _workflow_text() -> str:
    path = REPO_ROOT / ".github" / "workflows" / "sign-modules-on-approval.yml"
    return path.read_text(encoding="utf-8")


def _parsed_workflow() -> dict[Any, Any]:
    loaded = yaml.safe_load(_workflow_text())
    assert isinstance(loaded, dict)
    return cast(dict[Any, Any], loaded)


def _workflow_on_section(doc: dict[Any, Any]) -> dict[str, Any]:
    """Top-level workflow triggers. PyYAML 1.1 parses the key ``on`` as bool ``True``."""
    section = doc.get(True)
    if isinstance(section, dict):
        return cast(dict[str, Any], section)
    raw = doc.get("on")
    assert isinstance(raw, dict)
    return cast(dict[str, Any], raw)


def _sign_modules_job(doc: dict[Any, Any]) -> dict[str, Any]:
    jobs = doc["jobs"]
    assert isinstance(jobs, dict)
    job = jobs["sign-modules"]
    assert isinstance(job, dict)
    return cast(dict[str, Any], job)


def _step_by_field(steps: list[Any], field: str, value: str) -> dict[str, Any]:
    for raw in steps:
        if isinstance(raw, dict) and raw.get(field) == value:
            return cast(dict[str, Any], raw)
    raise AssertionError(f"No workflow step with {field}={value!r}")


def _assert_pull_request_review_submitted(doc: dict[Any, Any]) -> None:
    on = _workflow_on_section(doc)
    pr_review = on["pull_request_review"]
    assert isinstance(pr_review, dict)
    assert pr_review["types"] == ["submitted"]


def _assert_sign_job_has_no_top_level_if(doc: dict[Any, Any]) -> None:
    job = _sign_modules_job(doc)
    assert "if" not in job, "Job-level `if` prevents a stable required check; gating belongs in steps"


def _assert_eligibility_gate_step(doc: dict[Any, Any]) -> None:
    job = _sign_modules_job(doc)
    steps = job["steps"]
    assert isinstance(steps, list)
    gate = steps[0]
    assert isinstance(gate, dict)
    assert gate.get("name") == "Eligibility gate (required status check)"
    assert gate.get("id") == "gate"
    run = gate["run"]
    assert isinstance(run, str)
    assert "github.event.review.state" in run
    assert "github.event.review.user.author_association" in run
    assert "approved" in run
    assert "COLLABORATOR|MEMBER|OWNER" in run
    assert 'echo "sign=false"' in run
    assert 'echo "sign=true"' in run
    assert "github.event.pull_request.base.ref" in run
    assert "github.event.pull_request.head.repo.full_name" in run
    assert "github.repository" in run


def _assert_concurrency_and_permissions(doc: dict[Any, Any]) -> None:
    conc = doc["concurrency"]
    assert isinstance(conc, dict)
    assert conc["cancel-in-progress"] is True
    assert "${{ github.event.pull_request.number }}" in conc["group"]

    perms = doc["permissions"]
    assert isinstance(perms, dict)
    assert perms["contents"] == "write"


def test_sign_modules_on_approval_trigger_and_job_filter() -> None:
    doc = _parsed_workflow()
    _assert_pull_request_review_submitted(doc)
    _assert_sign_job_has_no_top_level_if(doc)
    _assert_eligibility_gate_step(doc)
    _assert_concurrency_and_permissions(doc)


def test_sign_modules_on_approval_checkout_and_python() -> None:
    workflow = _workflow_text()
    assert "actions/checkout@v4" in workflow
    assert "github.event.pull_request.head.sha" in workflow
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


def test_sign_modules_on_approval_secrets_guard() -> None:
    job = _sign_modules_job(_parsed_workflow())
    steps = job["steps"]
    assert isinstance(steps, list)
    guard = _step_by_field(steps, "name", "Guard signing secrets")
    run = guard["run"]
    assert isinstance(run, str)
    assert '[ -z "${SPECFACT_MODULE_PRIVATE_SIGN_KEY:-}" ]' in run
    assert '[ -z "${SPECFACT_MODULE_PRIVATE_SIGN_KEY_PASSPHRASE:-}" ]' in run
    assert 'echo "::error::Missing secret: SPECFACT_MODULE_PRIVATE_SIGN_KEY"' in run
    assert 'echo "::error::Missing secret: SPECFACT_MODULE_PRIVATE_SIGN_KEY_PASSPHRASE"' in run
    assert run.count("exit 1") >= 2


def test_sign_modules_on_approval_sign_step_merge_base() -> None:
    workflow = _workflow_text()
    assert "merge-base" in workflow
    assert "git merge-base HEAD" in workflow
    assert 'git fetch origin "${PR_BASE_REF}"' in workflow
    assert "--no-tags" in workflow
    assert "scripts/sign-modules.py" in workflow
    assert "--changed-only" in workflow
    assert "--base-ref" in workflow
    assert '"$MERGE_BASE"' in workflow
    assert "--bump-version patch" in workflow
    assert "--payload-from-filesystem" in workflow
    assert "steps.gate.outputs.sign == 'true'" in workflow
    assert '--base-ref "origin/' not in workflow


def _assert_discover_step_writes_outputs(steps: list[Any]) -> None:
    discover = _step_by_field(steps, "id", "discover")
    discover_run = discover["run"]
    assert isinstance(discover_run, str)
    assert "manifests_count=" in discover_run
    assert "GITHUB_OUTPUT" in discover_run


def _assert_commit_and_push_step(steps: list[Any]) -> None:
    commit_step = _step_by_field(steps, "name", "Commit and push signed manifests")
    assert commit_step.get("id") == "commit"
    commit_run = commit_step["run"]
    assert isinstance(commit_run, str)
    assert 'git commit -m "chore(modules): ci sign changed modules [skip ci]"' in commit_run
    assert 'git push origin "HEAD:${PR_HEAD_REF}"' in commit_run
    assert "Push to ${PR_HEAD_REF} failed" in commit_run


def _assert_job_summary_step(steps: list[Any]) -> None:
    summary = _step_by_field(steps, "name", "Write job summary")
    assert summary.get("if") == "always()"
    env = summary["env"]
    assert isinstance(env, dict)
    assert env["COMMIT_CHANGED"] == "${{ steps.commit.outputs.changed || '' }}"
    assert env["MANIFESTS_COUNT"] == "${{ steps.discover.outputs.manifests_count || '' }}"
    assert env["GATE_SIGN"] == "${{ steps.gate.outputs.sign }}"
    summary_run = summary["run"]
    assert isinstance(summary_run, str)
    assert "GITHUB_STEP_SUMMARY" in summary_run


def test_sign_modules_on_approval_commit_push_and_summary() -> None:
    job = _sign_modules_job(_parsed_workflow())
    steps = job["steps"]
    assert isinstance(steps, list)
    _assert_discover_step_writes_outputs(steps)
    _assert_commit_and_push_step(steps)
    _assert_job_summary_step(steps)
