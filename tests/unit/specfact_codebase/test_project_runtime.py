import contextlib
import json
import os
import signal
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from sys import _base_executable as base_executable

import pytest

from specfact_codebase import project_runtime
from specfact_codebase.project_runtime import (
    PreparationFailure,
    PreparedProject,
    ProjectCommand,
    ProjectSelection,
    _probe as probe_python,
    inspect_project,
    prepare_project,
)


@pytest.fixture(autouse=True)
def lifecycle_selector(request, record_property):
    record_property("specfact.selector", request.node.nodeid)


@pytest.fixture(name="project")
def customer_project(tmp_path):
    root = tmp_path / "customer"
    root.mkdir()
    (root / "pyproject.toml").write_text('[project]\nname="customer"\nversion="0"\n')
    (root / "hatch.toml").write_text(
        '[envs.default]\ndependencies=["pytest<8"]\n[envs.review]\ndetached=true\ndependencies=[]\n'
    )
    target = tmp_path / "existing"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(target)], check=True)
    log = tmp_path / "hatch.log"
    hatch = tmp_path / "hatch"
    hatch.write_text(
        f"#!{sys.executable}\nimport sys\nfrom pathlib import Path\n"
        f'with Path({str(log)!r}).open("a") as f: f.write(" ".join(sys.argv[1:])+"\\n")\n'
        f'print("Hatch, version test" if sys.argv[1:]==["--version"] else {str(target)!r})\n'
    )
    hatch.chmod(0o700)
    return root, target, hatch, log


def ready(project, tmp_path):
    root, target, hatch, _ = project
    plan = inspect_project(
        root, ProjectSelection(environment="review", python=str(target / "bin/python"), hatch=str(hatch))
    )
    prepared = prepare_project(plan, tmp_path / "invocation")
    assert isinstance(prepared, PreparedProject), prepared
    return prepared


def test_inspection_is_pure_and_ambiguity_is_actionable(project):
    root, _, hatch, log = project
    plan = inspect_project(root, ProjectSelection(hatch=str(hatch)))
    assert not log.exists()
    assert "review" in str(plan.diagnostics)
    assert "default" in str(plan.diagnostics)


def test_selected_venv_identity_and_no_sync_even_with_stale_dependencies(project, tmp_path):
    root, target, _, log = project
    config = root / "hatch.toml"
    config.write_text(
        config.read_text().replace("dependencies=[]", 'dependencies=["impossible-project-dependency==999"]')
    )
    prepared = ready(project, tmp_path)
    result = prepared.run(
        ProjectCommand(("python", "-c", "import sys,json; print(json.dumps([sys.prefix,sys.executable]))"), root),
        timeout=10,
    )
    assert result.outcome == "exited"
    assert json.loads(result.stdout) == [str(target), str(target / "bin/python")]
    assert "create" not in log.read_text()
    assert "run" not in log.read_text()


def test_missing_tool_never_falls_back_to_controller_path(project, tmp_path, monkeypatch):
    prepared = ready(project, tmp_path)
    shadow = tmp_path / "controller-bin"
    shadow.mkdir()
    executable = shadow / "definitely-missing-customer-tool"
    executable.write_text("#!/bin/sh\necho controller-tool-executed\n")
    executable.chmod(0o700)
    monkeypatch.setenv("PATH", str(shadow))
    result = prepared.run(ProjectCommand(("definitely-missing-customer-tool",), project[0]), timeout=10)
    assert result.outcome == "unavailable"
    assert result.exit_code is None


def test_controller_python_path_removed_and_explicit_override_honored(project, tmp_path, monkeypatch):
    prepared = ready(project, tmp_path)
    monkeypatch.setenv("PYTHONPATH", "/controller/contamination")
    monkeypatch.setenv("PYTHONHOME", "/controller/broken")
    result = prepared.run(
        ProjectCommand(
            ("python", "-c", "import os; print(os.getenv('PYTHONPATH')); print(os.getenv('CUSTOM'))"),
            project[0],
            {"CUSTOM": "customer"},
        ),
        timeout=10,
    )
    assert result.stdout == "None\ncustomer\n"
    refused = prepared.run(ProjectCommand(("python", "-V"), project[0], {"PATH": "/controller"}), timeout=10)
    assert refused.outcome == "execution_failed"


