"""Trust-boundary contracts for paired core workflow checkouts."""

from __future__ import annotations

import re
from importlib import import_module
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = (
    (
        "docs-review.yml",
        "docs-review",
        "Resolve paired core command sources ref",
        "Checkout paired core command sources",
    ),
    (
        "pr-orchestrator.yml",
        "quality",
        "Resolve paired core CLI ref",
        "Checkout paired core CLI",
    ),
    (
        "requirements-evidence.yml",
        "requirements-evidence",
        "Resolve paired core CLI ref",
        "Checkout paired core CLI",
    ),
)
EXPECTED_TRIGGERS: dict[str, set[str]] = {
    "docs-review.yml": {"pull_request", "push"},
    "pr-orchestrator.yml": {"pull_request", "push"},
    "requirements-evidence.yml": {"pull_request"},
}


def _step_text(workflow_name: str, job_name: str, step_name: str) -> str:
    workflow = (REPO_ROOT / ".github" / "workflows" / workflow_name).read_text(encoding="utf-8")
    job_match = re.search(
        rf"(?ms)^  {re.escape(job_name)}:\n(?P<body>.*?)(?=^  [a-zA-Z0-9_-]+:\n|\Z)",
        workflow,
    )
    assert job_match is not None, f"missing workflow job: {workflow_name}:{job_name}"
    step_match = re.search(
        rf"(?ms)^      - name: {re.escape(step_name)}\n(?P<body>.*?)(?=^      - (?:name|uses): |\Z)",
        job_match.group("body"),
    )
    assert step_match is not None, f"missing workflow step: {workflow_name}:{job_name}:{step_name}"
    return step_match.group(0)


def _workflow_events(workflow_name: str) -> set[str]:
    yaml = import_module("yaml")

    workflow_path = REPO_ROOT / ".github" / "workflows" / workflow_name
    parsed = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert isinstance(parsed, dict), f"invalid workflow mapping: {workflow_name}"
    events = parsed.get("on")
    assert isinstance(events, dict), f"invalid workflow trigger mapping: {workflow_name}"
    return {str(event) for event in events}


def test_dynamic_paired_core_workflows_exclude_manual_dispatch() -> None:
    for workflow_name, job_name, resolver_name, checkout_name in WORKFLOWS:
        resolver = _step_text(workflow_name, job_name, resolver_name)
        dynamic_checkout = _step_text(workflow_name, job_name, checkout_name)

        assert _workflow_events(workflow_name) == EXPECTED_TRIGGERS[workflow_name]
        assert "github.event_name != 'workflow_dispatch'" not in resolver
        assert "github.event_name != 'workflow_dispatch'" not in dynamic_checkout
        assert "ref: ${{ steps.core-ref.outputs.ref }}" in dynamic_checkout
        assert "persist-credentials: false" in dynamic_checkout


def test_dynamic_paired_core_workflows_have_no_dead_manual_checkout_paths() -> None:
    for workflow_name, _job_name, _resolver_name, checkout_name in WORKFLOWS:
        workflow = (REPO_ROOT / ".github" / "workflows" / workflow_name).read_text(encoding="utf-8")

        assert f"{checkout_name} (manual main)" not in workflow
        assert f"{checkout_name} (manual dev)" not in workflow
