"""Exercise actual native admission sinks under a larger realpath allocation contract."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest


NATIVE = Path(__file__).resolve().parents[2] / "packages/specfact-code-review/native/macos-arm64"


@pytest.mark.parametrize("sink", ["bootstrap", "git", "inherited"])
def test_native_canonical_sinks_use_system_allocation_and_preserve_rejection(tmp_path: Path, sink: str) -> None:
    if sink == "bootstrap":
        source = (NATIVE / "bootstrap.c").read_text()
        block = source.split("char *cwd = startup_string(&cursor, end)", 1)[1].split("const char *roots[]", 1)[0]
        # Reuse the actual admission block before any private-root/chdir/exec action.
        block = re.sub(r"^, canonical\[SPECFACT_MAX_PATH\];", "", block)
        block = block.lstrip(";")
        body = "static int admit(const char *cwd) {" + block + " return 0; }\n"
        call = "admit(argv[1]) == 0"
    elif sink == "git":
        body = '#include "git_child_policy.h"\n'
        call = "specfact_git_private_path(argv[1], argv[1], &request, selected) == 1"
    else:
        source = (NATIVE / "managed_workers.inc").read_text()
        body = "struct worker { struct specfact_request grant; };\n"
        body += "static int beneath(const char *p,const char *r) { size_t n=strlen(r); return !strncmp(p,r,n)&&p[n]=='/'; }\n"
        body += source.split("static int inherited_path(", 1)[1].split("static int inherited_python_path", 1)[0]
        body = body.replace("const struct worker *owner", "const struct worker *owner", 1)
        body = (
            body[: body.index("const struct worker")]
            + "static int inherited_path("
            + body[body.index("const struct worker") :]
        )
        call = "inherited_path(&owner, argv[1]) == 1"
    header = '#include "canonical_path.h"\n' if (NATIVE / "canonical_path.h").exists() else ""
    source = tmp_path / "canonical.c"
    source.write_text(
        r"""
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include "native_protocol.h"
static unsigned allocations, releases;
static char *modeled_realpath(const char *path, char *destination) {
    /* Focused larger-libc substitute, not an observed macOS overflow. */
    assert(destination == NULL);
    if (strstr(path, "missing")) return NULL;
    char *resolved = malloc(4096);
    assert(resolved);
    allocations++;
    if (strstr(path, "alias")) strcpy(resolved, "/different/canonical/path");
    else strcpy(resolved, path);
    return resolved;
}
static void tracked_free(void *pointer) { if (pointer) releases++; free(pointer); }
#define realpath modeled_realpath
#define free tracked_free
"""
        + header
        + body
        + r"""
int main(int argc, char **argv) {
    assert(argc == 3);
    struct specfact_request request = {0};
    snprintf(request.project, sizeof(request.project), "%s", argv[1]);
    char selected[SPECFACT_MAX_PATH];
    struct worker_placeholder { struct specfact_request grant; };
"""
        + ("struct worker owner={0}; owner.grant=request;\n" if sink == "inherited" else "")
        + f"int admitted = ({call});\n"
        + "assert(admitted == atoi(argv[2])); assert(allocations == releases); return 0; }\n"
    )
    binary = tmp_path / "canonical"
    subprocess.run(
        [
            "cc",
            "-std=c11",
            "-D_XOPEN_SOURCE=700",
            "-Wall",
            "-Wextra",
            "-Wno-unused-variable",
            "-I",
            str(NATIVE),
            str(source),
            "-o",
            str(binary),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    directory = tmp_path / "ordinary"
    directory.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(directory, target_is_directory=True)
    for value, expected in [(directory, "1"), (alias, "0"), (tmp_path / "missing", "0")]:
        subprocess.run([str(binary), str(value), expected], check=True, capture_output=True, text=True, timeout=5)


@pytest.mark.parametrize("spelling", ["canonical", "alias", "relative", "dot", "missing", "overlong", "null"])
def test_allocated_canonical_predicate_preserves_real_filesystem_policy(tmp_path: Path, spelling: str) -> None:
    source = tmp_path / "filesystem.c"
    binary = tmp_path / "filesystem"
    source.write_text(
        '#include "canonical_path.h"\n#include <stdio.h>\nint main(int argc,char **argv) { if(argc!=3)return 2; const char *p=!strcmp(argv[1],"NULL")?NULL:argv[1]; return specfact_canonical_path(p)!=atoi(argv[2]); }\n'
    )
    subprocess.run(
        [
            "cc",
            "-std=c11",
            "-D_XOPEN_SOURCE=700",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(NATIVE),
            str(source),
            "-o",
            str(binary),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    directory = (tmp_path / "ordinary").resolve()
    directory.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(directory, target_is_directory=True)
    values = {
        "canonical": str(directory),
        "alias": str(alias),
        "relative": "ordinary",
        "dot": str(directory) + "/.",
        "missing": str(tmp_path / "missing"),
        "overlong": "/" + "x" * 1024,
        "null": "NULL",
    }
    subprocess.run(
        [str(binary), values[spelling], "1" if spelling == "canonical" else "0"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
