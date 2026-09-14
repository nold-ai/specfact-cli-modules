"""Prepare private dependency artifacts using the verified namespace launcher."""

from __future__ import annotations

import errno
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from icontract import ensure, require
from packaging.specifiers import SpecifierSet

from specfact_code_review.run import sandbox
from specfact_code_review.run.runtime_adapters import MANAGER_REQUIREMENTS, install_commands
from specfact_code_review.run.runtime_artifacts import load_runtime, seal_runtime
from specfact_code_review.run.runtime_compatibility import analyzer_dependency_conflicts
from specfact_code_review.run.runtime_domains import member_dependency_graphs
from specfact_code_review.run.runtime_models import (
    PreparedRuntime,
    ProjectPlan,
    ProjectRuntimeError,
    content_digest,
    document_digest,
)
from specfact_code_review.run.runtime_native import elf_dependencies, inventory_native
from specfact_code_review.run.runtime_sources import IGNORED_INPUTS, source_identity, source_link_target, verify_inputs
from specfact_code_review.run.runtime_vcs import copy_vcs_context


@require(lambda source, destination: source.is_dir() and not destination.exists())
def copy_project(source: Path, destination: Path, *, commit: str = "HEAD") -> None:
    """Copy inputs into private build storage without dereferencing source links."""

    expected = source_identity(source)

    def ignored(directory: str, names: list[str]) -> set[str]:
        excluded = set(names) & IGNORED_INPUTS
        for name in set(names) - excluded:
            path = Path(directory) / name
            if path.is_symlink():
                source_link_target(path, source)
        return excluded

    # Never dereference aliases while reading the source. Validate the complete
    # copied tree before a builder can access it, including concurrent link edits.
    shutil.copytree(source, destination, ignore=ignored, symlinks=True)
    for path in destination.rglob("*"):
        if path.is_symlink():
            original = source / path.relative_to(destination)
            target = source_link_target(original, source)
            path.unlink()
            path.symlink_to(os.path.relpath(destination / target.relative_to(source), path.parent))
    if source_identity(destination) != expected:
        raise ProjectRuntimeError("project_runtime_source_changed_during_copy")
    copy_vcs_context(source, destination, commit)


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
    verify_inputs(plan)
    copy_project(plan.root, staging / "project", commit=plan.vcs.get("commit", "HEAD"))
    if source_identity(staging / "project") != plan.source_identity:
        raise ProjectRuntimeError("project_runtime_source_changed_during_copy")
    if plan.vcs_repository and plan.vcs_repository != plan.root:
        copy_vcs_context(plan.vcs_repository, staging / "project", plan.vcs["commit"])
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
            "#!/opt/specfact/python/bin/python\nimport os,sys\nroot='/opt/specfact/output/b"
            "uilder-tools'\nos.execv(root+'/native/ld-linux-x86-64.so.2', [root+'/native/l"
            "d-linux-x86-64.so.2', '--library-path', root+'/native', root+'/bin/git.real'"
            ", *sys.argv[1:]])\n"
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
            f"project_runtime_prepare_failed:exit={completed.returncode}; "
            f"inspect private build log {staging / 'build.log'}"
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


@require(lambda artifact, destination: artifact != destination)
def publish_artifact(artifact: Path, destination: Path) -> None:
    """Allow a concurrent cache winner, which the caller must fully verify."""
    try:
        os.rename(artifact, destination)
    except OSError as exc:
        if exc.errno not in {errno.EEXIST, errno.ENOTEMPTY}:
            raise


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
                    "runtime_domains.py",
                    "runtime_vcs.py",
                    "target_bootstrap.py",
                    "target_launch.py",
                    "target_pytest.py",
                    "sitecustomize.py",
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
            artifact, capsule_root=runtime.root, declared=plan.native_libraries, target_loader=True
        )
        inventory["analyzer_conflicts"] = analyzer_dependency_conflicts(
            inventory, runtime.root / "opt/specfact/analyzers"
        )
        inventory["member_graphs"] = member_dependency_graphs(inventory, runtime.root / "opt/specfact/analyzers")
        seal_runtime(
            artifact, plan=plan, environment_id=environment, worker_identity=runtime.identity, inventory=inventory
        )
        publish_artifact(artifact, destination)
        # A concurrent preparation must still pass full verification below.
    return load_runtime(descriptor_path, plan=plan, environment_id=environment, worker_identity=runtime.identity)
