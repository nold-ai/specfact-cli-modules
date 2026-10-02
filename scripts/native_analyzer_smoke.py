#!/usr/bin/env python3
"""Controlled maintainer smoke; never a production backend or sandbox receipt.

Run: /absolute/python scripts/native_analyzer_smoke.py --config /absolute/config.json
Config: {"python": "/absolute/venv/bin/python", "tools": {"ruff": "/absolute/ruff",
"radon": "/absolute/radon", "semgrep": "/absolute/semgrep", "pylint": "/absolute/pylint",
"crosshair": "/absolute/crosshair"}, "node": "/payload/bin/node",
"basedpyright_js": "/payload/basedpyright/index.js",
"system_tools": {"uname": "/usr/bin/uname"}, "ca_bundle": "/absolute/certifi/cacert.pem"}.
Missing members fail independently. Only embedded harmless fixtures are targets.
No installation, PATH discovery, customer targets, or production selection occurs.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import os
import platform
import select
import signal
import subprocess
import sys
import tempfile
import time
from contextlib import ExitStack, chdir, closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "packages/specfact-code-review/src"
BUNDLE = SOURCE / "specfact_code_review"
# Member -> real adapter module, function, expected defective diagnostic.
MEMBERS = {
    "ruff": ("ruff_runner", "run_ruff", "F821"),
    "radon": ("radon_runner", "run_radon", "CC13"),
    "semgrepclean": ("semgrep_runner", "run_semgrep", "print-in-src"),
    "semgrepbugs": ("semgrep_runner", "run_semgrep_bugs", "specfact-bugs-eval-exec"),
    "aibloat": ("ai_bloat_runner", "run_ai_bloat", "ai-bloat.verbose-bool-return"),
    "astclean": ("ast_clean_code_runner", "run_ast_clean_code", "yagni.unused-private-helper"),
    "basedpyright": ("basedpyright_runner", "run_basedpyright", "reportAssignmentType"),
    "contracts": ("contract_runner", "run_contract_check", "CROSSHAIR_COUNTEREXAMPLE"),
    "pylint": ("pylint_runner", "run_pylint", "E0602"),
    "pytestcoverage": ("runner", "_evaluate_pytest_execution", "TEST_COVERAGE_LOW"),
}
TOOL_NAMES = frozenset({"ruff", "radon", "semgrep", "pylint", "crosshair"})
CLEAN = (
    '"""Harmless native smoke fixture."""\n\ndef increment(value: int) -> int:\n'
    '    """Increment a value."""\n    return value + 1\n'
)
DEFECTS = {
    "ruff": "def increment(value):\n    return missing_name + value\n",
    "radon": "def count_matches(value: int) -> int:\n    total = 0\n"
    + "".join(f"    if value == {index}:\n        total += 1\n" for index in range(12))
    + "    return total\n",
    "semgrepclean": "def announce():\n    print('native smoke')\n",
    "semgrepbugs": "def constant():\n    return eval('1 + 1')\n",
    "aibloat": "def positive(value: int) -> bool:\n    if value > 0:\n        return True\n    return False\n",
    "astclean": "def _unused_increment(value: int) -> int:\n    return value + 1\n",
    "basedpyright": 'count: int = "wrong"\n',
    "contracts": (
        "from icontract import ensure\n\n@ensure(lambda result: result > 0)\n"
        "def positive(value: int) -> int:\n    return value\n"
    ),
    "pylint": "def increment(value):\n    return missing_name + value\n",
    "pytestcoverage": CLEAN + "\ndef untested(value):\n    answer = value + 2\n    answer += 3\n    return answer\n",
}
CONTRACT_CLEAN = (
    "from icontract import ensure\n\n@ensure(lambda result: result > 0)\n"
    "def positive(value: int) -> int:\n    return 1\n"
)


def absolute_file(value: object, *, executable: bool = False) -> str:
    """Validate a configured path without resolving venv interpreter symlinks."""
    if not isinstance(value, str) or not Path(value).is_absolute() or not Path(value).is_file():
        raise ValueError(f"required absolute file is missing: {value!r}")
    if executable and not os.access(value, os.X_OK):
        raise ValueError(f"configured executable is not executable: {value}")
    return value


def validate_config(config: dict) -> dict:
    """Reject target/command injection and ambient executable selection."""
    if not isinstance(config, dict) or set(config) - {
        "python",
        "tools",
        "node",
        "basedpyright_js",
        "system_tools",
        "ca_bundle",
    }:
        raise ValueError("config accepts only python, tools, node, basedpyright_js, system_tools, ca_bundle")
    absolute_file(config.get("python"), executable=True)
    tool_paths = config.get("tools", {})
    if not isinstance(tool_paths, dict) or set(tool_paths) - TOOL_NAMES:
        raise ValueError("tools contains unknown analyzer names")
    helpers = config.get("system_tools", {})
    if not isinstance(helpers, dict) or set(helpers) - {"uname"}:
        raise ValueError("only the explicit uname system helper is supported")
    return config


def command_for(config: dict, tool: str) -> list[str]:
    """Bind every executable, including Node, to a supplied path."""
    if tool == "basedpyright":
        return [absolute_file(config.get("node"), executable=True), absolute_file(config.get("basedpyright_js"))]
    if tool not in TOOL_NAMES:
        raise ValueError(f"unsupported executable: {tool}")
    executable = absolute_file(config.get("tools", {}).get(tool), executable=True)
    # Python console scripts use the supplied interpreter, never their shebang.
    return [executable] if tool == "ruff" else [config["python"], executable]


def assess(clean: list[dict], defective: list[dict], expected: str) -> bool:
    """Require clean evidence and a real diagnostic, never skip/error substitutes."""
    invalid = any(
        row.get("category") == "tool_error"
        or row.get("execution_state") in {"skipped", "error", "missing"}
        or row.get("evidence_outcome") == "UNKNOWN"
        for row in clean + defective
    )
    return not invalid and not clean and any(row.get("rule") == expected for row in defective)


def make_receipt(rows: dict, *, system: str, machine: str) -> dict:
    """All ten members and a native Darwin ARM64 worker are mandatory."""
    members = {name: rows.get(name, {"passed": False, "error": "required member missing"}) for name in MEMBERS}
    return {
        "evidence_kind": "native_compatibility_only",
        "analyzer_ids": {
            name: {
                "semgrepclean": "semgrep-clean",
                "semgrepbugs": "semgrep-bugs",
                "aibloat": "ai-bloat-ast",
                "astclean": "ast-clean-code",
                "pytestcoverage": "targeted-pytest-coverage",
            }.get(name, name)
            for name in MEMBERS
        },
        "execution": "controlled_maintainer_execution",
        "sandbox_verified": False,
        "production_eligible": False,
        "system": system,
        "architecture": machine,
        "os_version": platform.platform(),
        "passed": system == "Darwin"
        and machine == "arm64"
        and all(row.get("passed") is True for row in members.values()),
        "members": members,
    }


def controlled_env(directory: Path, config: dict) -> dict[str, str]:
    """Private writable home; no inherited Python, Node, plugin or tool settings."""
    launchers = directory / "bin"
    launchers.mkdir()
    for name, target in config.get("system_tools", {}).items():
        (launchers / name).symlink_to(absolute_file(target, executable=True))
    environment = {
        "PATH": str(launchers),
        "HOME": str(directory),
        "TMPDIR": str(directory),
        "LANG": "en_US.UTF-8",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "SEMGREP_SEND_METRICS": "off",
        "SEMGREP_ENABLE_VERSION_CHECK": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
    }

    if "ca_bundle" in config:
        environment["SSL_CERT_FILE"] = absolute_file(config["ca_bundle"])
    return environment


def _tool_for_member(member: str) -> str | None:
    return {"semgrepclean": "semgrep", "semgrepbugs": "semgrep", "contracts": "crosshair"}.get(
        member, member if member in TOOL_NAMES or member == "basedpyright" else None
    )


def _versions(config: dict, member: str) -> dict:
    versions = {"python": platform.python_version()}
    tool = _tool_for_member(member)
    if tool == "crosshair":
        command_for(config, tool)
        versions[tool] = importlib.metadata.version("crosshair-tool")
    elif tool:
        result = subprocess.run(
            [*command_for(config, tool), "--version"], capture_output=True, text=True, timeout=30, check=False
        )
        if result.returncode or not result.stdout.strip():
            raise ValueError(
                f"{tool} version probe failed: {result.returncode}: {(result.stderr[:1200] + result.stderr[-800:])}"
            )
        versions[tool] = result.stdout.strip()
    if member == "basedpyright":
        result = subprocess.run([config["node"], "--version"], capture_output=True, text=True, timeout=10, check=True)
        versions["node"] = result.stdout.strip()
    if member == "pytestcoverage":
        versions.update({name: importlib.metadata.version(name) for name in ("pytest", "pytest-cov", "coverage")})
    if member == "contracts":
        z3 = importlib.import_module("z3")

        versions["icontract"] = importlib.metadata.version("icontract")
        versions["z3-solver_distribution"] = importlib.metadata.version("z3-solver")
        versions["z3_runtime"] = z3.get_version_string()
    return versions


def _options(member: str, config: dict) -> dict:
    if member == "ruff":
        return {"extra_args": ("--isolated", "--select", "F821", "--no-cache")}
    if member == "pylint":
        return {"extra_args": ("--rcfile=/dev/null", "--disable=all", "--enable=E0602", "--persistent=n", "--jobs=1")}
    if member.startswith("semgrep"):
        return {"bundle_root": BUNDLE}
    if member == "basedpyright":
        return {"extra_args": ("--pythonpath", config["python"])}
    return {}


def _pytest_findings(runner, path: Path):
    """Exercise the real local pytest observer, reconciliation and coverage gate."""
    (path.parent / "test_fixture.py").write_text(
        "from fixture import increment\n\ndef test_increment():\n    assert increment(1) == 2\n"
    )
    (path.parent / "pytest.ini").write_text("[pytest]\n")
    (path.parent / ".coveragerc").write_text("[run]\nbranch = False\n")
    with patch.object(runner, "_SOURCE_ROOT", SOURCE):
        return runner._evaluate_pytest_execution(  # pylint: disable=protected-access
            # Exercise the released observer without launching the unsupported capsule backend.
            [path],
            lambda: runner._run_pytest_selection_with_coverage(  # pylint: disable=protected-access
                ("test_fixture.py::test_increment",),
                coverage_source=path.parent,
                policy_argv=("-c", "pytest.ini", "--rootdir=.", "--cov-config=.coveragerc"),
            ),
            planned=("test_fixture.py::test_increment",),
            allow_project_omitted_initializers=False,
        )[0]


def valid_exit(member: str, returncode: int) -> bool:
    """Reject operational exits even if an adapter parser accepts the output."""
    if member == "pylint":
        return returncode in {0, 2}  # Only E0602 enabled.
    if member in {"ruff", "basedpyright", "contracts", "pytestcoverage"}:
        return returncode in {0, 1}
    return returncode == 0


def _adapter_findings(config: dict, member: str, path: Path, executions: list[dict]) -> list[dict]:
    module_name, function_name, _ = MEMBERS[member]
    namespace = "run" if member == "pytestcoverage" else "tools"
    adapter = importlib.import_module(f"specfact_code_review.{namespace}.{module_name}")

    def bind(command):
        extra = ["--no-git-ignore", "--metrics=off", "--jobs=1"] if command[0] == "semgrep" else []
        return [*command_for(config, command[0]), *command[1:], *extra]

    def available(tool, _path):
        command_for(config, tool)  # Validation, not a fabricated analyzer result.
        return []

    def execute(command, **kwargs):
        if not Path(command[0]).is_absolute():
            raise ValueError("adapter attempted ambient executable lookup")
        kwargs["timeout"] = min(kwargs.get("timeout", 90), 90)
        check = kwargs.pop("check", False)
        result = subprocess.run(command, check=check, **kwargs)
        executions.append(
            {
                "argv": command,
                "returncode": result.returncode,
                "stdout": result.stdout[-12000:],
                "stderr": result.stderr[-4000:],
            }
        )
        if not valid_exit(member, result.returncode):
            raise ValueError(
                f"unexpected {member} exit: {result.returncode}: {(result.stderr[:1200] + result.stderr[-800:])}"
            )
        return result

    proxy = SimpleNamespace(
        run=execute, TimeoutExpired=subprocess.TimeoutExpired, CompletedProcess=subprocess.CompletedProcess
    )
    with ExitStack() as stack:
        if hasattr(adapter, "analyzer_command"):
            stack.enter_context(patch.object(adapter, "analyzer_command", bind))
        if hasattr(adapter, "skip_if_tool_missing"):
            stack.enter_context(patch.object(adapter, "skip_if_tool_missing", available))
        if hasattr(adapter, "subprocess"):
            stack.enter_context(patch.object(adapter, "subprocess", proxy))
        findings = (
            _pytest_findings(adapter, path)
            if member == "pytestcoverage"
            else getattr(adapter, function_name)([path], **_options(member, config))
        )
    return [finding.model_dump(mode="json") for finding in findings]


def worker(config: dict, member: str) -> dict:
    """Run a single fixed pair inside a dedicated, unsandboxed maintainer process."""
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("native evidence requires Darwin arm64")
    sys.path.insert(0, str(SOURCE))
    row = {"passed": False, "expected_diagnostic": MEMBERS[member][2], "executions": []}
    try:
        row["versions"] = _versions(config, member)
        row["adapter_sha256"] = hashlib.sha256(
            (BUNDLE / ("run" if member == "pytestcoverage" else "tools") / f"{MEMBERS[member][0]}.py").read_bytes()
        ).hexdigest()
        for case in ("clean", "defective"):
            directory = Path.cwd() / case
            directory.mkdir()
            source = (CONTRACT_CLEAN if member == "contracts" else CLEAN) if case == "clean" else DEFECTS[member]
            path = directory / "fixture.py"
            path.write_text(source)
            row[f"{case}_sha256"] = hashlib.sha256(source.encode()).hexdigest()
            with chdir(directory):
                row[case] = _adapter_findings(config, member, path, row["executions"])
        row["passed"] = assess(row["clean"], row["defective"], row["expected_diagnostic"])
        if not row["passed"]:
            row["error"] = "clean fixture findings, incomplete evidence, or expected defect missing"
    except Exception as exc:  # pylint: disable=broad-exception-caught
        # A failing adapter must produce a failed member receipt without losing the other nine.
        row["error"] = f"{type(exc).__name__}: {exc}"
    row["system"], row["architecture"] = platform.system(), platform.machine()
    return row


WORKER_OUTPUT_LIMIT = 16 * 1024 * 1024


def _register_exit_event(events, pid: int) -> bool:
    registration = select.kevent(
        pid,
        filter=select.KQ_FILTER_PROC,
        flags=select.KQ_EV_ADD | select.KQ_EV_ONESHOT,
        fflags=select.KQ_NOTE_EXIT,
    )
    try:
        events.control([registration], 0, 0)
    except ProcessLookupError:
        return False  # Already exited, but still our unreaped child.
    return True


def _exit_observed(events, pid: int, interval: float) -> bool:
    if events is None:
        if os.waitid(os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None:
            return True
        time.sleep(min(interval, 0.01))
        return False
    observed = events.control(None, 1, min(interval, 0.05))
    if not observed:
        return False
    if observed[0].flags & select.KQ_EV_ERROR:
        raise OSError(observed[0].data, "worker exit observation failed")
    return bool(observed[0].fflags & select.KQ_NOTE_EXIT)


def wait_worker_exit(pid: int, timeout: float, streams: tuple) -> None:
    """Observe exit without reaping, including macOS Python without os.waitid."""
    deadline = time.monotonic() + timeout
    with ExitStack() as stack:
        events = stack.enter_context(closing(select.kqueue())) if hasattr(select, "kqueue") else None
        if events is not None and not _register_exit_event(events, pid):
            return
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired("native compatibility worker", timeout)
            if any(os.fstat(stream.fileno()).st_size > WORKER_OUTPUT_LIMIT for stream in streams):
                raise ValueError("worker output limit exceeded")
            if _exit_observed(events, pid, remaining):
                return


def terminate_worker_group(pid: int) -> None:
    """Darwin reports EPERM for an unreaped group containing only zombies."""
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    except PermissionError:
        if sys.platform != "darwin":
            raise
        status = subprocess.run(
            ["/bin/ps", "-g", str(pid), "-o", "stat="], capture_output=True, text=True, timeout=5, check=False
        )
        states = status.stdout.split()
        if status.returncode != 0 or not states or not all(state.startswith("Z") for state in states):
            raise


def run_worker(argv: list[str], *, request_json: str, cwd: str, env: dict[str, str], timeout: float):
    """Bound trusted probes and clean their group before reaping its leader.

    This handles ordinary tool descendants, not sandbox escapes or broker death.
    Exit observation reserves the leader PID until cleanup, avoiding PID reuse.
    """
    with tempfile.TemporaryFile() as request, tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        request.write(request_json.encode())
        request.seek(0)
        # Popen.__exit__ waits without a timeout; retain explicit bounded cleanup instead.
        process = subprocess.Popen(  # pylint: disable=consider-using-with
            argv, stdin=request, stdout=output, stderr=errors, cwd=cwd, env=env, start_new_session=True
        )
        try:
            wait_worker_exit(process.pid, timeout, (output, errors))
        finally:
            try:
                terminate_worker_group(process.pid)
            finally:
                process.wait(timeout=10)
        captured = []
        for stream in (output, errors):
            stream.seek(0)
            data = stream.read(WORKER_OUTPUT_LIMIT + 1)
            if len(data) > WORKER_OUTPUT_LIMIT:
                raise ValueError("worker output limit exceeded")
            captured.append(data.decode("utf-8"))
        return subprocess.CompletedProcess(argv, process.returncode, captured[0], captured[1])


def _probe_member(config: dict, member: str) -> dict:
    try:
        with tempfile.TemporaryDirectory(prefix="native-analyzer-smoke-") as temporary:
            result = run_worker(
                [config["python"], "-I", str(Path(__file__).resolve()), "--worker", member],
                request_json=json.dumps(config),
                cwd=temporary,
                env=controlled_env(Path(temporary), config),
                timeout=240,
            )
            if result.returncode:
                raise ValueError(f"worker failed ({result.returncode}): {result.stderr[-4000:]}")
            return json.loads(result.stdout)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return {"passed": False, "error": str(exc)}


def run_smoke(config: dict) -> dict:
    """Preserve independent member failures while requiring complete evidence."""
    try:
        validate_config(config)
    except ValueError as exc:
        rows = {name: {"passed": False, "error": str(exc)} for name in MEMBERS}
    else:
        rows = {member: _probe_member(config, member) for member in MEMBERS}
    return make_receipt(rows, system=platform.system(), machine=platform.machine())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--config", type=Path)
    modes.add_argument("--worker", choices=MEMBERS, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        result = worker(validate_config(json.load(sys.stdin)), args.worker)
    else:
        result = run_smoke(json.loads(args.config.read_text()))
    sys.stdout.write(json.dumps(result, indent=2) + "\n")
    return 0 if args.worker or result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
