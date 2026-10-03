"""Startup evidence must distinguish survivors, missing identities and controls."""

from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture(name="startup")
def fixture_startup():
    path = Path(__file__).parents[2] / "scripts/macos_managed_boundary/startup.py"
    spec = importlib.util.spec_from_file_location("managed_startup", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_job_has_bounded_nonpersistent_ownership(startup, tmp_path):
    job = startup.job_config(
        "io.specfact.proof.test",
        startup.BootstrapInputs(tmp_path / "broker", tmp_path / "worker", "fixed profile"),
        tmp_path,
        False,
    )
    assert job["AbandonProcessGroup"] is False
    assert job["KeepAlive"] is False
    assert job["LaunchOnlyOnce"] is True
    assert 0 < job["ExitTimeOut"] < 5
    assert job["RunAtLoad"] is True
    assert all(Path(arg).is_absolute() for arg in job["ProgramArguments"][:2])


@pytest.mark.parametrize("field", ["pid", "start_sec", "start_usec"])
def test_reused_pid_is_not_fixture(startup, field):
    identity = {"pid": 123, "start_sec": 10, "start_usec": 20}
    changed = dict(identity)
    changed[field] += 1
    assert startup.same_birth_identity(identity, changed) is False


def test_same_birth_identity_matches(startup):
    identity = {"pid": 123, "start_sec": 10, "start_usec": 20}
    assert startup.same_birth_identity(identity, dict(identity)) is True


def test_missing_identity_is_never_success(startup):
    with pytest.raises(ValueError):
        startup.same_birth_identity({"pid": 123}, {"pid": 123})


@pytest.mark.parametrize("positive,negative", [(False, True), (True, False), (False, False)])
def test_failed_cleanup_or_control_cannot_pass(startup, positive, negative):
    report = startup.receipt(positive, negative, 100, [])
    assert report["startup_subset_passed"] is False
    assert report["production_approved"] is False


def test_one_success_cannot_claim_repetition_gate(startup):
    report = startup.receipt(True, True, 1, [])
    assert report["repetition_gate_passed"] is False
    assert report["production_approved"] is False


def test_repetition_claim_requires_actual_trials(startup):
    report = startup.receipt(True, True, 100, [])
    assert report["repetition_gate_passed"] is False


def test_required_startup_transitions_are_not_dropped(startup):
    assert set(startup.RACE_MODES) == {"suspended", "pretrace", "trace-stopped", "traced", "exec", "confined"}


@pytest.mark.parametrize("mode,flags", [("suspended", 2), ("pretrace", 2), ("traced", 0), ("exec", 0), ("confined", 0)])
def test_kernel_tracing_state_is_verified(startup, mode, flags):
    with pytest.raises(ValueError):
        startup.validate_tracing(mode, {"flags": flags})


@pytest.mark.parametrize(
    "mode,flags", [("suspended", 0), ("pretrace", 0), ("trace-stopped", 2), ("traced", 2), ("exec", 2), ("confined", 2)]
)
def test_expected_kernel_tracing_state_is_accepted(startup, mode, flags):
    startup.validate_tracing(mode, {"flags": flags})


def test_late_disappearance_cannot_pass_cleanup_bound(startup, monkeypatch):
    observed_times = iter([5.01] * 8)
    monkeypatch.setattr(startup.time, "monotonic", lambda: next(observed_times))
    monkeypatch.setattr(startup, "alive", lambda *_args: False)
    monkeypatch.setattr(startup, "job_absent", lambda _service: True)
    signals = []
    monkeypatch.setattr(startup, "signal_fixture", lambda _observer, identity: signals.append(identity) or (0.0, 0.0))
    identities = [{"pid": 100}, {"pid": 101}]
    result = startup.observe_cleanup(Path("observer"), identities, "service", False, startup.StartupPhase("pretrace"))
    assert result["passed"] is False
    assert signals == [identities[0]]


def test_registered_job_cannot_pass_worker_cleanup(startup, monkeypatch):
    observed_times = iter([0.0, 6.0, 6.0, 6.0, 6.0])
    monkeypatch.setattr(startup.time, "monotonic", lambda: next(observed_times))
    monkeypatch.setattr(startup, "alive", lambda *_args: False)
    monkeypatch.setattr(startup, "job_absent", lambda _service: False)
    monkeypatch.setattr(startup, "signal_fixture", lambda *_args: (0.0, 0.0))
    result = startup.observe_cleanup(
        Path("observer"), [{"pid": 100}, {"pid": 101}], "service", False, startup.StartupPhase("pretrace")
    )
    assert result["passed"] is False


def test_cleanup_error_still_attempts_job_removal(startup, monkeypatch):
    def fail(*_args):
        raise RuntimeError("observer failed")

    commands = []
    monkeypatch.setattr(startup, "signal_fixture", fail)
    monkeypatch.setattr(startup, "command", lambda args, **_kwargs: commands.append(args))
    monkeypatch.setattr(startup, "job_absent", lambda _service: True)
    with pytest.raises(RuntimeError, match="observer failed"):
        startup.remove_job(Path("observer"), [{"pid": 100}], "service")
    assert commands == [["/bin/launchctl", "bootout", "service"]]


def test_partial_identity_capture_is_retained_for_cleanup(startup, monkeypatch):
    responses = iter([{"pid": 100}, None])
    monkeypatch.setattr(startup, "observe", lambda *_args: next(responses))
    identities = []
    with pytest.raises(RuntimeError, match="worker disappeared"):
        startup.capture_identity(Path("observer"), {"broker": 100, "worker": 101}, identities)
    assert identities == [{"pid": 100}]


def test_launchd_inspection_error_cannot_be_absence(startup, monkeypatch):

    monkeypatch.setattr(startup, "command", lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stderr="failure"))
    with pytest.raises(RuntimeError, match="inspect job removal"):
        startup.job_absent("service")


