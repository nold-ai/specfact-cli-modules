"""Fail-closed contracts for controlled native analyzer compatibility."""

import importlib.util
import os
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import nullcontext, suppress
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("native_analyzer_smoke", ROOT / "scripts/native_analyzer_smoke.py")
assert SPEC is not None and SPEC.loader is not None
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


class NativeSmokeTests(unittest.TestCase):
    def test_receipt_maps_canonical_analyzer_ids(self):
        receipt = smoke.make_receipt({}, system="Darwin", machine="arm64")
        self.assertEqual(receipt["analyzer_ids"]["semgrepclean"], "semgrep-clean")
        self.assertEqual(receipt["analyzer_ids"]["semgrepbugs"], "semgrep-bugs")
        self.assertEqual(receipt["analyzer_ids"]["aibloat"], "ai-bloat-ast")
        self.assertEqual(receipt["analyzer_ids"]["astclean"], "ast-clean-code")
        self.assertEqual(receipt["analyzer_ids"]["pytestcoverage"], "targeted-pytest-coverage")
        self.assertEqual(set(receipt["analyzer_ids"]), set(smoke.MEMBERS))

    def test_all_ten_members_are_required(self):
        self.assertEqual(
            set(smoke.MEMBERS),
            {
                "ruff",
                "radon",
                "semgrepclean",
                "semgrepbugs",
                "aibloat",
                "astclean",
                "basedpyright",
                "contracts",
                "pylint",
                "pytestcoverage",
            },
        )

    def test_missing_member_never_passes(self):
        rows = {name: {"passed": True} for name in smoke.MEMBERS}
        del rows["contracts"]
        receipt = smoke.make_receipt(rows, system="Darwin", machine="arm64")
        self.assertFalse(receipt["passed"])
        self.assertFalse(receipt["sandbox_verified"])
        self.assertFalse(receipt["production_eligible"])
        self.assertEqual(receipt["evidence_kind"], "native_compatibility_only")
        self.assertEqual(set(receipt["members"]), set(smoke.MEMBERS))

    def test_wrong_platform_never_passes(self):
        rows = {name: {"passed": True} for name in smoke.MEMBERS}
        for system, machine in [("Linux", "aarch64"), ("Darwin", "x86_64")]:
            self.assertFalse(smoke.make_receipt(rows, system=system, machine=machine)["passed"])

    def test_explicit_config_rejects_extra_scope_and_relative_paths(self):
        for config in ({"python": sys.executable, "repository": "/tmp/customer"}, {"python": "python3"}):
            with self.assertRaises(ValueError):
                smoke.validate_config(config)

    def test_missing_tools_are_not_resolved_from_path(self):
        config = smoke.validate_config({"python": sys.executable})
        with self.assertRaises(ValueError):
            smoke.command_for(config, "ruff")
        with self.assertRaises(ValueError):
            smoke.command_for(config, "basedpyright")

    def test_basedpyright_requires_explicit_node_and_entrypoint(self):
        config = {"python": sys.executable, "node": sys.executable, "basedpyright_js": str(Path(__file__).resolve())}
        self.assertEqual(smoke.command_for(config, "basedpyright"), [sys.executable, config["basedpyright_js"]])

    def test_node_probe_revalidates_configured_executable_before_launch(self):
        config = {"python": sys.executable, "node": sys.executable, "basedpyright_js": str(Path(__file__).resolve())}

        def probe(argv, **_kwargs):
            config["node"] = "node"
            return subprocess.CompletedProcess(argv, 0, "basedpyright 1.39.10", "")

        with (
            patch.object(smoke.subprocess, "run", side_effect=probe) as run,
            self.assertRaisesRegex(ValueError, "required absolute file is missing"),
        ):
            smoke._versions(config, "basedpyright")
        self.assertEqual(run.call_count, 1)

    def test_node_version_failures_retain_bounded_stderr_in_member_receipt(self):
        config = {"python": sys.executable, "node": sys.executable, "basedpyright_js": str(Path(__file__).resolve())}
        stderr = "node-start" + "x" * 5000 + "node-end"
        for returncode, stdout in [(9, ""), (0, " \n")]:
            with self.subTest(returncode=returncode):

                def probe(argv, returncode=returncode, stdout=stdout, **kwargs):
                    if argv == [config["node"], "--version"]:
                        if kwargs.get("check") and returncode:
                            raise subprocess.CalledProcessError(returncode, argv, output=stdout, stderr=stderr)
                        return subprocess.CompletedProcess(argv, returncode, stdout, stderr)
                    return subprocess.CompletedProcess(argv, 0, "basedpyright 1.39.10", "")

                with (
                    tempfile.TemporaryDirectory(prefix="pr489-node-version-") as directory,
                    smoke.chdir(Path(directory)),
                    patch.object(smoke.platform, "system", return_value="Darwin"),
                    patch.object(smoke.platform, "machine", return_value="arm64"),
                    patch.object(smoke.subprocess, "run", side_effect=probe) as run,
                    patch.object(smoke, "_adapter_findings") as adapter,
                ):
                    row = smoke.worker(config, "basedpyright")
                self.assertFalse(row["passed"])
                self.assertEqual(
                    row["error"],
                    f"ValueError: node version probe failed: {returncode}: {stderr[:1200] + stderr[-800:]}",
                )
                adapter.assert_not_called()
                self.assertEqual(
                    run.call_args.kwargs, {"capture_output": True, "text": True, "timeout": 10, "check": False}
                )
                receipt = smoke.make_receipt({"basedpyright": row}, system="Darwin", machine="arm64")
                self.assertEqual(receipt["members"]["basedpyright"]["error"], row["error"])
                self.assertFalse(receipt["passed"])
                self.assertFalse(receipt["sandbox_verified"])
                self.assertFalse(receipt["production_eligible"])

    def test_successful_node_probe_records_stripped_version(self):
        config = {"python": sys.executable, "node": sys.executable, "basedpyright_js": str(Path(__file__).resolve())}
        with patch.object(
            smoke.subprocess,
            "run",
            side_effect=[
                subprocess.CompletedProcess([], 0, "basedpyright 1.39.10\n", ""),
                subprocess.CompletedProcess([], 0, " v24.16.0\n", ""),
            ],
        ) as run:
            versions = smoke._versions(config, "basedpyright")
        self.assertEqual(versions["basedpyright"], "basedpyright 1.39.10")
        self.assertEqual(versions["node"], "v24.16.0")
        self.assertEqual(run.call_args.args[0], [config["node"], "--version"])
        self.assertEqual(run.call_args.kwargs["timeout"], 10)

    def test_diagnostics_and_operational_errors_fail_closed(self):
        finding = {"rule": "F821", "category": "style", "execution_state": "completed"}
        self.assertTrue(smoke.assess([], [finding], "F821"))
        self.assertFalse(smoke.assess([], [], "F821"))
        self.assertFalse(smoke.assess([finding], [finding], "F821"))
        for field, value in [
            ("category", "tool_error"),
            ("execution_state", "skipped"),
            ("evidence_outcome", "UNKNOWN"),
        ]:
            self.assertFalse(smoke.assess([], [{**finding, field: value}], "F821"))

    def test_private_path_exposes_only_configured_system_helpers(self):
        with tempfile.TemporaryDirectory() as directory:
            config = {"python": sys.executable, "system_tools": {"uname": "/usr/bin/uname"}}
            environment = smoke.controlled_env(Path(directory), config)
            entries = list(Path(environment["PATH"]).iterdir())
            self.assertEqual([path.name for path in entries], ["uname"])
            self.assertEqual(entries[0].resolve(), Path("/usr/bin/uname").resolve())
            self.assertNotIn("PYTHONPATH", environment)
            self.assertNotIn("NODE_OPTIONS", environment)
            with self.assertRaises(ValueError):
                smoke.validate_config({**config, "system_tools": {"sh": "/bin/sh"}})

    def test_explicit_ca_bundle_is_bound_without_keychain_lookup(self):
        with tempfile.TemporaryDirectory() as directory:
            config = {"python": sys.executable, "ca_bundle": str(Path(__file__).resolve())}
            smoke.validate_config(config)
            self.assertEqual(smoke.controlled_env(Path(directory), config)["SSL_CERT_FILE"], config["ca_bundle"])

    def test_unexpected_exit_cannot_be_parsed_as_findings(self):
        self.assertFalse(smoke.valid_exit("pylint", 32))
        self.assertFalse(smoke.valid_exit("ruff", 2))
        self.assertFalse(smoke.valid_exit("pytestcoverage", 5))
        self.assertTrue(smoke.valid_exit("pylint", 2))

    def test_worker_errors_preserve_other_members(self):
        with patch.object(smoke, "run_worker", side_effect=OSError("probe unavailable")):
            receipt = smoke.run_smoke({"python": sys.executable})
        self.assertEqual(len(receipt["members"]), 10)
        self.assertTrue(all("probe unavailable" in row["error"] for row in receipt["members"].values()))

    def test_radon_requires_real_complexity_diagnostic(self):
        self.assertEqual(smoke.MEMBERS["radon"][2], "CC13")

    def test_empty_config_produces_ten_failures(self):
        receipt = smoke.run_smoke({"python": "/does/not/exist"})
        self.assertFalse(receipt["passed"])
        self.assertEqual(set(receipt["members"]), set(smoke.MEMBERS))
        self.assertTrue(all(not row["passed"] for row in receipt["members"].values()))

    def test_group_permission_error_only_accepts_verified_zombies(self):
        for output, code, accepted in [("Z\n", 0, True), ("Z S\n", 0, False), ("", 1, False)]:
            expected = nullcontext() if accepted else self.assertRaises(PermissionError)
            with (
                self.subTest(output=output),
                patch.object(smoke.sys, "platform", "darwin"),
                patch.object(smoke.os, "killpg", side_effect=PermissionError("denied")),
                patch.object(smoke.subprocess, "run", return_value=subprocess.CompletedProcess([], code, output, "")),
                expected,
            ):
                smoke.terminate_worker_group(123)

    @unittest.skipUnless(hasattr(smoke.select, "kqueue"), "Darwin kqueue compatibility")
    def test_worker_without_python_waitid(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(smoke.os, "waitid", None, create=True):
            result = smoke.run_worker(
                [sys.executable, "-c", "print('native')"],
                request_json="{}",
                cwd=directory,
                env={"PATH": "/usr/bin:/bin"},
                timeout=5,
            )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "native")


