"""Automatic scope attachment preserves static evidence on preparation failure."""

import configparser
import json
import shutil
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal, cast

import pytest

from specfact_code_review.run import portable_snapshot, runner
from specfact_code_review.run.portable_snapshot import (
    ProjectSnapshotRequest,
    project_runtime_requested,
    run_project_snapshot,
)
from specfact_code_review.run.portable_worker import DEPENDENT_MEMBERS
from specfact_code_review.run.runtime_models import PreparedRuntime, ProjectPlan, ProjectRuntimeError


def test_native_project_origin_policy_preserves_doctests_and_coverage_exclusions(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\naddopts="--doctest-modules"\ntestpaths=["tests"]\n'
        '[tool.coverage.report]\nexclude_lines=["pragma: no cover"]\n'
    )
    builder = runner._PolicyBindingBuilder()
    try:
        runner._bind_pytest_coverage_policy(builder, tmp_path, local_project_assurance="explicit_files")
        contents = {p.name: p.read_text() for root in builder.cleanup_roots for p in root.iterdir() if p.is_file()}
        assert "--doctest-modules" in contents["pytest.ini"]
        assert "pragma: no cover" in contents["coveragerc"]
    finally:
        for root in builder.cleanup_roots:
            shutil.rmtree(root)
    with pytest.raises(ValueError, match="pytest_selection_policy_unsupported"):
        runner._bind_pytest_coverage_policy(runner._PolicyBindingBuilder(), tmp_path)
    with pytest.raises(ValueError, match="project_origin_not_local"):
        runner._bind_pytest_coverage_policy(
            runner._PolicyBindingBuilder(), tmp_path, local_project_assurance="range_candidate"
        )
    assert runner.project_coverage_policy({"report:exclude_lines": ["pragma: no cover"]}).status == "UNKNOWN"


@pytest.mark.parametrize("filename, section", [(".coveragerc", "report"), ("setup.cfg", "coverage:report")])
def test_native_local_coverage_preserves_multiline_ini_expressions(tmp_path, filename, section):
    expressions = ["pragma: no cover", "if TYPE_CHECKING:", "[section-like-expression]", "else:"]
    (tmp_path / filename).write_text(
        f"[{section}]\nexclude_lines =\n" + "".join(f"    {value}\n" for value in expressions)
    )
    builder = runner._PolicyBindingBuilder()
    try:
        runner._bind_pytest_coverage_policy(builder, tmp_path, local_project_assurance="worktree")
        path = next(root / "coveragerc" for root in builder.cleanup_roots if (root / "coveragerc").is_file())
        parser = configparser.ConfigParser(interpolation=None)
        parser.read_string(path.read_text())
        assert parser.sections() == ["report", "run"]
        assert parser["report"]["exclude_lines"].splitlines() == expressions
        assert set(parser["report"]) == {"exclude_lines"}
    finally:
        for root in builder.cleanup_roots:
            shutil.rmtree(root)


@pytest.mark.parametrize("assurance", ["range_candidate", "pr_range", "unknown"])
def test_native_local_policy_rejects_protected_or_unknown_assurance(tmp_path, assurance):
    with pytest.raises(ValueError, match="project_origin_not_local"):
        runner._bind_pytest_coverage_policy(runner._PolicyBindingBuilder(), tmp_path, local_project_assurance=assurance)


@pytest.mark.parametrize("local_assurance", [None, "worktree"])
def test_native_local_policy_keeps_coverage_plugins_unsupported(tmp_path, local_assurance):
    (tmp_path / ".coveragerc").write_text("[run]\nplugins = malicious_project_plugin\n")
    with pytest.raises(ValueError, match="coverage_policy_unsupported"):
        runner._bind_pytest_coverage_policy(
            runner._PolicyBindingBuilder(), tmp_path, local_project_assurance=local_assurance
        )


