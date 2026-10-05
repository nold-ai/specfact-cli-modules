"""Resource evidence rejects signal-only, unpaired and rescued limit claims."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


@pytest.fixture(name="limits")
def fixture_limits():
    path = Path(__file__).parents[2] / "scripts/macos_managed_boundary/resource_limits.py"
    spec = importlib.util.spec_from_file_location("resource_proof", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cpu_signal_controls_cannot_be_omitted(limits):
    assert {"cpu-default", "cpu-ignore", "cpu-block", "cpu-control"} <= set(limits.CASES)
    assert {"wall-ignore", "wall-block"} <= set(limits.CASES)


def test_readback_and_raise_denial_both_required(limits):
    record = {
        "type": "limit",
        "resource": "NOFILE",
        "value": 32,
        "set_errno": 0,
        "raise_errno": 1,
        "soft": 32,
        "hard": 32,
    }
    limits.verify_limit(record)
    for field, value in (("set_errno", 22), ("raise_errno", 0), ("soft", 33), ("hard", 33)):
        with pytest.raises(RuntimeError):
            limits.verify_limit({**record, field: value})


@pytest.mark.parametrize("survivor,late,rescued", [(True, False, False), (False, True, False), (False, False, True)])
def test_cleanup_cannot_pass_on_rescue_or_late_observation(limits, survivor, late, rescued):
    assert not limits.cleanup_passed(survivor=survivor, seconds=5.01 if late else 1, rescued=rescued)


def test_default_cpu_signal_is_not_hard_cpu_proof(limits):
    trials = [{"case": "cpu-default", "passed": True, "signal": 24}]
    report = limits.receipt(trials)
    assert not report["resource_gate_passed"]
    assert not report["kernel_hard_cpu_enforced"]
    assert not report["production_approved"]


def test_full_fixture_suite_still_cannot_approve_production(limits):
    trials = [{"case": case, "passed": True, "enforced": False} for case in limits.CASES]
    report = limits.receipt(trials)
    assert report["probe_suite_passed"]
    assert not report["resource_gate_passed"]
    assert not report["production_approved"]


def test_timeout_never_becomes_a_successful_probe(limits):
    trials = [{"case": case, "passed": True} for case in limits.CASES]
    trials[0]["command_timeout"] = True
    assert not limits.receipt(trials)["probe_suite_passed"]


def test_survivor_failure_never_passes_suite(limits):
    trials = [{"case": case, "passed": True} for case in limits.CASES]
    trials[0]["passed"] = False
    assert not limits.receipt(trials)["probe_suite_passed"]


def test_lifecycle_count_comes_from_actual_evidence(limits):
    trials = [{"case": case, "passed": True} for case in limits.CASES]
    assert not limits.receipt(trials)["resource_lifecycle_subset_passed"]
    for case in ("death-ignore", "death-block"):
        trials.extend({"case": case, "passed": True} for _ in range(100))
    assert limits.receipt(trials)["resource_lifecycle_subset_passed"]


def test_missing_native_cpu_accounting_rejected(limits):
    with pytest.raises(RuntimeError):
        limits.verify_cpu("cpu-ignore", [], {"signal": 0, "exit": 37})


def test_exceeding_cpu_accounting_is_observed_only(limits):
    result = limits.verify_cpu(
        "cpu-ignore", [{"type": "cpu", "seconds": 3.0}], {"signal": 0, "exit": 37, "cpu_seconds": 3.01}
    )
    assert result["enforced"] is False
    assert result["classification"] == "observed-only"
    assert "SIGXCPU" in result["observation"]


def test_mach_vm_bypass_cannot_be_called_enforced(limits):
    records = [{"type": "probe", "positive": True, "over_errno": 12, "mach_positive": True, "mach_over_error": 0}]
    records.extend(limit_records("AS", 33555456))
    records.append({"type": "baseline", "virtual_bytes": 1024})
    status = {"exit": 37, "signal": 0, "safety_timeout": False}
    assert not limits.verify_probe("as", records, status)["enforced"]


def test_failed_mach_positive_control_rejects(limits):
    records = [{"type": "probe", "positive": True, "over_errno": 0, "mach_positive": False, "mach_over_error": 0}]
    records.extend(limit_records())
    with pytest.raises(RuntimeError):
        limits.verify_probe("as-control", records, {"exit": 37, "signal": 0})


def limit_records(resource=None, value=0):
    records = []
    for name, ceiling in [("CORE", 0)] + ([(resource, value)] if resource else []):
        for phase in ("pre", "post"):
            records.append(
                {
                    "type": "limit",
                    "resource": name,
                    "phase": phase,
                    "value": ceiling,
                    "set_errno": 0,
                    "raise_errno": 1,
                    "soft": ceiling,
                    "hard": ceiling,
                }
            )
    return records


def test_missing_limit_evidence_rejects(limits):
    with pytest.raises(RuntimeError):
        limits.verify_evidence("cpu-default", [])


def test_changed_fixed_ceiling_rejects(limits):
    with pytest.raises(RuntimeError):
        limits.verify_evidence("nofile", limit_records("NOFILE", 33))


def test_missing_post_confinement_readback_rejects(limits):
    records = limit_records("NOFILE", 32)
    with pytest.raises(RuntimeError):
        limits.verify_evidence("nofile", records[:-1])


def test_watchdog_requires_original_native_deadline(limits):
    records = [*limit_records("CPU", 1), {"type": "cpu-ready"}, {"type": "timer", "deadline_ms": 1500}]
    status = {"timer_fired": True, "signal": 9, "exit": -1, "elapsed_seconds": 1.6}
    with pytest.raises(RuntimeError):
        limits.verify_probe("wall-ignore", records, status)


def test_only_admitted_measured_bounds_gate_resource_subset(limits):
    admitted = {"nofile", "fsize", "as", "wall-ignore", "wall-block"}
    trials = [{"case": case, "passed": True, "enforced": case in admitted} for case in limits.CASES]
    for case in ("death-ignore", "death-block"):
        trials.extend({"case": case, "passed": True} for _ in range(100))
    report = limits.receipt(trials)
    assert report["resource_gate_passed"]
    assert not report["kernel_hard_cpu_enforced"]
    assert not report["physical_ram_ceiling_proven"]
    assert not report["production_approved"]


def test_missing_admitted_enforcement_blocks_resource_subset(limits):
    admitted = {"nofile", "fsize", "wall-ignore", "wall-block"}
    trials = [{"case": case, "passed": True, "enforced": case in admitted} for case in limits.CASES]
    for case in ("death-ignore", "death-block"):
        trials.extend({"case": case, "passed": True} for _ in range(100))
    assert not limits.receipt(trials)["resource_gate_passed"]


@pytest.mark.parametrize("completion", [True, None])
def test_competing_worker_completion_rejects_death_proof(limits, completion):
    with pytest.raises(RuntimeError):
        limits.verify_death_window([{"type": "cpu-ready", "self_completion": completion}])


def test_noncompleting_death_fixture_is_required(limits):
    limits.verify_death_window([{"type": "cpu-ready", "self_completion": False}])


def test_mach_worker_resource_header_api_and_profile(limits):
    header = (limits.SOURCE / "control_resource.h").read_text()
    assert "control_resource_configure" in header
    assert "control_resource_verify" in header
    assert "CONTROL_RESOURCE_POLICY" in header
    assert "SYS_setrlimit" in header


def test_actual_worker_configures_and_verifies_before_fixture(limits):
    worker = (limits.SOURCE / "control_worker.c").read_text()
    assert '#include "control_resource.h"' in worker
    confine = worker[worker.index("static int confine(int") : worker.index("static int exec_target")]
    assert confine.index("control_resource_configure(") < confine.index("return init(profile")
    assert worker.index("control_resource_verify(") < worker.index("result = control_probes(1,")
    assert worker.count("CONTROL_RESOURCE_POLICY") == 2


def test_resource_mach_gate_requires_native_transport_and_races(limits):
    with pytest.raises(RuntimeError):
        limits.verify_mach_resource_receipt({"signal_transport": "bsd", "production_approved": False})


def test_mode13_signal_ignore_only_after_kernel_tracing(limits):
    worker = (limits.SOURCE / "control_worker.c").read_text()
    assert worker.index("ptrace(PT_TRACE_ME") < worker.index("mode == 13 && signal")
    assert worker.index("mode == 13 && signal") < worker.index("ptrace(PT_SIGEXC")


def test_mach_record_checks_numeric_baseline_delta(limits):
    good = "resource-bounds vm-baseline=500000000000 vm-delta=1073741824 vm-ceiling=501073741824 nofile=128 fsize=16777216 api-denied=1"
    assert limits.parse_control_resources(good)["vm-ceiling"] == 501073741824
    for wrong in (
        good.replace("nofile=128", "nofile=129"),
        good.replace("501073741824", "501073741825"),
        good + "\n" + good,
    ):
        with pytest.raises(RuntimeError):
            limits.parse_control_resources(wrong)


def test_mach_receipt_missing_case_counts_cannot_admit(limits):
    report = {
        "signal_transport": "mach-exception-v1",
        "resource_records_verified": True,
        "protocol_passed": True,
        "worker_header_bound": True,
        "lifecycle_counts": {"one": 100},
        "all_trials_passed": True,
        "production_approved": False,
    }
    with pytest.raises(RuntimeError):
        limits.verify_mach_resource_receipt(report)


def test_actual_numeric_probe_requires_paired_denials(limits):
    with pytest.raises(RuntimeError):
        limits.verify_control_probe({"nofile": 128, "fsize_bytes": 16777216})
