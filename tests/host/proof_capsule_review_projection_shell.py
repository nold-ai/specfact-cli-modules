"""Required controller shell and standalone bootstrap proofs; never run inside the sealed portable runtime."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
import yaml

from specfact_code_review.run import target_bootstrap
from specfact_code_review.run.runtime_discovery import discover_project
from tests.host.proof_capsule_deferred_review_ci import _git, _prepare_committed_ci_subject
from tests.support.capsule_review_fixtures import REPO_ROOT, STEP_NAME, public_projector
from tests.unit.test_capsule_review_projection import _write_preparation_fixture


def _write_preparation_interpreter(tmp_path):

    interpreter = tmp_path / "venv/bin/python"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text(
        "#!" + sys.executable + "\n"
        "import os,sys\nfrom pathlib import Path\n"
        "if sys.argv[1:3] == ['-I','-c']:\n"
        "    if os.environ['REPORT_CASE'] == 'missing':\n"
        "        Path('commit-review-preparation.private.json').unlink()\n"
        "    else: print(Path('controlled-report.json').read_text())\n"
        "    raise SystemExit(int(os.environ['PREPARATION_EXIT']))\n"
        "os.execv(sys.executable, [sys.executable, *sys.argv[1:]])\n"
    )
    interpreter.chmod(0o700)


@pytest.fixture(name="preparation_shell")
def preparation_shell_fixture(tmp_path, monkeypatch):

    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    step = next(item for item in workflow["jobs"]["customer"]["steps"] if item.get("name") == STEP_NAME)
    recipe = "# Provisioning" + step["run"].split("# Provisioning", 1)[1].split("review_exit=0", 1)[0]
    _write_preparation_interpreter(tmp_path)

    def invoke(preparation):
        preparation_exit, report_case = preparation
        report = _write_preparation_fixture(tmp_path, "prepared" if report_case == "missing" else report_case)
        (tmp_path / "controlled-report.json").write_text(report.read_text())
        for name, value in {
            "CUSTOMER_ROOT": str(tmp_path),
            "GITHUB_WORKSPACE": str(tmp_path),
            "PROJECT_CONFIG": str(tmp_path / "project.toml"),
            "PREPARATION_EXIT": str(preparation_exit),
            "REPORT_CASE": report_case,
        }.items():
            monkeypatch.setenv(name, value)
        return subprocess.run(
            ["bash", "-c", "set -euo pipefail\n" + recipe + "printf 'REVIEW_STARTED\\n'"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

    return invoke


@pytest.mark.parametrize(
    "preparation,expected",
    [
        ((0, "prepared"), (0, "PREPARED", "prepared")),
        ((0, "not_applicable"), (0, "NOT_APPLICABLE", "not_applicable")),
        ((7, "not_applicable"), (7, "INCOMPLETE", "preparation_command_failed")),
        ((0, "not_applicable_reason"), (1, "INCOMPLETE", "invalid_not_applicable")),
        ((7, "prepared"), (7, "INCOMPLETE", "preparation_command_failed")),
        ((0, "invalid"), (1, "INCOMPLETE", "invalid_json")),
        ((7, "invalid"), (7, "INCOMPLETE", "invalid_json")),
        ((0, "missing"), (1, "INCOMPLETE", "unreadable_report")),
        ((7, "missing"), (7, "INCOMPLETE", "unreadable_report")),
    ],
)
def test_preparation_shell_preserves_failure_and_projects_incomplete(preparation_shell, preparation, expected):

    expected_exit, expected_status, expected_outcome = expected
    accepted = expected_status in {"PREPARED", "NOT_APPLICABLE"}
    result = preparation_shell(preparation)
    assert result.returncode == expected_exit
    lines = result.stdout.splitlines()
    assert lines, "every preparation exit must produce bounded diagnosis"
    projection = json.loads(lines[0])
    assert projection["status"] == expected_status
    assert ("REVIEW_STARTED" in lines) is accepted
    assert "private" not in result.stdout + result.stderr
    assert projection["report_outcome"] == expected_outcome


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize("review_exit", [17, 124])
def test_projector_crash_preserves_original_review_exit(tmp_path: Path, job_name, review_exit):
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    name = STEP_NAME if job_name == "customer" else "Prepare and review through the authenticated installed controller"
    recipe = next(step["run"] for step in workflow["jobs"][job_name]["steps"] if step.get("name") == name)
    invocation = next(line for line in recipe.splitlines() if "REVIEW_PUBLIC_EXIT=" in line and "<<'PY'" in line)
    guard = invocation.split("<<'PY'", 1)[1]
    report = tmp_path / ".specfact/code-review.json"
    report.parent.mkdir()
    report.write_text('{"analyzer_evidence":42}')
    program = public_projector(job_name)
    shell = (
        f"set -e\nreview_exit={review_exit}\n"
        f"REVIEW_PUBLIC_EXIT=$review_exit {shlex.quote(sys.executable)} - <<'PY'{guard}\n"
        + program
        + '\nPY\nexit "$review_exit"\n'
    )
    result = subprocess.run(
        ["bash", "-c", shell],
        cwd=tmp_path,
        env=dict(os.environ, CUSTOMER_ROOT=str(tmp_path), TRUSTED_ROOT=str(tmp_path)),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == review_exit, "Diagnostics must preserve the original failed review result"
    assert result.stderr == "", "Projector tracebacks must remain private"
    assert json.loads(result.stdout.splitlines()[-1]) == {
        "status": "INCOMPLETE",
        "phase": "review",
        "diagnostic": "review_projection_failed",
    }
    assert "TypeError" in (tmp_path / "review-projection.private.log").read_text()


@pytest.mark.parametrize("review_exit", [17, 124])
def test_candidate_secondary_projector_crash_preserves_review_exit(tmp_path: Path, review_exit):
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    recipe = next(step["run"] for step in workflow["jobs"]["customer"]["steps"] if step.get("name") == STEP_NAME)
    marker = "<<'PY_CANDIDATE_FAILURE'"
    invocation = next(line for line in recipe.splitlines() if marker in line)
    guard = invocation.split(marker, 1)[1]
    program = recipe.split(marker, 1)[1].split("\n", 1)[1].split("\nPY_CANDIDATE_FAILURE", 1)[0]
    shell = (
        f"set -e\nreview_exit={review_exit}\n{shlex.quote(sys.executable)} - {marker}{guard}\n"
        + "raise SystemExit(3)\n"
        + program
        + '\nPY_CANDIDATE_FAILURE\nexit "$review_exit"\n'
    )
    result = subprocess.run(
        ["bash", "-c", shell],
        cwd=tmp_path,
        env=dict(os.environ, CUSTOMER_ROOT=str(tmp_path)),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == review_exit, "Every diagnostic invocation must preserve the failed review result"
    assert result.stderr == ""
    assert json.loads(result.stdout) == {
        "status": "INCOMPLETE",
        "phase": "review",
        "diagnostic": "review_projection_failed",
    }


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize("module_name", ["ast", "json"])
@pytest.mark.parametrize("import_origin", ["checkout", "pythonpath"])
@pytest.mark.parametrize("review_exit", [17, 124])
def test_actual_projector_launch_excludes_untrusted_imports(
    tmp_path: Path, job_name, module_name, import_origin, review_exit
):
    invocation = _projector_invocation(job_name)
    candidate, ambient, marker, report = _poisoned_projector_paths(tmp_path, job_name, module_name, import_origin)
    shell = f"set -e\ntrusted_env=(env)\nreview_exit={review_exit}\n" + invocation + "\n" + public_projector(job_name)
    shell += '\nPY\nexit "$review_exit"\n'
    environment = dict(os.environ, CUSTOMER_ROOT=str(tmp_path), TRUSTED_ROOT=str(tmp_path), PYTHONPATH=str(ambient))
    environment["REVIEW_PUBLIC_REPORT"] = str(report)
    result = subprocess.run(
        ["bash", "-c", shell], cwd=candidate, env=environment, capture_output=True, text=True, check=False
    )
    _assert_projector_result(result, marker, review_exit)
    _assert_projector_private_state(result, report)


def _projector_invocation(job_name):
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    name = STEP_NAME if job_name == "customer" else "Prepare and review through the authenticated installed controller"
    recipe = next(step["run"] for step in workflow["jobs"][job_name]["steps"] if step.get("name") == name)
    return next(line for line in recipe.splitlines() if "REVIEW_PUBLIC_EXIT=" in line and "<<'PY'" in line)


def _poisoned_projector_paths(tmp_path, job_name, module_name, import_origin):
    interpreter = tmp_path / "venv/bin/python"
    interpreter.parent.mkdir(parents=True)
    interpreter.symlink_to(sys.executable)
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    ambient = tmp_path / "ambient"
    ambient.mkdir()
    marker = tmp_path / "untrusted-import-executed"
    poison = candidate if import_origin == "checkout" else ambient
    (poison / f"{module_name}.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n"
        "raise RuntimeError('UNTRUSTED_IMPORT')\n"
    )
    report = candidate / ".specfact/code-review.json" if job_name == "customer" else tmp_path / "review.private.json"
    report.parent.mkdir(exist_ok=True)
    report.write_text("PRIVATE_REPORT invalid JSON")
    return candidate, ambient, marker, report


def _assert_projector_result(result, marker, review_exit):
    assert not marker.exists(), "Candidate or ambient standard-library lookalikes executed on the host"
    assert result.returncode == review_exit and result.stderr == ""
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    assert rows[-1] == {"status": "INCOMPLETE", "phase": "review", "diagnostic": "review_report_unreadable"}
    assert (review_exit != 124) or rows[0]["diagnostic"] == "analysis_timeout"


def _assert_projector_private_state(result, report):
    assert "PRIVATE_REPORT" not in result.stdout and "UNTRUSTED_IMPORT" not in result.stdout
    assert report.read_text() == "PRIVATE_REPORT invalid JSON"


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


@pytest.mark.parametrize(
    "operation",
    [
        (
            "next(entry for entry in sys.meta_path if hasattr(entry, 'names'))."
            "find_spec.__func__.__globals__['_registered_six_spec'] = lambda *a: None"
        ),
        (
            "next(entry for entry in sys.meta_path if hasattr(entry, 'names'))."
            "find_spec.__func__.__globals__['_registered_six_spec'].__code__ = (lambda *a: None).__code__"
        ),
        (
            "next(entry for entry in sys.meta_path if hasattr(entry, 'names'))."
            "find_spec.__func__.__globals__['_verified_virtual_spec'] = lambda *a: None"
        ),
        (
            "next(entry for entry in sys.meta_path if hasattr(entry, 'names'))."
            "find_spec.__func__.__globals__['_verified_virtual_spec'].__code__ = (lambda *a: None).__code__"
        ),
        (
            "next(entry for entry in sys.meta_path if hasattr(entry, 'names'))."
            "find_spec.__func__.__globals__['_verified_six_importer'] = lambda *a: None"
        ),
        (
            "next(entry for entry in sys.meta_path if hasattr(entry, 'names'))."
            "find_spec.__func__.__globals__['_verified_six_importer'].__code__ = (lambda *a: None).__code__"
        ),
    ],
)
def test_target_startup_cannot_replace_registered_virtual_lookup(collision_runtime, operation):
    completed = _probe_member_dispatch(collision_runtime, "pylint", operation)
    assert completed.returncode == 78
    assert "project_worker_startup_import_state_changed" in completed.stderr
    assert "VERIFIED_DISPATCH" not in completed.stdout


@pytest.mark.parametrize(
    "relative",
    [
        "scripts/check_macos_boundary_ci_receipts.py",
        "scripts/macos_managed_boundary/control.py",
        "tests/unit/test_macos_boundary_ci_receipts.py",
        "tests/unit/test_macos_managed_control.py",
        "scripts/macos_managed_boundary/unrelated.py",
    ],
)
def test_native_diagnostic_committed_review_scope_is_exact(tmp_path: Path, relative: str) -> None:
    worktree, base, _head, _workflow = _prepare_committed_ci_subject(tmp_path, "valid")
    path = worktree / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("fixture native diagnostic\n")
    _git(worktree, "add", ".")
    _git(worktree, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture native diagnostic scope")
    head = _git(worktree, "rev-parse", "HEAD")
    before = (_git(worktree, "write-tree"), _git(worktree, "status", "--porcelain"))
    result = subprocess.run(
        [sys.executable, "-I", str(REPO_ROOT / "scripts/owner_commit_entry.py"), "--head", head, "--base", base],
        cwd=worktree,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == (1 if relative.endswith("unrelated.py") else 0), result.stdout + result.stderr
    assert _git(worktree, "rev-parse", "HEAD") == head
    assert (_git(worktree, "write-tree"), _git(worktree, "status", "--porcelain")) == before


def _prepare_ci_wrapper_source_case(tmp_path: Path, case: str) -> tuple[Path, str, str]:
    schedule_case = "valid" if case == "valid" else "disabled"
    worktree, base, _head, _workflow = _prepare_committed_ci_subject(tmp_path, schedule_case)
    entry_path = worktree / "scripts/owner_commit_entry.py"
    source = (REPO_ROOT / "scripts/owner_commit_entry.py").read_text()
    if case == "early-success":
        source = 'import sys\nsys.stderr.write("UNVERIFIED_WRAPPER_RAN\\n")\nraise SystemExit(0)\n'
    elif case == "skip-validation":
        source = source.replace("checked = validate_commit(Path.cwd(), args.head, args.base)", "checked = False")
    if case == "missing":
        entry_path.unlink(missing_ok=True)
    else:
        entry_path.write_text(source)
    _git(worktree, "add", ".")
    _git(
        worktree,
        "-c",
        "core.hooksPath=/dev/null",
        "commit",
        "--allow-empty",
        "-qm",
        "fixture candidate wrapper regression",
    )
    head = _git(worktree, "rev-parse", "HEAD")
    return worktree, base, head


@pytest.mark.parametrize("case", ["valid", "disabled", "early-success", "skip-validation", "missing"])
def test_required_ci_authenticates_wrapper_before_committed_validation(tmp_path: Path, case: str) -> None:
    worktree, base, head = _prepare_ci_wrapper_source_case(tmp_path, case)
    before = (_git(worktree, "write-tree"), _git(worktree, "status", "--porcelain"))
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/sign-modules.yml").read_text())
    names = {"Authenticate committed scheduling validator", "Validate committed capsule review scheduling"}
    recipes = [step["run"] for step in workflow["jobs"]["verify"]["steps"] if step.get("name") in names]
    recipe = "set -e\n" + "\n".join(recipes)
    recipe = recipe.replace("python -I", shlex.quote(sys.executable) + " -I")
    result = subprocess.run(
        ["bash", "-c", recipe],
        cwd=worktree,
        env=os.environ | {"CANDIDATE_HEAD": head, "CANDIDATE_BASE": base},
        text=True,
        capture_output=True,
        check=False,
    )
    if case == "valid":
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        assert result.returncode != 0, result.stdout + result.stderr
    assert "UNVERIFIED_WRAPPER_RAN" not in result.stderr
    assert _git(worktree, "rev-parse", "HEAD") == head
    assert (_git(worktree, "write-tree"), _git(worktree, "status", "--porcelain")) == before


def test_ci_wrapper_authentication_is_blocking_and_immediately_precedes_validation() -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/sign-modules.yml").read_text())
    steps = workflow["jobs"]["verify"]["steps"]
    authentication = next(step for step in steps if step.get("name") == "Authenticate committed scheduling validator")
    validation = next(step for step in steps if step.get("name") == "Validate committed capsule review scheduling")
    assert steps.index(authentication) + 1 == steps.index(validation)
    assert authentication["if"] == validation["if"] == "github.event_name == 'pull_request' && github.base_ref == 'dev'"
    assert "continue-on-error" not in authentication
    assert "a65627e8dda3d8dcc5de2f79f9a53972f2ec4dcc567163086fe8da06f909a02b" in authentication["run"]
    assert (
        validation["run"] == 'python -I scripts/owner_commit_entry.py --head "$CANDIDATE_HEAD" --base "$CANDIDATE_BASE"'
    )


@pytest.mark.parametrize("suffix", ["plain", "\n", "\r", "\t", '"', "\\", "\u2028", "docs"])
def test_committed_ci_checks_complete_path_surface(tmp_path: Path, suffix: str) -> None:
    worktree, base, _head, _workflow = _prepare_committed_ci_subject(tmp_path, "valid")
    relative = "llms.txt" if suffix == "docs" else "tests/unit/unrelated" + suffix + ".py"
    path = worktree / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("fixture committed path\n")
    _git(worktree, "add", ".")
    _git(worktree, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture complete committed surface")
    head = _git(worktree, "rev-parse", "HEAD")
    before = (_git(worktree, "write-tree"), _git(worktree, "status", "--porcelain"))
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    result = subprocess.run(
        [sys.executable, "-I", str(REPO_ROOT / "scripts/owner_commit_entry.py"), "--head", head, "--base", base],
        cwd=worktree,
        env=os.environ | {"TMPDIR": str(scratch)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == (0 if suffix == "docs" else 1), result.stdout + result.stderr
    assert _git(worktree, "rev-parse", "HEAD") == head
    assert (_git(worktree, "write-tree"), _git(worktree, "status", "--porcelain")) == before
    assert not list(scratch.iterdir())
