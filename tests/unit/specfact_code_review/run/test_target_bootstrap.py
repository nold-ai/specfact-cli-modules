"""Analyzer entry-point lookup rejects project-owned replacements."""

import json
import os
import shutil
import subprocess
import sys
import zipfile
from importlib.metadata import DistributionFinder
from pathlib import Path

import pytest

from specfact_code_review.run import target_bootstrap
from specfact_code_review.run.runtime_discovery import discover_project
from specfact_code_review.run.target_bootstrap import _project_python_command, python_execution_domain


def test_analyzer_entry_point_is_confined_to_verified_root(tmp_path: Path, monkeypatch) -> None:
    analyzers = tmp_path / "analyzers"
    analyzers.mkdir()
    (analyzers / "owned.py").write_text('raise AssertionError("lookup must not execute")\n')
    monkeypatch.setattr(target_bootstrap, "ANALYZERS", analyzers)
    finder = target_bootstrap.AnalyzerFinder({"owned"})
    specification = finder.find_spec("owned")
    assert specification is not None
    assert specification.origin == str(analyzers / "owned.py")
    assert finder.find_spec("project_dependency") is None
    hostile = tmp_path / "hostile"
    hostile.mkdir()
    (hostile / "owned.py").write_text('raise AssertionError("must not execute")\n')
    with pytest.raises(ImportError, match="origin_mismatch"):
        finder.find_spec("owned", [str(hostile)])


def test_python_cli_keeps_code_separate_from_bootstrap() -> None:

    code = 'from __future__ import annotations\nprint("project code")'
    command, environment = _project_python_command(["-u", "-c", code])
    assert command[-3:] == ["-u", "-c", code]
    assert environment["SPECFACT_PROJECT_PYTHON"] == "1"
    assert environment["PYTHONPATH"] == "/opt/specfact/builtin/specfact_code_review/run"


def test_member_fallback_rejects_unrelated_analyzer_imports(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "needed.py").write_text("VALUE = 1\n")
    (tmp_path / "unrelated.py").write_text("VALUE = 2\n")
    monkeypatch.setattr(target_bootstrap, "ANALYZERS", tmp_path)
    finder = target_bootstrap.DomainFinder({"sealed_imports": ["needed"], "installed": []})
    assert finder.find_spec("needed") is not None
    assert finder.find_spec("unrelated") is None


@pytest.fixture(name="collision_runtime")
def collision_runtime_fixture(tmp_path: Path) -> dict[str, Path]:
    project = tmp_path / "project"
    installed = project / "site-packages"
    snapshot = tmp_path / "snapshot"
    analyzers = tmp_path / "analyzers"
    for directory in (installed, snapshot, analyzers):
        directory.mkdir(parents=True)
    (snapshot / "packaging.py").write_text('OWNER = "snapshot"\n')
    (analyzers / "packaging.py").write_text('OWNER = "analyzer"\n')
    (installed / "project_owned.py").write_text('OWNER = "project"\n')
    (analyzers / "project_owned.py").write_text('OWNER = "wrong-analyzer"\n')
    descriptor = {
        "project": {"source_roots": ["."]},
        "inventory": {
            "member_graphs": {
                "pylint": {
                    "sealed_imports": ["packaging"],
                    "installed": [
                        {"name": "packaging", "origin": "analyzer"},
                        {"name": "project-owned", "origin": "project"},
                    ],
                }
            }
        },
    }
    (project / "project-runtime.json").write_text(json.dumps(descriptor))
    return {"PROJECT": project, "SNAPSHOT": snapshot, "ANALYZERS": analyzers}


