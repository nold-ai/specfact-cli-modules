"""Trusted Darwin analyzer worker with a closed managed-process handoff."""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from contextlib import ExitStack
from functools import partial
from importlib import import_module
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Final, cast
from unittest.mock import patch

from pydantic import ValidationError

from specfact_code_review.run.findings import ReviewFinding
from specfact_code_review.tools.ai_bloat_runner import run_ai_bloat
from specfact_code_review.tools.ast_clean_code_runner import run_ast_clean_code


EXIT_COMPLETE: Final = 0
EXIT_REPLAY_REQUIRED: Final = 75
EXIT_INVALID_REQUEST: Final = 76
EXIT_INVALID_RESULT: Final = 77
EXIT_OUTPUT_COLLISION: Final = 78

_REQUEST_NAME: Final = ".specfact-native-request.json"
_REPLIES_NAME: Final = ".specfact-native-replies.json"
_REQUEST_SCHEMA: Final = "specfact-native-analyzer-request-v1"
_REPLIES_SCHEMA: Final = "specfact-native-analyzer-replies-v1"
_BROKER_OUTPUTS: Final = frozenset({"managed-stdout.bin", "managed-stderr.bin"})
_REQUEST_FIELDS: Final = frozenset(
    {"adapter_argv", "bug_hunt", "complete_pytest_inventory", "member", "paths", "schema"}
)
_UNSAFE_ENVIRONMENT: Final = frozenset(
    {
        "DYLD_FRAMEWORK_PATH",
        "DYLD_INSERT_LIBRARIES",
        "DYLD_LIBRARY_PATH",
        "LD_PRELOAD",
        "PYTHONHOME",
        "PYTHONPATH",
        "PYTHONSTARTUP",
    }
)
_EXTERNAL_TOOLS: Final = {
    "basedpyright": "basedpyright",
    "contracts": "crosshair",
    "pylint": "pylint",
    "radon": "radon",
    "ruff": "ruff",
    "semgrep-bugs": "semgrep",
    "semgrep-clean": "semgrep",
    "targeted-pytest-coverage": "pytest",
}
_MEMBERS: Final = frozenset({"ai-bloat-ast", "ast-clean-code", *_EXTERNAL_TOOLS})
_MAX_PATHS: Final = 100_000
_MAX_PATH_BYTES: Final = 240
_MAX_REQUEST_BYTES: Final = 16 << 20
_MAX_ADAPTER_ARGUMENTS: Final = 128
_MAX_ARGUMENT_BYTES: Final = 1024
_MAX_PROCESS_ARGUMENT_BYTES: Final = 64 << 10
_MAX_REPLIES: Final = 128
_MAX_PROCESS_OUTPUT_BYTES: Final = 4 << 20
_CONFIG_PATH = re.compile(r"/opt/specfact/config/[1-9][0-9]*/[A-Za-z0-9_.-]+\Z")
_PYLINT_OPTION = re.compile(r"--[a-z][a-z0-9-]*=[^\x00\r\n]{0,512}\Z")
_PLUGIN_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.:]*\Z")

Adapter = Callable[[list[Path]], list[ReviewFinding]]
ManagedRun = Callable[..., subprocess.CompletedProcess[str]]
ExternalAdapter = Callable[[list[Path], ManagedRun, list[str], bool, bool], list[ReviewFinding]]
IN_PROCESS_ADAPTERS: dict[str, Adapter] = {
    "ai-bloat-ast": run_ai_bloat,
    "ast-clean-code": run_ast_clean_code,
}


class WorkerContractError(ValueError):
    """The fixed worker invocation, request, or result violated its contract."""


class RequestPending(BaseException):
    """One exact broker request needs a controller result before replay."""

    def __init__(self, request: dict[str, object]) -> None:
        self.request = request


class ReplayContractViolation(BaseException):
    """A supplied reply or adapter launch differs from the immutable plan."""


def _root(raw: str, *, writable: bool, private_tree: bool = False) -> Path:
    path = Path(raw)
    if not path.is_absolute() or path.is_symlink():
        raise WorkerContractError("worker roots must be absolute non-symlink directories")
    resolved = path.resolve(strict=True)
    if not resolved.is_dir() or resolved != path:
        raise WorkerContractError("worker root identity changed during resolution")
    mode = resolved.stat().st_mode
    if private_tree and (not mode & stat.S_IWUSR or mode & (stat.S_IRWXG | stat.S_IRWXO)):
        raise WorkerContractError("private worker root is not owner-only")
    if writable and not private_tree and not mode & stat.S_IWUSR:
        raise WorkerContractError("writable worker root is not owner-writable")
    if not writable and not private_tree and mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
        raise WorkerContractError("immutable worker root is writable")
    return resolved


