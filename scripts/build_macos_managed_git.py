#!/usr/bin/env python3
"""Bounded offline maintainer build of the pinned macOS ARM64 SCM image."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path, PurePosixPath


VERSION = "2.54.0"
UPSTREAM_COMMIT = "94f057755b7941b321fd11fec1b2e3ca5313a4e0"
ARCHIVE_SHA256 = "f689162364c10de79ef89aa8dbf48731eb057e34edbbd20aca510ce0154681a3"
ARCHIVE_URL = "https://www.kernel.org/pub/software/scm/git/git-2.54.0.tar.xz"
CHECKSUM_URL = "https://www.kernel.org/pub/software/scm/git/sha256sums.asc"
SIGNING_IDENTIFIER = "ai.nold.specfact.managed-git"
BUILD_TIMEOUT_SECONDS = 600
MAX_ARCHIVE_BYTES = 32 << 20
MAX_SOURCE_BYTES = 128 << 20
MAX_SOURCE_FILES = 10000


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None, timeout: int = 60):
    return subprocess.run(command, cwd=cwd, env=env, check=True, capture_output=True, text=True, timeout=timeout)


def validate_archive(archive: Path) -> None:
    if (
        archive.is_symlink()
        or not archive.is_file()
        or archive.resolve() != archive
        or archive.stat().st_size > MAX_ARCHIVE_BYTES
        or digest(archive) != ARCHIVE_SHA256
    ):
        raise ValueError("source archive differs from the official release pin")


def extract_source(archive: Path, destination: Path) -> Path:
    """Extract ordinary source only; omit three pinned documentation/GUI links."""
    prefix = f"git-{VERSION}"
    omitted = {f"{prefix}/RelNotes", f"{prefix}/subprojects/git-gui", f"{prefix}/subprojects/gitk"}
    with tarfile.open(archive, "r:xz") as stream:
        members = []
        total = 0
        names = set()
        for item in stream:
            path = PurePosixPath(item.name)
            if item.issym() and item.name in omitted:
                continue
            total += item.size
            if (
                not path.parts
                or path.parts[0] != prefix
                or path.is_absolute()
                or ".." in path.parts
                or item.name in names
                or not (item.isfile() or item.isdir())
                or total > MAX_SOURCE_BYTES
                or len(members) >= MAX_SOURCE_FILES
            ):
                raise ValueError("upstream source exceeds ordinary bounded extraction")
            names.add(item.name)
            members.append(item)
        stream.extractall(destination, members=members, filter="data")
    source = destination / prefix
    if (source / "version").read_text().strip() != VERSION:
        raise ValueError("upstream source version differs from pin")
    return source


def make_invocation(source: Path, sdk: Path, compiler: Path, *, jobs: int) -> tuple[list[str], dict[str, str]]:
    if not 1 <= jobs <= 4:
        raise ValueError("maintainer build jobs must be between one and four")
    disabled = (
        "CURL",
        "OPENSSL",
        "EXPAT",
        "PERL",
        "PYTHON",
        "GETTEXT",
        "TCLTK",
        "UNIX_SOCKETS",
        "HOMEBREW",
        "FINK",
        "DARWIN_PORTS",
    )
    flags = (
        f"-O2 -arch arm64 -mmacosx-version-min=14.0 -isysroot {sdk} "
        f"-fstack-protector-strong -ffile-prefix-map={source}=/usr/src/git"
    )
    command = [
        "/usr/bin/make",
        f"-j{jobs}",
        "git",
        *[f"NO_{name}=YesPlease" for name in disabled],
        f"CC={compiler}",
        f"CFLAGS={flags}",
        f"LDFLAGS=-arch arm64 -mmacosx-version-min=14.0 -isysroot {sdk}",
        "prefix=/nonexistent/specfact-managed-git",
        "GIT_VERSION=" + VERSION,
        "GIT_BUILT_FROM_COMMIT=" + UPSTREAM_COMMIT,
        "GIT_DATE=",
        "SOURCE_DATE_EPOCH=0",
    ]
    return command, {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(source),
        "LC_ALL": "C",
        "TZ": "UTC",
        "SOURCE_DATE_EPOCH": "0",
    }


def apple_dependencies(listing: str) -> list[str]:
    dependencies = [line.strip().split(" (", 1)[0] for line in listing.splitlines()[1:] if line.strip()]
    if not dependencies or any(not value.startswith(("/usr/lib/", "/System/Library/")) for value in dependencies):
        raise ValueError("Git static closure contains non-platform dependencies")
    return dependencies


def build(archive: Path, output: Path, *, jobs: int = 2) -> dict:
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("maintainer build requires macOS ARM64")
    validate_archive(archive)
    if output.exists() or output.is_symlink() or output.parent.resolve() != output.parent or not output.parent.is_dir():
        raise ValueError("artifact output must be a new canonical path")
    sdk = Path(run(["/usr/bin/xcrun", "--sdk", "macosx", "--show-sdk-path"]).stdout.strip())
    compiler = Path(run(["/usr/bin/xcrun", "--sdk", "macosx", "--find", "clang"]).stdout.strip())
    with tempfile.TemporaryDirectory(prefix="specfact-git-source-", dir=output.parent) as directory:
        private = Path(directory)
        pinned = private / "upstream.tar.xz"
        shutil.copyfile(archive, pinned)
        validate_archive(pinned)
        source = extract_source(pinned, private / "source")
        command, environment = make_invocation(source, sdk, compiler, jobs=jobs)
        result = run(command, cwd=source, env=environment, timeout=BUILD_TIMEOUT_SECONDS)
        image = source / "git"
        if image.is_symlink() or not image.is_file():
            raise ValueError("maintainer build lacks an ordinary Git image")
        dependencies = apple_dependencies(run(["/usr/bin/otool", "-L", str(image)]).stdout)
        if run(["/usr/bin/lipo", "-archs", str(image)]).stdout.strip() != "arm64":
            raise ValueError("Git image architecture differs from pin")
        if run([str(image), "--version"], env=environment).stdout.strip() != f"git version {VERSION}":
            raise ValueError("Git image version differs from pin")
        candidate = private / "artifact"
        (candidate / "bin").mkdir(parents=True)
        (candidate / "licenses").mkdir()
        (candidate / "source").mkdir()
        target = candidate / "bin/git"
        shutil.copyfile(image, target)
        target.chmod(0o755)
        run(
            [
                "/usr/bin/codesign",
                "--force",
                "--sign",
                "-",
                "--options",
                "runtime",
                "--identifier",
                SIGNING_IDENTIFIER,
                str(target),
            ]
        )
        run(["/usr/bin/codesign", "--verify", "--strict", str(target)])
        signing = run(["/usr/bin/codesign", "--display", "--verbose=4", "--requirements", "-", str(target)])
        details = signing.stdout + signing.stderr
        requirement = re.search(r"^# designated => (.+)$", details, re.MULTILINE)
        cdhash = re.search(r"^CDHash=([0-9a-f]{40})$", details, re.MULTILINE)
        if (
            not requirement
            or not cdhash
            or f"Identifier={SIGNING_IDENTIFIER}" not in details
            or "runtime)" not in details
            or "Signature=adhoc" not in details
        ):
            raise ValueError("Git ad-hoc hardened identity is missing")
        (candidate / "git.requirement").write_text(requirement[1] + "\n")
        shutil.copyfile(source / "COPYING", candidate / "licenses/Git-COPYING")
        shutil.copyfile(source / "sha1dc/LICENSE.txt", candidate / "licenses/sha1dc-LICENSE.txt")
        shutil.copyfile(source / "reftable/LICENSE", candidate / "licenses/reftable-LICENSE")
        shutil.copyfile(pinned, candidate / f"source/git-{VERSION}.tar.xz")
        (candidate / "build.log").write_text(result.stdout + result.stderr)
        provenance = {
            "schema": "specfact-managed-git-build-v1",
            "maintainer_only": True,
            "upstream": {
                "version": VERSION,
                "commit": UPSTREAM_COMMIT,
                "archive_url": ARCHIVE_URL,
                "archive_sha256": ARCHIVE_SHA256,
                "checksum_url": CHECKSUM_URL,
            },
            "toolchain": {
                "compiler": str(compiler),
                "compiler_version": run([str(compiler), "--version"]).stdout.strip(),
                "sdk": str(sdk),
                "sdk_version": run(["/usr/bin/xcrun", "--sdk", "macosx", "--show-sdk-version"]).stdout.strip(),
                "make_version": run(["/usr/bin/make", "--version"]).stdout.splitlines()[0],
            },
            "build": {
                "command": [arg.replace(str(source), "/usr/src/git") for arg in command],
                "environment": {**environment, "HOME": "/usr/src/git"},
                "timeout_seconds": BUILD_TIMEOUT_SECONDS,
            },
            "signing": {
                "mode": "adhoc",
                "identifier": SIGNING_IDENTIFIER,
                "cdhash": cdhash[1],
                "requirement": requirement[1],
            },
            "dependencies": dependencies,
            "inventory": {
                p.relative_to(candidate).as_posix(): digest(p) for p in sorted(candidate.rglob("*")) if p.is_file()
            },
        }
        (candidate / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
        (candidate / "SHA256SUMS").write_text(
            "".join(
                f"{digest(p)}  {p.relative_to(candidate).as_posix()}\n"
                for p in sorted(candidate.rglob("*"))
                if p.is_file()
            )
        )
        for path in candidate.rglob("*"):
            if path.is_file():
                path.chmod(0o555 if path == target else 0o444)
        candidate.rename(output)
    return provenance


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--jobs", type=int, choices=range(1, 5), default=2)
    args = parser.parse_args()
    provenance = build(args.source_archive, args.output, jobs=args.jobs)
    print(json.dumps({"output": str(args.output), "git_sha256": provenance["inventory"]["bin/git"]}))


if __name__ == "__main__":
    main()
