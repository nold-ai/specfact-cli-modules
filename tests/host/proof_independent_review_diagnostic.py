"""Required ordinary-host Linux lifecycle proofs for the diagnostic owner."""

import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.support.capsule_review_fixtures import (
    REPO_ROOT,
    STEP_NAME,
    _capture_program,
    _git,
    _write_preparation_fixture,
    _write_public_report,
    public_projector,
)


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
    from tests.unit.test_independent_diagnostic_controller import capture_functions

    captured = capture_functions()["capture_original"](
        report,
        tmp_path / "original-private",
        {"role": "candidate" if job_name == "customer" else "independent", "head": "a" * 40, "attempt": "1"},
        review_exit,
    )
    assert captured["status"] == "COMPLETE"
    shell = (
        f"set -e\ntrusted_env=(env)\nreview_exit={review_exit}\n"
        f"original_capture_admitted={str(captured['status'] == 'COMPLETE').lower()}\n"
        + invocation
        + "\n"
        + public_projector(job_name)
    )
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


def test_private_observer_descriptor_is_not_inherited_even_without_close_fds(tmp_path):
    from types import ModuleType

    from tests.unit.test_independent_member_observation import controller_definitions

    module = ModuleType("inert")
    module._prepare_capsule_runtime = lambda: None
    ns = controller_definitions()
    private = tmp_path / "observation-private"
    private.mkdir(mode=0o700)
    observer = ns["HostObservation"](
        module, {"_prepare_capsule_runtime": module._prepare_capsule_runtime}, private / "receipt", {}
    )
    try:
        assert not os.get_inheritable(observer.descriptor)
        assert (private / "receipt").stat().st_mode & 0o777 == 0o600
        program = "import os,sys\ntry: os.fstat(int(sys.argv[1]))\nexcept OSError: sys.exit(0)\nelse: sys.exit(1)"
        result = subprocess.run(
            [sys.executable, "-I", "-c", program, str(observer.descriptor)], close_fds=False, timeout=10, check=False
        )
        assert result.returncode == 0
    finally:
        observer.finish()


@pytest.mark.parametrize("conflict", [False, True])
def test_actual_request_mount_sources_exclude_private_receipt(tmp_path, monkeypatch, conflict):
    from types import ModuleType, SimpleNamespace

    from tests.unit.test_independent_member_observation import controller_definitions

    trusted = tmp_path / "trusted"
    trusted.mkdir()
    private = trusted / "observation-private"
    private.mkdir(mode=0o700)
    for name in ("tmp", "cache", "subject", "config", "project-runtime"):
        (trusted / name).mkdir()
    monkeypatch.setenv("TMPDIR", str(trusted / "tmp"))
    request = SimpleNamespace(
        member="pylint",
        snapshot_root=trusted / "subject",
        runtime=SimpleNamespace(root=trusted / "cache"),
        config_roots=(trusted if conflict else trusted / "config",),
        project_runtime_root=trusted / "project-runtime",
    )
    calls = []
    module = ModuleType("inert")

    def producer(value):
        calls.append(value)
        return "same"

    module._execute_capsule_member = producer
    ns = controller_definitions()
    observer = ns["HostObservation"](module, {"_execute_capsule_member": producer}, private / "receipt", {})
    observer.install()
    assert module._execute_capsule_member(request) == "same"
    observer.finish()
    assert calls == [request]
    assert observer.lost is conflict
    assert (private / "receipt").exists() is not conflict


def test_authenticated_old_mount_constructors_exclude_receipt_ancestors(tmp_path):
    """Authenticate archive data, then exercise only equal inert current constructors."""
    import ast
    import hashlib
    import tarfile
    from dataclasses import dataclass
    from types import SimpleNamespace

    from specfact_cli.registry.crypto_validator import verify_signature
    from specfact_cli.registry.module_installer import _bundled_public_key_path, _module_artifact_payload_stable

    archive_path = REPO_ROOT / "registry/modules/specfact-code-review-0.51.2.tar.gz"
    package = tmp_path / "archive-data"
    package.mkdir()
    with tarfile.open(archive_path) as archive:
        members = archive.getmembers()
        assert len(members) <= 2048 and sum(member.size for member in members) <= 32 * 1024 * 1024
        for member in members:
            assert member.isfile()
            relative = Path(member.name).relative_to("specfact-code-review")
            assert ".." not in relative.parts and not relative.is_absolute()
            target = package / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            stream = archive.extractfile(member)
            assert stream is not None
            with stream:
                target.write_bytes(stream.read(member.size + 1))
    metadata = yaml.safe_load((package / "module-package.yaml").read_bytes())
    payload = _module_artifact_payload_stable(package)
    assert metadata["version"] == "0.51.2"
    assert hashlib.sha256(payload).hexdigest() == "d4bcfd8db105c60440b3bdefbe414f1dc148a75c21b8533801d43d888b3d0df4"
    key = _bundled_public_key_path().read_bytes()
    assert hashlib.sha256(key).hexdigest() == "4e54ffb02307e1a85c166c40aba6d1bc40fbb9a8ef40bf756f8870e5bb08d1c8"
    assert verify_signature(payload, metadata["integrity"]["signature"], key.decode())
    old = ast.parse((package / "src/specfact_code_review/run/sandbox.py").read_bytes())
    current = ast.parse(
        (REPO_ROOT / "packages/specfact-code-review/src/specfact_code_review/run/sandbox.py").read_bytes()
    )
    names = {"_mounts", "_bubblewrap_command"}
    old_functions = {node.name: node for node in old.body if isinstance(node, ast.FunctionDef) and node.name in names}
    current_functions = {
        node.name: node for node in current.body if isinstance(node, ast.FunctionDef) and node.name in names
    }
    for name in names:
        assert ast.dump(old_functions[name]) == ast.dump(current_functions[name])
        assert not current_functions[name].decorator_list
    mount_type = next(node for node in current.body if isinstance(node, ast.ClassDef) and node.name == "SandboxMount")
    namespace = {
        "Path": Path,
        "dataclass": dataclass,
        "SnapshotInvocationContext": SimpleNamespace,
        "SandboxLaunchPlan": SimpleNamespace,
        "_PROJECT_RUNTIME_MEMBERS": frozenset({"pylint"}),
    }
    exec(
        compile(
            ast.Module(body=[mount_type, *current_functions.values()], type_ignores=[]),
            "inert-current-mount-constructors",
            "exec",
        ),
        namespace,
    )
    trusted = tmp_path / "trusted"
    private = trusted / "observation-private"
    private.mkdir(parents=True, mode=0o700)
    for member in ("pylint", "radon"):
        control = trusted / "tmp/control"
        control.mkdir(parents=True, exist_ok=True)
        context = SimpleNamespace(
            member=member,
            config_roots=(trusted / "tmp/request", trusted / "subject/config"),
            output_root=trusted / "tmp/output",
            temporary_root=trusted / "tmp/scratch",
            snapshot_root=trusted / "subject",
            control_root=control,
            project_runtime_root=trusted / "home/project-runtime",
        )
        mounts = namespace["_mounts"](context)
        plan = SimpleNamespace(startup_sys_path=(trusted / "cache/capsule",), mounts=mounts, cwd="/", argv=("inert",))
        command = namespace["_bubblewrap_command"](9, plan, extra_argv=())
        sources = [Path(command[index + 1]) for index, value in enumerate(command) if value in ("--bind", "--ro-bind")]
        assert sources == [trusted / "cache/capsule", *(mount.source for mount in mounts)]
        assert sources and all(
            not private.is_relative_to(source) and not source.is_relative_to(private) for source in sources
        )
        assert "--unshare-all" in command and "--clearenv" in command
        assert str(private) not in command


def test_inert_observation_timing_is_measured_without_neutrality_claim(tmp_path):
    from time import perf_counter_ns
    from types import ModuleType

    from tests.unit.test_independent_member_observation import controller_definitions

    module = ModuleType("inert")
    argument = object()

    def producer(value):
        return value

    module._prepare_capsule_runtime = producer
    start = perf_counter_ns()
    for _ in range(63):
        assert producer(argument) is argument
    stock_ns = perf_counter_ns() - start
    observer = controller_definitions()["HostObservation"](
        module, {"_prepare_capsule_runtime": producer}, tmp_path / "receipt", {}
    )
    observer.install()
    start = perf_counter_ns()
    for _ in range(63):
        assert module._prepare_capsule_runtime(argument) is argument
    observed_ns = perf_counter_ns() - start
    observer.finish()
    assert not observer.lost
    print(
        json.dumps(
            {
                "controlled_calls": 63,
                "stock_elapsed_ns": stock_ns,
                "observed_elapsed_ns": observed_ns,
                "includes_authentication_or_compilation": False,
                "timing_neutrality_claim": False,
            }
        )
    )


def _local_invocation_context(tmp_path, environment, case):
    """Use real inert Git objects; never borrow the caller's event or repository."""
    import shutil

    for key in list(environment):
        if key.startswith(("GITHUB_", "GIT_")) or key == "CANDIDATE_HEAD":
            environment.pop(key)
    if case == "absent":
        return None
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    relative = ".github/workflows/capsule-customer-execution.yml"
    workflow = checkout / relative
    workflow.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / relative, workflow)

    def git(*args):
        return subprocess.check_output(
            ["git", "-C", str(checkout), *args], env=environment, text=True, stderr=subprocess.PIPE
        ).strip()

    git("init", "-q")
    git("add", ".")
    git(
        "-c",
        "user.name=Inert proof",
        "-c",
        "user.email=proof@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-qm",
        "inert workflow",
    )
    head = git("rev-parse", "HEAD")
    environment.update(GITHUB_WORKSPACE=str(checkout), CANDIDATE_HEAD=head, GITHUB_RUN_ID="123", GITHUB_RUN_ATTEMPT="2")
    invalid = {
        "missing_head": ("CANDIDATE_HEAD", None),
        "bad_head": ("CANDIDATE_HEAD", "A" * 40),
        "missing_run": ("GITHUB_RUN_ID", None),
        "missing_attempt": ("GITHUB_RUN_ATTEMPT", None),
        "zero_run": ("GITHUB_RUN_ID", "0"),
        "bad_attempt": ("GITHUB_RUN_ATTEMPT", "1:2"),
        "long_attempt": ("GITHUB_RUN_ATTEMPT", "1" * 128),
        "missing_checkout": ("GITHUB_WORKSPACE", str(tmp_path / "missing")),
        "missing_commit": ("CANDIDATE_HEAD", "0" * 40),
    }
    if case in invalid:
        key, value = invalid[case]
        if value is None:
            environment.pop(key)
        else:
            environment[key] = value
    if case == "mismatch":
        workflow.write_text(workflow.read_text() + "\n# changed checkout\n")
    if case == "missing_blob":
        git("rm", relative)
        git(
            "-c",
            "user.name=Inert proof",
            "-c",
            "user.email=proof@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "remove workflow",
        )
        environment["CANDIDATE_HEAD"] = git("rev-parse", "HEAD")
        workflow.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / relative, workflow)
    return head


