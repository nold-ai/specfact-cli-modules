"""Static contract tests for the requirements-evidence GitHub Actions job."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _workflow_text() -> str:
    return (REPO_ROOT / ".github" / "workflows" / "requirements-evidence.yml").read_text(encoding="utf-8")


def test_requirements_evidence_workflow_runs_adapter_with_paired_core() -> None:
    workflow = _workflow_text()

    assert "name: requirements-evidence" in workflow
    assert "pull_request:" in workflow
    assert "branches: [main, dev]" in workflow
    assert "repository: nold-ai/specfact-cli" in workflow
    assert "hatch run pip install -e ./specfact-cli" in workflow
    assert "hatch run pip install -e ./packages/specfact-requirements" not in workflow
    assert "PYTHONPATH: packages/specfact-project/src:packages/specfact-requirements/src" in workflow
    assert "scripts/requirements_evidence_gate.py" in workflow
    assert "--base-ref" in workflow
    assert "--output artifacts/requirements-evidence/requirements-evidence.json" in workflow
    assert "--summary artifacts/requirements-evidence/requirements-evidence.md" in workflow


def test_requirements_evidence_workflow_retains_red_artifacts_and_enforces_verdict() -> None:
    workflow = _workflow_text()

    assert "continue-on-error: true" in workflow
    assert "if: always()" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "name: requirements-evidence" in workflow
    assert "steps.run-evidence.outcome == 'failure'" in workflow
    assert 'cat artifacts/requirements-evidence/requirements-evidence.md >> "$GITHUB_STEP_SUMMARY"' in workflow
    assert "setup-unavailable" in workflow
    assert "requirements-evidence.md" in workflow
    assert "scripts/requirements_evidence_fallback.py" in workflow
