"""Portable runtime discovery scenarios: never execute project code."""

import re
from pathlib import Path

import pytest
from packaging.specifiers import SpecifierSet

from specfact_code_review.run import runtime_discovery
from specfact_code_review.run.runtime_discovery import discover_project
from specfact_code_review.run.runtime_models import ProjectRuntimeError


def test_hatchling_does_not_override_uv_lock(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[build-system]\nbuild-backend="hatchling.build"\n[project]\nname="consumer"\nrequires-python=">=3.11"\n'
    )
    (tmp_path / "uv.lock").write_text("version = 1\n")
    plan = discover_project(tmp_path)
    assert plan.manager == "uv"
    assert not (tmp_path / ".venv").exists()


def test_ambiguous_managers_need_explicit_selection(tmp_path: Path) -> None:
    (tmp_path / "uv.lock").touch()
    (tmp_path / "poetry.lock").touch()
    with pytest.raises(ProjectRuntimeError, match=r"ambiguous.*poetry.*uv"):
        discover_project(tmp_path)
    (tmp_path / "review.toml").write_text('manager="uv"\ngroups=["test"]\n')
    plan = discover_project(tmp_path, config_path=tmp_path / "review.toml")
    assert plan.manager == "uv"
    assert plan.groups == ("test",)


def test_detached_hatch_env_does_not_inherit_default(tmp_path: Path) -> None:
    (tmp_path / "hatch.toml").write_text(
        '[envs.default]\ndependencies=["unrelated"]\n'
        '[envs.review]\ndetached=true\ndependencies=["pandas", "pytest-asyncio"]\n'
    )
    (tmp_path / "review.toml").write_text('manager="hatch"\nenvironment="review"\n')
    plan = discover_project(tmp_path, config_path=tmp_path / "review.toml")
    assert plan.environment == "review"
    assert plan.manager == "hatch"
    assert "hatch.toml" in plan.inputs
    assert plan.inputs["hatch.toml"].startswith("sha256:")


