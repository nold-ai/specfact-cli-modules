"""Physical proof that project file size and broker stream budgets are distinct."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


SOURCE = Path(__file__).parents[2] / "packages/specfact-code-review/native/macos-arm64"
HARNESS = r"""
#define main specfact_bootstrap_main
#include "SOURCE_PATH"
#undef main
int main(int argc, char **argv) {
    if (argc != 2) return 20;
    struct specfact_request request = {0};
    request.open_files = 64;
    request.file_size_bytes = 32ULL << 20;
    request.output_bytes = 8ULL << 20;
    request.address_space_bytes = 1ULL << 30;
    if (apply_limits(&request)) return 21;
    struct rlimit observed;
    if (getrlimit(RLIMIT_FSIZE, &observed) || observed.rlim_cur != request.file_size_bytes) return 22;
    signal(SIGXFSZ, SIG_IGN);
    int descriptor = open(argv[1], O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (descriptor < 0) return 23;
    char block[1024 * 1024] = {0};
    for (int index = 0; index < 12; index++) {
        if (write(descriptor, block, sizeof(block)) != sizeof(block)) return 24;
    }
    close(descriptor);
    return 0;
}
"""


def test_file_budget_does_not_inherit_smaller_stream_budget() -> None:
    """The signed ARM64 bootstrap admits a 12 MiB file with an 8 MiB stream limit."""
    if sys.platform != "darwin" or os.uname().machine != "arm64" or os.environ.get("SPECFACT_NATIVE_CONTROL") != "1":
        import pytest

        pytest.skip("explicit physical ARM64 native bootstrap run")
    with tempfile.TemporaryDirectory(prefix="sf-native-file-budget-") as directory:
        root = Path(directory).resolve(strict=True)
        source = root / "proof.c"
        program = root / "proof"
        output = root / "project-output"
        source.write_text(HARNESS.replace("SOURCE_PATH", str(SOURCE / "bootstrap.c")), encoding="utf-8")
        subprocess.run(
            [
                "/usr/bin/xcrun",
                "clang",
                "-arch",
                "arm64",
                "-mmacosx-version-min=14.0",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-Wno-deprecated-declarations",
                "-I",
                str(SOURCE),
                str(source),
                "-o",
                str(program),
                "-lsandbox",
            ],
            check=True,
            capture_output=True,
            timeout=60,
        )
        subprocess.run(
            ["/usr/bin/codesign", "--force", "--sign", "-", "--options", "runtime", str(program)],
            check=True,
            capture_output=True,
            timeout=30,
        )
        subprocess.run(
            ["/usr/bin/codesign", "--verify", "--strict", str(program)],
            check=True,
            capture_output=True,
            timeout=30,
        )
        result = subprocess.run([str(program), str(output)], check=False, capture_output=True, timeout=30)
        assert result.returncode == 0, (result.returncode, result.stderr[-200:])
        assert output.stat().st_size == 12 << 20


if __name__ == "__main__":
    if sys.argv[1:] != ["--self-test"]:
        raise SystemExit(64)
    test_file_budget_does_not_inherit_smaller_stream_budget()
    print(json.dumps({"file_bytes": 12 << 20, "stream_budget_bytes": 8 << 20, "production_eligible": False}))