def _probe_dependency_origins(paths: dict[str, Path], module: str, preload: str) -> subprocess.CompletedProcess[str]:
    if preload == "pth":
        (paths["PROJECT"] / "site-packages/preload.pth").write_text("import packaging; import project_owned\n")
    script = f"""
import json, runpy, sys
from pathlib import Path
bootstrap = runpy.run_path({str(Path(target_bootstrap.__file__))!r})
configure = bootstrap['_configure_runtime']
configure.__globals__.update(
    PROJECT=Path({str(paths["PROJECT"])!r}),
    SNAPSHOT=Path({str(paths["SNAPSHOT"])!r}),
    ANALYZERS=Path({str(paths["ANALYZERS"])!r}),
)
if {preload!r} == 'before':
    sys.path.insert(0, {str(paths["SNAPSHOT"])!r})
    import packaging
    sys.path.pop(0)
configure({module!r})
preloaded = 'packaging' in sys.modules
import packaging, project_owned
print(json.dumps([packaging.OWNER, packaging.__file__, project_owned.OWNER, preloaded]))
"""
    return subprocess.run(
        [sys.executable, "-I", "-S", "-c", script], cwd=paths["SNAPSHOT"], capture_output=True, text=True, check=False
    )


@pytest.mark.parametrize(
    "module,preload,expected_owner,origin_root",
    [
        ("pylint", "none", "analyzer", "ANALYZERS"),
        ("pylint", "pth", "analyzer", "ANALYZERS"),
        ("project-python", "none", "snapshot", "SNAPSHOT"),
        ("project-python", "pth", "snapshot", "SNAPSHOT"),
        ("project-python", "before", "snapshot", "SNAPSHOT"),
    ],
)
def test_analyzer_dependency_origin_survives_snapshot_collision_and_pth_preload(
    collision_runtime: dict[str, Path], module: str, preload: str, expected_owner: str, origin_root: str
) -> None:
    completed = _probe_dependency_origins(collision_runtime, module, preload)
    assert completed.returncode == 0, completed.stderr
    owner, origin, project_owner, preloaded = json.loads(completed.stdout)
    assert owner == expected_owner
    assert origin == str(collision_runtime[origin_root] / "packaging.py")
    assert project_owner == "project"
    assert preloaded is (preload != "none")


def test_analyzer_rejects_dependency_loaded_before_bootstrap(collision_runtime: dict[str, Path]) -> None:
    completed = _probe_dependency_origins(collision_runtime, "pylint", "before")
    assert completed.returncode != 0
    assert "project_worker_analyzer_origin_mismatch:packaging" in completed.stderr


@pytest.mark.parametrize(
    "operation",
    [
        "sys.meta_path[:] = [entry for entry in sys.meta_path if not hasattr(entry, 'names')]",
        "next(entry for entry in sys.meta_path if hasattr(entry, 'names')).names.clear()",
        "next(entry for entry in sys.meta_path if hasattr(entry, 'names')).find_spec = lambda *args: None",
        "importlib.machinery.PathFinder.find_spec = lambda *args, **kwargs: None",
        "builtins.__import__ = lambda *args, **kwargs: None",
    ],
)
def test_executable_pth_cannot_change_protected_import_state(
    collision_runtime: dict[str, Path], operation: str
) -> None:
    pth = collision_runtime["PROJECT"] / "site-packages/changed-imports.pth"
    pth.write_text(f"import sys, importlib.machinery, builtins; {operation}\n")
    completed = _probe_dependency_origins(collision_runtime, "pylint", "none")
    assert completed.returncode != 0
    assert "project_worker_startup_import_state_changed" in completed.stderr


def _workspace_dependency(paths: dict[str, Path]) -> Path:
    (paths["PROJECT"] / "site-packages/project_owned.py").unlink()
    (paths["ANALYZERS"] / "project_owned.py").unlink()
    workspace = paths["SNAPSHOT"] / "workspace/member"
    workspace.mkdir(parents=True)
    (workspace / "project_owned.py").write_text('OWNER = "project"\n')
    return workspace


