"""Reviewed ABI, OS-image and execution-check policy (no payload imports)."""

ABIS = ("cp311", "cp312", "cp313")
PLATFORMS = {
    "macos-14": ("14.8.9", "23J631"),
    "macos-15": ("15.7.9", "24G830"),
    "macos-26": ("26.6.2", "25G83"),
}
REQUIRED_CHECKS = (
    "native_boundary",
    "loader_profile",
    "all_ten_analyzers",
    "project_tests",
    "project_coverage",
    "project_extensions",
    "cold_extraction",
    "offline_reuse",
)
