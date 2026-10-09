from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from pytest import MonkeyPatch

from specfact_code_review.run import native_backend, runner
from specfact_code_review.run.native_capsule import NativeCapsuleLease
from specfact_code_review.tools import ruff_runner


def test_incomplete_native_report_keeps_selected_platform_identity(monkeypatch: MonkeyPatch) -> None:
    selected = native_backend.BackendSelection("darwin-arm64", "darwin-arm64-cp312", "")
    monkeypatch.setattr(native_backend, "select_runtime_backend", lambda: selected)
    seen: list[str] = []
    original = runner._activated_capsule_report_evidence

    def capture(evidence: dict[str, dict[str, object]], expected_versions: Any, platform_id: str) -> Any:
        seen.append(platform_id)
        return original(evidence, expected_versions, platform_id)

    monkeypatch.setattr(runner, "_activated_capsule_report_evidence", capture)
    report = runner._unknown_capsule_report(
        "native_capsule_catalog_missing",
        options=runner.ReviewOptions(),
        scope_evidence={"assurance_kind": "explicit_files"},
    )

    assert seen == ["darwin-arm64"]
    assert report.analyzer_evidence is not None
    assert {item["environment_id"] for item in report.analyzer_evidence} == {"darwin-arm64-cp312"}
    assert {item["version"] for item in report.analyzer_evidence} == {"unavailable"}
    assert all(item["execution_state"] == "error" for item in report.analyzer_evidence)


def test_policy_binding_builder_canonicalizes_controller_created_projection_root(
    tmp_path: Path,
) -> None:
    canonical_root = tmp_path / "canonical"
    projection_root = canonical_root / "projection"
    projection_root.mkdir(parents=True)
    projection = projection_root / "pytest.ini"
    projection.write_text("[pytest]\n", encoding="utf-8")
    alias = tmp_path / "alias"
    alias.symlink_to(canonical_root, target_is_directory=True)

    builder = runner._PolicyBindingBuilder()
    mounted = builder.register(alias / "projection" / "pytest.ini")

    assert mounted == "/opt/specfact/config/1/pytest.ini"
    assert builder.result().config_roots == (projection_root.resolve(strict=True),)


def test_seal_native_private_tree_normalizes_owner_only_state_and_rejects_indirection(tmp_path: Path) -> None:
    root = tmp_path / "temporary"
    nested = root / "tool-home" / ".cache"
    nested.mkdir(parents=True, mode=0o755)
    payload = nested / "state.json"
    payload.write_text("{}\n", encoding="utf-8")
    payload.chmod(0o644)

    runner._seal_native_private_tree(root)

    assert root.stat().st_mode & 0o777 == 0o700
    assert (root / "tool-home").stat().st_mode & 0o777 == 0o700
    assert nested.stat().st_mode & 0o777 == 0o700
    assert payload.stat().st_mode & 0o777 == 0o600

    alias = root / "alias"
    alias.symlink_to(payload)
    with pytest.raises(ValueError, match="native private tree contains indirection"):
        runner._seal_native_private_tree(root)


@pytest.mark.parametrize("directory_alias", [False, True])
def test_native_scratch_unlinks_symlinks_without_touching_targets(tmp_path, directory_alias):
    root = tmp_path / "temporary"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir(mode=0o755)
    secret = outside / "secret"
    secret.write_text("must remain unchanged")
    secret.chmod(0o644)
    alias = root / "pytest-current"
    alias.symlink_to(outside if directory_alias else secret, target_is_directory=directory_alias)
    broken = root / "missing"
    broken.symlink_to(outside / "does-not-exist")
    runner._seal_native_private_tree(root, discard_symlinks=True)
    assert not alias.is_symlink() and not broken.is_symlink()
    assert secret.read_text() == "must remain unchanged"
    assert secret.stat().st_mode & 0o777 == 0o644
    assert outside.stat().st_mode & 0o777 == 0o755
    assert root.stat().st_mode & 0o777 == 0o700


def test_native_scratch_does_not_admit_linked_receipts(tmp_path):
    root = tmp_path / "temporary"
    evidence = root / "pytest-evidence"
    evidence.mkdir(parents=True)
    forged = tmp_path / "forged.json"
    forged.write_text("[]")
    observer = evidence / "observer.json"
    observer.symlink_to(forged)
    runner._seal_native_private_tree(root, discard_symlinks=True)
    assert not observer.exists()
    assert forged.read_text() == "[]"


def test_normalize_native_semgrep_reply_rebinds_only_exact_tool_snapshot_paths(tmp_path: Path) -> None:
    project = tmp_path / "project-001"
    source = project / "pkg/example.py"
    source.parent.mkdir(parents=True)
    source.write_text("value = 1\n", encoding="utf-8")
    payload = {
        "errors": [],
        "paths": {"scanned": [str(source)], "skipped": []},
        "results": [{"path": str(source), "start": {"line": 1}}],
        "version": "1.175.0",
    }

    normalized = json.loads(runner._normalize_native_tool_stdout("semgrep", json.dumps(payload), project))

    assert normalized["paths"] == {"scanned": ["pkg/example.py"], "skipped": []}
    assert normalized["results"][0]["path"] == "pkg/example.py"


