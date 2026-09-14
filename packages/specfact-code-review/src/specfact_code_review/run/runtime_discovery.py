"""Discover Python project inputs without importing or executing project code."""

from __future__ import annotations

import configparser
import os
import shlex
import sys
import tomllib
from pathlib import Path
from typing import Any

from icontract import require

from specfact_code_review.run.runtime_models import ProjectPlan, ProjectRuntimeError, content_digest
from specfact_code_review.run.runtime_sources import source_identity


PROJECT_INPUT_NAMES = (
    "pyproject.toml",
    "hatch.toml",
    "uv.toml",
    "uv.lock",
    "poetry.lock",
    "pylock.toml",
    "setup.py",
    "setup.cfg",
    ".python-version",
    "pytest.ini",
    ".pytest.ini",
    "pytest.toml",
    ".pytest.toml",
    "tox.ini",
    "pyrightconfig.json",
    "basedpyrightconfig.json",
    "ruff.toml",
    ".ruff.toml",
    ".pylintrc",
    "pylintrc",
)
_CONFIG_FIELDS = frozenset(
    {
        "manager",
        "environment",
        "python",
        "groups",
        "extras",
        "requirements",
        "constraints",
        "source_roots",
        "native_libraries",
    }
)
_MANAGERS = frozenset({"pip", "hatch", "uv", "poetry"})


