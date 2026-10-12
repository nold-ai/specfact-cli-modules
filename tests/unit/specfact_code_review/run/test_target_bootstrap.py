"""Analyzer entry-point lookup rejects project-owned replacements."""

import importlib
import importlib.machinery
import importlib.util
import os
import shutil
import subprocess
import sys
from importlib.metadata import DistributionFinder
from pathlib import Path

import pytest
import six as six_source

from specfact_code_review.run import target_bootstrap
from specfact_code_review.run.target_bootstrap import _project_python_command, python_execution_domain
from tests.host.proof_capsule_review_projection_shell import _write_pytest_runtime


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


@pytest.fixture(name="owned_six")
def owned_six_fixture(tmp_path: Path, monkeypatch):
    root = tmp_path / "analyzers"
    root.mkdir()
    shutil.copyfile(six_source.__file__, root / "six.py")
    monkeypatch.setattr(sys, "meta_path", list(sys.meta_path))
    original_names = {name for name in sys.modules if name == "six" or name.startswith("six.")}
    for name in original_names:
        monkeypatch.delitem(sys.modules, name)
    spec = importlib.util.spec_from_file_location("six", root / "six.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "six", module)
    spec.loader.exec_module(module)
    try:
        yield root, module
    finally:
        for name in tuple(sys.modules):
            if (name == "six" or name.startswith("six.")) and name not in original_names:
                sys.modules.pop(name, None)


@pytest.mark.parametrize("cached", [False, True])
def test_verified_analyzer_resolves_real_registered_six_namespace(owned_six, monkeypatch, cached):
    root, six = owned_six
    finder = target_bootstrap.AnalyzerFinder({"six"}, analyzer_root=root)
    if cached:
        moved = importlib.import_module("six.moves")
        assert moved.xrange is range
        finder.validate_loaded()
    else:
        monkeypatch.setattr(sys, "meta_path", [finder, *sys.meta_path])
        spec = finder.find_spec("six.moves")
        assert spec is not None
        assert spec.name == "six.moves" and spec.loader is vars(six)["_importer"] and spec.origin is None
        moved = importlib.import_module("six.moves")
        assert moved.xrange is range
        finder.validate_loaded()


@pytest.mark.parametrize("name", ["six.moves", "six.moves.unregistered", "unrelated.virtual"])
def test_verified_virtual_namespace_rejects_foreign_loader_or_unknown_name(owned_six, name, monkeypatch):
    root, _six = owned_six
    loader = importlib.machinery.SourceFileLoader(name, str(root / "foreign.py"))
    spec = importlib.machinery.ModuleSpec(name, loader)
    module = type(sys)(name)
    module.__spec__ = spec
    monkeypatch.setitem(sys.modules, name, module)
    finder = target_bootstrap.AnalyzerFinder({name.partition(".")[0]}, analyzer_root=root)
    with pytest.raises(ImportError, match="project_worker_analyzer_origin_mismatch"):
        finder.validate_loaded()


def test_verified_virtual_namespace_rejects_parent_file_substitution(owned_six, monkeypatch, tmp_path):
    root, six = owned_six
    monkeypatch.setattr(six, "__file__", str(tmp_path / "foreign-six.py"))
    finder = target_bootstrap.AnalyzerFinder({"six"}, analyzer_root=root)
    with pytest.raises(ImportError, match="project_worker_analyzer_origin_mismatch"):
        finder.find_spec("six.moves")


@pytest.mark.parametrize(
    "operation",
    [
        "p._SixMetaPathImporter = type('Fake', (), {'__module__': 'six'}); p._importer = p._SixMetaPathImporter()",
        "p._importer.find_spec.__func__.__code__ = (lambda *args: None).__code__",
        "p._importer.known_modules['six.moves'] = type(sys)('six.moves')",
        "p.spec_from_loader = lambda *args: None",
        "p._importer.known_modules = dict(p._importer.known_modules)",
    ],
)
def test_real_startup_cannot_substitute_owned_registered_importer(owned_six, monkeypatch, tmp_path, operation):
    root, _six = owned_six
    project = tmp_path / "project"
    (project / "site-packages").mkdir(parents=True)
    monkeypatch.setattr(target_bootstrap, "PROJECT", project)
    monkeypatch.setattr(target_bootstrap, "ANALYZERS", root)
    stdlib = target_bootstrap._stdlib_paths()
    monkeypatch.setattr(sys, "path", stdlib)
    finder = target_bootstrap.AnalyzerFinder({"six"}, analyzer_root=root)
    monkeypatch.setattr(sys, "meta_path", [finder, *sys.meta_path])
    (project / "site-packages/substitute.pth").write_text(
        "import sys; p = sys.modules['six']; " + operation + "\n", encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="project_worker_startup_import_state_changed"):
        target_bootstrap._configure_member_site(finder, stdlib)


def test_real_startup_retains_verified_registered_lazy_import(owned_six, monkeypatch, tmp_path):
    root, _six = owned_six
    project = tmp_path / "project"
    (project / "site-packages").mkdir(parents=True)
    monkeypatch.setattr(target_bootstrap, "PROJECT", project)
    monkeypatch.setattr(target_bootstrap, "ANALYZERS", root)
    stdlib = target_bootstrap._stdlib_paths()
    monkeypatch.setattr(sys, "path", stdlib)
    finder = target_bootstrap.AnalyzerFinder({"six"}, analyzer_root=root)
    monkeypatch.setattr(sys, "meta_path", [finder, *sys.meta_path])
    (project / "site-packages/valid.pth").write_text(
        "import six.moves; assert six.moves.xrange is range\n", encoding="utf-8"
    )
    target_bootstrap._configure_member_site(finder, stdlib)
    finder.validate_loaded()
