"""Native adapters preserve lock and explicit dependency-group selection."""

import subprocess
import sys
from pathlib import Path

import pytest

from specfact_code_review.run.runtime_adapters import install_commands
from specfact_code_review.run.runtime_discovery import discover_project
from specfact_code_review.run.runtime_models import ProjectPlan, ProjectRuntimeError


def test_pip_preserves_requirement_constraints_and_groups(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname="consumer"\n')
    (tmp_path / "constraints.txt").write_text("requests<3\n")
    config = tmp_path / "review.toml"
    config.write_text('manager="pip"\ngroups=["test"]\nextras=["speed"]\nconstraints=["constraints.txt"]\n')
    commands = install_commands(discover_project(tmp_path, config_path=config), python="/runtime/python")
    combined = [arg for command in commands for arg in command]
    assert "--group" in combined and "test" in combined
    assert "-c" in combined and "constraints.txt" in combined
    assert ".[speed]" in combined


def test_uv_uses_locked_resolution_without_changing_source(tmp_path: Path) -> None:
    (tmp_path / "uv.lock").write_text("version=1\n")
    commands = install_commands(discover_project(tmp_path), python="/runtime/python")
    assert "--locked" in [arg for command in commands for arg in command]
    assert not (tmp_path / ".venv").exists()


def test_hatch_prepare_uses_selected_native_environment(tmp_path: Path) -> None:
    (tmp_path / "hatch.toml").write_text("[envs.review]\ndetached=true\n")
    config = tmp_path / "review.toml"
    config.write_text('manager="hatch"\nenvironment="review"\n')
    commands = install_commands(discover_project(tmp_path, config_path=config), python="/runtime/python")
    assert commands == (("/runtime/python", "-m", "hatch", "env", "create", "review"),)


def test_explicit_groups_do_not_install_unrelated_defaults(tmp_path: Path) -> None:

    uv = install_commands(ProjectPlan(root=tmp_path, manager="uv", groups=("tests",)), python="python")[0]
    poetry = install_commands(ProjectPlan(root=tmp_path, manager="poetry", groups=("test",)), python="python")[0]
    assert "--no-default-groups" in uv
    assert poetry[poetry.index("--only") + 1] == "main,test"


@pytest.mark.parametrize("manager", ["uv", "hatch", "poetry"])
@pytest.mark.parametrize("field", ["requirements", "constraints"])
def test_native_adapter_rejects_unconsumed_dependency_inputs(tmp_path: Path, manager: str, field: str) -> None:
    plan = ProjectPlan(
        root=tmp_path,
        manager=manager,
        requirements=("dependencies.txt",) if field == "requirements" else (),
        constraints=("dependencies.txt",) if field == "constraints" else (),
    )
    with pytest.raises(ProjectRuntimeError, match=f"project_manager_inputs_unsupported:{manager}") as error:
        install_commands(plan, python="python")
    assert field in str(error.value)


def test_tool_only_setup_cfg_prepares_requirements_without_installing_root(tmp_path: Path) -> None:
    (tmp_path / "setup.cfg").write_text("[tool:pytest]\naddopts = --strict-markers\npythonpath = .\n")
    (tmp_path / "requirements.txt").write_text("packaging\n")
    (tmp_path / "constraints.txt").write_text("packaging>=1\n")
    config = tmp_path / "review.toml"
    config.write_text('manager="pip"\nconstraints=["constraints.txt"]\n')
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    plan = discover_project(tmp_path, config_path=config)
    assert plan.pytest_config["addopts"] == "--strict-markers"
    assert plan.source_roots == (".",)
    commands = install_commands(plan, python=sys.executable)
    # pip's no-index dry run validates the actual adapter command without installs.
    completed = subprocess.run(
        [*commands[0], "--no-index", "--no-deps", "--dry-run"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert commands[0][-4:] == ("-r", "requirements.txt", "-c", "constraints.txt")
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == before


@pytest.mark.parametrize("contents", ["[tool:pytest]\naddopts = --strict-markers\n", "[metadata]\nname = example\n"])
def test_setup_cfg_without_package_entrypoint_requires_no_install(tmp_path: Path, contents: str) -> None:
    (tmp_path / "setup.cfg").write_text(contents)
    assert install_commands(discover_project(tmp_path), python="python") == ()


@pytest.mark.parametrize(
    "name,contents",
    [
        ("setup.py", 'raise AssertionError("discovery must not execute setup.py")\n'),
        ("pyproject.toml", '[project]\nname="example"\nversion="1.0"\n'),
        ("pyproject.toml", '[tool.pytest.ini_options]\naddopts="--strict-markers"\n'),
    ],
)
def test_pip_native_package_entrypoints_retain_root_install_and_extras(
    tmp_path: Path, name: str, contents: str
) -> None:
    (tmp_path / name).write_text(contents)
    plan = ProjectPlan(root=tmp_path, manager="pip", extras=("speed",))
    assert install_commands(plan, python="python")[0][-1] == ".[speed]"


@pytest.mark.parametrize("name", ["pyproject.toml", "setup.py"])
def test_pip_package_entrypoint_must_be_a_regular_file(tmp_path: Path, name: str) -> None:
    (tmp_path / name).mkdir()
    assert install_commands(ProjectPlan(root=tmp_path, manager="pip"), python="python") == ()