def _invocation_roots() -> tuple[Path, Path, Path, Path]:
    if len(sys.argv) != 5:
        raise WorkerContractError("worker requires exactly four root arguments")
    capsule = _root(sys.argv[1], writable=True, private_tree=True)
    project = _root(sys.argv[2], writable=False)
    output = _root(sys.argv[3], writable=True)
    temporary = _root(sys.argv[4], writable=True)
    roots = (capsule, project, output, temporary)
    if len(set(roots)) != len(roots) or any(
        left.is_relative_to(right) or right.is_relative_to(left)
        for index, left in enumerate(roots)
        for right in roots[index + 1 :]
    ):
        raise WorkerContractError("worker roots must be distinct and disjoint")
    return roots


def _reject_unsafe_environment() -> None:
    present = sorted(name for name in _UNSAFE_ENVIRONMENT if os.environ.get(name))
    if present:
        raise WorkerContractError(f"unsafe worker environment: {','.join(present)}")


def _read_request(project: Path) -> dict[str, object]:
    request_path = project / _REQUEST_NAME
    if request_path.is_symlink() or not request_path.is_file():
        raise WorkerContractError("request must be a regular project file")
    if request_path.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
        raise WorkerContractError("request file is writable")
    size = request_path.stat().st_size
    if size <= 0 or size > _MAX_REQUEST_BYTES:
        raise WorkerContractError("request size is outside the admitted bound")
    try:
        value = json.loads(request_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkerContractError("request is not canonical UTF-8 JSON") from exc
    if not isinstance(value, dict) or set(value) != _REQUEST_FIELDS:
        raise WorkerContractError("request fields differ from schema v1")
    return cast(dict[str, object], value)


def _safe_relative(value: str) -> bool:
    path = Path(value.split("::", maxsplit=1)[0])
    return bool(value) and not path.is_absolute() and ".." not in path.parts and "\x00" not in value


def _validated_adapter_argv(member: str, raw: object) -> list[str]:
    if (
        not isinstance(raw, list)
        or len(raw) > _MAX_ADAPTER_ARGUMENTS
        or not all(
            isinstance(item, str) and len(item.encode("utf-8")) <= _MAX_ARGUMENT_BYTES and "\x00" not in item
            for item in raw
        )
    ):
        raise WorkerContractError("adapter argv must be a bounded string list")
    argv = cast(list[str], raw)
    if not argv:
        return []
    valid = False
    if member == "ruff":
        valid = argv == ["--isolated", "--no-cache", "--no-force-exclude"] or (
            len(argv) == 4
            and argv[0] == "--config"
            and bool(_CONFIG_PATH.fullmatch(argv[1]))
            and argv[2:] == ["--no-cache", "--no-force-exclude"]
        )
    elif member == "radon":
        valid = argv == ["radon-full-result-v1"]
    elif member in {"semgrep-clean", "semgrep-bugs"}:
        valid = len(argv) == 1 and bool(re.fullmatch(r"/opt/specfact/config/[1-9][0-9]*", argv[0]))
    elif member == "basedpyright":
        valid = len(argv) == 2 and argv[0] == "--project" and bool(_CONFIG_PATH.fullmatch(argv[1]))
    elif member == "pylint":
        valid = (
            len(argv) >= 2
            and argv[0] == "--rcfile"
            and bool(_CONFIG_PATH.fullmatch(argv[1]))
            and all(_PYLINT_OPTION.fullmatch(item) for item in argv[2:])
        )
    elif member == "contracts":
        valid = (
            (len(argv) >= 3 and argv[0] == "contract-inputs-v1")
            and len(argv[1:]) % 2 == 0
            and all(
                flag == "--test-root" and _safe_relative(value)
                for flag, value in zip(argv[1::2], argv[2::2], strict=True)
            )
        )
        valid = valid or (len(argv) == 2 and argv[0] == "contract-inputs-v2" and bool(_CONFIG_PATH.fullmatch(argv[1])))
    elif member == "targeted-pytest-coverage":
        try:
            separator = argv.index("--")
        except ValueError:
            separator = len(argv)
        policy = argv[:separator]
        selectors = argv[separator + 1 :] if separator < len(argv) else []
        valid = (
            len(policy) >= 6
            and policy[:1] == ["-c"]
            and bool(_CONFIG_PATH.fullmatch(policy[1]))
            and policy[2:4] == ["--rootdir", "/opt/specfact/snapshot"]
            and policy[4:5] == ["--cov-config"]
            and bool(_CONFIG_PATH.fullmatch(policy[5]))
            and len(policy[6:]) % 2 == 0
            and all(
                flag == "-p" and bool(_PLUGIN_NAME.fullmatch(plugin))
                for flag, plugin in zip(policy[6::2], policy[7::2], strict=True)
            )
            and all(_safe_relative(selector) for selector in selectors)
        )
    if not valid:
        raise WorkerContractError("adapter argv does not match the fixed member plan")
    return argv


def _request_member(request: dict[str, object]) -> tuple[str, list[str]]:
    member = request["member"]
    if not isinstance(member, str) or member not in _MEMBERS:
        raise WorkerContractError("request member is not in the closed analyzer set")
    if request["schema"] != _REQUEST_SCHEMA:
        raise WorkerContractError("request schema is unsupported")
    if not isinstance(request["bug_hunt"], bool) or not isinstance(request["complete_pytest_inventory"], bool):
        raise WorkerContractError("request flags must be booleans")
    adapter_argv = _validated_adapter_argv(member, request["adapter_argv"])
    if member != "targeted-pytest-coverage" and request["complete_pytest_inventory"]:
        raise WorkerContractError("complete pytest inventory is invalid for this member")
    return member, adapter_argv


def _materialized_adapter_argv(adapter_argv: list[str], project: Path) -> list[str]:
    materialized: list[str] = []
    config_prefix = "/opt/specfact/config/"
    snapshot_prefix = "/opt/specfact/snapshot"
    for argument in adapter_argv:
        if argument == snapshot_prefix:
            materialized.append(str(project))
        elif argument.startswith(snapshot_prefix + "/"):
            relative = Path(argument.removeprefix(snapshot_prefix + "/"))
            if ".." in relative.parts:
                raise WorkerContractError("snapshot policy path escapes the project")
            materialized.append(str(project / relative))
        elif argument.startswith(config_prefix):
            relative = Path(argument.removeprefix(config_prefix))
            if ".." in relative.parts:
                raise WorkerContractError("configuration policy path escapes the project")
            materialized.append(str(project / ".specfact-native-config" / relative))
        else:
            materialized.append(argument)
    return materialized


def _selected_paths(request: dict[str, object], project: Path) -> tuple[list[Path], list[str]]:
    raw_paths = request["paths"]
    if (
        not isinstance(raw_paths, list)
        or not raw_paths
        or len(raw_paths) > _MAX_PATHS
        or not all(isinstance(item, str) for item in raw_paths)
    ):
        raise WorkerContractError("selected paths are invalid")
    relative_names: list[str] = []
    resolved_paths: list[Path] = []
    for raw in cast(list[str], raw_paths):
        if not raw or len(raw.encode("utf-8")) > _MAX_PATH_BYTES or "\x00" in raw:
            raise WorkerContractError("selected path exceeds its bound")
        relative = Path(raw)
        if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
            raise WorkerContractError("selected path escapes the project")
        candidate = project / relative
        current = project
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise WorkerContractError("selected path contains a symlink")
        if not candidate.is_file():
            raise WorkerContractError("selected path is not a regular file")
        resolved = candidate.resolve(strict=True)
        if not resolved.is_relative_to(project) or resolved != candidate:
            raise WorkerContractError("selected path identity changed during resolution")
        if resolved.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
            raise WorkerContractError("selected project file is writable")
        normalized = relative.as_posix()
        if normalized in relative_names or normalized in {_REQUEST_NAME, _REPLIES_NAME}:
            raise WorkerContractError("selected paths collide")
        relative_names.append(normalized)
        resolved_paths.append(resolved)
    if relative_names != sorted(relative_names):
        raise WorkerContractError("selected paths are not canonical")
    return resolved_paths, relative_names


def _read_replies(project: Path) -> list[dict[str, object]]:
    reply_path = project / _REPLIES_NAME
    if not os.path.lexists(reply_path):
        return []
    if reply_path.is_symlink() or not reply_path.is_file():
        raise WorkerContractError("reply document must be a regular project file")
    if reply_path.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
        raise WorkerContractError("reply document is writable")
    size = reply_path.stat().st_size
    if size <= 0 or size > _MAX_REQUEST_BYTES:
        raise WorkerContractError("reply document size is outside the admitted bound")
    try:
        document = json.loads(reply_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkerContractError("reply document is not UTF-8 JSON") from exc
    if not isinstance(document, dict) or set(document) != {"replies", "schema"}:
        raise WorkerContractError("reply document fields differ from schema v1")
    if document["schema"] != _REPLIES_SCHEMA:
        raise WorkerContractError("reply document schema is unsupported")
    raw_replies = document["replies"]
    if not isinstance(raw_replies, list) or len(raw_replies) > _MAX_REPLIES:
        raise WorkerContractError("reply count exceeds its bound")
    replies: list[dict[str, object]] = []
    identities: set[str] = set()
    for raw in raw_replies:
        if not isinstance(raw, dict) or set(raw) != {"request", "result"}:
            raise WorkerContractError("reply entry fields differ from schema v1")
        request = raw["request"]
        result = raw["result"]
        if not isinstance(request, dict) or not isinstance(result, dict):
            raise WorkerContractError("reply request and result must be objects")
        if set(result) != {"returncode", "stderr", "stdout"}:
            raise WorkerContractError("reply result fields differ from schema v1")
        returncode = result["returncode"]
        if type(returncode) is not int or not -255 <= returncode <= 255:
            raise WorkerContractError("reply return code is invalid")
        for field in ("stdout", "stderr"):
            value = result[field]
            if not isinstance(value, str) or len(value.encode("utf-8")) > _MAX_PROCESS_OUTPUT_BYTES:
                raise WorkerContractError("reply process output exceeds its bound")
        identity = json.dumps(request, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        if identity in identities:
            raise WorkerContractError("duplicate managed-launch reply")
        identities.add(identity)
        replies.append(cast(dict[str, object], raw))
    return replies


class ReplayTransport:
    """Translate trusted adapter run calls into exact controller replay entries."""

    def __init__(
        self,
        *,
        member: str,
        tool: str,
        replies: list[dict[str, object]],
        capsule: Path,
        project: Path,
        temporary: Path,
    ) -> None:
        self.member = member
        self.tool = tool
        self.replies = replies
        self.capsule = capsule
        self.project = project
        self.temporary = temporary
        self.consumed = 0
        self.target_execution: dict[str, object] | None = None

    def _logical_path(self, value: str) -> str:
        normalized = value
        for label, root in (
            ("project", self.project),
            ("capsule", self.capsule),
            ("temporary", self.temporary),
        ):
            normalized = normalized.replace(str(root), label)
            try:
                relative = Path(value).relative_to(root)
            except ValueError:
                continue
            return label if not relative.parts else f"{label}/{relative.as_posix()}"
        if normalized != value:
            return normalized
        if value.startswith(("/opt/specfact/config/", "/opt/specfact/snapshot")):
            return value
        if Path(value).is_absolute():
            raise ReplayContractViolation("adapter requested an absolute host path")
        return value

    def _environment(self, raw: object) -> dict[str, str]:
        if raw is None:
            return {}
        if not isinstance(raw, Mapping) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in raw.items()
        ):
            raise ReplayContractViolation("adapter environment is invalid")
        environment = cast(Mapping[str, str], raw)
        if any(name in environment for name in _UNSAFE_ENVIRONMENT):
            raise ReplayContractViolation("adapter requested an unsafe environment")
        admitted_deltas = {
            "COVERAGE_FILE",
            "HOME",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
            "SEMGREP_SEND_METRICS",
            "SEMGREP_SETTINGS_FILE",
            "XDG_CACHE_HOME",
            "XDG_CONFIG_HOME",
        }
        result: dict[str, str] = {}
        for name, value in sorted(environment.items()):
            if os.environ.get(name) == value:
                continue
            if name not in admitted_deltas:
                raise ReplayContractViolation("adapter environment differs from the closed plan")
            result[name] = self._logical_path(value) if value.startswith("/") else value
        return result

    def run(self, args: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if (
            isinstance(args, str)
            or not args
            or len(args) > _MAX_ADAPTER_ARGUMENTS
            or any(
                not isinstance(argument, str)
                or "\x00" in argument
                or len(argument.encode("utf-8")) > _MAX_PROCESS_ARGUMENT_BYTES
                for argument in args
            )
        ):
            raise ReplayContractViolation("managed argv is invalid")
        arguments = list(args)
        executable = f"capsule-tool:{self.tool}"
        if arguments[0] != executable:
            raise ReplayContractViolation("adapter requested an unbound executable")
        allowed = {"capture_output", "text", "check", "timeout", "cwd", "env", "encoding", "errors"}
        if set(kwargs) - allowed:
            raise ReplayContractViolation("adapter requested unsupported process options")
        if kwargs.get("capture_output", True) is not True or kwargs.get("text", True) is not True:
            raise ReplayContractViolation("adapter requested unsupported process streams")
        if kwargs.get("encoding", "utf-8") != "utf-8" or kwargs.get("errors", "strict") != "strict":
            raise ReplayContractViolation("adapter requested unsupported output decoding")
        cwd = kwargs.get("cwd", self.project)
        if Path(cast(str | Path, cwd)).resolve() != self.project:
            raise ReplayContractViolation("adapter requested an unbound working directory")
        timeout = kwargs.get("timeout", 5)
        if not isinstance(timeout, int | float) or isinstance(timeout, bool) or not 0 < timeout <= 240:
            raise ReplayContractViolation("adapter timeout is invalid")
        request: dict[str, object] = {
            "argv": [executable, *(self._logical_path(argument) for argument in arguments[1:])],
            "capture_output": True,
            "cwd": "project",
            "environment": self._environment(kwargs.get("env")),
            "member": self.member,
            "schema": "specfact-managed-launch-request-v1",
            "sequence": self.consumed,
            "text": True,
            "timeout_ms": int(timeout * 1000),
            "tool": self.tool,
        }
        if self.consumed >= len(self.replies):
            raise RequestPending(request)
        reply = self.replies[self.consumed]
        if reply["request"] != request:
            raise ReplayContractViolation("managed-launch reply does not match the exact request")
        self.consumed += 1
        result = cast(dict[str, object], reply["result"])
        completed = subprocess.CompletedProcess(
            arguments,
            cast(int, result["returncode"]),
            cast(str, result["stdout"]),
            cast(str, result["stderr"]),
        )
        if kwargs.get("check", False) and completed.returncode:
            raise subprocess.CalledProcessError(
                completed.returncode,
                arguments,
                output=completed.stdout,
                stderr=completed.stderr,
            )
        return completed

    def verify_complete(self) -> None:
        if self.consumed != len(self.replies):
            raise WorkerContractError("controller supplied extra or reordered managed-launch replies")


def _bind_command(tool: str, command: Sequence[str]) -> list[str]:
    if isinstance(command, str) or not command or command[0] != tool:
        raise ReplayContractViolation("adapter executable differs from its fixed tool plan")
    return [f"capsule-tool:{tool}", *command[1:]]


def _tool_available(expected: str, tool: str, _path: Path) -> list[ReviewFinding]:
    if tool != expected:
        raise ReplayContractViolation("adapter availability probe differs from its fixed tool")
    return []


def _proxy(managed_run: ManagedRun) -> SimpleNamespace:
    def reject_popen(*_args: object, **_kwargs: object) -> None:
        raise ReplayContractViolation("Popen streaming is not admitted")

    return SimpleNamespace(
        run=managed_run,
        Popen=reject_popen,
        TimeoutExpired=subprocess.TimeoutExpired,
        CompletedProcess=subprocess.CompletedProcess,
        CalledProcessError=subprocess.CalledProcessError,
    )


def _patched_adapter(module: ModuleType, *, tool: str, managed_run: ManagedRun) -> ExitStack:
    stack = ExitStack()
    if hasattr(module, "analyzer_command"):
        stack.enter_context(patch.object(module, "analyzer_command", lambda command: _bind_command(tool, command)))
    if hasattr(module, "skip_if_tool_missing"):
        stack.enter_context(
            patch.object(
                module,
                "skip_if_tool_missing",
                lambda observed, path, expected=tool: _tool_available(expected, observed, path),
            )
        )
    if hasattr(module, "skip_if_pytest_unavailable"):
        stack.enter_context(patch.object(module, "skip_if_pytest_unavailable", lambda _path: []))
    if hasattr(module, "subprocess"):
        stack.enter_context(patch.object(module, "subprocess", _proxy(managed_run)))
    return stack


def _native_contract_roots(argv: list[str], project: Path) -> tuple[Path, ...]:
    """Read only a bounded sealed inventory under the materialized config grant."""
    if argv[:1] != ["contract-inputs-v2"]:
        return tuple(Path(value) for value in argv[2::2])
    if len(argv) != 2:
        raise WorkerContractError("invalid native contract manifest request")
    path = Path(argv[1])
    if not path.is_relative_to(project / ".specfact-native-config") or path.is_symlink():
        raise WorkerContractError("contract inventory escapes the sealed config grant")
    with path.open("rb") as handle:
        payload = handle.read(_MAX_REQUEST_BYTES + 1)
    if len(payload) > _MAX_REQUEST_BYTES:
        raise WorkerContractError("contract inventory exceeds its admitted byte limit")
    document = json.loads(payload)
    if (
        not isinstance(document, dict)
        or set(document) != {"schema", "test_roots"}
        or document["schema"] != "contract-inputs-v2"
    ):
        raise WorkerContractError("invalid native contract inventory schema")
    roots = document["test_roots"]
    if (
        not isinstance(roots, list)
        or len(roots) > _MAX_PATHS
        or any(
            not isinstance(root, str) or len(root.encode()) > _MAX_PATH_BYTES or not _safe_relative(root) or root == "."
            for root in roots
        )
    ):
        raise WorkerContractError("invalid native contract inventory paths")
    return tuple(Path(value) for value in roots)


def _standard_external_adapter(
    member: str,
    paths: list[Path],
    managed_run: ManagedRun,
    adapter_argv: list[str],
    bug_hunt: bool,
    _complete_pytest_inventory: bool,
) -> list[ReviewFinding]:
    modules = {
        "basedpyright": ("specfact_code_review.tools.basedpyright_runner", "run_basedpyright"),
        "contracts": ("specfact_code_review.tools.contract_runner", "run_contract_check"),
        "pylint": ("specfact_code_review.tools.pylint_runner", "run_pylint"),
        "radon": ("specfact_code_review.tools.radon_runner", "run_radon"),
        "ruff": ("specfact_code_review.tools.ruff_runner", "run_ruff"),
    }
    module_name, function_name = modules[member]
    module = import_module(module_name)
    with _patched_adapter(module, tool=_EXTERNAL_TOOLS[member], managed_run=managed_run):
        function = getattr(module, function_name)
        if member in {"ruff", "basedpyright", "pylint"}:
            return cast(list[ReviewFinding], function(paths, extra_args=tuple(adapter_argv)))
        if member == "radon":
            return cast(list[ReviewFinding], function(paths, full_result=bool(adapter_argv)))
        if member == "contracts":
            transport = cast(ReplayTransport, getattr(managed_run, "__self__", None))
            test_roots = _native_contract_roots(adapter_argv, transport.project) if adapter_argv else ()
            crosshair_files = [
                path
                for path in paths
                if path.suffix == ".py"
                and not any(
                    path.relative_to(transport.project) == root
                    or path.relative_to(transport.project).is_relative_to(root)
                    for root in test_roots
                )
            ]
            return cast(
                list[ReviewFinding],
                function(paths, bug_hunt=bug_hunt, crosshair_files=crosshair_files),
            )
    raise ReplayContractViolation("external adapter dispatch is incomplete")


class _FixedTemporaryDirectory:
    def __init__(self, root: Path, *_args: object, **_kwargs: object) -> None:
        self.root = root

    def __enter__(self) -> str:
        self.root.mkdir(mode=0o700, exist_ok=True)
        return str(self.root)

    def __exit__(self, *_args: object) -> None:
        return None


def _semgrep_external_adapter(
    member: str,
    paths: list[Path],
    managed_run: ManagedRun,
    adapter_argv: list[str],
    _bug_hunt: bool,
    _complete_pytest_inventory: bool,
) -> list[ReviewFinding]:
    module = import_module("specfact_code_review.tools.semgrep_runner")
    transport = cast(ReplayTransport, getattr(managed_run, "__self__", None))
    package_root = Path(__file__).resolve().parents[1]
    if adapter_argv:
        if len(adapter_argv) != 1:
            raise ReplayContractViolation("Semgrep policy projection is invalid")
        package_root = Path(adapter_argv[0])
        if not package_root.is_relative_to(transport.project / ".specfact-native-config"):
            raise ReplayContractViolation("Semgrep policy projection escapes the immutable project")
    elif not package_root.is_relative_to(transport.capsule):
        raise ReplayContractViolation("Semgrep rules are outside the verified capsule")
    temporary = transport.temporary / "semgrep-home"
    with _patched_adapter(module, tool="semgrep", managed_run=managed_run) as stack:
        stack.enter_context(
            patch.object(
                module,
                "tempfile",
                SimpleNamespace(TemporaryDirectory=lambda *args, **kwargs: _FixedTemporaryDirectory(temporary)),
            )
        )
        function_name = "run_semgrep_bugs" if member == "semgrep-bugs" else "run_semgrep"
        return cast(list[ReviewFinding], getattr(module, function_name)(paths, bundle_root=package_root))


def _bind_pytest_private_state(adapter_argv: list[str], temporary: Path) -> list[str]:
    """Insert the one admitted pytest cache override before inventory selectors."""
    try:
        separator = adapter_argv.index("--")
    except ValueError:
        separator = len(adapter_argv)
    return [
        *adapter_argv[:separator],
        "-o",
        f"cache_dir={temporary / 'pytest/cache-dir'}",
        *adapter_argv[separator:],
    ]


def _read_pytest_artifact(path: Path, temporary: Path) -> bytes:
    """Read one bounded ordinary artifact from the confined private state."""
    if not path.is_relative_to(temporary) or path.parent.resolve(strict=True) != path.parent:
        raise WorkerContractError("native pytest artifact path is invalid")
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > 16 << 20:
                raise WorkerContractError("native pytest artifact type or size is invalid")
            with os.fdopen(descriptor, "rb", closefd=False) as stream:
                payload = stream.read((16 << 20) + 1)
            if len(payload) > 16 << 20:
                raise WorkerContractError("native pytest artifact size is invalid")
            return payload
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise WorkerContractError("native pytest artifact is unavailable") from exc


def _capture_pytest_observation(result: Any, transport: ReplayTransport) -> dict[str, object]:
    completed, coverage_path, observer_path, junit_path = result
    coverage = json.loads(_read_pytest_artifact(coverage_path, transport.temporary))
    records = json.loads(_read_pytest_artifact(observer_path, transport.temporary))
    _read_pytest_artifact(junit_path, transport.temporary)
    if not isinstance(coverage, dict) or not isinstance(coverage.get("files"), dict):
        raise WorkerContractError("native pytest coverage artifact is invalid")
    if not isinstance(records, list) or not all(isinstance(record, dict) for record in records):
        raise WorkerContractError("native pytest observer artifact is invalid")
    collected = sorted(
        {
            str(record["nodeid"])
            for record in records
            if record.get("phase") in {"collection", "setup", "call", "teardown"}
        }
    )
    return {
        "collected": collected,
        "records": records,
        "coverage": coverage,
        "process_exit": completed.returncode,
        "result_provenance": "project-origin-v1",
    }


def _pytest_external_adapter(
    paths: list[Path],
    managed_run: ManagedRun,
    adapter_argv: list[str],
    _bug_hunt: bool,
    complete_pytest_inventory: bool,
) -> list[ReviewFinding]:
    module = import_module("specfact_code_review.run.runner")
    transport = cast(ReplayTransport, getattr(managed_run, "__self__", None))
    evidence = transport.temporary / "pytest-evidence"
    evidence.mkdir(mode=0o700, exist_ok=True)
    coverage = evidence / "coverage.json"
    observer = evidence / "observer.json"
    junit = evidence / "junit.xml"
    from specfact_code_review.run.native_analyzer_view import VIEW_NAME

    site_packages = transport.project / VIEW_NAME
    adapter_argv = _bind_pytest_private_state(adapter_argv, transport.temporary)
    projected_test_roots = module._projected_pytest_test_roots

    def native_test_roots(policy_argv: tuple[str, ...]) -> tuple[Path, ...]:
        logical_roots = [str(root) for root in projected_test_roots(policy_argv)]
        return tuple(Path(root) for root in _materialized_adapter_argv(logical_roots, transport.project))

    def native_pytest_environment() -> dict[str, str]:
        environment = dict(os.environ)
        environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        return environment

    execute = module._run_pytest_selection_with_coverage

    def observed_execution(*args: Any, **kwargs: Any) -> Any:
        result = execute(*args, **kwargs)
        transport.target_execution = _capture_pytest_observation(result, transport)
        return result

    with _patched_adapter(module, tool="pytest", managed_run=managed_run) as stack:
        stack.enter_context(patch.object(module, "_run_pytest_selection_with_coverage", observed_execution))
        if complete_pytest_inventory:
            stack.enter_context(patch.object(module, "_projected_pytest_test_roots", native_test_roots))
            stack.enter_context(
                patch.object(
                    module,
                    "_evaluate_complete_tdd_gate",
                    partial(
                        module._evaluate_complete_tdd_gate,
                        snapshot_root=transport.project,
                        allow_project_discovery=True,
                    ),
                )
            )
        stack.enter_context(patch.object(module, "_pytest_python_executable", lambda: "capsule-tool:pytest"))
        stack.enter_context(patch.object(module, "_pytest_in_capsule", lambda: False))
        stack.enter_context(patch.object(module, "_pytest_env", native_pytest_environment))
        stack.enter_context(patch.object(module, "_SOURCE_ROOT", site_packages))
        stack.enter_context(patch.object(module, "_PACKAGE_ROOT", transport.project))
        stack.enter_context(patch.object(module, "_temporary_pytest_evidence_path", lambda suffix: evidence / suffix))
        stack.enter_context(
            patch.object(module, "_temporary_pytest_evidence_paths", lambda: (coverage, observer, junit))
        )
        return cast(
            list[ReviewFinding],
            module._member_findings(
                "targeted-pytest-coverage",
                paths,
                bug_hunt=False,
                adapter_argv=tuple(adapter_argv),
                complete_pytest_inventory=complete_pytest_inventory,
            ),
        )


def _external_adapter(member: str) -> ExternalAdapter:
    if member in {"semgrep-clean", "semgrep-bugs"}:
        return lambda paths, run, argv, bug_hunt, complete: _semgrep_external_adapter(
            member, paths, run, argv, bug_hunt, complete
        )
    if member == "targeted-pytest-coverage":
        return _pytest_external_adapter
    return lambda paths, run, argv, bug_hunt, complete: _standard_external_adapter(
        member, paths, run, argv, bug_hunt, complete
    )


EXTERNAL_ADAPTERS: dict[str, ExternalAdapter] = {member: _external_adapter(member) for member in _EXTERNAL_TOOLS}


def _normalize_findings(raw_findings: object, *, project: Path, selected: set[str]) -> list[dict[str, object]]:
    if not isinstance(raw_findings, list):
        raise WorkerContractError("adapter findings are not a list")
    normalized: list[dict[str, object]] = []
    for raw in raw_findings:
        try:
            finding = ReviewFinding.model_validate(raw)
        except (TypeError, ValidationError) as exc:
            raise WorkerContractError("adapter emitted a malformed finding") from exc
        finding_path = Path(finding.file)
        try:
            relative = (
                finding_path.resolve(strict=True).relative_to(project) if finding_path.is_absolute() else finding_path
            )
        except (OSError, ValueError) as exc:
            raise WorkerContractError("finding path escapes the immutable project") from exc
        name = relative.as_posix()
        if relative.is_absolute() or ".." in relative.parts or name not in selected:
            raise WorkerContractError("finding path is outside selected inputs")
        normalized.append(finding.model_copy(update={"file": name}).model_dump(mode="json"))
    return normalized


def _completed_response(
    member: str,
    raw_findings: object,
    *,
    project: Path,
    selected: set[str],
    target_execution: dict[str, object] | None = None,
) -> dict[str, object]:
    findings = _normalize_findings(raw_findings, project=project, selected=selected)
    unknown = any(item["category"] == "tool_error" for item in findings)
    blocking = any(ReviewFinding.model_validate(item).is_blocking() for item in findings)
    response: dict[str, object] = {
        "diagnostic": "analyzer_reported_incomplete_execution" if unknown else "",
        "evidence_outcome": "UNKNOWN" if unknown else "FAIL" if blocking else "PASS",
        "execution_state": "error" if unknown else "ran",
        "findings": findings,
        "member": member,
    }
    if target_execution is not None:
        response["target_execution"] = target_execution
    return response


def _unknown_response(member: str, diagnostic: str) -> dict[str, object]:
    return {
        "diagnostic": diagnostic,
        "evidence_outcome": "UNKNOWN",
        "execution_state": "error",
        "findings": [],
        "member": member,
    }


def _write_result(output: Path, response: dict[str, object]) -> None:
    destination = output / "result.json"
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("result output already exists")
    temporary = output / f".result.{os.getpid()}.tmp"
    payload = json.dumps(response, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, destination, follow_symlinks=False)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    """Execute one fixed in-process adapter or request broker-managed replay."""

    output: Path | None = None
    member = "unknown"
    try:
        capsule, project, output, temporary = _invocation_roots()
        if {path.name for path in output.iterdir()} - _BROKER_OUTPUTS:
            return EXIT_OUTPUT_COLLISION
        _reject_unsafe_environment()
        request = _read_request(project)
        member, adapter_argv = _request_member(request)
        adapter_argv = _materialized_adapter_argv(adapter_argv, project)
        paths, names = _selected_paths(request, project)
        if member in IN_PROCESS_ADAPTERS:
            try:
                response = _completed_response(
                    member,
                    IN_PROCESS_ADAPTERS[member](paths),
                    project=project,
                    selected=set(names),
                )
            except (OSError, TypeError, ValueError, ValidationError) as exc:
                _write_result(output, _unknown_response(member, f"native_worker_result_invalid:{exc}"))
                return EXIT_INVALID_RESULT
            _write_result(output, response)
            return EXIT_COMPLETE
        transport = ReplayTransport(
            member=member,
            tool=_EXTERNAL_TOOLS[member],
            replies=_read_replies(project),
            capsule=capsule,
            project=project,
            temporary=temporary,
        )
        try:
            findings = EXTERNAL_ADAPTERS[member](
                paths,
                transport.run,
                adapter_argv,
                cast(bool, request["bug_hunt"]),
                cast(bool, request["complete_pytest_inventory"]),
            )
            transport.verify_complete()
            response = _completed_response(
                member, findings, project=project, selected=set(names), target_execution=transport.target_execution
            )
        except RequestPending as pending:
            response = _unknown_response(member, "managed_tool_replay_required")
            response["managed_launch_request"] = pending.request
            _write_result(output, response)
            print(json.dumps(pending.request, separators=(",", ":"), sort_keys=True), flush=True)
            return EXIT_REPLAY_REQUIRED
        except ReplayContractViolation as exc:
            _write_result(output, _unknown_response(member, f"native_worker_request_invalid:{exc}"))
            return EXIT_INVALID_REQUEST
        _write_result(output, response)
        return EXIT_COMPLETE
    except FileExistsError:
        return EXIT_OUTPUT_COLLISION
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        if output is not None and not ({path.name for path in output.iterdir()} - _BROKER_OUTPUTS):
            try:
                _write_result(output, _unknown_response(member, f"native_worker_request_invalid:{exc}"))
            except (FileExistsError, OSError):
                return EXIT_OUTPUT_COLLISION
        return EXIT_INVALID_REQUEST


if __name__ == "__main__":
    raise SystemExit(main())
