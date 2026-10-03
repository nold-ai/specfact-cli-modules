"""MIG build inputs and outputs must be private, captured and attributable."""

import hashlib
import importlib.util
import stat
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest


SOURCE = Path(__file__).parents[2] / "scripts/macos_managed_boundary/control_mach_build.py"
OUTPUTS = ("mach_exc_server.c", "mach_exc_server.h", "mach_exc_user.h")


@pytest.fixture(name="helper")
def fixture_helper():
    spec = importlib.util.spec_from_file_location("control_mach_build", SOURCE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(name="build")
def fixture_build(tmp_path):
    root = tmp_path / "private build"
    root.mkdir(mode=0o700)
    sdk = tmp_path / "SDK with spaces"
    defs = sdk / "usr/include/mach/mach_exc.defs"
    defs.parent.mkdir(parents=True)
    defs.write_bytes(b"subsystem mach_exc 2405;\n")

    def run(args, **_kwargs):
        if args[1] == "--show-sdk-path":
            return subprocess.CompletedProcess(args, 0, str(sdk) + "\n", "")
        if args[1] == "--show-sdk-version":
            return subprocess.CompletedProcess(args, 0, "27.0\n", "")
        assert args[1] == "mig"
        captured = Path(args[-1])
        assert captured.parent == root
        assert captured.read_bytes() == defs.read_bytes()
        assert stat.S_IMODE(captured.stat().st_mode) == 0o444
        for name in OUTPUTS:
            (root / name).write_text(f"/* {name} */\n")
        return subprocess.CompletedProcess(args, 0, "", "")

    return root, sdk, defs, Mock(side_effect=run)


def test_generation_binds_snapshots_flags_sdk_and_output_hashes(helper, build):
    root, sdk, defs, command = build
    args, inventory = helper.prepare(root, command)
    assert args == [f"-I{root}", str(root / OUTPUTS[0])]
    mig = command.call_args_list[-1].args[0]
    assert mig == [
        "/usr/bin/xcrun",
        "mig",
        "-DMACH_EXC_SERVER_AUDITTOKEN=1",
        f"-I{sdk / 'usr/include'}",
        "-server",
        str(root / OUTPUTS[0]),
        "-sheader",
        str(root / OUTPUTS[1]),
        "-user",
        "/dev/null",
        "-header",
        str(root / OUTPUTS[2]),
        str(root / "mach_exc.defs"),
    ]
    assert len(inventory) == 4
    for record in inventory:
        path = Path(record["path"])
        assert record["sdk_path"] == str(sdk)
        assert record["sdk_version"] == "27.0"
        assert record["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert stat.S_IMODE(path.stat().st_mode) == 0o444
    assert inventory[0]["source_path"] == str(defs)
    before = (root / "mach_exc.defs").read_bytes()
    defs.write_bytes(b"changed SDK")
    assert (root / "mach_exc.defs").read_bytes() == before


def test_sdk_version_unavailable_is_explicit(helper, build):
    root, _, _, command = build
    normal = command.side_effect

    def run(args, **kwargs):
        if args[1] == "--show-sdk-version":
            return subprocess.CompletedProcess(args, 1, "", "unavailable")
        return normal(args, **kwargs)

    command.side_effect = run
    _, inventory = helper.prepare(root, command)
    assert all(record["sdk_version"] is None for record in inventory)


@pytest.mark.parametrize("bad", ["", "relative/sdk", "/sdk\n/other"])
def test_invalid_sdk_output_fails_before_generation(helper, build, bad):
    root, _, _, command = build
    command.side_effect = None
    command.return_value = subprocess.CompletedProcess([], 0, bad, "")
    with pytest.raises(RuntimeError, match="sdk-path") as caught:
        helper.prepare(root, command)
    assert caught.value.provenance == []
    assert command.call_count == 1


@pytest.mark.parametrize("kind", ["symlink", "directory", "empty"])
def test_nonregular_or_empty_defs_rejected(helper, build, kind):
    root, _, defs, command = build
    defs.unlink()
    if kind == "symlink":
        defs.symlink_to(SOURCE)
    elif kind == "directory":
        defs.mkdir()
    else:
        defs.touch()
    with pytest.raises(RuntimeError, match="input"):
        helper.prepare(root, command)
    assert not (root / "mach_exc.defs").exists()
    assert all(call.args[0][1] != "mig" for call in command.call_args_list)


def test_generator_failure_retains_input_digest_and_cause(helper, build):
    root, _, defs, command = build
    normal = command.side_effect
    failure = subprocess.TimeoutExpired(["mig"], 10)

    def run(args, **kwargs):
        if args[1] == "mig":
            raise failure
        return normal(args, **kwargs)

    command.side_effect = run
    with pytest.raises(RuntimeError, match="generate") as caught:
        helper.prepare(root, command)
    assert caught.value.__cause__ is failure
    assert caught.value.provenance[0]["sha256"] == hashlib.sha256(defs.read_bytes()).hexdigest()
    assert len(caught.value.provenance) == 1


@pytest.mark.parametrize("kind", ["missing", "symlink", "directory", "empty"])
def test_invalid_generated_output_fails_with_partial_provenance(helper, build, kind):
    root, _, _, command = build
    normal = command.side_effect

    def run(args, **kwargs):
        result = normal(args, **kwargs)
        if args[1] != "mig":
            return result
        target = root / OUTPUTS[1]
        target.unlink()
        if kind == "symlink":
            target.symlink_to(root / OUTPUTS[0])
        elif kind == "directory":
            target.mkdir()
        elif kind == "empty":
            target.touch()
        return result

    command.side_effect = run
    with pytest.raises(RuntimeError, match="outputs") as caught:
        helper.prepare(root, command)
    assert len(caught.value.provenance) == 2
    assert caught.value.provenance[-1]["path"] == str(root / OUTPUTS[0])


def test_existing_destinations_are_never_overwritten(helper, build):
    root, _, _, command = build
    target = root / OUTPUTS[0]
    target.write_bytes(b"keep")
    with pytest.raises(RuntimeError, match="root"):
        helper.prepare(root, command)
    assert target.read_bytes() == b"keep"
    command.assert_not_called()


def test_shared_or_symlink_buildroot_rejected(helper, build, tmp_path):
    root, _, _, command = build
    root.chmod(0o755)
    with pytest.raises(RuntimeError, match="root"):
        helper.prepare(root, command)
    root.chmod(0o700)
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(RuntimeError, match="root"):
        helper.prepare(alias, command)
    command.assert_not_called()


def test_nonzero_generator_status_is_not_success(helper, build):
    root, _, _, command = build
    normal = command.side_effect

    def run(args, **kwargs):
        if args[1] == "mig":
            return subprocess.CompletedProcess(args, 7, "", "generation rejected")
        return normal(args, **kwargs)

    command.side_effect = run
    with pytest.raises(RuntimeError, match=r"generate.*status 7") as caught:
        helper.prepare(root, command)
    assert len(caught.value.provenance) == 1


def test_mutated_snapshot_is_never_accepted(helper, build):
    root, _, _, command = build
    normal = command.side_effect

    def run(args, **kwargs):
        result = normal(args, **kwargs)
        if args[1] == "mig":
            captured = root / "mach_exc.defs"
            captured.chmod(0o600)
            captured.write_bytes(b"mutated snapshot")
        return result

    command.side_effect = run
    with pytest.raises(RuntimeError, match=r"outputs.*snapshot changed") as caught:
        helper.prepare(root, command)
    assert len(caught.value.provenance) == 1


def test_oversize_defs_rejected_before_capture(helper, build):
    root, _, defs, command = build
    with defs.open("wb") as stream:
        stream.truncate(4 * 1024 * 1024 + 1)
    with pytest.raises(RuntimeError, match=r"input.*invalid regular file"):
        helper.prepare(root, command)
    assert not (root / "mach_exc.defs").exists()
