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
    assert b"\r\n" not in output_path.read_bytes()
    assert b"\r\n" not in summary_path.read_bytes()


def test_temporary_evidence_writer_pins_lf_line_endings(tmp_path: Path) -> None:
    temporary_path = fallback._write_temporary_text(tmp_path / "evidence.json", "one\ntwo\n")

    assert temporary_path.read_bytes() == b"one\ntwo\n"


def test_failure_report_restores_the_prior_artifact_pair_when_json_publication_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_path = tmp_path / "requirements-evidence.json"
    summary_path = tmp_path / "requirements-evidence.md"
    previous_output = b'{"verdict": "previous"}\r\n'
    previous_summary = b"previous summary\r\n"
    output_path.write_bytes(previous_output)
    summary_path.write_bytes(previous_summary)
    original_replace = Path.replace

    def _fail_json_publication(path: Path, target: Path) -> Path:
        if target == output_path:
            raise OSError("json publication failed")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", _fail_json_publication)

    with pytest.raises(OSError, match="json publication failed"):
        fallback._write_failure_report(output_path, summary_path, stage="setup-unavailable")

    assert output_path.read_bytes() == previous_output
    assert summary_path.read_bytes() == previous_summary


def test_failure_report_rejects_identical_resolved_destinations_before_writing(tmp_path: Path) -> None:
    output_path = tmp_path / "evidence" / "requirements-evidence.json"
    summary_path = tmp_path / "evidence" / "temporary" / ".." / "requirements-evidence.json"

    with pytest.raises(ValueError, match="different destinations"):
        fallback._write_failure_report(output_path, summary_path, stage="setup-unavailable")

    assert not output_path.parent.exists()


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