@pytest.mark.parametrize("key", ["exclude_lines", "exclude_also", "partial_branches", "partial_also"])
def test_native_local_toml_exclusions_cannot_inject_coverage_sections(tmp_path, key):
    from coverage.config import read_coverage_config

    expression = "foo\n[coverage:run]\nplugins = project_plugin"
    (tmp_path / "pyproject.toml").write_text(f'[tool.coverage.report]\n{key}=["""{expression}"""]\n')
    builder = runner._PolicyBindingBuilder()
    try:
        runner._bind_pytest_coverage_policy(builder, tmp_path, local_project_assurance="worktree")
        path = next(
            path for root in builder.cleanup_roots for path in root.iterdir() if path.name.startswith("coveragerc")
        )
        projected = read_coverage_config(str(path), warn=lambda _message: None)
        assert projected.plugins == []
        assert projected.data_file.startswith("/opt/specfact/tmp/coverage/")
        field = "exclude_list" if key.startswith("exclude") else "partial_list"
        assert expression in getattr(projected, field)
    finally:
        for root in builder.cleanup_roots:
            shutil.rmtree(root)


@pytest.mark.parametrize("key, field", [("exclude_also", "exclude_list"), ("partial_also", "partial_list")])
def test_native_local_additive_exclusions_preserve_coverage_defaults(tmp_path, key, field):
    from coverage.config import read_coverage_config

    expression = "@overload"
    (tmp_path / "pyproject.toml").write_text(f'[tool.coverage.report]\n{key}=["{expression}"]\n')
    defaults = read_coverage_config(False, warn=lambda _message: None)
    builder = runner._PolicyBindingBuilder()
    try:
        runner._bind_pytest_coverage_policy(builder, tmp_path, local_project_assurance="worktree")
        path = next(root / "coveragerc" for root in builder.cleanup_roots if (root / "coveragerc").is_file())
        projected = read_coverage_config(str(path), warn=lambda _message: None)
        assert getattr(projected, field) == [*getattr(defaults, field), expression]
    finally:
        for root in builder.cleanup_roots:
            shutil.rmtree(root)


def test_native_basedpyright_uses_verified_editable_source_roots(tmp_path):
    source, configs = tmp_path / "source", tmp_path / "config"
    (source / "src/customer").mkdir(parents=True)
    configs.mkdir()
    (source / "src/customer/__init__.py").write_text("VALUE=1\n")
    config = portable_snapshot._write_native_basedpyright_config(
        source, [Path("src/customer/__init__.py")], configs, source_roots=("src",)
    )
    document = json.loads(config.read_text())
    assert document["extraPaths"] == ["../../.specfact-project-runtime/site-packages", "../../src"]


def test_native_basedpyright_rejects_unbound_source_roots(tmp_path):
    source, configs = tmp_path / "source", tmp_path / "config"
    source.mkdir()
    configs.mkdir()
    with pytest.raises(ValueError, match="source_root"):
        portable_snapshot._write_native_basedpyright_config(source, [], configs, source_roots=("../host",))


@pytest.mark.parametrize(
    ("backend", "expected_argv"),
    [
        ("linux-x86_64", ("--pythonpath", "/opt/specfact/project-runtime/bin/python")),
        ("darwin-arm64", ("--project", "/opt/specfact/config/1/basedpyright-native.json")),
    ],
)
def test_project_snapshot_configures_basedpyright_for_platform_runtime(
    tmp_path: Path, monkeypatch, backend: Literal["linux-x86_64", "darwin-arm64"], expected_argv: tuple[str, ...]
) -> None:
    source = tmp_path / "app.py"
    source.write_text("import dependency\n", encoding="utf-8")
    artifact = tmp_path / "project-runtime"
    artifact.mkdir()
    prepared = PreparedRuntime(
        artifact,
        artifact / "project-runtime.json",
        "sha256:" + "b" * 64,
        {"inventory": {}},
    )
    observed: list[runner.CapsuleSnapshotSettings] = []

    monkeypatch.setattr(portable_snapshot, "prepare_runtime", lambda *_args, **_kwargs: prepared)
    monkeypatch.setattr(portable_snapshot, "load_runtime", lambda *_args, **_kwargs: prepared)
    monkeypatch.setattr(portable_snapshot, "verify_inputs", lambda _plan: None)

    def run_snapshot(_runtime, _request, settings):
        observed.append(settings)
        if backend == "darwin-arm64":
            assert len(settings.config_roots) == 1
            config = settings.config_roots[0] / "basedpyright-native.json"
            values = json.loads(config.read_text(encoding="utf-8"))
            assert values == {
                "extraPaths": ["../../.specfact-project-runtime/site-packages"],
                "include": ["../../app.py"],
            }
            assert config.stat().st_mode & 0o222 == 0
        else:
            assert settings.config_roots == ()
        return runner.CapsuleSnapshotResult({}, {})

    monkeypatch.setattr(portable_snapshot, "_run_in_private_source", run_snapshot)
    runtime = runner.CapsuleRuntime(
        tmp_path,
        "sha256:" + "a" * 64,
        ("darwin-arm64-cp312" if backend == "darwin-arm64" else "linux-x86_64-cp312"),
        "python",
        "bootstrap",
        None,
        backend=backend,
    )
    plan = cast(
        ProjectPlan, SimpleNamespace(root=tmp_path, identity="sha256:" + "c" * 64, source_roots=(), pytest_config={})
    )

    portable_snapshot._run_project_snapshot(
        runtime,
        ProjectSnapshotRequest(tmp_path, [source], runner.ReviewOptions(no_tests=True), "explicit_files"),
        plan,
    )

    member_argv = observed[0].member_argv
    assert member_argv is not None
    assert member_argv["basedpyright"] == expected_argv
    if backend == "darwin-arm64":
        assert all("/bin/python" not in argument for argument in member_argv["basedpyright"])


