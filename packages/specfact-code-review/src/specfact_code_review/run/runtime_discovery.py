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
from packaging.specifiers import InvalidSpecifier, SpecifierSet

from specfact_code_review.run.runtime_adapters import validate_adapter_inputs
from specfact_code_review.run.runtime_models import ProjectPlan, ProjectRuntimeError, content_digest
from specfact_code_review.run.runtime_sources import source_identity
from specfact_code_review.run.runtime_vcs import vcs_context


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


def _validate_config_value(name: str, value: Any) -> None:
    if name in {"manager", "environment", "python"}:
        if not isinstance(value, str) or not value:
            raise ProjectRuntimeError(f"project_config_invalid:{name} must be a nonempty string")
        return
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ProjectRuntimeError(f"project_config_invalid:{name} must be an array of strings")


def _config(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    if path.is_symlink() or not path.is_file():
        raise ProjectRuntimeError("project_config_invalid: expected a regular TOML file")
    values = _toml(path)
    unknown = sorted(set(values) - _CONFIG_FIELDS)
    if unknown:
        raise ProjectRuntimeError(f"project_config_unknown_fields:{','.join(unknown)}")
    for name, value in values.items():
        _validate_config_value(name, value)
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


def _requirement_include(line: str) -> str:
    tokens = shlex.split(line, comments=True)
    if not tokens:
        return ""
    flag = tokens[0]
    if flag in {"-r", "--requirement", "-c", "--constraint"} and len(tokens) >= 2:
        return tokens[1]
    if flag.startswith(("--requirement=", "--constraint=")):
        return flag.split("=", 1)[1]
    if flag.startswith(("-r", "-c")) and len(flag) > 2:
        return flag[2:]
    return ""


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
        if path.name == "pylock.toml" or (path.name.startswith("pylock.") and path.suffix == ".toml"):
            return
        logical_lines = path.read_text(encoding="utf-8").replace("\\\n", "").splitlines()
        for line in logical_lines:
            included = _requirement_include(line)
            if not included:
                continue
            if "://" in included:
                raise ProjectRuntimeError(
                    "project_requirements_remote_include_unsupported; provide a repository-local requirements include"
                )
            child = Path(included)
            if child.is_absolute():
                raise ProjectRuntimeError(f"project_input_escape:{included}")
            relative = os.path.relpath(path.parent / child, root)
            visit(relative, active | {canonical})

    for name in names:
        visit(name, frozenset())
    return visited


def _ini(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read(path, encoding="utf-8")
    except (UnicodeError, configparser.Error) as exc:
        raise ProjectRuntimeError(f"project_config_invalid:{path.name}:{exc}") from exc
    return parser


def _validated_pytest_paths(configuration: dict[str, Any], source: str) -> dict[str, Any]:
    for option in ("pythonpath", "testpaths"):
        value = configuration.get(option, "")
        if isinstance(value, str) or (isinstance(value, list) and all(isinstance(item, str) for item in value)):
            continue
        raise ProjectRuntimeError(
            f"project_pytest_config_invalid:{source}:{option}; expected a string or list of strings"
        )
    return configuration


def _pytest_table(value: Any, source: str, section: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProjectRuntimeError(f"project_pytest_config_invalid:{source}:{section}; expected a table")
    return value


def _pytest_config(root: Path, project: dict[str, Any]) -> dict[str, Any]:
    for name in ("pytest.toml", ".pytest.toml"):
        if (root / name).exists():
            return _validated_pytest_paths(_pytest_table(_toml(root / name).get("pytest", {}), name, "pytest"), name)
    for name in ("pytest.ini", ".pytest.ini", "pyproject.toml", "tox.ini", "setup.cfg"):
        if name == "pyproject.toml":
            pytest = _pytest_table(project.get("tool", {}).get("pytest", {}), name, "tool.pytest")
            if pytest:
                options = _pytest_table(pytest.get("ini_options", pytest), name, "tool.pytest.ini_options")
                return _validated_pytest_paths(options, name)
            continue
        path = root / name
        if not path.exists():
            continue
        parser = _ini(path)
        section = "tool:pytest" if name == "setup.cfg" else "pytest"
        if parser.has_section(section):
            return _validated_pytest_paths(dict(parser[section]), name)
    return {}


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
                f"project_environment_ambiguous:{','.join(sorted(environments))}; "
                "select environment in --project-config"
            )
        environment = next(iter(environments), "default")
    if "groups" in values:
        return environment, tuple(values["groups"])
    if manager == "hatch" or "extras" in values:
        return environment, ()
    groups = project.get("dependency-groups", {})
    if manager == "poetry":
        groups = project.get("tool", {}).get("poetry", {}).get("group", groups)
    tests = sorted(set(groups) & {"test", "tests", "testing"})
    if len(tests) > 1:
        raise ProjectRuntimeError(f"project_test_groups_ambiguous:{','.join(tests)}; select groups in --project-config")
    return environment, tuple(tests)


def _default_requirements(root: Path) -> list[str]:
    texts = [name for name in ("requirements.txt", "requirements.in") if (root / name).is_file()]
    if (root / "pylock.toml").is_file() and texts:
        raise ProjectRuntimeError(
            f"project_requirements_ambiguous:pylock.toml,{','.join(texts)}; select requirements in --project-config"
        )
    for name in ("pylock.toml", "requirements.txt", "requirements.in"):
        if (root / name).is_file():
            return [name]
    return []


def _python_constraint(root: Path, project: dict[str, Any], manager: str) -> str:
    declared = project.get("project", {}).get("requires-python")
    if declared is None:
        declared = _ini(root / "setup.cfg").get("options", "python_requires", fallback="")
    poetry = project.get("tool", {}).get("poetry", {}).get("dependencies", {}).get("python")
    if manager != "poetry" or poetry is None:
        return str(declared)
    remedy = (
        "project_python_constraint_unsupported:tool.poetry.dependencies.python="
        f"{poetry!r}; express the declaration as an equivalent PEP440 version range"
    )
    if not isinstance(poetry, str):
        raise ProjectRuntimeError(remedy)
    try:
        constraint = SpecifierSet(poetry)
    except InvalidSpecifier as exc:
        raise ProjectRuntimeError(remedy) from exc
    return str(SpecifierSet(str(declared)) & constraint)


def _test_extras(
    project: dict[str, Any], values: dict[str, Any], manager: str, groups: tuple[str, ...]
) -> tuple[str, ...]:
    if "extras" in values:
        return tuple(values["extras"])
    if manager == "hatch" or "groups" in values:
        return ()
    declared = project.get("project", {}).get("optional-dependencies", {})
    if manager == "poetry":
        declared = {**project.get("tool", {}).get("poetry", {}).get("extras", {}), **declared}
    candidates = sorted(set(declared) & {"test", "tests", "testing"})
    if len(candidates) > 1 or (candidates and groups):
        choices = [*("extra:" + name for name in candidates), *("group:" + name for name in groups)]
        raise ProjectRuntimeError(
            f"project_test_dependencies_ambiguous:{','.join(choices)}; select groups/extras in --project-config"
        )
    return tuple(candidates)


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
    selection = {**_active_selection(root, project, hatch), **values} if "manager" not in values else values
    manager = _manager(root, project, hatch, selection)
    requirements = tuple(values.get("requirements", ()))
    constraints = tuple(values.get("constraints", []))
    validate_adapter_inputs(manager, requirements, constraints)
    if manager == "pip" and "requirements" not in values:
        requirements = tuple(_default_requirements(root))
    for name in sorted(_requirements_inputs(root, requirements + constraints)):
        inputs[name] = content_digest((root / name).read_bytes())
    pytest = _pytest_config(root, project)
    testpaths = pytest.get("testpaths", [])
    for testpath in testpaths.split() if isinstance(testpaths, str) else testpaths:
        _safe_input(root, testpath)
    environment, groups = _selection(project, hatch, selection, manager)
    return ProjectPlan(
        root=root,
        source_identity=source_identity(root),
        manager=manager,
        environment=environment,
        vcs=vcs_context(root),
        python=values.get(
            "python", (root / ".python-version").read_text().strip() if (root / ".python-version").is_file() else ""
        ),
        requires_python=_python_constraint(root, project, manager),
        groups=groups,
        extras=_test_extras(project, selection, manager, groups),
        requirements=requirements,
        constraints=constraints,
        source_roots=_source_roots(root, values, pytest),
        native_libraries=tuple(values.get("native_libraries", [])),
        inputs=inputs,
        pytest_config=pytest,
    )
