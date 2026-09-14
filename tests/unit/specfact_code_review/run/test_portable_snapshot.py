"""Automatic scope attachment preserves static evidence on preparation failure."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from specfact_code_review.run import portable_snapshot, runner
from specfact_code_review.run.portable_snapshot import (
    ProjectSnapshotRequest,
    project_runtime_requested,
    run_project_snapshot,
)
from specfact_code_review.run.portable_worker import DEPENDENT_MEMBERS
from specfact_code_review.run.runtime_models import PreparedRuntime, ProjectRuntimeError


def test_failed_preparation_never_runs_dependency_members(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname="consumer"\ndependencies=["pandas"]\n')
    source = tmp_path / "app.py"
    source.write_text("import pandas\n")
    calls = []

    def fail(*_args, **_kwargs):
        raise ProjectRuntimeError("project_native_library_missing:libodbc.so.2")

    monkeypatch.setattr("specfact_code_review.run.portable_snapshot.prepare_runtime", fail)

    def dispatch(request, **_kwargs):
        calls.append(request.member)
        return {"execution_state": "ran", "evidence_outcome": "PASS", "findings": []}

    monkeypatch.setattr(runner, "_dispatch_capsule_member", dispatch)
    runtime = SimpleNamespace(identity="sha256:" + "a" * 64, environment_id="linux-x86_64-cp312")
    snapshot, evidence = run_project_snapshot(
        runtime,
        ProjectSnapshotRequest(
            snapshot_root=tmp_path, files=[source], options=runner.ReviewOptions(), assurance_kind="explicit_files"
        ),
    )
    assert not set(calls) & {"basedpyright", "pylint", "contracts", "targeted-pytest-coverage"}
    assert "ruff" in calls
    assert evidence["diagnostic"] == "project_native_library_missing:libodbc.so.2"
    assert snapshot.evidence["basedpyright"]["evidence_outcome"] == "UNKNOWN"


def test_runtime_kwargs_are_accepted(tmp_path: Path) -> None:
    config = tmp_path / "review.toml"
    options = runner._review_options_from_kwargs(None, {"project_config": config})
    assert options.project_config == config


def test_immutable_pair_prepares_each_side_and_downgrades_authority(tmp_path: Path, monkeypatch) -> None:

    base_root, head_root = tmp_path / "base", tmp_path / "head"
    base_root.mkdir()
    head_root.mkdir()
    calls = []

    def run_side(_runtime, request):
        calls.append((request.snapshot_root, request.options.project_runtime))
        return runner.CapsuleSnapshotResult({}, {}), {"identity": str(request.snapshot_root)}

    monkeypatch.setattr(portable_snapshot, "run_project_snapshot", run_side)
    monkeypatch.setattr(runner, "_snapshot_python_files", lambda *args: [])
    monkeypatch.setattr(runner, "_classify_range_findings", lambda *args: ({}, {}))
    monkeypatch.setattr(runner, "_capsule_report", lambda *args, **kwargs: kwargs["scope_evidence"])
    resolution = SimpleNamespace(
        base_snapshot=SimpleNamespace(root=base_root, contents={"app.py": b""}),
        head_snapshot=SimpleNamespace(root=head_root, contents={"app.py": b""}),
        selected_paths=("pyproject.toml",),
    )
    descriptor = tmp_path / "project-runtime.json"
    observed = portable_snapshot.run_project_scope_pair(
        resolution,
        runtime=object(),
        options=runner.ReviewOptions(project_runtime=descriptor),
        scope_evidence={"assurance_kind": "range_candidate"},
    )
    assert calls == [(base_root, None), (head_root, descriptor)]
    assert observed["assurance_kind"] == "range_preview"
    assert observed["project_runtime"]["base"]["identity"] != observed["project_runtime"]["head"]["identity"]


def _portable_range_resolution(tmp_path: Path, change: str, source: bytes) -> SimpleNamespace:
    base_contents = {"unrelated.py": source, "pyproject.toml": b"[project]\nname='fixture'\n"}
    head_contents = dict(base_contents)
    selected: tuple[str, ...] = () if change == "empty" else ("pyproject.toml",)
    if change in {"deleted", "added"}:
        selected = (f"{change}.py",)
        (base_contents if change == "deleted" else head_contents)[selected[0]] = source
        (head_contents if change == "deleted" else base_contents).pop("pyproject.toml")
    snapshots = []
    for side, contents in (("base", base_contents), ("head", head_contents)):
        root = tmp_path / side
        root.mkdir()
        for name, content in contents.items():
            (root / name).write_bytes(content)
        snapshots.append(SimpleNamespace(root=root, contents=contents))
    return SimpleNamespace(
        base_snapshot=snapshots[0],
        head_snapshot=snapshots[1],
        selected_paths=selected,
        path_statuses={f"{change}.py": "D" if change == "deleted" else "A"} if change in {"deleted", "added"} else {},
    )


@pytest.mark.parametrize("change", ["deleted", "added", "metadata", "empty"])
@pytest.mark.parametrize("preparation_fails", [False, True])
def test_portable_range_keeps_absent_selection_out_of_unrelated_findings(
    tmp_path: Path, monkeypatch, change: str, preparation_fails: bool
) -> None:
    source = b"def check():\n    return missing_name\n"
    resolution = _portable_range_resolution(tmp_path, change, source)
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    prepared = PreparedRuntime(artifact, artifact / "project-runtime.json", "sha256:" + "b" * 64, {"inventory": {}})

    def prepare(plan, **_context):
        if preparation_fails and not (plan.root / "pyproject.toml").exists():
            raise ProjectRuntimeError("project_fixture_preparation_unavailable")
        return prepared

    executed = []

    def analyze(request):
        findings = []
        if request.member == "ruff":
            for path in request.files:
                assert path.read_bytes() == source
                relative = path.relative_to(request.snapshot_root).as_posix()
                executed.append(relative)
                findings.append(
                    {
                        "category": "style",
                        "severity": "warning",
                        "tool": "ruff",
                        "rule": "F821",
                        "file": relative,
                        "line": 2,
                        "message": "Undefined name missing_name",
                        "fixable": False,
                    }
                )
        return {"execution_state": "ran", "evidence_outcome": "PASS", "findings": findings}

    monkeypatch.setattr(portable_snapshot, "prepare_runtime", prepare)
    monkeypatch.setattr(portable_snapshot, "load_runtime", lambda *_args, **_context: prepared)
    monkeypatch.setattr(runner, "_execute_capsule_member", analyze)
    runtime = runner.CapsuleRuntime(
        tmp_path,
        "sha256:" + "a" * 64,
        "linux-x86_64-cp312",
        "python",
        "bootstrap",
        runner.BubblewrapIdentity(
            path="bwrap",
            format="ELF",
            architecture="x86_64",
            linkage="static",
            interpreter=(),
            needed=(),
            sha256="a" * 64,
            descriptor_digest="b" * 64,
        ),
    )
    report = portable_snapshot.run_project_scope_pair(
        resolution,
        runtime=runtime,
        options=runner.ReviewOptions(no_tests=True),
        scope_evidence={"assurance_kind": "range_preview"},
    )
    expected = {
        "deleted": (["deleted.py"], [("deleted.py", "fixed")]),
        "added": (["added.py"], [("added.py", "introduced")]),
        "metadata": (["unrelated.py", "unrelated.py"], [("unrelated.py", "unchanged")]),
        "empty": ([], []),
    }
    expected_files, expected_findings = expected[change]
    assert [(finding.file, finding.differential_state) for finding in report.findings] == expected_findings
    assert executed == expected_files
    if preparation_fails and change in {"deleted", "added"}:
        absent_side = "head" if change == "deleted" else "base"
        assert report.scope_evidence["project_runtime"][absent_side]["status"] == "UNKNOWN"


def test_source_change_during_full_analysis_invalidates_runtime_binding(tmp_path: Path, monkeypatch) -> None:

    root = tmp_path / "project"
    root.mkdir()
    source = root / "app.py"
    source.write_text("VALUE = 1\n")
    artifact = tmp_path / "artifact"
    prepared = PreparedRuntime(artifact, artifact / "project-runtime.json", "sha256:" + "b" * 64, {"inventory": {}})
    runtime = runner.CapsuleRuntime(
        root,
        "sha256:" + "a" * 64,
        "linux-x86_64-cp312",
        "python",
        "bootstrap",
        runner.BubblewrapIdentity(
            path="bwrap",
            format="ELF",
            architecture="x86_64",
            linkage="static",
            interpreter=(),
            needed=(),
            sha256="a" * 64,
            descriptor_digest="b" * 64,
        ),
    )
    monkeypatch.setattr(portable_snapshot, "prepare_runtime", lambda *args, **kwargs: prepared)
    monkeypatch.setattr(portable_snapshot, "load_runtime", lambda *args, **kwargs: prepared)

    def analyze(*_args, **_kwargs):
        source.write_text("VALUE = 2\n")
        return runner.CapsuleSnapshotResult({name: {"evidence_outcome": "PASS"} for name in DEPENDENT_MEMBERS}, {})

    monkeypatch.setattr(runner, "_run_capsule_snapshot", analyze)
    snapshot, evidence = run_project_snapshot(
        runtime, ProjectSnapshotRequest(root, [source], runner.ReviewOptions(no_tests=True), "full")
    )
    assert evidence["status"] == "UNKNOWN"
    assert all(snapshot.evidence[name]["evidence_outcome"] == "UNKNOWN" for name in DEPENDENT_MEMBERS)


def test_pip_tools_source_input_triggers_automatic_runtime(tmp_path: Path) -> None:

    (tmp_path / "requirements.in").write_text("requests\n")
    assert project_runtime_requested(tmp_path, SimpleNamespace(project_config=None, project_runtime=None))


@pytest.mark.parametrize("python_pin", [None, "3.12", "3.99"])
def test_python_version_only_project_routes_preparation_and_preserves_static_fallback(
    tmp_path: Path, monkeypatch, python_pin: str | None
) -> None:
    source = tmp_path / "app.py"
    source.write_text("VALUE = 1\n")
    if python_pin is not None:
        (tmp_path / ".python-version").write_text(python_pin + "\n")
    monkeypatch.chdir(tmp_path)
    prepared_pins = []
    members = []
    local_snapshot = runner.CapsuleSnapshotResult({}, {})

    def prepare_project(plan, **_kwargs):
        prepared_pins.append(plan.python)
        raise ProjectRuntimeError("project_native_library_missing:libfixture.so")

    def dispatch(request, **_kwargs):
        members.append(request.member)
        return {"execution_state": "ran", "evidence_outcome": "PASS", "findings": []}

    monkeypatch.setattr(portable_snapshot, "prepare_runtime", prepare_project)
    monkeypatch.setattr(runner, "_dispatch_capsule_member", dispatch)
    monkeypatch.setattr(runner, "_run_local_capsule_snapshot", lambda *_args, **_kwargs: local_snapshot)
    monkeypatch.setattr(runner, "_finalize_local_capsule_snapshot", lambda snapshot, _context: snapshot)
    runtime = cast(
        runner.CapsuleRuntime, SimpleNamespace(identity="sha256:" + "a" * 64, environment_id="linux-x86_64-cp312")
    )
    evidence: dict[str, Any] = {"assurance_kind": "explicit_files"}
    snapshot = runner._run_local_capsule_context(runtime, [source], runner.ReviewOptions(), evidence, "explicit_files")
    if python_pin is None:
        assert snapshot is local_snapshot
        assert not prepared_pins and not members
        assert "project_runtime" not in evidence
    else:
        assert prepared_pins == (["3.12"] if python_pin == "3.12" else [])
        assert "ruff" in members and not set(members) & DEPENDENT_MEMBERS
        assert snapshot.evidence["basedpyright"]["evidence_outcome"] == "UNKNOWN"
        expected = (
            "project_native_library_missing:libfixture.so"
            if python_pin == "3.12"
            else "project_python_incompatible:pin=3.99"
        )
        assert evidence["project_runtime"]["diagnostic"].startswith(expected)
        assert evidence["project_runtime"]["status"] == "UNKNOWN"


@pytest.mark.parametrize("relative", [False, True])
def test_analysis_source_copy_excludes_local_environment_files(tmp_path: Path, monkeypatch, relative: bool) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "app.py").write_text("VALUE = 1\n")
    (source / ".env").write_text("SYNTHETIC_SECRET=fixture\n")
    (source / ".venv").mkdir()
    (source / ".venv/private.txt").write_text("synthetic excluded fixture")
    observed = []

    def analyze(_runtime, *, snapshot_root, files, **_context):
        assert snapshot_root != source
        assert not (snapshot_root / ".env").exists()
        assert not (snapshot_root / ".venv").exists()
        assert files == [snapshot_root / "app.py"]
        assert files[0].read_text() == "VALUE = 1\n"
        observed.append(snapshot_root)
        return runner.CapsuleSnapshotResult({}, {})

    monkeypatch.setattr(runner, "_run_capsule_snapshot", analyze)
    selected = Path("app.py") if relative else source / "app.py"
    request = ProjectSnapshotRequest(source, [selected], runner.ReviewOptions(), "explicit_files")
    portable_snapshot._run_in_private_source(object(), request, runner.CapsuleSnapshotSettings())
    assert observed and not observed[0].exists()
    assert (source / ".env").read_text() == "SYNTHETIC_SECRET=fixture\n"


@pytest.mark.parametrize(
    ("filename", "contents", "diagnostic"),
    [
        ("setup.cfg", "missing section header\n", "project_config_invalid:setup.cfg:"),
        ("pyproject.toml", "tool=1\n", "project_config_invalid:pyproject.toml:tool"),
        ("hatch.toml", "envs=false\n", "project_config_invalid:hatch.toml:envs"),
        ("pytest.toml", "pytest=1\n", "project_pytest_config_invalid:pytest.toml:pytest"),
        ("pyproject.toml", "[tool]\npytest=false\n", "project_pytest_config_invalid:pyproject.toml:tool.pytest"),
        (
            "pyproject.toml",
            "[tool.pytest]\nini_options=[]\n",
            "project_pytest_config_invalid:pyproject.toml:tool.pytest.ini_options",
        ),
        (
            "pyproject.toml",
            "[tool.pytest.ini_options]\npythonpath=[1]\n",
            "project_pytest_config_invalid:pyproject.toml:pythonpath",
        ),
        (
            "pyproject.toml",
            "[tool.pytest.ini_options]\ntestpaths=1\n",
            "project_pytest_config_invalid:pyproject.toml:testpaths",
        ),
    ],
)
def test_malformed_configuration_preserves_independent_analyzer_evidence(
    tmp_path: Path, monkeypatch, filename: str, contents: str, diagnostic: str
) -> None:
    (tmp_path / filename).write_text(contents)
    source = tmp_path / "app.py"
    source.write_text("import dependency\n")
    calls = []

    def dispatch(request, **_context):
        calls.append(request.member)
        return {"execution_state": "ran", "evidence_outcome": "PASS", "findings": []}

    monkeypatch.setattr(runner, "_dispatch_capsule_member", dispatch)
    runtime = SimpleNamespace(identity="sha256:" + "a" * 64, environment_id="linux-x86_64-cp312")
    snapshot, evidence = run_project_snapshot(
        runtime, ProjectSnapshotRequest(tmp_path, [source], runner.ReviewOptions(), "explicit_files")
    )
    assert "ruff" in calls and not set(calls) & DEPENDENT_MEMBERS
    assert evidence["diagnostic"].startswith(diagnostic)
    assert snapshot.evidence["basedpyright"]["evidence_outcome"] == "UNKNOWN"


@pytest.mark.parametrize("selected", ["../outside.py", "/outside.py"])
def test_analysis_source_copy_rejects_escaping_selection(tmp_path: Path, monkeypatch, selected: str) -> None:
    def unexpected(*_args, **_kwargs):
        pytest.fail("escaping selection reached analysis")

    monkeypatch.setattr(runner, "_run_capsule_snapshot", unexpected)
    request = ProjectSnapshotRequest(tmp_path, [Path(selected)], runner.ReviewOptions(), "explicit_files")
    with pytest.raises(ValueError):
        portable_snapshot._run_in_private_source(object(), request, runner.CapsuleSnapshotSettings())


@pytest.mark.parametrize("reason", ["project_config_invalid:setup.cfg", "project_native_library_missing:libodbc.so.2"])
def test_preparation_fallback_uses_only_sanitized_source(tmp_path: Path, monkeypatch, reason: str) -> None:
    source = tmp_path / "app.py"
    source.write_text("VALUE = 1\n")
    (tmp_path / ".env").write_text("PRIVATE=fixture\n")
    (tmp_path / ".git/objects").mkdir(parents=True)
    observed = []

    def dispatch(request, **_kwargs):
        assert request.snapshot_root != tmp_path
        assert not (request.snapshot_root / ".env").exists()
        assert not (request.snapshot_root / ".git").exists()
        assert request.files[0].read_text() == "VALUE = 1\n"
        observed.append(request.member)
        return {"execution_state": "ran", "evidence_outcome": "PASS", "findings": []}

    monkeypatch.setattr(runner, "_dispatch_capsule_member", dispatch)
    runtime = SimpleNamespace(identity="sha256:" + "a" * 64, environment_id="linux-x86_64-cp312")
    snapshot, evidence = portable_snapshot._failed_project_snapshot(
        runtime, snapshot_root=tmp_path, files=[source], options=runner.ReviewOptions(), reason=reason
    )
    assert "ruff" in observed and not set(observed) & DEPENDENT_MEMBERS
    assert snapshot.evidence["basedpyright"]["evidence_outcome"] == "UNKNOWN"
    assert evidence["diagnostic"] == reason


def test_unsafe_fallback_source_never_dispatches_analyzer(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "app.py"
    source.write_text("VALUE = 1\n")
    (tmp_path / ".env").write_text("PRIVATE=fixture\n")
    (tmp_path / "alias.py").symlink_to(".env")

    def dispatch(*_args, **_kwargs):
        pytest.fail("unsafe original source reached an analyzer")

    monkeypatch.setattr(runner, "_dispatch_capsule_member", dispatch)
    runtime = SimpleNamespace(identity="sha256:" + "a" * 64, environment_id="linux-x86_64-cp312")
    snapshot, evidence = run_project_snapshot(
        runtime, ProjectSnapshotRequest(tmp_path, [source], runner.ReviewOptions(), "explicit_files")
    )
    assert evidence["status"] == "UNKNOWN"
    assert "project_source_copy_failed" in evidence["diagnostic"]
    assert all(row["evidence_outcome"] == "UNKNOWN" for row in snapshot.evidence.values())
