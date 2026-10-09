import json
from pathlib import Path

import pytest

from tests.unit.test_macos_python_candidate_source import candidate


def _fixture_log_tail(root: Path) -> str:
    try:
        with (root / "diagnostics.log").open("rb") as stream:
            stream.seek(0, 2)
            stream.seek(max(0, stream.tell() - 8192))
            return stream.read(8192).decode("utf-8", errors="replace")
    except OSError:
        return ""


def _native_fixture_identity(marker: dict) -> dict[str, object]:
    from scripts.macos_managed_boundary.control import FAILURE_PHASES

    case, phase = marker.get("failed_case"), marker.get("failure_phase")
    cases = {"python-" + name for name in ("clean", "defective", "denials", "trap", "reexec", "loop")}
    if not isinstance(case, str) or not isinstance(phase, str) or case not in cases or phase not in FAILURE_PHASES:
        return {}
    return {"case": case, "phase": phase}


def _native_failure_marker(line: str) -> dict[str, object]:
    from scripts.macos_managed_boundary.control import STATE

    try:
        marker = json.loads(line)
    except (ValueError, RecursionError):
        return {}
    if not isinstance(marker, dict):
        return {}
    projected = _native_fixture_identity(marker)
    if not projected:
        return {}
    state = marker.get("last_worker_state")
    if isinstance(state, dict) and all(isinstance(state.get(field), bool) for field in STATE.STATE_FIELDS):
        projected["state"] = {field: state[field] for field in STATE.STATE_FIELDS}
    if result := STATE.project_worker_result(marker.get("last_worker_result")):
        projected["result"] = result
    return projected


def native_failure_summary(root: Path, version: str) -> dict[str, object]:
    """Expose only fixed fixture identity and existing boolean wait observations."""
    if version not in ("3.11", "3.12", "3.13"):
        return {}
    for line in reversed(_fixture_log_tail(root).splitlines()):
        if marker := _native_failure_marker(line):
            return {"abi": version, **marker}
    return {"abi": version}


def _run_native_candidate(module, root: Path, runtime: Path, version: str):
    from contextlib import redirect_stdout

    try:
        with (root / "diagnostics.log").open("w") as stream, redirect_stdout(stream):
            return module.run(root, runtime, version)
    except Exception as error:
        (root / "failure.txt").write_text(f"{type(error).__name__}: {error}\n")
        print(json.dumps(native_failure_summary(root, version), sort_keys=True))
        raise AssertionError("Native proof failed; raw diagnostics retained privately") from None


def test_native_candidate_matrix():
    import os
    import platform
    import tempfile

    selected = os.environ.get("SPECFACT_CPYTHON_CANDIDATE_INPUTS")
    if not selected:
        pytest.skip("maintainer-only native inputs not selected")
    assert platform.system() == "Darwin" and platform.machine() == "arm64"
    module = candidate()

    inputs = json.loads(selected)
    assert set(inputs) == {"3.11", "3.12", "3.13"}
    for version, runtime in sorted(inputs.items()):
        # Retain private raw diagnostics even after a failed measurement.
        root = Path(tempfile.mkdtemp(prefix="sf-python-pytest-", dir="/private/tmp"))
        result = _run_native_candidate(module, root, Path(runtime), version)
        assert result["candidate_passed"] is True
        assert result["cases"] == result["passed"] == 6
        assert result["production_approved"] is False
        assert result["signed_boundary_verified"] is False
