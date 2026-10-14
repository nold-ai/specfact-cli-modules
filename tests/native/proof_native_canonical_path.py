"""Exercise actual native admission sinks under a larger realpath allocation contract."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

import pytest

from tests.unit.test_macos_managed_control import _ControlTestCase


NATIVE = Path(__file__).resolve().parents[2] / "packages/specfact-code-review/native/macos-arm64"


def _canonical_sink_admission(sink: str) -> tuple[str, str]:
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
        body += (
            "static int beneath(const char *p,const char *r) { size_t n=strlen(r); "
            "return !strncmp(p,r,n)&&p[n]=='/'; }\n"
        )
        body += source.split("static int inherited_path(", 1)[1].split("static int inherited_python_path", 1)[0]
        body = body.replace("const struct worker *owner", "const struct worker *owner", 1)
        body = (
            body[: body.index("const struct worker")]
            + "static int inherited_path("
            + body[body.index("const struct worker") :]
        )
        call = "inherited_path(&owner, argv[1]) == 1"
    return body, call


def _write_canonical_sink_source(tmp_path: Path, sink: str, body: str, call: str) -> Path:
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
    return source


@pytest.mark.parametrize("sink", ["bootstrap", "git", "inherited"])
def test_native_canonical_sinks_use_system_allocation_and_preserve_rejection(tmp_path: Path, sink: str) -> None:
    body, call = _canonical_sink_admission(sink)
    source = _write_canonical_sink_source(tmp_path, sink, body, call)
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
        '#include "canonical_path.h"\n#include <stdio.h>\n'
        'int main(int argc,char **argv) { if(argc!=3)return 2; const char *p=!strcmp(argv[1],"NULL")?NULL:argv[1]; '
        "return specfact_canonical_path(p)!=atoi(argv[2]); }\n"
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


class NativeControlTests(_ControlTestCase):
    @unittest.skipUnless(os.environ.get("SPECFACT_NATIVE_CONTROL") == "1", "explicit native fixture run")
    def test_withheld_eof_cannot_pass_via_worker_timeout(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp", prefix="sf-eof-negative-") as temporary:
            root = Path(temporary).resolve()
            broker, observer, _inventory = self.control.build(root)
            with self.control.Invocation(broker, observer, root) as invocation:
                self._reject_withheld_eof(invocation)

    def _reject_withheld_eof(self, invocation):
        client = invocation.connect()
        launched = client.launch()
        identity = invocation.capture_worker(launched)
        held = client.stream.dup()
        try:
            client.stream.sendall(
                self.control.frame(client.capability, 2, self.control.FrameFields(handle=launched["handle"]))
            )
            deadline = self.control.cleanup_deadline(launched)
            started = self.control.time.monotonic()
            client.close()
            with self.assertRaisesRegex(RuntimeError, "survivor/job failure"):
                self.control.observe_absence(invocation, identity, started, job=True, native_deadline_ns=deadline)
            self.assertTrue(self.control.STARTUP.alive(invocation.observer, identity))
            self.assertLess(
                self.control.time.clock_gettime_ns(self.control.time.CLOCK_MONOTONIC), launched["deadline_ns"]
            )
        finally:
            held.close()

    @unittest.skipUnless(os.environ.get("SPECFACT_NATIVE_CONTROL") == "1", "explicit native fixture run")
    def test_held_cancellation_is_independently_observed_lifecycle_case(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp", prefix="sf-control-held-case-") as temporary:
            root = Path(temporary).resolve()
            broker, observer, _inventory = self.control.build(root)
            result = self.control.lifecycle_trial(broker, observer, root, "cancel-held-stop")
            self.assertTrue(result["passed"])
            self.assertEqual(result["status"]["signal"], 9)
            self.assertEqual(result["status"]["reason"], "cancel")
            self.assertLessEqual(result["observation_seconds"], 5)

    @unittest.skipUnless(os.environ.get("SPECFACT_NATIVE_CONTROL") == "1", "explicit native fixture run")
    def test_held_initial_exception_can_be_cancelled(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp", prefix="sf-control-held-") as temporary:
            root = Path(temporary).resolve()
            broker, observer, _inventory = self.control.build(root)
            with self.control.Invocation(broker, observer, root) as invocation:
                client = invocation.connect()
                launched = client.launch(4)
                invocation.capture_worker(launched, 4)
                self.assertTrue(client.request(4, handle=launched["handle"])["ok"])
                result = client.request(2, handle=launched["handle"])
                self.assertEqual(result["signal"], 9)
                self.assertEqual(result["reason"], "cancel")
                self.assertEqual(result["exit"], -1)

    @unittest.skipUnless(os.environ.get("SPECFACT_NATIVE_CONTROL") == "1", "explicit native fixture run")
    def test_actual_runtime_trap_preserves_signal(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp", prefix="sf-control-trap-") as temporary:
            root = Path(temporary).resolve()
            broker, observer, _inventory = self.control.build(root)
            with self.control.Invocation(broker, observer, root) as invocation:
                client = invocation.connect()
                launched = client.launch(5)
                result = client.request(2, handle=launched["handle"])
                self.assertEqual(result["signal"], 5)
                self.assertEqual(result["exit"], -1)
                self.assertNotIn("runtime-trap-was-suppressed", result["output"])

    @unittest.skipUnless(os.environ.get("SPECFACT_NATIVE_CONTROL") == "1", "explicit native fixture run")
    def test_actual_native_control_subset(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp", prefix="sf-control-test-") as temporary:
            root = Path(temporary).resolve()
            broker, observer, inventory = self.control.build(root)
            trials = self.control.run_trials(broker, observer, root, 1)
            broker_inputs = next(item for item in inventory if item["name"] == "broker")
            self.assertEqual(broker_inputs["signal_transport"], "mach-exception-v1")
            self.assertEqual(len(broker_inputs["build_inputs"]), 8)
            self.assertIn("control_exec_policy.h", {item["name"] for item in broker_inputs["build_inputs"]})
            self.assertTrue(all(item["passed"] for item in trials), trials)
            self.assertEqual(
                set(self.control.LIFECYCLE_CASES),
                {item["case"] for item in trials if item["case"] in self.control.LIFECYCLE_CASES},
            )