@pytest.mark.parametrize("placement", ["append", "prepend"])
def test_executable_editable_finder_remains_available_behind_sealed_imports(
    collision_runtime: dict[str, Path], placement: str
) -> None:
    workspace = _workspace_dependency(collision_runtime)
    installed = collision_runtime["PROJECT"] / "site-packages"
    hook = f"""
import importlib.machinery, sys
class EditableFinder:
    def find_spec(self, fullname, path=None, target=None):
        roots = {{'project_owned': {str(workspace)!r}, 'packaging': {str(collision_runtime["SNAPSHOT"])!r}}}
        if fullname in roots:
            return importlib.machinery.PathFinder.find_spec(fullname, [roots[fullname]])
def install():
    if {placement!r} == 'prepend':
        sys.meta_path.insert(0, EditableFinder())
    else:
        sys.meta_path.append(EditableFinder())
"""
    (installed / "editable_fixture.py").write_text(hook)
    (installed / "editable.pth").write_text("import editable_fixture; editable_fixture.install()\n")
    completed = _probe_dependency_origins(collision_runtime, "pylint", "none")
    assert completed.returncode == 0, completed.stderr
    owner, origin, project_owner, _ = json.loads(completed.stdout)
    assert owner == "analyzer"
    assert origin == str(collision_runtime["ANALYZERS"] / "packaging.py")
    assert project_owner == "project"


def test_path_only_pth_retains_rebased_workspace_import(collision_runtime: dict[str, Path]) -> None:
    workspace = _workspace_dependency(collision_runtime)
    pth = collision_runtime["PROJECT"] / "site-packages/workspace.pth"
    pth.write_text(str(workspace) + "\n")
    completed = _probe_dependency_origins(collision_runtime, "pylint", "none")
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)[2] == "project"


def test_executable_editable_namespace_path_hook_is_retained(collision_runtime: dict[str, Path]) -> None:
    workspace = _workspace_dependency(collision_runtime)
    installed = collision_runtime["PROJECT"] / "site-packages"
    hook = f"""
import importlib.machinery, sys
PLACEHOLDER = '__editable__.fixture.__path_hook__'
class EditablePathFinder:
    def find_spec(self, fullname, target=None):
        if fullname == 'project_owned':
            return importlib.machinery.PathFinder.find_spec(fullname, [{str(workspace)!r}])
def path_hook(path):
    if path == PLACEHOLDER:
        return EditablePathFinder()
    raise ImportError
def install():
    sys.path_hooks.append(path_hook)
    sys.path.append(PLACEHOLDER)
"""
    (installed / "editable_namespace.py").write_text(hook)
    (installed / "namespace.pth").write_text("import editable_namespace; editable_namespace.install()\n")
    completed = _probe_dependency_origins(collision_runtime, "pylint", "none")
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)[2] == "project"


def test_pth_paths_outside_runtime_roots_have_actionable_diagnostic(
    collision_runtime: dict[str, Path], tmp_path: Path
) -> None:
    outside = tmp_path / "outside-runtime"
    outside.mkdir()
    pth = collision_runtime["PROJECT"] / "site-packages/external.pth"
    pth.write_text(str(outside) + "\n")
    completed = _probe_dependency_origins(collision_runtime, "pylint", "none")
    assert completed.returncode != 0
    assert "project_worker_startup_path_escape" in completed.stderr
    assert "rebuild editable installs against the copied project" in completed.stderr


@pytest.mark.parametrize("form", ["module", "namespace", "symlink", "missing"])
def test_sealed_dependency_rejects_unverified_origins(tmp_path: Path, monkeypatch, form: str) -> None:
    analyzers = tmp_path / "analyzers"
    hostile = tmp_path / "hostile"
    analyzers.mkdir()
    hostile.mkdir()
    monkeypatch.setattr(target_bootstrap, "ANALYZERS", analyzers)
    if form == "namespace":
        (hostile / "needed").mkdir()
    elif form != "missing":
        (hostile / "needed.py").write_text("VALUE = 1\n")
    if form == "symlink":
        (analyzers / "needed.py").symlink_to(hostile / "needed.py")
    finder = target_bootstrap.DomainFinder({"sealed_imports": ["needed"], "installed": []})
    search = [str(analyzers)] if form in {"symlink", "missing"} else [str(hostile)]
    with pytest.raises(ImportError, match="project_worker_analyzer_origin_mismatch:needed"):
        finder.find_spec("needed", search)