def test_normalize_native_semgrep_reply_rejects_outside_paths(tmp_path: Path) -> None:
    project = tmp_path / "project-001"
    project.mkdir()
    payload = {
        "errors": [],
        "paths": {"scanned": ["/etc/passwd"], "skipped": []},
        "results": [],
        "version": "1.175.0",
    }

    with pytest.raises(ValueError, match="outside exact tool snapshot"):
        runner._normalize_native_tool_stdout("semgrep", json.dumps(payload), project)


@pytest.mark.parametrize(
    ("tool", "make_payload", "extract_path"),
    [
        ("ruff", lambda path: [{"filename": path}], lambda payload: payload[0]["filename"]),
        ("pylint", lambda path: [{"path": path, "abspath": path}], lambda payload: payload[0]["path"]),
        (
            "basedpyright",
            lambda path: {"generalDiagnostics": [{"file": path}]},
            lambda payload: payload["generalDiagnostics"][0]["file"],
        ),
        ("radon", lambda path: {path: []}, lambda payload: next(iter(payload))),
    ],
)
def test_native_structured_tool_diagnostics_rebind_exact_snapshot_paths(
    tmp_path: Path, tool: str, make_payload: Any, extract_path: Any
) -> None:
    project = tmp_path / "project-001"
    source = project / "pkg/example.py"
    source.parent.mkdir(parents=True)
    source.write_text("x = 1\n", encoding="utf-8")

    normalized = json.loads(runner._normalize_native_tool_stdout(tool, json.dumps(make_payload(str(source))), project))

    assert extract_path(normalized) == "pkg/example.py"


def test_native_crosshair_diagnostic_rebinds_exact_snapshot_path(tmp_path: Path) -> None:
    project = tmp_path / "project-001"
    source = project / "pkg/example.py"
    source.parent.mkdir(parents=True)
    source.write_text("x = 1\n", encoding="utf-8")

    normalized = runner._normalize_native_tool_stdout("crosshair", f"{source}:7: error: postcondition false\n", project)

    assert normalized == "pkg/example.py:7: error: postcondition false\n"


@pytest.mark.parametrize(
    ("tool", "payload"),
    [
        ("ruff", [{"filename": "/etc/passwd"}]),
        ("pylint", [{"path": "/etc/passwd"}]),
        ("basedpyright", {"generalDiagnostics": [{"file": "/etc/passwd"}]}),
        ("radon", {"/etc/passwd": []}),
        ("crosshair", "/etc/passwd:1: error: forged\n"),
    ],
)
def test_native_tool_diagnostic_rejects_outside_snapshot_paths(tmp_path: Path, tool: str, payload: Any) -> None:
    project = tmp_path / "project-001"
    project.mkdir()
    stdout = payload if isinstance(payload, str) else json.dumps(payload)

    with pytest.raises(ValueError, match="outside exact tool snapshot"):
        runner._normalize_native_tool_stdout(tool, stdout, project)


