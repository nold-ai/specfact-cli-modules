"""Physical characterization of untrusted native pytest receipt forgery."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from specfact_code_review.run import runner


def test_project_atexit_forges_observer_receipts_without_controller_gate(tmp_path: Path) -> None:
    capsule, project, output, temporary = (tmp_path / name for name in ("capsule", "project", "output", "temporary"))
    for root in (capsule, project, output, temporary):
        root.mkdir(mode=0o700)
    evidence = temporary / "pytest-evidence"
    evidence.mkdir()
    observer, junit, coverage = (evidence / name for name in ("observer.json", "junit.xml", "coverage.json"))
    node = "test_forgery.py::test_forgery"
    forged_observer = [
        {"nodeid": node, "phase": phase, "passed": True, "skipped": False, "wasxfail": ""}
        for phase in ("collection", "setup", "call", "teardown")
    ]
    test_file = project / "test_forgery.py"
    test_file.write_text(
        "import atexit, json, os\n"
        "from pathlib import Path\n"
        "def test_forgery():\n"
        "    def forge():\n"
        f"        Path({str(observer)!r}).write_text(json.dumps({forged_observer!r}))\n"
        f'        Path({str(junit)!r}).write_text(\'<testsuite><testcase classname="test_forgery" name="test_forgery"/></testsuite>\')\n'
        f"        Path({str(coverage)!r}).write_text('{{\"files\": {{}}}}')\n"
        "        os._exit(0)\n"
        "    atexit.register(forge)\n"
        "    assert False, 'physical failed test'\n",
        encoding="utf-8",
    )
    # This characterizes the observer's project-origin evidence, not the OS
    # boundary. Broker startup and dependency admission have separate tests.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            runner._pytest_observer_script(),
            str(observer),
            "--import-mode=importlib",
            "--cov",
            str(project),
            "--cov-fail-under=0",
            f"--cov-report=json:{coverage}",
            f"--junitxml={junit}",
            str(test_file),
        ],
        cwd=project,
        env={**os.environ, "COVERAGE_FILE": str(evidence / ".coverage"), "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(observer.read_text(encoding="utf-8")) == forged_observer
    assert json.loads(coverage.read_text(encoding="utf-8")) == {"files": {}}
    observed, junit_records = runner._load_pytest_outcome_evidence(observer, junit)
    outcome = runner.reconcile_pytest_outcomes(
        observer=observed, junit=junit_records, process_exit=result.returncode, planned=(node,)
    )
    assert outcome.status == "PASS", "the fixture demonstrates the accepted limit of project-origin pytest results"
