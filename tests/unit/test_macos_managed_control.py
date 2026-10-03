"""Contract tests for the bounded native control experiment (stdlib runner)."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/macos_managed_boundary/control.py"


def module():
    spec = importlib.util.spec_from_file_location("managed_control_fixture", SOURCE)
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class _ControlTestCase(unittest.TestCase):
    def setUp(self):
        self.control = module()


class ControlContractTests(_ControlTestCase):
    # Private diagnostic helpers are deliberately exercised for failure/privacy regression coverage.
    def test_exact_versioned_wire(self):
        packet = self.control.frame(b"a" * 32, 1, self.control.FrameFields(argument=2, timeout_ms=300))
        self.assertEqual(len(packet), 56)
        self.assertEqual(struct.unpack("!I", packet[:4]), (52,))
        self.assertEqual(struct.unpack("!BBHQII32s", packet[4:]), (1, 1, 0, 0, 2, 300, b"a" * 32))

    def test_no_exec_pid_or_grant_arguments(self):
        for field in ("pid", "executable", "project", "grants"):
            with self.subTest(field=field), self.assertRaises(TypeError):
                self.control.frame(b"a" * 32, 1, self.control.FrameFields(**{field: "/bin/sh"}))

    def test_capability_length(self):
        for value in (b"", b"a" * 31, b"a" * 33):
            with self.assertRaises(ValueError):
                self.control.frame(value, 0)

    def test_socket_job_ownership(self):
        config = self.control.job_config("fixture", Path("/broker"), Path("/private"))
        self.assertFalse(config["KeepAlive"])
        self.assertFalse(config["AbandonProcessGroup"])
        self.assertTrue(config["LaunchOnlyOnce"])
        self.assertEqual(config["Sockets"]["control"]["SockPathMode"], 0o600)
        self.assertEqual(config["Sockets"]["control"]["SockPathName"], "/private/control.sock")
        self.assertEqual(config["ProgramArguments"], ["/broker", "/private/authority"])
        self.assertNotIn("worker", json.dumps(config))

    def test_partial_counts_do_not_admit(self):
        report = self.control.receipt(100, [{"case": "cancel", "passed": True}])
        self.assertFalse(report["repetition_gate_passed"])
        self.assertFalse(report["production_approved"])
        self.assertFalse(report["signed_boundary_verified"])

    def test_all_lifecycle_counts_required(self):
        trials = [{"case": case, "passed": True} for case in self.control.LIFECYCLE_CASES for _ in range(100)]
        trials += [{"case": case, "passed": True} for case in self.control.PROTOCOL_CASES]
        report = self.control.receipt(100, trials)
        self.assertTrue(report["repetition_gate_passed"])
        self.assertFalse(report["production_approved"])

    def test_failure_cannot_be_hidden_by_count(self):
        trials = [{"case": case, "passed": True} for case in self.control.LIFECYCLE_CASES for _ in range(100)]
        trials += [{"case": case, "passed": True} for case in self.control.PROTOCOL_CASES]
        trials.append({"case": "cancel", "passed": False})
        self.assertFalse(self.control.receipt(100, trials)["repetition_gate_passed"])

    def test_socket_path_limit(self):
        with self.assertRaises(ValueError):
            self.control.job_config("fixture", Path("/broker"), Path("/" + "a" * 104))

    def test_protocol_gates_required_for_repetition(self):
        trials = [{"case": case, "passed": True} for case in self.control.LIFECYCLE_CASES for _ in range(100)]
        self.assertFalse(self.control.receipt(100, trials)["repetition_gate_passed"])

    def test_bounded_reply_decoder(self):
        for size in (0, 2049, 2**32 - 1):
            left, right = socket.socketpair()
            try:
                left.sendall(struct.pack("!I", size))
                with self.assertRaises(ValueError):
                    self.control.response(right)
            finally:
                left.close()
                right.close()

    def test_bootstrap_timeout_still_removes_possible_job(self):
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.object(
                self.control.STARTUP, "observe", return_value={"audit_token": [501, 501, 20, 501, 20, 123, 1, 10]}
            ),
            patch.object(self.control.STARTUP, "command", side_effect=subprocess.TimeoutExpired("launchctl", 10)),
            patch.object(self.control.STARTUP, "remove_job") as remove,
            self.assertRaises(subprocess.TimeoutExpired),
        ):
            try:
                self.control.Invocation(Path("/broker"), Path("/observer"), Path(temporary))
            finally:
                self.assertEqual(remove.call_count, 1)

    def test_cleanup_deadline_precedes_competing_worker_timeout(self):
        launched = {"deadline_ns": 15_000_000_000}
        with patch.object(self.control.time, "clock_gettime_ns", return_value=10_000_000_000):
            deadline = self.control.cleanup_deadline(launched)
        self.assertEqual(deadline, 14_750_000_000)
        self.assertLess(deadline, launched["deadline_ns"])
        with (
            patch.object(self.control.time, "clock_gettime_ns", return_value=14_800_000_000),
            self.assertRaises(RuntimeError),
        ):
            self.control.cleanup_deadline(launched)

    def test_worker_death_after_proof_deadline_is_not_eof_success(self):
        invocation = SimpleNamespace(observer=Path("/observer"), service="fixture")
        with (
            patch.object(self.control.time, "monotonic", return_value=14.8),
            patch.object(self.control.time, "clock_gettime_ns", return_value=14_800_000_000),
            patch.object(self.control.STARTUP, "alive", return_value=False),
            patch.object(self.control.STARTUP, "job_absent", return_value=True),
            self.assertRaises(RuntimeError),
        ):
            self.control.observe_absence(invocation, {"pid": 123}, 10.0, job=True, native_deadline_ns=14_750_000_000)

    def test_native_deadline_does_not_compare_mach_clock_epoch(self):
        with (
            patch.object(self.control.time, "monotonic", return_value=1000000.0),
            patch.object(self.control.time, "clock_gettime_ns", return_value=10_000_000_000),
        ):
            self.assertEqual(self.control.cleanup_deadline({"deadline_ns": 15_000_000_000}), 14_750_000_000)

    def test_launch_binds_timeout_to_request_start(self):
        client = object.__new__(self.control.Client)
        with (
            patch.object(
                client, "request", return_value={"ok": True, "state": "launched", "deadline_ns": 999_000_000_000}
            ),
            patch.object(self.control.time, "monotonic", return_value=100.0),
        ):
            launched = client.launch(timeout_ms=5000)
        self.assertEqual(launched["deadline_ns"], 999_000_000_000)

    def test_failed_invocation_retains_diagnostics_before_cleanup(self):
        invocation = object.__new__(self.control.Invocation)
        error = TimeoutError("terminal wait")
        calls = []
        with (
            patch.object(invocation, "retain_failure", side_effect=lambda value: calls.append(("capture", value))),
            patch.object(invocation, "cleanup", side_effect=lambda: calls.append(("cleanup", None))),
        ):
            invocation.__exit__(TimeoutError, error, None)
        self.assertEqual(calls, [("capture", error), ("cleanup", None)])

    def test_native_sources_exist(self):
        for name in ("control_broker.c", "control_worker.c"):
            self.assertTrue((SOURCE.parent / name).is_file())


class SocketReadinessTests(_ControlTestCase):
    def _observe(self, observations, *, directory_mode=stat.S_IFDIR | 0o700, directory_uid=None):
        uid = os.getuid()
        directory = Path("/private-fixture")
        clock = [10.0]
        snapshots = iter(observations)
        sleeps = []
        directory_info = SimpleNamespace(st_mode=directory_mode, st_uid=uid if directory_uid is None else directory_uid)

        def lstat(path):
            if path == directory:
                return directory_info
            self.assertEqual(path, directory / "control.sock")
            at, mode, owner = next(snapshots)
            clock[0] = at
            if mode is None:
                raise FileNotFoundError("not bound")
            return SimpleNamespace(st_mode=mode, st_uid=uid if owner is None else owner)

        def sleep(seconds):
            self.assertGreater(seconds, 0)
            self.assertLessEqual(seconds, min(0.005, 13.0 - clock[0]))
            sleeps.append(seconds)
            clock[0] += seconds

        with (
            patch.object(self.control.SOCKET.Path, "lstat", autospec=True, side_effect=lstat) as inspect,
            patch.object(self.control.SOCKET.Path, "stat", side_effect=AssertionError("must not follow symlinks")),
            patch.object(self.control.SOCKET.Path, "exists", side_effect=AssertionError("existence is not readiness")),
            patch.object(self.control.SOCKET.time, "monotonic", side_effect=lambda: clock[0]),
            patch.object(self.control.SOCKET.time, "sleep", side_effect=sleep),
        ):
            self.control.SOCKET.wait_socket_ready(directory / "control.sock")
        return inspect.call_count, sleeps

    def test_owned_socket_ready_immediately(self):
        calls, sleeps = self._observe([(10.0, stat.S_IFSOCK | 0o600, None)])
        self.assertEqual(calls, 2)
        self.assertEqual(sleeps, [])

    def test_owned_socket_modes_transition_to_ready(self):
        for mode in (0o000, 0o666, 0o700, 0o1600):
            with self.subTest(mode=oct(mode)):
                calls, sleeps = self._observe([(10.0, stat.S_IFSOCK | mode, None), (10.5, stat.S_IFSOCK | 0o600, None)])
                self.assertEqual(calls, 4)
                self.assertEqual(len(sleeps), 1)

    def test_delayed_binding_then_mode_transition(self):
        calls, sleeps = self._observe(
            [(10.0, None, None), (10.5, stat.S_IFSOCK | 0o666, None), (12.9, stat.S_IFSOCK | 0o600, None)]
        )
        self.assertEqual(calls, 6)
        self.assertEqual(len(sleeps), 2)

    def test_missing_or_non_ready_mode_exhausts_original_budget(self):
        for mode in (None, stat.S_IFSOCK | 0o666):
            with (
                self.subTest(mode=mode),
                self.assertRaisesRegex(RuntimeError, "socket readiness deadline"),
            ):
                self._observe([(10.0, mode, None), (12.999, mode, None)])

    def test_ready_at_or_after_deadline_is_rejected(self):
        for ready_at in (13.0, 13.001, 14.0):
            with (
                self.subTest(ready_at=ready_at),
                self.assertRaisesRegex(RuntimeError, "socket readiness deadline"),
            ):
                self._observe([(10.0, stat.S_IFSOCK | 0o666, None), (ready_at, stat.S_IFSOCK | 0o600, None)])

    def test_first_ready_snapshot_finishing_late_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "socket readiness deadline"):
            self._observe([(13.1, stat.S_IFSOCK | 0o600, None)])

    def test_wrong_owner_fails_without_waiting_even_before_chmod(self):
        for mode in (0o600, 0o666):
            with (
                self.subTest(mode=oct(mode)),
                self.assertRaisesRegex(RuntimeError, "socket type/owner"),
            ):
                self._observe([(10.0, stat.S_IFSOCK | mode, os.getuid() + 1)])

    def test_non_socket_and_symlink_fail_closed(self):
        for kind in (stat.S_IFREG, stat.S_IFDIR, stat.S_IFIFO, stat.S_IFLNK):
            with self.subTest(kind=kind), self.assertRaisesRegex(RuntimeError, "socket type/owner"):
                self._observe([(10.0, kind | 0o600, None)])

    def test_directory_must_remain_owned_private_directory(self):
        for mode, uid in (
            (stat.S_IFDIR | 0o755, None),
            (stat.S_IFDIR | 0o1700, None),
            (stat.S_IFDIR | 0o700, os.getuid() + 1),
            (stat.S_IFLNK | 0o700, None),
            (stat.S_IFREG | 0o700, None),
        ):
            with self.subTest(mode=mode, uid=uid), self.assertRaisesRegex(RuntimeError, "private directory"):
                self._observe([], directory_mode=mode, directory_uid=uid)

    def test_unexpected_lstat_error_is_terminal(self):
        with (
            patch.object(self.control.SOCKET.Path, "lstat", side_effect=PermissionError("denied")),
            patch.object(self.control.SOCKET.time, "sleep") as sleep,
            self.assertRaises(PermissionError),
        ):
            self.control.SOCKET.wait_socket_ready(Path("/private-fixture/control.sock"))
        sleep.assert_not_called()

    def test_constructor_observes_readiness_after_one_registration(self):
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.object(self.control.STARTUP, "observe", return_value={"audit_token": [0] * 8}),
            patch.object(self.control.STARTUP, "command") as register,
            patch.object(self.control.SOCKET, "wait_socket_ready") as ready,
        ):
            invocation = self.control.Invocation(Path("/broker"), Path("/observer"), Path(temporary))
        register.assert_called_once()
        ready.assert_called_once_with(invocation.directory / "control.sock")
        self.assertEqual(invocation.phase, "bootstrap-socket")

    def test_readiness_failure_keeps_phase_and_cleans_registered_job(self):
        original = RuntimeError("socket readiness deadline exceeded")
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.object(self.control.STARTUP, "observe", return_value={"audit_token": [0] * 8}),
            patch.object(self.control.STARTUP, "command") as register,
            patch.object(self.control.SOCKET, "wait_socket_ready", side_effect=original),
            patch.object(self.control.Invocation, "retain_failure", autospec=True) as retain,
            patch.object(self.control.STARTUP, "remove_job") as remove,
            self.assertRaises(RuntimeError) as raised,
        ):
            self.control.Invocation(Path("/broker"), Path("/observer"), Path(temporary))
        self.assertIs(raised.exception, original)
        register.assert_called_once()
        remove.assert_called_once()
        invocation = retain.call_args.args[0]
        owner, phase = original.__dict__["_control_failure_origin"]
        self.assertIs(owner, invocation)
        self.assertEqual(phase, "bootstrap-socket")
        self.assertEqual(invocation.phase, "cleanup")


class ControlHelperImportTests(_ControlTestCase):
    def test_direct_script_loads_siblings_outside_repository_import_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run(
                [sys.executable, "-I", str(SOURCE), "--help"],
                cwd=temporary,
                check=True,
                capture_output=True,
                text=True,
            )
        self.assertIn("--repetitions", result.stdout)
        self.assertEqual(result.stderr, "")


class ControlFailureTests(_ControlTestCase):
    def test_bootstrap_diagnostic_failure_preserves_original_exception(self):
        original = subprocess.TimeoutExpired("launchctl", 10)
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.object(
                self.control.STARTUP, "observe", return_value={"audit_token": [501, 501, 20, 501, 20, 123, 1, 10]}
            ),
            patch.object(self.control.STARTUP, "command", side_effect=original),
            patch.object(self.control, "_write_diagnostic", side_effect=FileNotFoundError("private detail")),
            patch.object(self.control.STARTUP, "remove_job") as remove,
            self.assertRaises(subprocess.TimeoutExpired) as raised,
        ):
            try:
                self.control.Invocation(Path("/broker"), Path("/observer"), Path(temporary))
            finally:
                self.assertEqual(remove.call_count, 1)
        self.assertIs(raised.exception, original)
        self.assertIn("FileNotFoundError", " ".join(original.__notes__))
        self.assertNotIn("private detail", " ".join(original.__notes__))

    def test_failed_context_preserves_original_despite_secondary_failures(self):
        for secondary in (OSError("private detail"), KeyboardInterrupt()):
            with self.subTest(secondary=type(secondary).__name__):
                invocation = object.__new__(self.control.Invocation)
                original = RuntimeError("native proof failed")
                with (
                    patch.object(invocation, "retain_failure", side_effect=secondary),
                    patch.object(invocation, "cleanup", side_effect=OSError("cleanup private detail")) as cleanup,
                    self.assertRaises(RuntimeError) as raised,
                    invocation as _fixture,
                ):
                    raise original
                self.assertIs(raised.exception, original)
                cleanup.assert_called_once_with()
                notes = " ".join(original.__notes__)
                self.assertIn(type(secondary).__name__, notes)
                self.assertIn("cleanup", notes.lower())
                self.assertNotIn("private detail", notes)

    def test_successful_context_does_not_hide_cleanup_failure(self):
        invocation = object.__new__(self.control.Invocation)
        original = OSError("cleanup failed")
        with (
            patch.object(invocation, "retain_failure") as retain,
            patch.object(invocation, "cleanup", side_effect=original),
            self.assertRaises(OSError) as raised,
            invocation as _fixture,
        ):
            pass
        self.assertIs(raised.exception, original)
        retain.assert_called_once_with(original)

    def test_diagnostic_uses_portable_private_tempfile_without_private_tmp(self):
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.object(self.control.Path, "is_dir", return_value=False),
            patch.object(self.control.tempfile, "gettempdir", return_value=temporary),
        ):
            path = self.control._write_diagnostic({"case": "cancel"})  # pylint: disable=protected-access
            self.assertEqual(path.parent, Path(temporary))
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(path.read_text()), {"case": "cancel"})

    def test_diagnostic_retains_private_tmp_when_available(self):
        with (
            patch.object(self.control.Path, "is_dir", return_value=True),
            patch.object(self.control.tempfile, "gettempdir") as fallback,
            patch.object(self.control.tempfile, "mkstemp", side_effect=OSError("capture failed")) as create,
            self.assertRaises(OSError),
        ):
            self.control._write_diagnostic({"case": "cancel"})  # pylint: disable=protected-access
        self.assertEqual(create.call_args.kwargs["dir"], "/private/tmp")
        fallback.assert_not_called()

    def test_request_phase_is_explicit_before_decoding_and_validation(self):
        invocation = object.__new__(self.control.Invocation)
        client = object.__new__(self.control.Client)
        client.owner = invocation
        client.capability = b"a" * 32
        client.history = []
        client.stream = MagicMock()
        for opcode, expected in enumerate(
            ("request-authenticate", "request-launch", "request-wait", "request-signal", "request-cancel")
        ):
            with self.subTest(opcode=opcode), patch.object(self.control, "response", return_value={"ok": False}):
                client.request(opcode)
                self.assertEqual(invocation.phase, expected)
        with patch.object(self.control, "response", return_value={"ok": False}):
            client.request(99)
        self.assertEqual(invocation.phase, "unknown")

    def test_failure_emission_contains_trusted_phase_without_raw_error_details(self):
        with tempfile.TemporaryDirectory() as temporary:
            invocation = object.__new__(self.control.Invocation)
            self.control.__dict__["_activate_operation"](invocation, "isolation-extra-connection")
            invocation.case = "isolation-left"
            invocation.client = None
            invocation.identities = []
            invocation.directory = Path(temporary)
            invocation.observer = Path("/observer")
            invocation.broker = Path(temporary) / "missing-broker"
            invocation.service = "private service"
            with (
                patch.object(self.control, "_write_diagnostic", return_value=Path(temporary) / "failure.json") as write,
                patch.object(self.control, "_emit_json") as emit,
            ):
                invocation.retain_failure(TimeoutError("private error detail"))
            emitted = emit.call_args.args[0]
            self.assertEqual(emitted["failure_phase"], "isolation-extra-connection")
            self.assertNotIn("private error detail", json.dumps(emitted))
            self.assertEqual(write.call_args.args[0]["failure_phase"], "isolation-extra-connection")
            self.control.__dict__["_activate_operation"](invocation, "untrusted phase detail")
            self.assertEqual(invocation.phase, "unknown")  # pylint: disable=protected-access

    def test_bootstrap_failure_records_registration_phase(self):
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.object(
                self.control.STARTUP, "observe", return_value={"audit_token": [501, 501, 20, 501, 20, 123, 1, 10]}
            ),
            patch.object(self.control.STARTUP, "command", side_effect=subprocess.TimeoutExpired("launchctl", 10)),
            patch.object(self.control.Invocation, "retain_failure", autospec=True) as retain,
            patch.object(self.control.STARTUP, "remove_job"),
            self.assertRaises(subprocess.TimeoutExpired),
        ):
            try:
                self.control.Invocation(Path("/broker"), Path("/observer"), Path(temporary))
            finally:
                invocation = retain.call_args.args[0]
                original = retain.call_args.args[1]
                owner, phase = original.__dict__["_control_failure_origin"]
                self.assertIs(owner, invocation)
                self.assertEqual(phase, "bootstrap-register")
                self.assertEqual(invocation.phase, "cleanup")

    def test_native_marker_failure_records_trusted_marker_phase(self):
        invocation = object.__new__(self.control.Invocation)
        invocation.directory = Path("/unused")
        invocation.client = None
        invocation.phase = "unknown"
        for field in ("broker", "trace", "output"):
            with (
                self.subTest(field=field),
                patch.object(self.control, "_event_from_file", side_effect=OSError("private marker detail")),
                self.assertRaises(OSError),
            ):
                try:
                    invocation.wait_event(field)
                finally:
                    self.assertEqual(invocation.phase, "marker-" + field)  # pylint: disable=protected-access


class ControlFailureOwnershipTests(_ControlTestCase):
    def _invocation(self, root, case, pid):
        invocation = object.__new__(self.control.Invocation)
        invocation.case = case
        invocation.phase = "unknown"
        invocation.directory = root
        invocation.observer = root / "observer"
        invocation.broker = root / "broker"
        invocation.service = "private service"
        invocation.registered = False
        invocation.identities = [{"pid": pid, "pgid": pid}]
        client = object.__new__(self.control.Client)
        client.capability = b"a" * 32
        client.history = []
        client.stream = MagicMock()
        client.owner = invocation
        invocation.client = client
        return invocation

    def _isolation_failure(self, scenario):
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            root = Path(temporary)
            first = self._invocation(root, "isolation-left", 11)
            second = self._invocation(root, "isolation-right", 22)
            emitted, cleanups = [], []
            extra = MagicMock()
            extra.recv.return_value = b""
            if scenario == "extra-connection":
                extra.recv.side_effect = TimeoutError("private extra socket detail")
            left_reply = {"ok": True, "state": "launched", "handle": 1, "pid": 100, "deadline_ns": 999999999999}
            if scenario == "left-launch":
                left_reply = {"ok": False, "error": "spawn"}
            right_replies = iter(
                [
                    {"ok": True, "state": "launched", "handle": 2, "pid": 200, "deadline_ns": 999999999999},
                    {"error": "handle"},
                    {"error": "capability"},
                    {"ok": True},
                    {"signal": 9, "reason": "timeout" if scenario == "right-wait-status" else "cancel"},
                ]
            )

            def reply(stream):
                if stream is first.client.stream:
                    return left_reply
                result = next(right_replies)
                if scenario == "right-wait-transport" and "signal" in result:
                    raise TimeoutError("private wait detail")
                return result

            def marker(_path, field, pid):
                if scenario == "left-marker" and pid == 100:
                    raise RuntimeError("private marker detail")
                return {field: pid}

            def cleanup(invocation):
                cleanups.append(invocation.case)
                # Cleanup must not change the already-stamped failure owner/phase.
                activate = self.control.__dict__.get("_activate_operation")
                if activate is not None:
                    activate(invocation, "bootstrap-register")

            for invocation in (first, second):
                stack.enter_context(patch.object(invocation, "connect", return_value=invocation.client))
                stack.enter_context(patch.object(invocation, "cleanup", side_effect=partial(cleanup, invocation)))
            for target, name, values in (
                (self.control, "Invocation", {"side_effect": [first, second]}),
                (self.control, "response", {"side_effect": reply}),
                (self.control, "_event_from_file", {"side_effect": marker}),
                (self.control, "_failure_identity", {"return_value": None}),
                (self.control, "_write_diagnostic", {"return_value": root / "failure.json"}),
                (self.control, "_emit_json", {"side_effect": emitted.append}),
                (self.control, "cleanup_deadline", {"return_value": 999999999999}),
                (self.control, "observe_absence", {"return_value": {"passed": True}}),
                (self.control.STARTUP, "alive", {"return_value": True}),
                (self.control.socket, "socket", {"return_value": extra}),
            ):
                options: dict[str, Any] = values
                stack.enter_context(patch.object(target, name, **options))
            stack.enter_context(
                patch.object(
                    self.control.STARTUP,
                    "observe",
                    side_effect=lambda _observer, pid: {
                        "pid": pid,
                        "ppid": 11 if pid == 100 else 22,
                        "pgid": pid,
                        "flags": 2,
                    },
                )
            )
            with self.assertRaises((RuntimeError, TimeoutError)):
                self.control.isolation_trial(root / "broker", root / "observer", root)
            self.assertEqual(cleanups, ["isolation-right", "isolation-left"])
            return emitted

    def test_nested_unwind_reports_actual_owner_and_phase(self):
        for scenario, owner, phase in (
            ("left-launch", "isolation-left", "request-launch"),
            ("left-marker", "isolation-left", "marker-output"),
            ("right-wait-transport", "isolation-right", "request-wait"),
            ("right-wait-status", "isolation-right", "request-wait"),
            ("extra-connection", "isolation-left", "isolation-extra-connection"),
        ):
            with self.subTest(scenario=scenario):
                records = self._isolation_failure(scenario)
                self.assertEqual(len(records), 2)
                origins = [item for item in records if item.get("failure_origin") is True]
                self.assertEqual(len(origins), 1)
                self.assertEqual(origins[0]["failed_case"], owner)
                self.assertTrue(all(item["failure_phase"] == phase for item in records))
                for item in records:
                    self.assertIs(type(item["failure_origin"]), bool)
                    self.assertEqual(set(item), {"failed_case", "failure_phase", "failure_origin", "diagnostic"})
                    self.assertNotIn("private wait detail", json.dumps(item))

    def test_successful_nested_body_cleanup_failure_reports_cleanup_owner_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = self._invocation(root, "isolation-left", 11)
            second = self._invocation(root, "isolation-right", 22)
            original = OSError("private cleanup detail")
            second.client.stream.close.side_effect = original
            records = []
            with (
                patch.object(self.control, "response", return_value={"ok": True}),
                patch.object(self.control, "_failure_identity", return_value=None),
                patch.object(self.control, "_write_diagnostic", return_value=root / "failure.json"),
                patch.object(self.control, "_emit_json", side_effect=records.append),
                self.assertRaises(OSError) as raised,
                first as _first,
                second as _second,
            ):
                first.client.request(2)
            self.assertIs(raised.exception, original)
            first.client.stream.close.assert_called_once_with()
            second.client.stream.close.assert_called_once_with()
            self.assertEqual(len(records), 2)
            origins = [item for item in records if item["failure_origin"] is True]
            self.assertEqual([item["failed_case"] for item in origins], ["isolation-right"])
            self.assertTrue(all(item["failure_phase"] == "cleanup" for item in records))

    def test_decoded_launch_rejection_keeps_request_phase_through_validation(self):
        with tempfile.TemporaryDirectory() as temporary:
            invocation = self._invocation(Path(temporary), "protocol", 11)
            invocation.phase = "marker-output"
            with (
                patch.object(self.control, "response", return_value={"ok": False, "error": "spawn"}),
                patch.object(self.control, "_write_diagnostic", return_value=Path(temporary) / "failure.json"),
                patch.object(self.control, "_failure_identity", return_value=None),
                patch.object(self.control, "_emit_json") as emit,
                patch.object(invocation, "cleanup"),
                self.assertRaises(RuntimeError),
                invocation,
            ):
                invocation.client.launch()
            record = emit.call_args.args[0]
            self.assertEqual(record["failure_phase"], "request-launch")
            self.assertIs(record["failure_origin"], True)


class BuildProvenanceTests(_ControlTestCase):
    def test_repository_change_during_compile_cannot_change_source_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / "originals"
            source.mkdir()
            root = directory / "build"
            root.mkdir()
            originals = {}
            reads = {}
            compiled = {}
            for name in ("control_mach.inc", "control_mach_policy.h"):
                (source / name).write_bytes(b"captured include")
            for name in ("control_worker.c", "startup_observe.c", "control_broker.c"):
                path = source / name
                originals[path] = name.encode() + b" initial source"
                path.write_bytes(originals[path])
                reads[path] = 0
            read_bytes = Path.read_bytes

            def counted_read(path):
                if path in reads:
                    reads[path] += 1
                return read_bytes(path)

            def command(args):
                if args[0] == "/usr/bin/xcrun":
                    compiler_input = Path(args[args.index("-o") - 1])
                    target = Path(args[args.index("-o") + 1])
                    # Select this build's source without relying on the snapshot naming convention.
                    initial = read_bytes(compiler_input)
                    original = next(path for path, value in originals.items() if value == initial)
                    compiled[target.name.removeprefix("control-")] = (compiler_input, initial)
                    original.write_bytes(b"changed concurrently after compiler input was captured")
                    target.write_bytes(b"mock signed binary")
                details = "flags=0x10002(adhoc,runtime)\nSignature=adhoc\nCDHash=" + "a" * 40
                return SimpleNamespace(stdout="control-positive-ok" if len(args) == 2 else "", stderr=details)

            with (
                patch.object(self.control, "SOURCE", source),
                patch.object(self.control, "verify_native_clock", return_value={}),
                patch.object(self.control.MACH, "prepare", return_value=([], [])),
                patch.object(self.control.STARTUP, "command", side_effect=command),
                patch.object(Path, "read_bytes", counted_read),
            ):
                _broker, _observer, inventory = self.control.build(root)
            for item in inventory:
                compiler_input, initial = compiled[item["name"]]
                with self.subTest(component=item["name"], property="private-snapshot"):
                    self.assertEqual(compiler_input.parent, root)
                    self.assertEqual(compiler_input.stat().st_mode & 0o777, 0o444)
                with self.subTest(component=item["name"], property="compiled-source-digest"):
                    self.assertEqual(item["source_sha256"], hashlib.sha256(initial).hexdigest())
            self.assertEqual(set(reads.values()), {1})
            self.assertEqual(root.stat().st_mode & 0o777, 0o700)


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
            self.assertEqual(len(broker_inputs["build_inputs"]), 6)
            self.assertTrue(all(item["passed"] for item in trials), trials)
            self.assertEqual(
                set(self.control.LIFECYCLE_CASES),
                {item["case"] for item in trials if item["case"] in self.control.LIFECYCLE_CASES},
            )


if __name__ == "__main__":
    unittest.main()