def test_native_ruff_replay_preserves_a_real_diagnostic_across_project_stages(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    first = tmp_path / "project-001"
    second = tmp_path / "project-002"
    for root in (first, second):
        source = root / "pkg/example.py"
        source.parent.mkdir(parents=True)
        source.write_text("import os\n", encoding="utf-8")
    raw = [
        {"filename": str(first / "pkg/example.py"), "location": {"row": 1}, "code": "F401", "message": "unused import"}
    ]

    replay = json.loads(runner._normalize_native_tool_stdout("ruff", json.dumps(raw), first))
    monkeypatch.chdir(second)
    finding = ruff_runner._finding_from_item(
        replay[0], allowed_paths=ruff_runner._allowed_paths([second / "pkg/example.py"])
    )

    assert finding is not None
    assert finding.rule == "F401"
    assert finding.file == "pkg/example.py"


def test_capture_native_selected_files_only_stages_requested_internal_alias(tmp_path: Path) -> None:
    snapshot = tmp_path / "source"
    package = snapshot / "pkg"
    package.mkdir(parents=True)
    target = package / "target.py"
    target.write_text("VALUE = 1\n", encoding="utf-8")
    alias = package / "selected.py"
    alias.symlink_to(target.name)
    (package / "unselected.py").write_text("SECRET = 2\n", encoding="utf-8")

    assert runner._capture_native_files(snapshot, [(alias, Path("pkg/selected.py"))]) == [
        ("pkg/selected.py", b"VALUE = 1\n")
    ]


def test_capture_native_selected_files_rejects_external_alias(tmp_path: Path) -> None:
    snapshot = tmp_path / "source"
    snapshot.mkdir()
    external = tmp_path / "external.py"
    external.write_text("SECRET = 1\n", encoding="utf-8")
    alias = snapshot / "selected.py"
    alias.symlink_to(external)

    with pytest.raises(ValueError, match="native_snapshot_alias_escape"):
        runner._capture_native_files(snapshot, [(alias, Path("selected.py"))])


def test_prepare_native_runtime_retains_verified_lease_until_runtime_cleanup(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    selected = native_backend.BackendSelection("darwin-arm64", "darwin-arm64-cp312", "")
    lease = SimpleNamespace(
        path=tmp_path / "capsule",
        identity="a" * 64,
        analyzer_versions={
            **runner._C14_ANALYZER_VERSIONS,
            "semgrep-clean": "1.175.0",
            "semgrep-bugs": "1.175.0",
        },
        evidence={"status": "VERIFIED_CACHE_CANDIDATE"},
        closed=False,
    )
    lease.path.mkdir()

    def close() -> None:
        lease.closed = True

    lease.close = close
    monkeypatch.setattr(runner.native_backend, "select_runtime_backend", lambda *_args: selected)
    monkeypatch.setattr(
        runner.native_backend,
        "prepare_native_runtime",
        lambda *_args, **_kwargs: native_backend.NativePreparation(
            "VERIFIED", cast(NativeCapsuleLease, lease), "", dict(lease.evidence)
        ),
    )
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_CAPSULE_CACHE", str(tmp_path / "cache"))

    runtime, reason = runner._prepare_capsule_runtime()

    assert reason == ""
    assert runtime is not None
    assert runtime.backend == "darwin-arm64"
    assert runtime.environment_id == "darwin-arm64-cp312"
    assert runtime.identity == "sha256:" + "a" * 64
    assert runtime.native_lease is lease
    assert runtime.analyzer_versions is not None
    assert runtime.analyzer_versions["semgrep-clean"] == "1.175.0"
    assert runtime.bubblewrap is None
    assert lease.closed is False

    runner._cleanup_capsule_runtime(runtime)
    assert lease.closed is True


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError("timeout"),
        ValueError("invalid signature"),
        OSError("cache denied"),
        subprocess.TimeoutExpired(["codesign", "/private/secret"], 10),
    ],
)
def test_native_acquisition_failures_return_structured_incomplete(monkeypatch, tmp_path, error):
    selected = native_backend.BackendSelection("darwin-arm64", "darwin-arm64-cp311", "")
    monkeypatch.setattr(runner.native_backend, "select_runtime_backend", lambda *_args: selected)
    monkeypatch.setattr(runner.native_backend, "load_native_artifact_catalog", dict)

    def fail(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(runner.native_backend, "prepare_native_runtime", fail)
    runtime, reason = runner._prepare_capsule_runtime()
    assert runtime is None
    assert reason.startswith("native_capsule_runtime_unavailable:")
    assert "secret" not in reason


def test_native_profile_uses_authenticated_analyzer_versions_without_relabeling_linux() -> None:
    versions = {
        **runner._C14_ANALYZER_VERSIONS,
        "semgrep-clean": "1.175.0",
        "semgrep-bugs": "1.175.0",
    }
    evidence: dict[str, dict[str, object]] = {
        member: {
            "execution_state": "ran",
            "evidence_outcome": "PASS",
            "version": version,
        }
        for member, version in versions.items()
    }

    native = runner.aggregate_profile_evidence(evidence, expected_versions=versions)
    linux = runner.aggregate_profile_evidence(evidence)

    assert native.assurance_status == "PASS"
    assert linux.assurance_status == "UNKNOWN"


def test_native_report_admits_authenticated_darwin_semgrep_suppression_policy() -> None:
    versions = {
        **runner._C14_ANALYZER_VERSIONS,
        "semgrep-clean": "1.175.0",
        "semgrep-bugs": "1.175.0",
    }
    evidence: dict[str, dict[str, object]] = {
        member: {
            "execution_state": "ran",
            "evidence_outcome": "PASS",
            "version": version,
        }
        for member, version in versions.items()
    }

    report = runner._capsule_report(
        evidence,
        {},
        options=runner.ReviewOptions(),
        scope_evidence={"assurance_kind": "explicit_files"},
        expected_versions=versions,
        platform_id="darwin-arm64",
    )
    relabeled_linux = runner._capsule_report(
        evidence,
        {},
        options=runner.ReviewOptions(),
        scope_evidence={"assurance_kind": "explicit_files"},
        expected_versions=versions,
        platform_id="linux-x86_64",
    )
    protected_range = runner._capsule_report(
        evidence,
        {},
        options=runner.ReviewOptions(),
        scope_evidence={"assurance_kind": "range_candidate"},
        expected_versions=versions,
        platform_id="darwin-arm64",
    )

    assert report.assurance_status == "PASS"
    assert report.scope_evidence is not None
    assert report.scope_evidence["native_pytest_result_provenance"] == "project-origin-v1"
    assert report.analyzer_evidence is not None
    pytest_evidence = next(item for item in report.analyzer_evidence if item["id"] == "targeted-pytest-coverage")
    assert pytest_evidence["result_provenance"] == "project-origin-v1"
    assert report.suppression_catalog_digest is not None
    assert relabeled_linux.assurance_status == "UNKNOWN"
    assert relabeled_linux.scope_evidence is not None
    assert "native_pytest_result_provenance" not in relabeled_linux.scope_evidence
    assert relabeled_linux.suppression_catalog_digest is None
    assert protected_range.assurance_status == "UNKNOWN"
    assert protected_range.analyzer_evidence is not None
    protected_pytest = next(
        item for item in protected_range.analyzer_evidence if item["id"] == "targeted-pytest-coverage"
    )
    assert protected_pytest["diagnostic"] == "native_project_origin_pytest_not_protected_range_evidence"


def test_native_incomplete_report_preserves_root_diagnostic_before_catalog_activation() -> None:
    versions = dict.fromkeys(runner.default_pr_range_profile().all_ids, "unavailable")
    evidence: dict[str, dict[str, object]] = {
        member: {
            "execution_state": "error",
            "evidence_outcome": "UNKNOWN",
            "version": version,
            "diagnostic": "project_native_acquisition_entry_missing",
        }
        for member, version in versions.items()
    }

    report = runner._capsule_report(
        evidence,
        {},
        options=runner.ReviewOptions(),
        scope_evidence={"assurance_kind": "explicit_files"},
        expected_versions=versions,
        platform_id="darwin-arm64",
    )

    assert report.assurance_status == "UNKNOWN"
    assert {item["diagnostic"] for item in report.analyzer_evidence or []} == {
        "project_native_acquisition_entry_missing"
    }


@pytest.mark.parametrize("no_tests", [False, True])
def test_native_report_requires_pytest_even_when_skipped(no_tests: bool) -> None:
    versions = {**runner._C14_ANALYZER_VERSIONS, "semgrep-clean": "1.175.0", "semgrep-bugs": "1.175.0"}
    evidence: dict[str, dict[str, object]] = {
        member: {"execution_state": "ran", "evidence_outcome": "PASS", "version": version}
        for member, version in versions.items()
    }
    if not no_tests:
        evidence["targeted-pytest-coverage"]["execution_state"] = "not_applicable"
        evidence["targeted-pytest-coverage"]["evidence_outcome"] = "NOT_APPLICABLE"

    report = runner._capsule_report(
        evidence,
        {},
        options=runner.ReviewOptions(no_tests=no_tests),
        scope_evidence={"assurance_kind": "explicit_files"},
        expected_versions=versions,
        platform_id="darwin-arm64",
    )

    assert report.analyzer_evidence is not None
    pytest_evidence = next(item for item in report.analyzer_evidence if item["id"] == "targeted-pytest-coverage")
    assert report.assurance_status == "UNKNOWN"
    assert pytest_evidence["evidence_outcome"] == "UNKNOWN"
    assert pytest_evidence["diagnostic"] == "native_pytest_required_for_complete_review"


def test_native_no_tests_keeps_more_specific_pytest_error() -> None:
    versions = {**runner._C14_ANALYZER_VERSIONS, "semgrep-clean": "1.175.0", "semgrep-bugs": "1.175.0"}
    evidence: dict[str, dict[str, object]] = {
        member: {"execution_state": "ran", "evidence_outcome": "PASS", "version": version}
        for member, version in versions.items()
    }
    evidence["targeted-pytest-coverage"].update(
        execution_state="error", evidence_outcome="UNKNOWN", diagnostic="project_runtime_required"
    )

    report = runner._capsule_report(
        evidence,
        {},
        options=runner.ReviewOptions(no_tests=True),
        scope_evidence={"assurance_kind": "explicit_files"},
        expected_versions=versions,
        platform_id="darwin-arm64",
    )

    assert report.assurance_status == "UNKNOWN"
    assert report.analyzer_evidence is not None
    pytest_evidence = next(item for item in report.analyzer_evidence if item["id"] == "targeted-pytest-coverage")
    assert pytest_evidence["diagnostic"] == "project_runtime_required"


def test_native_range_keeps_specific_pytest_error_before_provenance_check() -> None:
    versions = {**runner._C14_ANALYZER_VERSIONS, "semgrep-clean": "1.175.0", "semgrep-bugs": "1.175.0"}
    evidence: dict[str, dict[str, object]] = {
        member: {"execution_state": "ran", "evidence_outcome": "PASS", "version": version}
        for member, version in versions.items()
    }
    evidence["targeted-pytest-coverage"].update(
        execution_state="error", evidence_outcome="UNKNOWN", diagnostic="project_runtime_required"
    )

    report = runner._capsule_report(
        evidence,
        {},
        options=runner.ReviewOptions(),
        scope_evidence={"assurance_kind": "range_candidate"},
        expected_versions=versions,
        platform_id="darwin-arm64",
    )

    assert report.assurance_status == "UNKNOWN"
    assert report.analyzer_evidence is not None
    pytest_evidence = next(item for item in report.analyzer_evidence if item["id"] == "targeted-pytest-coverage")
    assert pytest_evidence["diagnostic"] == "project_runtime_required"


def test_native_no_tests_cannot_skip_pytest_boundary_before_launch(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    snapshot = tmp_path / "source"
    snapshot.mkdir()
    source = snapshot / "sample.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    runtime = runner.CapsuleRuntime(
        root=tmp_path / "capsule",
        identity="sha256:" + "a" * 64,
        environment_id="darwin-arm64-cp312",
        interpreter="python/bin/python3",
        bootstrap="bin/specfact-native-bootstrap",
        bubblewrap=None,
        backend="darwin-arm64",
        native_lease=SimpleNamespace(),
    )
    request = runner.CapsuleMemberExecutionRequest(
        runtime=runtime,
        member="targeted-pytest-coverage",
        invocation_id="invocation-1",
        snapshot_root=snapshot,
        files=[source],
        options=runner.ReviewOptions(no_tests=True),
    )
    monkeypatch.setattr(
        runner,
        "_execute_capsule_member",
        lambda _request: (_ for _ in ()).throw(AssertionError("native tests must not run after no_tests")),
    )

    response = runner._dispatch_capsule_member(
        request,
        applicability=runner.classify_snapshot_input_kinds(("sample.py",)),
        sealed_bugs_policy=False,
    )

    assert response["evidence_outcome"] == "UNKNOWN"
    assert response["diagnostic"] == "native_pytest_required_for_complete_review"


def test_linux_no_tests_keeps_legacy_pytest_opt_out(tmp_path: Path) -> None:
    snapshot = tmp_path / "source"
    snapshot.mkdir()
    source = snapshot / "sample.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    runtime = runner.CapsuleRuntime(
        root=tmp_path / "capsule",
        identity="sha256:" + "a" * 64,
        environment_id="linux-x86_64-cp312",
        interpreter="python/bin/python3",
        bootstrap="bin/specfact-native-bootstrap",
        bubblewrap=None,
        backend="linux-x86_64",
    )
    request = runner.CapsuleMemberExecutionRequest(
        runtime=runtime,
        member="targeted-pytest-coverage",
        invocation_id="invocation-1",
        snapshot_root=snapshot,
        files=[source],
        options=runner.ReviewOptions(no_tests=True),
    )

    response = runner._dispatch_capsule_member(
        request,
        applicability=runner.classify_snapshot_input_kinds(("sample.py",)),
        sealed_bugs_policy=False,
    )

    assert response == {
        "execution_state": "not_applicable",
        "evidence_outcome": "NOT_APPLICABLE",
        "findings": [],
        "diagnostic": "tests_explicitly_disabled_for_legacy_scope",
    }


