"""Owned Mach stop transport contracts; mocks cannot approve runtime acceptance."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture(name="mach_contract_binary", scope="module")
def fixture_mach_contract_binary(tmp_path_factory):
    if os.environ.get("SPECFACT_NATIVE_CONTROL") != "1" or sys.platform != "darwin":
        pytest.skip("explicit signed ARM64 Mach contract proof")
    target = tmp_path_factory.mktemp("mach-contract") / "contract"
    source = Path(__file__).parents[2] / "scripts/macos_managed_boundary/control_mach_test.c"
    subprocess.run(
        ["/usr/bin/xcrun", "clang", "-arch", "arm64", "-Wall", "-Wextra", "-Werror", str(source), "-o", str(target)],
        check=True,
        timeout=15,
    )
    subprocess.run(
        ["/usr/bin/codesign", "--force", "--sign", "-", "--options", "runtime", str(target)], check=True, timeout=10
    )
    subprocess.run(["/usr/bin/codesign", "--verify", "--strict", str(target)], check=True, timeout=10)
    return target


@pytest.mark.parametrize(
    "scenario",
    ["initial", "runtime", "foreign-sender", "foreign-child", "wrong-kind", "short-code", "bad-signal", "reaped"],
)
def test_exception_admission_is_owned_and_bounded(mach_contract_binary, scenario):
    subprocess.run([str(mach_contract_binary), scenario], check=True, timeout=10)
