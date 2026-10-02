"""Contract tests for the bounded native control experiment (stdlib runner)."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import socket
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


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
            self.assertTrue(inventory)
            self.assertTrue(all(item["passed"] for item in trials), trials)
            self.assertEqual(
                set(self.control.LIFECYCLE_CASES),
                {item["case"] for item in trials if item["case"] in self.control.LIFECYCLE_CASES},
            )


if __name__ == "__main__":
    unittest.main()