def test_member_metadata_lookup_cannot_expand_explicit_target_inventory(tmp_path: Path, monkeypatch) -> None:

    metadata = tmp_path / "needed-1.0.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text("Metadata-Version: 2.1\nName: needed\nVersion: 1.0\n")
    monkeypatch.setattr(target_bootstrap, "ANALYZERS", tmp_path)
    finder = target_bootstrap.DomainFinder(
        {
            "sealed_imports": ["needed"],
            "installed": [{"name": "needed", "version": "1.0", "origin": "analyzer"}],
        }
    )
    context = DistributionFinder.Context(path=["/project-only"])
    assert not list(finder.find_distributions(context))
    default_context = DistributionFinder.Context(name="needed")
    assert [dist.version for dist in finder.find_distributions(default_context)] == ["1.0"]


def test_nested_python_domain_uses_namespace_identity(tmp_path: Path, monkeypatch) -> None:
    context = tmp_path / "context"
    monkeypatch.setattr(target_bootstrap, "CONTEXT", context)
    monkeypatch.setattr(target_bootstrap, "BUILTIN", Path(target_bootstrap.__file__).parents[2])
    context.symlink_to(Path(target_bootstrap.__file__))
    monkeypatch.setenv("SPECFACT_TARGET_PYTEST", "1")
    assert python_execution_domain() == "project-python"
    context.unlink()
    context.symlink_to(Path(target_bootstrap.__file__).with_name("target_pytest.py"))
    monkeypatch.delenv("SPECFACT_TARGET_PYTEST")
    assert python_execution_domain() == "pytest-observe"


@pytest.mark.parametrize(
    "arguments, option", [(["-I", "-c", "pass"], "-I"), (["-uS", "script"], "-S"), (["-E", "-m", "pytest"], "-E")]
)
def test_python_startup_cannot_bypass_runtime(arguments, option) -> None:
    with pytest.raises(RuntimeError, match=f"project_python_option_unsupported:{option}"):
        target_bootstrap._project_python_command(arguments)


def _write_pytest_runtime(project: Path, snapshot: Path, configuration: Path | None = None) -> dict[str, Path]:
    descriptor = {
        "project": discover_project(snapshot, config_path=configuration).document(),
        "inventory": {"member_graphs": {"pytest-observe": {"sealed_imports": [], "installed": []}}},
    }
    (project / "project-runtime.json").write_text(json.dumps(descriptor))
    return {"PROJECT": project, "SNAPSHOT": snapshot, "ANALYZERS": Path(pytest.__file__).parent.parent}


