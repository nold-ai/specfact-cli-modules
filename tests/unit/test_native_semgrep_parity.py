"""Acceptance contracts for fixed native Semgrep frontend comparisons."""

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("native_semgrep_parity", ROOT / "scripts/native_semgrep_parity.py")
assert SPEC is not None and SPEC.loader is not None
parity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(parity)


def payload(*, results=None, errors=None, scanned=None):
    return {
        "version": "1.175.0",
        "results": results or [],
        "errors": errors or [],
        "paths": {"scanned": ["fixture.py"] if scanned is None else scanned},
    }


def finding(rule="print-in-src", path="fixture.py", line=2):
    return {
        "check_id": rule,
        "path": path,
        "start": {"line": line},
        "end": {"line": line},
        "extra": {"message": "Avoid print", "severity": "WARNING"},
    }


class NativeSemgrepParityTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directory)
        self.directory = self.directory.resolve()
        (self.directory / "fixture.py").write_text("def announce():\n    print('native smoke')\n")

    def _canonical(self, value):
        return parity.canonicalize(value, self.directory)

    def _row(self, value, status=0):
        return {"returncode": status, "canonical": self._canonical(value)}

    def test_relative_paths_are_equivalent_but_rule_ids_are_never_rewritten(self):
        relative = self._canonical(payload(results=[finding()]))
        absolute = self._canonical(payload(results=[finding(path=str(self.directory / "fixture.py"))]))
        self.assertEqual(relative, absolute)
        prefixed = self._canonical(payload(results=[finding(rule="rules.print-in-src")]))
        self.assertNotEqual(relative, prefixed)

    def test_duplicate_findings_are_preserved_and_order_is_irrelevant(self):
        first, second = finding(), finding(rule="another-rule")
        self.assertEqual(
            self._canonical(payload(results=[first, second])), self._canonical(payload(results=[second, first]))
        )
        self.assertEqual(len(self._canonical(payload(results=[first, first]))["findings"]), 2)

    def test_outside_traversal_unknown_and_symlink_paths_are_rejected(self):
        (self.directory / "link.py").symlink_to(self.directory / "fixture.py")
        for name in ("../fixture.py", "/tmp/customer.py", "other.py", "link.py"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self._canonical(payload(results=[finding(path=name)]))

    def test_malformed_and_incomplete_payloads_fail_closed(self):
        variants = [
            {},
            {**payload(), "version": "1.174.0"},
            {**payload(), "results": {}},
            {**payload(), "errors": {}},
            {**payload(), "paths": {}},
            payload(results=[{**finding(), "start": {"line": True}}]),
            payload(results=[{**finding(), "extra": {}}]),
        ]
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self._canonical(value)

    def test_missing_findings_or_scanned_targets_cannot_pass(self):
        positive = self._row(payload(results=[finding()]))
        for value in (payload(), payload(results=[finding()], scanned=[])):
            self.assertFalse(parity.assess_case("clean_code_defective", positive, self._row(value))["passed"])
        empty = self._row(payload())
        self.assertFalse(parity.assess_case("clean_code_defective", empty, empty)["passed"])

    def test_clean_false_positive_exit_line_message_and_severity_differences_fail(self):
        positive = self._row(payload(results=[finding()]))
        self.assertTrue(parity.assess_case("clean_code_defective", positive, positive)["passed"])
        self.assertFalse(parity.assess_case("clean_code_clean", positive, positive)["passed"])
        for value, status in (
            (payload(results=[finding(line=1)]), 0),
            (payload(results=[finding()]), 1),
            (payload(results=[{**finding(), "extra": {"message": "changed", "severity": "ERROR"}}]), 0),
        ):
            self.assertFalse(parity.assess_case("clean_code_defective", positive, self._row(value, status))["passed"])

    def test_errors_and_error_exit_are_mandatory_and_compared(self):
        value = payload(
            errors=[{"type": "Syntax error", "level": "warn", "path": "fixture.py", "spans": [{"start": {"line": 1}}]}]
        )
        error = self._row(value)
        self.assertTrue(parity.assess_case("parse_error", error, error)["passed"])
        self.assertFalse(parity.assess_case("parse_error", error, self._row(payload()))["passed"])
        self.assertFalse(parity.assess_case("invalid_rule", error, error)["passed"])
        invalid = self._row(payload(errors=[{"type": "Rule parse error", "level": "error"}], scanned=[]), 7)
        self.assertFalse(parity.assess_case("invalid_rule", invalid, invalid)["passed"])
        self.assertFalse(parity.assess_case("invalid_rule", invalid, {**invalid, "returncode": 2})["passed"])

    def test_partial_parsing_variant_preserves_error_locations(self):
        location = {"path": "fixture.py", "start": {"line": 2}, "end": {"line": 2}}
        value = payload(
            errors=[
                {
                    "code": 3,
                    "type": ["PartialParsing", [location]],
                    "level": "warn",
                    "path": "fixture.py",
                    "spans": [{"file": "fixture.py", "start": {"line": 2}, "end": {"line": 2}}],
                }
            ]
        )
        error = self._row(value)
        self.assertTrue(parity.assess_case("parse_error", error, error)["passed"])
        self.assertEqual(error["canonical"]["errors"][0]["type"][1][0]["path"], "fixture.py")
        location["path"] = "../customer.py"
        with self.assertRaises(ValueError):
            self._canonical(value)

    def test_error_span_cannot_hide_a_customer_path(self):
        value = payload(
            errors=[
                {
                    "type": "Syntax error",
                    "level": "warn",
                    "path": "fixture.py",
                    "spans": [{"file": "../customer.py", "start": {"line": 2}}],
                }
            ]
        )
        with self.assertRaises(ValueError):
            self._canonical(value)

    def test_changed_error_end_line_is_not_discarded(self):
        value = payload(
            errors=[
                {
                    "type": "Syntax error",
                    "level": "warn",
                    "path": "fixture.py",
                    "spans": [{"file": "fixture.py", "start": {"line": 2}, "end": {"line": 2}}],
                }
            ]
        )
        first = self._canonical(value)
        value["errors"][0]["spans"][0]["end"]["line"] = 3
        self.assertNotEqual(first, self._canonical(value))

    def test_output_limit_still_cleans_and_reaps(self):
        process = unittest.mock.Mock(pid=12345, returncode=0)

        def launch(*_args, **kwargs):
            kwargs["stdout"].write(b"x" * 9)
            return process

        with (
            patch.object(parity.subprocess, "Popen", side_effect=launch),
            patch.object(parity.smoke, "wait_worker_exit"),
            patch.object(parity.smoke, "terminate_worker_group") as cleanup,
            patch.object(parity.smoke, "WORKER_OUTPUT_LIMIT", 8),
            self.assertRaises(ValueError),
        ):
            parity.run_command(["osemgrep"], executable="/verified/core", cwd=self.directory, env={})
        cleanup.assert_called_once_with(12345)
        process.wait.assert_called_once_with(timeout=10)

    def test_cli_refuses_customer_targets_before_any_launch(self):
        result = subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts/native_semgrep_parity.py"), "--target", "customer.py"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("unrecognized arguments", result.stderr)

    def test_asset_digest_size_symlink_and_executable_checks(self):
        path = self.directory / "tool"
        path.write_bytes(b"fixed")
        digest = parity.sha256_file(path, limit=8)
        self.assertEqual(parity.verify_file(path, digest, limit=8), path)
        path.write_bytes(b"changed")
        with self.assertRaises(ValueError):
            parity.verify_file(path, digest, limit=8)
        with self.assertRaises(ValueError):
            parity.sha256_file(path, limit=2)
        with self.assertRaises(ValueError):
            parity.verify_file(path, parity.sha256_file(path, limit=8), limit=8, executable=True)
        link = self.directory / "linked"
        link.symlink_to(path)
        with self.assertRaises(ValueError):
            parity.verify_file(link, parity.sha256_file(path, limit=8), limit=8)

    def test_fixed_native_argv_and_unknown_cases_cannot_inject_targets(self):
        assets = {
            "python": Path(sys.executable),
            "frontend": self.directory / "semgrep",
            "core": self.directory / "semgrep-core",
        }
        rule = self.directory / "clean_code.yaml"
        command, executable = parity.build_command("native", assets, self.directory, "clean_code_defective")
        self.assertEqual(command[0], "osemgrep")
        self.assertEqual(executable, str(assets["core"]))
        self.assertEqual(command[-3:], ["--config", str(rule), "fixture.py"])
        self.assertIn("--experimental", command)
        self.assertIn("--oss-only", command)
        self.assertNotIn("--oss", command)
        self.assertIn("--project-root", command)
        python_command, executable = parity.build_command("python", assets, self.directory, "clean_code_defective")
        self.assertEqual(python_command[:4], [sys.executable, "-I", "-B", str(assets["frontend"])])
        self.assertNotIn("--experimental", python_command)
        self.assertIn("--legacy", python_command)
        self.assertIn("--oss-only", python_command)
        for frontend, case in (("sh", "clean_code_defective"), ("native", "; sh customer.py")):
            with self.assertRaises(ValueError):
                parity.build_command(frontend, assets, self.directory, case)

    def test_bounded_runner_uses_explicit_executable_and_cleanup_before_wait(self):
        order = []
        process = unittest.mock.Mock(pid=12345, returncode=0)
        process.wait.side_effect = lambda **_kwargs: order.append("reap")
        with (
            patch.object(parity.subprocess, "Popen", return_value=process) as popen,
            patch.object(parity.smoke, "wait_worker_exit", side_effect=subprocess.TimeoutExpired("fixed", 30)),
            patch.object(parity.smoke, "terminate_worker_group", side_effect=lambda _pid: order.append("cleanup")),
            self.assertRaises(subprocess.TimeoutExpired),
        ):
            parity.run_command(["osemgrep", "--version"], executable="/verified/core", cwd=self.directory, env={})
        self.assertEqual(order, ["cleanup", "reap"])
        self.assertEqual(popen.call_args.kwargs["executable"], "/verified/core")
        self.assertTrue(popen.call_args.kwargs["start_new_session"])
        self.assertNotIn("shell", popen.call_args.kwargs)

    def test_fixture_integrity_is_checked_before_launch(self):
        parity.prepare_fixture(self.directory, "clean_code_defective", {"clean_code": b"rules: []\n"})
        (self.directory / "fixture.py").write_text("customer replacement")
        with self.assertRaises(ValueError):
            parity.verify_fixture(self.directory, "clean_code_defective", {"clean_code": b"rules: []\n"})

    def test_receipt_cannot_claim_sandbox_production_or_process_proof(self):
        rows = {name: {"passed": True} for name in parity.CASES}
        receipt = parity.make_receipt(rows, system="Darwin", machine="arm64")
        self.assertTrue(receipt["passed"])
        for flag in ("sandbox_verified", "production_eligible", "single_process_verified"):
            self.assertIs(receipt[flag], False)
        del rows["parse_error"]
        self.assertFalse(parity.make_receipt(rows, system="Darwin", machine="arm64")["passed"])
        self.assertFalse(parity.make_receipt(rows, system="Linux", machine="arm64")["passed"])

    def test_invalid_json_execution_never_becomes_empty_success(self):
        result = subprocess.CompletedProcess(["fixed"], 0, "not JSON", "")
        with self.assertRaises(ValueError):
            parity.execution_row(result, self.directory)
        result.stdout = json.dumps(payload())
        self.assertEqual(parity.execution_row(result, self.directory)["returncode"], 0)


class SourceProvenanceTests(unittest.TestCase):
    def test_receipt_does_not_reread_executed_sources(self):
        captured = parity.smoke.CLEAN
        with (
            patch.object(parity, "ROOT", Path("/missing-checkout")),
            patch.object(parity, "validate_assets", side_effect=ValueError("fixture preflight failure")),
        ):
            report = parity.run_parity()
        self.assertNotIn("harness_sha256", report)
        self.assertEqual(report["smoke_sha256"], parity.hashlib.sha256(parity.SMOKE_SOURCE).hexdigest())
        self.assertEqual(parity.smoke.CLEAN, captured)


class DependencyParityContracts(unittest.TestCase):
    def test_nested_rule_layout_is_mandatory_and_uses_literal_rule_ids(self):
        self.assertIn("nested_clean_code_defective", parity.CASES)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary).resolve()
            parity.prepare_fixture(directory, "nested_clean_code_defective", {"clean_code": b"rules: []\n"})
            self.assertTrue((directory / ".semgrep/clean_code.yaml").is_file())
            assets = {"python": Path(sys.executable), "frontend": directory / "semgrep", "core": directory / "core"}
            for frontend in ("python", "native"):
                argv, _ = parity.build_command(frontend, assets, directory, "nested_clean_code_defective")
                self.assertIn("--no-rewrite-rule-ids", argv)
                self.assertEqual(argv[-2], str(directory / ".semgrep/clean_code.yaml"))

    def test_equal_wrong_invalid_rule_exit_never_passes(self):
        canonical = {"findings": [], "errors": [{"type": "Rule parse error", "level": "error"}], "scanned": []}
        row = {"canonical": canonical, "returncode": 2}
        self.assertFalse(parity.assess_case("invalid_rule", row, row)["passed"])

    def test_receipt_exposes_counts_and_never_admits_dependencies(self):
        rows = {name: {"passed": True} for name in parity.CASES}
        receipt = parity.make_receipt(rows, system="Darwin", machine="arm64")
        self.assertEqual(receipt["matched_cases"], len(parity.CASES))
        self.assertEqual(receipt["required_cases"], len(parity.CASES))
        self.assertIs(receipt["dependency_admitted"], False)