class NativeWorkerCleanupTests(unittest.TestCase):
    @unittest.skipUnless(
        (hasattr(os, "waitid") or hasattr(smoke.select, "kqueue")) and hasattr(os, "killpg"), "POSIX worker supervision"
    )
    def test_timeout_and_normal_exit_clean_process_group(self):
        for timeout_case in (False, True):
            with self.subTest(timeout=timeout_case):
                self._assert_group_cleanup(timeout_case)

    @staticmethod
    def _wait_for_descendant_exit(pid):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            status = subprocess.run(
                ["/bin/ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True, check=False
            )
            if not status.stdout.strip() or status.stdout.strip().startswith("Z"):
                return True
            time.sleep(0.02)
        return False

    def _assert_group_cleanup(self, timeout_case):
        with tempfile.TemporaryDirectory() as directory:
            pid_file = Path(directory) / "child.pid"
            source = (
                "import pathlib, subprocess, sys, time; "
                "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); "
                f"pathlib.Path({str(pid_file)!r}).write_text(str(child.pid)); "
                + ("time.sleep(30)" if timeout_case else "print('done')")
            )
            cleanup_confirmed = False
            try:
                expected = self.assertRaises(subprocess.TimeoutExpired) if timeout_case else nullcontext()
                with expected:
                    result = smoke.run_worker(
                        [sys.executable, "-c", source],
                        request_json="{}",
                        cwd=directory,
                        env={"PATH": "/usr/bin:/bin"},
                        timeout=1 if timeout_case else 5,
                    )
                    self.assertEqual(result.returncode, 0)
                    self.assertEqual(result.stdout.strip(), "done")
                self.assertTrue(pid_file.exists())
                cleanup_confirmed = self._wait_for_descendant_exit(int(pid_file.read_text()))
                self.assertTrue(cleanup_confirmed, "controlled descendant remained running")
            finally:
                self._cleanup_fixture(pid_file, cleanup_confirmed)

    @staticmethod
    def _cleanup_fixture(pid_file, cleanup_confirmed):
        if not cleanup_confirmed and pid_file.exists():
            with suppress(ProcessLookupError):
                os.kill(int(pid_file.read_text()), 9)


if __name__ == "__main__":
    unittest.main()
