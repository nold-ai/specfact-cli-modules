"""Owned Mach stop transport contracts; mocks cannot approve runtime acceptance."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


def _signed_fixture(tmp_path_factory, source_name):
    if os.environ.get("SPECFACT_NATIVE_CONTROL") != "1" or sys.platform != "darwin":
        pytest.skip("explicit signed ARM64 Mach contract proof")
    target = tmp_path_factory.mktemp(Path(source_name).stem) / "contract"
    source = Path(__file__).parents[2] / "scripts/macos_managed_boundary" / source_name
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


@pytest.fixture(name="signed_mach_binary", scope="module")
def fixture_signed_mach_binary(request, tmp_path_factory):
    return _signed_fixture(tmp_path_factory, request.param)


@pytest.mark.parametrize("signed_mach_binary", ["control_mach_test.c"], indirect=True)
@pytest.mark.parametrize(
    "scenario",
    ["initial", "runtime", "foreign-sender", "foreign-child", "wrong-kind", "short-code", "bad-signal", "reaped"],
)
def test_exception_admission_is_owned_and_bounded(signed_mach_binary, scenario):
    subprocess.run([str(signed_mach_binary), scenario], check=True, timeout=10)


@pytest.mark.parametrize("signed_mach_binary", ["control_mach_reply_test.c"], indirect=True)
@pytest.mark.parametrize("scenario", ["success", "invalid-destination", "timeout", "interrupted", "invalid-right"])
def test_owned_reply_failure_disposes_before_continuation_or_fail_closed(signed_mach_binary, scenario):
    subprocess.run([str(signed_mach_binary), scenario], check=True, timeout=10)