def test_linux_member_refuses_missing_bubblewrap_identity_before_setup(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    snapshot = tmp_path / "source"
    snapshot.mkdir()
    source = snapshot / "sample.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    runtime = runner.CapsuleRuntime(
        root=tmp_path / "capsule",
        identity="sha256:" + "a" * 64,
        environment_id="linux-x86_64-cp312",
        interpreter="python/bin/python3",
        bootstrap="bin/specfact-native-bootstrap",
        bubblewrap=None,
    )
    request = runner.CapsuleMemberExecutionRequest(
        runtime=runtime,
        member="ruff",
        invocation_id="invocation-1",
        snapshot_root=snapshot,
        files=[source],
        options=runner.ReviewOptions(),
    )
    monkeypatch.setattr(
        runner,
        "_prepare_capsule_process_roots",
        lambda *_args: (_ for _ in ()).throw(AssertionError("sandbox preparation must not begin")),
    )

    assert runner._execute_capsule_member(request) == {
        "execution_state": "error",
        "evidence_outcome": "UNKNOWN",
        "findings": [],
        "diagnostic": "linux_bubblewrap_identity_missing",
    }


def test_prepare_native_runtime_allows_another_admitted_darwin_abi(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    selected = native_backend.BackendSelection("darwin-arm64", "darwin-arm64-cp312", "")
    lease = SimpleNamespace(
        path=tmp_path / "capsule",
        identity="b" * 64,
        analyzer_versions=dict(runner._C14_ANALYZER_VERSIONS),
        evidence={"status": "VERIFIED_CACHE_CANDIDATE"},
        close=lambda: None,
    )
    lease.path.mkdir()
    observed: list[native_backend.BackendSelection] = []
    monkeypatch.setattr(runner.native_backend, "select_runtime_backend", lambda *_args: selected)

    def prepare(selection: native_backend.BackendSelection, **_kwargs: object) -> native_backend.NativePreparation:
        observed.append(selection)
        return native_backend.NativePreparation("VERIFIED", cast(NativeCapsuleLease, lease), "", dict(lease.evidence))

    monkeypatch.setattr(runner.native_backend, "prepare_native_runtime", prepare)
    monkeypatch.setattr(runner.native_backend, "load_native_artifact_catalog", dict)
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_CAPSULE_CACHE", str(tmp_path / "cache"))

    runtime, reason = runner._prepare_capsule_runtime(environment_id="darwin-arm64-cp311")

    assert reason == ""
    assert runtime is not None
    assert runtime.environment_id == "darwin-arm64-cp311"
    assert observed == [native_backend.BackendSelection("darwin-arm64", "darwin-arm64-cp311", "")]


def test_native_member_execution_uses_native_backend_instead_of_bubblewrap(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    lease = SimpleNamespace()
    runtime = runner.CapsuleRuntime(
        root=tmp_path / "capsule",
        identity="sha256:" + "a" * 64,
        environment_id="darwin-arm64-cp312",
        interpreter="python/bin/python3",
        bootstrap="bin/specfact-native-bootstrap",
        bubblewrap=None,
        backend="darwin-arm64",
        native_lease=lease,
    )
    request = SimpleNamespace(runtime=runtime, member="ruff")
    expected = {
        "member": "ruff",
        "execution_state": "ran",
        "evidence_outcome": "PASS",
        "findings": [],
    }
    observed: list[object] = []

    def execute(value: object) -> dict[str, object]:
        observed.append(value)
        return expected

    monkeypatch.setattr(runner, "_execute_native_capsule_member", execute)
    monkeypatch.setattr(
        runner,
        "build_launch_plan",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("native execution used bubblewrap")),
    )

    assert runner._execute_capsule_member(request) == expected  # type: ignore[arg-type]
    assert observed == [request]


@pytest.mark.parametrize("overlay", ["absent", "generated", "collision"])
def test_native_member_execution_stages_immutable_snapshot_and_uses_closed_plan(
    monkeypatch: MonkeyPatch, tmp_path: Path, overlay: str
) -> None:
    snapshot = tmp_path / "source"
    snapshot.mkdir()
    source = snapshot / "pkg" / "example.py"
    source.parent.mkdir()
    source.write_text("value = 1\n", encoding="utf-8")
    snapshot_alias = tmp_path / "source-alias"
    snapshot_alias.symlink_to(snapshot, target_is_directory=True)
    selected_source = snapshot_alias / "pkg" / "example.py"
    support = snapshot / "pkg" / "support.py"
    support.write_text("HELPER = 2\n", encoding="utf-8")
    config_root = tmp_path / "config"
    config_root.mkdir()
    config = config_root / "ruff.toml"
    config.write_text("[lint]\nselect = ['F']\n", encoding="utf-8")
    project_runtime = tmp_path / "project-runtime"
    dependency = project_runtime / "site-packages/fixture_dep/__init__.py"
    dependency.parent.mkdir(parents=True)
    dependency.write_text("VALUE = 1\n", encoding="utf-8")
    (project_runtime / "project-runtime.json").write_text("{}\n", encoding="utf-8")
    if overlay != "absent":
        generated = project_runtime / "source-overlay/pkg" / ("example.py" if overlay == "collision" else "_version.py")
        generated.parent.mkdir(parents=True)
        generated.write_text("VERSION = 7\n")
    lease = SimpleNamespace()
    runtime = runner.CapsuleRuntime(
        root=tmp_path / "capsule",
        identity="sha256:" + "a" * 64,
        environment_id="darwin-arm64-cp312",
        interpreter="python/bin/python3",
        bootstrap="bin/specfact-native-bootstrap",
        bubblewrap=None,
        backend="darwin-arm64",
        native_lease=lease,
    )
    request = runner.CapsuleMemberExecutionRequest(
        runtime=runtime,
        member="ruff",
        invocation_id="invocation-1",
        snapshot_root=snapshot,
        files=[selected_source],
        options=runner.ReviewOptions(),
        config_roots=(config_root,),
        project_runtime_root=project_runtime,
    )
    captured: dict[str, Any] = {}

    def prepare(**kwargs: Any) -> SimpleNamespace:
        captured.update(kwargs)
        staged = kwargs["project_snapshot"]
        if overlay == "generated":
            assert (staged / "pkg/_version.py").read_text() == "VERSION = 7\n"
            assert not (snapshot / "pkg/_version.py").exists()
        assert (staged / "pkg" / "example.py").read_text(encoding="utf-8") == "value = 1\n"
        assert (staged / "pkg" / "support.py").read_text(encoding="utf-8") == "HELPER = 2\n"
        assert (staged / ".specfact-native-config/1/ruff.toml").read_text(encoding="utf-8") == (
            "[lint]\nselect = ['F']\n"
        )
        assert (staged / "pkg" / "example.py").stat().st_mode & 0o222 == 0
        assert (staged / ".specfact-project-runtime/site-packages/fixture_dep/__init__.py").read_text() == (
            "VALUE = 1\n"
        )
        assert (staged / ".specfact-project-runtime/project-runtime.json").stat().st_mode & 0o222 == 0
        assert staged.stat().st_mode & 0o222 == 0
        return SimpleNamespace(output_root=kwargs["output_root"])

    class Session:
        def __init__(self, _transport: object) -> None:
            self.prepared: SimpleNamespace | None = None

        def __enter__(self) -> Session:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def launch(self, prepared: SimpleNamespace) -> int:
            self.prepared = prepared
            (prepared.output_root / "result.json").write_text(
                '{"evidence_outcome":"PASS","execution_state":"ran","findings":[],"member":"ruff"}\n',
                encoding="utf-8",
            )
            return 7

        def wait(self, handle: int, timeout_ms: int) -> SimpleNamespace:
            assert handle == 7
            assert timeout_ms == 120_000
            return SimpleNamespace(returncode=0)

    monkeypatch.setattr(runner.native_execution, "prepare_native_execution", prepare)
    monkeypatch.setattr(runner.native_execution, "BinaryNativeExecutionTransport", lambda value: value)
    monkeypatch.setattr(runner.native_execution, "NativeExecutionSession", Session)

    if overlay == "collision":
        response = runner._execute_native_capsule_member(request)
        assert response["evidence_outcome"] == "UNKNOWN"
        diagnostic = response["diagnostic"]
        assert isinstance(diagnostic, str)
        assert "generated source collision" in diagnostic
        assert source.read_text() == "value = 1\n"
        return
    assert runner._execute_native_capsule_member(request) == {
        "evidence_outcome": "PASS",
        "execution_state": "ran",
        "findings": [],
        "member": "ruff",
    }
    assert captured["lease"] is lease
    assert captured["plan_id"] == "analyzer.ruff.v1"
    assert captured["environment"] == {
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "NO_COLOR": "1",
        "PYTHONHASHSEED": "0",
        "PYTHONUTF8": "1",
        "TZ": "UTC",
    }


def test_native_member_execution_rejects_unmapped_member_without_launch(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    runtime = runner.CapsuleRuntime(
        root=tmp_path / "capsule",
        identity="sha256:" + "a" * 64,
        environment_id="darwin-arm64-cp312",
        interpreter="python/bin/python3",
        bootstrap="bin/specfact-native-bootstrap",
        bubblewrap=None,
        backend="darwin-arm64",
        native_lease=SimpleNamespace(),
    )
    snapshot = tmp_path / "source"
    snapshot.mkdir()
    source = snapshot / "example.py"
    source.write_text("value = 1\n", encoding="utf-8")
    request = runner.CapsuleMemberExecutionRequest(
        runtime=runtime,
        member="unknown-analyzer",
        invocation_id="invocation-1",
        snapshot_root=snapshot,
        files=[source],
        options=runner.ReviewOptions(),
    )
    monkeypatch.setattr(
        runner.native_execution,
        "prepare_native_execution",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("unsupported member launched")),
    )

    assert runner._execute_native_capsule_member(request) == {
        "member": "unknown-analyzer",
        "execution_state": "error",
        "evidence_outcome": "UNKNOWN",
        "findings": [],
        "diagnostic": "native_capsule_execution_plan_not_admitted:unknown-analyzer",
    }


def test_native_pytest_reaches_snapshot_with_project_origin_results(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    snapshot = tmp_path / "source"
    snapshot.mkdir()
    source = snapshot / "sample.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    observed: list[Path] = []
    runtime = runner.CapsuleRuntime(
        root=tmp_path / "capsule",
        identity="sha256:" + "a" * 64,
        environment_id="darwin-arm64-cp312",
        interpreter="python/bin/python3",
        bootstrap="bin/specfact-native-bootstrap",
        bubblewrap=None,
        backend="darwin-arm64",
        native_lease=SimpleNamespace(),
    )
    request = runner.CapsuleMemberExecutionRequest(
        runtime=runtime,
        member="targeted-pytest-coverage",
        invocation_id="invocation-1",
        snapshot_root=snapshot,
        files=[source],
        options=runner.ReviewOptions(),
        complete_pytest_inventory=True,
    )

    def capture(root: Path) -> list[tuple[str, bytes]]:
        observed.append(root)
        return [("sample.py", b"VALUE = 1\n"), ("test_sample.py", b"def test_value(): pass\n")]

    monkeypatch.setattr(runner, "_capture_native_snapshot", capture)
    monkeypatch.setattr(
        runner,
        "_capture_native_files",
        lambda *_args: (_ for _ in ()).throw(AssertionError("complete pytest used selected-file capture")),
    )
    monkeypatch.setattr(
        runner.native_execution,
        "NativeExecutionSession",
        lambda *_args: (_ for _ in ()).throw(ValueError("stop after snapshot selection")),
    )

    response = runner._execute_native_capsule_member(request)

    assert observed == [snapshot]
    assert response["diagnostic"].startswith("native_analyzer_execution_failed:")


def test_native_member_execution_replays_closed_broker_owned_tool_until_complete(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    snapshot = tmp_path / "source"
    snapshot.mkdir()
    source = snapshot / "pkg" / "example.py"
    source.parent.mkdir()
    source.write_text("value = missing\n", encoding="utf-8")
    lease = SimpleNamespace()
    runtime = runner.CapsuleRuntime(
        root=tmp_path / "capsule",
        identity="sha256:" + "a" * 64,
        environment_id="darwin-arm64-cp312",
        interpreter="python/bin/python3",
        bootstrap="bin/specfact-native-bootstrap",
        bubblewrap=None,
        backend="darwin-arm64",
        native_lease=lease,
    )
    request = runner.CapsuleMemberExecutionRequest(
        runtime=runtime,
        member="ruff",
        invocation_id="invocation-1",
        snapshot_root=snapshot,
        files=[source],
        options=runner.ReviewOptions(),
    )
    managed_request = {
        "argv": [
            "capsule-tool:ruff",
            "check",
            "--output-format",
            "json",
            "project/pkg/example.py",
        ],
        "capture_output": True,
        "cwd": "project",
        "environment": {},
        "member": "ruff",
        "schema": "specfact-managed-launch-request-v1",
        "sequence": 0,
        "text": True,
        "timeout_ms": 180_000,
        "tool": "ruff",
    }
    prepared_plans: list[str] = []

    def prepare(**kwargs: Any) -> SimpleNamespace:
        prepared_plans.append(kwargs["plan_id"])
        assert kwargs["timeout_ms"] == (180_000 if kwargs["plan_id"] == "tool.ruff.v1" else 120_000)
        return SimpleNamespace(
            plan_id=kwargs["plan_id"],
            project_snapshot=kwargs["project_snapshot"],
            output_root=kwargs["output_root"],
        )

    class Session:
        launches = 0

        def __init__(self, _transport: object) -> None:
            pass

        def __enter__(self) -> Session:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def launch(self, prepared: SimpleNamespace) -> int:
            self.prepared = prepared
            Session.launches += 1
            if Session.launches == 1:
                (prepared.output_root / "result.json").write_text(
                    json.dumps(
                        {
                            "diagnostic": "managed_tool_replay_required",
                            "evidence_outcome": "UNKNOWN",
                            "execution_state": "error",
                            "findings": [],
                            "managed_launch_request": managed_request,
                            "member": "ruff",
                        },
                        separators=(",", ":"),
                        sort_keys=True,
                    )
                    + "\n",
                    encoding="utf-8",
                )
            elif Session.launches == 2:
                assert prepared.plan_id == "tool.ruff.v1"
                tool_request = json.loads(
                    (prepared.project_snapshot / ".specfact-native-tool-request.json").read_text(encoding="utf-8")
                )
                assert tool_request == managed_request
            else:
                replies = json.loads(
                    (prepared.project_snapshot / ".specfact-native-replies.json").read_text(encoding="utf-8")
                )
                assert replies == {
                    "replies": [
                        {
                            "request": managed_request,
                            "result": {"returncode": 0, "stderr": "", "stdout": "[]"},
                        }
                    ],
                    "schema": "specfact-native-analyzer-replies-v1",
                }
                (prepared.output_root / "result.json").write_text(
                    '{"diagnostic":"","evidence_outcome":"PASS","execution_state":"ran",'
                    '"findings":[],"member":"ruff"}\n',
                    encoding="utf-8",
                )
            return Session.launches

        def wait(self, handle: int, timeout_ms: int) -> SimpleNamespace:
            assert timeout_ms == (180_000 if handle == 2 else 120_000)
            if handle == 1:
                return SimpleNamespace(returncode=75, stdout=b"", stderr=b"")
            if handle == 2:
                return SimpleNamespace(returncode=0, stdout=b"[]", stderr=b"")
            return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(runner.native_execution, "prepare_native_execution", prepare)
    monkeypatch.setattr(runner.native_execution, "BinaryNativeExecutionTransport", lambda value: value)
    monkeypatch.setattr(runner.native_execution, "NativeExecutionSession", Session)

    assert runner._execute_native_capsule_member(request) == {
        "diagnostic": "",
        "evidence_outcome": "PASS",
        "execution_state": "ran",
        "findings": [],
        "member": "ruff",
    }
    assert prepared_plans == ["analyzer.ruff.v1", "tool.ruff.v1", "analyzer.ruff.v1"]


def test_native_pytest_starts_managed_analyzer_with_project_origin_results(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    snapshot = tmp_path / "source"
    snapshot.mkdir()
    source = snapshot / "sample.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    runtime = runner.CapsuleRuntime(
        root=tmp_path / "capsule",
        identity="sha256:" + "a" * 64,
        environment_id="darwin-arm64-cp312",
        interpreter="python/bin/python3",
        bootstrap="bin/specfact-native-bootstrap",
        bubblewrap=None,
        backend="darwin-arm64",
        native_lease=SimpleNamespace(),
    )
    request = runner.CapsuleMemberExecutionRequest(
        runtime=runtime,
        member="targeted-pytest-coverage",
        invocation_id="invocation-1",
        snapshot_root=snapshot,
        files=[source],
        options=runner.ReviewOptions(),
    )
    managed = {
        "argv": ["capsule-tool:pytest", "-c", "trusted-observer"],
        "capture_output": True,
        "cwd": "project",
        "environment": {},
        "member": "targeted-pytest-coverage",
        "schema": "specfact-managed-launch-request-v1",
        "sequence": 0,
        "text": True,
        "timeout_ms": 30_000,
        "tool": "pytest",
    }

    class Session:
        launches = 0

        def __init__(self, _transport: object) -> None:
            pass

        def __enter__(self) -> Session:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def launch(self, prepared: SimpleNamespace) -> int:
            Session.launches += 1
            if Session.launches == 2:
                return 2
            assert Session.launches == 1
            (prepared.output_root / "result.json").write_text(
                json.dumps(
                    {
                        "diagnostic": "managed_tool_replay_required",
                        "evidence_outcome": "UNKNOWN",
                        "execution_state": "error",
                        "findings": [],
                        "managed_launch_request": managed,
                        "member": "targeted-pytest-coverage",
                    }
                ),
                encoding="utf-8",
            )
            return Session.launches

        def wait(self, handle: int, _timeout_ms: int) -> SimpleNamespace:
            if handle == 2:
                raise ValueError("stop after managed pytest tool launch")
            return SimpleNamespace(returncode=75)

    monkeypatch.setattr(
        runner.native_execution,
        "prepare_native_execution",
        lambda **kwargs: SimpleNamespace(output_root=kwargs["output_root"]),
    )
    monkeypatch.setattr(runner.native_execution, "BinaryNativeExecutionTransport", lambda value: value)
    monkeypatch.setattr(runner.native_execution, "NativeExecutionSession", Session)

    response = runner._execute_native_capsule_member(request)
    assert response["diagnostic"].startswith("native_analyzer_execution_failed:")
    assert Session.launches == 2