def test_requirements_include_constraint_affects_identity(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("-r requirements-dev.txt\n-c constraints.txt\n")
    (tmp_path / "requirements-dev.txt").write_text("requests\n")
    constraints = tmp_path / "constraints.txt"
    constraints.write_text("requests==2.32.3\n")
    before = discover_project(tmp_path)
    constraints.write_text("requests==2.32.4\n")
    after = discover_project(tmp_path)
    assert before.identity != after.identity
    assert set(before.inputs) >= {"requirements.txt", "requirements-dev.txt", "constraints.txt"}


@pytest.mark.parametrize("include", ["-r ../secret.txt", "-c /etc/passwd", "-r requirements.txt"])
def test_unsafe_or_cyclic_requirements_are_rejected(tmp_path: Path, include: str) -> None:
    (tmp_path / "requirements.txt").write_text(include + "\n")
    with pytest.raises(ProjectRuntimeError, match=r"(escape|cycle|absolute)"):
        discover_project(tmp_path)


def test_symlinked_input_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").symlink_to("/etc/passwd")
    with pytest.raises(ProjectRuntimeError, match="symlink"):
        discover_project(tmp_path)


def test_input_change_invalidates_even_without_git(tmp_path: Path) -> None:
    project = tmp_path / "pyproject.toml"
    project.write_text('[project]\nname="consumer"\ndependencies=["requests<3"]\n')
    first = discover_project(tmp_path)
    project.write_text('[project]\nname="consumer"\ndependencies=["requests<4"]\n')
    assert first.identity != discover_project(tmp_path).identity


def test_source_roots_and_pytest_config_are_recorded(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="consumer"\n[tool.pytest.ini_options]\npythonpath=["src", "tools", "."]\n'
        'addopts="-ra -v --import-mode=importlib -p pytest_asyncio.plugin"\n'
    )
    (tmp_path / "tools").mkdir()
    plan = discover_project(tmp_path)
    assert plan.source_roots == ("src", "tools", ".")
    assert "-p pytest_asyncio.plugin" in plan.pytest_config["addopts"]


def test_unknown_config_fields_are_actionable(tmp_path: Path) -> None:
    config = tmp_path / "review.toml"
    config.write_text('manger="uv"\n')
    with pytest.raises(ProjectRuntimeError, match="manger"):
        discover_project(tmp_path, config_path=config)


def test_inspect_does_not_run_setup_py(tmp_path: Path) -> None:
    (tmp_path / "setup.py").write_text('raise RuntimeError("must not execute")\n')
    plan = discover_project(tmp_path)
    assert plan.manager == "pip"
    assert "setup.py" in plan.inputs


def test_pyproject_pytest_config_precedes_tox(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[tool.pytest.ini_options]\naddopts="--import-mode=importlib"\n')
    (tmp_path / "tox.ini").write_text("[pytest]\naddopts=--collect-only\n")
    assert discover_project(tmp_path).pytest_config["addopts"] == "--import-mode=importlib"


def test_changed_local_workspace_source_invalidates_runtime(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname="consumer"\n')
    workspace = tmp_path / "components" / "local"
    workspace.mkdir(parents=True)
    source = workspace / "library.py"
    source.write_text("VALUE = 1\n")
    before = discover_project(tmp_path)
    source.write_text("VALUE = 2\n")
    assert before.identity != discover_project(tmp_path).identity


def test_pytest_paths_cannot_escape_snapshot(tmp_path: Path) -> None:
    (tmp_path / "pytest.ini").write_text("[pytest]\ntestpaths=../outside\n")
    with pytest.raises(ProjectRuntimeError, match="escape"):
        discover_project(tmp_path)


@pytest.mark.parametrize("option", ["testpaths", "pythonpath"])
@pytest.mark.parametrize("quote", ['"', "'"])
@pytest.mark.parametrize("path_kind", ["parent", "absolute", "symlink"])
def test_quoted_pytest_paths_are_checked_after_parsing(tmp_path: Path, option: str, quote: str, path_kind: str) -> None:
    config = tmp_path / "review.toml"
    config.write_text('source_roots=["."]\n')
    if path_kind == "symlink":
        relative = "external tree"
        (tmp_path / relative).symlink_to(tmp_path.parent / "outside tree", target_is_directory=True)
    else:
        relative = "../outside tree" if path_kind == "parent" else str(tmp_path.parent / "outside tree")
    (tmp_path / "pytest.ini").write_text(f"[pytest]\n{option}={quote}{relative}{quote}\n")
    with pytest.raises(ProjectRuntimeError, match=r"project_input_(escape|symlink)"):
        discover_project(tmp_path, config_path=config)


@pytest.mark.parametrize("option", ["testpaths", "pythonpath"])
@pytest.mark.parametrize("config_format", ["ini", "toml-list"])
def test_contained_pytest_paths_with_spaces_retain_native_values(
    tmp_path: Path, option: str, config_format: str
) -> None:
    relative = "source tree"
    (tmp_path / relative).mkdir()
    if config_format == "ini":
        recorded = f'"{relative}"'
        (tmp_path / "pytest.ini").write_text(f"[pytest]\n{option}={recorded}\n")
    else:
        recorded = [relative]
        (tmp_path / "pytest.toml").write_text(f'[pytest]\n{option}=["{relative}"]\n')
    plan = discover_project(tmp_path)
    assert plan.pytest_config[option] == recorded
    if option == "pythonpath":
        assert plan.source_roots == (relative,)


def test_single_declared_test_group_is_prepared_automatically(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[dependency-groups]\ntest=["pytest"]\ndocs=["sphinx"]\n')
    assert discover_project(tmp_path).groups == ("test",)


def test_competing_hatch_environments_require_selection(tmp_path: Path) -> None:
    (tmp_path / "hatch.toml").write_text(
        '[envs.default]\ndependencies=["pytest<8"]\n[envs.test]\ndependencies=["pytest>=9"]\n'
    )
    with pytest.raises(ProjectRuntimeError, match=r"environment_ambiguous.*default.*test"):
        discover_project(tmp_path)


def test_requirements_parent_include_inside_repository(tmp_path: Path) -> None:
    (tmp_path / "requirements").mkdir()
    (tmp_path / "requirements.txt").write_text("-r requirements/dev.txt\n")
    (tmp_path / "requirements/dev.txt").write_text("-c ../constraints.txt\nrequests\n")
    (tmp_path / "constraints.txt").write_text("requests<3\n")
    assert "constraints.txt" in discover_project(tmp_path).inputs


def test_verified_active_hatch_context_resolves_competing_signals(tmp_path: Path, monkeypatch) -> None:
    environment = tmp_path / ".venv"
    environment.mkdir()
    (environment / "pyvenv.cfg").write_text("home = /usr/bin\n")
    (tmp_path / "uv.lock").touch()
    (tmp_path / "hatch.toml").write_text("[envs.default]\n[envs.review]\ndetached=true\n")
    monkeypatch.setenv("VIRTUAL_ENV", str(environment))
    monkeypatch.setenv("HATCH_ENV_ACTIVE", "review")
    monkeypatch.setattr(runtime_discovery.sys, "prefix", str(environment))
    plan = discover_project(tmp_path)
    assert (plan.manager, plan.environment) == ("hatch", "review")


def test_unverified_active_context_cannot_override_repository(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "uv.lock").touch()
    monkeypatch.setenv("VIRTUAL_ENV", str(tmp_path / "missing-env"))
    monkeypatch.setenv("HATCH_ENV_ACTIVE", "review")
    assert discover_project(tmp_path).manager == "uv"


def test_unlocked_pip_tools_input_is_discovered(tmp_path: Path) -> None:
    (tmp_path / "requirements.in").write_text("requests<3\n")
    plan = discover_project(tmp_path)
    assert plan.requirements == ("requirements.in",)
    assert "requirements.in" in plan.inputs
    (tmp_path / "requirements.txt").write_text("requests==2.32.5\n")
    assert discover_project(tmp_path).requirements == ("requirements.txt",)


def test_legacy_static_python_constraint_is_imported(tmp_path: Path) -> None:
    (tmp_path / "setup.cfg").write_text("[options]\npython_requires = >=3.11,<3.12\n")
    assert discover_project(tmp_path).requires_python == ">=3.11,<3.12"


def test_poetry_python_constraint_intersects_package_metadata(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nrequires-python=">=3.12"\n[tool.poetry.dependencies]\npython=">=3.11,<3.13"\n'
    )
    constraint = SpecifierSet(discover_project(tmp_path).requires_python)
    assert "3.12.1" in constraint
    assert "3.11.1" not in constraint and "3.13.1" not in constraint


@pytest.mark.parametrize("declared", ["^3.12", "~3.12", ">=3.11,<3.12 || >=3.13", {"version": ">=3.12"}])
def test_unsupported_poetry_python_syntax_has_exact_remedy(tmp_path: Path, declared) -> None:
    text = '{version=">=3.12"}' if isinstance(declared, dict) else f'"{declared}"'
    (tmp_path / "pyproject.toml").write_text(f"[tool.poetry.dependencies]\npython={text}\n")
    with pytest.raises(ProjectRuntimeError, match="project_python_constraint_unsupported") as error:
        discover_project(tmp_path)
    assert "tool.poetry.dependencies.python" in str(error.value)
    assert "PEP440" in str(error.value)


def test_explicit_pip_does_not_import_poetry_resolver_constraint(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nrequires-python=">=3.11"\n[tool.poetry.dependencies]\npython="^3.12"\n'
    )
    config = tmp_path / "review.toml"
    config.write_text('manager="pip"\n')
    assert discover_project(tmp_path, config_path=config).requires_python == ">=3.11"


@pytest.mark.parametrize("manager", ["uv", "hatch", "poetry"])
@pytest.mark.parametrize("fields", [("requirements",), ("constraints",), ("requirements", "constraints")])
def test_non_pip_rejects_explicit_dependency_inputs_before_reading(tmp_path: Path, manager: str, fields) -> None:
    config = tmp_path / "review.toml"
    config.write_text(f'manager="{manager}"\n' + "".join(f'{field}=["absent.txt"]\n' for field in fields))
    with pytest.raises(ProjectRuntimeError, match=f"project_manager_inputs_unsupported:{manager}") as error:
        discover_project(tmp_path, config_path=config)
    assert all(field in str(error.value) for field in fields)
    assert "pip" in str(error.value) and "--project-config" in str(error.value)


@pytest.mark.parametrize("manager", ["uv", "hatch", "poetry"])
def test_native_manager_does_not_select_unrelated_pip_exports(tmp_path: Path, manager: str) -> None:
    (tmp_path / "pyproject.toml").write_text(
        f"[tool.{manager}]\n" if manager != "hatch" else "[tool.hatch.envs.test]\n"
    )
    (tmp_path / "pylock.toml").write_text('lock-version="1.0"\n')
    (tmp_path / "requirements.txt").write_text("-r absent.txt\n")
    plan = discover_project(tmp_path)
    assert plan.manager == manager
    assert not plan.requirements and not plan.constraints
    assert "requirements.txt" not in plan.inputs


@pytest.mark.parametrize("manager", ["uv", "hatch", "poetry"])
def test_non_pip_accepts_empty_dependency_overrides(tmp_path: Path, manager: str) -> None:
    config = tmp_path / "review.toml"
    config.write_text(f'manager="{manager}"\nrequirements=[]\nconstraints=[]\n')
    plan = discover_project(tmp_path, config_path=config)
    assert not plan.requirements and not plan.constraints


def test_one_test_extra_is_prepared_automatically(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project.optional-dependencies]\ntest=["pytest"]\n')
    assert discover_project(tmp_path).extras == ("test",)


def test_group_and_extra_require_explicit_selection(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project.optional-dependencies]\ntest=["pytest"]\n[dependency-groups]\ntest=["pytest<9"]\n'
    )
    with pytest.raises(ProjectRuntimeError, match="test_dependencies_ambiguous"):
        discover_project(tmp_path)
    configuration = tmp_path / "runtime.toml"
    configuration.write_text('extras=["test"]\n')
    plan = discover_project(tmp_path, config_path=configuration)
    assert plan.extras == ("test",) and not plan.groups


def test_executable_source_mode_is_part_of_runtime_identity(tmp_path: Path) -> None:
    script = tmp_path / "manage"
    script.write_text("#!/usr/bin/env python\nprint('ready')\n")
    script.chmod(0o644)
    before = discover_project(tmp_path).identity
    script.chmod(0o755)
    assert discover_project(tmp_path).identity != before


def test_pylock_uses_native_pip_input_without_requirement_line_parsing(tmp_path: Path) -> None:
    (tmp_path / "pylock.toml").write_text(
        'lock-version="1.0"\ncreated-by="pip"\n[[packages]]\nname="requests"\nversion="2.32.5"\n'
    )
    assert discover_project(tmp_path).requirements == ("pylock.toml",)
    (tmp_path / "requirements.txt").write_text("requests<2\n")
    with pytest.raises(ProjectRuntimeError, match="requirements_ambiguous"):
        discover_project(tmp_path)


def test_remote_requirement_include_diagnostic_omits_credentials(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("-r https://username:secret-token@example.invalid/requirements.txt\n")
    with pytest.raises(ProjectRuntimeError) as error:
        discover_project(tmp_path)
    assert "remote_include" in str(error.value)
    assert "secret-token" not in str(error.value)


def test_source_identity_distinguishes_executable_permission_classes(tmp_path: Path) -> None:
    script = tmp_path / "manage"
    script.write_text("#!/usr/bin/env python\n")
    script.chmod(0o754)
    before = discover_project(tmp_path).identity
    script.chmod(0o745)
    assert discover_project(tmp_path).identity != before


def test_pylock_and_uncompiled_requirements_need_explicit_selection(tmp_path: Path) -> None:
    (tmp_path / "pylock.toml").write_text('lock-version="1.0"\n')
    (tmp_path / "requirements.in").write_text("requests\n")
    with pytest.raises(ProjectRuntimeError, match=r"ambiguous.*pylock.toml.*requirements.in"):
        discover_project(tmp_path)
    config = tmp_path / "selection.toml"
    config.write_text('requirements=["requirements.in"]\n')
    assert discover_project(tmp_path, config_path=config).requirements == ("requirements.in",)


@pytest.mark.parametrize("filename", ["setup.cfg", "pytest.ini", "tox.ini"])
def test_malformed_ini_is_a_project_diagnostic(tmp_path: Path, filename: str) -> None:
    (tmp_path / filename).write_text("not an INI section\n")
    with pytest.raises(ProjectRuntimeError, match=r"project_config_invalid:" + filename):
        discover_project(tmp_path)


@pytest.mark.parametrize(
    "filename,section",
    [
        ("pytest.toml", "pytest"),
        (".pytest.toml", "pytest"),
        ("pyproject.toml", "tool.pytest.ini_options"),
        ("pyproject.toml", "tool.pytest"),
    ],
)
@pytest.mark.parametrize("option", ["pythonpath", "testpaths"])
@pytest.mark.parametrize("value", ["1", "true", "[1]", '["tests", 1]', "{path = 'tests'}"])
def test_invalid_pytest_path_shape_has_project_diagnostic(
    tmp_path: Path, filename: str, section: str, option: str, value: str
) -> None:
    (tmp_path / filename).write_text(f"[{section}]\n{option} = {value}\n")
    with pytest.raises(ProjectRuntimeError, match=f"project_pytest_config_invalid:{filename}:{option}"):
        discover_project(tmp_path)


@pytest.mark.parametrize(
    "filename,section",
    [("pytest.ini", "pytest"), (".pytest.ini", "pytest"), ("tox.ini", "pytest"), ("setup.cfg", "tool:pytest")],
)
def test_ini_pytest_path_strings_are_preserved(tmp_path: Path, filename: str, section: str) -> None:
    (tmp_path / filename).write_text(f"[{section}]\npythonpath = src tests\ntestpaths = tests\n")
    plan = discover_project(tmp_path)
    assert plan.pytest_config["pythonpath"] == "src tests"
    assert plan.pytest_config["testpaths"] == "tests"
    assert plan.source_roots == ("src", "tests")


@pytest.mark.parametrize(
    "filename,section,prefix",
    [
        ("pytest.toml", "pytest", ""),
        (".pytest.toml", "pytest", ""),
        ("pyproject.toml", "tool.pytest", "[tool]\n"),
        ("pyproject.toml", "tool.pytest.ini_options", "[tool.pytest]\n"),
    ],
)
@pytest.mark.parametrize("value", ["1", "0", "true", "false", "[]", '["tests"]', '"invalid"'])
def test_malformed_pytest_table_has_project_diagnostic(
    tmp_path: Path, filename: str, section: str, prefix: str, value: str
) -> None:
    (tmp_path / filename).write_text(prefix + section.rsplit(".", 1)[-1] + "=" + value + "\n")
    with pytest.raises(
        ProjectRuntimeError, match=re.escape(f"project_pytest_config_invalid:{filename}:{section}; expected a table")
    ):
        discover_project(tmp_path)


@pytest.mark.parametrize(
    "filename,section",
    [
        ("pyproject.toml", "tool"),
        ("pyproject.toml", "project"),
        ("pyproject.toml", "dependency-groups"),
        ("pyproject.toml", "project.optional-dependencies"),
        ("pyproject.toml", "tool.uv"),
        ("pyproject.toml", "tool.hatch"),
        ("pyproject.toml", "tool.hatch.envs"),
        ("pyproject.toml", "tool.poetry"),
        ("pyproject.toml", "tool.poetry.dependencies"),
        ("pyproject.toml", "tool.poetry.group"),
        ("pyproject.toml", "tool.poetry.extras"),
        ("hatch.toml", "envs"),
    ],
)
@pytest.mark.parametrize("value", ["1", "false", "[]", '"invalid"'])
@pytest.mark.parametrize("explicit", [False, True])
def test_consumed_metadata_tables_have_actionable_shape_diagnostics(
    tmp_path: Path, filename: str, section: str, value: str, explicit: bool
) -> None:
    parent, _, option = section.rpartition(".")
    declaration = (f"[{parent}]\n" if parent else "") + f"{option}={value}\n"
    (tmp_path / filename).write_text(declaration)
    config = tmp_path / "review-runtime.toml"
    config.write_text('manager="pip"\n')
    with pytest.raises(
        ProjectRuntimeError, match=re.escape(f"project_config_invalid:{filename}:{section}; expected a table")
    ):
        discover_project(tmp_path, config_path=config if explicit else None)