def test_worker_first_output_does_not_complete_identity_wait(startup, monkeypatch, tmp_path):
    path = tmp_path / "events"
    path.write_text("ready:pretrace\n")

    def append_identity(_seconds):
        path.write_text('ready:pretrace\n{"broker":100,"worker":101}\n')

    monkeypatch.setattr(startup.time, "sleep", append_identity)
    content = startup.wait_events(path, "identity")
    assert '{"broker":100,"worker":101}' in content


def test_fallback_overlap_is_rejected(startup):
    with pytest.raises(RuntimeError, match="fallback"):
        startup.validate_fallback("fallback-deadline=7000000000\n", 3.0)


def test_safe_fallback_window_is_accepted(startup):
    startup.validate_fallback("fallback-deadline=60000000000\n", 3.0)


def test_missing_audit_token_never_signals_numeric_pid(startup):
    with pytest.raises(ValueError, match="audit"):
        startup.signal_fixture(Path("observer"), {"pid": 100})


def test_delayed_registration_can_settle_within_deadline(startup, monkeypatch):
    states = iter([False, False, True])
    monkeypatch.setattr(startup, "job_absent", lambda _service: next(states))
    monkeypatch.setattr(startup.time, "monotonic", lambda: 0.0)
    monkeypatch.setattr(startup.time, "sleep", lambda _seconds: None)
    assert startup.wait_job_absent("service", 5.0) is True


def test_audit_signaling_uses_kernel_issue_times(startup, monkeypatch):

    token = [501, 501, 20, 501, 20, 100, 1, 10]
    commands = []

    def run(args, **_kwargs):
        commands.append(args)
        return SimpleNamespace(returncode=0, stdout='{"before_ns":1000000000,"after_ns":1000000100}')

    monkeypatch.setattr(startup, "command", run)
    assert startup.signal_fixture(Path("observer"), {"pid": 100, "audit_token": token}) == (1.0, 1.0000001)
    assert commands == [["observer", "--signal", *map(str, token)]]


