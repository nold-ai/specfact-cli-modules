"""Bounded read-only Mach-O inventory contract; inputs are never executed."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/native_runtime_inventory.py"
MAGIC = bytes.fromhex("cffaedfe")


@pytest.fixture(name="inventory_module")
def load_inventory_module():
    spec = importlib.util.spec_from_file_location("native_runtime_inventory", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def commands(kind="EXECUTE", loads=(), rpaths=(), identity=None):
    entries = [("LC_LOAD_DYLIB", "name", name) for name in loads]
    entries += [("LC_RPATH", "path", name) for name in rpaths]
    if identity:
        entries.append(("LC_ID_DYLIB", "name", identity))
    body = "".join(
        (
            f"Load command {i}\n cmd {cmd}\n cmdsize 256\n {field} {name} (offset 24)\n"
            for i, (cmd, field, name) in enumerate(entries)
        )
    )
    return (
        "image:\nMach header\n magic cputype cpusubtype caps filetype ncmds sizeofcmds flags\n"
        f"MH_MAGIC_64 ARM64 ALL 0x00 {kind} {len(entries)} {256 * len(entries)} NOUNDEFS\n" + body
    )


def payload(tmp_path, images):
    for name in images:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(MAGIC + name.encode())
    return tmp_path


def inspect_mock(images, architectures="arm64"):

    def inspect(argv):
        assert argv[0] in ("/usr/bin/lipo", "/usr/bin/otool")
        assert Path(argv[-1]).is_absolute()
        if argv[0] == "/usr/bin/lipo":
            assert argv[1] == "-archs"
            return architectures
        assert argv[1:5] == ["-arch", "arm64", "-hv", "-l"]
        return images[Path(argv[-1]).name]

    return inspect


def test_arm64_closure_hashes_ids_and_inherited_rpaths(inventory_module, tmp_path):
    images = {
        "app": commands(loads=["@rpath/libA.dylib"], rpaths=["@executable_path/../lib"]),
        "libA.dylib": commands("DYLIB", ["@rpath/libB.dylib"], identity="@rpath/libA.dylib"),
        "libB.dylib": commands("DYLIB", ["/usr/lib/libSystem.B.dylib"]),
    }
    payload(tmp_path, ["bin/app", "lib/libA.dylib", "lib/libB.dylib"])
    with patch.object(inventory_module, "inspect_tool", side_effect=inspect_mock(images, "x86_64 arm64")):
        result = inventory_module.inventory(tmp_path)
    assert result["production_eligible"] is False
    assert result["sandbox_verified"] is False
    app = next(image for image in result["images"] if image["path"] == "bin/app")
    assert app["architectures"] == ["x86_64", "arm64"]
    assert app["sha256"] == hashlib.sha256((tmp_path / "bin/app").read_bytes()).hexdigest()
    assert len(result["resolutions"]) == 3
    assert result["resolutions"][1]["resolved"] == "lib/libB.dylib"


@pytest.mark.parametrize("architectures", ["x86_64", "arm64e", "arm64 garbage!", "", "arm64 arm64"])
def test_architecture_is_not_inferred_from_filename(inventory_module, tmp_path, architectures):
    payload(tmp_path, ["arm64-native"])
    with (
        patch.object(inventory_module, "inspect_tool", return_value=architectures),
        pytest.raises(inventory_module.InventoryError, match=r"architecture|arm64"),
    ):
        inventory_module.inventory(tmp_path)


@pytest.mark.parametrize(
    "load",
    [
        "/opt/homebrew/lib/a.dylib",
        "a.dylib",
        "@unknown/a",
        "@rpath/missing",
        "@loader_path/missing",
        "/usr/lib/../../tmp/a",
        "/usr/library/a",
    ],
)
def test_ambient_missing_and_unsafe_loads_fail(inventory_module, tmp_path, load):
    payload(tmp_path, ["app"])
    with (
        patch.object(inventory_module, "inspect_tool", side_effect=inspect_mock({"app": commands(loads=[load])})),
        pytest.raises(inventory_module.InventoryError),
    ):
        inventory_module.inventory(tmp_path)


@pytest.mark.parametrize("rpath", ["/opt/homebrew/lib", ".", "@rpath/lib", "@loader_path/../../outside"])
def test_unsafe_unused_rpath_fails(inventory_module, tmp_path, rpath):
    payload(tmp_path, ["app"])
    with (
        patch.object(inventory_module, "inspect_tool", side_effect=inspect_mock({"app": commands(rpaths=[rpath])})),
        pytest.raises(inventory_module.InventoryError),
    ):
        inventory_module.inventory(tmp_path)


def test_loader_and_executable_contexts_remain_distinct(inventory_module, tmp_path):
    images = {
        "app": commands(loads=["@loader_path/../lib/a"]),
        "a": commands("DYLIB", ["@loader_path/b", "@executable_path/helper"]),
        "b": commands("DYLIB"),
        "helper": commands("DYLIB"),
    }
    payload(tmp_path, ["bin/app", "lib/a", "lib/b", "bin/helper"])
    with patch.object(inventory_module, "inspect_tool", side_effect=inspect_mock(images)):
        result = inventory_module.inventory(tmp_path)
    assert {row["resolved"] for row in result["resolutions"]} == {"lib/a", "lib/b", "bin/helper"}


def test_each_executable_context_is_checked(inventory_module, tmp_path):
    images = {
        "one": commands(loads=["@loader_path/../lib/a"]),
        "two": commands(loads=["@loader_path/../lib/a"]),
        "a": commands("DYLIB", ["@executable_path/helper"]),
        "helper": commands("DYLIB"),
    }
    payload(tmp_path, ["bin/one", "other/two", "lib/a", "bin/helper"])
    with (
        patch.object(inventory_module, "inspect_tool", side_effect=inspect_mock(images)),
        pytest.raises(inventory_module.InventoryError, match="helper"),
    ):
        inventory_module.inventory(tmp_path)


def test_orphan_library_cannot_invent_executable_context(inventory_module, tmp_path):
    payload(tmp_path, ["a"])
    with (
        patch.object(
            inventory_module, "inspect_tool", side_effect=inspect_mock({"a": commands("DYLIB", ["@executable_path/a"])})
        ),
        pytest.raises(inventory_module.InventoryError, match="executable"),
    ):
        inventory_module.inventory(tmp_path)


def test_symlink_escape_rejected_before_tools(inventory_module, tmp_path):
    (tmp_path / "escape").symlink_to("/usr/bin/true")
    with patch.object(inventory_module, "inspect_tool") as tool:
        with pytest.raises(inventory_module.InventoryError, match="escape"):
            inventory_module.inventory(tmp_path)
        tool.assert_not_called()


def test_internal_alias_and_cycle_are_bounded(inventory_module, tmp_path):
    payload(tmp_path, ["app", "lib/a"])
    (tmp_path / "alias").symlink_to("lib/a")
    images = {"app": commands(loads=["@loader_path/alias"]), "a": commands("DYLIB", ["@loader_path/a"])}
    with patch.object(inventory_module, "inspect_tool", side_effect=inspect_mock(images)):
        result = inventory_module.inventory(tmp_path)
    assert len(result["images"]) == 2
    assert len(result["resolutions"]) == 2


@pytest.mark.parametrize(
    "output",
    [
        "",
        "not Mach-O",
        commands(loads=["x"]).replace("LC_LOAD_DYLIB", "0x80000099"),
        commands(loads=["x"]).replace("name x (offset 24)", "name x"),
        commands(loads=["x"]).replace("Load command 0", "Load command 2"),
        commands(loads=["x"]).replace("cmdsize 256", "cmdsize 8"),
        commands(loads=["x"]) + "error: truncated\n",
    ],
)
def test_malformed_inspection_fails(inventory_module, tmp_path, output):
    payload(tmp_path, ["app"])
    with (
        patch.object(inventory_module, "inspect_tool", side_effect=inspect_mock({"app": output})),
        pytest.raises(inventory_module.InventoryError),
    ):
        inventory_module.inventory(tmp_path)


@pytest.mark.parametrize(
    "command", ["LC_LOAD_WEAK_DYLIB", "LC_REEXPORT_DYLIB", "LC_LOAD_UPWARD_DYLIB", "LC_LAZY_LOAD_DYLIB"]
)
def test_all_dylib_load_variants_are_dependencies(inventory_module, tmp_path, command):
    payload(tmp_path, ["app"])
    output = commands(loads=["@loader_path/missing"]).replace("LC_LOAD_DYLIB", command)
    with (
        patch.object(inventory_module, "inspect_tool", side_effect=inspect_mock({"app": output})),
        pytest.raises(inventory_module.InventoryError, match="missing"),
    ):
        inventory_module.inventory(tmp_path)


def test_limits_and_non_macho_dependency(inventory_module, tmp_path):
    payload(tmp_path, ["app"])
    (tmp_path / "text").write_text("not a dylib")
    with (
        patch.object(inventory_module, "MAX_ENTRIES", 1),
        pytest.raises(inventory_module.InventoryError, match="limit"),
    ):
        inventory_module.inventory(tmp_path)
    with (
        patch.object(
            inventory_module, "inspect_tool", side_effect=inspect_mock({"app": commands(loads=["@loader_path/text"])})
        ),
        pytest.raises(inventory_module.InventoryError, match="Mach-O"),
    ):
        inventory_module.inventory(tmp_path)


def test_cli_json_failure_never_admits_production(inventory_module, tmp_path, capsys):
    assert inventory_module.main([str(tmp_path)]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["production_eligible"] is False
    assert result["ok"] is False
    assert result["errors"]


def test_tool_failure_is_actionable(inventory_module):
    with (
        patch.object(inventory_module.subprocess, "Popen", side_effect=OSError("unavailable")),
        pytest.raises(inventory_module.InventoryError, match="unavailable"),
    ):
        inventory_module.inspect_tool(["/usr/bin/lipo", "-archs", "/missing"])


@pytest.mark.skipif(sys.platform != "darwin", reason="Apple inspection tools required")
def test_real_system_binary_is_only_inspected(inventory_module, tmp_path):
    shutil.copyfile("/usr/bin/true", tmp_path / "true")
    archs = inventory_module.inspect_tool(["/usr/bin/lipo", "-archs", str(tmp_path / "true")]).split()
    if "arm64" not in archs:
        with pytest.raises(inventory_module.InventoryError, match="arm64"):
            inventory_module.inventory(tmp_path)
    else:
        assert inventory_module.inventory(tmp_path)["ok"] is True


@pytest.mark.parametrize(
    "chunks,returncode,message", [([b"x" * 65], 0, "limit"), ([b""], 2, "failed"), ([b"\xff", b""], 0, "failed")]
)
def test_tool_output_failures_are_bounded(inventory_module, chunks, returncode, message):
    process = MagicMock()
    process.__enter__.return_value = process
    process.wait.return_value = returncode
    process.poll.return_value = 0
    selector = MagicMock()
    selector.__enter__.return_value = selector
    selector.select.return_value = [object()]
    with (
        patch.object(inventory_module.subprocess, "Popen", return_value=process) as popen,
        patch.object(inventory_module.selectors, "DefaultSelector", return_value=selector),
        patch.object(inventory_module.os, "read", side_effect=chunks),
        patch.object(inventory_module, "MAX_OUTPUT", 64),
        pytest.raises(inventory_module.InventoryError, match=message),
    ):
        inventory_module.inspect_tool(["/usr/bin/lipo", "-archs", "/payload/app"])
    assert popen.call_args.kwargs["env"] == {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}
    assert popen.call_args.kwargs["stdin"] == subprocess.DEVNULL


def test_tool_timeout_kills_and_reaps_inspector(inventory_module):
    process = MagicMock()
    process.__enter__.return_value = process
    process.poll.return_value = None
    selector = MagicMock()
    selector.__enter__.return_value = selector
    selector.select.return_value = []
    with (
        patch.object(inventory_module.subprocess, "Popen", return_value=process),
        patch.object(inventory_module.selectors, "DefaultSelector", return_value=selector),
        pytest.raises(inventory_module.InventoryError, match="timeout"),
    ):
        inventory_module.inspect_tool(["/usr/bin/otool", "-l", "/payload/app"])
    process.kill.assert_called_once()
    process.wait.assert_called_once_with(timeout=1)
    assert 0 < selector.select.call_args.args[0] <= inventory_module.TOOL_TIMEOUT


def test_plain_word_architecture_diagnostic_rejected(inventory_module, tmp_path):
    payload(tmp_path, ["app"])
    with (
        patch.object(inventory_module, "inspect_tool", side_effect=inspect_mock({"app": commands()}, "arm64 garbage")),
        pytest.raises(inventory_module.InventoryError, match="architecture"),
    ):
        inventory_module.inventory(tmp_path)


def test_system_edges_count_toward_context_bound(inventory_module, tmp_path):
    payload(tmp_path, ["app"])
    images = {"app": commands(loads=["/usr/lib/libSystem.B.dylib"] * 3)}
    with (
        patch.object(inventory_module, "inspect_tool", side_effect=inspect_mock(images)),
        patch.object(inventory_module, "MAX_CONTEXTS", 2),
        pytest.raises(inventory_module.InventoryError, match="limit"),
    ):
        inventory_module.inventory(tmp_path)


@pytest.mark.skipif(sys.platform != "darwin", reason="Apple compiler and inspection tools required")
def test_real_compiled_arm64_is_only_inspected(inventory_module, tmp_path):
    executable = tmp_path / "fixture"
    subprocess.run(
        ["/usr/bin/clang", "-arch", "arm64", "-x", "c", "-", "-o", str(executable)],
        input="int main(void) { return 0; }\n",
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
        env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
    )
    result = inventory_module.inventory(tmp_path)
    assert result["ok"] is True
    assert result["images"][0]["architectures"] == ["arm64"]
    assert result["images"][0]["filetype"] == "EXECUTE"
    assert result["production_eligible"] is False
    assert any(edge["resolved"] == "/usr/lib/libSystem.B.dylib" for edge in result["resolutions"])


def test_malformed_dylib_string_offset_rejected(inventory_module, tmp_path):
    payload(tmp_path, ["app"])
    output = commands(loads=["/usr/lib/libSystem.B.dylib"]).replace("offset 24", "offset 8")
    with (
        patch.object(inventory_module, "inspect_tool", side_effect=inspect_mock({"app": output})),
        pytest.raises(inventory_module.InventoryError, match="Invalid name"),
    ):
        inventory_module.inventory(tmp_path)


def test_filename_containing_unknown_is_not_diagnostic(inventory_module, tmp_path):
    payload(tmp_path, ["unknown-app"])
    output = commands(loads=["/usr/lib/libSystem.B.dylib"]).replace("image:", "unknown-app:")
    with patch.object(inventory_module, "inspect_tool", side_effect=inspect_mock({"unknown-app": output})):
        assert inventory_module.inventory(tmp_path)["ok"] is True


def test_inspection_atime_change_does_not_invalidate_content(inventory_module, tmp_path):
    payload(tmp_path, ["app"])
    inspector = inspect_mock({"app": commands()})

    def inspect(argv):
        path = Path(argv[-1])
        info = path.stat()
        inventory_module.os.utime(path, ns=(info.st_atime_ns + 1000000000, info.st_mtime_ns))
        return inspector(argv)

    with patch.object(inventory_module, "inspect_tool", side_effect=inspect):
        assert inventory_module.inventory(tmp_path)["ok"] is True


def test_directory_enumeration_stops_at_entry_budget(inventory_module, tmp_path, monkeypatch):
    """A large directory is not materialized before enforcing the scan budget."""
    for number in range(20):
        (tmp_path / f"entry-{number}").write_text("")
    consumed = []
    original = inventory_module.os.scandir

    @contextmanager
    def counted(directory):
        with original(directory) as entries:

            def observe():
                for entry in entries:
                    consumed.append(entry.name)
                    yield entry

            yield observe()

    monkeypatch.setattr(inventory_module.os, "scandir", counted)
    monkeypatch.setattr(inventory_module, "MAX_ENTRIES", 2)
    with pytest.raises(inventory_module.InventoryError, match="entry limit"):
        inventory_module.payload_files(tmp_path)
    assert len(consumed) == 3