@pytest.mark.parametrize("review_exit", [0, 2, 7])
@pytest.mark.parametrize(
    "case",
    [
        "absent",
        "missing_head",
        "bad_head",
        "missing_run",
        "missing_attempt",
        "zero_run",
        "bad_attempt",
        "long_attempt",
        "missing_checkout",
        "missing_commit",
        "missing_blob",
        "mismatch",
        "mkdir_failure",
        "write_failure",
        "hash_failure",
        "valid",
    ],
)
def test_optional_context_preserves_required_review(tmp_path, case, review_exit):
    import hashlib

    from tests.support.capsule_review_fixtures import (
        assert_installed_review_arguments,
        create_isolated_reviewer,
        independent_review_job,
    )

    trusted, environment = create_isolated_reviewer(tmp_path, (review_exit, "NOT_APPLICABLE", "no_governed_impact"))
    head = _local_invocation_context(tmp_path, environment, case)
    environment["GITHUB_OUTPUT"] = str(tmp_path / "capture-output")
    environment["REVIEW_CAPTURE_ADMITTED"] = "true"
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    bootstrap = next(
        step["run"] for step in workflow["jobs"]["customer"]["steps"] if "PY_CAPTURE" in step.get("run", "")
    )
    capture = bootstrap.split("<<'PY_CAPTURE'", 1)[1].split("\n", 1)[1].split("\nPY_CAPTURE", 1)[0]
    (trusted / "capture-original.py").write_text(capture)
    (trusted / "review.private.json").write_text('{"findings": []}')
    prefix = ""
    if case == "mkdir_failure":
        (trusted / "observation-private").mkdir(mode=0o700)
    elif case == "write_failure":
        prefix = (
            'mkdir() { command mkdir "$@" && command mkdir "$TRUSTED_ROOT/observation-private/invocation.json"; }\n'
        )
    elif case == "hash_failure":
        prefix = 'git() { if [ "$1" = hash-object ]; then return 1; else command git "$@"; fi; }\n'
    step = next(item for item in independent_review_job()["steps"] if item.get("id") == "independent_review")
    result = subprocess.run(
        ["bash", "-x", "-c", prefix + step["run"]],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == review_exit, result.stdout + result.stderr
    assert (tmp_path / "capture-output").read_text() == f"original_capture_admitted={str(case == 'valid').lower()}\n"
    assert_installed_review_arguments(trusted, prepared=False)
    calls = [line for line in result.stderr.splitlines() if line.startswith("+ env -i ")]
    assert sum(" prepare-index " in line for line in calls) == 1
    assert sum(" code review run " in line for line in calls) == 1
    binding_path = trusted / "observation-private/invocation.json"
    manifest = trusted / "original-private/manifest.json"
    if case == "valid":
        binding = json.loads(binding_path.read_text())
        assert binding["head"] == head
        assert binding["attempt"] == "123:2"
        assert binding["controller_sha256"] == hashlib.sha256((trusted / "reviewer.py").read_bytes()).hexdigest()
        expected_blob = subprocess.check_output(
            [
                "git",
                "-C",
                environment["GITHUB_WORKSPACE"],
                "rev-parse",
                f"{head}:.github/workflows/capsule-customer-execution.yml",
            ],
            text=True,
        ).strip()
        assert binding["workflow_blob"] == expected_blob
        assert binding_path.stat().st_mode & 0o777 == 0o600
        assert binding_path.parent.stat().st_mode & 0o777 == 0o700
        assert json.loads(manifest.read_text())["status"] == "COMPLETE"
    else:
        assert not binding_path.is_file()
        assert not manifest.exists()
        assert not (trusted / "original-private/original.json").exists()
        assert not (trusted / "observation-private/receipt.jsonl").exists()


@pytest.mark.parametrize("failure", ["write", "close", "controller_read"])
def test_binding_failure_after_publication_leaves_no_usable_manifest(tmp_path, failure):
    """Run the emitted optional shell with failure in the actual manifest writer."""
    from tests.support.capsule_review_fixtures import independent_review_job

    trusted = tmp_path / "trusted"
    (trusted / "venv/bin").mkdir(parents=True)
    (trusted / "reviewer.py").write_text("# inert controller bytes\n")
    environment = dict(os.environ, TRUSTED_ROOT=str(trusted), BINDING_FAILURE=failure)
    _local_invocation_context(tmp_path, environment, "valid")
    interpreter = trusted / "venv/bin/python"
    interpreter.write_text(
        f"#!{sys.executable}\n"
        "import os,sys\nfrom pathlib import Path\n"
        "source=sys.stdin.read(); sys.argv=sys.argv[2:]\n"
        "original_fdopen=os.fdopen\n"
        "class FailedStream:\n"
        " def __init__(self, descriptor, mode): self.stream=original_fdopen(descriptor,mode)\n"
        " def __enter__(self): return self\n"
        " def write(self, text):\n"
        "  result=self.stream.write(text)\n"
        "  if os.environ['BINDING_FAILURE']=='write' and text=='}':\n"
        "   self.stream.flush(); raise OSError('inert final write failure')\n"
        "  return result\n"
        " def __exit__(self, *args):\n"
        "  self.stream.close()\n"
        "  if os.environ['BINDING_FAILURE']=='close': raise OSError('inert close failure')\n"
        "os.fdopen=FailedStream\n"
        "if os.environ['BINDING_FAILURE']=='controller_read':\n"
        " def failed_read(self): raise OSError('inert controller read failure')\n"
        " Path.read_bytes=failed_read\n"
        "exec(compile(source,'actual-binding-writer','exec'))\n"
    )
    interpreter.chmod(0o700)
    recipe = next(item["run"] for item in independent_review_job()["steps"] if item.get("id") == "independent_review")
    start = "observation_ready=false" if "observation_ready=false" in recipe else "if mkdir -m 0700"
    optional = recipe[recipe.index(start) : recipe.index("trusted_env=(env -i")]
    result = subprocess.run(
        ["bash", "-c", "set -euo pipefail\n" + optional + '\nprintf "%s\\n" "${observation_ready:-false}"'],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "false"
    assert not (trusted / "observation-private/invocation.json").exists()


@pytest.mark.parametrize("review_exit", [17, 124])
@pytest.mark.parametrize("case", ["valid", "absent", "mismatch"])
def test_capture_output_preserves_failed_required_call(tmp_path, case, review_exit):
    test_optional_context_preserves_required_review(tmp_path, case, review_exit)


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize("damage", ["missing", "partial", "digest", "duplicate"])
def test_uncommitted_original_bytes_are_never_projected(tmp_path, job_name, damage):
    import hashlib

    _write_public_report(tmp_path, [])
    private = tmp_path / "original-private"
    private.mkdir(mode=0o700)
    report = private / "original.json"
    raw = json.dumps({"findings": [{"file": "public.py", "line": 1, "severity": "error"}]}).encode()
    report.write_bytes(raw)
    manifest = {
        "status": "COMPLETE",
        "binding": {"role": "candidate", "head": "a" * 40, "attempt": "1"},
        "required_exit": 1,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }
    if damage == "partial":
        manifest["status"] = "UNAVAILABLE"
    elif damage == "digest":
        manifest["sha256"] = "0" * 64
    if damage != "missing":
        text = json.dumps(manifest)
        if damage == "duplicate":
            text = text.replace('"status": "COMPLETE"', '"status": "UNAVAILABLE", "status": "COMPLETE"')
        (private / "manifest.json").write_text(text)
    result = subprocess.run(
        [sys.executable, "-I", "-c", public_projector(job_name)],
        cwd=tmp_path,
        env=dict(os.environ, REVIEW_PUBLIC_REPORT=str(report), REVIEW_PUBLIC_EXIT="1", REVIEW_CAPTURE_ADMITTED="true"),
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0
    assert "finding_location" not in result.stdout
    assert json.loads(result.stdout)["diagnostic"] == "original_capture_unavailable"


def _original_reader(reader):
    if reader in ("customer", "independent-review"):
        return public_projector(reader)
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    candidate = reader == "candidate-failure"
    job = "customer" if candidate else "independent-review"
    marker = "PY_CANDIDATE_FAILURE" if candidate else "PY_REVIEW_FAILURE"
    recipe = next(s["run"] for s in workflow["jobs"][job]["steps"] if f"<<'{marker}'" in s.get("run", ""))
    return recipe.split(f"<<'{marker}'", 1)[1].split("\n", 1)[1].split(f"\n{marker}", 1)[0]


def _successful_original_capture(tmp_path, reader):
    writer = tmp_path / "capture.py"
    writer.write_text(_capture_program())
    raw = json.dumps(
        {
            "findings": [],
            "analyzer_evidence": [{"id": "pylint", "diagnostic": "timeout"}],
            "assurance_status": "PASS",
            "overall_verdict": "PASS",
        }
    ).encode()
    source = tmp_path / "source.json"
    source.write_bytes(raw)
    role = "candidate" if reader in ("customer", "candidate-failure") else "independent"
    args = [sys.executable, "-I", str(writer), str(tmp_path), str(source), role, "a" * 40, "123:2", "17"]
    first = subprocess.run(args, capture_output=True, timeout=5, check=False)
    assert first.returncode == 0
    report = tmp_path / "original-private/original.json"
    return args, raw, report


@pytest.mark.parametrize("reader", ["customer", "independent-review", "candidate-failure", "independent-failure"])
@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "role",
        "head",
        "attempt",
        "exit",
        "permissions",
        "skipped",
        "command-failure",
        "publication-failure",
        "missing",
        "false",
        "unexpected",
        "digest",
        "duplicate",
    ],
)
def test_original_readers_require_actual_owner_success(tmp_path, monkeypatch, capsys, reader, case):
    args, raw, report = _successful_original_capture(tmp_path, reader)
    manifest = report.parent / "manifest.json"
    if case == "role":
        args[-4] = "independent" if args[-4] == "candidate" else "candidate"
    elif case == "head":
        args[-3] = "b" * 40
    elif case == "attempt":
        args[-2] = "123:3"
    elif case == "exit":
        args[-1] = "124"
    if case == "permissions":
        report.parent.chmod(0o755)
    if case == "publication-failure":
        (tmp_path / "original-report.public.json").unlink()
        (tmp_path / "original-report.public.json").mkdir()
    before = (report.read_bytes(), manifest.read_bytes())
    if case in {"skipped", "missing", "false", "unexpected"}:
        admission = {"skipped": "false", "missing": None, "false": "false", "unexpected": "TRUE"}[case]
    else:
        if case == "command-failure":
            args[2] = str(tmp_path / "absent-writer.py")
        outcome = subprocess.run(args, capture_output=True, timeout=5, check=False)
        admission = "true" if outcome.returncode == 0 else "false"
    assert (report.read_bytes(), manifest.read_bytes()) == before
    if case == "digest":
        manifest.write_text(manifest.read_text().replace('"sha256": "', '"sha256": "0'))
    elif case == "duplicate":
        manifest.write_text(manifest.read_text().replace('"status":', '"status": "COMPLETE", "status":'))
    if admission is None:
        monkeypatch.delenv("REVIEW_CAPTURE_ADMITTED", raising=False)
    else:
        monkeypatch.setenv("REVIEW_CAPTURE_ADMITTED", admission)
    monkeypatch.setenv("REVIEW_PUBLIC_REPORT", str(report))
    monkeypatch.setenv("REVIEW_REPORT", str(report))
    monkeypatch.setenv("REVIEW_PUBLIC_EXIT", "17")
    monkeypatch.setenv("REVIEW_LOG", str(tmp_path / "missing.log"))
    monkeypatch.chdir(tmp_path)
    _git(tmp_path, "init", "-q")
    program = tmp_path / "reader.py"
    program.write_text(_original_reader(reader))
    opened, parsed = [], []
    original_open, original_loads = Path.open, json.loads

    def observed_open(path, *args, **kwargs):
        if path in (report, manifest):
            opened.append(path)
        return original_open(path, *args, **kwargs)

    def observed_loads(value, *args, **kwargs):
        if value == raw:
            parsed.append(value)
        return original_loads(value, *args, **kwargs)

    monkeypatch.setattr(Path, "open", observed_open)
    monkeypatch.setattr(json, "loads", observed_loads)
    runpy.run_path(str(program))
    output = capsys.readouterr().out
    if admission != "true":
        assert not opened, "Rejected or skipped owner must prevent manifest and raw opens"
    assert len(parsed) == (1 if case == "valid" else 0)
    if case != "valid":
        assert '"PASS"' not in output and '"analyzer": "pylint"' not in output


@pytest.mark.parametrize("role", ["candidate", "independent"])
@pytest.mark.parametrize("review_exit", [17, 124])
@pytest.mark.parametrize("case", ["valid", "stale", "missing", "skipped", "command-failure"])
def test_capture_shell_transports_owner_result_before_required_exit(tmp_path, role, review_exit, case):
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    job = "customer" if role == "candidate" else "independent-review"
    step = next(
        s
        for s in workflow["jobs"][job]["steps"]
        if s.get("id") == ("deferred_review" if role == "candidate" else "independent_review")
    )
    recipe = step["run"]
    start = (
        recipe.index("original_capture_admitted=false")
        if "original_capture_admitted=false" in recipe
        else recipe.index('"$CUSTOMER_ROOT/venv/bin/python" -I "$CUSTOMER_ROOT/capture-original.py"')
        if role == "candidate"
        else recipe.index('if [ "$observation_ready" = true ]; then')
    )
    root = tmp_path / "root"
    (root / "venv/bin").mkdir(parents=True)
    (root / "venv/bin/python").symlink_to(sys.executable)
    (root / "subject").mkdir()
    _git(root / "subject", "init", "-q")
    (root / "capture-original.py").write_text(_capture_program())
    review = root / "subject"
    (review / ".specfact").mkdir()
    source = review / ".specfact/code-review.json" if role == "candidate" else root / "review.private.json"
    source.write_text('{"findings":[],"analyzer_evidence":[]}')
    if case == "stale":
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                str(root / "capture-original.py"),
                str(root),
                str(source),
                role,
                "b" * 40,
                "123:2",
                str(review_exit),
            ],
            capture_output=True,
            timeout=5,
            check=False,
        )
        assert result.returncode == 0
    if case == "missing":
        source.unlink()
    if case == "command-failure":
        (root / "capture-original.py").unlink()
    output = tmp_path / "outputs"
    env = dict(
        os.environ,
        CUSTOMER_ROOT=str(root),
        TRUSTED_ROOT=str(root),
        REVIEW_ROOT=str(review),
        CANDIDATE_HEAD="a" * 40,
        GITHUB_RUN_ID="123",
        GITHUB_RUN_ATTEMPT="2",
        GITHUB_OUTPUT=str(output),
        REVIEW_CAPTURE_ADMITTED="true",
    )
    prefix = (
        f"set -euo pipefail\nreview_exit={review_exit}\nobservation_head={'a' * 40}\n"
        f"observation_attempt=123:2\nobservation_ready={'false' if case == 'skipped' else 'true'}\n"
        'trusted_env=(env -i PATH="$PATH")\n'
    )
    result = subprocess.run(
        ["bash", "-c", prefix + recipe[start:]],
        cwd=review,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == review_exit, result.stderr
    admitted = case == "valid" or (role == "candidate" and case == "skipped")
    assert output.read_text() == f"original_capture_admitted={str(admitted).lower()}\n"
    if not admitted:
        assert "original_capture_unavailable" in result.stdout
    if review_exit == 124:
        assert "analysis_timeout" in result.stdout
    if role == "independent":
        (root / "review-attempted").touch()
        later = next(
            s for s in workflow["jobs"][job]["steps"] if s.get("name") == "Project independent review failure privately"
        )
        later_env = {**env, "REVIEW_CAPTURE_ADMITTED": output.read_text().strip().split("=", 1)[1]}
        projected = subprocess.run(
            ["bash", "-c", later["run"]], env=later_env, capture_output=True, text=True, timeout=5, check=False
        )
        assert projected.returncode == 0, projected.stderr
        assert json.loads(projected.stdout)["report_outcome"] == (
            "structured_report" if admitted else "unreadable_report"
        )


@pytest.mark.parametrize("admission", [None, "", "false", "TRUE"])
def test_replay_rejects_absent_capture_before_any_manifest_read(tmp_path, admission):
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    recipe = next(
        s["run"]
        for s in workflow["jobs"]["customer"]["steps"]
        if s.get("name") == "Profile failed candidate review privately"
    )
    guard = '[ "${REVIEW_CAPTURE_ADMITTED:-false}" = true ] || exit 0'
    assert guard in recipe
    prefix = recipe[recipe.index(guard) : recipe.index("# Separate pinned profiler")]
    env = {**os.environ, "CUSTOMER_ROOT": str(tmp_path), "REVIEW_ROOT": str(tmp_path)}
    env.pop("REVIEW_CAPTURE_ADMITTED", None)
    if admission is not None:
        env["REVIEW_CAPTURE_ADMITTED"] = admission
    result = subprocess.run(
        ["bash", "-c", "set -euo pipefail\n" + prefix + "exit 91"], env=env, capture_output=True, timeout=5, check=False
    )
    assert result.returncode == 0 and not result.stderr


@pytest.mark.parametrize("merge_failure", [False, True])
def test_linux23_correction_independent_actual_step_environment(tmp_path, merge_failure):
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    recipe = next(
        s["run"]
        for s in workflow["jobs"]["independent-review"]["steps"]
        if s.get("name") == "Prepare and review through the authenticated installed controller"
    )
    prefix = recipe[recipe.index("trusted_env=(") :]
    (tmp_path / "subject").mkdir()
    executable = tmp_path / "venv/bin/python"
    executable.parent.mkdir(parents=True)
    records = tmp_path / "calls.jsonl"
    executable.write_text(
        f"#!{sys.executable}\n"
        + f"""
import json, os, sys
from pathlib import Path
record = {{"argv": sys.argv[1:], "base": os.environ.get("REVIEW_DIAGNOSTIC_BASE"), "head": os.environ.get("REVIEW_DIAGNOSTIC_HEAD")}}
with Path({str(records)!r}).open("a") as stream:
    stream.write(json.dumps(record) + "\\n")
if "-c" in sys.argv:
    code = sys.argv[sys.argv.index("-c") + 1]
    if "merge-base" in code:
        assert sys.argv[-2:] == [{("a" * 40)!r}, {("c" * 40)!r}]
        import subprocess
        def merge_output(argv, **kwargs):
            assert argv == ["git", "merge-base", {("a" * 40)!r}, {("c" * 40)!r}]
            assert kwargs == {{"timeout": 5}}
            if {merge_failure!r}:
                raise subprocess.CalledProcessError(128, argv)
            return {("b" * 40 + chr(10)).encode()!r}
        subprocess.check_output = merge_output
        sys.argv = ["-c", {("a" * 40)!r}, {("c" * 40)!r}]
        exec(compile(code, "actual-merge-base", "exec"))
    elif "timeout=600" in code:
        sys.exit(7)
    elif "timeout=1800" not in code:
        sys.exit(99)
else:
    assert sys.argv[1:] == ["-I", "-"]
    sys.stdin.read()
"""
    )
    executable.chmod(0o700)
    env = {
        **os.environ,
        "TRUSTED_ROOT": str(tmp_path),
        "CANDIDATE_HEAD": "a" * 40,
        "CANDIDATE_BASE": "c" * 40,
        "observation_ready": "false",
    }
    env.pop("REVIEW_BASE", None)
    result = subprocess.run(
        ["bash", "-c", "set -euo pipefail\n" + prefix], env=env, capture_output=True, timeout=5, check=False
    )
    assert result.returncode == 7, result.stderr.decode()
    assert len(result.stdout) <= 65536
    calls = [json.loads(line) for line in records.read_text().splitlines()]
    required = [index for index, call in enumerate(calls) if any("timeout=600" in arg for arg in call["argv"])]
    merge = [index for index, call in enumerate(calls) if any("merge-base" in arg for arg in call["argv"])]
    assert len(required) == len(merge) == 1
    assert required[0] < merge[0]
    assert calls[-1]["argv"] == ["-I", "-"]
    assert calls[-1]["head"] == "a" * 40
    assert calls[-1]["base"] == ("" if merge_failure else "b" * 40)


def _linux30_owner():
    path = REPO_ROOT / "scripts/semgrep_input_diagnostic.py"
    assert path.is_file(), "Dedicated bounded direct parser owner is missing"
    return runpy.run_path(str(path))


def _linux30_native_error():
    return {
        "version": "1.144.0",
        "results": [],
        "paths": {"scanned": ["/opt/specfact/snapshot/first.py"]},
        "errors": [
            {
                "type": "Syntax error",
                "code": 3,
                "message": "RAW_SECRET_CANARY",
                "spans": [
                    {
                        "file": "/opt/specfact/snapshot/second.py",
                        "start": {"line": 2, "col": 1},
                        "end": {"line": 2, "col": 4},
                    }
                ],
            }
        ],
    }


def test_linux30_nonfirst_native_coordinate_and_private_message():
    native = _linux30_native_error()
    result = _linux30_owner()["project_native"](
        json.dumps(native).encode(), {"first.py": b"x=1\n", "second.py": b"x=1\nbad\n"}, {}, "head", "clean"
    )
    assert result["errors"] == [
        {
            "side": "head",
            "member": "clean",
            "category": "syntax_error",
            "code": 3,
            "path": "second.py",
            "role": "source",
            "line": 2,
            "column": 1,
            "end_line": 2,
            "end_column": 4,
        }
    ]
    assert "RAW_SECRET_CANARY" not in json.dumps(result)
    assert result["status"] == "DIAGNOSTIC_COMPLETE"
    assert result["acceptance"] is False


@pytest.mark.parametrize("mutation", ["truncated", "foreign", "unaccounted", "message_only", "boolean", "overspan"])
def test_linux30_projection_rejects_unbound_evidence(mutation):
    owner = _linux30_owner()
    native = _linux30_native_error()
    error = native["errors"][0]
    if mutation == "foreign":
        error["spans"][0]["file"] = "/secret/customer.py"
    elif mutation == "unaccounted":
        native["paths"]["scanned"] = []
    elif mutation == "message_only":
        error.pop("spans")
        error["message"] = "/opt/specfact/snapshot/second.py:2 RAW_SECRET_CANARY"
    elif mutation == "boolean":
        error["spans"][0]["start"]["line"] = True
    elif mutation == "overspan":
        error["spans"][0]["end"]["col"] = 900
    raw = json.dumps(native).encode()
    result = owner["project_native"](
        raw[:-1] if mutation == "truncated" else raw,
        {"first.py": b"x=1\n", "second.py": b"x=1\nbad\n"},
        {},
        "base",
        "bugs",
    )
    assert result["status"] == "INCOMPLETE"
    assert "RAW_SECRET_CANARY" not in json.dumps(result)
    assert "/secret" not in json.dumps(result)


@pytest.mark.parametrize(
    "field,value",
    [
        ("ref", "refs/heads/codex/native-pylint-execution-budget"),
        ("before", "1" * 40),
        ("after", "2" * 40),
        ("created", False),
        ("deleted", True),
        ("attempt", "2"),
        ("parents", []),
    ],
)
def test_linux30_admission_rejects_before_setup(field, value):
    owner = _linux30_owner()
    event = {
        "ref": "refs/heads/codex/pr510-semgrep-once-25",
        "before": "0" * 40,
        "after": "a" * 40,
        "created": True,
        "deleted": False,
    }
    attempt, parents = "1", [owner["SUBJECT_HEAD"]]
    if field == "attempt":
        attempt = value
    elif field == "parents":
        parents = value
    else:
        event[field] = value
    with pytest.raises(ValueError, match="admission"):
        owner["admit"](event, "a" * 40, attempt, parents)


@pytest.mark.parametrize(
    "program,expected",
    [
        ("import os\nwhile True: os.write(1,b'x'*4096)", "output_limit"),
        ("import os\nwhile True: os.write(2,b'x'*4096)", "output_limit"),
        ("import time; time.sleep(60)", "deadline"),
        ("import os,time\nif os.fork()==0: os.setsid(); time.sleep(60)", "deadline"),
    ],
)
@pytest.mark.skipif(sys.platform != "linux", reason="Linux owned-tree and subreaper proof")
def test_linux30_bounded_capture_lifecycle(tmp_path, program, expected):
    owner = _linux30_owner()
    result = owner["capture"](
        [sys.executable, "-c", program], tmp_path, "scan", 2 if expected == "output_limit" else 0.2, 8192
    )
    assert result["gap"] == expected
    assert result["cleaned"] is True
    assert result["bytes"] <= 8192
    assert (tmp_path / "scan.stdout").stat().st_mode & 0o777 == 0o600
    assert (tmp_path / "scan.stderr").stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        owner["capture"]([sys.executable, "-c", "pass"], tmp_path, "scan", 0.2, 8192)


def test_linux30_path_only_error_keeps_input_without_synthetic_span():
    owner = _linux30_owner()
    native = _linux30_native_error()
    native["errors"] = [
        {
            "type": "Syntax error",
            "code": 3,
            "path": "/opt/specfact/snapshot/second.py",
            "message": "Syntax error at line /opt/specfact/snapshot/second.py:2:\n RAW_SECRET_CANARY",
        }
    ]
    result = owner["project_native"](
        json.dumps(native).encode(), {"first.py": b"x\n", "second.py": b"bad\n"}, {}, "base", "bugs"
    )
    assert result["status"] == "DIAGNOSTIC_COMPLETE"
    assert result["errors"] == [
        {"side": "base", "member": "bugs", "category": "syntax_error", "code": 3, "path": "second.py", "role": "source"}
    ]
    assert "RAW_SECRET_CANARY" not in json.dumps(result)


def test_linux30_frozen_manifest_and_unique_workflow():
    owner = _linux30_owner()
    assert len(owner["INPUTS"]["head"]) == 30
    assert sum(row["status"] == "present" for row in owner["INPUTS"]["base"].values()) == 23
    assert sum(row["status"] == "absent" for row in owner["INPUTS"]["base"].values()) == 7
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/semgrep-input-diagnostic.yml").read_text())
    assert workflow[True]["push"] == {"branches": ["codex/pr510-semgrep-once-25"]}
    assert workflow[True]["pull_request"] == {
        "branches": ["dev"],
        "paths": [
            ".github/workflows/semgrep-input-diagnostic.yml",
            "scripts/semgrep_input_diagnostic.py",
            "tests/host/proof_independent_review_diagnostic.py",
        ],
    }
    assert "github.event_name == 'push'" in workflow["jobs"]["diagnostic"]["if"]
    job = workflow["jobs"]["diagnostic"]
    assert job["timeout-minutes"] == 30
    assert "strategy" not in job
    steps = job["steps"]
    admission_index = next(index for index, step in enumerate(steps) if "--phase admit" in step.get("run", ""))
    setup_index = next(index for index, step in enumerate(steps) if "actions/setup-python@" in step.get("uses", ""))
    assert admission_index < setup_index
    assert sum("--phase setup" in step.get("run", "") for step in steps) == 1
    assert "stdout" not in steps[-1]["with"]["path"]


def test_linux30_stale_git_input_stops_materialization(tmp_path):
    owner = _linux30_owner()
    materialize = owner["materialize"]
    materialize.__globals__["git"] = lambda *_args: b"100644 blob wrong\twrong.py\0"
    with pytest.raises(ValueError, match="input_identity"):
        materialize(tmp_path, tmp_path)


@pytest.mark.skipif(sys.platform != "linux", reason="Linux pre-exec bounded supervision")
def test_linux30_preexec_hang_and_cleanup_failure_preserve_primary(tmp_path):
    import time
    from types import SimpleNamespace

    owner = _linux30_owner()
    sandbox = SimpleNamespace(_request_exec_trace=lambda: time.sleep(60))
    capture = owner["capture"]
    result = capture([sys.executable, "-c", "pass"], tmp_path, "preexec", 0.1, 1024, sandbox=sandbox)
    assert result["gap"] == "deadline"
    assert result["cleaned"] is True
    real_cleanup = capture.__globals__["_reap_tree"]

    def cleanup_then_fail(pid):
        assert real_cleanup(pid)
        raise OSError("RAW_CLEANUP_SECRET")

    capture.__globals__["_reap_tree"] = cleanup_then_fail
    result = capture([sys.executable, "-c", "import time;time.sleep(60)"], tmp_path, "cleanup", 0.1, 1024)
    assert result["gap"] == "deadline"
    assert result["cleaned"] is False
    assert "RAW_CLEANUP_SECRET" not in json.dumps(result)


@pytest.mark.skipif(sys.platform != "linux", reason="Linux real exec-stop and rejected dynamic launcher")
def test_linux30_pre_namespace_authentication_precedes_child_execution(tmp_path):
    from specfact_code_review.run import sandbox

    owner = _linux30_owner()
    marker = tmp_path / "must-not-execute"
    descriptor = os.open(sys.executable, os.O_RDONLY)
    try:
        result = owner["capture"](
            [sys.executable, "-c", f"from pathlib import Path;Path({str(marker)!r}).touch()"],
            tmp_path,
            "reject-loader",
            2,
            1024,
            descriptor=descriptor,
            sandbox=sandbox,
        )
    finally:
        os.close(descriptor)
    assert result["gap"] == "exec_identity"
    assert result["cleaned"] is True
    assert not marker.exists()


def test_linux30_rule_spans_and_skipped_targets_are_explicit():
    owner = _linux30_owner()
    native = _linux30_native_error()
    native["paths"]["skipped"] = [{"path": "/opt/specfact/snapshot/second.py", "reason": "always_skipped"}]
    native["errors"][0]["spans"][0]["file"] = "/opt/specfact/config/0/.semgrep/bugs.yaml"
    result = owner["project_native"](
        json.dumps(native).encode(),
        {"first.py": b"x\n", "second.py": b"bad\n"},
        {".semgrep/bugs.yaml": b"rules:\nbad\n"},
        "head",
        "bugs",
    )
    assert result["status"] == "DIAGNOSTIC_COMPLETE"
    assert result["errors"][0]["role"] == "rule"
    assert result["errors"][0]["path"] == ".semgrep/bugs.yaml"
    assert result["accounted"] == [
        {"path": "first.py", "dispositions": ["scanned"]},
        {"path": "second.py", "dispositions": ["skipped"]},
    ]


def test_linux30_finalization_failure_preserves_failed_exit(tmp_path, monkeypatch):
    owner = _linux30_owner()
    main = owner["main"]
    monkeypatch.setattr(owner["signal"], "signal", lambda *_args: None)
    main.__globals__["admission"] = lambda *_args: (_ for _ in ()).throw(ValueError("primary"))
    main.__globals__["private_file"] = lambda *_args: (_ for _ in ()).throw(OSError("secondary"))
    monkeypatch.setattr(
        sys, "argv", ["controller", "--phase", "setup", "--root", str(tmp_path), "--repository", str(tmp_path)]
    )
    previous_umask = os.umask(0o077)
    try:
        assert main() == 1
    finally:
        os.umask(previous_umask)


def test_linux30_failure_stage_is_useful_without_raw_details():
    owner = _linux30_owner()
    failure = owner["CommandFailureError"](
        "setup-4", {"returncode": 1, "bytes": 29, "gap": None, "cleaned": True, "stderr": "RAW_FAILURE_SECRET"}
    )
    record = owner["failure_record"]("setup", failure)
    assert record["stage"] == "setup-4"
    assert record["capture"] == {"returncode": 1, "bytes": 29, "gap": None, "cleaned": True}
    assert "RAW_FAILURE_SECRET" not in json.dumps(record)
    unknown = owner["failure_record"]("prepare", ValueError("RAW_FAILURE_SECRET"))
    assert unknown["category"] == "UNKNOWN"
    assert "RAW_FAILURE_SECRET" not in json.dumps(unknown)


@pytest.mark.skipif(sys.platform != "linux", reason="Linux adopted descendant identity and pipe proof")
def test_linux30_descendant_holding_pipe_is_observed_and_reaped(tmp_path):
    owner = _linux30_owner()
    pid_file = tmp_path / "descendant.pid"
    program = (
        "import os,time\nfrom pathlib import Path\n"
        "if os.fork()==0:\n os.setsid()\n"
        f" Path({str(pid_file)!r}).write_text(str(os.getpid()))\n time.sleep(60)\n"
    )
    captured = owner["capture"]([sys.executable, "-c", program], tmp_path, "held-pipe", 1, 1024)
    assert pid_file.is_file()
    assert not Path("/proc", pid_file.read_text()).exists()
    assert captured["gap"] == "deadline"
    assert captured["cleaned"] is True


@pytest.mark.parametrize(
    "tag,payload",
    [
        ("PartialParsing", []),
        ("PartialParsing", 42),
        ("PartialParsing", [42]),
        ("PartialParsing", [{"file": []}]),
        ("PatternParseError", 42),
        ("IncompatibleRule", {}),
        ("DependencyResolutionError", "RAW_SECRET_CANARY"),
    ],
)
def test_linux31_tagged_errors_remain_incomplete_and_accounted(tag, payload):
    native = _linux30_native_error()
    native["errors"] = [{"type": [tag, payload], "path": "/opt/specfact/snapshot/first.py", "code": 3}]
    result = _linux30_owner()["project_native"](json.dumps(native).encode(), {"first.py": b"x\n"}, {}, "head", "clean")
    assert result["status"] == "INCOMPLETE"
    assert len(result["errors"]) == 1
    assert "RAW_SECRET_CANARY" not in json.dumps(result)
    if tag == "PartialParsing":
        assert result["errors"] == [{"side": "head", "member": "clean", "category": "partial_parsing", "code": 3}]


@pytest.mark.parametrize("registration", [1, 2])
def test_linux31_registration_failure_owns_mock_child_and_all_pipes(tmp_path, monkeypatch, registration):
    owner, _spawn_attempts = _linux34_mock_capture_owner(monkeypatch)
    capture = owner["capture"]
    pipes, reaped = [], []
    real_pipe = os.pipe
    selector_type = owner["selectors"].DefaultSelector

    def pipe():
        pair = real_pipe()
        pipes.extend(pair)
        return pair

    class FailingSelector(selector_type):
        registrations = 0

        def register(self, *args, **kwargs):
            self.registrations += 1
            if self.registrations == registration:
                raise OSError("PRIMARY_REGISTRATION_FAILURE")
            return super().register(*args, **kwargs)

    monkeypatch.setattr(os, "pipe", pipe)
    monkeypatch.setattr(owner["selectors"], "DefaultSelector", FailingSelector)
    capture.__globals__["_spawn"] = lambda *_args: 123456789
    capture.__globals__["_reap_tree"] = lambda pid: reaped.append(pid) or True
    result = None
    try:
        result = capture(["unused"], tmp_path, "registration", 0.1, 1024)
    except OSError:
        pass
    finally:
        closed = []
        for fd in pipes:
            try:
                os.fstat(fd)
            except OSError:
                closed.append(fd)
            else:
                os.close(fd)
    assert reaped == [123456789]
    assert closed == pipes
    assert result is not None
    assert result["gap"] == "supervision_failed"
    assert result["cleaned"] is True


@pytest.mark.parametrize("signum", ["SIGTERM", "SIGINT"])
def test_linux31_pending_cancellation_waits_for_mock_pid_ownership(tmp_path, monkeypatch, signum):
    import signal

    owner, _spawn_attempts = _linux34_mock_capture_owner(monkeypatch)
    capture = owner["capture"]
    reaped = []
    selected = getattr(signal, signum)
    prior_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())

    def cancel(*_args):
        raise InterruptedError("PRIMARY_CANCELLATION")

    def spawn(*_args):
        os.kill(os.getpid(), selected)
        return 123456789

    previous = signal.signal(selected, cancel)
    monkeypatch.setitem(capture.__globals__, "_spawn", spawn)
    monkeypatch.setitem(capture.__globals__, "_reap_tree", lambda pid: reaped.append(pid) or True)
    try:
        result = capture(["unused"], tmp_path, "pending", 0.1, 1024)
        assert result["gap"] == "supervision_failed"
        assert result["cleaned"] is True
        assert reaped == [123456789]
        assert signal.pthread_sigmask(signal.SIG_BLOCK, set()) == prior_mask
    finally:
        signal.signal(selected, previous)
        signal.pthread_sigmask(signal.SIG_SETMASK, prior_mask)


