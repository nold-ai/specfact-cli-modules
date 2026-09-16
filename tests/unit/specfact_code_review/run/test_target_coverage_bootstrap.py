"""Reviewer coverage helpers stay confined to the authenticated pytest domain."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import cast

import pytest

from specfact_code_review.run import runtime_builder, target_bootstrap
from specfact_code_review.run.runtime_models import ProjectPlan, ProjectRuntimeError
from specfact_code_review.run.target_bootstrap import _load_pytest_coverage


@pytest.fixture(name="coverage_runtime")
def coverage_runtime_fixture(tmp_path: Path) -> dict[str, Path]:
    roots = {
        "PROJECT": tmp_path / "project",
        "SNAPSHOT": tmp_path / "snapshot",
        "ANALYZERS": tmp_path / "analyzers",
        "BUILTIN": tmp_path / "builtin",
        "CONTEXT": tmp_path / "context",
    }
    for name, path in roots.items():
        if name != "CONTEXT":
            path.mkdir()
    (roots["PROJECT"] / "site-packages").mkdir()
    descriptor = {
        "project": {"source_roots": ["."]},
        "inventory": {"member_graphs": {"pytest-observe": {"sealed_imports": [], "installed": []}}},
    }
    (roots["PROJECT"] / "project-runtime.json").write_text(json.dumps(descriptor))
    helpers = roots["BUILTIN"] / "specfact_code_review/run"
    helpers.mkdir(parents=True)
    source = Path(target_bootstrap.__file__).parent
    for name in ("target_bootstrap.py", "target_launch.py", "sitecustomize.py"):
        text = (source / name).read_text()
        for variable, path in roots.items():
            if name == "target_bootstrap.py":
                original = getattr(target_bootstrap, variable)
                text = text.replace(f'{variable} = Path("{original}")', f"{variable} = Path({str(path)!r})")
        (helpers / name).write_text(text)
    (helpers / "target_coverage.py").write_text('OWNER = "verified-builtin"\n')
    (helpers / "target_pytest.py").write_text("import _specfact_target_coverage as collector\nprint(collector.OWNER)\n")
    os.link(helpers / "target_pytest.py", roots["CONTEXT"])
    (roots["SNAPSHOT"] / "_specfact_target_coverage.py").write_text('OWNER = "customer-collision"\n')
    roots["HELPERS"] = helpers
    return roots


def _probe(roots: dict[str, Path], script: str) -> subprocess.CompletedProcess[str]:
    bootstrap = roots["HELPERS"] / "target_bootstrap.py"
    prefix = f"import runpy,sys; from pathlib import Path; b=runpy.run_path({str(bootstrap)!r}); "
    return subprocess.run(
        [sys.executable, "-I", "-S", "-c", prefix + script],
        cwd=roots["SNAPSHOT"],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )


@pytest.mark.parametrize("route", ["first", "nested"])
def test_pytest_domain_loads_fixed_helper_in_actual_startup_routes(coverage_runtime, route):
    if route == "first":
        script = "sys.argv=['bootstrap','pytest-observe']; b['main']()"
    else:
        script = (
            "import os;os.environ['SPECFACT_PROJECT_PYTHON']='1';"
            f"runpy.run_path({str(coverage_runtime['HELPERS'] / 'sitecustomize.py')!r});"
            "import _specfact_target_coverage as collector; print(collector.OWNER)"
        )
    result = _probe(coverage_runtime, script)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "verified-builtin"


@pytest.mark.parametrize(
    "script, expected",
    [
        pytest.param(
            "b['_configure_runtime']('project-python'); print('_specfact_target_coverage' in sys.modules)",
            "False",
            id="project-python-does-not-load-collector",
        ),
        pytest.param(
            "load=b['_load_pytest_coverage']; print(load() is load())",
            "True",
            id="owned-collector-object-is-reused",
        ),
    ],
)
def test_coverage_helper_respects_domain_and_owned_object_lifecycle(coverage_runtime, script, expected):
    result = _probe(coverage_runtime, script)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected


@pytest.mark.parametrize("forged_origin", ["different", "same"])
def test_preloaded_coverage_alias_cannot_claim_builtin_ownership(coverage_runtime, forged_origin):
    path = (
        coverage_runtime["HELPERS"] / "target_coverage.py"
        if forged_origin == "same"
        else Path("/customer/collector.py")
    )
    script = (
        "import types,importlib.util; alias='_specfact_target_coverage'; fake=types.ModuleType(alias);"
        f"fake.__file__={str(path)!r};fake.__spec__=importlib.util.spec_from_file_location(alias,{str(path)!r});"
        "sys.modules[alias]=fake; b['_load_pytest_coverage']()"
    )
    result = _probe(coverage_runtime, script)
    assert result.returncode != 0
    assert "project_pytest_coverage_helper_origin_mismatch" in result.stderr


def test_failed_helper_load_does_not_leave_authenticated_alias(coverage_runtime):
    (coverage_runtime["HELPERS"] / "target_coverage.py").write_text("raise RuntimeError('fixture failure')\n")
    script = (
        "\ntry:\n b['_load_pytest_coverage']()\nexcept RuntimeError:\n"
        " print('_specfact_target_coverage' in sys.modules)\n"
    )
    result = _probe(coverage_runtime, script)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"


def test_changed_collector_bytes_invalidate_runtime_cache(tmp_path, monkeypatch):
    helpers = tmp_path / "helpers"
    helpers.mkdir()
    for path in Path(runtime_builder.__file__).parent.glob("*.py"):
        (helpers / path.name).write_bytes(path.read_bytes())
    helper = helpers / "target_coverage.py"
    helper.write_text("POLICY = 1\n")
    lock = Path("resources/contracts/pr-range-v1-toolchain-lock.json")
    (tmp_path / lock).parent.mkdir(parents=True)
    (tmp_path / lock).write_bytes((Path(runtime_builder.__file__).parents[1] / lock).read_bytes())
    monkeypatch.setattr(runtime_builder, "__file__", str(helpers / "runtime_builder.py"))
    monkeypatch.setattr(runtime_builder, "capture_public_trust", lambda _root: b"fixture trust")
    monkeypatch.setattr(runtime_builder, "git_identity", lambda: "fixed-git")
    plan = ProjectPlan(tmp_path, manager="pip")
    worker = SimpleNamespace(environment_id="linux-x86_64-cp312", identity="sha256:" + "a" * 64)
    identities = []
    digest = runtime_builder.document_digest

    def record_identity(value):
        identities.append(value)
        return digest(value)

    monkeypatch.setattr(runtime_builder, "document_digest", record_identity)
    for content in ("POLICY = 1\n", "POLICY = 2\n"):
        helper.write_text(content)
        with pytest.raises(ProjectRuntimeError, match="offline_cache_miss"):
            runtime_builder.prepare_runtime(plan, runtime=worker, cache_root=tmp_path / "cache", offline=True)
    assert digest(identities[0]) != digest(identities[1])
    assert identities[1]["builder"]["target_coverage.py"] == runtime_builder.content_digest(helper.read_bytes())


@pytest.fixture(name="owned_helper")
def owned_helper_fixture(tmp_path, monkeypatch):
    """Run the production loader with a contained fixture, restoring process state."""
    helper = tmp_path / "target_coverage.py"
    helper.write_text('ORIGIN = "owned-fixture"\n')
    alias = "_specfact_target_coverage"
    missing = object()
    previous = sys.modules.pop(alias, missing)
    monkeypatch.setattr(target_bootstrap, "__file__", str(tmp_path / "target_bootstrap.py"))
    monkeypatch.setattr(target_bootstrap, "_OWNED_COVERAGE_MODULES", {})
    try:
        yield helper
    finally:
        sys.modules.pop(alias, None)
        if previous is not missing:
            sys.modules[alias] = cast(ModuleType, previous)


def test_production_loader_retains_actual_owned_module(owned_helper):
    loaded = _load_pytest_coverage()
    assert loaded.ORIGIN == "owned-fixture"
    assert loaded.__file__ == str(owned_helper)
    assert loaded.__spec__ is not None
    assert loaded.__spec__.origin == str(owned_helper)
    assert _load_pytest_coverage() is loaded
    assert sys.modules["_specfact_target_coverage"] is loaded


@pytest.mark.parametrize("same_origin", [False, True])
def test_production_loader_rejects_unowned_cached_module(owned_helper, same_origin):
    alias = "_specfact_target_coverage"
    origin = owned_helper if same_origin else owned_helper.with_name("customer.py")
    forged = ModuleType(alias)
    forged.__file__ = str(origin)
    forged.__spec__ = importlib.util.spec_from_file_location(alias, origin)
    sys.modules[alias] = forged
    with pytest.raises(ImportError, match="coverage_helper_origin_mismatch"):
        _load_pytest_coverage()
    assert sys.modules[alias] is forged


@pytest.mark.parametrize("kind", ["missing", "symlink"])
def test_production_loader_requires_regular_contained_helper(owned_helper, kind):
    owned_helper.unlink()
    if kind == "symlink":
        alternate = owned_helper.with_name("alternate.py")
        alternate.write_text("raise AssertionError('must not execute')\n")
        owned_helper.symlink_to(alternate)
    with pytest.raises(ImportError, match="coverage_helper_unavailable"):
        _load_pytest_coverage()
    assert "_specfact_target_coverage" not in sys.modules


def test_production_loader_removes_its_failed_module(owned_helper):
    owned_helper.write_text("raise RuntimeError('fixture execution failed')\n")
    with pytest.raises(RuntimeError, match="fixture execution failed"):
        _load_pytest_coverage()
    assert "_specfact_target_coverage" not in sys.modules


@pytest.mark.parametrize("field", ["__file__", "__spec__"])
def test_production_loader_rejects_owned_origin_drift(owned_helper, field):
    loaded = _load_pytest_coverage()
    if field == "__file__":
        loaded.__file__ = str(owned_helper.with_name("other.py"))
    else:
        loaded.__spec__ = None
    with pytest.raises(ImportError, match="coverage_helper_origin_mismatch"):
        _load_pytest_coverage()
