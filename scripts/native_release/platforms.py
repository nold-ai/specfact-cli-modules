"""Reviewed ABI, OS-image and execution-check policy (no payload imports)."""

import os
import platform
import subprocess

from icontract import ensure


ABIS = ("cp311", "cp312", "cp313")
PLATFORMS = {
    "macos-14": ("14.8.9", "23J631"),
    "macos-15": ("15.7.9", "24G830"),
    "macos-26": ("26.6.2", "25G83"),
}
REQUIRED_CHECKS = (
    "native_boundary",
    "native_execution",
    "loader_profile",
    "all_ten_analyzers",
    "project_tests",
    "project_coverage",
    "project_extensions",
    "cold_extraction",
    "offline_reuse",
)


@ensure(
    lambda result: (
        set(result) == {"runner", "os_version", "os_build", "architecture"}
        and all(isinstance(value, str) and value.strip() for value in result.values())
    ),
    error=ValueError("native platform observations must be nonempty strings"),
)
def platform_context(label: str) -> dict[str, str]:
    version = subprocess.run(
        ["/usr/bin/sw_vers", "-productVersion"], check=True, text=True, capture_output=True, timeout=10
    ).stdout.strip()
    build = subprocess.run(
        ["/usr/bin/sw_vers", "-buildVersion"], check=True, text=True, capture_output=True, timeout=10
    ).stdout.strip()
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("native platform is not Darwin ARM64")
    if label != "local" and (version, build) != PLATFORMS.get(label):
        raise ValueError("supported native platform image drift")
    if os.getuid() == 0:
        raise ValueError("native acceptance requires an ordinary user")
    subprocess.run(["/bin/launchctl", "print", f"gui/{os.getuid()}"], check=True, capture_output=True, timeout=10)
    return {"runner": label, "os_version": version, "os_build": build, "architecture": "arm64"}
