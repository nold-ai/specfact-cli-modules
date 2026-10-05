"""Build local ad-hoc signed ARM64 XPC experiments, never release artifacts."""

from __future__ import annotations

import argparse
import hashlib
import platform
import plistlib
import subprocess
from pathlib import Path


SOURCE = Path(__file__).resolve().parent
SERVICE = "ai.nold.specfact.boundary.runner"


def command(*args: str) -> None:
    """Run a fixed build command and stop on any failure."""
    subprocess.run(args, check=True, timeout=120)


def plist(path: Path, value: dict) -> None:
    """Write a deterministic local bundle property list."""
    path.write_bytes(plistlib.dumps(value))


def compile_binary(source: str, target: Path, *flags: str) -> None:
    """Compile only native ARM64 fixture sources with warning checks."""
    command(
        "/usr/bin/xcrun",
        "clang",
        "-arch",
        "arm64",
        "-Wall",
        "-Wextra",
        "-Werror",
        *flags,
        str(SOURCE / source),
        "-o",
        str(target),
    )


def build(root: Path, sandbox: bool = True) -> Path:
    """Build a fresh experiment bundle without installing a system service."""
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("native macOS ARM64 is required")
    root.mkdir(parents=True, exist_ok=False)
    app = root / "Boundary.app"
    service = app / "Contents/XPCServices/Runner.xpc"
    for bundle in (app, service):
        (bundle / "Contents/MacOS").mkdir(parents=True)
    resources = service / "Contents/Resources"
    resources.mkdir()
    plist(
        app / "Contents/Info.plist",
        {
            "CFBundleIdentifier": "ai.nold.specfact.boundary",
            "CFBundleExecutable": "BoundaryClient",
            "CFBundlePackageType": "APPL",
            "CFBundleVersion": "1",
            "LSUIElement": True,
        },
    )
    plist(
        service / "Contents/Info.plist",
        {
            "CFBundleIdentifier": SERVICE,
            "CFBundleExecutable": "Runner",
            "CFBundlePackageType": "XPC!",
            "CFBundleVersion": "1",
            "XPCService": {"ServiceType": "Application", "RunLoopType": "dispatch_main"},
        },
    )
    flags = ("-fobjc-arc", "-fblocks", "-framework", "Foundation")
    compile_binary("boundary.m", app / "Contents/MacOS/BoundaryClient", *flags)
    compile_binary("boundary.m", service / "Contents/MacOS/Runner", "-DSERVICE", *flags)
    compile_binary("fixture.c", resources / "fixture")
    compile_binary("observe.c", root / "observe")
    service_entitlements = root / "service.plist"
    worker_entitlements = root / "worker.plist"
    plist(service_entitlements, {"com.apple.security.app-sandbox": True} if sandbox else {})
    plist(
        worker_entitlements,
        {"com.apple.security.app-sandbox": True, "com.apple.security.inherit": True} if sandbox else {},
    )
    command(
        "/usr/bin/codesign",
        "--force",
        "--sign",
        "-",
        "--entitlements",
        str(worker_entitlements),
        str(resources / "fixture"),
    )
    command("/usr/bin/codesign", "--force", "--sign", "-", "--entitlements", str(service_entitlements), str(service))
    command("/usr/bin/codesign", "--force", "--sign", "-", str(app))
    command("/usr/bin/codesign", "--verify", "--deep", "--strict", str(app))
    return app


def identities(root: Path) -> dict[str, str]:
    """Identify source, profile and executable bytes in a local receipt."""
    paths = list(SOURCE.glob("*.c")) + list(SOURCE.glob("*.m")) + list(SOURCE.glob("*.py"))
    paths += [p for p in root.rglob("*") if p.is_file()]
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--unsandboxed-control", action="store_true")
    args = parser.parse_args()
    print(build(args.output, not args.unsandboxed_control))
