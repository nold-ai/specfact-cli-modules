"""Stage Git's HTTP transport and native closure for the disposable builder."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from icontract import ensure, require

from specfact_code_review.run.runtime_models import ProjectRuntimeError, content_digest
from specfact_code_review.run.runtime_native import elf_dependencies, inventory_native


GIT = Path("/usr/bin/git")
BUILDER_ROOT = "/opt/specfact/output/builder-tools"


def _programs() -> dict[str, Path]:
    if not GIT.is_file():
        raise ProjectRuntimeError("project_builder_tool_missing:git; install Git on the builder")
    result = subprocess.run(
        [str(GIT), "--exec-path"], env={"PATH": "/usr/bin:/bin"}, capture_output=True, text=True, check=True, timeout=10
    )
    directory = Path(result.stdout.strip())
    programs = {"bin/git": GIT}
    for name in ("git-remote-http", "git-remote-https"):
        path = directory / name
        if not path.is_file():
            raise ProjectRuntimeError(f"project_builder_tool_missing:{name}; install Git HTTP transport helpers")
        programs[f"git-core/{name}"] = path
    return programs


@ensure(lambda result: all(value.startswith("sha256:") and len(value) == 71 for value in result.values()))
def git_identity() -> dict[str, str]:
    """Bind available transport helpers as well as the main executable."""
    if not GIT.is_file():
        return {}
    # Inspection and offline cache lookup must remain usable on non-Linux hosts.
    if not GIT.read_bytes().startswith(b"\x7fELF"):
        return {"bin/git": content_digest(GIT.read_bytes())}
    return {name: content_digest(path.read_bytes()) for name, path in _programs().items()}


@require(lambda staging: staging.is_dir())
def stage_git(staging: Path) -> None:
    """Give each Git program the matching private loader and library search path."""
    root = staging / "builder-tools"
    needed = {"ld-linux-x86-64.so.2"}
    for name, source in _programs().items():
        if not source.read_bytes().startswith(b"\x7fELF"):
            raise ProjectRuntimeError(f"project_builder_tool_not_elf:{name}")
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        executable = target.with_name(target.name + ".real")
        shutil.copyfile(source, executable)
        executable.chmod(0o755)
        needed.update(elf_dependencies(source))
        target.write_text(
            "#!/opt/specfact/python/bin/python\nimport os,sys\n"
            f"root={BUILDER_ROOT!r}\n"
            "os.environ['GIT_EXEC_PATH']=root+'/git-core'\n"
            "loader=root+'/native/ld-linux-x86-64.so.2'\n"
            f"os.execv(loader, [loader, '--library-path', root+'/native', root+'/{name}.real', *sys.argv[1:]])\n"
        )
        target.chmod(0o755)
    inventory_native(root, capsule_root=staging / "no-capsule-libraries", declared=tuple(sorted(needed)))
