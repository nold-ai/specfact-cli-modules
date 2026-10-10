"""Required controller shell proofs; never executed inside the sealed portable runtime."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.support.capsule_review_fixtures import REPO_ROOT, STEP_NAME, public_projector
from tests.unit.test_capsule_review_projection import _write_preparation_fixture


def _write_preparation_interpreter(tmp_path):

    interpreter = tmp_path / "venv/bin/python"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text(
        "#!" + sys.executable + "\n"
        "import os,sys\nfrom pathlib import Path\n"
        "if sys.argv[1:3] == ['-I','-c']:\n"
        "    if os.environ['REPORT_CASE'] == 'missing':\n"
        "        Path('commit-review-preparation.private.json').unlink()\n"
        "    else: print(Path('controlled-report.json').read_text())\n"
        "    raise SystemExit(int(os.environ['PREPARATION_EXIT']))\n"
        "os.execv(sys.executable, [sys.executable, *sys.argv[1:]])\n"
    )
    interpreter.chmod(0o700)


@pytest.fixture(name="preparation_shell")
def preparation_shell_fixture(tmp_path, monkeypatch):

    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    step = next(item for item in workflow["jobs"]["customer"]["steps"] if item.get("name") == STEP_NAME)
    recipe = "# Provisioning" + step["run"].split("# Provisioning", 1)[1].split("review_exit=0", 1)[0]
    _write_preparation_interpreter(tmp_path)

    def invoke(preparation):
        preparation_exit, report_case = preparation
        report = _write_preparation_fixture(tmp_path, "prepared" if report_case == "missing" else report_case)
        (tmp_path / "controlled-report.json").write_text(report.read_text())
        for name, value in {
            "CUSTOMER_ROOT": str(tmp_path),
            "GITHUB_WORKSPACE": str(tmp_path),
            "PROJECT_CONFIG": str(tmp_path / "project.toml"),
            "PREPARATION_EXIT": str(preparation_exit),
            "REPORT_CASE": report_case,
        }.items():
            monkeypatch.setenv(name, value)
        return subprocess.run(
            ["bash", "-c", "set -euo pipefail\n" + recipe + "printf 'REVIEW_STARTED\\n'"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

    return invoke


@pytest.mark.parametrize(
    "preparation,expected",
    [
        ((0, "prepared"), (0, "PREPARED", "prepared")),
        ((0, "not_applicable"), (0, "NOT_APPLICABLE", "not_applicable")),
        ((7, "not_applicable"), (7, "INCOMPLETE", "preparation_command_failed")),
        ((0, "not_applicable_reason"), (1, "INCOMPLETE", "invalid_not_applicable")),
        ((7, "prepared"), (7, "INCOMPLETE", "preparation_command_failed")),
        ((0, "invalid"), (1, "INCOMPLETE", "invalid_json")),
        ((7, "invalid"), (7, "INCOMPLETE", "invalid_json")),
        ((0, "missing"), (1, "INCOMPLETE", "unreadable_report")),
        ((7, "missing"), (7, "INCOMPLETE", "unreadable_report")),
    ],
)
def test_preparation_shell_preserves_failure_and_projects_incomplete(preparation_shell, preparation, expected):

    expected_exit, expected_status, expected_outcome = expected
    accepted = expected_status in {"PREPARED", "NOT_APPLICABLE"}
    result = preparation_shell(preparation)
    assert result.returncode == expected_exit
    lines = result.stdout.splitlines()
    assert lines, "every preparation exit must produce bounded diagnosis"
    projection = json.loads(lines[0])
    assert projection["status"] == expected_status
    assert ("REVIEW_STARTED" in lines) is accepted
    assert "private" not in result.stdout + result.stderr
    assert projection["report_outcome"] == expected_outcome


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize("review_exit", [17, 124])
def test_projector_crash_preserves_original_review_exit(tmp_path: Path, job_name, review_exit):
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    name = STEP_NAME if job_name == "customer" else "Prepare and review through the authenticated installed controller"
    recipe = next(step["run"] for step in workflow["jobs"][job_name]["steps"] if step.get("name") == name)
    invocation = next(line for line in recipe.splitlines() if "REVIEW_PUBLIC_EXIT=" in line and "<<'PY'" in line)
    guard = invocation.split("<<'PY'", 1)[1]
    report = tmp_path / ".specfact/code-review.json"
    report.parent.mkdir()
    report.write_text('{"analyzer_evidence":42}')
    program = public_projector(job_name)
    shell = (
        f"set -e\nreview_exit={review_exit}\n"
        f"REVIEW_PUBLIC_EXIT=$review_exit {shlex.quote(sys.executable)} - <<'PY'{guard}\n"
        + program
        + '\nPY\nexit "$review_exit"\n'
    )
    result = subprocess.run(
        ["bash", "-c", shell],
        cwd=tmp_path,
        env=dict(os.environ, CUSTOMER_ROOT=str(tmp_path), TRUSTED_ROOT=str(tmp_path)),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == review_exit, "Diagnostics must preserve the original failed review result"
    assert result.stderr == "", "Projector tracebacks must remain private"
    assert json.loads(result.stdout.splitlines()[-1]) == {
        "status": "INCOMPLETE",
        "phase": "review",
        "diagnostic": "review_projection_failed",
    }
    assert "TypeError" in (tmp_path / "review-projection.private.log").read_text()


@pytest.mark.parametrize("review_exit", [17, 124])
def test_candidate_secondary_projector_crash_preserves_review_exit(tmp_path: Path, review_exit):
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    recipe = next(step["run"] for step in workflow["jobs"]["customer"]["steps"] if step.get("name") == STEP_NAME)
    marker = "<<'PY_CANDIDATE_FAILURE'"
    invocation = next(line for line in recipe.splitlines() if marker in line)
    guard = invocation.split(marker, 1)[1]
    program = recipe.split(marker, 1)[1].split("\n", 1)[1].split("\nPY_CANDIDATE_FAILURE", 1)[0]
    shell = (
        f"set -e\nreview_exit={review_exit}\n{shlex.quote(sys.executable)} - {marker}{guard}\n"
        + "raise SystemExit(3)\n"
        + program
        + '\nPY_CANDIDATE_FAILURE\nexit "$review_exit"\n'
    )
    result = subprocess.run(
        ["bash", "-c", shell],
        cwd=tmp_path,
        env=dict(os.environ, CUSTOMER_ROOT=str(tmp_path)),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == review_exit, "Every diagnostic invocation must preserve the failed review result"
    assert result.stderr == ""
    assert json.loads(result.stdout) == {
        "status": "INCOMPLETE",
        "phase": "review",
        "diagnostic": "review_projection_failed",
    }


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize("module_name", ["ast", "json"])
@pytest.mark.parametrize("import_origin", ["checkout", "pythonpath"])
@pytest.mark.parametrize("review_exit", [17, 124])
def test_actual_projector_launch_excludes_untrusted_imports(
    tmp_path: Path, job_name, module_name, import_origin, review_exit
):
    invocation = _projector_invocation(job_name)
    candidate, ambient, marker, report = _poisoned_projector_paths(tmp_path, job_name, module_name, import_origin)
    shell = f"set -e\ntrusted_env=(env)\nreview_exit={review_exit}\n" + invocation + "\n" + public_projector(job_name)
    shell += '\nPY\nexit "$review_exit"\n'
    environment = dict(os.environ, CUSTOMER_ROOT=str(tmp_path), TRUSTED_ROOT=str(tmp_path), PYTHONPATH=str(ambient))
    environment["REVIEW_PUBLIC_REPORT"] = str(report)
    result = subprocess.run(
        ["bash", "-c", shell], cwd=candidate, env=environment, capture_output=True, text=True, check=False
    )
    _assert_projector_result(result, marker, review_exit)
    _assert_projector_private_state(result, report)


def _projector_invocation(job_name):
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    name = STEP_NAME if job_name == "customer" else "Prepare and review through the authenticated installed controller"
    recipe = next(step["run"] for step in workflow["jobs"][job_name]["steps"] if step.get("name") == name)
    return next(line for line in recipe.splitlines() if "REVIEW_PUBLIC_EXIT=" in line and "<<'PY'" in line)


def _poisoned_projector_paths(tmp_path, job_name, module_name, import_origin):
    interpreter = tmp_path / "venv/bin/python"
    interpreter.parent.mkdir(parents=True)
    interpreter.symlink_to(sys.executable)
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    ambient = tmp_path / "ambient"
    ambient.mkdir()
    marker = tmp_path / "untrusted-import-executed"
    poison = candidate if import_origin == "checkout" else ambient
    (poison / f"{module_name}.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n"
        "raise RuntimeError('UNTRUSTED_IMPORT')\n"
    )
    report = candidate / ".specfact/code-review.json" if job_name == "customer" else tmp_path / "review.private.json"
    report.parent.mkdir(exist_ok=True)
    report.write_text("PRIVATE_REPORT invalid JSON")
    return candidate, ambient, marker, report


def _assert_projector_result(result, marker, review_exit):
    assert not marker.exists(), "Candidate or ambient standard-library lookalikes executed on the host"
    assert result.returncode == review_exit and result.stderr == ""
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    assert rows[-1] == {"status": "INCOMPLETE", "phase": "review", "diagnostic": "review_report_unreadable"}
    assert (review_exit != 124) or rows[0]["diagnostic"] == "analysis_timeout"


def _assert_projector_private_state(result, report):
    assert "PRIVATE_REPORT" not in result.stdout and "UNTRUSTED_IMPORT" not in result.stdout
    assert report.read_text() == "PRIVATE_REPORT invalid JSON"
