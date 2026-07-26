"""Tests for the workflow-level Requirements evidence fallback artifact."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import requirements_evidence_fallback as fallback


def test_private_failure_report_retains_machine_readable_setup_evidence(tmp_path: Path) -> None:
    output_path = tmp_path / "requirements-evidence.json"
    summary_path = tmp_path / "requirements-evidence.md"

    fallback._write_failure_report(output_path, summary_path, stage="setup-unavailable")

    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["verdict"] == "failed"
    assert report["execution_proof"] == "not-included"
    assert report["sources"][0]["reasons"] == ["setup-unavailable"]
    assert "Failure stage: `setup-unavailable`" in summary_path.read_text(encoding="utf-8")


def test_failure_report_does_not_publish_either_artifact_before_the_pair_is_ready(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_path = tmp_path / "requirements-evidence.json"
    summary_path = tmp_path / "requirements-evidence.md"

    def _write_until_summary(destination: Path, contents: str) -> Path:
        if destination == summary_path:
            raise OSError("summary temporary write failed")
        temporary_path = tmp_path / f".{destination.name}.tmp"
        temporary_path.write_text(contents, encoding="utf-8")
        return temporary_path

    monkeypatch.setattr(fallback, "_write_temporary_text", _write_until_summary)

    with pytest.raises(OSError, match="summary temporary write failed"):
        fallback._write_failure_report(output_path, summary_path, stage="setup-unavailable")

    assert not output_path.exists()
    assert not summary_path.exists()
