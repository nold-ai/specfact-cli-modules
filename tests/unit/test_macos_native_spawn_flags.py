"""Physical ARM64 regression for a failed broker spawn-attribute flag setup.

The disposable, ad-hoc signed broker records the real call site. Its spawn
interceptor refuses every attempted worker launch, including the RED control.
No injected binary or source is installed into the module.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[2] / "packages/specfact-code-review/native/macos-arm64"
BROKER = SOURCE / "broker.c"
REQUEST = struct.Struct("<IHHIIIIQQQ1024s1024s1024s1024s")
REPLY = struct.Struct("<IHHIiI")
CHECKED_CALL = "if (posix_spawnattr_setflags(&attributes, flags)) die();"
UNCHECKED_CALL = "posix_spawnattr_setflags(&attributes, flags);"
INJECTION = r"""
#include <errno.h>
#include <fcntl.h>
#include <spawn.h>
#include <stdlib.h>
#include <unistd.h>

static void record(char event) {
    const char *path = getenv("SPECFACT_TEST_TRACE");
    if (!path) _exit(90);
    int fd = open(path, O_WRONLY | O_APPEND | O_CLOEXEC);
    if (fd < 0 || write(fd, &event, 1) != 1 || close(fd)) _exit(91);
}

static int failing_setflags(posix_spawnattr_t *attributes, short flags) {
    (void)attributes;
    (void)flags;
    record('F');
    return EINVAL;
}

static int denied_spawn(pid_t *pid, const char *path,
                        const posix_spawn_file_actions_t *actions,
                        const posix_spawnattr_t *attributes,
                        char *const arguments[], char *const environment[]) {
    (void)pid;
    (void)path;
    (void)actions;
    (void)attributes;
    (void)arguments;
    (void)environment;
    record('S');
    return EPERM;
}

