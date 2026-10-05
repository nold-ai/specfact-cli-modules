"""Generate private SDK Mach exception fixtures; no production admission.

The injected command runner must execute argv without a shell, capture text and
apply a finite timeout (the controller's runner uses ten seconds). Read-only
snapshots bind captured bytes, not a hostile same-user filesystem boundary.
"""

from __future__ import annotations

import hashlib
import os
import stat
from collections.abc import Callable
from pathlib import Path
from typing import Any


_FILES = ("mach_exc.defs", "mach_exc_server.c", "mach_exc_server.h", "mach_exc_user.h")
_MAX_BYTES = 4 * 1024 * 1024


def _read_regular(path: Path) -> bytes:
    """Open without following a final symlink; bound regular nonempty content."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode) or not 0 < metadata.st_size <= _MAX_BYTES:
            raise ValueError(f"invalid regular file: {path}")
        content = stream.read(_MAX_BYTES + 1)
        if len(content) != metadata.st_size:
            raise ValueError(f"file changed during capture: {path}")
        return content


def _private_root(root: Path) -> None:
    """Require an existing owned private directory and fresh generated paths."""
    metadata = root.lstat()
    if (
        not root.is_absolute()
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) & 0o077
    ):
        raise ValueError("buildroot must be an absolute owned private directory")
    for name in _FILES:
        if os.path.lexists(root / name):
            raise FileExistsError(f"build path already exists: {name}")


def _sdk_path(command: Callable[..., Any]) -> Path:
    """Resolve and validate the selected SDK directory."""
    result = command(["/usr/bin/xcrun", "--show-sdk-path"])
    sdk_text = result.stdout.strip()
    if result.returncode or not sdk_text or "\n" in sdk_text or "\r" in sdk_text:
        raise ValueError("invalid SDK path response")
    sdk = Path(sdk_text)
    if not sdk.is_absolute() or not sdk.is_dir():
        raise ValueError("SDK path must be an absolute directory")
    return sdk


def _sdk_version(command: Callable[..., Any]) -> str | None:
    """Capture an optional single-line SDK version."""
    version_result = command(["/usr/bin/xcrun", "--show-sdk-version"], check=False)
    version = version_result.stdout.strip() if version_result.returncode == 0 else None
    if version and ("\n" in version or "\r" in version):
        raise ValueError("invalid SDK version response")
    return version or None


def _capture_input(root: Path, sdk: Path, context: dict[str, Any], provenance: list[dict[str, Any]]) -> bytes:
    """Snapshot SDK definitions and append their byte provenance."""
    source = sdk / "usr/include/mach/mach_exc.defs"
    content = _read_regular(source)
    captured = root / _FILES[0]
    with captured.open("xb") as stream:
        stream.write(content)
        os.fchmod(stream.fileno(), 0o444)
    provenance.append(
        {
            "name": "mach-exception-defs",
            "path": str(captured),
            "source_path": str(source),
            "sha256": hashlib.sha256(content).hexdigest(),
            **context,
        }
    )
    return content


def _generate(root: Path, sdk: Path, command: Callable[..., Any]) -> list[str]:
    """Run MIG with the captured definitions and exact fixture arguments."""
    captured = root / _FILES[0]
    argv = [
        "/usr/bin/xcrun",
        "mig",
        "-DMACH_EXC_SERVER_AUDITTOKEN=1",
        f"-I{sdk / 'usr/include'}",
        "-server",
        str(root / _FILES[1]),
        "-sheader",
        str(root / _FILES[2]),
        "-user",
        "/dev/null",
        "-header",
        str(root / _FILES[3]),
        str(captured),
    ]
    generated = command(argv)
    if generated.returncode:
        raise RuntimeError(f"MIG exited with status {generated.returncode}")
    return argv


def _capture_outputs(
    root: Path,
    content: bytes,
    argv: list[str],
    context: dict[str, Any],
    provenance: list[dict[str, Any]],
) -> None:
    """Verify the input snapshot and append each validated output in order."""
    captured = root / _FILES[0]
    if _read_regular(captured) != content or stat.S_IMODE(captured.stat().st_mode) != 0o444:
        raise ValueError("MIG input snapshot changed")
    for name in _FILES[1:]:
        path = root / name
        output = _read_regular(path)
        path.chmod(0o444)
        provenance.append(
            {
                "name": name,
                "path": str(path),
                "sha256": hashlib.sha256(output).hexdigest(),
                "generator_argv": argv.copy(),
                "input_sha256": provenance[0]["sha256"],
                **context,
            }
        )


def prepare(root: Path, command: Callable[..., Any]) -> tuple[list[str], list[dict[str, Any]]]:
    """Return clang inputs and byte provenance, or fail with partial provenance.

    Failed attempts are not reusable: their captured files remain for diagnostics.
    Retry with a fresh private buildroot. SDK transitive includes resolve through
    the selected SDK; only the top-level defs and three outputs are snapshotted.
    """
    provenance: list[dict[str, Any]] = []
    phase = "root"
    try:
        _private_root(root)
        phase = "sdk-path"
        sdk = _sdk_path(command)
        phase = "sdk-version"
        context = {"sdk_path": str(sdk), "sdk_version": _sdk_version(command)}
        phase = "input"
        content = _capture_input(root, sdk, context, provenance)
        phase = "generate"
        argv = _generate(root, sdk, command)
        phase = "outputs"
        _capture_outputs(root, content, argv, context, provenance)
        return [f"-I{root}", str(root / _FILES[1])], provenance
    except Exception as cause:
        error = RuntimeError(f"Mach MIG build failed during {phase}: {cause}")
        error.provenance = provenance  # type: ignore[attr-defined]
        error.phase = phase  # type: ignore[attr-defined]
        raise error from cause
