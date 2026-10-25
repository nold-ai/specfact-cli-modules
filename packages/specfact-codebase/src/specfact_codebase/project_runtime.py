"""Trusted local Hatch preparation and execution without dependency synchronization.

This first slice supports detached virtual environments and explicit executable argv.
Native Hatch scripts and effective environment-context expansion are not implemented.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import selectors
import shutil
import signal
import subprocess
import tempfile
import time
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Literal

from packaging.specifiers import InvalidSpecifier, SpecifierSet


_OUTPUT_LIMIT = 65536
_HATCH_CONFIG_DIAGNOSTIC = (
    "Custom HATCH_CONFIG global configuration is unsupported in this milestone; unset it before inspection"
)
_RESERVED_ENV = frozenset({"PATH", "VIRTUAL_ENV", "PYTHONHOME", "PYTHONPATH", "CONDA_PREFIX", "__PYVENV_LAUNCHER__"})
_IGNORED_DIRS = frozenset(
    {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "dist", "build", ".hatch"}
)
_CONFIG_NAMES = frozenset(
    {
        "pyproject.toml",
        "hatch.toml",
        ".python-version",
        "pytest.ini",
        ".pytest.ini",
        "pytest.toml",
        ".pytest.toml",
        "tox.ini",
        "setup.cfg",
        "setup.py",
        "ruff.toml",
        ".ruff.toml",
        "uv.lock",
        "poetry.lock",
        "pylock.toml",
    }
)


@dataclass(frozen=True)
class ProjectSelection:
    python: str | None = None
    manager: str | None = None
    environment: str | None = None
    groups: tuple[str, ...] = ()
    extras: tuple[str, ...] = ()
    hatch: str = "hatch"


@dataclass(frozen=True)
class ProjectCommand:
    argv: tuple[str, ...]
    cwd: Path
    env_overrides: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ProjectPlan:
    root: Path
    selection: ProjectSelection
    input_identity: str
    environment: str | None
    python_request: str | None
    python_constraint: str
    diagnostics: tuple[str, ...]
    hatch_environment: Mapping[str, object] = field(default_factory=dict, repr=False)


@dataclass(frozen=True)
class InterpreterFacts:
    executable: Path
    prefix: Path
    base_prefix: Path
    version: tuple[int, int, int]
    scripts: Path


@dataclass(frozen=True)
class EnvironmentIdentity:
    interpreter: InterpreterFacts
    manager: str
    manager_version: str
    environment: str
    ownership: Literal["existing", "invocation"]
    inputs: str


@dataclass(frozen=True)
class PreparationFailure:
    plan: ProjectPlan
    reason: str
    remedy: str


@dataclass(frozen=True)
class ProjectCommandResult:
    outcome: Literal["exited", "unavailable", "timed_out", "execution_failed"]
    exit_code: int | None
    stdout: str = ""
    stderr: str = ""
    output_truncated: bool = False
    source_identity: str = ""


def _files(root: Path):
    pending = [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as stream:
            entries = sorted(stream, key=lambda entry: entry.name)
        directories = []
        for entry in entries:
            if not entry.is_dir():
                yield Path(entry.path)
                continue
            if entry.name in _IGNORED_DIRS or entry.name.endswith(".egg-info"):
                continue
            if entry.is_symlink():
                yield Path(entry.path)
                continue
            directories.append(Path(entry.path))
        pending.extend(reversed(directories))


def _identity(root: Path, *, source: bool = False) -> str:
    digest = hashlib.sha256()
    for path in _files(root):
        if path.is_symlink() and path.is_dir():
            digest.update(json.dumps(["directory-link", str(path.relative_to(root)), os.readlink(path)]).encode())
            continue
        selected = (
            path.name in _CONFIG_NAMES
            or path.name.startswith(("requirements", "constraints"))
            or path.suffix == ".lock"
        )
        if selected or (source and path.suffix in {".py", ".in"}):
            digest.update(
                json.dumps([str(path.relative_to(root)), hashlib.sha256(path.read_bytes()).hexdigest()]).encode()
            )
    return digest.hexdigest()


def _version_components(request: str) -> tuple[int, ...] | None:
    parts = request.split(".")
    valid = 1 <= len(parts) <= 3 and all(part.isdigit() for part in parts)
    return tuple(map(int, parts)) if valid else None


@dataclass
class _Inspection:
    environment: str | None
    python_request: str | None = None
    python_constraint: str = ""
    hatch_environment: Mapping[str, object] = field(default_factory=dict)
    diagnostics: list[str] = field(default_factory=list)


def _select_environment(envs: object, state: _Inspection) -> None:
    if not isinstance(envs, dict):
        raise ValueError("Hatch envs must be a table")
    if state.environment is None:
        if len(envs) == 1:
            state.environment = next(iter(envs))
        else:
            state.diagnostics.append("Choose environment explicitly from: " + ", ".join(sorted(envs)))
    if state.environment is not None:
        if state.environment not in envs or not isinstance(envs[state.environment], dict):
            state.diagnostics.append(
                f"Unknown environment {state.environment!r}; candidates: {', '.join(sorted(envs))}"
            )
        else:
            state.hatch_environment = envs[state.environment]


def _check_environment(state: _Inspection) -> None:
    config = state.hatch_environment
    if config.get("type", "virtual") != "virtual":
        state.diagnostics.append("Selected environment type is unsupported; select standard virtual")
    if config.get("detached") is not True:
        state.diagnostics.append("Selected environment must be detached in this milestone")
    for key in ("env-vars", "env-include", "env-exclude", "matrix", "template", "platforms"):
        if config.get(key):
            state.diagnostics.append(
                f"Selected Hatch {key} requires native context fidelity not supported in this milestone"
            )


def _read_python_request(root: Path, state: _Inspection) -> None:
    raw_python = state.hatch_environment.get("python")
    if raw_python is None or isinstance(raw_python, str):
        state.python_request = raw_python
    else:
        state.diagnostics.append("Selected Python declaration must be a string")
    version_file = root / ".python-version"
    if not version_file.exists():
        return
    declared = version_file.read_text().strip()
    if state.python_request and not os.path.isabs(state.python_request):
        hatch_parts = _version_components(state.python_request)
        file_parts = _version_components(declared)
        width = min(len(hatch_parts or ()), len(file_parts or ()))
        if not hatch_parts or not file_parts or hatch_parts[:width] != file_parts[:width]:
            state.diagnostics.append(
                "Selected Hatch Python conflicts with .python-version; choose a consistent declaration"
            )
    state.python_request = declared


def _read_declarations(root: Path, selection: ProjectSelection, state: _Inspection) -> None:
    project = tomllib.loads((root / "pyproject.toml").read_text())
    state.python_constraint = project.get("project", {}).get("requires-python", "")
    SpecifierSet(state.python_constraint)
    hatch_file = root / "hatch.toml"
    hatch = tomllib.loads(hatch_file.read_text()) if hatch_file.exists() else project.get("tool", {}).get("hatch", {})
    envs = hatch.get("envs", {"default": {}})
    _select_environment(envs, state)
    if selection.manager not in {None, "hatch"}:
        state.diagnostics.append("Only native Hatch is supported in this milestone")
    if selection.groups or selection.extras:
        state.diagnostics.append("Explicit groups/extras are not supported in this Hatch slice")
    if hatch.get("env", {}).get("requires"):
        state.diagnostics.append(
            "Hatch environment plugin requirements are unsupported; provision a standard virtual environment"
        )
    if state.environment is not None and state.environment in envs:
        _check_environment(state)
    _read_python_request(root, state)


def inspect_project(root: Path, selection: ProjectSelection | None = None) -> ProjectPlan:
    """Inspect declarations only. Ambiguities and unsupported cells remain diagnostics."""
    selection = selection or ProjectSelection()
    root = root.resolve()
    state = _Inspection(selection.environment)
    if os.environ.get("HATCH_CONFIG"):
        state.diagnostics.append(_HATCH_CONFIG_DIAGNOSTIC)
    try:
        _read_declarations(root, selection, state)
    except (OSError, ValueError, TypeError, AttributeError, InvalidSpecifier) as error:
        state.diagnostics.append(f"Cannot inspect project declarations: {error}")
    input_identity = ""
    try:
        input_identity = _identity(root)
    except OSError as error:
        state.diagnostics.append(f"Cannot fingerprint project declarations: {error}")
    return ProjectPlan(
        root,
        selection,
        input_identity,
        state.environment,
        state.python_request,
        state.python_constraint,
        tuple(state.diagnostics),
        state.hatch_environment,
    )


def _environment(scripts: Path | None = None) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in _RESERVED_ENV
        and not key.startswith("PYTHON")
        and (not key.startswith(("HATCH_", "CONDA_")) or key in {"HATCH_DATA_DIR", "HATCH_CACHE_DIR"})
    }
    env["PATH"] = os.pathsep.join([str(scripts)] if scripts else []) + (os.pathsep if scripts else "") + os.defpath
    return env


def _register_pipe(selector: selectors.BaseSelector, stream: IO[bytes] | None, index: int) -> None:
    if stream is None:
        raise ValueError("Subprocess capture pipe is unavailable")
    os.set_blocking(stream.fileno(), False)
    selector.register(stream, selectors.EVENT_READ, index)


def _read_output(selector, buffers, truncated, wait: float) -> bool:
    events = selector.select(wait)
    for key, _ in events:
        block = os.read(key.fd, 8192)
        if not block:
            selector.unregister(key.fileobj)
            continue
        index = key.data
        available = _OUTPUT_LIMIT - len(buffers[index])
        buffers[index].extend(block[:available])
        truncated[index] |= len(block) > available
    return bool(events)


def _capture_output(process, selector, timeout: float):
    buffers = [bytearray(), bytearray()]
    truncated = [False, False]
    deadline = time.monotonic() + timeout
    outcome: Literal["exited", "timed_out"] = "exited"
    while selector.get_map() or process.poll() is None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            if process.poll() is None:
                outcome = "timed_out"
            break
        events = _read_output(selector, buffers, truncated, min(remaining, 0.05))
        if not events and process.poll() is not None:
            break
    return outcome, buffers, truncated


def _stop_process(process) -> None:
    # Detached descendants can retain pipes beyond the original process group.
    with contextlib.suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGKILL)
    process.wait()


def _execute(argv: tuple[str, ...], cwd: Path, env: Mapping[str, str], timeout: float) -> ProjectCommandResult:
    if timeout <= 0:
        return ProjectCommandResult("execution_failed", None, stderr="Timeout must be positive")
    try:
        with (
            subprocess.Popen(
                argv, cwd=cwd, env=dict(env), stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True
            ) as process,
            selectors.DefaultSelector() as selector,
        ):
            for index, stream in enumerate((process.stdout, process.stderr)):
                _register_pipe(selector, stream, index)
            try:
                outcome, buffers, truncated = _capture_output(process, selector, timeout)
            finally:
                _stop_process(process)
            return ProjectCommandResult(
                outcome,
                process.returncode if outcome == "exited" else None,
                buffers[0].decode(errors="replace"),
                buffers[1].decode(errors="replace"),
                any(truncated),
            )
    except FileNotFoundError as error:
        return ProjectCommandResult("unavailable", None, stderr=str(error))
    except (OSError, ValueError) as error:
        return ProjectCommandResult("execution_failed", None, stderr=str(error))


def _probe(executable: Path, cwd: Path) -> InterpreterFacts:
    code = (
        "import json,sys,sysconfig; print(json.dumps([sys.executable,sys.prefix,sys.base_prefix,"
        "list(sys.version_info[:3]),sysconfig.get_path('scripts')]))"
    )
    result = _execute((str(executable), "-I", "-c", code), cwd, _environment(), 15)
    if result.outcome != "exited" or result.exit_code != 0:
        raise ValueError(f"Selected Python probe failed: {result.stderr}")
    try:
        executable_name, prefix, base_prefix, version, scripts = json.loads(result.stdout)
        if len(version) != 3 or not all(isinstance(part, int) for part in version):
            raise ValueError("invalid version")
        return InterpreterFacts(Path(executable_name), Path(prefix), Path(base_prefix), tuple(version), Path(scripts))
    except (ValueError, TypeError) as error:
        raise ValueError("Selected Python returned malformed identity") from error


def _python(plan: ProjectPlan) -> InterpreterFacts:
    declared = plan.hatch_environment.get("python")
    absolute_declared = declared if isinstance(declared, str) and os.path.isabs(declared) else None
    request = plan.selection.python or absolute_declared or plan.python_request
    if not request:
        raise ValueError(
            "Select a local project Python explicitly or declare .python-version; controller fallback is disabled"
        )
    if os.path.isabs(request):
        executable = Path(request).absolute()
    else:
        version = re.fullmatch(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", request)
        name = "python" + ".".join(part for part in version.groups()[:2] if part) if version else request
        found = shutil.which(name)
        if not found:
            raise ValueError(f"Project Python {request} is not available locally; select its absolute executable")
        executable = Path(found).absolute()
    facts = _probe(executable, plan.root)
    _validate_explicit_request(facts, plan.selection.python)
    _validate_python(facts, plan)
    return facts


def _validate_explicit_request(facts: InterpreterFacts, request: str | None) -> None:
    parts = _version_components(request) if request else None
    if parts and facts.version[: len(parts)] != parts:
        raise ValueError(f"Selected Python {facts.version} does not match explicitly requested {request}")


def _validate_python(facts: InterpreterFacts, plan: ProjectPlan) -> None:
    if not SpecifierSet(plan.python_constraint).contains(".".join(map(str, facts.version))):
        raise ValueError(f"Selected Python {facts.version} violates project requires-python {plan.python_constraint}")
    declarations = {
        request
        for request in (plan.python_request, plan.hatch_environment.get("python"))
        if isinstance(request, str) and request
    }
    for request in sorted(declarations):
        if os.path.isabs(request):
            declared = _probe(Path(request), plan.root)
            if facts.base_prefix.resolve() != declared.base_prefix.resolve() or facts.version != declared.version:
                raise ValueError(
                    f"Selected Python {facts.version} at {facts.base_prefix} "
                    f"does not match declared Hatch Python {request}"
                )
        else:
            parts = _version_components(request)
            if parts is None or facts.version[: len(parts)] != parts:
                raise ValueError(f"Selected Python {facts.version} does not match {request}")


def _execution_failure(result: ProjectCommandResult, diagnostic: str, source: str) -> ProjectCommandResult:
    stderr = (diagnostic + "\n" + result.stderr).encode()
    return ProjectCommandResult(
        "execution_failed",
        None,
        result.stdout,
        stderr[:_OUTPUT_LIMIT].decode(errors="replace"),
        result.output_truncated or len(stderr) > _OUTPUT_LIMIT,
        source,
    )


def _command_admission(command: ProjectCommand, cwd: Path, root: Path, source: str) -> ProjectCommandResult | None:
    if not cwd.is_relative_to(root) or not cwd.is_dir() or not command.argv:
        return ProjectCommandResult(
            "execution_failed",
            None,
            stderr="Command needs executable-first argv and a project working directory",
            source_identity=source,
        )
    if _RESERVED_ENV.intersection(command.env_overrides) or any(
        not isinstance(key, str) or not isinstance(value, str) or "=" in key or "\0" in key + value
        for key, value in command.env_overrides.items()
    ):
        return ProjectCommandResult(
            "execution_failed",
            None,
            stderr="Invalid or identity-reserved environment override",
            source_identity=source,
        )
    return None


def _command_executable(command: ProjectCommand, facts: InterpreterFacts, source: str) -> Path | ProjectCommandResult:
    name = command.argv[0]
    if name == "python":
        return facts.executable
    if Path(name).name == name and name not in {".", ".."}:
        return facts.scripts / name
    if Path(name).is_absolute() and (Path(name) == facts.executable or Path(name).parent == facts.scripts):
        return Path(name)
    return ProjectCommandResult(
        "unavailable", None, stderr="Executable must belong to the selected environment", source_identity=source
    )


@dataclass(frozen=True)
class PreparedProject:
    plan: ProjectPlan
    identity: EnvironmentIdentity

    def run(self, command: ProjectCommand, *, timeout: float) -> ProjectCommandResult:
        """Run in the selected environment, with no manager lifecycle authority."""
        try:
            source = _identity(self.plan.root, source=True)
            inputs = _identity(self.plan.root)
        except OSError as error:
            return ProjectCommandResult(
                "execution_failed", None, stderr=f"Cannot fingerprint project before execution: {error}"
            )
        if inputs != self.plan.input_identity:
            return ProjectCommandResult(
                "execution_failed",
                None,
                stderr="Project configuration/dependencies changed; reinspect before execution",
                source_identity=source,
            )
        cwd = command.cwd.resolve()
        refusal = _command_admission(command, cwd, self.plan.root, source)
        if refusal is not None:
            return refusal
        facts = self.identity.interpreter
        name = command.argv[0]
        executable = _command_executable(command, facts, source)
        if isinstance(executable, ProjectCommandResult):
            return executable
        if not executable.is_file() or not os.access(executable, os.X_OK):
            return ProjectCommandResult(
                "unavailable",
                None,
                stderr=(
                    f"Selected environment has no executable {name!r}; "
                    "install it through the project manager in a separate preparation"
                ),
                source_identity=source,
            )
        env = _environment(facts.scripts)
        env["VIRTUAL_ENV"] = str(facts.prefix)
        env.update(command.env_overrides)
        result = _execute((str(executable), *command.argv[1:]), cwd, env, timeout)
        try:
            inputs = _identity(self.plan.root)
        except OSError as error:
            return _execution_failure(result, f"Cannot fingerprint project after execution: {error}", source)
        if inputs != self.plan.input_identity:
            return _execution_failure(
                result, "Project configuration/dependencies changed during execution; reinspect", source
            )
        return ProjectCommandResult(
            result.outcome, result.exit_code, result.stdout, result.stderr, result.output_truncated, source
        )


def _check_preparation(plan: ProjectPlan, workspace: Path) -> None:
    if plan.diagnostics:
        raise ValueError("; ".join(plan.diagnostics))
    if os.environ.get("HATCH_CONFIG"):
        raise ValueError(_HATCH_CONFIG_DIAGNOSTIC)
    if _identity(plan.root) != plan.input_identity:
        raise ValueError("Project inputs changed; reinspect before preparation")
    if workspace.is_relative_to(plan.root) or plan.root.is_relative_to(workspace):
        raise ValueError("Preparation workspace must be external to the project")
    if workspace.exists():
        raise ValueError("Preparation workspace must be fresh and invocation-owned")


def _check_selected_target(requested: InterpreterFacts, target: Path, existing: bool, workspace: Path) -> None:
    if workspace.is_relative_to(requested.prefix) or (existing and workspace.is_relative_to(target.resolve())):
        raise ValueError("Preparation workspace must be outside the selected interpreter prefix")
    if requested.prefix != requested.base_prefix and (not existing or requested.prefix.resolve() != target.resolve()):
        raise ValueError("Explicit virtualenv is not the selected native Hatch environment")


@dataclass(frozen=True)
class _HatchTarget:
    executable: str
    version: ProjectCommandResult
    path: Path
    environment: dict[str, str]
    existing: bool


def _find_hatch_target(plan: ProjectPlan) -> _HatchTarget:
    hatch = shutil.which(plan.selection.hatch)
    if not hatch:
        raise ValueError("Native Hatch executable unavailable; install Hatch externally and select its path")
    env = _environment(Path(hatch).parent)
    version = _execute((hatch, "--version"), plan.root, env, 15)
    if version.outcome != "exited" or version.exit_code:
        raise ValueError(f"Native Hatch version query failed: {version.stderr}")
    location = _execute((hatch, "env", "find", str(plan.environment)), plan.root, env, 30)
    if location.outcome != "exited" or location.exit_code:
        raise ValueError(f"Native Hatch environment lookup failed: {location.stderr}")
    target = Path(location.stdout.strip())
    if not target.is_absolute():
        raise ValueError("Native Hatch returned an invalid environment path")
    existing = (target / "bin/python").is_file()
    return _HatchTarget(hatch, version, target, env, existing)


def _create_cold_target(plan: ProjectPlan, native: _HatchTarget, workspace: Path) -> Path:
    if plan.hatch_environment.get("locked") or plan.hatch_environment.get("path"):
        raise ValueError(
            "Cold selected locked/path environment is unsupported until immutable native preparation is proved"
        )
    target = workspace / "environment"
    native.environment["HATCH_ENV_TYPE_VIRTUAL_PATH"] = str(target)
    creation = _execute((native.executable, "env", "create", str(plan.environment)), plan.root, native.environment, 180)
    if creation.outcome != "exited" or creation.exit_code:
        raise ValueError(f"Native Hatch preparation {creation.outcome}: {creation.stderr}")
    return target


def _check_prepared_identity(facts: InterpreterFacts, requested: InterpreterFacts, target: Path) -> None:
    if (
        facts.prefix.resolve() != target.resolve()
        or facts.version != requested.version
        or facts.base_prefix.resolve() != requested.base_prefix.resolve()
    ):
        raise ValueError(
            f"Prepared interpreter {facts.version} at {facts.prefix} with base {facts.base_prefix} "
            f"does not match selected Python {requested.version} with base {requested.base_prefix} "
            f"at environment {target}"
        )


def _publish_completion(plan: ProjectPlan, identity: EnvironmentIdentity, hatch: str, workspace: Path) -> None:
    facts = identity.interpreter
    payload = {
        "root": str(plan.root),
        "environment": plan.environment,
        "inputs": plan.input_identity,
        "python": str(facts.executable),
        "prefix": str(facts.prefix),
        "version": facts.version,
        "hatch": hatch,
        "hatch_version": identity.manager_version,
        "ownership": identity.ownership,
    }
    with tempfile.NamedTemporaryFile(mode="w", dir=workspace, delete=False) as stream:
        json.dump(payload, stream)
        temporary = Path(stream.name)
    temporary.replace(workspace / "completed.json")


def _preparation_failure(plan: ProjectPlan, workspace: Path, owned: bool, error: Exception) -> PreparationFailure:
    remedy = (
        "Resolve the diagnostic and reinspect with an explicit compatible local environment/Python; "
        "use a fresh external workspace"
    )
    if owned:
        try:
            shutil.rmtree(workspace)
        except OSError as cleanup_error:
            remedy += f". Incomplete workspace remains at {workspace}; cleanup failed: {cleanup_error}"
    return PreparationFailure(plan, str(error), remedy)


def prepare_project(plan: ProjectPlan, workspace: Path) -> PreparedProject | PreparationFailure:
    """Resolve existing Hatch without sync, or natively create one owned cold target."""
    owned = False
    workspace = workspace.resolve()
    try:
        _check_preparation(plan, workspace)
        requested = _python(plan) if plan.selection.python else None
        if requested is not None and workspace.is_relative_to(requested.prefix):
            raise ValueError("Preparation workspace must be outside the selected interpreter prefix")
        native = _find_hatch_target(plan)
        target = native.path
        if requested is None:
            requested = _probe(target / "bin/python", plan.root) if native.existing else _python(plan)
            _validate_python(requested, plan)
        _check_selected_target(requested, target, native.existing, workspace)
        native.environment["PATH"] = str(requested.scripts) + os.pathsep + native.environment["PATH"]
        native.environment["HATCH_PYTHON"] = str(requested.executable)
        workspace.mkdir(parents=True, mode=0o700)
        owned = True
        if not native.existing:
            target = _create_cold_target(plan, native, workspace)
        facts = _probe(target / "bin/python", plan.root)
        _validate_python(facts, plan)
        _check_prepared_identity(facts, requested, target)
        if _identity(plan.root) != plan.input_identity:
            raise ValueError("Project inputs changed during preparation; reinspect")
        identity = EnvironmentIdentity(
            facts,
            "hatch",
            native.version.stdout.strip(),
            str(plan.environment),
            "existing" if native.existing else "invocation",
            plan.input_identity,
        )
        _publish_completion(plan, identity, native.executable, workspace)
        return PreparedProject(plan, identity)
    except (OSError, ValueError, TypeError) as error:
        return _preparation_failure(plan, workspace, owned, error)
