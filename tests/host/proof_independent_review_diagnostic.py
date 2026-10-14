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
    from tests.unit.test_independent_diagnostic_controller import capture_functions

    captured = capture_functions()["capture_original"](
        report,
        tmp_path / "original-private",
        {"role": "candidate" if job_name == "customer" else "independent", "head": "a" * 40, "attempt": "1"},
        review_exit,
    )
    assert captured["status"] == "COMPLETE"
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
