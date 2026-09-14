"""Native adapters preserve lock and explicit dependency-group selection."""

from pathlib import Path

from specfact_code_review.run.runtime_adapters import install_commands
from specfact_code_review.run.runtime_discovery import discover_project


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
    from specfact_code_review.run.runtime_adapters import install_commands
    from specfact_code_review.run.runtime_models import ProjectPlan

    uv = install_commands(ProjectPlan(root=tmp_path, manager="uv", groups=("tests",)), python="python")[0]
    poetry = install_commands(ProjectPlan(root=tmp_path, manager="poetry", groups=("test",)), python="python")[0]
    assert "--no-default-groups" in uv
    assert poetry[poetry.index("--only") + 1] == "main,test"
