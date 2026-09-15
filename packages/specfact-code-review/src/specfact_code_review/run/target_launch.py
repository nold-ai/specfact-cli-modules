"""Launch target imports with no access to the sealed parent's writable results."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


PROJECT = Path("/opt/specfact/project-runtime")
BUILTIN = Path(globals().get("BUILTIN", "/opt/specfact/builtin"))
CONTEXT = Path(globals().get("CONTEXT", "/opt/specfact/config/python-context"))
DOMAIN_FILES = {
    "project-python": "specfact_code_review/run/target_bootstrap.py",
    "pytest-observe": "specfact_code_review/run/target_pytest.py",
    "pylint": "specfact_code_review/run/target_pylint.py",
    "basedpyright": "specfact_code_review/tools/basedpyright_runner.py",
    "crosshair": "specfact_code_review/tools/contract_runner.py",
}
SEALED = Path("/opt/specfact/analyzers")
MEMBER = Path("/opt/specfact/config/member-analyzers")


def member_mounts(module: str) -> list[str]:
    """Expose a real import directory containing only the verified member closure."""
    if module == "python-argv":
        module = "project-python"
    mounts = ["--tmpfs", str(MEMBER)]
    if module == "project-python":
        return mounts
    descriptor = json.loads((PROJECT / "project-runtime.json").read_text(encoding="utf-8"))
    graph = descriptor["inventory"]["member_graphs"][module]
    imports = set(graph["sealed_imports"])
    distributions = {row["name"] for row in graph["installed"] if row["origin"] == "analyzer"}
    for entry in sorted(SEALED.iterdir()):
        if entry.name.endswith(".dist-info"):
            admitted = (
                re.sub(r"[-_.]+", "-", entry.name.removesuffix(".dist-info").rsplit("-", 1)[0]).lower() in distributions
            )
        else:
            admitted = entry.name.split(".", maxsplit=1)[0] in imports
        if admitted:
            mounts.extend(["--ro-bind", str(entry), str(MEMBER / entry.name)])
    return mounts


def execution_domain() -> str:
    """Read the inherited member identity; environment variables cannot change it."""
    for module, relative in DOMAIN_FILES.items():
        try:
            if CONTEXT.samefile(BUILTIN / relative):
                return module
        except OSError:
            continue
    raise RuntimeError("project_python_context_missing_or_invalid; launch Python inside an attached target worker")


def interpreter_command(arguments: list[str]) -> list[str]:
    """Enter the target native loader domain while keeping the signed Python binary."""
    python = "/opt/specfact/python/bin/python"
    loader = PROJECT / "native/ld-linux-x86-64.so.2"
    if loader.is_file():
        return [str(loader), "--library-path", str(loader.parent), python, *arguments]
    return [python, *arguments]


def target_command(module: str, arguments: list[str]) -> list[str]:
    """Separate PID/mount/network domains before any customer Python executes."""
    return [
        "/opt/specfact/bin/bwrap-static",
        "--die-with-parent",
        "--new-session",
        "--unshare-all",
        "--ro-bind",
        "/",
        "/",
        "--tmpfs",
        "/opt/specfact/output",
        "--tmpfs",
        "/opt/specfact/config",
        "--tmpfs",
        "/opt/specfact/control",
        "--tmpfs",
        "/tmp",
        "--ro-bind",
        "/opt/specfact/project-runtime/worker-config",
        "/etc",
        "--bind",
        "/opt/specfact/tmp",
        "/opt/specfact/tmp",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        *member_mounts(module),
        "--ro-bind",
        str(BUILTIN / DOMAIN_FILES.get(module, DOMAIN_FILES["project-python"])),
        str(CONTEXT),
        "--clearenv",
        "--setenv",
        "HOME",
        "/opt/specfact/tmp/home",
        "--setenv",
        "TMPDIR",
        "/opt/specfact/tmp",
        "--setenv",
        "PATH",
        "/opt/specfact/project-runtime/bin:/opt/specfact/python/bin:/opt/specfact/analyzers/bin",
        "--setenv",
        "COVERAGE_FILE",
        "/opt/specfact/tmp/.coverage",
        "--setenv",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
        "1",
        "--setenv",
        "SPECFACT_TARGET_PYTEST",
        "1" if module == "pytest-observe" else "0",
        "--chdir",
        "/opt/specfact/snapshot",
        *interpreter_command(
            ["-I", "-S", "/opt/specfact/builtin/specfact_code_review/run/target_bootstrap.py", module, *arguments]
        ),
    ]


def main() -> None:
    # This generated executable is called only from an already isolated worker.
    # First-entry callers always use target_command and cannot select this via env.
    command = interpreter_command(
        ["-I", "-S", str(BUILTIN / DOMAIN_FILES["project-python"]), "python-argv", *sys.argv[1:]]
    )
    os.execv(command[0], command)


if __name__ == "__main__":
    main()
