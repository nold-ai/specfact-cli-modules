"""Bounded bootstrap failures cannot decode as successful startup."""

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_failure_markers_are_bounded_and_disjoint_from_readiness(tmp_path: Path) -> None:
    source = tmp_path / "protocol.c"
    program = tmp_path / "protocol"
    source.write_text(
        r"""
#include <assert.h>
#include <stdint.h>
#include "native_protocol.h"
int main(void) {
    assert(specfact_startup_failure_phase(SPECFACT_MARKER_READY) == 0);
    assert(specfact_startup_failure_phase(0) == 0);
    assert(specfact_startup_failure_marker(66, 22) == 0);
    assert(specfact_startup_failure_marker(71, 22) == 0);
    assert(specfact_startup_failure_marker(68, 65536) == 0);
    for (uint32_t phase = 67; phase <= 70; phase++) {
        uint32_t errors[] = {0, 1, 22, 65535};
        for (unsigned int i = 0; i < sizeof(errors) / sizeof(errors[0]); i++) {
            uint32_t marker = specfact_startup_failure_marker(phase, errors[i]);
            assert(marker != SPECFACT_MARKER_READY);
            assert(specfact_startup_failure_phase(marker) == phase);
            assert(specfact_startup_failure_errno(marker) == errors[i]);
            assert(specfact_startup_failure_phase(marker ^ 0x01000000u) == 0);
        }
    }
    assert(specfact_startup_failure_phase(0x53474616u) == 0);
    return 0;
}
""",
        encoding="utf-8",
    )
    subprocess.run(
        [
            "cc",
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(REPO_ROOT / "packages/specfact-code-review/native/macos-arm64"),
            str(source),
            "-o",
            str(program),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    subprocess.run([str(program)], capture_output=True, text=True, check=True, timeout=5)
