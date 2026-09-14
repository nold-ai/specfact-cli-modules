"""Analyzer entry-point lookup rejects project-owned replacements."""

import json
import subprocess
import sys
from importlib.metadata import DistributionFinder
from pathlib import Path

import pytest

from specfact_code_review.run import target_bootstrap
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
    return subprocess.run([sys.executable, "-I", "-S", "-c", script], capture_output=True, text=True, check=False)


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


def test_only_pytest_children_receive_the_pytest_dependency_domain(monkeypatch) -> None:

    monkeypatch.delenv("SPECFACT_TARGET_PYTEST", raising=False)
    assert python_execution_domain() == "project-python"
    monkeypatch.setenv("SPECFACT_TARGET_PYTEST", "1")
    assert python_execution_domain() == "pytest-observe"


@pytest.mark.parametrize(
    "arguments, option", [(["-I", "-c", "pass"], "-I"), (["-uS", "script"], "-S"), (["-E", "-m", "pytest"], "-E")]
)
def test_python_startup_cannot_bypass_runtime(arguments, option) -> None:
    with pytest.raises(RuntimeError, match=f"project_python_option_unsupported:{option}"):
        target_bootstrap._project_python_command(arguments)
