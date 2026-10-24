import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from specfact_codebase import project_runtime
from specfact_codebase.project_runtime import (
    PreparedProject,
    ProjectCommand,
    ProjectSelection,
    inspect_project,
    prepare_project,
)


@pytest.fixture(autouse=True)
def record_selector(request, record_property):
    record_property("specfact.selector", request.node.nodeid)


def test_existing_and_cold_native_hatch_workflow():
    location = os.environ.get("SPECFACT_HATCH_PROOF_WORKSPACE")
    if not location:
        pytest.skip(
            "Set SPECFACT_HATCH_PROOF_WORKSPACE with native Hatch and Python 3.11 prerequisites for the acceptance cell"
        )
    prerequisites = ("SPECFACT_HATCH_EXECUTABLE", "SPECFACT_HATCH_PROJECT_PYTHON")
    missing = [name for name in prerequisites if not os.environ.get(name)]
    if missing:
        pytest.fail("Configured native acceptance cell requires: " + ", ".join(missing))
    hatch, python = (os.environ[name] for name in prerequisites)
    script = Path(__file__).resolve().parents[2] / "scripts/prove_hatch_project_runtime.py"
    spec = importlib.util.spec_from_file_location("hatch_runtime_proof", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    receipt = module.prove(
        Path(location),
        hatch=Path(hatch),
        python=Path(python),
    )
    assert set(receipt["cases"]) == {"existing", "cold"}


def _create_storage_customer(tmp_path, hatch, python):
    root = tmp_path / "customer"
    root.mkdir()
    (root / "pyproject.toml").write_text('[project]\nname="storage-customer"\nversion="0"\n')
    (root / "hatch.toml").write_text("[envs.review]\ndetached=true\ndependencies=[]\n")
    data = tmp_path / "customer-data"
    cache = tmp_path / "customer-cache"
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("HATCH_") and key not in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"}
    }
    environment.update(HATCH_DATA_DIR=str(data), HATCH_CACHE_DIR=str(cache), HATCH_PYTHON=python)
    subprocess.run(
        [hatch, "env", "create", "review"],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
        timeout=180,
    )
    location = subprocess.run(
        [hatch, "env", "find", "review"],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    prefix = Path(location.stdout.strip())
    assert prefix.is_relative_to(data)
    return root, data, cache, prefix


def test_native_hatch_customer_storage_survives_controller_context(tmp_path, monkeypatch):
    hatch = os.environ.get("SPECFACT_HATCH_EXECUTABLE")
    python = os.environ.get("SPECFACT_HATCH_PROJECT_PYTHON")
    if not hatch or not python:
        pytest.skip("Native Hatch and project Python are required for customer storage acceptance")
    root, data, cache, prefix = _create_storage_customer(tmp_path, hatch, python)
    monkeypatch.setenv("HATCH_DATA_DIR", str(data))
    monkeypatch.setenv("HATCH_CACHE_DIR", str(cache))
    monkeypatch.delenv("HATCH_CONFIG", raising=False)
    for name in ("HATCH_ENV_ACTIVE", "HATCH_PYTHON", "HATCH_ENV_TYPE_VIRTUAL_PATH", "HATCH_PROJECT"):
        monkeypatch.setenv(name, "/controller/invalid")
    plan = inspect_project(root, ProjectSelection(environment="review", hatch=hatch))
    prepared = prepare_project(plan, tmp_path / "invocation")
    assert isinstance(prepared, PreparedProject), prepared
    assert prepared.identity.ownership == "existing"
    assert prepared.identity.interpreter.prefix == prefix
    result = prepared.run(
        ProjectCommand(
            (
                "python",
                "-c",
                "import os,json; print(json.dumps([os.getenv('HATCH_DATA_DIR'),"
                "os.getenv('HATCH_CACHE_DIR'),os.getenv('HATCH_ENV_ACTIVE'),"
                "os.getenv('HATCH_PYTHON'),os.getenv('HATCH_ENV_TYPE_VIRTUAL_PATH'),"
                "os.getenv('HATCH_PROJECT')]))",
            ),
            root,
        ),
        timeout=10,
    )
    assert result.outcome == "exited" and result.exit_code == 0
    assert json.loads(result.stdout) == [str(data), str(cache), None, None, None, None]


@pytest.mark.parametrize("optimization", ["flag", "environment"])
def test_native_proof_rejects_optimized_python_before_allocation(tmp_path, optimization):
    repository = Path(__file__).resolve().parents[2]
    workspace = tmp_path / "proof"
    command = [sys.executable]
    if optimization == "flag":
        command.append("-O")
    command += [
        str(repository / "scripts/prove_hatch_project_runtime.py"),
        "--workspace",
        str(workspace),
        "--hatch",
        str(tmp_path / "missing-hatch"),
        "--python",
        str(tmp_path / "missing-python"),
    ]
    environment = os.environ | {"PYTHONPATH": str(repository / "packages/specfact-codebase/src")}
    if optimization == "environment":
        environment["PYTHONOPTIMIZE"] = "1"
    result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=15, check=False)
    assert result.returncode != 0
    assert "optimized Python" in result.stderr
    assert not workspace.exists()
    assert not (workspace / "receipt.json").exists()


