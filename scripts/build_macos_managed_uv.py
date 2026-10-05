#!/usr/bin/env python3
"""Build the reviewed macOS ARM64 managed uv as a maintainer-only artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
NATIVE = REPOSITORY_ROOT / "packages/specfact-code-review/native/macos-arm64"
PATCH = NATIVE / "uv-managed-launch.patch"
BRIDGE = NATIVE / "uv_managed.rs"
UPSTREAM_COMMIT = "0ebbd9274a55a8a53a13970be3b97e4209598e17"
LOCK_SHA256 = "43656655b1cd577551f79567af2dd534d5a27f9c7140741cc966103cb7a1eb64"
PATCH_SHA256 = "2f8c115cd00fe9c6a1f136d712fe34fb0a6420707a59510f9ce0c0f575862b20"
BRIDGE_SHA256 = "064492cb34ebb3bd25a2022df0b088da5c783dcc82c379c678f29252283fccdd"
SIGNING_IDENTIFIER = "ai.nold.specfact.managed-uv"
BUILD_TIMEOUT_SECONDS = 1800


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def run(
    command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None, timeout: int = 120
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, check=True, capture_output=True, text=True, timeout=timeout)


def validate_source(source: Path, *, expected_commit: str | None = None) -> None:
    if not source.is_dir() or source.is_symlink():
        raise ValueError("upstream source must be an ordinary directory")
    if run(["git", "rev-parse", "--show-toplevel"], cwd=source).stdout.strip() != str(source.resolve()):
        raise ValueError("upstream source must be the checkout root")
    if run(["git", "rev-parse", "HEAD"], cwd=source).stdout.strip() != (expected_commit or UPSTREAM_COMMIT):
        raise ValueError("upstream commit does not match the reviewed pin")
    if run(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=source).stdout:
        raise ValueError("upstream checkout is dirty")
    lock = source / "Cargo.lock"
    if not lock.is_file() or lock.is_symlink() or digest(lock) != LOCK_SHA256:
        raise ValueError("Cargo.lock differs from the reviewed pin")
    for name in ("Cargo.toml", "LICENSE-MIT", "LICENSE-APACHE"):
        item = source / name
        if not item.is_file() or item.is_symlink() or not item.stat().st_size:
            raise ValueError(f"upstream source lacks {name}")


def validate_reviewed_inputs(patch: Path = PATCH, bridge: Path = BRIDGE) -> None:
    for path, expected, label in ((patch, PATCH_SHA256, "reviewed patch"), (bridge, BRIDGE_SHA256, "reviewed bridge")):
        if not path.is_file() or path.is_symlink() or digest(path) != expected:
            raise ValueError(f"missing or substituted {label}")


def require_new_output(output: Path) -> None:
    if output.exists() or output.is_symlink():
        raise ValueError("output already exists")
    if not output.parent.is_dir() or output.parent.is_symlink():
        raise ValueError("output parent must be an ordinary directory")


def cargo_invocation(source: Path, target: Path, toolchain: Path, cargo_home: Path) -> tuple[list[str], dict[str, str]]:
    environment = {
        "PATH": f"{toolchain / 'bin'}:/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(source),
        "CARGO_HOME": str(cargo_home),
        "CARGO_TARGET_DIR": str(target),
        "CARGO_NET_OFFLINE": "true",
        "CARGO_INCREMENTAL": "0",
        "RUSTC": str(toolchain / "bin/rustc"),
    }
    return [
        str(toolchain / "bin/cargo"),
        "build",
        "--locked",
        "--offline",
        "--release",
        "--bin",
        "uv",
        "--no-default-features",
    ], environment


def validate_toolchain(toolchain: Path, cargo_home: Path) -> None:
    if not toolchain.is_dir() or toolchain.is_symlink() or not cargo_home.is_dir() or cargo_home.is_symlink():
        raise ValueError("local Rust toolchain and Cargo home are required")
    for executable in ("rustc", "cargo"):
        path = toolchain / "bin" / executable
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"missing pinned {executable}")
        version = run([str(path), "--version"]).stdout.strip()
        if not version.startswith(f"{executable} 1.96.0 "):
            raise ValueError(f"{executable} must be version 1.96.0")


def prepare_source(source: Path, destination: Path) -> str:
    archive = destination.parent / "upstream.tar"
    run(["git", "archive", "--format=tar", "HEAD", "-o", str(archive)], cwd=source)
    archive_sha256 = digest(archive)
    destination.mkdir()
    with tarfile.open(archive) as bundle:
        bundle.extractall(destination, filter="data")
    archive.unlink()
    if digest(destination / "Cargo.lock") != LOCK_SHA256:
        raise ValueError("archived Cargo.lock differs from the reviewed pin")
    run(["git", "apply", "--check", str(PATCH)], cwd=destination)
    run(["git", "apply", str(PATCH)], cwd=destination)
    bridge_destination = destination / "crates/uv-python/src/specfact_managed.rs"
    if bridge_destination.exists() or bridge_destination.is_symlink():
        raise ValueError("bridge destination already exists upstream")
    shutil.copyfile(BRIDGE, bridge_destination)
    if digest(bridge_destination) != BRIDGE_SHA256 or digest(destination / "Cargo.lock") != LOCK_SHA256:
        raise ValueError("prepared source differs from reviewed inputs")
    return archive_sha256


def verify_signed_binary(binary: Path) -> None:
    description = run(["file", "-b", str(binary)]).stdout
    if "Mach-O 64-bit executable arm64" not in description:
        raise ValueError("built uv is not a macOS ARM64 executable")
    run(["codesign", "--force", "--sign", "-", "--options", "runtime", "--identifier", SIGNING_IDENTIFIER, str(binary)])
    run(["codesign", "--verify", "--strict", "--verbose=2", str(binary)])
    details = run(["codesign", "-dv", "--verbose=2", str(binary)]).stderr
    if (
        f"Identifier={SIGNING_IDENTIFIER}" not in details
        or "Signature=adhoc" not in details
        or ("flags=0x10002" not in details and "flags=0x10000" not in details)
    ):
        raise ValueError("uv ad-hoc hardened signature does not match the requested identity")


def write_artifacts(
    output: Path,
    binary: Path,
    rust_version: str,
    license_source: Path,
    toolchain: Path,
    source_archive_sha256: str,
) -> dict[str, Path]:
    binary_destination = output / "bin/uv"
    binary_destination.parent.mkdir()
    shutil.copy2(binary, binary_destination)
    licenses = output / "licenses"
    sources = output / "sources"
    licenses.mkdir()
    sources.mkdir()
    copied: dict[str, Path] = {"binary": binary_destination}
    for name in ("LICENSE-MIT", "LICENSE-APACHE"):
        copied[name] = licenses / name
        shutil.copyfile(license_source / name, copied[name])
    for path in (PATCH, BRIDGE):
        copied[path.name] = sources / path.name
        shutil.copyfile(path, copied[path.name])
    provenance = {
        "upstream": "https://github.com/astral-sh/uv",
        "upstream_version": "0.12.13",
        "upstream_commit": UPSTREAM_COMMIT,
        "cargo_lock_sha256": LOCK_SHA256,
        "source_archive_sha256": source_archive_sha256,
        "rust_version": rust_version,
        "toolchain_sha256": {name: digest(toolchain / "bin" / name) for name in ("rustc", "cargo")},
        "cargo_args": ["build", "--locked", "--offline", "--release", "--bin", "uv", "--no-default-features"],
        "signature": {"mode": "adhoc", "identifier": SIGNING_IDENTIFIER, "hardened_runtime": True},
        "binary_sha256": digest(binary_destination),
        "files_sha256": {str(path.relative_to(output)): digest(path) for path in copied.values()},
    }
    provenance_path = output / "provenance.json"
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    copied["provenance"] = provenance_path
    return copied


def validate_artifact(root: Path) -> dict[str, object]:
    """Validate the complete maintained output before it enters a capsule candidate."""
    if root.resolve() != root or root.is_symlink() or not root.is_dir():
        raise ValueError("managed uv artifact must be a canonical ordinary directory")
    metadata = root / "provenance.json"
    if metadata.is_symlink() or not metadata.is_file() or metadata.stat().st_size > 1 << 20:
        raise ValueError("managed uv provenance is missing or unbounded")
    document = json.loads(metadata.read_text())
    expected = {
        "bin/uv",
        "licenses/LICENSE-MIT",
        "licenses/LICENSE-APACHE",
        "sources/uv-managed-launch.patch",
        "sources/uv_managed.rs",
    }
    if (
        not isinstance(document, dict)
        or document.get("upstream_commit") != UPSTREAM_COMMIT
        or document.get("upstream_version") != "0.12.13"
        or document.get("cargo_lock_sha256") != LOCK_SHA256
        or document.get("rust_version") != "1.96.0"
        or document.get("signature") != {"mode": "adhoc", "identifier": SIGNING_IDENTIFIER, "hardened_runtime": True}
        or not isinstance(document.get("files_sha256"), dict)
        or set(document["files_sha256"]) != expected
    ):
        raise ValueError("managed uv provenance differs from reviewed pins")
    observed = set()
    for path in root.rglob("*"):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError("managed uv artifact contains indirection or special files")
        if path.is_file():
            observed.add(path.relative_to(root).as_posix())
    if observed != expected | {"provenance.json"}:
        raise ValueError("managed uv artifact has undeclared or missing files")
    for name, checksum in document["files_sha256"].items():
        path = root / name
        if not 0 < path.stat().st_size <= 512 << 20 or digest(path) != checksum:
            raise ValueError("managed uv artifact digest mismatch")
    if (
        document.get("binary_sha256") != document["files_sha256"]["bin/uv"]
        or document["files_sha256"]["sources/uv-managed-launch.patch"] != PATCH_SHA256
        or document["files_sha256"]["sources/uv_managed.rs"] != BRIDGE_SHA256
    ):
        raise ValueError("managed uv artifact digest differs from reviewed inputs")
    return document


def build(source: Path, output: Path, toolchain: Path, cargo_home: Path) -> Path:
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("maintainer build requires a macOS ARM64 host")
    source, output, toolchain, cargo_home = (path.absolute() for path in (source, output, toolchain, cargo_home))
    require_new_output(output)
    validate_source(source)
    validate_reviewed_inputs()
    validate_toolchain(toolchain, cargo_home)
    if source == output or output.is_relative_to(source) or output.is_relative_to(cargo_home):
        raise ValueError("output must be separate from source and Cargo home")
    with tempfile.TemporaryDirectory(prefix="managed-uv-", dir=output.parent) as directory:
        temporary = Path(directory)
        prepared = temporary / "source"
        source_archive_sha256 = prepare_source(source, prepared)
        command, environment = cargo_invocation(prepared, temporary / "target", toolchain, cargo_home)
        run(command, cwd=prepared, env=environment, timeout=BUILD_TIMEOUT_SECONDS)
        if digest(prepared / "Cargo.lock") != LOCK_SHA256:
            raise ValueError("Cargo.lock changed during the build")
        binary = temporary / "target/release/uv"
        if not binary.is_file() or binary.is_symlink():
            raise ValueError("Cargo did not produce a regular uv executable")
        verify_signed_binary(binary)
        artifact = temporary / "artifact"
        artifact.mkdir()
        write_artifacts(artifact, binary, "1.96.0", prepared, toolchain, source_archive_sha256)
        require_new_output(output)
        os.replace(artifact, output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--rust-toolchain", required=True, type=Path)
    parser.add_argument("--cargo-home", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(build(args.upstream_source, args.output, args.rust_toolchain, args.cargo_home))
    except (ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        parser.exit(1, f"managed uv build rejected: {exc}\n")


if __name__ == "__main__":
    main()
