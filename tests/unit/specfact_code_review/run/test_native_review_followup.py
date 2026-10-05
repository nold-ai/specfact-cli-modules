from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from pytest import MonkeyPatch

from specfact_code_review.run import portable_snapshot, runner


def test_native_project_range_report_retains_snapshot_platform_and_versions(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    base = SimpleNamespace(root=tmp_path / "base", contents={"app.py": b"pass\n"})
    head = SimpleNamespace(root=tmp_path / "head", contents={"app.py": b"pass\n"})
    for side in (base, head):
        side.root.mkdir()
        (side.root / "app.py").write_text("pass\n", encoding="utf-8")
    resolution = SimpleNamespace(base_snapshot=base, head_snapshot=head, selected_paths=("app.py",))
    versions = dict.fromkeys(runner.default_pr_range_profile().all_ids, "1.175.0")
    result = runner.CapsuleSnapshotResult({}, {}, versions, "darwin-arm64")
    monkeypatch.setattr(portable_snapshot, "run_project_snapshot", lambda *_args: (result, {"status": "PASS"}))
    monkeypatch.setattr(runner, "_snapshot_python_files", lambda *_args: [base.root / "app.py"])
    monkeypatch.setattr(runner, "_classify_range_findings", lambda *_args: ({}, {}))
    observed: dict[str, Any] = {}

    def report(*_args: object, **kwargs: Any) -> dict[str, Any]:
        observed.update(kwargs)
        return observed

    monkeypatch.setattr(runner, "_capsule_report", report)
    portable_snapshot.run_project_scope_pair(
        resolution,
        runtime=object(),
        options=runner.ReviewOptions(),
        scope_evidence={"assurance_kind": "range_preview"},
    )
    assert observed["expected_versions"] == versions
    assert observed["platform_id"] == "darwin-arm64"


def test_ordinary_native_snapshot_keeps_import_support_without_unrelated_data(tmp_path: Path) -> None:
    snapshot = tmp_path / "project"
    package = snapshot / "pkg"
    package.mkdir(parents=True)
    (package / "selected.py").write_text("from pkg.support import VALUE\n", encoding="utf-8")
    (package / "support.py").write_text("VALUE = 1\n", encoding="utf-8")
    (snapshot / "secret.txt").write_text("secret\n", encoding="utf-8")
    selected = [(package / "selected.py", Path("pkg/selected.py"))]
    entries = runner._capture_native_source_context(snapshot, selected)
    assert {name for name, _ in entries} == {"pkg/selected.py", "pkg/support.py"}