def test_native_proof_rejects_wrong_controller_before_allocation(tmp_path, monkeypatch):
    script = Path(__file__).resolve().parents[2] / "scripts/prove_hatch_project_runtime.py"
    spec = importlib.util.spec_from_file_location("hatch_precondition_proof", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "sys", SimpleNamespace(version_info=(3, 11, 15), executable="wrong-controller"))
    workspace = tmp_path / "proof"
    with pytest.raises(RuntimeError, match=r"controller Python 3\.12"):
        module.prove(workspace, hatch=tmp_path / "missing-hatch", python=tmp_path / "missing-python")
    assert not workspace.exists()
    assert not (workspace / "receipt.json").exists()


def _create_absolute_customer(tmp_path, python, version_file):
    expected = json.loads(
        subprocess.check_output(
            [python, "-I", "-c", "import sys,json; print(json.dumps([sys.base_prefix,list(sys.version_info[:3])]))"],
            text=True,
        )
    )
    customer = tmp_path / "customer"
    customer.mkdir()
    (customer / "pyproject.toml").write_text('[project]\nname="absolute-python-customer"\nversion="0"\n')
    (customer / "hatch.toml").write_text(
        "[envs.review]\ndetached=true\ndependencies=[]\npython=" + json.dumps(python) + "\n"
    )
    if version_file:
        (customer / ".python-version").write_text(".".join(map(str, expected[1])) + "\n")
    declarations = {path.name: path.read_bytes() for path in customer.iterdir()}
    return customer, expected, declarations


def _absolute_target(tmp_path, monkeypatch, customer, hatch, existing):
    for name in tuple(os.environ):
        if name.startswith("HATCH_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("HATCH_DATA_DIR", str(tmp_path / "hatch-data"))
    monkeypatch.setenv("HATCH_CACHE_DIR", str(tmp_path / "hatch-cache"))
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "__PYVENV_LAUNCHER__"}
    }
    if existing:
        subprocess.run(
            [hatch, "env", "create", "review"],
            cwd=customer,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
        )
    return (
        Path(
            subprocess.check_output([hatch, "env", "find", "review"], cwd=customer, env=environment, text=True).strip()
        )
        if existing
        else tmp_path / "invocation/environment"
    )


def _assert_absolute_identity(prepared, customer, expected_target, expected, existing):
    assert prepared.identity.ownership == ("existing" if existing else "invocation")
    assert prepared.identity.interpreter.prefix == expected_target
    assert str(prepared.identity.interpreter.base_prefix) == expected[0]
    assert list(prepared.identity.interpreter.version) == expected[1]
    result = prepared.run(
        ProjectCommand(
            (
                "python",
                "-c",
                "import sys,json; print(json.dumps([sys.base_prefix,list(sys.version_info[:3]),"
                "sys.prefix,sys.executable]))",
            ),
            customer,
        ),
        timeout=10,
    )
    assert result.outcome == "exited" and result.exit_code == 0
    assert json.loads(result.stdout) == [*expected, str(expected_target), str(prepared.identity.interpreter.executable)]


@pytest.mark.parametrize("version_file", [False, True], ids=["without-version-file", "with-version-file"])
@pytest.mark.parametrize("existing", [False, True], ids=["cold", "existing"])
def test_native_hatch_absolute_python_declaration(tmp_path, monkeypatch, existing, version_file):
    hatch = os.environ.get("SPECFACT_HATCH_EXECUTABLE")
    python = os.environ.get("SPECFACT_HATCH_PROJECT_PYTHON")
    if not hatch or not python:
        pytest.skip("Native Hatch and project Python are required for absolute declaration acceptance")
    customer, expected, declarations = _create_absolute_customer(tmp_path, python, version_file)
    expected_target = _absolute_target(tmp_path, monkeypatch, customer, hatch, existing)
    native_which = project_runtime.shutil.which
    monkeypatch.setattr(project_runtime.shutil, "which", lambda name: native_which(name) if name == hatch else None)
    plan = inspect_project(customer, ProjectSelection(environment="review", hatch=hatch))
    assert not plan.diagnostics
    prepared = prepare_project(plan, tmp_path / "invocation")
    assert isinstance(prepared, PreparedProject), prepared
    _assert_absolute_identity(prepared, customer, expected_target, expected, existing)
    assert {name: (customer / name).read_bytes() for name in declarations} == declarations
