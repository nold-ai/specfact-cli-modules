"""Exercise the actual native worker request parser with private uv grants."""

import plistlib
import subprocess
import sys
from pathlib import Path

import pytest


NATIVE = Path(__file__).resolve().parents[2] / "packages/specfact-code-review/native/macos-arm64"
pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="native CoreFoundation parser requires macOS")


@pytest.fixture(scope="module")
def parser(tmp_path_factory):
    root = tmp_path_factory.mktemp("uv-child-parser")
    source = root / "parser.c"
    native = (NATIVE / "managed_workers.inc").read_text().split("static void worker_reply(", 1)[0]
    source.write_text(
        '#include "native_protocol.h"\n'
        "#include <CoreFoundation/CoreFoundation.h>\n"
        "#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n#include <sys/stat.h>\n"
        "struct worker { struct specfact_request grant; };\n"
        "static int beneath(const char *p,const char *r) { size_t n=strlen(r); return !strncmp(p,r,n)&&p[n]=='/'; }\n"
        + native
        + "\nint main(int argc,char **argv) { if(argc!=5)return 2; struct worker owner={0};\n"
        "strlcpy(owner.grant.project,argv[2],SPECFACT_MAX_PATH);"
        "strlcpy(owner.grant.output,argv[3],SPECFACT_MAX_PATH);"
        "strlcpy(owner.grant.temporary,argv[4],SPECFACT_MAX_PATH);\n"
        'unsigned char payload[SPECFACT_WORKER_PAYLOAD]; FILE *f=fopen(argv[1],"rb"); if(!f)return 2;'
        "size_t n=fread(payload,1,sizeof(payload),f); fclose(f); int input=0,merge=0;"
        "int program=launch_document(&owner,payload,(uint32_t)n,&input,&merge); if(!program)return 1;"
        "if(program==2) {struct specfact_uv_child_startup startup; uint32_t length=0;"
        "if(!uv_startup_document(&owner,payload,(uint32_t)n,&startup,&length))return 1;"
        "fwrite(&startup,1,length,stdout);} return 0; }\n"
    )
    binary = root / "parser"
    subprocess.run(
        ["xcrun", "clang", "-I", str(NATIVE), str(source), "-framework", "CoreFoundation", "-o", str(binary)],
        check=True,
        capture_output=True,
    )
    return binary


def request_for(roots):
    project, _output, temporary = roots
    return {
        "program": "uv",
        "argv": ["venv", str(temporary / "environment")],
        "cwd": "project",
        "environment": {
            "UV_OFFLINE": "1",
            "UV_NO_INDEX": "1",
            "UV_FIND_LINKS": str(project / "wheelhouse"),
            "UV_CACHE_DIR": str(temporary / "uv-cache"),
            "UV_PYTHON_DOWNLOADS": "never",
            "UV_KEYRING_PROVIDER": "disabled",
            "UV_LINK_MODE": "copy",
        },
        "stdin_pipe": False,
        "merge_stderr": False,
        "python_paths": [],
        "python_prefix": "",
        "python_alias": "",
    }


@pytest.mark.parametrize(
    "mutation",
    [
        None,
        "network",
        "wheelhouse",
        "cwd",
        "prefix",
        "paths",
        "identity",
        "credential",
        "lowercase-credential",
        "channel",
        "path",
        "virtual-env",
        "expansion",
    ],
)
def test_native_uv_request_uses_only_offline_private_grants(parser, tmp_path, mutation):
    roots = tuple(tmp_path / name for name in ("project", "output", "temporary"))
    for root in roots:
        root.mkdir()
    (roots[0] / "wheelhouse").mkdir()
    request = request_for(roots)
    if mutation == "network":
        request["environment"]["UV_OFFLINE"] = "0"
    elif mutation == "wheelhouse":
        request["environment"]["UV_FIND_LINKS"] = "/host/wheels"
    elif mutation == "cwd":
        request["cwd"] = "project/../output"
    elif mutation == "prefix":
        request["python_prefix"] = str(roots[2])
        request["python_alias"] = "python"
    elif mutation == "paths":
        request["python_paths"] = [str(roots[0])]
    elif mutation == "identity":
        request["program"] = "/capsule/tools/uv"
    elif mutation == "credential":
        request["environment"]["UV_INDEX_TOKEN"] = "denied"
    elif mutation == "lowercase-credential":
        request["environment"]["private_token"] = "denied"
    elif mutation == "channel":
        request["environment"]["SPECFACT_MANAGED_CAPSULE"] = "/host/capsule"
    elif mutation == "path":
        request["environment"]["PATH"] = "/usr/bin"
    elif mutation == "virtual-env":
        request["environment"]["VIRTUAL_ENV"] = "/host/environment"
    elif mutation == "expansion":
        request["argv"] = ["x" * 100] * 60
    document = tmp_path / "request.plist"
    document.write_bytes(plistlib.dumps(request, fmt=plistlib.FMT_BINARY))
    result = subprocess.run([str(parser), str(document), *(str(root) for root in roots)], capture_output=True)
    assert result.returncode == (0 if mutation is None else 1)
    if mutation is None:
        import struct

        argc, envc = struct.unpack("<II", result.stdout[:8])
        strings = result.stdout[8:].split(b"\0")
        assert (argc, envc) == (2, 0)
        assert strings == [str(roots[0]).encode(), b"venv", str(roots[2] / "environment").encode(), b""]


def test_managed_uv_compact_launch_round_trips_through_native_parser(parser, tmp_path):
    import os
    import shutil

    rustc = shutil.which("rustc")
    assert rustc is not None, "native managed uv regression requires a Rust compiler"
    binary = tmp_path / "managed-uv-tests"
    subprocess.run(
        [rustc, "--edition=2021", "--test", str(NATIVE / "uv_managed.rs"), "-o", str(binary)],
        check=True,
        capture_output=True,
        timeout=60,
    )
    roots = tuple(tmp_path / (name + " space λ") for name in ("project", "output", "temporary"))
    for root in roots:
        root.mkdir()
    capsule = tmp_path / "capsule"
    (capsule / "python/bin").mkdir(parents=True)
    environment = {"PATH": os.defpath, "SPECFACT_MANAGED_CAPSULE": str(capsule)}
    environment.update(
        {
            "SPECFACT_MANAGED_" + name.upper(): str(root)
            for name, root in zip(("project", "output", "temporary"), roots, strict=True)
        }
    )
    result = subprocess.run(
        [str(binary), "--exact", "tests::managed_python_launch_retains_large_xml_fields_in_fixed_frame", "--nocapture"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    encoded = next(line.removeprefix("REQUEST=") for line in result.stdout.splitlines() if line.startswith("REQUEST="))
    payload = bytes.fromhex(encoded)
    document = plistlib.loads(payload)
    assert len(plistlib.dumps(document)) > 4096
    assert len(payload) <= 4096
    assert document["program"] == "python" and document["cwd"] == "project"
    assert document["argv"] == ["-c", 'print("' + "<literal>&" * 70 + '")']
    for index in range(30):
        assert document["environment"][f"BUILD_SETTING_{index}"] == "literal<&>" * 10
    request = tmp_path / "request.plist"
    request.write_bytes(payload)
    parsed = subprocess.run(
        [str(parser), str(request), *(str(root) for root in roots)], capture_output=True, timeout=10
    )
    assert parsed.returncode == 0
