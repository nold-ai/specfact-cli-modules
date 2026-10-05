"""Actual native parser admission for the packaged SCM child."""

import plistlib
import subprocess
import sys
from pathlib import Path

import pytest


NATIVE = Path(__file__).resolve().parents[2] / "packages/specfact-code-review/native/macos-arm64"
pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="CoreFoundation parser requires macOS")


@pytest.fixture(scope="module")
def parser(tmp_path_factory):
    root = tmp_path_factory.mktemp("git-parser")
    source = root / "parser.c"
    native = (NATIVE / "managed_workers.inc").read_text().split("static void worker_reply(", 1)[0]
    source.write_text(
        '#include "native_protocol.h"\n#include "git_child_policy.h"\n'
        "#include <CoreFoundation/CoreFoundation.h>\n#include <stdio.h>\n#include <stdlib.h>\n"
        "#include <string.h>\n#include <sys/stat.h>\n"
        "struct worker { struct specfact_request grant; };\n"
        "static int beneath(const char *p,const char *r) { size_t n=strlen(r); return !strncmp(p,r,n)&&p[n]=='/'; }\n"
        + native
        + "\nint main(int argc,char **argv) { if(argc!=5)return 2; struct worker owner={0};"
        "strlcpy(owner.grant.project,argv[2],SPECFACT_MAX_PATH);"
        "strlcpy(owner.grant.output,argv[3],SPECFACT_MAX_PATH);"
        "strlcpy(owner.grant.temporary,argv[4],SPECFACT_MAX_PATH);"
        'unsigned char payload[SPECFACT_WORKER_PAYLOAD]; FILE *f=fopen(argv[1],"rb"); if(!f)return 2;'
        "size_t n=fread(payload,1,sizeof(payload),f); fclose(f); int input=0,merge=0;"
        "return launch_document(&owner,payload,(uint32_t)n,&input,&merge)==3 ? 0 : 1; }\n"
    )
    binary = root / "parser"
    subprocess.run(
        ["xcrun", "clang", "-I", str(NATIVE), str(source), "-framework", "CoreFoundation", "-o", str(binary)],
        check=True,
        capture_output=True,
    )
    return binary


@pytest.mark.parametrize(
    "mutation",
    [
        None,
        "transport",
        "config",
        "dir",
        "env",
        "paths",
        "prefix",
        "identity",
        "broken",
        "cwd",
        "ref-write",
        "xdg",
        "locale",
    ],
)
def test_native_git_requests_confine_queries_and_configuration(parser, tmp_path, mutation):
    roots = tuple((tmp_path / name).resolve() for name in ("project", "output", "temporary"))
    for root in roots:
        root.mkdir()
    (roots[0] / ".git").mkdir()
    request = {
        "program": "git",
        "argv": ["--git-dir", str(roots[0] / ".git"), "describe", "--dirty", "--tags", "--long", "--match", "hatch-v*"],
        "cwd": "project",
        "environment": {"LANG": "C"},
        "stdin_pipe": False,
        "merge_stderr": False,
        "python_paths": [],
        "python_prefix": "",
        "python_alias": "",
    }
    if mutation == "transport":
        request["argv"] = ["fetch"]
    elif mutation == "config":
        request["argv"] = ["-c", "alias.q=!true", "q"]
    elif mutation == "dir":
        request["argv"][1] = "/usr"
    elif mutation == "env":
        request["environment"]["GIT_CONFIG_COUNT"] = "1"
    elif mutation == "xdg":
        request["environment"]["XDG_CONFIG_HOME"] = "/host/config"
    elif mutation == "locale":
        request["environment"]["LC_ALL"] = "untrusted-locale"
    elif mutation == "paths":
        request["python_paths"] = [str(roots[0])]
    elif mutation == "prefix":
        request.update(python_prefix=str(roots[2]), python_alias="python")
    elif mutation == "identity":
        request["program"] = "/usr/bin/git"
    elif mutation == "broken":
        request["argv"] = ["describe", "--broken"]
    elif mutation == "cwd":
        request["cwd"] = "project/../output"
    elif mutation == "ref-write":
        request["argv"] = ["symbolic-ref", "HEAD", "refs/heads/new"]
    document = tmp_path / "request.plist"
    document.write_bytes(plistlib.dumps(request, fmt=plistlib.FMT_BINARY))
    result = subprocess.run([str(parser), str(document), *map(str, roots)], capture_output=True)
    assert result.returncode == (0 if mutation is None else 1)