class DistributionBindingTests(unittest.TestCase):
    def test_distribution_metadata_is_hash_pinned_before_execution(self):
        self.assertIn("metadata", parity.ASSET_PINS)
        path, digest = parity.ASSET_PINS["metadata"]
        self.assertEqual(path, parity.SITE / f"semgrep-{parity.VERSION}.dist-info/METADATA")
        with tempfile.TemporaryDirectory() as temporary:
            changed = Path(temporary).resolve() / "METADATA"
            changed.write_bytes(b"Name: semgrep\nVersion: 1.175.0\nRequires-Dist: unreviewed\n")
            with (
                patch.object(parity, "ASSET_PINS", {"metadata": (changed, digest)}),
                self.assertRaisesRegex(ValueError, "SHA-256"),
            ):
                parity.validate_assets()


class VersionedAdapterTests(unittest.TestCase):
    setUp = NativeSemgrepParityTests.setUp
    _canonical = NativeSemgrepParityTests._canonical

    def invalid_native(self):
        data = payload(
            errors=[
                {
                    "code": 2,
                    "type": "Rule parse error",
                    "level": "error",
                    "rule_id": "invalid-pattern",
                    "message": "invalid pattern retained",
                }
            ],
            scanned=[],
        )
        return {
            "returncode": 7,
            "stdout": json.dumps(data),
            "stderr": "raw failure",
            "canonical": self._canonical(data),
        }

    def test_real_discovery_becomes_legacy_selected_paths_without_claiming_analysis(self):
        native = self.invalid_native()
        discovery = {"returncode": 0, "stdout": "fixture.py\n", "stderr": ""}
        adapted = parity.adapt_native_result(native, discovery, self.directory)
        self.assertEqual(adapted["schema"], "specfact-semgrep-1.175.0-legacy-result-v1")
        self.assertEqual(adapted["returncode"], 2)
        self.assertEqual(adapted["payload"]["errors"], json.loads(native["stdout"])["errors"])
        self.assertEqual(adapted["payload"]["paths"]["scanned"], ["fixture.py"])
        self.assertEqual(adapted["analyzed_targets"], [])
        self.assertEqual(native["returncode"], 7)
        self.assertEqual(native["canonical"]["scanned"], [])

    def test_missing_failed_duplicate_outside_or_empty_discovery_rejects(self):
        for discovery in (
            None,
            {"returncode": 1, "stdout": "fixture.py\n"},
            {"returncode": 0, "stdout": ""},
            {"returncode": 0, "stdout": "fixture.py\nfixture.py\n"},
            {"returncode": 0, "stdout": "../customer.py\n"},
        ):
            with self.subTest(discovery=discovery), self.assertRaises(ValueError):
                parity.adapt_native_result(self.invalid_native(), discovery, self.directory)

    def test_other_error_types_and_findings_are_never_mapped_to_rule_failure(self):
        for update in (
            {"results": [finding()]},
            {"errors": [{"code": 7, "type": "SemgrepError", "level": "error", "message": "missing config"}]},
            {"version": "1.176.0"},
        ):
            native = self.invalid_native()
            data = json.loads(native["stdout"])
            data.update(update)
            native["stdout"] = json.dumps(data)
            with self.subTest(update=update), self.assertRaises(ValueError):
                parity.adapt_native_result(native, {"returncode": 0, "stdout": "fixture.py\n"}, self.directory)

    def test_error_code_and_message_are_semantic_and_never_discarded(self):
        data = payload(errors=[{"code": 2, "type": "Rule parse error", "level": "error", "message": "first"}])
        first = self._canonical(data)
        data["errors"][0]["message"] = "changed"
        self.assertNotEqual(first, self._canonical(data))
        data["errors"][0]["message"] = "first"
        data["errors"][0]["code"] = 7
        self.assertNotEqual(first, self._canonical(data))