@pytest.mark.parametrize("projection_fails", [False, True])
@pytest.mark.parametrize("full_discovery", [False, True])
@pytest.mark.parametrize("declared_roots", [["tests"], ["."], []])
def test_darwin_project_snapshot_binds_native_managed_pytest_contract(
    tmp_path: Path, monkeypatch, projection_fails, full_discovery, declared_roots
) -> None:
    (tmp_path / "pytest.ini").write_text("[pytest]\ntestpaths=tests\n")
    source = tmp_path / "app.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    tests = tmp_path / "tests"
    tests.mkdir()
    selected_test = tests / "test_runtime.py"
    selected_test.write_text("def test_runtime():\n    assert True\n", encoding="utf-8")
    artifact = tmp_path / "project-runtime"
    artifact.mkdir()
    prepared = PreparedRuntime(
        artifact,
        artifact / "project-runtime.json",
        "sha256:" + "b" * 64,
        {"inventory": {}},
    )
    observed: list[runner.CapsuleSnapshotSettings] = []

    monkeypatch.setattr(portable_snapshot, "prepare_runtime", lambda *_args, **_kwargs: prepared)
    monkeypatch.setattr(portable_snapshot, "load_runtime", lambda *_args, **_kwargs: prepared)
    monkeypatch.setattr(portable_snapshot, "verify_inputs", lambda _plan: None)
    monkeypatch.setattr(
        portable_snapshot,
        "select_test_paths",
        lambda *_args, **_kwargs: () if full_discovery else ("tests/test_runtime.py",),
    )
    if projection_fails:

        def fail_projection(*_args, **_kwargs):
            raise ValueError("coverage_policy_unsupported")

        monkeypatch.setattr(runner, "_bind_pytest_coverage_policy", fail_projection)

    def run_snapshot(_runtime, _request, settings):
        observed.append(settings)
        assert settings.member_argv is not None
        contract_argv = settings.member_argv["contracts"]
        assert contract_argv[0] == "contract-inputs-v2" and len(contract_argv) == 2
        inventory = json.loads((settings.config_roots[-1] / "contracts-native.json").read_text())
        assert inventory["test_roots"] == (["tests"] if declared_roots == ["tests"] else ["tests/test_runtime.py"])
        if projection_fails:
            assert settings.unavailable_members["targeted-pytest-coverage"]["evidence_outcome"] == "UNKNOWN"
            return runner.CapsuleSnapshotResult({}, {})
        argv = settings.member_argv["targeted-pytest-coverage"]
        assert argv[0] == "-c"
        assert argv[2:4] == ("--rootdir", "/opt/specfact/snapshot")
        assert argv[4] == "--cov-config"
        assert argv[-1:] == ("--",) if full_discovery else argv[-2:] == ("--", "tests/test_runtime.py")
        assert runner._complete_snapshot_pytest("targeted-pytest-coverage", settings)
        assert "portable-pytest-v2" not in argv
        assert settings.portable_runtime is False
        assert len(settings.config_roots) == 3
        assert all(root.is_dir() for root in settings.config_roots)
        return runner.CapsuleSnapshotResult({}, {})

    monkeypatch.setattr(portable_snapshot, "_run_in_private_source", run_snapshot)
    runtime = runner.CapsuleRuntime(
        tmp_path,
        "sha256:" + "a" * 64,
        "darwin-arm64-cp312",
        "python",
        "bootstrap",
        None,
        backend="darwin-arm64",
    )
    plan = cast(
        ProjectPlan,
        SimpleNamespace(
            root=tmp_path, identity="sha256:" + "c" * 64, source_roots=(), pytest_config={"testpaths": declared_roots}
        ),
    )

    portable_snapshot._run_project_snapshot(
        runtime,
        ProjectSnapshotRequest(tmp_path, [source], runner.ReviewOptions(), "full"),
        plan,
    )

    assert observed


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