@pytest.mark.skipif(
    sys.platform != "linux", reason="Linux real fork handoff, pending cancellation and PID absence proof"
)
@pytest.mark.parametrize("fault", ["register1", "register2", "SIGTERM", "SIGINT", "cleanup"])
def test_linux31_outermost_handoff_reaps_real_child_and_descendant(tmp_path, fault):
    driver = tmp_path / "driver.py"
    driver.write_text('''
import json, os, runpy, selectors, signal, sys, time
from pathlib import Path
root = Path(sys.argv[1])
fault = sys.argv[2]
owner = runpy.run_path(sys.argv[3])
capture = owner["capture"]
namespace = capture.__globals__
real_spawn, real_reap, real_pipe = namespace["_spawn"], namespace["_reap_tree"], os.pipe
pipe_fds = []
spawned = []
registrations = []
original_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
def cancel(*_args):
    raise InterruptedError("PRIMARY_CANCELLATION")
signal.signal(signal.SIGTERM, cancel)
signal.signal(signal.SIGINT, cancel)
def pipe():
    pair = real_pipe()
    pipe_fds.extend(pair)
    return pair
def spawn(*args):
    pid = real_spawn(*args)
    spawned.append(pid)
    deadline = time.monotonic() + 2
    while not (root / "pids.json").exists() and time.monotonic() < deadline:
        time.sleep(0.005)
    if fault in {"SIGTERM", "SIGINT"}:
        os.kill(os.getpid(), getattr(signal, fault))
    return pid
class Selector(selectors.DefaultSelector):
    def register(self, *args, **kwargs):
        registrations.append(args[0])
        if (fault in {"register1", "cleanup"} and len(registrations) == 1) or (fault == "register2" and len(registrations) == 2):
            raise OSError("PRIMARY_REGISTRATION_FAILURE")
        return super().register(*args, **kwargs)
def reap(pid):
    cleaned = real_reap(pid)
    if fault == "cleanup":
        raise OSError("SECONDARY_CLEANUP_FAILURE")
    return cleaned
os.pipe = pipe
selectors.DefaultSelector = Selector
namespace["_spawn"], namespace["_reap_tree"] = spawn, reap
program = """import json,os,signal,sys,time
from pathlib import Path
parent=os.getpid()
if os.fork()==0:
 os.setsid()
 mask=signal.pthread_sigmask(signal.SIG_BLOCK,set())
 Path(sys.argv[1]).write_text(json.dumps({'parent':parent,'descendant':os.getpid(),'blocked':[int(s) for s in mask]}))
time.sleep(60)
"""
started = time.monotonic()
result = capture([sys.executable, "-c", program, str(root / "pids.json")], root, "handoff", 4, 1024)
closed = []
for fd in pipe_fds:
    try:
        os.fstat(fd)
    except OSError:
        closed.append(fd)
print(json.dumps({'result':result,'spawned':spawned,'pipe_fds':pipe_fds,'closed':closed,'registrations':len(registrations),'seconds':time.monotonic()-started,'mask_restored':signal.pthread_sigmask(signal.SIG_BLOCK,set()) == original_mask}))
''')
    completed = subprocess.run(
        [sys.executable, str(driver), str(tmp_path), fault, str(REPO_ROOT / "scripts/semgrep_input_diagnostic.py")],
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    pids = json.loads((tmp_path / "pids.json").read_text())
    assert report["spawned"] == [pids["parent"]]
    assert not Path("/proc", str(pids["parent"])).exists()
    assert not Path("/proc", str(pids["descendant"])).exists()
    assert pids["blocked"] == []
    assert report["closed"] == report["pipe_fds"]
    assert len(report["closed"]) == 4
    assert report["mask_restored"] is True
    assert report["result"]["gap"] == "supervision_failed"
    assert report["result"]["cleaned"] is (fault != "cleanup")
    assert report["registrations"] == {"register1": 1, "register2": 2, "cleanup": 1, "SIGTERM": 0, "SIGINT": 0}[fault]
    assert report["seconds"] < 5
    assert "PRIMARY_" not in completed.stdout
    assert "SECONDARY_" not in completed.stdout


def test_linux31_partial_parsing_preserves_valid_native_locations():
    native = _linux30_native_error()
    native["errors"][0]["type"] = ["PartialParsing", native["errors"][0].pop("spans")]
    result = _linux30_owner()["project_native"](
        json.dumps(native).encode(), {"first.py": b"x=1\n", "second.py": b"x=1\nbad\n"}, {}, "head", "clean"
    )
    assert result["status"] == "DIAGNOSTIC_COMPLETE"
    assert result["errors"] == [
        {
            "side": "head",
            "member": "clean",
            "category": "partial_parsing",
            "code": 3,
            "path": "second.py",
            "role": "source",
            "line": 2,
            "column": 1,
            "end_line": 2,
            "end_column": 4,
        }
    ]


@pytest.mark.parametrize("fault", ["second_pipe", "fork"])
def test_linux31_pre_spawn_failure_closes_owned_pipes(tmp_path, monkeypatch, fault):
    owner, _spawn_attempts = _linux34_mock_capture_owner(monkeypatch)
    capture = owner["capture"]
    pipes, reaped = [], []
    real_pipe = os.pipe

    def pipe():
        if pipes and fault == "second_pipe":
            raise OSError("PIPE_FAILURE")
        pair = real_pipe()
        pipes.extend(pair)
        return pair

    def spawn(*_args):
        raise OSError("FORK_FAILURE")

    monkeypatch.setattr(os, "pipe", pipe)
    monkeypatch.setitem(capture.__globals__, "_spawn", spawn)
    monkeypatch.setitem(capture.__globals__, "_reap_tree", lambda pid: reaped.append(pid) or True)
    result = capture(["unused"], tmp_path, "pre-spawn", 0.1, 1024)
    assert result["gap"] == "supervision_failed"
    assert result["cleaned"] is True
    assert reaped == []
    assert len(pipes) == (2 if fault == "second_pipe" else 4)
    for fd in pipes:
        with pytest.raises(OSError):
            os.fstat(fd)


def test_linux31_valid_admission_accepts_exact_single_parent():
    owner = _linux30_owner()
    sha = "a" * 40
    event = {"ref": owner["ALIAS"], "before": "0" * 40, "after": sha, "created": True, "deleted": False}
    assert owner["admit"](event, sha, "1", [owner["SUBJECT_HEAD"]]) is None


def test_linux31_host_workflow_is_exact_head_and_separate_from_scanner():
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/semgrep-input-diagnostic.yml").read_text())
    host = workflow["jobs"]["linux-host-proof"]
    assert host["if"] == "github.event_name == 'pull_request' && github.head_ref != 'codex/pr510-semgrep-once-25'"
    assert host["runs-on"] == "ubuntu-24.04"
    assert host["timeout-minutes"] == 20
    steps = host["steps"]
    assert steps[0]["with"]["ref"] == "${{ github.event.pull_request.head.sha }}"
    assert steps[0]["with"]["persist-credentials"] is False
    core = next(step for step in steps if step.get("with", {}).get("repository") == "nold-ai/specfact-cli")
    assert core["with"]["ref"] == "d579970565530c3fd7b98bad4de90cf874c2a99d"
    assert core["with"]["persist-credentials"] is False
    runs = "\n".join(step.get("run", "") for step in steps)
    assert "--phase" not in runs
    assert "semgrep_input_diagnostic.py" not in runs
    assert "hatch env create" in runs
    assert "hatch run python tools/ensure_core_dependency.py" in runs
    assert "timeout 600 hatch run python -m pytest" in runs
    assert (
        "tests/host/proof_capsule_deferred_review_ci.py tests/host/proof_independent_review_diagnostic.py -n0" in runs
    )
    assert 'test "$(git rev-parse HEAD)" = "$EXPECTED_HEAD"' in runs
    assert 'test "$(git -C "$SPECFACT_CLI_REPO" rev-parse HEAD)" = "$EXPECTED_CORE"' in runs
    assert all(step.get("timeout-minutes", 0) > 0 for step in steps)


@pytest.mark.parametrize("mutation", ["complete", "missing", "skipped", "failure", "duplicate"])
def test_linux31_workflow_rejects_incomplete_linux_junit(tmp_path, mutation):
    import xml.etree.ElementTree as ET

    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/semgrep-input-diagnostic.yml").read_text())
    step = next(
        step
        for step in workflow["jobs"]["linux-host-proof"]["steps"]
        if step.get("name") == "Require every real Linux lifecycle proof"
    )
    script = step["run"].split("python -I - <<'PYPROOF'\n", 1)[1].rsplit("PYPROOF", 1)[0]
    suite = ET.Element("testsuite")
    for name, count in [
        ("test_linux30_bounded_capture_lifecycle", 4),
        ("test_linux30_preexec_hang_and_cleanup_failure_preserve_primary", 1),
        ("test_linux30_pre_namespace_authentication_precedes_child_execution", 1),
        ("test_linux30_descendant_holding_pipe_is_observed_and_reaped", 1),
        ("test_linux31_outermost_handoff_reaps_real_child_and_descendant", 5),
    ]:
        for index in range(count):
            ET.SubElement(suite, "testcase", name=f"{name}[{index}]")
    if mutation == "missing":
        suite.remove(suite[-1])
    elif mutation in {"skipped", "failure"}:
        ET.SubElement(suite[-1], mutation)
    elif mutation == "duplicate":
        suite[-1].set("name", suite[-2].attrib["name"])
    ET.ElementTree(suite).write(tmp_path / "junit.xml")
    result = subprocess.run(
        [sys.executable, "-I", "-"],
        input=script,
        text=True,
        env=dict(os.environ, PROOF_DIR=str(tmp_path), PYTHONOPTIMIZE="2"),
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert (result.returncode == 0) is (mutation == "complete")
    assert (tmp_path / "lifecycle-counts.json").exists() is (mutation == "complete")


@pytest.mark.parametrize("mismatch", [None, "head", "core"])
def test_linux31_workflow_checks_actual_checkout_identities(tmp_path, mismatch):
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/semgrep-input-diagnostic.yml").read_text())
    step = next(
        step
        for step in workflow["jobs"]["linux-host-proof"]["steps"]
        if step.get("name") == "Assert and retain exact source identities"
    )
    executable = tmp_path / "git"
    executable.write_text('#!/bin/sh\nif [ "$1" = "-C" ]; then echo "$ACTUAL_CORE"; else echo "$ACTUAL_HEAD"; fi\n')
    executable.chmod(0o700)
    environment = dict(
        os.environ,
        PATH=str(tmp_path) + os.pathsep + os.environ["PATH"],
        PROOF_DIR=str(tmp_path / "evidence"),
        EXPECTED_HEAD="a" * 40,
        EXPECTED_CORE="b" * 40,
        ACTUAL_HEAD=("c" if mismatch == "head" else "a") * 40,
        ACTUAL_CORE=("c" if mismatch == "core" else "b") * 40,
        SPECFACT_CLI_REPO=str(tmp_path / "core"),
    )
    result = subprocess.run(["bash", "-c", step["run"]], env=environment, capture_output=True, timeout=5, check=False)
    assert (result.returncode == 0) is (mismatch is None)
    assert (tmp_path / "evidence/identities.txt").read_text().splitlines() == [
        environment["ACTUAL_HEAD"],
        environment["ACTUAL_CORE"],
    ]


def _linux32_capture_rig(tmp_path, monkeypatch):
    import signal
    from types import SimpleNamespace

    owner, _spawn_attempts = _linux34_mock_capture_owner(monkeypatch)
    namespace = owner["capture"].__globals__
    events, fds, outputs = [], [], []
    handlers = {
        signal.SIGTERM: lambda *_: (_ for _ in ()).throw(InterruptedError("SAVED_TERM")),
        signal.SIGINT: signal.SIG_IGN,
    }
    original = handlers.copy()
    state = {"mask": {signal.SIGUSR1}, "phase": None, "fault": None, "triggered": False}
    original_mask = state["mask"].copy()

    def trigger(phase):
        events.append(phase)
        if state["phase"] == phase:
            handler = handlers[signal.SIGTERM]
            if callable(handler):
                handler(signal.SIGTERM, None)
                handler(signal.SIGINT, None)
        if state["fault"] == phase and not state["triggered"]:
            state["triggered"] = True
            raise OSError("INJECTED_FAILURE")

    def change_handler(sig, handler):
        phase = ("restore_" if handler is original[sig] else "install_") + signal.Signals(sig).name
        trigger(phase)
        previous = handlers[sig]
        handlers[sig] = handler
        return previous

    def mask(how, selected):
        trigger("mask_restore" if how == signal.SIG_SETMASK else "mask_block")
        before = state["mask"].copy()
        state["mask"] = set(selected) if how == signal.SIG_SETMASK else before | set(selected)
        return before

    fake_signal = SimpleNamespace(
        SIGTERM=signal.SIGTERM,
        SIGINT=signal.SIGINT,
        SIG_BLOCK=signal.SIG_BLOCK,
        SIG_SETMASK=signal.SIG_SETMASK,
        SIGTRAP=signal.SIGTRAP,
        SIG_IGN=signal.SIG_IGN,
        getsignal=handlers.__getitem__,
        signal=change_handler,
        pthread_sigmask=mask,
    )
    monkeypatch.setitem(namespace, "signal", fake_signal)
    real_file, real_pipe, real_close = namespace["private_file"], os.pipe, os.close
    selector_type = namespace["selectors"].DefaultSelector

    class Output:
        def __init__(self, path):
            trigger("acquire_" + path.suffix[1:])
            self.stream = real_file(path)
            self.name = path.suffix[1:]
            outputs.append(self.stream)

        def __enter__(self):
            trigger("open_" + self.name)
            return self

        def __exit__(self, *_args):
            self.stream.close()
            trigger("close_" + self.name)

        def write(self, data):
            return self.stream.write(data)

    class Selector(selector_type):
        def __init__(self):
            trigger("acquire_selector")
            super().__init__()

        def register(self, *args, **kwargs):
            trigger("register")
            return super().register(*args, **kwargs)

        def close(self):
            super().close()
            trigger("selector_close")

    def pipe():
        pair = real_pipe()
        fds.extend(pair)
        return pair

    def close(fd):
        real_close(fd)
        if fd in fds:
            trigger("fd_close")

    def spawn(*_args):
        trigger("spawn")
        return 123456789

    def reap(pid):
        assert pid == 123456789
        trigger("reap")
        return True

    monkeypatch.setitem(namespace, "private_file", Output)
    monkeypatch.setattr(namespace["selectors"], "DefaultSelector", Selector)
    monkeypatch.setattr(os, "pipe", pipe)
    monkeypatch.setattr(os, "close", close)
    monkeypatch.setattr(os, "waitpid", lambda *_: (123456789, 0))
    monkeypatch.setitem(namespace, "_spawn", spawn)
    monkeypatch.setitem(namespace, "_reap_tree", reap)
    return owner, state, events, fds, outputs, handlers, original, original_mask


@pytest.mark.parametrize(
    "phase", ["spawn", "reap", "fd_close", "selector_close", "close_stderr", "close_stdout", "mask_restore"]
)
def test_linux32_cancellation_owns_every_finalizer(tmp_path, monkeypatch, phase):
    owner, state, events, fds, outputs, handlers, original, mask = _linux32_capture_rig(tmp_path, monkeypatch)
    state["phase"] = phase
    result = owner["capture"](["unused"], tmp_path, "record", 1, 1024)
    assert result == {
        "returncode": None if phase in {"spawn", "mask_restore", "fd_close"} else 0,
        "bytes": 0,
        "gap": "supervision_failed",
        "cleaned": True,
    }
    assert events.count("reap") == 1
    assert all(output.closed for output in outputs)
    assert handlers == original
    assert state["mask"] == mask
    assert events.index("restore_SIGTERM") > events.index("close_stdout")
    assert events.index("restore_SIGINT") > events.index("close_stdout")
    for fd in fds:
        with pytest.raises(OSError):
            os.fstat(fd)


@pytest.mark.parametrize(
    "fault",
    [
        "acquire_stdout",
        "acquire_stderr",
        "acquire_selector",
        "install_SIGTERM",
        "install_SIGINT",
        "mask_restore",
        "restore_SIGTERM",
        "restore_SIGINT",
        "reap",
        "fd_close",
        "selector_close",
        "close_stderr",
        "close_stdout",
    ],
)
def test_linux32_failures_remain_nonaccepting_and_attempt_all_restoration(tmp_path, monkeypatch, fault):
    owner, state, events, fds, outputs, handlers, original, mask = _linux32_capture_rig(tmp_path, monkeypatch)
    state["fault"] = fault
    result = owner["capture"](["unused"], tmp_path, "failure", 1, 1024)
    assert result["gap"] in {"supervision_failed", "cleanup_failed"}
    assert "restore_SIGTERM" in events
    assert "restore_SIGINT" in events
    assert state["mask"] == mask
    if fault.startswith("install"):
        assert not fds and not outputs and "spawn" not in events
    if not fault.startswith("restore"):
        assert handlers == original
    assert all(output.closed for output in outputs)
    for fd in fds:
        with pytest.raises(OSError):
            os.fstat(fd)


def test_linux32_deferred_callback_at_cleanup_entry_preserves_first_gap(tmp_path, monkeypatch):
    owner, state, events, fds, outputs, handlers, original, mask = _linux32_capture_rig(tmp_path, monkeypatch)
    state["phase"] = "reap"
    state["fault"] = "register"
    namespace = owner["capture"].__globals__
    signals = namespace["signal"]
    original_mask_call = signals.pthread_sigmask
    original_reap = namespace["_reap_tree"]
    pending = []
    selector_type = namespace["selectors"].DefaultSelector

    class DeferredSelector(selector_type):
        def register(self, *args, **kwargs):
            pending.append(signals.getsignal(signals.SIGTERM))
            return super().register(*args, **kwargs)

    def deliver():
        if pending:
            callback = pending.pop()
            callback(signals.SIGTERM, None)

    def mask_call(*args):
        deliver()
        return original_mask_call(*args)

    def reap(pid):
        deliver()
        return original_reap(pid)

    monkeypatch.setattr(namespace["selectors"], "DefaultSelector", DeferredSelector)
    monkeypatch.setattr(signals, "pthread_sigmask", mask_call)
    monkeypatch.setitem(namespace, "_reap_tree", reap)
    result = owner["capture"](["unused"], tmp_path, "deferred", 1, 1024)
    assert result["gap"] == "supervision_failed"
    assert not pending
    assert events.count("reap") == 1
    for fd in fds:
        with pytest.raises(OSError):
            os.fstat(fd)
    assert result["cleaned"] is True
    assert handlers == original and state["mask"] == mask
    assert all(output.closed for output in outputs)


def test_linux32_workflow_uses_runner_context_only_in_consuming_step_env():
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/semgrep-input-diagnostic.yml").read_text())
    host = workflow["jobs"]["linux-host-proof"]
    assert "PROOF_DIR" not in host["env"]
    consumers = [step for step in host["steps"] if "PROOF_DIR" in step.get("run", "")]
    assert len(consumers) == 3
    assert all(step["env"]["PROOF_DIR"] == "${{ runner.temp }}/semgrep-host-proof" for step in consumers)


@pytest.mark.parametrize("fault", ["reap", "restore_SIGTERM", "mask_restore"])
def test_linux32_secondary_failure_keeps_exec_identity_gap(tmp_path, monkeypatch, fault):
    import signal

    owner, state, events, _fds, _outputs, _handlers, _original, _mask = _linux32_capture_rig(tmp_path, monkeypatch)
    namespace = owner["capture"].__globals__
    original_reap = namespace["_reap_tree"]

    def reap(pid):
        state["fault"] = fault
        return original_reap(pid)

    monkeypatch.setitem(namespace, "_reap_tree", reap)
    monkeypatch.setattr(os, "waitpid", lambda *_: (123456789, (signal.SIGSTOP << 8) | 0x7F))
    result = owner["capture"](["unused"], tmp_path, "identity", 1, 1024)
    assert result["gap"] == "exec_identity"
    assert events.count("reap") == 1
    assert "restore_SIGTERM" in events and "restore_SIGINT" in events


@pytest.mark.parametrize("failure", [None, "handler", "mask"])
def test_linux32_child_restores_dispositions_before_unmask_and_exits_on_failure(monkeypatch, failure):
    import signal
    from types import SimpleNamespace

    owner = _linux30_owner()
    spawn = owner["_spawn"]
    events = []

    def saved(*_args):
        return None

    inherited = SimpleNamespace(handlers={signal.SIGTERM: saved, signal.SIGINT: signal.SIG_IGN}, mask={signal.SIGUSR1})

    def disposition(sig, handler):
        events.append(("handler", sig, handler))
        if failure == "handler":
            raise OSError("CHILD_HANDLER_FAILURE")

    def unmask(how, mask):
        events.append(("mask", how, mask))
        if failure == "mask":
            raise OSError("CHILD_MASK_FAILURE")

    def execute(*_args):
        events.append(("exec",))
        raise OSError("EXEC_SENTINEL")

    class ChildExit(BaseException):
        pass

    def exit_child(code):
        assert code == 125
        raise ChildExit

    fake_os = SimpleNamespace(
        fork=lambda: 0,
        setsid=lambda: None,
        open=lambda *_: 10,
        devnull="/dev/null",
        O_RDONLY=0,
        dup2=lambda *_: None,
        sysconf=lambda *_: 256,
        closerange=lambda *_: None,
        execve=execute,
        _exit=exit_child,
    )
    fake_signal = SimpleNamespace(signal=disposition, pthread_sigmask=unmask, SIG_SETMASK=signal.SIG_SETMASK)
    monkeypatch.setitem(spawn.__globals__, "os", fake_os)
    monkeypatch.setitem(spawn.__globals__, "signal", fake_signal)
    with pytest.raises(ChildExit):
        spawn(["unused"], 11, 12, None, None, {}, inherited)
    expected = [("handler", signal.SIGTERM, saved)]
    if failure != "handler":
        expected += [("handler", signal.SIGINT, signal.SIG_IGN), ("mask", signal.SIG_SETMASK, {signal.SIGUSR1})]
    if failure is None:
        expected += [("exec",)]
    assert events == expected


@pytest.mark.parametrize("phase", ["reap", "open_stdout", "install_SIGINT"])
def test_linux32_late_capture_cancellation_aborts_actual_experiment_loop(tmp_path, monkeypatch, phase):
    import signal
    from types import SimpleNamespace

    owner, state, events, _fds, _outputs, _handlers, _original, _mask = _linux32_capture_rig(tmp_path, monkeypatch)
    if phase.startswith("install"):
        state["fault"] = phase
    else:
        state["phase"] = phase
    namespace = owner["experiment"].__globals__
    runtime = tmp_path / "cache/invocations/runtime"
    runtime.mkdir(parents=True)
    (tmp_path / "runtime.private.json").write_text(
        json.dumps(
            {
                "root": str(runtime),
                "prepared_root_digest": "fixed",
                "interpreter": "unused",
                "bootstrap": "unused",
                "bubblewrap": {},
            }
        )
    )
    sandbox = SimpleNamespace(
        SnapshotInvocationContext=lambda **_: SimpleNamespace(digest="fixed"),
        build_launch_plan=lambda *_: SimpleNamespace(mounts=[]),
        BubblewrapIdentity=lambda **_: None,
        validate_bubblewrap=lambda *_: SimpleNamespace(status="PASS"),
        _verified_bubblewrap_descriptor=lambda *_: os.open(os.devnull, os.O_RDONLY),
        _bubblewrap_command=lambda *_args, **_kwargs: ["unused"],
        _observe_pre_namespace_objects=lambda *_: None,
        validate_pre_namespace_objects=lambda *_: SimpleNamespace(status="PASS"),
        _ptrace=lambda *_: None,
        _PTRACE_DETACH=17,
    )
    statuses = iter([(123456789, (signal.SIGTRAP << 8) | 0x7F), (123456789, 0)])
    monkeypatch.setattr(os, "waitpid", lambda *_: next(statuses))
    monkeypatch.setitem(namespace, "authenticate", lambda *_: (None, sandbox))
    monkeypatch.setitem(namespace, "root_digest", lambda *_: "fixed")
    monkeypatch.setitem(
        namespace, "materialize", lambda *_: {side: (tmp_path, tmp_path, {}, {}) for side in ("head", "base")}
    )
    owner["experiment"](tmp_path, tmp_path, tmp_path)
    report = json.loads((tmp_path / "public.json").read_text())
    assert events.count("spawn") == (1 if phase == "reap" else 0)
    assert len(report["calls"]) == 1
    assert report["calls"][0]["capture"]["gap"] == "supervision_failed"
    assert report["status"] == "INCOMPLETE" and report["acceptance"] is False
    evidence = json.loads((tmp_path / "head-clean-capture.private.json").read_text())
    missing = {"open_stdout": {"stderr"}, "install_SIGINT": {"stdout", "stderr"}}.get(phase, set())
    for stream in ("stdout", "stderr"):
        assert (evidence[stream + "_sha256"] is None) is (stream in missing)
        assert (evidence[stream + "_bytes"] is None) is (stream in missing)


def test_linux32_cancellation_before_reaper_failure_is_primary(tmp_path, monkeypatch):
    owner, state, events, _fds, outputs, handlers, original, mask = _linux32_capture_rig(tmp_path, monkeypatch)
    state["phase"] = state["fault"] = "reap"
    result = owner["capture"](["unused"], tmp_path, "first-cancel", 1, 1024)
    assert result["gap"] == "supervision_failed"
    assert result["cleaned"] is False
    assert events.count("reap") == 1
    assert all(output.closed for output in outputs)
    assert handlers == original and state["mask"] == mask


def test_linux32_failed_output_wrapper_closes_acquired_descriptor(tmp_path, monkeypatch):
    import contextlib

    owner, _spawn_attempts = _linux34_mock_capture_owner(monkeypatch)
    namespace = owner["capture"].__globals__
    real_open = os.open
    acquired, spawned = [], []

    def forbidden_spawn(*_args):
        spawned.append("spawn")
        pytest.fail("Output wrapper failure must precede spawn")

    monkeypatch.setitem(namespace, "_spawn", forbidden_spawn)

    def acquire(path, *args):
        fd = real_open(path, *args)
        acquired.append(fd)
        return fd

    def fail_wrapper(*_args):
        raise OSError("FDOPEN_FAILURE")

    monkeypatch.setattr(os, "open", acquire)
    monkeypatch.setattr(os, "fdopen", fail_wrapper)
    try:
        result = owner["capture"](["unused"], tmp_path, "wrapper", 1, 1024)
        assert result["gap"] == "supervision_failed"
        assert len(acquired) == 1
        assert spawned == []
        with pytest.raises(OSError):
            os.fstat(acquired[0])
    finally:
        for fd in acquired:
            with contextlib.suppress(OSError):
                os.close(fd)


@pytest.mark.parametrize("ambient", ["count_two", "non_main"])
def test_linux33_portable_rig_owns_context_before_capture(tmp_path, monkeypatch, ambient):
    import threading
    from types import SimpleNamespace

    load_owner = _linux30_owner
    owner = load_owner()
    namespace = owner["capture"].__globals__
    main, other = object(), object()
    ambient_view = SimpleNamespace(
        main_thread=lambda: main,
        current_thread=lambda: other if ambient == "non_main" else main,
        active_count=lambda: 2 if ambient == "count_two" else 1,
    )
    real_functions = threading.main_thread, threading.current_thread, threading.active_count
    with monkeypatch.context() as local:
        local.setitem(namespace, "threading", ambient_view)
        local.setitem(_linux32_capture_rig.__globals__, "_linux30_owner", lambda: owner)
        rig_owner, state, events, fds, outputs, handlers, original, mask = _linux32_capture_rig(tmp_path, local)
        state["phase"] = "spawn"
        result = rig_owner["capture"](["unused"], tmp_path, "ambient", 1, 1024)
        assert result == {"returncode": None, "bytes": 0, "gap": "supervision_failed", "cleaned": True}
        assert events.count("spawn") == events.count("reap") == 1
        assert events.index("acquire_stdout") < events.index("spawn") < events.index("reap")
        assert events.index("reap") < events.index("close_stdout") < events.index("restore_SIGTERM")
        assert len(outputs) == 2 and all(output.closed for output in outputs)
        assert len(fds) == 4
        for fd in fds:
            with pytest.raises(OSError):
                os.fstat(fd)
        assert handlers == original and state["mask"] == mask
        assert load_owner()["capture"].__globals__["threading"] is threading
        assert (threading.main_thread, threading.current_thread, threading.active_count) == real_functions
    assert namespace["threading"] is threading
    assert load_owner()["capture"].__globals__["threading"] is threading


@pytest.mark.parametrize("ambient", ["count_two", "non_main"])
def test_linux33_real_capture_rejects_thread_context_before_ownership(tmp_path, monkeypatch, ambient):
    import threading
    from types import SimpleNamespace

    owner = _linux30_owner()
    namespace = owner["capture"].__globals__
    main, other = object(), object()
    events = []

    def forbidden(*_args, **_kwargs):
        events.append("ownership_attempt")
        pytest.fail("Thread rejection must precede every ownership operation")

    with monkeypatch.context() as local:
        local.setitem(
            namespace,
            "threading",
            SimpleNamespace(
                main_thread=lambda: main,
                current_thread=lambda: other if ambient == "non_main" else main,
                active_count=lambda: 2 if ambient == "count_two" else 1,
            ),
        )
        local.setitem(namespace, "sys", SimpleNamespace(platform="linux"))
        local.setitem(namespace, "ctypes", SimpleNamespace(CDLL=forbidden))
        local.setitem(namespace, "selectors", SimpleNamespace(DefaultSelector=forbidden))
        local.setitem(namespace, "os", SimpleNamespace(open=forbidden, fdopen=forbidden, pipe=forbidden))
        for name in ("_CaptureCancellation", "private_file", "_spawn", "_reap_tree"):
            local.setitem(namespace, name, forbidden)
        with pytest.raises(ValueError, match=r"^single_thread_required$"):
            owner["capture"](["unused"], tmp_path, "denied", 1, 1024)
        assert events == []
        assert list(tmp_path.iterdir()) == []
        assert _linux30_owner()["capture"].__globals__["threading"] is threading
    assert namespace["threading"] is threading


@pytest.mark.parametrize("ambient", ["count_two", "non_main"])
@pytest.mark.parametrize(
    ("caller", "argument"),
    [
        (test_linux31_registration_failure_owns_mock_child_and_all_pipes, 1),
        (test_linux31_registration_failure_owns_mock_child_and_all_pipes, 2),
        (test_linux31_pending_cancellation_waits_for_mock_pid_ownership, "SIGTERM"),
        (test_linux31_pending_cancellation_waits_for_mock_pid_ownership, "SIGINT"),
        (test_linux31_pre_spawn_failure_closes_owned_pipes, "second_pipe"),
        (test_linux31_pre_spawn_failure_closes_owned_pipes, "fork"),
    ],
)
def test_linux34_legacy_mock_callers_own_context(tmp_path, monkeypatch, ambient, caller, argument):
    import threading
    from types import SimpleNamespace

    load_owner = _linux30_owner
    owner = load_owner()
    namespace = owner["capture"].__globals__
    main, other = object(), object()
    real_functions = threading.main_thread, threading.current_thread, threading.active_count
    with monkeypatch.context() as local:
        local.setitem(
            namespace,
            "threading",
            SimpleNamespace(
                main_thread=lambda: main,
                current_thread=lambda: other if ambient == "non_main" else main,
                active_count=lambda: 2 if ambient == "count_two" else 1,
            ),
        )
        local.setitem(caller.__globals__, "_linux30_owner", lambda: owner)
        caller(tmp_path, local, argument)
        assert load_owner()["capture"].__globals__["threading"] is threading
        assert (threading.main_thread, threading.current_thread, threading.active_count) == real_functions
    assert namespace["threading"] is threading


def _linux34_mock_capture_owner(monkeypatch):
    from types import SimpleNamespace

    owner = _linux30_owner()
    namespace = owner["capture"].__globals__
    spawn_attempts = []

    def default_spawn(*_args):
        spawn_attempts.append("spawn")
        raise OSError("MOCK_SPAWN_NOT_CONFIGURED")

    main = object()
    monkeypatch.setitem(
        namespace,
        "threading",
        SimpleNamespace(
            main_thread=lambda: main,
            current_thread=lambda: main,
            active_count=lambda: 1,
        ),
    )
    monkeypatch.setitem(namespace, "_spawn", default_spawn)
    return owner, spawn_attempts


def test_linux34_default_mock_owner_never_spawns_real_child(tmp_path, monkeypatch):
    from types import SimpleNamespace

    owner, spawn_attempts = _linux34_mock_capture_owner(monkeypatch)
    namespace = owner["capture"].__globals__
    child_operations = []

    def forbidden_child_operation(*_args, **_kwargs):
        child_operations.append("child_operation")
        raise OSError("REAL_CHILD_OPERATION_FORBIDDEN")

    monkeypatch.setitem(
        namespace,
        "os",
        SimpleNamespace(
            **{
                **vars(os),
                "fork": forbidden_child_operation,
                "waitpid": forbidden_child_operation,
                "kill": forbidden_child_operation,
            }
        ),
    )
    monkeypatch.setitem(namespace, "_reap_tree", forbidden_child_operation)
    result = owner["capture"](["unused"], tmp_path, "default-mock", 1, 1024)
    assert spawn_attempts == ["spawn"]
    assert child_operations == []
    assert result == {"returncode": None, "bytes": 0, "gap": "supervision_failed", "cleaned": True}
