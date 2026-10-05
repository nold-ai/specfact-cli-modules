"""Contract for private native control snapshots (diagnostic only).

Emit exactly control_state (private worker PID), wait_accepted, wait_pending,
worker_reaped and output_closed. The four flags MUST be JSON booleans. Emit on
initialized launch, valid wait acceptance, terminal reap, output EOF and wait
completion after pending clears, including immediate completion. Stopped,
transient and rejected paths MUST NOT invent terminal/acceptance evidence.
Missing evidence remains unknown in consumers; this producer exports no payload,
status, handles or authority bytes. Eight workers and 64 requests bound emissions.
The actual broker is compiled and ad-hoc signed only with explicit native opt-in;
its spawn, wait, read, select, ptrace and signal operations are safely mocked.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture(name="native_event_binary", scope="module")
def fixture_native_event_binary(tmp_path_factory):
    if os.environ.get("SPECFACT_NATIVE_CONTROL") != "1" or sys.platform != "darwin":
        pytest.skip("explicit native ARM64 control event fixture run")
    target = tmp_path_factory.mktemp("native-events") / "event-test"
    source = Path(__file__).parents[2] / "scripts/macos_managed_boundary/control_events_test.c"
    subprocess.run(
        [
            "/usr/bin/xcrun",
            "clang",
            "-arch",
            "arm64",
            "-Wall",
            "-Wextra",
            "-Werror",
            str(source),
            "-o",
            str(target),
            "-framework",
            "Security",
            "-framework",
            "CoreFoundation",
        ],
        check=True,
        timeout=10,
    )
    subprocess.run(
        ["/usr/bin/codesign", "--force", "--sign", "-", "--options", "runtime", str(target)],
        check=True,
        timeout=10,
    )
    subprocess.run(["/usr/bin/codesign", "--verify", "--strict", str(target)], check=True, timeout=10)
    return target


def assert_snapshot(event):
    assert set(event) == {"control_state", "wait_accepted", "wait_pending", "worker_reaped", "output_closed"}
    assert isinstance(event["control_state"], int) and not isinstance(event["control_state"], bool)
    assert 1234567 <= event["control_state"] < 1234575
    assert all(isinstance(event[key], bool) for key in event if key != "control_state")


def snapshots(binary, scenario):
    result = subprocess.run([str(binary), scenario], check=True, capture_output=True, text=True, timeout=10)
    assert "private-worker-payload" not in result.stdout
    assert "private-reason" not in result.stdout
    events = [json.loads(line) for line in result.stdout.splitlines()]
    states = [event for event in events if "control_state" in event]
    for event in states:
        assert_snapshot(event)
    return [
        tuple(event[key] for key in ("wait_accepted", "wait_pending", "worker_reaped", "output_closed"))
        for event in states
    ]


@pytest.mark.parametrize(
    ("scenario", "expected"),
    [
        ("launch", [(False, False, False, False)]),
        ("pending", [(False, False, False, False), (True, True, False, False)]),
        ("rejected", [(False, False, False, False), (True, True, False, False)]),
        ("stopped", [(False, False, False, False), (True, True, False, False)]),
        ("held-stop", [(False, False, False, False), (True, True, False, False)]),
        (
            "immediate",
            [
                (False, False, False, False),
                (False, False, True, False),
                (False, False, True, True),
                (True, False, True, True),
            ],
        ),
        (
            "reap-first",
            [
                (False, False, False, False),
                (True, True, False, False),
                (True, True, True, False),
                (True, True, True, True),
                (True, False, True, True),
            ],
        ),
        (
            "eof-first",
            [
                (False, False, False, False),
                (True, True, False, False),
                (True, True, False, True),
                (True, True, True, True),
                (True, False, True, True),
            ],
        ),
        (
            "transient",
            [
                (False, False, False, False),
                (True, True, False, False),
                (True, True, True, False),
                (True, True, True, True),
                (True, False, True, True),
            ],
        ),
    ],
)
def test_control_snapshot_transitions(native_event_binary, scenario, expected):
    assert snapshots(native_event_binary, scenario) == expected


def test_control_snapshot_emissions_are_bounded(native_event_binary):
    states = snapshots(native_event_binary, "bounds")
    assert len(states) == 8 * 3 + 64
    assert states[-64:] == [(True, False, True, True)] * 64


@pytest.mark.parametrize(
    "scenario",
    [
        "reconcile-empty",
        "reconcile-reaped",
        "reconcile-active",
        "reconcile-held",
        "reconcile-earlier",
        "reconcile-later",
    ],
)
def test_owned_child_reconciliation_deadline(native_event_binary, scenario):
    snapshots(native_event_binary, scenario)


def test_owned_child_completion_without_signal_pipe_readiness(native_event_binary):
    assert snapshots(native_event_binary, "reconcile-lost") == [
        (False, False, False, False),
        (True, True, False, False),
        (True, True, False, True),
        (True, True, True, True),
        (True, False, True, True),
    ]
