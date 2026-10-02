"""Compile actual broker request/timer logic with signaling safely mocked."""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture(name="native_timer_binary", scope="module")
def fixture_native_timer_binary(tmp_path_factory):
    if os.environ.get("SPECFACT_NATIVE_CONTROL") != "1":
        pytest.skip("explicit native timer fixture run")
    target = tmp_path_factory.mktemp("native-timers") / "timer-test"
    source = Path(__file__).parents[2] / "scripts/macos_managed_boundary/control_timers_test.c"
    subprocess.run(
        [
            "/usr/bin/xcrun",
            "clang",
            "-arch",
            "arm64",
            "-Wall",
            "-Wextra",
            "-Werror",
            str(source),
            "-o",
            str(target),
            "-framework",
            "Security",
            "-framework",
            "CoreFoundation",
        ],
        check=True,
        timeout=10,
    )
    subprocess.run(
        ["/usr/bin/codesign", "--force", "--sign", "-", "--options", "runtime", str(target)], check=True, timeout=10
    )
    subprocess.run(["/usr/bin/codesign", "--verify", "--strict", str(target)], check=True, timeout=10)
    return target


@pytest.mark.parametrize("mode", [1, 2, 3], ids=["cancel", "sigkill", "ignored-sigterm"])
def test_terminal_action_keeps_its_reason(native_timer_binary, mode):
    result = subprocess.run([str(native_timer_binary), str(mode)], check=False, timeout=10)
    assert result.returncode == 0
