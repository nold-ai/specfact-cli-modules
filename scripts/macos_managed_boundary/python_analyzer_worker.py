"""Trusted staged analyzer worker, copied into the immutable candidate payload."""

from __future__ import annotations

import contextlib
import importlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


# This file runs only as -I -S -B in the signed traced fixture.
TRUSTED = Path(__file__).resolve().parent
PAYLOAD = TRUSTED.parent
sys.path[:0] = [str(PAYLOAD / "site-packages"), str(TRUSTED)]
from managed_subprocess import (  # noqa: E402  # Frozen -S import domain is established first.
    ManagedRun,
    UnadaptedProcessError,
)


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


class RequestPending(BaseException):
    pass


def main():
    request_path = Path(sys.argv[1])
    config = json.loads(request_path.read_text())
    stage = request_path.parent
    io = stage / "io"
    (io / "python-entry.json").write_text(
        json.dumps({"pid": os.getpid(), "entry_ns": time.clock_gettime_ns(time.CLOCK_MONOTONIC)})
    )
    assert sys.implementation.name == "cpython" and sys.flags.isolated and sys.flags.no_site
    assert sys.version_info[:2] == tuple(config["abi"])
    if config["kind"] == "tool":
        argv = config["argv"]
        sys.argv = argv
        sys.path.append(str(Path.cwd()))  # Project code belongs only in this tool domain.
        try:
            if config["tool"] == "pytestcoverage":
                sys.argv = ["-c", *argv[3:]]
                exec(compile(argv[2], "<trusted-pytest-observer>", "exec"), {"__name__": "__main__"})
            else:
                module, attribute = {
                    "radon": ("radon", "main"),
                    "pylint": ("pylint", "run_pylint"),
                    "contracts": ("crosshair.main", "main"),
                }[config["tool"]]
                sys.argv = [config["tool"], *argv[1:]]
                result = getattr(importlib.import_module(module), attribute)()
                return result or 0
        except PermissionError as error:
            print("managed subprocess incomplete: kernel-denied operation; no host fallback", file=sys.stderr)
            raise error
        return 0

    member = config["member"]
    module_name, function, expected = MEMBERS[member]
    adapter = importlib.import_module(
        f"specfact_code_review.{'run' if member == 'pytestcoverage' else 'tools'}.{module_name}"
    )
    domain = Path.cwd()
    aliases = {
        str(PAYLOAD / "bin" / tool): tool
        for tool in ("ruff", "radon", "pylint", "contracts", "semgrep", "basedpyright")
    }
    aliases[str(PAYLOAD / "bin" / f"python{config['version']}")] = "pytestcoverage"
    replies = config.get("replies", [])
    requested = []

    def transport(request):
        index = len(requested)
        requested.append(request)
        if index < len(replies):
            reply = replies[index]
            if request != reply["request"]:
                raise UnadaptedProcessError("replayed request does not match immutable plan")
            return reply["result"]
        (io / "pending.json").write_text(json.dumps(request))
        raise RequestPending()

    def bind(command):
        tool = {"crosshair": "contracts"}.get(command[0], command[0])
        if not isinstance(tool, str):
            raise UnadaptedProcessError("invalid analyzer name")
        return [str(PAYLOAD / "bin" / tool), *command[1:]]

    def available(tool, _path):
        if tool not in ("ruff", "radon", "semgrep", "basedpyright", "pylint", "crosshair"):
            raise UnadaptedProcessError("unknown analyzer availability request")
        return []

    def execute(command, **kwargs):
        # Bind environment after trusted adapter construction, with no untrusted
        # arbitrary env accepted by ManagedRun. Parent records/validates request.
        env = kwargs.get("env", {})
        if any(key in env for key in ("DYLD_INSERT_LIBRARIES", "PYTHONSTARTUP", "LD_PRELOAD")):
            raise UnadaptedProcessError("unsafe adapter environment")
        runner = ManagedRun(aliases, transport, cwd=str(domain), environment=env)
        return runner.run(command, **kwargs)

    proxy = SimpleNamespace(
        run=execute,
        Popen=ManagedRun.popen,
        TimeoutExpired=subprocess.TimeoutExpired,
        CompletedProcess=subprocess.CompletedProcess,
        CalledProcessError=subprocess.CalledProcessError,
    )
    options = {
        "ruff": {"extra_args": ("--isolated", "--select", "F821", "--no-cache")},
        "pylint": {
            "extra_args": ("--rcfile=/dev/null", "--disable=all", "--enable=E0602", "--persistent=n", "--jobs=1")
        },
    }
    if member.startswith("semgrep"):
        options[member] = {"bundle_root": TRUSTED / "specfact_code_review"}
    if member == "basedpyright":
        options[member] = {"extra_args": ("--pythonversion", config["version"], "--pythonplatform", "Darwin")}

    class FixedTemporary:
        def __init__(self, *args, **kwargs):
            self.path = domain / "semgrep-scratch"

        def __enter__(self):
            self.path.mkdir(exist_ok=True)
            return str(self.path)

        def __exit__(self, *args):
            return None

    try:
        with contextlib.ExitStack() as stack:
            for name, replacement in (
                ("analyzer_command", bind),
                ("skip_if_tool_missing", available),
                ("subprocess", proxy),
            ):
                if hasattr(adapter, name):
                    stack.enter_context(patch.object(adapter, name, replacement))
            if member.startswith("semgrep"):
                stack.enter_context(
                    patch.object(adapter, "tempfile", SimpleNamespace(TemporaryDirectory=FixedTemporary))
                )
            if member == "pytestcoverage":
                stack.enter_context(patch.object(adapter, "_SOURCE_ROOT", TRUSTED))
                stack.enter_context(
                    patch.object(
                        adapter, "_temporary_pytest_evidence_path", lambda suffix: domain / ("evidence" + suffix)
                    )
                )
                stack.enter_context(
                    patch.object(
                        adapter,
                        "_temporary_pytest_evidence_paths",
                        lambda: (domain / "coverage.json", domain / "observer.json", domain / "junit.xml"),
                    )
                )
                findings = adapter._evaluate_pytest_execution(
                    [domain / "fixture.py"],
                    lambda: adapter._run_pytest_selection_with_coverage(
                        ("test_fixture.py::test_increment",),
                        coverage_source=domain,
                        policy_argv=("-c", "pytest.ini", "--rootdir=.", "--cov-config=.coveragerc"),
                    ),
                    planned=("test_fixture.py::test_increment",),
                    allow_project_omitted_initializers=False,
                )[0]
            else:
                findings = getattr(adapter, function)([domain / "fixture.py"], **options.get(member, {}))
        data = [item.model_dump(mode="json") for item in findings]
        (io / "adapter.json").write_text(json.dumps({"findings": data, "expected": expected, "requests": requested}))
        print("python-adapter-complete", flush=True)
        return 0
    except RequestPending:
        print("python-adapter-request-pending", flush=True)
        return 75


if __name__ == "__main__":
    raise SystemExit(main())
