"""Prepare private dependency artifacts using the verified namespace launcher."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any

from icontract import ensure, require
from packaging.specifiers import SpecifierSet

from specfact_code_review.run import sandbox
from specfact_code_review.run.runtime_adapters import MANAGER_REQUIREMENTS, install_commands
from specfact_code_review.run.runtime_artifacts import load_runtime, seal_runtime
from specfact_code_review.run.runtime_compatibility import analyzer_dependency_conflicts
from specfact_code_review.run.runtime_models import (
    PreparedRuntime,
    ProjectPlan,
    ProjectRuntimeError,
    content_digest,
    document_digest,
)
from specfact_code_review.run.runtime_native import elf_dependencies, inventory_native
from specfact_code_review.run.runtime_sources import IGNORED_INPUTS, verify_inputs


@require(lambda source, destination: source.is_dir() and not destination.exists())
def copy_project(source: Path, destination: Path) -> None:
    """Copy inputs into private build storage without dereferencing source links."""

    def ignored(directory: str, names: list[str]) -> set[str]:
        excluded = set(names) & IGNORED_INPUTS
        for name in set(names) - excluded:
            path = Path(directory) / name
            if path.is_symlink():
                try:
                    target = path.resolve(strict=True)
                except (OSError, RuntimeError) as exc:
                    raise ProjectRuntimeError(f"project_source_symlink_invalid:{path}") from exc
                if not target.is_relative_to(source) or target == source or path.is_relative_to(target):
                    raise ProjectRuntimeError(f"project_source_symlink_escape:{path}")
        return excluded

    shutil.copytree(source, destination, ignore=ignored)
    if (source / ".git").exists():
        with tempfile.TemporaryDirectory(prefix="specfact-build-git-", dir=destination.parent) as directory:
            clone = Path(directory) / "clone"
            completed = subprocess.run(
                [
                    "git",
                    "-c",
                    "core.hooksPath=/dev/null",
                    "clone",
                    "--quiet",
                    "--no-hardlinks",
                    "--no-checkout",
                    str(source),
                    str(clone),
                ],
                capture_output=True,
                check=False,
                timeout=120,
            )
            if completed.returncode:
                raise ProjectRuntimeError("project_git_snapshot_failed")
            shutil.move(str(clone / ".git"), destination / ".git")
        (destination / ".git/config").write_text(
            "[core]\nrepositoryformatversion = 0\nbare = false\nhooksPath = /dev/null\n", encoding="utf-8"
        )
        shutil.rmtree(destination / ".git/hooks", ignore_errors=True)


@ensure(lambda result: "--clearenv" in result and "--unshare-all" in result)
def builder_command(runtime: Any, *, staging: Path, executable: str) -> list[str]:
    """Construct a private network-enabled acquisition namespace, not an analyzer launch."""
    command = [
        executable,
        "--die-with-parent",
        "--new-session",
        "--unshare-all",
        "--share-net",
        "--ro-bind",
        str(runtime.root),
        "/",
        "--bind",
        str(staging),
        "/opt/specfact/output",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--clearenv",
        "--setenv",
        "HOME",
        "/opt/specfact/output/home",
        "--setenv",
        "TMPDIR",
        "/tmp",
        "--setenv",
        "PATH",
        "/opt/specfact/output/builder-tools/bin:/opt/specfact/python/bin:/usr/bin:/bin",
        "--setenv",
        "GIT_CONFIG_NOSYSTEM",
        "1",
        "--setenv",
        "SSL_CERT_FILE",
        "/etc/ssl/certs/ca-certificates.crt",
        "--chdir",
        "/opt/specfact/output/project",
    ]
    for path in ("/etc/resolv.conf", "/etc/ssl/certs"):
        if Path(path).exists():
            command.extend(("--ro-bind", path, path))
    command.extend((runtime.interpreter, "/opt/specfact/output/build_driver.py"))
    return command


def _build(plan: ProjectPlan, runtime: Any, staging: Path) -> Path:
    copy_project(plan.root, staging / "project")
    if (staging / "project/.git").is_dir():
        git = Path("/usr/bin/git")
        if not git.is_file():
            raise ProjectRuntimeError("project_builder_tool_missing:git; install Git on the builder")
        builder_tools = staging / "builder-tools"
        (builder_tools / "bin").mkdir(parents=True)
        shutil.copyfile(git, builder_tools / "bin/git.real")
        (builder_tools / "bin/git.real").chmod(0o755)
        inventory_native(
            builder_tools,
            capsule_root=staging / "no-capsule-libraries",
            declared=(*elf_dependencies(git), "ld-linux-x86-64.so.2"),
        )
        (builder_tools / "native/ld-linux-x86-64.so.2").chmod(0o755)
        (builder_tools / "bin/git").write_text(
            "#!/opt/specfact/python/bin/python\nimport os,sys\nroot='/opt/specfact/output/builder-tools'\nos.execv(root+'/native/ld-linux-x86-64.so.2', [root+'/native/ld-linux-x86-64.so.2', '--library-path', root+'/native', root+'/bin/git.real', *sys.argv[1:]])\n"
        )
        (builder_tools / "bin/git").chmod(0o755)
    (staging / "home").mkdir()
    driver = Path(__file__).with_name("runtime_build_driver.py")
    shutil.copyfile(driver, staging / "build_driver.py")
    config = {
        "manager": plan.manager,
        "environment": plan.environment,
        "interpreter": runtime.interpreter,
        "manager_requirements": MANAGER_REQUIREMENTS[plan.manager],
        "commands": install_commands(plan, python="/opt/specfact/output/tools/bin/python"),
    }
    (staging / "build.json").write_text(json.dumps(config), encoding="utf-8")
    descriptor = sandbox._verified_bubblewrap_descriptor(runtime.root, runtime.bubblewrap)
    try:
        completed = subprocess.run(
            builder_command(runtime, staging=staging, executable=f"/proc/self/fd/{descriptor}"),
            pass_fds=(descriptor,),
            capture_output=True,
            text=True,
            check=False,
            timeout=4500,
        )
    finally:
        os.close(descriptor)
    if completed.returncode:
        with (staging / "build.log").open("a", encoding="utf-8") as stream:
            stream.write(completed.stdout + completed.stderr)
        # Build logs stay private; repository-controlled errors may contain index credentials.
        raise ProjectRuntimeError(
            f"project_runtime_prepare_failed:exit={completed.returncode}; inspect private build log {staging / 'build.log'}"
        )
    if not (staging / "artifact/site-packages").is_dir():
        raise ProjectRuntimeError("project_runtime_prepare_incomplete")
    return staging / "artifact"


def _validate_python(plan: ProjectPlan, environment: str) -> None:
    lock = json.loads(
        (Path(__file__).parents[1] / "resources/contracts/pr-range-v1-toolchain-lock.json").read_text(encoding="utf-8")
    )
    versions = {row["environment_id"]: row["python_version"] for row in lock["environments"]}
    version = versions.get(environment)
    if version is None or (plan.requires_python and version not in SpecifierSet(plan.requires_python)):
        raise ProjectRuntimeError(f"project_python_incompatible:{environment}:{plan.requires_python}")
    if plan.python and not (version == plan.python or version.startswith(plan.python + ".")):
        raise ProjectRuntimeError(f"project_python_incompatible:{version}:{plan.python}")


@ensure(lambda result, plan: result.descriptor["project_identity"] == plan.identity)
def prepare_runtime(
    plan: ProjectPlan,
    *,
    runtime: Any,
    cache_root: Path | None = None,
    offline: bool = False,
) -> PreparedRuntime:
    """Build or validate reusable local dependencies for the exact capsule ABI."""
    environment = str(runtime.environment_id)
    _validate_python(plan, environment)
    cache = cache_root or Path.home() / ".cache/specfact/code-review/project-runtimes-v2"
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    if cache.is_symlink():
        raise ProjectRuntimeError("project_runtime_cache_symlink")
    key = document_digest(
        {
            "project": plan.identity,
            "environment": environment,
            "worker": runtime.identity,
            "manager": MANAGER_REQUIREMENTS[plan.manager],
            "builder": {
                name: content_digest(Path(__file__).with_name(name).read_bytes())
                for name in (
                    "runtime_build_driver.py",
                    "runtime_builder.py",
                    "runtime_native.py",
                    "runtime_adapters.py",
                )
            },
            "git": content_digest(Path("/usr/bin/git").read_bytes()) if Path("/usr/bin/git").is_file() else None,
        }
    )[7:]
    destination = cache / key
    descriptor_path = destination / "project-runtime.json"
    if destination.exists():
        return load_runtime(descriptor_path, plan=plan, environment_id=environment, worker_identity=runtime.identity)
    if offline:
        raise ProjectRuntimeError("project_runtime_offline_cache_miss: run runtime prepare with network first")
    with tempfile.TemporaryDirectory(prefix=".preparing-", dir=cache) as directory:
        staging = Path(directory)
        try:
            artifact = _build(plan, runtime, staging)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            log = staging / "build.log"
            retained = cache / f"failed-{key}.log"
            if log.is_file():
                shutil.copyfile(log, retained)
                retained.chmod(0o600)
            raise ProjectRuntimeError(
                f"project_runtime_prepare_failed; private log: {retained}; {type(exc).__name__}"
            ) from exc
        verify_inputs(plan)
        inventory = json.loads((artifact / "inventory.json").read_text(encoding="utf-8"))
        inventory["native_libraries"] = inventory_native(
            artifact, capsule_root=runtime.root, declared=plan.native_libraries
        )
        inventory["analyzer_conflicts"] = analyzer_dependency_conflicts(
            inventory, runtime.root / "opt/specfact/analyzers"
        )
        seal_runtime(
            artifact, plan=plan, environment_id=environment, worker_identity=runtime.identity, inventory=inventory
        )
        with suppress(FileExistsError):
            os.rename(artifact, destination)
        # A concurrent preparation must still pass full verification below.
    return load_runtime(descriptor_path, plan=plan, environment_id=environment, worker_identity=runtime.identity)
