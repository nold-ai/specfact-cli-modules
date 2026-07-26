"""Tests for the workflow-level Requirements evidence fallback artifact."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import requirements_evidence_fallback as fallback


def test_write_failure_report_retains_machine_readable_setup_evidence(tmp_path: Path) -> None:
    output_path = tmp_path / "requirements-evidence.json"
    summary_path = tmp_path / "requirements-evidence.md"

    fallback.write_failure_report(output_path, summary_path, stage="setup-unavailable")

    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["verdict"] == "failed"
    assert report["execution_proof"] == "not-included"
    assert report["sources"][0]["reasons"] == ["setup-unavailable"]
    assert "Failure stage: `setup-unavailable`" in summary_path.read_text(encoding="utf-8")