def _install_generated_package(project: Path) -> None:
    """Install a local wheel whose generated output differs from the raw sources."""
    wheel = project / "capsule_origin-1.0-py3-none-any.whl"
    files = {
        "capsule_origin/__init__.py": "from .generated import ORIGIN\n",
        "capsule_origin/generated.py": 'ORIGIN = "built"\n',
        "capsule_origin-1.0.dist-info/METADATA": "Metadata-Version: 2.1\nName: capsule-origin\nVersion: 1.0\n",
        "capsule_origin-1.0.dist-info/WHEEL": (
            "Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
        ),
    }
    record = "capsule_origin-1.0.dist-info/RECORD"
    files[record] = "".join(f"{name},,\n" for name in [*files, record])
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-deps",
            "--disable-pip-version-check",
            "--target",
            str(project / "site-packages"),
            str(wheel),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def _run_origin_pytest(
    paths: dict[str, Path], *, capsule: bool, import_mode: str, selection: str = "tests/test_origin.py"
) -> subprocess.CompletedProcess[str]:
    native_setup = f"""
import site
site.addsitedir({str(paths["PROJECT"] / "site-packages")!r})
site.addsitedir({str(paths["ANALYZERS"])!r})
"""
    capsule_setup = f"""
bootstrap = runpy.run_path({str(Path(target_bootstrap.__file__))!r})
configure = bootstrap['_configure_runtime']
configure.__globals__.update({", ".join(f"{key}=Path({str(value)!r})" for key, value in paths.items())})
configure('pytest-observe')
"""
    script = f"""
import runpy, sys
from pathlib import Path
{capsule_setup if capsule else native_setup}
import pytest
raise SystemExit(pytest.main(['-q', '--import-mode={import_mode}', {selection!r}]))
"""
    return subprocess.run(
        [sys.executable, "-I", "-S", "-c", script],
        cwd=paths["SNAPSHOT"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
    )


@pytest.mark.parametrize("import_mode", ["prepend", "importlib"])
@pytest.mark.parametrize("paths_mode", ["undeclared", "empty", "pytest", "explicit", "editable"])
def test_target_pytest_preserves_built_or_explicit_source_imports(
    tmp_path: Path, paths_mode: str, import_mode: str
) -> None:
    project, snapshot = tmp_path / "runtime", tmp_path / "snapshot"
    project.mkdir()
    source = snapshot / "src with spaces" if paths_mode == "pytest" else snapshot / "src"
    package = source / "capsule_origin"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('ORIGIN = "raw"\n')
    (snapshot / "tests").mkdir()
    _install_generated_package(project)
    expected = "raw" if paths_mode in {"pytest", "explicit", "editable"} else "built"
    (snapshot / "tests/test_origin.py").write_text(
        f"import capsule_origin\ndef test_origin():\n    assert capsule_origin.ORIGIN == {expected!r}\n"
    )
    configuration = None
    if paths_mode == "pytest":
        (snapshot / "pytest.ini").write_text('[pytest]\npythonpath = "src with spaces"\n')
    if paths_mode == "empty":
        (snapshot / "pytest.ini").write_text("[pytest]\npythonpath =\n")
    if paths_mode == "explicit":
        configuration = snapshot / "review.toml"
        configuration.write_text('source_roots = ["src"]\n')
    if paths_mode == "editable":
        # The selected environment's ordinary .pth editable mapping owns this path.
        (project / "site-packages/capsule-editable.pth").write_text(str(source) + "\n")
        # A real editable installation supplies source instead of the built package.
        shutil.rmtree(project / "site-packages/capsule_origin")
    paths = _write_pytest_runtime(project, snapshot, configuration)
    if paths_mode != "explicit":
        native = _run_origin_pytest(paths, capsule=False, import_mode=import_mode)
        assert native.returncode == 0, native.stdout + native.stderr
    observed = _run_origin_pytest(paths, capsule=True, import_mode=import_mode)
    assert observed.returncode == 0, observed.stdout + observed.stderr


@pytest.mark.parametrize("pytest_child", [False, True])
@pytest.mark.parametrize("invocation", ["code", "module", "script"])
def test_native_python_path_zero_survives_runtime_startup(tmp_path: Path, pytest_child: bool, invocation: str) -> None:
    project, snapshot = tmp_path / "runtime", tmp_path / "snapshot"
    (project / "site-packages").mkdir(parents=True)
    snapshot.mkdir()
    source = snapshot / "tools" if invocation == "script" else snapshot
    source.mkdir(exist_ok=True)
    (source / "flat_module.py").write_text('VALUE = "native-path-zero"\n')
    probe = "import flat_module\nprint(flat_module.VALUE)\n"
    (source / "probe.py").write_text(probe)
    _write_pytest_runtime(project, snapshot)
    startup = tmp_path / "startup"
    startup.mkdir()
    context = tmp_path / "python-context"
    token = "target_pytest.py" if pytest_child else "target_bootstrap.py"
    context.symlink_to(Path(target_bootstrap.__file__).with_name(token))
    (startup / "sitecustomize.py").write_text(f"""
import runpy
from pathlib import Path
bootstrap = runpy.run_path({str(Path(target_bootstrap.__file__))!r})
configure = bootstrap['_configure_runtime']
configure.__globals__.update(PROJECT=Path({str(project)!r}), SNAPSHOT=Path({str(snapshot)!r}),
    CONTEXT=Path({str(context)!r}), BUILTIN=Path({str(Path(target_bootstrap.__file__).parents[2])!r}),
    ANALYZERS=Path({str(Path(pytest.__file__).parent.parent)!r}))
configure(bootstrap['python_execution_domain']())
""")
    arguments = {"code": ["-c", probe], "module": ["-m", "probe"], "script": [str(source / "probe.py")]}[invocation]
    environment = {**os.environ, "SPECFACT_TARGET_PYTEST": "1" if pytest_child else "0"}
    environment.pop("PYTHONPATH", None)
    command = [sys.executable, "-s", *arguments]
    native = subprocess.run(command, cwd=snapshot, env=environment, capture_output=True, text=True, check=False)
    environment["PYTHONPATH"] = str(startup)
    attached = subprocess.run(command, cwd=snapshot, env=environment, capture_output=True, text=True, check=False)
    assert native.returncode == attached.returncode == 0, attached.stderr
    assert native.stdout == attached.stdout == "native-path-zero\n"
    assert not attached.stderr


def test_native_pytest_adds_flat_test_module_root_without_runtime_override(tmp_path: Path) -> None:
    project, snapshot = tmp_path / "runtime", tmp_path / "snapshot"
    (project / "site-packages").mkdir(parents=True)
    snapshot.mkdir()
    (snapshot / "flat_module.py").write_text("VALUE = 42\n")
    (snapshot / "test_flat.py").write_text("import flat_module\ndef test_flat():\n    assert flat_module.VALUE == 42\n")
    paths = _write_pytest_runtime(project, snapshot)
    for capsule in (False, True):
        result = _run_origin_pytest(paths, capsule=capsule, import_mode="prepend", selection="test_flat.py")
        assert result.returncode == 0, result.stdout + result.stderr


def _probe_member_dispatch(paths: dict[str, Path], module: str, operation: str) -> subprocess.CompletedProcess[str]:
    builtin = paths["SNAPSHOT"] / "builtin"
    observer = builtin / "specfact_code_review/run/target_pytest.py"
    observer.parent.mkdir(parents=True)
    observer.write_text('print("VERIFIED_DISPATCH")\n')
    observer.with_name("target_pylint.py").write_text("import pylint\n")
    (paths["ANALYZERS"] / "pylint.py").write_text('print("VERIFIED_DISPATCH")\n')
    (paths["SNAPSHOT"] / "counterfeit.py").write_text('print("COUNTERFEIT_DISPATCH")\n')
    descriptor_path = paths["PROJECT"] / "project-runtime.json"
    descriptor = json.loads(descriptor_path.read_text())
    descriptor["inventory"]["member_graphs"]["pytest-observe"] = {"sealed_imports": [], "installed": []}
    descriptor_path.write_text(json.dumps(descriptor))
    (paths["PROJECT"] / "site-packages/dispatch.pth").write_text(
        f"import sys, runpy, pkgutil, io, builtins, importlib.util; {operation}\n"
    )
    script = f"""
import runpy, sys
from pathlib import Path
bootstrap = runpy.run_path({str(Path(target_bootstrap.__file__))!r})
bootstrap['main'].__globals__.update({", ".join(f"{key}=Path({str(value)!r})" for key, value in paths.items())},
    BUILTIN=Path({str(builtin)!r}))
sys.argv[:] = ['target_bootstrap.py', {module!r}]
bootstrap['main']()
"""
    return subprocess.run(
        [sys.executable, "-I", "-S", "-c", script], cwd=paths["SNAPSHOT"], capture_output=True, text=True, check=False
    )


@pytest.mark.parametrize(
    "module,operation",
    [
        ("pylint", "runpy.run_module = lambda *a, **k: print('COUNTERFEIT_DISPATCH')"),
        ("pytest-observe", "runpy.run_path = lambda *a, **k: print('COUNTERFEIT_DISPATCH')"),
        ("pylint", "runpy._run_code = lambda *a, **k: print('COUNTERFEIT_DISPATCH')"),
        ("pylint", "runpy._run_code.__globals__['exec'] = lambda *a, **k: print('COUNTERFEIT_DISPATCH')"),
        ("pylint", "runpy._TempModule.__enter__ = lambda *a: None"),
        ("pylint", "runpy.run_module.__code__ = (lambda *a, **k: print('COUNTERFEIT_DISPATCH')).__code__"),
        ("pylint", "runpy._run_code.__code__ = (lambda *a, **k: print('COUNTERFEIT_DISPATCH')).__code__"),
        (
            "pytest-observe",
            "runpy._get_code_from_file = lambda *a: compile('print(\"COUNTERFEIT_DISPATCH\")', '<fake>', 'exec')",
        ),
        (
            "pytest-observe",
            "pkgutil.read_code = lambda *a: compile('print(\"COUNTERFEIT_DISPATCH\")', '<fake>', 'exec')",
        ),
        ("pytest-observe", "io.open_code = lambda *a: io.BytesIO(b'print(\"COUNTERFEIT_DISPATCH\")')"),
        (
            "pylint",
            "importlib.util.find_spec = lambda name: importlib.util.spec_from_file_location(name, 'counterfeit.py')",
        ),
        (
            "pylint",
            "importlib.machinery.SourceFileLoader.get_code = lambda *a: "
            "compile('print(\"COUNTERFEIT_DISPATCH\")', '<fake>', 'exec')",
        ),
        ("pylint", "builtins.exec = lambda *a, **k: print('COUNTERFEIT_DISPATCH')"),
        (
            "pytest-observe",
            "next(entry for entry in sys.meta_path if hasattr(entry, 'names'))"
            ".find_spec.__func__.__globals__['BUILTIN'] = __import__('pathlib').Path('unverified')",
        ),
    ],
)
def test_executable_pth_cannot_substitute_analyzer_dispatch(
    collision_runtime: dict[str, Path], module: str, operation: str
) -> None:
    completed = _probe_member_dispatch(collision_runtime, module, operation)
    assert completed.returncode != 0, completed.stdout
    assert "project_worker_startup_import_state_changed" in completed.stderr
    assert "VERIFIED_DISPATCH" not in completed.stdout


@pytest.mark.parametrize("module", ["pylint", "pytest-observe"])
def test_additive_startup_hooks_preserve_verified_member_dispatch(
    collision_runtime: dict[str, Path], module: str
) -> None:
    editable = collision_runtime["SNAPSHOT"] / "editable"
    editable.mkdir()
    completed = _probe_member_dispatch(collision_runtime, module, f"sys.path.append({str(editable)!r})")
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == "VERIFIED_DISPATCH\n"


@pytest.mark.parametrize("module", ["pylint", "pytest-observe"])
def test_startup_rejection_has_distinct_exit_despite_analyzer_shaped_stdout(
    collision_runtime: dict[str, Path], module: str
) -> None:
    completed = _probe_member_dispatch(collision_runtime, module, "print('[]'); runpy._run_code = lambda *a, **k: None")
    assert completed.returncode == 78
    assert completed.stdout == "[]\n"
    assert "project_worker_startup_import_state_changed" in completed.stderr


def test_preloaded_analyzer_origin_failure_uses_startup_exit(collision_runtime: dict[str, Path]) -> None:
    operation = (
        "spec = importlib.util.spec_from_file_location('packaging', 'packaging.py'); "
        "module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); "
        "sys.modules['packaging'] = module; print('[]')"
    )
    completed = _probe_member_dispatch(collision_runtime, "pylint", operation)
    assert completed.returncode == 78
    assert completed.stdout == "[]\n"
    assert "project_worker_analyzer_origin_mismatch:packaging" in completed.stderr


@pytest.mark.parametrize("owner", ["SourceFileLoader", "SourceFileLoader.__mro__[1]"])
def test_loader_filename_substitution_cannot_redirect_verified_dispatch(
    collision_runtime: dict[str, Path], owner: str
) -> None:
    operation = f"importlib.machinery.{owner}.get_filename = lambda self, fullname=None: 'counterfeit.py'"
    completed = _probe_member_dispatch(collision_runtime, "pylint", operation)
    assert completed.returncode == 78, completed.stdout + completed.stderr
    assert "project_worker_startup_import_state_changed" in completed.stderr
    assert "VERIFIED_DISPATCH" not in completed.stdout
    assert "COUNTERFEIT_DISPATCH" not in completed.stdout