def test_broker_already_gone_cannot_pass_death_trial(startup, monkeypatch):
    monkeypatch.setattr(startup, "signal_fixture", lambda *_args: None)
    with pytest.raises(RuntimeError, match="before injected death"):
        startup.observe_cleanup(
            Path("observer"), [{"pid": 100}, {"pid": 101}], "service", False, startup.StartupPhase("pretrace")
        )


def test_actual_runtime_trap_after_exec_is_preserved(startup, tmp_path):

    if os.environ.get("SPECFACT_NATIVE_STARTUP") != "1":
        pytest.skip("explicit native startup fixture run")
    broker, worker, observer, _inventory = startup.build(tmp_path)
    result = startup.trial(
        startup.NativeBinaries(broker, worker, observer),
        tmp_path / "runtime-trap",
        False,
        "runtime-trap",
        (Path(startup.__file__).parent / "fixture.sb").read_text(),
    )
    assert result["passed"] is True


def test_source_digest_identifies_the_bytes_compiled(startup, monkeypatch, tmp_path):

    source = tmp_path / "source"
    source.mkdir()
    approved = {}
    for name in ("broker", "worker", "observe"):
        path = source / f"startup_{name}.c"
        approved[path.name] = f"approved {name}".encode()
        path.write_bytes(approved[path.name])
    monkeypatch.setattr(startup, "__file__", str(source / "startup.py"))
    build = tmp_path / "build"
    build.mkdir()
    compiled = []

    def mutate_current(args):
        if "clang" in args:
            snapshot = Path(args[args.index("-o") - 1])
            name = snapshot.name.removeprefix("source-").removesuffix(".c")
            original = source / f"startup_{'observe' if name == 'observer' else name}.c"
            original.write_bytes(b"changed after capture")
            compiled.append(snapshot.read_bytes())
            Path(args[-1]).write_bytes(b"binary")
        return SimpleNamespace(stderr="flags=0x10002(adhoc,runtime)\nSignature=adhoc", stdout="")

    monkeypatch.setattr(startup, "command", mutate_current)
    _broker, _worker, _observer, inventory = startup.build(build)
    assert compiled == list(approved.values())
    assert [item["source_sha256"] for item in inventory] == [hashlib.sha256(raw).hexdigest() for raw in compiled]


def test_every_startup_launch_uses_the_supplied_profile(startup, monkeypatch, tmp_path):
    profiles = []

    def trial(_binaries, _directory, abandon, mode, profile):
        profiles.append(profile)
        return {"passed": True, "mode": mode, "abandon_process_group": abandon}

    monkeypatch.setattr(startup, "trial", trial)
    startup.run_trials(
        startup.NativeBinaries(Path("broker"), Path("worker"), Path("observer")), "captured policy", tmp_path, 2
    )
    assert profiles == ["captured policy"] * 17


def test_teardown_observes_asynchronous_job_removal_once(startup, monkeypatch):
    states = iter((False, False, True))
    clock = iter((0, 1, 2, 3, 4))
    monkeypatch.setattr(startup.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(startup.time, "sleep", lambda _delay: None)
    monkeypatch.setattr(startup, "job_absent", lambda _service: next(states))
    monkeypatch.setattr(startup, "signal_fixture", lambda *_args: None)
    issued = []
    monkeypatch.setattr(startup, "command", lambda args, **_kwargs: issued.append(args))
    startup.remove_job(Path("observer"), [{"pid": 100}], "owned-service")
    assert issued == [["/bin/launchctl", "bootout", "owned-service"]]


def test_teardown_cannot_verify_after_original_five_second_bound(startup, monkeypatch):
    clock = iter((0, 6))
    monkeypatch.setattr(startup.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(startup, "job_absent", lambda _service: True)
    monkeypatch.setattr(startup, "signal_fixture", lambda *_args: None)
    monkeypatch.setattr(startup, "command", lambda *_args, **_kwargs: None)
    with pytest.raises(RuntimeError, match="job removal could not be verified"):
        startup.remove_job(Path("observer"), [], "owned-service")