def test_native_local_multiline_unicode_coverage_preserves_threshold(tmp_path):
    from coverage.config import read_coverage_config

    expression = "first\nsecond 😀"
    (tmp_path / "pyproject.toml").write_text(
        '[tool.coverage.report]\nexclude_lines=["""' + expression + '"""]\nfail_under=99\n'
    )
    builder = runner._PolicyBindingBuilder()
    try:
        runner._bind_pytest_coverage_policy(builder, tmp_path, local_project_assurance="worktree")
        path = next(
            path for root in builder.cleanup_roots for path in root.iterdir() if path.name.startswith("coveragerc")
        )
        projected = read_coverage_config(str(path), warn=lambda _message: None)
        assert expression in projected.exclude_list
        assert runner._coverage_threshold_from_policy_argv(("--cov-config", str(path))) == 99
    finally:
        for root in builder.cleanup_roots:
            shutil.rmtree(root)


def test_projected_toml_coverage_enforces_requested_threshold(tmp_path):
    path = tmp_path / "coveragerc.toml"
    path.write_text("[tool.coverage.report]\nfail_under=99\n")
    assert runner._coverage_threshold_from_policy_argv(("--cov-config", str(path))) == 99


def test_contract_default_inventory_does_not_exclude_production_sources(tmp_path):
    from specfact_code_review.run.native_worker import _validated_adapter_argv
    from specfact_code_review.run.portable_worker import contract_inputs

    (tmp_path / "app.py").write_text("def calculate(): return 1\n")
    plan = cast(ProjectPlan, SimpleNamespace(root=tmp_path, pytest_config={}))
    assert contract_inputs(plan) == ("contract-inputs-v2",)
    path = portable_snapshot._write_native_contract_inventory(plan, tmp_path)
    assert json.loads(path.read_text())["test_roots"] == []
    argv = ["contract-inputs-v2", "/opt/specfact/config/1/" + path.name]
    assert _validated_adapter_argv("contracts", argv) == argv
    assert not runner._path_is_below_test_root(Path("app.py"), ())


def test_native_contract_inventory_keeps_transport_bounded(tmp_path):
    from specfact_code_review.run.native_worker import _native_contract_roots, _validated_adapter_argv

    tests = tmp_path / "tests"
    tests.mkdir()
    for index in range(64):
        (tests / f"test_{index}.py").write_text("def test_value(): assert True\n")
    configs = tmp_path / ".specfact-native-config/1"
    configs.mkdir(parents=True)
    plan = cast(ProjectPlan, SimpleNamespace(root=tmp_path, pytest_config={}))
    path = portable_snapshot._write_native_contract_inventory(plan, configs)
    argv = ["contract-inputs-v2", "/opt/specfact/config/1/" + path.name]
    assert _validated_adapter_argv("contracts", argv) == argv
    bound = ["contract-inputs-v2", str(path)]
    assert len(_native_contract_roots(bound, tmp_path)) == 64
    document = json.loads(path.read_text())
    path.chmod(0o600)
    document["test_roots"] = ["../host"]
    path.write_text(json.dumps(document))
    with pytest.raises(ValueError):
        _native_contract_roots(bound, tmp_path)