#define posix_spawnattr_setflags failing_setflags
#define posix_spawn denied_spawn
#include "broker_under_test.c"
"""


@dataclass(frozen=True)
class Observation:
    trace: bytes
    exit_code: int
    reply: bytes
    group_alive: bool


def _enabled() -> bool:
    return (
        sys.platform == "darwin" and os.uname().machine == "arm64" and os.environ.get("SPECFACT_NATIVE_CONTROL") == "1"
    )


def _path(path: Path) -> bytes:
    encoded = os.fsencode(path)
    assert len(encoded) < 1024
    return encoded.ljust(1024, b"\0")


def _build(root: Path, broker_source: str) -> Path:
    source = root / "source"
    capsule = root / "capsule"
    root.mkdir(mode=0o700)
    source.mkdir(mode=0o700)
    capsule.mkdir(mode=0o700)
    for path in SOURCE.iterdir():
        if path.is_file():
            shutil.copy2(path, source / path.name)
    (source / "broker_under_test.c").write_text(broker_source, encoding="utf-8")
    (source / "broker.c").write_text(INJECTION, encoding="utf-8")
    requirement = root / "python.requirement"
    requirement.write_text('cdhash H"0000000000000000000000000000000000000000"\n', encoding="ascii")
    subprocess.run(
        [str(source / "build.sh")],
        env={
            **os.environ,
            "SPECFACT_NATIVE_BUILD_DIR": str(capsule),
            "SPECFACT_PYTHON_REQUIREMENT_FILE": str(requirement),
        },
        check=True,
        capture_output=True,
        timeout=90,
    )
    for path in capsule.rglob("*"):
        path.chmod(0o700 if path.is_dir() else 0o500)
    capsule.chmod(0o700)
    subprocess.run(
        ["/usr/bin/codesign", "--verify", "--strict", str(capsule / "bin/specfact-native-broker")],
        check=True,
        capture_output=True,
        timeout=10,
    )
    return capsule


def _group_alive(group: int) -> bool:
    try:
        os.killpg(group, 0)
    except ProcessLookupError:
        return False
    return True


def _exercise(root: Path, broker_source: str) -> Observation:
    capsule = _build(root, broker_source)
    invocation = root / "invocation"
    invocation.mkdir(mode=0o700)
    for name, mode in (("project", 0o500), ("output", 0o700), ("temporary", 0o700)):
        (invocation / name).mkdir(mode=mode)
    trace = root / "trace"
    trace.touch(mode=0o600)
    parent, child = socket.socketpair()
    broker: subprocess.Popen[bytes] | None = None
    try:
        broker = subprocess.Popen(
            [
                str(capsule / "bin/specfact-native-broker"),
                "--control-fd",
                str(child.fileno()),
                "--capsule-root",
                str(capsule),
            ],
            pass_fds=(child.fileno(),),
            start_new_session=True,
            env={"LANG": "C", "LC_ALL": "C", "SPECFACT_CAPSULE_ROOT": str(capsule), "SPECFACT_TEST_TRACE": str(trace)},
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        child.close()
        stopped, status = os.waitpid(broker.pid, os.WUNTRACED)
        assert stopped == broker.pid and os.WIFSTOPPED(status) and os.WSTOPSIG(status) == signal.SIGSTOP
        requirement = json.loads((capsule / "component.json").read_text())["broker_designated_requirement"]
        subprocess.run(
            [str(capsule / "bin/specfact-native-verifier"), str(broker.pid), requirement],
            check=True,
            capture_output=True,
            timeout=5,
        )
        os.kill(broker.pid, signal.SIGCONT)
        parent.settimeout(5)
        parent.sendall(
            REQUEST.pack(
                0x53464E31,
                1,
                1,
                1,
                0,
                900_000,
                1024,
                16 << 30,
                16 << 20,
                8 << 20,
                _path(invocation),
                _path(invocation / "project"),
                _path(invocation / "output"),
                _path(invocation / "temporary"),
            )
        )
        parent.shutdown(socket.SHUT_WR)
        response = bytearray()
        while chunk := parent.recv(4096):
            response.extend(chunk)
        exit_code = broker.wait(timeout=5)
        group_alive = _group_alive(broker.pid)
        return Observation(trace.read_bytes(), exit_code, bytes(response), group_alive)
    finally:
        parent.close()
        child.close()
        if broker is not None:
            if _group_alive(broker.pid):
                os.killpg(broker.pid, signal.SIGKILL)
            if broker.poll() is None:
                broker.kill()
            broker.wait(timeout=5)
            if broker.stderr:
                broker.stderr.close()


def _assert_fail_closed(observed: Observation) -> None:
    assert observed.trace == b"F", f"setflags failure was not terminal: {observed.trace!r}"
    assert observed.exit_code == -signal.SIGKILL, observed
    assert observed.reply == b"", observed
    assert not observed.group_alive, observed


def _run_proof() -> tuple[Observation, Observation]:
    source = BROKER.read_text(encoding="utf-8")
    assert source.count(CHECKED_CALL) == 1, "broker call site changed; review the injection"
    with tempfile.TemporaryDirectory(dir="/private/tmp", prefix="sf-native-spawn-flags-") as directory:
        root = Path(directory).resolve(strict=True)
        red = _exercise(root / "red", source.replace(CHECKED_CALL, UNCHECKED_CALL, 1))
        assert red.trace == b"FS", f"reconstructed pre-fix did not reach denied spawn: {red}"
        assert red.exit_code == 0 and len(red.reply) == REPLY.size and not red.group_alive, red
        assert REPLY.unpack(red.reply)[2] == 1, red
        try:
            _assert_fail_closed(red)
        except AssertionError:
            pass
        else:
            raise AssertionError("RED control unexpectedly satisfied the fail-closed assertion")
        green = _exercise(root / "green", source)
        _assert_fail_closed(green)
    return red, green


def test_setflags_failure_prevents_worker_launch() -> None:
    """The signed broker dies before spawn; a reconstructed pre-fix attempts it."""
    if not _enabled():
        import pytest

        pytest.skip("explicit physical ARM64 native broker run")
    _run_proof()


if __name__ == "__main__":
    if sys.argv[1:] != ["--self-test"]:
        raise SystemExit(64)
    if _enabled():
        red, green = _run_proof()
        print(
            json.dumps(
                {
                    "red": {
                        "trace": red.trace.decode(),
                        "exit_code": red.exit_code,
                        "reply_status": REPLY.unpack(red.reply)[2],
                    },
                    "green": {
                        "trace": green.trace.decode(),
                        "exit_code": green.exit_code,
                        "reply_bytes": len(green.reply),
                    },
                    "process_groups_alive": [red.group_alive, green.group_alive],
                    "signed": True,
                }
            )
        )
    else:
        print(json.dumps({"skipped": "set SPECFACT_NATIVE_CONTROL=1 on macOS ARM64"}))
