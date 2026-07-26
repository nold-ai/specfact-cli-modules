"""Contract tests for the requirements dogfooding evidence adapter."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from scripts import requirements_evidence_gate as evidence_gate


def _import_result(*, imported: int, diagnostics: list[dict[str, str]]) -> SimpleNamespace:
    return SimpleNamespace(
        requirements=[SimpleNamespace(requirement_id=f"REQ-{index}") for index in range(imported)],
        diagnostics=[SimpleNamespace(model_dump=lambda *_args, item=item, **_kwargs: item) for item in diagnostics],
    )


def _validation(status: str, violations: list[dict[str, str]] | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        status=status,
        model_dump=lambda *_args, **_kwargs: {"status": status, "violations": violations or []},
    )


def _coverage(*, total: int, with_test_links: int) -> SimpleNamespace:
    return SimpleNamespace(
        model_dump=lambda *_args, **_kwargs: {"total_requirements": total, "with_test_links": with_test_links},
    )


def _mapped_requirement(requirement_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        requirement_id=requirement_id,
        model_dump=lambda *_args, **_kwargs: {
            "schema_version": "1",
            "requirement_id": requirement_id,
            "title": "Mapped requirement",
            "sources": [{"source_type": "openspec_change", "locator": "openspec/changes/mapped"}],
            "evidence_links": [],
        },
    )


def _mapped_source(tmp_path: Path) -> tuple[Path, Path, bytes]:
    source = tmp_path / "openspec" / "changes" / "mapped-evidence"
    source.mkdir(parents=True)
    test_target = tmp_path / "tests" / "unit" / "test_evidence.py"
    test_target.parent.mkdir(parents=True)
    test_target.write_text("def test_evidence() -> None:\n    pass\n", encoding="utf-8")
    sidecar = source / "requirements-evidence.yaml"
    sidecar.write_text(
        "requirements:\n  REQ-1:\n    test_links:\n      - tests/unit/test_evidence.py::test_evidence\n",
        encoding="utf-8",
    )
    return source, sidecar, sidecar.read_bytes()


def _resolve_shipped_openspec_change_source(repo_root: Path, change_id: str) -> Path:
    """Find a shipped change in its active or OpenSpec-managed archive location."""
    changes_root = repo_root / "openspec" / "changes"
    candidates = [changes_root / change_id]
    candidates.extend(sorted((changes_root / "archive").glob(f"*-{change_id}")))
    sources = [candidate for candidate in candidates if candidate.is_dir()]

    assert len(sources) == 1, f"expected one active or archived OpenSpec source for {change_id}, found {sources}"
    return sources[0]


def test_evaluate_sources_emits_passed_verdict_with_preserved_evidence(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "openspec" / "changes" / "widget-evidence"
    source.mkdir(parents=True)
    monkeypatch.setattr(
        evidence_gate,
        "import_native_requirements_to_bundle",
        lambda *_args: _import_result(imported=1, diagnostics=[]),
    )
    monkeypatch.setattr(
        evidence_gate,
        "validate_requirements_bundle",
        lambda *_args, **_kwargs: _validation("warnings"),
    )
    monkeypatch.setattr(
        evidence_gate,
        "inspect_requirements_bundle_coverage",
        lambda *_args: _coverage(total=1, with_test_links=1),
    )
    monkeypatch.setattr(evidence_gate, "requirements_gate_finding_counts", lambda *_args, **_kwargs: {})

    report = evidence_gate._evaluate_sources([source], bundle_parent=tmp_path)

    assert report["verdict"] == "passed"
    assert report["execution_proof"] == "not-included"
    assert report["summary"] == {"failed_sources": 0, "passed_sources": 1, "skipped_sources": 0, "total_sources": 1}
    source_report = report["sources"][0]
    assert source_report["import"] == {"diagnostics": [], "imported": 1}
    assert source_report["validation"]["status"] == "warnings"
    assert source_report["coverage"] == {"total_requirements": 1, "with_test_links": 1}
    assert source_report["gate_finding_counts"] == {}


def test_evaluate_sources_emits_failed_reasons_for_import_and_traceability(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "openspec" / "changes" / "incomplete-evidence"
    source.mkdir(parents=True)
    monkeypatch.setattr(
        evidence_gate,
        "import_native_requirements_to_bundle",
        lambda *_args: _import_result(
            imported=0,
            diagnostics=[{"code": "source-incomplete", "severity": "error"}],
        ),
    )

    report = evidence_gate._evaluate_sources([source], bundle_parent=tmp_path)

    assert report["verdict"] == "failed"
    source_report = report["sources"][0]
    assert source_report["verdict"] == "failed"
    assert source_report["reasons"] == ["import-error:source-incomplete", "no-requirements-imported"]
    assert source_report["validation"] is None
    assert source_report["coverage"] is None


def test_evaluate_sources_fails_for_missing_test_links_and_gate_findings(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "openspec" / "changes" / "partial-evidence"
    source.mkdir(parents=True)
    monkeypatch.setattr(
        evidence_gate,
        "import_native_requirements_to_bundle",
        lambda *_args: _import_result(imported=2, diagnostics=[]),
    )
    monkeypatch.setattr(
        evidence_gate,
        "validate_requirements_bundle",
        lambda *_args, **_kwargs: _validation("failed", [{"code": "scenario-unverified", "severity": "error"}]),
    )
    monkeypatch.setattr(
        evidence_gate,
        "inspect_requirements_bundle_coverage",
        lambda *_args: _coverage(total=2, with_test_links=1),
    )
    monkeypatch.setattr(
        evidence_gate, "requirements_gate_finding_counts", lambda *_args, **_kwargs: {"scenario-unverified": 1}
    )

    report = evidence_gate._evaluate_sources([source], bundle_parent=tmp_path)

    assert report["verdict"] == "failed"
    assert report["sources"][0]["reasons"] == [
        "validation-failed",
        "test-link-coverage-incomplete:1/2",
        "gate-finding:scenario-unverified=1",
    ]


def test_evaluate_sources_retains_informational_gate_counts_without_blocking(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "openspec" / "changes" / "information-only"
    source.mkdir(parents=True)
    monkeypatch.setattr(
        evidence_gate,
        "import_native_requirements_to_bundle",
        lambda *_args: _import_result(imported=1, diagnostics=[]),
    )
    monkeypatch.setattr(evidence_gate, "validate_requirements_bundle", lambda *_args, **_kwargs: _validation("passed"))
    monkeypatch.setattr(
        evidence_gate,
        "inspect_requirements_bundle_coverage",
        lambda *_args: _coverage(total=1, with_test_links=1),
    )
    monkeypatch.setattr(
        evidence_gate, "requirements_gate_finding_counts", lambda *_args, **_kwargs: {"unsupported-profile-field": 1}
    )

    report = evidence_gate._evaluate_sources([source], bundle_parent=tmp_path)

    assert report["verdict"] == "passed"
    assert report["sources"][0]["gate_finding_counts"] == {"unsupported-profile-field": 1}


def test_evaluate_sources_overlays_valid_sidecar_test_links_without_mutating_source(
    monkeypatch, tmp_path: Path
) -> None:
    source, sidecar, source_before = _mapped_source(tmp_path)
    monkeypatch.setattr(
        evidence_gate,
        "import_native_requirements_to_bundle",
        lambda *_args: SimpleNamespace(requirements=[_mapped_requirement("REQ-1")], diagnostics=[]),
    )
    captured_overlay: list[dict[str, object]] = []
    monkeypatch.setattr(
        evidence_gate,
        "import_requirements_file_to_bundle",
        lambda overlay_path, _bundle_dir: captured_overlay.append(json.loads(overlay_path.read_text(encoding="utf-8"))),
    )
    monkeypatch.setattr(
        evidence_gate, "validate_requirements_bundle", lambda *_args, **_kwargs: _validation("warnings")
    )
    monkeypatch.setattr(
        evidence_gate,
        "inspect_requirements_bundle_coverage",
        lambda *_args: _coverage(total=1, with_test_links=1),
    )
    monkeypatch.setattr(evidence_gate, "requirements_gate_finding_counts", lambda *_args, **_kwargs: {})

    report = evidence_gate._evaluate_sources([source], bundle_parent=tmp_path)

    assert report["verdict"] == "passed"
    overlay_requirements = cast(list[dict[str, object]], captured_overlay[0]["requirements"])
    assert overlay_requirements[0]["evidence_links"] == [
        {"link_type": "test", "target": "tests/unit/test_evidence.py::test_evidence"}
    ]
    assert sidecar.read_bytes() == source_before


def test_load_evidence_sidecar_rejects_unknown_requirements_and_missing_tests(tmp_path: Path) -> None:
    source = tmp_path / "openspec" / "changes" / "invalid-evidence"
    source.mkdir(parents=True)
    (source / "requirements-evidence.yaml").write_text(
        "requirements:\n  REQ-UNKNOWN:\n    test_links:\n      - tests/missing_test.py\n",
        encoding="utf-8",
    )

    _, reasons = evidence_gate._load_evidence_sidecar(source, tmp_path, {"REQ-1"})

    assert reasons == [
        "evidence-sidecar-unknown-requirement:REQ-UNKNOWN",
        "evidence-sidecar-missing-test:tests/missing_test.py",
    ]


def test_load_evidence_sidecar_rejects_targets_outside_the_repository(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    source = repo_root / "openspec" / "changes" / "invalid-evidence"
    source.mkdir(parents=True)
    outside_target = tmp_path / "outside_test.py"
    outside_target.write_text("def test_outside() -> None:\n    pass\n", encoding="utf-8")
    link_target = repo_root / "tests" / "linked_outside_test.py"
    link_target.parent.mkdir()
    link_target.symlink_to(outside_target)
    (source / "requirements-evidence.yaml").write_text(
        "requirements:\n  REQ-1:\n    test_links:\n      - ../outside_test.py\n      - tests/linked_outside_test.py\n",
        encoding="utf-8",
    )

    _, reasons = evidence_gate._load_evidence_sidecar(source, repo_root, {"REQ-1"})

    assert reasons == [
        "evidence-sidecar-missing-test:../outside_test.py",
        "evidence-sidecar-missing-test:tests/linked_outside_test.py",
    ]


def test_evaluate_sources_counts_findings_with_the_validation_profile(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "openspec" / "changes" / "profile-evidence"
    source.mkdir(parents=True)
    monkeypatch.setattr(
        evidence_gate,
        "import_native_requirements_to_bundle",
        lambda *_args: _import_result(imported=1, diagnostics=[]),
    )
    monkeypatch.setattr(evidence_gate, "validate_requirements_bundle", lambda *_args, **_kwargs: _validation("passed"))
    monkeypatch.setattr(
        evidence_gate,
        "inspect_requirements_bundle_coverage",
        lambda *_args: _coverage(total=1, with_test_links=1),
    )
    profiles: list[str | None] = []
    monkeypatch.setattr(
        evidence_gate,
        "requirements_gate_finding_counts",
        lambda *_args, profile=None: profiles.append(profile) or {},
    )

    report = evidence_gate._evaluate_sources([source], bundle_parent=tmp_path)

    assert report["verdict"] == "passed"
    assert profiles == ["enterprise"]


def test_evaluate_sources_skips_without_sources(tmp_path: Path) -> None:
    report = evidence_gate._evaluate_sources([], bundle_parent=tmp_path)

    assert report["verdict"] == "skipped"
    assert not report["sources"]
    assert report["summary"] == {"failed_sources": 0, "passed_sources": 0, "skipped_sources": 1, "total_sources": 0}


def test_resolve_shipped_openspec_change_source_accepts_active_or_archived_location(tmp_path: Path) -> None:
    changes_root = tmp_path / "openspec" / "changes"
    active = changes_root / "requirements-evidence"
    active.mkdir(parents=True)

    assert _resolve_shipped_openspec_change_source(tmp_path, "requirements-evidence") == active

    active.rmdir()
    archived = changes_root / "archive" / "2026-07-26-requirements-evidence"
    archived.mkdir(parents=True)

    assert _resolve_shipped_openspec_change_source(tmp_path, "requirements-evidence") == archived


def test_resolve_shipped_openspec_change_source_rejects_ambiguous_locations(tmp_path: Path) -> None:
    changes_root = tmp_path / "openspec" / "changes"
    (changes_root / "requirements-evidence").mkdir(parents=True)
    (changes_root / "archive" / "2026-07-26-requirements-evidence").mkdir(parents=True)

    with pytest.raises(AssertionError, match="expected one active or archived OpenSpec source"):
        _resolve_shipped_openspec_change_source(tmp_path, "requirements-evidence")


def test_shipped_source_readiness_and_dogfood_specs_pass_actual_evidence_gate(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    sources = [
        _resolve_shipped_openspec_change_source(repo_root, "requirements-04-upstream-source-readiness"),
        _resolve_shipped_openspec_change_source(repo_root, "requirements-05-dogfood-evidence-gate"),
    ]

    report = evidence_gate._evaluate_sources(sources, bundle_parent=tmp_path)

    assert report["verdict"] == "passed"
    assert report["execution_proof"] == "not-included"
    assert report["summary"] == {"failed_sources": 0, "passed_sources": 2, "skipped_sources": 0, "total_sources": 2}
    assert len(report["sources"]) == 2
    assert all(source["verdict"] == "passed" for source in report["sources"])
    assert all(source["import"]["diagnostics"] == [] for source in report["sources"])
    assert all(source["import"]["imported"] > 0 for source in report["sources"])
    assert all(
        source["coverage"]["total_requirements"] == source["coverage"]["with_test_links"]
        for source in report["sources"]
    )
    assert all(source["reasons"] == [] for source in report["sources"])


def test_discover_changed_openspec_sources_includes_deleted_active_files(monkeypatch, tmp_path: Path) -> None:
    active = tmp_path / "openspec" / "changes" / "widget-evidence"
    archived = tmp_path / "openspec" / "changes" / "archive" / "widget-evidence"
    active.mkdir(parents=True)
    archived.mkdir(parents=True)
    changed_paths = "\n".join(
        [
            "openspec/changes/widget-evidence/specs/widgets/spec.md",
            "openspec/changes/widget-evidence/requirements-evidence.yaml",
            "openspec/changes/archive/widget-evidence/spec.md",
            "openspec/changes/deleted-evidence/spec.md",
            "docs/overview.md",
        ]
    )
    commands: list[list[str]] = []

    def _diff_command(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(args)
        return subprocess.CompletedProcess(args=[], returncode=0, stdout=changed_paths)

    monkeypatch.setattr(
        evidence_gate.subprocess,
        "run",
        _diff_command,
    )

    discovered = evidence_gate._discover_changed_openspec_sources(tmp_path, "origin/dev")

    assert discovered == [active]
    assert "--diff-filter=ACMRD" in commands[0]


def test_discover_changed_openspec_sources_rejects_option_like_base_refs(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="base ref"):
        evidence_gate._discover_changed_openspec_sources(tmp_path, "--output=/tmp/untrusted")


def test_run_evidence_gate_writes_failed_report_before_returning_nonzero(monkeypatch, tmp_path: Path) -> None:
    output_path = tmp_path / "requirements-evidence.json"
    monkeypatch.setattr(evidence_gate, "_discover_changed_openspec_sources", lambda *_args: [])
    monkeypatch.setattr(
        evidence_gate,
        "_evaluate_sources",
        lambda *_args, **_kwargs: {
            "schema_version": "1",
            "verdict": "failed",
            "execution_proof": "not-included",
            "sources": [],
            "summary": {"failed_sources": 1, "passed_sources": 0, "skipped_sources": 0, "total_sources": 1},
        },
    )

    exit_code = evidence_gate._run_evidence_gate(tmp_path, "origin/dev", output_path)

    assert exit_code == 1
    assert '"verdict": "failed"' in output_path.read_text(encoding="utf-8")


def test_run_evidence_gate_writes_failed_report_when_discovery_raises(monkeypatch, tmp_path: Path) -> None:
    output_path = tmp_path / "requirements-evidence.json"
    summary_path = tmp_path / "requirements-evidence.md"
    monkeypatch.setattr(
        evidence_gate,
        "_discover_changed_openspec_sources",
        lambda *_args: (_ for _ in ()).throw(subprocess.CalledProcessError(128, ["git", "diff"])),
    )

    exit_code = evidence_gate._run_evidence_gate(tmp_path, "missing-base", output_path, summary_path)

    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert report["verdict"] == "failed"
    assert report["sources"][0]["reasons"] == ["gate-exception:CalledProcessError"]
    assert "**failed**" in summary_path.read_text(encoding="utf-8")
