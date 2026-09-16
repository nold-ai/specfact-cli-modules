"""Capture explicitly requested system capabilities outside disposable builders."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from icontract import ensure

from specfact_code_review.run.runtime_models import ProjectRuntimeError, content_digest, document_digest
from specfact_code_review.run.runtime_native import SYSTEM_LIBRARY_ROOTS, elf_dependencies, inventory_native


PROGRAM_ROOT = Path("/usr/bin")
GIT_HELPER_ROOTS = (Path("/usr/lib/git-core"), Path("/usr/libexec/git-core"))
GIT_HELPER_NAMES = (
    "git-remote-http",
    "git-remote-https",
    "git-upload-pack",
    "git-receive-pack",
    "git-upload-archive",
)
SUPPORTED_TOOLS = frozenset({"git", "uname", "sed"})
_RUNTIME_ROOT = "/opt/specfact/project-runtime/native-tools"


@dataclass(frozen=True)
class CapturedTools:
    """Controller memory owns every byte before the untrusted builder starts."""

    files: dict[str, bytes]
    inventory: dict[str, dict[str, str]]

    @property
    @ensure(lambda result: result.startswith("sha256:") and len(result) == 71)
    def identity(self) -> str:
        """Bind launchers, programs, libraries and sealed external requirements."""
        return document_digest(self.inventory)


@ensure(lambda result: result == tuple(sorted(set(result))))
def validate_native_tools(names: object) -> tuple[str, ...]:
    """Reject unsupported capabilities without searching ambient executable paths."""
    if not isinstance(names, (list, tuple)) or not all(isinstance(name, str) for name in names):
        raise ProjectRuntimeError("project_config_invalid:native_tools must be an array of strings")
    unknown = set(names) - SUPPORTED_TOOLS
    if unknown:
        raise ProjectRuntimeError(
            f"project_native_tool_unsupported:{','.join(sorted(unknown))}; supported: git,sed,uname"
        )
    return tuple(sorted(set(names)))


def _programs(names: tuple[str, ...]) -> dict[str, Path]:
    programs = {name: PROGRAM_ROOT / name for name in names}
    if "git" in names:
        for name in GIT_HELPER_NAMES:
            found = {root.joinpath(name).resolve() for root in GIT_HELPER_ROOTS if (root / name).is_file()}
            if len(found) != 1:
                raise ProjectRuntimeError(f"project_native_tool_missing:{name}; install one Git helper installation")
            programs[f"git-core/{name}"] = found.pop()
    return programs


def _launcher(name: str) -> bytes:
    git_environment = "os.environ['GIT_EXEC_PATH']=root+'/git-core'\nos.environ['GIT_CONFIG_NOSYSTEM']='1'\n"
    text = (
        "#!/opt/specfact/python/bin/python\nimport os,sys\n"
        f"root={_RUNTIME_ROOT!r}\n"
        + (git_environment if name == "git" or name.startswith("git-core/") else "")
        + "loader=root+'/native/ld-linux-x86-64.so.2'\n"
        + f"os.execv(loader,[loader,'--library-path',root+'/native',root+'/executables/{name}',*sys.argv[1:]])\n"
    )
    return text.encode()


def _capture_program(root: Path, name: str, source: Path) -> dict[str, str]:
    if not source.is_file():
        raise ProjectRuntimeError(f"project_native_tool_missing:{name}; install the declared system tool")
    payload = source.read_bytes()
    if not payload.startswith(b"\x7fELF"):
        raise ProjectRuntimeError(f"project_native_tool_not_elf:{name}; Linux x86-64 tooling required")
    target = root / "executables" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    elf_dependencies(target)  # Validate architecture before publishing captured bytes.
    return {"source": str(source.resolve()), "sha256": content_digest(payload)}


def _shell_requirement(capsule_root: Path | None) -> dict[str, str]:
    if capsule_root is None:
        raise ProjectRuntimeError("project_native_tool_shell_missing:git requires the sealed /bin/sh")
    shell = (capsule_root / "bin/sh").resolve()
    if not shell.is_relative_to(capsule_root.resolve()) or not shell.is_file() or not shell.stat().st_mode & 0o111:
        raise ProjectRuntimeError("project_native_tool_shell_missing:git requires the sealed /bin/sh")
    return {"source": "/bin/sh", "sha256": content_digest(shell.read_bytes())}


def _capture_payload(root: Path, programs: dict[str, Path]) -> CapturedTools:
    inventory = {}
    for name, source in programs.items():
        inventory[f"native-tools/executables/{name}"] = _capture_program(root, name, source)
    needed = {"ld-linux-x86-64.so.2"}
    for name in programs:
        needed.update(elf_dependencies(root / "executables" / name))
    libraries = inventory_native(
        root, capsule_root=root / "no-capsule", declared=tuple(sorted(needed)), system_roots=SYSTEM_LIBRARY_ROOTS
    )
    for row in libraries:
        key = "native-tools/" + row["path"]
        inventory.setdefault(key, {"source": row.get("source", "controller-capture"), "sha256": row["sha256"]})
    files = {
        "native-tools/" + path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }
    for name in programs:
        key = "native-tools/" + name if name.startswith("git-core/") else "bin/" + name
        files[key] = _launcher(name)
        inventory[key] = {"source": "generated-controller-launcher", "sha256": content_digest(files[key])}
    return CapturedTools(files, inventory)


@ensure(
    lambda result: all(
        content_digest(payload) == result.inventory[name]["sha256"] for name, payload in result.files.items()
    )
)
def capture_native_tools(names: tuple[str, ...], *, capsule_root: Path | None = None) -> CapturedTools:
    """Snapshot bounded tools and complete ELF closures before cache lookup or builds."""
    selected = validate_native_tools(names)
    if not selected:
        return CapturedTools({}, {})
    programs = _programs(selected)
    with tempfile.TemporaryDirectory(prefix="specfact-native-tools-") as directory:
        captured = _capture_payload(Path(directory), programs)
    if "git" in selected:
        captured.inventory["@capsule/bin/sh"] = _shell_requirement(capsule_root)
    return captured


def _reject_destinations(capture: CapturedTools, artifact: Path) -> None:
    destinations = [artifact / "native-tools", *(artifact / name for name in capture.files if name.startswith("bin/"))]
    binary_directory = artifact / "bin"
    invalid_bin = binary_directory.is_symlink() or (binary_directory.exists() and not binary_directory.is_dir())
    if invalid_bin or any(path.exists() or path.is_symlink() for path in destinations):
        raise ProjectRuntimeError("project_native_tool_collision: builder output occupies a declared tool destination")


@ensure(
    lambda capture, artifact: all((artifact / name).read_bytes() == payload for name, payload in capture.files.items())
)
def install_native_tools(capture: CapturedTools, artifact: Path) -> None:
    """Install only captured bytes after rejecting all builder-owned destinations."""
    if not capture.files:
        return
    _reject_destinations(capture, artifact)
    for name, payload in capture.files.items():
        target = artifact / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        target.chmod(0o755)