class CompleteAdapterErrorTests(unittest.TestCase):
    setUp = NativeSemgrepParityTests.setUp
    _canonical = NativeSemgrepParityTests._canonical

    def test_error_columns_and_offsets_are_compared_as_part_of_complete_structure(self):
        data = payload(
            errors=[
                {
                    "code": 3,
                    "type": "Syntax error",
                    "level": "warn",
                    "message": "syntax failed",
                    "path": "fixture.py",
                    "spans": [{"file": "fixture.py", "start": {"line": 2, "col": 5, "offset": 0}}],
                }
            ]
        )
        reference = {"returncode": 0, "stdout": json.dumps(data), "canonical": self._canonical(data)}
        data["errors"][0]["spans"][0]["start"]["col"] = 6
        native = {"returncode": 0, "stdout": json.dumps(data), "discovery": {"returncode": 0, "stdout": "fixture.py\n"}}
        self.assertFalse(parity.assess_adapter_case("parse_error", reference, native, self.directory)["passed"])


class RawErrorControlTests(unittest.TestCase):
    def test_reference_and_native_rule_failure_controls_have_distinct_pinned_statuses(self):
        errors = [{"type": "Rule parse error", "level": "error", "code": 2, "message": "failed pattern"}]
        reference = {"returncode": 2, "canonical": {"findings": [], "errors": errors, "scanned": ["fixture.py"]}}
        native = {"returncode": 7, "canonical": {"findings": [], "errors": errors, "scanned": []}}
        compared = parity.assess_case("invalid_rule", reference, native)
        self.assertEqual(compared["positive_controls"], {"python": True, "native": True})
        self.assertFalse(compared["passed"])