def test_nonzero_timeout_and_bounded_output_are_distinct(project, tmp_path):
    prepared = ready(project, tmp_path)
    failed = prepared.run(ProjectCommand(("python", "-c", "raise SystemExit(7)"), project[0]), timeout=10)
    assert failed.outcome == "exited" and failed.exit_code == 7
    timed = prepared.run(ProjectCommand(("python", "-c", "import time; time.sleep(5)"), project[0]), timeout=0.05)
    assert timed.outcome == "timed_out" and timed.exit_code is None
    huge = prepared.run(ProjectCommand(("python", "-c", "print('a'*2000000)"), project[0]), timeout=10)
    assert huge.outcome == "exited" and len(huge.stdout) <= 65536
    assert huge.output_truncated

    descendant_pid = tmp_path / "detached.pid"
    child_code = (
        "import subprocess,sys; from pathlib import Path; "
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(8)'],start_new_session=True); "
        f"Path({str(descendant_pid)!r}).write_text(str(child.pid)); "
        "print('parent-finished',flush=True)"
    )
    root, target, hatch, _ = project
    watchdog_code = (
        "import time; from pathlib import Path; from specfact_codebase.project_runtime import "
        "ProjectSelection,ProjectCommand,PreparedProject,inspect_project,prepare_project; "
        f"root=Path({str(root)!r}); "
        f"selection=ProjectSelection(environment='review',python={str(target / 'bin/python')!r},hatch={str(hatch)!r}); "
        f"project=prepare_project(inspect_project(root,selection),Path({str(tmp_path / 'watchdog-invocation')!r})); "
        "assert isinstance(project,PreparedProject); "
        "started=time.monotonic(); "
        f"result=project.run(ProjectCommand(('python','-c',{child_code!r}),root),timeout=1.0); "
        "assert time.monotonic()-started < 3, 'project command exceeded bounded pipe drain'; "
        "assert result.outcome=='exited' and result.exit_code==0; "
        "assert 'parent-finished' in result.stdout"
    )
    environment = dict(
        os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[3] / "packages/specfact-codebase/src")
    )
    try:
        subprocess.run(
            [sys.executable, "-c", watchdog_code],
            env=environment,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    finally:
        if descendant_pid.exists():
            with contextlib.suppress(ProcessLookupError):
                os.kill(int(descendant_pid.read_text()), signal.SIGKILL)


def test_source_edits_allowed_but_dependency_drift_requires_reinspection(project, tmp_path):
    prepared = ready(project, tmp_path)
    cmd = ProjectCommand(("python", "-c", "print('ran')"), project[0])
    before = prepared.run(cmd, timeout=10)
    (project[0] / "customer.py").write_text("raise AssertionError\n")
    after = prepared.run(cmd, timeout=10)
    assert after.outcome == "exited" and before.source_identity != after.source_identity
    config = project[0] / "hatch.toml"
    drift_command = ProjectCommand(
        (
            "python",
            "-c",
            "import sys; from pathlib import Path; "
            f"p=Path({str(config)!r}); p.write_text(p.read_text()+'\\n# during execution\\n'); "
            "print('native-drift-stderr', file=sys.stderr)",
        ),
        project[0],
    )
    drift = prepared.run(drift_command, timeout=10)
    assert drift.outcome == "execution_failed"
    assert "changed during execution" in drift.stderr
    assert "native-drift-stderr" in drift.stderr
    config.write_text(config.read_text() + "\n# changed\n")
    stale = prepared.run(cmd, timeout=10)
    assert stale.outcome == "execution_failed"
    assert "reinspect" in stale.stderr.lower()


def test_selected_unsupported_context_rejected_before_native_query(project, tmp_path):
    root, target, hatch, log = project
    config = root / "hatch.toml"
    config.write_text(config.read_text() + '\n[envs.review.env-vars]\nCUSTOM="{root}"\n')
    plan = inspect_project(
        root, ProjectSelection(environment="review", python=str(target / "bin/python"), hatch=str(hatch))
    )
    refused = prepare_project(plan, tmp_path / "invocation")
    assert isinstance(refused, PreparationFailure)
    assert "env-vars" in refused.reason
    assert not log.exists()

    config.write_text("[envs.review]\n")
    empty_plan = inspect_project(
        root, ProjectSelection(environment="review", python=str(target / "bin/python"), hatch=str(hatch))
    )
    empty_result = prepare_project(empty_plan, tmp_path / "empty-invocation")
    assert isinstance(empty_result, PreparationFailure)
    assert "detached" in empty_result.reason
    assert not log.exists()


def test_unrelated_scripts_and_locks_do_not_block_existing_execution(project, tmp_path):
    root = project[0]
    (root / "uv.lock").write_text("unrelated")
    config = root / "hatch.toml"
    config.write_text(config.read_text() + '\n[envs.other]\ntype="custom"\n[envs.review.scripts]\ncheck="python -V"\n')
    assert ready(project, tmp_path).run(ProjectCommand(("python", "-V"), root), timeout=10).exit_code == 0


def test_external_fresh_workspace_required(project, tmp_path):
    root, target, hatch, _ = project
    plan = inspect_project(
        root, ProjectSelection(environment="review", python=str(target / "bin/python"), hatch=str(hatch))
    )
    assert isinstance(prepare_project(plan, root / "owned"), PreparationFailure)
    workspace = tmp_path / "occupied"
    workspace.mkdir()
    (workspace / "unowned").write_text("preserve")
    assert isinstance(prepare_project(plan, workspace), PreparationFailure)
    assert (workspace / "unowned").read_text() == "preserve"


@pytest.mark.parametrize("location", ["inside", "symlink", "external"])
def test_explicit_base_existing_target_excludes_workspace(project, tmp_path, location):
    root, target, hatch, log = project
    prefix = target
    if location == "symlink":
        prefix = tmp_path / "target-link"
        prefix.symlink_to(target, target_is_directory=True)
    workspace = (tmp_path if location == "external" else prefix) / "invocation"
    before = {path.relative_to(target) for path in target.rglob("*")}
    plan = inspect_project(
        root, ProjectSelection(environment="review", python=str(Path(base_executable).resolve()), hatch=str(hatch))
    )
    result = prepare_project(plan, workspace)
    if location == "external":
        assert isinstance(result, PreparedProject), result
        assert (workspace / "completed.json").is_file()
    else:
        assert isinstance(result, PreparationFailure), result
        assert "outside the selected" in result.reason
        assert not workspace.exists()
    assert {path.relative_to(target) for path in target.rglob("*")} == before
    assert "create" not in log.read_text()


def test_project_python_constraint_rejected_before_native_query(project, tmp_path):
    root, target, hatch, log = project
    (root / "pyproject.toml").write_text('[project]\nname="customer"\nversion="0"\nrequires-python=">=3.99"\n')
    plan = inspect_project(
        root, ProjectSelection(environment="review", python=str(target / "bin/python"), hatch=str(hatch))
    )
    result = prepare_project(plan, tmp_path / "invocation")
    assert isinstance(result, PreparationFailure)
    assert "requires-python" in result.reason
    assert not log.exists()


def test_existing_environment_discovered_without_redundant_python_override(project, tmp_path, monkeypatch):
    root, target, hatch, log = project
    plan = inspect_project(root, ProjectSelection(environment="review", hatch=str(hatch)))
    prepared = prepare_project(plan, tmp_path / "invocation")
    assert isinstance(prepared, PreparedProject), prepared
    assert prepared.identity.interpreter.prefix == target
    assert prepared.run(ProjectCommand(("python", "-V"), root), timeout=10).exit_code == 0
    assert "create" not in log.read_text()

    native_which = project_runtime.shutil.which
    monkeypatch.setattr(
        project_runtime.shutil, "which", lambda name: native_which(name) if name == str(hatch) else None
    )
    (root / ".python-version").write_text(f"{sys.version_info.major}.{sys.version_info.minor}\n")
    declared_plan = inspect_project(root, ProjectSelection(environment="review", hatch=str(hatch)))
    declared = prepare_project(declared_plan, tmp_path / "declared-invocation")
    assert isinstance(declared, PreparedProject), declared
    assert declared.identity.interpreter.prefix == target
    (root / ".python-version").unlink()
    config = root / "hatch.toml"
    config.write_text(config.read_text() + f'python="{sys.version_info.major}.{sys.version_info.minor}"\n')
    hatch_plan = inspect_project(root, ProjectSelection(environment="review", hatch=str(hatch)))
    configured = prepare_project(hatch_plan, tmp_path / "configured-invocation")
    assert isinstance(configured, PreparedProject), configured
    assert configured.identity.interpreter.prefix == target


def test_unreadable_inspection_identity_is_diagnostic(project, tmp_path, monkeypatch):
    root, _, hatch, log = project
    blocked = root / "requirements-extra.txt"
    blocked.write_text("customer-dependency\n")
    read_bytes = Path.read_bytes

    def read_or_deny(path):
        if path == blocked:
            raise PermissionError("customer identity unreadable")
        return read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", read_or_deny)
    plan = inspect_project(root, ProjectSelection(environment="review", hatch=str(hatch)))
    assert "customer identity unreadable" in " ".join(plan.diagnostics)
    assert not plan.input_identity
    failed = prepare_project(plan, tmp_path / "invocation")
    assert isinstance(failed, PreparationFailure)
    assert "customer identity unreadable" in failed.reason
    assert not log.exists()


@pytest.mark.parametrize("after_execution", [False, True], ids=["before-command", "after-command"])
def test_unreadable_execution_identity_is_structured(project, tmp_path, monkeypatch, after_execution):
    prepared = ready(project, tmp_path)
    root = project[0]
    marker = tmp_path / "command-ran"
    blocked = root / "hatch.toml"
    read_bytes = Path.read_bytes

    def read_or_deny(path):
        if path == blocked and (not after_execution or marker.exists()):
            raise PermissionError("customer identity unreadable")
        return read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", read_or_deny)
    command = ProjectCommand(
        (
            "python",
            "-c",
            f"import sys; from pathlib import Path; Path({str(marker)!r}).touch(); "
            "print('command-output'); print('native-stderr', file=sys.stderr); "
            "print('x'*65500, file=sys.stderr)",
        ),
        root,
    )
    failed = prepared.run(command, timeout=10)
    assert failed.outcome == "execution_failed"
    assert failed.exit_code is None
    assert "customer identity unreadable" in failed.stderr
    assert marker.exists() is after_execution
    if after_execution:
        assert_captured_failure(failed)
    else:
        assert not failed.stdout
        assert not failed.source_identity


def assert_captured_failure(failed):
    assert failed.stdout == "command-output\n"
    assert "native-stderr" in failed.stderr
    assert len(failed.stderr) <= 65536
    assert failed.output_truncated
    assert failed.source_identity


def test_cleanup_failure_preserves_preparation_failure(project, tmp_path, monkeypatch):
    root, _, hatch, _ = project
    plan = inspect_project(root, ProjectSelection(environment="review", hatch=str(hatch)))
    workspace = tmp_path / "invocation"

    def fail_completion(*args, **kwargs):
        raise OSError("completion metadata cannot be written")

    def fail_cleanup(path):
        assert path == workspace
        raise PermissionError("workspace cleanup denied")

    monkeypatch.setattr(project_runtime.tempfile, "NamedTemporaryFile", fail_completion)
    monkeypatch.setattr(project_runtime.shutil, "rmtree", fail_cleanup)
    failed = prepare_project(plan, workspace)
    assert isinstance(failed, PreparationFailure)
    assert failed.reason == "completion metadata cannot be written"
    assert "workspace cleanup denied" in failed.remedy
    assert str(workspace) in failed.remedy
    assert "fresh" in failed.remedy.lower()
    assert workspace.is_dir()
    assert not (workspace / "completed.json").exists()


def test_custom_hatch_config_is_diagnostic_before_native_query(project, tmp_path, monkeypatch):
    root, _, hatch, log = project
    custom = tmp_path / "global-hatch.toml"
    custom.write_text('mode="project"\n')
    monkeypatch.delenv("HATCH_CONFIG", raising=False)
    earlier_plan = inspect_project(root, ProjectSelection(environment="review", hatch=str(hatch)))
    monkeypatch.setenv("HATCH_CONFIG", str(custom))
    changed_context = prepare_project(earlier_plan, tmp_path / "changed-context")
    assert isinstance(changed_context, PreparationFailure)
    assert "HATCH_CONFIG" in changed_context.reason
    assert not log.exists()
    plan = inspect_project(root, ProjectSelection(environment="review", hatch=str(hatch)))
    assert "HATCH_CONFIG" in " ".join(plan.diagnostics)
    failed = prepare_project(plan, tmp_path / "invocation")
    assert isinstance(failed, PreparationFailure)
    assert "HATCH_CONFIG" in failed.reason
    assert not log.exists()


@pytest.mark.parametrize("mismatch", ["base-prefix", "version"])
def test_absolute_hatch_python_must_match_selected_interpreter(project, tmp_path, monkeypatch, mismatch):
    customer, _, hatch, _ = project
    declared = Path(base_executable).resolve()
    config = customer / "hatch.toml"
    config.write_text(config.read_text() + f"python={json.dumps(str(declared))}\n")
    plan = inspect_project(customer, ProjectSelection(environment="review", hatch=str(hatch)))
    assert not plan.diagnostics

    def mismatched_declaration(executable, cwd):
        facts = probe_python(executable, cwd)
        if executable == declared:
            return (
                replace(facts, base_prefix=tmp_path / "different-base")
                if mismatch == "base-prefix"
                else replace(facts, version=(3, 99, 0))
            )
        return facts

    monkeypatch.setattr(project_runtime, "_probe", mismatched_declaration)
    failed = prepare_project(plan, tmp_path / "invocation")
    assert isinstance(failed, PreparationFailure)
    assert "declared Hatch Python" in failed.reason
    assert "does not match" in failed.reason


def test_numeric_hatch_and_version_file_compare_whole_components(project):
    customer, _, hatch, log = project
    config = customer / "hatch.toml"
    config.write_text(config.read_text() + 'python="3.11.1"\n')
    (customer / ".python-version").write_text("3.11.15\n")
    plan = inspect_project(customer, ProjectSelection(environment="review", hatch=str(hatch)))
    assert "conflicts with .python-version" in " ".join(plan.diagnostics)
    assert not log.exists()
    config.write_text(config.read_text().replace('python="3.11.1"', 'python="3.11"'))
    compatible = inspect_project(customer, ProjectSelection(environment="review", hatch=str(hatch)))
    assert not compatible.diagnostics
    assert not log.exists()


def test_cold_absolute_hatch_python_validates_created_base(project, tmp_path, monkeypatch):
    customer, _, hatch, _ = project
    declared = Path(base_executable).resolve()
    config = customer / "hatch.toml"
    config.write_text(config.read_text() + f"python={json.dumps(str(declared))}\n")
    hatch.write_text(
        f"#!{sys.executable}\nimport os,subprocess,sys\n"
        "if sys.argv[1:]==['env','create','review']:\n"
        f"    subprocess.run([{str(declared)!r},'-m','venv','--without-pip',"
        "os.environ['HATCH_ENV_TYPE_VIRTUAL_PATH']],check=True)\n"
        "print('Hatch, version test' if sys.argv[1:]==['--version'] "
        f"else {str(tmp_path / 'missing-native-target')!r})\n"
    )
    plan = inspect_project(customer, ProjectSelection(environment="review", hatch=str(hatch)))
    assert not plan.diagnostics
    workspace = tmp_path / "invocation"
    target_python = workspace / "environment/bin/python"

    def mismatched_created_target(executable, cwd):
        facts = probe_python(executable, cwd)
        if executable == target_python:
            return replace(facts, base_prefix=tmp_path / "different-created-base")
        return facts

    monkeypatch.setattr(project_runtime, "_probe", mismatched_created_target)
    failed = prepare_project(plan, workspace)
    assert isinstance(failed, PreparationFailure)
    assert "declared Hatch Python" in failed.reason
    assert "does not match" in failed.reason
    assert not (workspace / "completed.json").exists()


@pytest.mark.parametrize("existing", [True, False], ids=["existing", "cold"])
def test_explicit_base_python_must_match_prepared_target(project, tmp_path, monkeypatch, existing):
    customer, target, hatch, _ = project
    selected = Path(base_executable).resolve()
    workspace = tmp_path / "invocation"
    if not existing:
        hatch.write_text(
            f"#!{sys.executable}\nimport os,subprocess,sys\n"
            "if sys.argv[1:]==['env','create','review']:\n"
            f"    subprocess.run([{str(selected)!r},'-m','venv','--without-pip',"
            "os.environ['HATCH_ENV_TYPE_VIRTUAL_PATH']],check=True)\n"
            "print('Hatch, version test' if sys.argv[1:]==['--version'] "
            f"else {str(tmp_path / 'missing-native-target')!r})\n"
        )
        target = workspace / "environment"
    other_base = tmp_path / "different-python-installation"

    def different_target_base(executable, cwd):
        facts = probe_python(executable, cwd)
        return replace(facts, base_prefix=other_base) if executable == target / "bin/python" else facts

    monkeypatch.setattr(project_runtime, "_probe", different_target_base)
    plan = inspect_project(customer, ProjectSelection(environment="review", python=str(selected), hatch=str(hatch)))
    assert not plan.diagnostics
    failed = prepare_project(plan, workspace)
    assert isinstance(failed, PreparationFailure), failed
    assert "selected Python" in failed.reason
    assert "base" in failed.reason
    assert str(other_base) in failed.reason
    assert str(Path(sys.base_prefix).resolve()) in failed.reason
    assert not (workspace / "completed.json").exists()


@pytest.mark.parametrize("mismatch", [False, True], ids=["matching", "wrong-patch"])
def test_explicit_numeric_python_checks_all_requested_components(project, tmp_path, monkeypatch, mismatch):
    customer, target, hatch, log = project
    actual = tuple(sys.version_info[:3])
    requested = (*actual[:2], actual[2] + 1000) if mismatch else actual
    request = ".".join(map(str, requested))
    lookup = "python" + ".".join(map(str, actual[:2]))
    native_which = project_runtime.shutil.which
    monkeypatch.setattr(
        project_runtime.shutil,
        "which",
        lambda name: str(target / "bin/python") if name == lookup else native_which(name),
    )
    plan = inspect_project(customer, ProjectSelection(environment="review", python=request, hatch=str(hatch)))
    prepared = prepare_project(plan, tmp_path / "invocation")
    if mismatch:
        assert isinstance(prepared, PreparationFailure), prepared
        assert request in prepared.reason
        assert str(actual) in prepared.reason
        assert not log.exists()
    else:
        assert isinstance(prepared, PreparedProject), prepared
        assert prepared.identity.interpreter.version == actual
        assert "create" not in log.read_text()


def test_controller_python_startup_removed_and_explicit_override_honored(project, tmp_path, monkeypatch):
    prepared = ready(project, tmp_path)
    startup = {
        "PYTHONOPTIMIZE": "1",
        "PYTHONSTARTUP": "/controller/startup.py",
        "PYTHONUSERBASE": "/controller/user-base",
        "PYTHONSAFEPATH": "1",
        "PYTHONEXECUTABLE": "/controller/python",
        "PYTHONINSPECT": "1",
    }
    for name, value in startup.items():
        monkeypatch.setenv(name, value)
    code = (
        "import os,sys,json\n"
        f"names={list(startup)!r}\n"
        "print(json.dumps([sys.flags.optimize,*[os.getenv(name) for name in names]]))"
    )
    inherited = prepared.run(ProjectCommand(("python", "-c", code), project[0]), timeout=10)
    assert inherited.outcome == "exited" and inherited.exit_code == 0, inherited
    assert json.loads(inherited.stdout) == [0, *[None] * len(startup)]
    explicit = prepared.run(ProjectCommand(("python", "-c", code), project[0], {"PYTHONOPTIMIZE": "1"}), timeout=10)
    assert explicit.outcome == "exited" and explicit.exit_code == 0, explicit
    assert json.loads(explicit.stdout) == [1, "1", *[None] * (len(startup) - 1)]