def _safe_input(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ProjectRuntimeError(f"project_input_escape:{relative}; use repository-relative inputs")
    target = root / path
    if any(parent.is_symlink() for parent in (target, *target.parents) if parent != root.parent):
        raise ProjectRuntimeError(f"project_input_symlink:{relative}")
    if not target.resolve().is_relative_to(root):
        raise ProjectRuntimeError(f"project_input_escape:{relative}")
    return target


def _toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ProjectRuntimeError(f"project_config_invalid:{path.name}:{exc}") from exc


def _config(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    if path.is_symlink() or not path.is_file():
        raise ProjectRuntimeError("project_config_invalid: expected a regular TOML file")
    values = _toml(path)
    unknown = sorted(set(values) - _CONFIG_FIELDS)
    if unknown:
        raise ProjectRuntimeError(f"project_config_unknown_fields:{','.join(unknown)}")
    for name in ("manager", "environment", "python"):
        if name in values and (not isinstance(values[name], str) or not values[name]):
            raise ProjectRuntimeError(f"project_config_invalid:{name} must be a nonempty string")
    for name in _CONFIG_FIELDS - {"manager", "environment", "python"}:
        if name in values and (
            not isinstance(values[name], list) or not all(isinstance(item, str) and item for item in values[name])
        ):
            raise ProjectRuntimeError(f"project_config_invalid:{name} must be an array of strings")
    return values


def _active_selection(root: Path, project: dict[str, Any], hatch: dict[str, Any]) -> dict[str, str]:
    """Trust manager activation only when it belongs to this running interpreter."""
    prefix = os.environ.get("VIRTUAL_ENV", "")
    if not prefix or Path(prefix).resolve() != Path(sys.prefix).resolve():
        return {}
    local_environment = any((root / name).resolve() == Path(prefix).resolve() for name in (".venv", "venv"))
    if not local_environment or not (Path(prefix) / "pyvenv.cfg").is_file():
        return {}
    selected = {}
    environments = hatch.get("envs", project.get("tool", {}).get("hatch", {}).get("envs", {}))
    active = os.environ.get("HATCH_ENV_ACTIVE", "")
    if active and active in environments:
        selected = {"manager": "hatch", "environment": active}
    if os.environ.get("POETRY_ACTIVE") == "1":
        if selected:
            raise ProjectRuntimeError("project_active_environment_ambiguous:hatch,poetry; use --project-config")
        selected = {"manager": "poetry"}
    return selected


def _manager(root: Path, project: dict[str, Any], hatch: dict[str, Any], config: dict[str, Any]) -> str:
    explicit = config.get("manager")
    if explicit is not None:
        if explicit not in _MANAGERS:
            raise ProjectRuntimeError(f"project_manager_unsupported:{explicit}")
        return str(explicit)
    tools = project.get("tool", {})
    candidates = set()
    if (root / "uv.lock").exists() or (root / "uv.toml").exists() or "uv" in tools:
        candidates.add("uv")
    if (root / "poetry.lock").exists() or "poetry" in tools:
        candidates.add("poetry")
    if hatch.get("envs") or tools.get("hatch", {}).get("envs"):
        candidates.add("hatch")
    if len(candidates) > 1:
        raise ProjectRuntimeError(
            f"project_manager_ambiguous:{','.join(sorted(candidates))}; select manager in --project-config"
        )
    return next(iter(candidates), "pip")


def _requirements_inputs(root: Path, names: tuple[str, ...]) -> set[str]:
    visited: set[str] = set()

    def visit(name: str, active: frozenset[str]) -> None:
        path = _safe_input(root, name)
        canonical = path.relative_to(root).as_posix()
        if canonical in active:
            raise ProjectRuntimeError(f"project_requirements_cycle:{canonical}")
        if canonical in visited:
            return
        if not path.is_file():
            raise ProjectRuntimeError(f"project_input_missing:{canonical}")
        visited.add(canonical)
        logical_lines = path.read_text(encoding="utf-8").replace("\\\n", "").splitlines()
        for line in logical_lines:
            tokens = shlex.split(line, comments=True)
            if not tokens:
                continue
            flag = tokens[0]
            included = ""
            if flag in {"-r", "--requirement", "-c", "--constraint"} and len(tokens) >= 2:
                included = tokens[1]
            elif flag.startswith(("--requirement=", "--constraint=")):
                included = flag.split("=", 1)[1]
            elif flag.startswith(("-r", "-c")) and len(flag) > 2:
                included = flag[2:]
            if included:
                child = Path(included)
                if child.is_absolute():
                    raise ProjectRuntimeError(f"project_input_escape:{included}")
                relative = os.path.relpath(path.parent / child, root)
                visit(relative, active | {canonical})

    for name in names:
        visit(name, frozenset())
    return visited


def _pytest_config(root: Path, project: dict[str, Any]) -> dict[str, Any]:
    for name in ("pytest.toml", ".pytest.toml"):
        if (root / name).exists():
            return dict(_toml(root / name).get("pytest", {}))
    for name in ("pytest.ini", ".pytest.ini", "pyproject.toml", "tox.ini", "setup.cfg"):
        if name == "pyproject.toml":
            pytest = project.get("tool", {}).get("pytest", {})
            if pytest:
                return dict(pytest.get("ini_options", pytest))
            continue
        path = root / name
        if not path.exists():
            continue
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(path, encoding="utf-8")
        section = "tool:pytest" if name == "setup.cfg" else "pytest"
        if parser.has_section(section):
            return dict(parser[section])
    tools = project.get("tool", {})
    pytest = tools.get("pytest", {})
    return dict(pytest.get("ini_options", pytest))


def _source_roots(root: Path, config: dict[str, Any], pytest: dict[str, Any]) -> tuple[str, ...]:
    roots = config.get("source_roots", pytest.get("pythonpath", ["src", "."] if (root / "src").is_dir() else ["."]))
    if isinstance(roots, str):
        roots = roots.split()
    result = tuple(dict.fromkeys(roots))
    for relative in result:
        _safe_input(root, relative)
    return result


def _selection(
    project: dict[str, Any], hatch: dict[str, Any], values: dict[str, Any], manager: str
) -> tuple[str, tuple[str, ...]]:
    """Select only a single declared environment/test group when no override exists."""
    environment = values.get("environment", "default")
    if manager == "hatch" and "environment" not in values:
        environments = hatch.get("envs", project.get("tool", {}).get("hatch", {}).get("envs", {}))
        if len(environments) > 1:
            raise ProjectRuntimeError(
                f"project_environment_ambiguous:{','.join(sorted(environments))}; select environment in --project-config"
            )
        environment = next(iter(environments), "default")
    if "groups" in values:
        return environment, tuple(values["groups"])
    if manager == "hatch":
        return environment, ()
    groups = project.get("dependency-groups", {})
    if manager == "poetry":
        groups = project.get("tool", {}).get("poetry", {}).get("group", groups)
    tests = sorted(set(groups) & {"test", "tests", "testing"})
    if len(tests) > 1:
        raise ProjectRuntimeError(f"project_test_groups_ambiguous:{','.join(tests)}; select groups in --project-config")
    return environment, tuple(tests)


@require(lambda root: root.is_dir())
def discover_project(root: Path, *, config_path: Path | None = None) -> ProjectPlan:
    """Inspect project manifests; never install dependencies or import setup code."""
    root = root.resolve()
    values = _config(config_path)
    inputs: dict[str, str] = {}
    for name in PROJECT_INPUT_NAMES:
        path = _safe_input(root, name)
        if path.is_file():
            inputs[name] = content_digest(path.read_bytes())
    project = _toml(root / "pyproject.toml")
    hatch = _toml(root / "hatch.toml")
    requirements = tuple(
        values.get("requirements", ["requirements.txt"] if (root / "requirements.txt").exists() else [])
    )
    constraints = tuple(values.get("constraints", []))
    for name in sorted(_requirements_inputs(root, requirements + constraints)):
        inputs[name] = content_digest((root / name).read_bytes())
    pytest = _pytest_config(root, project)
    testpaths = pytest.get("testpaths", [])
    for testpath in testpaths.split() if isinstance(testpaths, str) else testpaths:
        _safe_input(root, testpath)
    selection = {**_active_selection(root, project, hatch), **values} if "manager" not in values else values
    manager = _manager(root, project, hatch, selection)
    environment, groups = _selection(project, hatch, selection, manager)
    return ProjectPlan(
        root=root,
        source_identity=source_identity(root),
        manager=manager,
        environment=environment,
        python=values.get("python", ""),
        requires_python=str(project.get("project", {}).get("requires-python", "")),
        groups=groups,
        extras=tuple(values.get("extras", [])),
        requirements=requirements,
        constraints=constraints,
        source_roots=_source_roots(root, values, pytest),
        native_libraries=tuple(values.get("native_libraries", [])),
        inputs=inputs,
        pytest_config=pytest,
    )
