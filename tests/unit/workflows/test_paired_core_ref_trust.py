"""Trust-boundary contracts for paired core workflow checkouts."""

from __future__ import annotations

import re
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


def test_dynamic_paired_core_resolution_excludes_manual_dispatch() -> None:
    for workflow_name, job_name, resolver_name, checkout_name in WORKFLOWS:
        resolver = _step_text(workflow_name, job_name, resolver_name)
        dynamic_checkout = _step_text(workflow_name, job_name, checkout_name)

        assert "github.event_name != 'workflow_dispatch'" in resolver
        assert "github.event_name != 'workflow_dispatch'" in dynamic_checkout
        assert "ref: ${{ steps.core-ref.outputs.ref }}" in dynamic_checkout
        assert "persist-credentials: false" in dynamic_checkout


def test_manual_dispatch_uses_mutually_exclusive_literal_core_refs() -> None:
    for workflow_name, job_name, _resolver_name, checkout_name in WORKFLOWS:
        manual_main = _step_text(workflow_name, job_name, f"{checkout_name} (manual main)")
        manual_dev = _step_text(workflow_name, job_name, f"{checkout_name} (manual dev)")

        assert "github.event_name == 'workflow_dispatch'" in manual_main
        assert "github.ref_name == 'main'" in manual_main
        assert 'ref: "main"' in manual_main
        assert "persist-credentials: false" in manual_main

        assert "github.event_name == 'workflow_dispatch'" in manual_dev
        assert "github.ref_name != 'main'" in manual_dev
        assert 'ref: "dev"' in manual_dev
        assert "persist-credentials: false" in manual_dev
