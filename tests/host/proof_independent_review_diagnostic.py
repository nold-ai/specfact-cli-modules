"""Required ordinary-host Linux lifecycle proofs for the diagnostic owner."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.support.capsule_review_fixtures import REPO_ROOT, STEP_NAME, _write_preparation_fixture, public_projector


@pytest.mark.skipif(__import__("sys").platform != "linux", reason="Linux subreaper and pidfd proof")
@pytest.mark.parametrize("mode", ["timeout", "exit", "cancel"])
def test_owned_descendants_are_reaped_after_setsid(tmp_path, mode):
    import subprocess
    import sys
    import time

    child = tmp_path / "tree.py"
    child.write_text(
        "import os,time,sys\n"
        "from pathlib import Path\n"
        "pid=os.fork()\n"
        "if pid==0:\n"
        " os.setsid()\n"
        " Path(sys.argv[1]).write_text(str(os.getpid()))\n"
        ' time.sleep(0.4 if sys.argv[2]=="exit" else 120)\n'
        "else:\n"
        ' time.sleep(0.2 if sys.argv[2]=="exit" else 120)\n'
    )
    driver = tmp_path / "driver.py"
    driver.write_text(
        "import ctypes,os,sys,signal,json\nfrom pathlib import Path\n"
        "from scripts.independent_review_diagnostic import VerifiedContext,InstalledSymbols,_owned_run,_cancel\n"
        "assert ctypes.CDLL(None).prctl(36,1,0,0,0)==0\n"
        "signal.signal(signal.SIGTERM,_cancel)\n"
        "root=Path(sys.argv[1]);c=VerifiedContext(root,root,root,InstalledSymbols({}),dict(os.environ))\n"
        "try:\n"
        ' result=_owned_run(c,[sys.executable,str(root/"tree.py"),str(root/"child.pid"),sys.argv[2]],1)\n'
        " print(json.dumps(result))\n"
        'except InterruptedError:\n print("cancelled")\n'
    )
    environment = dict(__import__("os").environ, PYTHONPATH=str(Path(__file__).resolve().parents[2]))
    process = subprocess.Popen(
        [sys.executable, str(driver), str(tmp_path), mode],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + 10
    while not (tmp_path / "child.pid").exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert (tmp_path / "child.pid").exists()
    if mode == "cancel":
        process.terminate()
    stdout, stderr = process.communicate(timeout=12)
    assert process.returncode == 0, stderr
    pid = int((tmp_path / "child.pid").read_text())
    assert not Path(f"/proc/{pid}").exists()
    if mode == "cancel":
        assert stdout.strip() == "cancelled"
    else:
        code, owned, cleaned = json.loads(stdout)
        assert code == (124 if mode == "timeout" else 0)
        assert owned >= 2
        assert cleaned is True


@pytest.mark.skipif(__import__("sys").platform != "linux", reason="Linux owned sampler ancestor proof")
def test_sampler_exit_preserves_owned_target_until_it_finishes(tmp_path):
    import subprocess
    import sys

    profiler = tmp_path / "profiler"
    profiler.write_text(
        f"#!{sys.executable}\nimport os,sys,time\nfrom pathlib import Path\n"
        'pid=int(sys.argv[sys.argv.index("--pid")+1])\n'
        'parent=int(Path(f"/proc/{pid}/stat").read_text().rsplit(")",1)[1].split()[1])\n'
        "assert parent==os.getpid()\ntime.sleep(0.1)\n"
    )
    profiler.chmod(0o700)
    target = tmp_path / "target.py"
    target.write_text("import time,sys\nfrom pathlib import Path\ntime.sleep(0.6)\nPath(sys.argv[1]).touch()\n")
    program = (
        "import ctypes,os,sys,json\nfrom pathlib import Path\n"
        "from scripts.independent_review_diagnostic import VerifiedContext,InstalledSymbols,_owned_run,SAMPLER_BOOTSTRAP\n"
        "assert ctypes.CDLL(None).prctl(36,1,0,0,0)==0\n"
        f"root=Path({str(tmp_path)!r});c=VerifiedContext(root,root,root,InstalledSymbols({{}}),dict(os.environ))\n"
        'cmd=[sys.executable,"-I","-c",SAMPLER_BOOTSTRAP,str(root/"profiler"),str(root/"profile"),"1",'
        'sys.executable,str(root/"target.py"),str(root/"completed")]\n'
        "print(json.dumps(_owned_run(c,cmd,2)))\n"
    )
    result = subprocess.run([sys.executable, "-c", program], check=True, capture_output=True, text=True)
    assert json.loads(result.stdout) == [0, 2, True]
    assert (tmp_path / "completed").is_file()


@pytest.mark.skipif(__import__("sys").platform != "linux", reason="Linux provisioning cancellation proof")
def test_provisioning_cancellation_reaps_setsid_grandchild(tmp_path):
    import subprocess
    import sys
    import time

    child = tmp_path / "provision.py"
    child.write_text(
        "import os,time,sys\nfrom pathlib import Path\n"
        "if os.fork()==0:\n os.setsid()\n Path(sys.argv[1]).write_text(str(os.getpid()))\n"
        "time.sleep(120)\n"
    )
    program = (
        "import ctypes,os,sys,signal\nfrom pathlib import Path\n"
        "from scripts.independent_review_diagnostic import VerifiedContext,InstalledSymbols,_checked_output,_cancel\n"
        "assert ctypes.CDLL(None).prctl(36,1,0,0,0)==0\nsignal.signal(signal.SIGTERM,_cancel)\n"
        f"root=Path({str(tmp_path)!r});c=VerifiedContext(root,root,root,InstalledSymbols({{}}),dict(os.environ))\n"
        'try:\n _checked_output(c,[sys.executable,str(root/"provision.py"),str(root/"child.pid")],30)\n'
        'except InterruptedError:\n print("cancelled")\n'
    )
    process = subprocess.Popen(
        [sys.executable, "-c", program], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    deadline = time.monotonic() + 10
    while not (tmp_path / "child.pid").exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert (tmp_path / "child.pid").is_file()
    process.terminate()
    stdout, stderr = process.communicate(timeout=10)
    assert process.returncode == 0, stderr
    assert stdout.strip() == "cancelled"
    assert not Path("/proc", (tmp_path / "child.pid").read_text()).exists()


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize("review_exit", [17, 124])
def test_projector_crash_preserves_original_review_exit(tmp_path: Path, job_name, review_exit):
    import shlex

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
        f"set -e\nreview_exit={review_exit}\nREVIEW_PUBLIC_EXIT=$review_exit {shlex.quote(sys.executable)} - <<'PY'{guard}\n"
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
    import shlex

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
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    name = STEP_NAME if job_name == "customer" else "Prepare and review through the authenticated installed controller"
    recipe = next(step["run"] for step in workflow["jobs"][job_name]["steps"] if step.get("name") == name)
    invocation = next(line for line in recipe.splitlines() if "REVIEW_PUBLIC_EXIT=" in line and "<<'PY'" in line)
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
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\nraise RuntimeError('UNTRUSTED_IMPORT')\n"
    )
    report = candidate / ".specfact/code-review.json" if job_name == "customer" else tmp_path / "review.private.json"
    report.parent.mkdir(exist_ok=True)
    report.write_text("PRIVATE_REPORT invalid JSON")
    shell = f"set -e\ntrusted_env=(env)\nreview_exit={review_exit}\n" + invocation + "\n" + public_projector(job_name)
    shell += '\nPY\nexit "$review_exit"\n'
    environment = dict(os.environ, CUSTOMER_ROOT=str(tmp_path), TRUSTED_ROOT=str(tmp_path), PYTHONPATH=str(ambient))
    environment["REVIEW_PUBLIC_REPORT"] = str(report)
    result = subprocess.run(
        ["bash", "-c", shell], cwd=candidate, env=environment, capture_output=True, text=True, check=False
    )
    assert not marker.exists(), "Candidate or ambient standard-library lookalikes executed on the host"
    assert result.returncode == review_exit and result.stderr == ""
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    assert rows[-1] == {"status": "INCOMPLETE", "phase": "review", "diagnostic": "review_report_unreadable"}
    assert (review_exit != 124) or rows[0]["diagnostic"] == "analysis_timeout"
    assert "PRIVATE_REPORT" not in result.stdout and "UNTRUSTED_IMPORT" not in result.stdout
    assert report.read_text() == "PRIVATE_REPORT invalid JSON"


def _write_preparation_interpreter(tmp_path):
    import sys

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


@pytest.fixture
def preparation_shell(tmp_path, monkeypatch):
    import subprocess

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
    import json

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


@pytest.mark.parametrize("prior_stage, expected_exit, report_expected", [(1.2, 0, True), (7, 124, False)])
def test_required_parent_preserves_leaf_budget_and_expiry(tmp_path, prior_stage, expected_exit, report_expected):
    import ast

    steps = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())["jobs"][
        "independent-review"
    ]["steps"]
    review = next(item for item in steps if item.get("id") == "independent_review")
    source = "import subprocess,sys\n" + review["run"].split("'import subprocess,sys\n", 1)[1].split("' \\\n", 1)[0]
    tree = ast.parse(source)
    deadlines = [node for node in ast.walk(tree) if isinstance(node, ast.keyword) and node.arg == "timeout"]
    assert len(deadlines) == 1
    deadline = deadlines[0].value
    assert isinstance(deadline, ast.Constant)
    value = deadline.value
    assert isinstance(value, int)
    deadline.value = value / 100
    program = ast.unparse(tree)
    report = tmp_path / "report.json"
    child = (
        "import subprocess,sys,time;from pathlib import Path;"
        f"time.sleep({prior_stage});"
        "subprocess.run([sys.executable,'-c','import time;time.sleep(2.2)'],timeout=3,check=True);"
        "Path(sys.argv[1]).write_text('complete')"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", program, sys.executable, "-I", "-c", child, str(report)],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == expected_exit
    assert report.exists() is report_expected
