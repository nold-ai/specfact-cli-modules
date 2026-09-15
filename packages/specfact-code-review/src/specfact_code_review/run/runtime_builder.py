"""Prepare private dependency artifacts using the verified namespace launcher."""

from __future__ import annotations

import errno
import json
import os
import re
import selectors
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import IO, Any

from icontract import ensure, require
from packaging.specifiers import SpecifierSet

from specfact_code_review.run import sandbox
from specfact_code_review.run.runtime_adapters import MANAGER_REQUIREMENTS, install_commands
from specfact_code_review.run.runtime_artifacts import load_runtime, seal_runtime, validate_build_artifact
from specfact_code_review.run.runtime_compatibility import analyzer_dependency_conflicts
from specfact_code_review.run.runtime_domains import member_dependency_graphs
from specfact_code_review.run.runtime_git import git_identity, stage_git
from specfact_code_review.run.runtime_models import (
    PreparedRuntime,
    ProjectPlan,
    ProjectRuntimeError,
    content_digest,
    document_digest,
)
from specfact_code_review.run.runtime_native import inventory_native
from specfact_code_review.run.runtime_sources import (
    is_excluded_source,
    source_identity,
    source_link_target,
    verify_inputs,
)
from specfact_code_review.run.runtime_vcs import copy_vcs_context


_BUILDER_FILES = (
    "runtime_build_driver.py",
    "runtime_builder.py",
    "runtime_artifacts.py",
    "runtime_native.py",
    "runtime_adapters.py",
    "runtime_domains.py",
    "runtime_vcs.py",
    "runtime_git.py",
    "target_bootstrap.py",
    "target_launch.py",
    "target_pytest.py",
    "target_pylint.py",
    "sitecustomize.py",
)
_BUILD_TIMEOUT_SECONDS = 4500


def _stream_builder_output(process: subprocess.Popen[bytes], build_log: IO[bytes], deadline: float) -> None:
    """Drain bounded binary chunks without exposing the destination file to children."""
    assert process.stdout is not None
    os.set_blocking(process.stdout.fileno(), False)
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(process.args, _BUILD_TIMEOUT_SECONDS)
            if not selector.select(remaining):
                raise subprocess.TimeoutExpired(process.args, _BUILD_TIMEOUT_SECONDS)
            try:
                chunk = os.read(process.stdout.fileno(), 65536)
            except BlockingIOError:
                continue
            if not chunk:
                return
            build_log.write(chunk)
            build_log.flush()


def _run_logged_builder(command: list[str], descriptor: int, build_log: IO[bytes]) -> int:
    """Keep the private log inode in the controller while supervising one child."""
    deadline = time.monotonic() + _BUILD_TIMEOUT_SECONDS
    with subprocess.Popen(command, pass_fds=(descriptor,), stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as process:
        try:
            _stream_builder_output(process, build_log, deadline)
            return process.wait(timeout=max(0.0, deadline - time.monotonic()))
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()


@require(lambda source, destination: source.is_dir() and not destination.exists())
def copy_project(source: Path, destination: Path, *, commit: str = "HEAD", include_vcs: bool = True) -> None:
    """Copy inputs into private build storage without dereferencing source links."""

    expected = source_identity(source)

    def ignored(directory: str, names: list[str]) -> set[str]:
        excluded = {name for name in names if is_excluded_source(Path(directory) / name)}
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
    if include_vcs:
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
        "GIT_EXEC_PATH",
        "/opt/specfact/output/builder-tools/git-core",
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


def _build(plan: ProjectPlan, runtime: Any, staging: Path, *, build_log: IO[bytes] | None = None) -> Path:
    verify_inputs(plan)
    copy_project(plan.root, staging / "project", include_vcs=False)
    if source_identity(staging / "project") != plan.source_identity:
        raise ProjectRuntimeError("project_runtime_source_changed_during_copy")
    if plan.vcs:
        copy_vcs_context(
            plan.vcs_repository or plan.root,
            staging / "project",
            plan.vcs["commit"],
            tree=plan.vcs.get("tree"),
            bound_vcs=plan.vcs,
        )
    stage_git(staging)
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
        command = builder_command(runtime, staging=staging, executable=f"/proc/self/fd/{descriptor}")
        if build_log is not None:
            returncode = _run_logged_builder(command, descriptor, build_log)
        else:
            returncode = subprocess.run(
                command,
                pass_fds=(descriptor,),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=_BUILD_TIMEOUT_SECONDS,
            ).returncode
    finally:
        os.close(descriptor)
    if returncode:
        raise ProjectRuntimeError(f"project_runtime_prepare_failed:exit={returncode}")
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


def _public_build_failure_reason(error: BaseException) -> str:
    """Expose stable controller codes without arbitrary exception details or paths."""
    if not isinstance(error, ProjectRuntimeError):
        return type(error).__name__
    code, _, detail = str(error).partition(":")
    code = code.partition(";")[0]
    if re.fullmatch(r"project_[a-z0-9_]+", code) is None:
        return type(error).__name__
    if code == "project_runtime_prepare_failed" and re.fullmatch(r"exit=-?[0-9]+", detail):
        return f"{code}:{detail}"
    return code


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
            "builder": {name: content_digest(Path(__file__).with_name(name).read_bytes()) for name in _BUILDER_FILES},
            "git": git_identity(),
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
        # The exclusive 0600 file is outside the builder's writable staging mount.
        # Never reopen a path supplied by the builder, including for log retention.
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f"failed-{key}-", suffix=".log", dir=cache, delete=False
        ) as build_log:
            try:
                artifact = _build(plan, runtime, staging, build_log=build_log.file)
                validate_build_artifact(artifact)
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                raise ProjectRuntimeError(
                    f"project_runtime_prepare_failed; private log: {build_log.name}; "
                    f"{_public_build_failure_reason(exc)}"
                ) from exc
        try:
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
            # A concurrent preparation must still pass full verification.
            prepared = load_runtime(
                descriptor_path, plan=plan, environment_id=environment, worker_identity=runtime.identity
            )
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            raise ProjectRuntimeError(f"{exc}; private log: {build_log.name}") from exc
    Path(build_log.name).unlink()
    return prepared
