"""Execute the hosted gate recipe against a real isolated Git index."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import venv
from pathlib import Path
from string import Template

import yaml


__all__ = [
    "REPO_ROOT",
    "STEP_NAME",
    "_BLOCK2_HATCH_FIXTURE",
    "_DEFERRED_REVIEW_SCRIPT",
    "_ISOLATED_REVIEWER_TEMPLATES",
    "_PREPARATION_CLI_SCRIPT",
    "_TRUSTED_BOOTSTRAP_LAUNCHER",
    "_git",
    "_isolated_reviewer_modules",
    "_write_deferred_fixture_sources",
    "_write_public_report",
    "assert_block2_trace",
    "assert_incomplete_preparation",
    "assert_installed_review_arguments",
    "create_isolated_reviewer",
    "deferral_policy_environment",
    "deferral_worktree",
    "deferred_review_repository",
    "independent_review_job",
    "public_projector",
    "write_public_phase_record_report",
]


REPO_ROOT = Path(__file__).resolve().parents[2]


STEP_NAME = "Run deferred candidate commit review without weakening enforcement"


_DEFERRED_REVIEW_SCRIPT = (
    "import os, subprocess, sys\n"
    "from pathlib import Path\n"
    "assert os.environ['SPECFACT_CODE_REVIEW_ENFORCEMENT'] == 'changed'\n"
    "import tomllib\n"
    "config = Path(os.environ['SPECFACT_CODE_REVIEW_PROJECT_CONFIG'])\n"
    "assert tomllib.loads(config.read_text()) == {'manager': 'hatch', 'environment': 'default'}\n"
    "assert Path(os.environ['SPECFACT_CODE_REVIEW_SUBJECT_ROOT']).resolve() == Path.cwd()\n"
    "assert not {'GITHUB_TOKEN', 'GH_TOKEN', 'PYTHONPATH'} & os.environ.keys()\n"
    "from pathlib import Path\n"
    "cache = Path(os.environ['SPECFACT_CODE_REVIEW_CAPSULE_CACHE'])\n"
    "assert cache == Path(os.environ['CUSTOMER_ROOT']) / 'commit-review-cache'\n"
    "cache.mkdir(parents=True, exist_ok=True)\n"
    "(cache / 'verified-fixture-blob').write_text('fixture')\n"
    "assert sys.argv[1:] == ['packages/example/src/example.py']\n"
    "assert open(sys.argv[1]).read() == 'value = 2\\n'\n"
    "assert subprocess.check_output(['git', 'diff', '--cached', '--name-only'], text=True).strip() == sys.argv[1]\n"
    "assert not subprocess.check_output(['git', 'diff', '--name-only'])\n"
    "raise SystemExit(int(os.environ['FIXTURE_GATE_EXIT']))\n"
)


_PREPARATION_CLI_SCRIPT = (
    "import os,sys,json\n"
    "from pathlib import Path\n"
    "def app(*,args):\n"
    "    assert args[:6] == ['code','review','runtime','prepare','--scope','index']\n"
    "    assert os.environ['SPECFACT_MODULES_REPO'] == os.environ['GITHUB_WORKSPACE']\n"
    "    assert os.environ['SPECFACT_CODE_REVIEW_CAPSULE_CACHE'].endswith('/commit-review-cache')\n"
    "    descriptor=Path(os.environ['CUSTOMER_ROOT'])/'fixture-descriptor.json'\n"
    "    descriptor.write_text('{}')\n"
    "    print(json.dumps({'runtimes':{side:{'descriptor':str(descriptor)} for side in ('base','head')}}))\n"
    "if __name__ == '__main__':\n"
    "    print('SpecFact CLI - v0.55.4')\n"
    "    print('Started: fixture')\n"
    "    app(args=sys.argv[1:])\n"
    "    print('Finished: fixture')\n"
)


_BLOCK2_HATCH_FIXTURE = (
    "\n"
    'uname() { if [[ "${1:-}" == "-m" ]]; then echo arm64; else echo "$FIXTURE_PLATFORM"; fi; }\n'
    "hatch() {\n"
    '  printf \'%s\\n\' "$*" >> "$FIXTURE_CALLS"\n'
    '  if [[ "$*" == *pre_commit_code_review.py* ]]; then return 99; fi\n'
    '  if [[ "$*" == *contract-test-status* ]]; then return 1; fi\n'
    "  return 0\n"
    "}\n"
    "run_block2\n"
)


_TRUSTED_BOOTSTRAP_LAUNCHER = (
    "            import subprocess,sys\n"
    "            from pathlib import Path\n"
    "            result=subprocess.run([sys.executable,*sys.argv[1:]],check=False)\n"
    "            if result.returncode:\n"
    "                raise SystemExit(result.returncode)\n"
    "            target=Path(sys.argv[-1])\n"
    "            site=next((target/'lib').glob('python*/site-packages'))\n"
    "            (site/'pip/__main__.py').write_text(\n"
    "                \"import sys\\nassert sys.argv[1:]==['install','--no-cache-dir','specfact-cli==0.55.4']\\n\"\n"
    "            )\n"
    "            core=site/'specfact_cli'\n"
    "            core.mkdir()\n"
    "            (core/'__init__.py').write_text('')\n"
    "            (core/'cli.py').write_text(\n"
    "                \"import sys\\nassert sys.argv[1:]==['module','install','nold-ai/specfact-code-review',\"\n"
    "                \"'--scope','user','--version','0.51.2','--source','marketplace']\\n\"\n"
    "            )\n"
    "            "
)


_ISOLATED_REVIEWER_TEMPLATES = {
    "specfact_cli/__init__.py": "",
    "specfact_cli/cli.py": "import os,json\n"
    "from pathlib import Path\n"
    "root=Path(os.environ['HOME']).parent\n"
    "assert Path.cwd() == root, 'core discovery entered the candidate subject'\n"
    "assert not "
    "{'PYTHONPATH','GITHUB_TOKEN','GH_TOKEN','SPECFACT_MODULES_ROOTS','SPECFACT_ALLOW_UNSIGNED'} "
    "& os.environ.keys()\n"
    "def app(*,args):\n"
    "    assert Path.cwd() == root/'subject'\n"
    "    (root/'argv.json').write_text(json.dumps(args))\n"
    "    raise SystemExit($REVIEW_EXIT)\n",
    "specfact_cli/registry/__init__.py": "import os\n"
    "from pathlib import Path\n"
    "class CommandRegistry:\n"
    "    @classmethod\n"
    "    def get_module_typer(cls,name):\n"
    "        root=Path(os.environ['HOME']).parent\n"
    "        assert name=='code' and Path.cwd()==root\n"
    "        (root/'preloaded').touch()\n",
    "specfact_code_review/__init__.py": "",
    "specfact_code_review/run/__init__.py": "",
    "specfact_code_review/run/portable_snapshot.py": "def "
    "discover_snapshot(root,*,config_path,source_snapshot):\n"
    "    assert root==source_snapshot.root and "
    "config_path.is_file()\n"
    "    return source_snapshot\n",
    "specfact_code_review/run/runtime_builder.py": "import os\n"
    "from pathlib import Path\n"
    "def prepare_runtime(plan,*,runtime):\n"
    "    root=Path(os.environ['HOME']).parent\n"
    "    assert (root/'preloaded').exists()\n"
    "    with (root/'prepared').open('a') as out: "
    "out.write(plan.root.name+'\\n')\n",
    "specfact_code_review/run/runtime_interpreter.py": "def select_environment(plan,*,current): return current\n",
    "specfact_code_review/run/runner.py": "def _capsule_environment_id(): return 'linux-x86_64-cp312'\n"
    "def _prepare_capsule_runtime(*,environment_id): return object(),''\n"
    "def _cleanup_capsule_runtime(runtime): pass\n",
    "specfact_code_review/run/scope.py": "from types import SimpleNamespace\n"
    "def ScopeRequest(**kw): return SimpleNamespace(**kw)\n"
    "def resolve_scope(request):\n"
    "    assert request.scope=='index' and "
    "request.portable_project_runtime\n"
    "    return "
    "SimpleNamespace(status=$STATUS,reason=$REASON,selected_paths=$SELECTED_PATHS,"
    "ci_exit_code=$SCOPE_EXIT,base_snapshot=SimpleNamespace(root=request.repository/'base'),"
    "head_snapshot=SimpleNamespace(root=request.repository/'head'))\n"
    "def cleanup_scope_resolution(resolution):\n"
    "    import os\n    from pathlib import Path\n"
    "    (Path(os.environ['HOME']).parent/'cleaned').touch()\n",
}


_FIXED_ANALYZER_FINDING_ROWS = [
    {
        "file": "public.py",
        "line": 1,
        "severity": "error",
        "category": "clean_code",
        "tool": "radon",
        "rule": "CC34",
        "message": "PRIVATE_MESSAGE",
    },
    {
        "file": "public.py",
        "line": 2,
        "severity": "error",
        "category": "tool_error",
        "tool": "semgrep",
        "rule": "tool_error",
        "message": "TimeoutExpired PRIVATE_SECRET",
    },
    {
        "file": "public.py",
        "line": 3,
        "severity": "error",
        "category": "PRIVATE_CATEGORY",
        "tool": "PRIVATE_TOOL",
        "rule": "PRIVATE_RULE",
        "message": "PRIVATE_SECRET",
    },
]


_DEPTH_FAILURE_FINDING_ROWS = [
    {
        "file": "public.py",
        "line": 1,
        "severity": "error",
        "category": "tool_error",
        "tool": "semgrep",
        "message": "semgrep returned structured errors; details=DECODER_DEPTH_FAILURE",
    }
]


def _write_public_report(root, findings):
    _git(root, "init", "-q")
    (root / "public.py").write_text("value = 1\n")
    _git(root, "add", "public.py")
    report = root / ".specfact/code-review.json"
    report.parent.mkdir()
    report.write_text(json.dumps({"findings": findings}))


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def _write_deferred_fixture_sources(repository):
    target = repository / "packages/example/src/example.py"
    target.parent.mkdir(parents=True)
    target.write_text("value = 1\n")
    unrelated = target.with_name("unrelated.py")
    unrelated.write_text("value = 1\n")
    script = repository / "scripts/pre_commit_code_review.py"
    script.parent.mkdir()
    script.write_text(_DEFERRED_REVIEW_SCRIPT)
    controller = repository / "packages/specfact-code-review/src/specfact_cli"
    controller.mkdir(parents=True)
    (controller / "__init__.py").write_text("")
    (controller / "cli.py").write_text(_PREPARATION_CLI_SCRIPT)
    return target, unrelated


def deferred_review_repository(tmp_path: Path, advanced_dev: bool):
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.email", "fixture@example.invalid")
    _git(repository, "config", "user.name", "Fixture")
    target, unrelated = _write_deferred_fixture_sources(repository)
    _git(repository, "add", ".")
    _git(repository, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture base")
    base = _git(repository, "rev-parse", "HEAD")
    target.write_text("value = 2\n")
    _git(repository, "add", ".")
    _git(repository, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture candidate")
    head = _git(repository, "rev-parse", "HEAD")
    if advanced_dev:
        _git(repository, "checkout", "-qb", "dev", base)
        unrelated.write_text("value = 3\n")
        _git(repository, "add", ".")
        _git(repository, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture advanced dev")
        base = _git(repository, "rev-parse", "HEAD")
        _git(repository, "checkout", "--detach", head)
    return repository, base, head


def _write_deferral_baseline(repository, candidate_path, independent_review):
    workflow = repository / ".github/workflows/capsule-customer-execution.yml"
    workflow.parent.mkdir(parents=True)
    workflow_source = (REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text()
    workflow.write_text(
        workflow_source if independent_review else workflow_source.split("\n  independent-review:", 1)[0]
    )
    files = [
        "llms.txt",
        "docs/reference/commands.generated.json",
        "docs/reference/commands.generated.md",
        candidate_path,
        "openspec/changes/example/spec.md",
        "tests/unit/test_check_prompt_commands_script.py",
    ]
    for relative in files:
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("baseline\n")
    orchestrator = repository / ".github/workflows/pr-orchestrator.yml"
    orchestrator_source = (REPO_ROOT / ".github/workflows/pr-orchestrator.yml").read_text()
    orchestrator.write_text(
        orchestrator_source + "\n# Baseline routing fixture.\n"
        if candidate_path == ".github/workflows/pr-orchestrator.yml"
        else orchestrator_source
    )
    capsule_manifest = repository / "packages/specfact-code-review/module-package.yaml"
    capsule_manifest.parent.mkdir(parents=True, exist_ok=True)
    capsule_manifest.write_text("version: 1\n")
    checker = repository / "scripts/validate_capsule_ci_schedule.py"
    checker.parent.mkdir()
    checker.write_bytes((REPO_ROOT / "scripts/validate_capsule_ci_schedule.py").read_bytes())
    return files[-3:], capsule_manifest


def deferral_worktree(tmp_path: Path, scenario, *, schedule_mutation=None, restore_schedule=False):
    candidate_path, advanced_dev, independent_review = scenario[3:6]
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.email", "fixture@example.invalid")
    _git(repository, "config", "user.name", "Fixture")
    candidate_files, capsule_manifest = _write_deferral_baseline(repository, candidate_path, independent_review)
    _git(repository, "add", ".")
    _git(repository, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture base")
    _git(repository, "update-ref", "refs/remotes/origin/dev", "HEAD")
    worktree = tmp_path / "worktree"
    _git(repository, "worktree", "add", "-qb", "codex/fixture", str(worktree))
    if advanced_dev:
        capsule_manifest.write_text("version: 2\n")
        _git(repository, "add", ".")
        _git(repository, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture advanced dev")
        _git(repository, "update-ref", "refs/remotes/origin/dev", "HEAD")
    _stage_deferral_candidate(
        worktree,
        candidate_files,
        independent_review,
        schedule_mutation,
        restore_schedule,
    )
    return worktree


def _stage_deferral_candidate(
    worktree,
    candidate_files,
    independent_review,
    schedule_mutation,
    restore_schedule,
):
    orchestrator_source = (REPO_ROOT / ".github/workflows/pr-orchestrator.yml").read_text()
    workflow_source = (REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text()
    for relative in candidate_files:
        (worktree / relative).write_text(
            orchestrator_source if relative == ".github/workflows/pr-orchestrator.yml" else "candidate\n"
        )
    if independent_review == "unstaged_restore":
        (worktree / ".github/workflows/capsule-customer-execution.yml").write_text(
            workflow_source.split("\n  independent-review:", 1)[0]
        )
    if schedule_mutation:
        staged_schedule = yaml.load(orchestrator_source, Loader=yaml.BaseLoader)
        schedule_mutation(staged_schedule)
        (worktree / ".github/workflows/pr-orchestrator.yml").write_text(yaml.safe_dump(staged_schedule))
    _git(worktree, "add", ".")
    if restore_schedule:
        (worktree / ".github/workflows/pr-orchestrator.yml").write_text(orchestrator_source)
    if independent_review == "unstaged_restore":
        (worktree / ".github/workflows/capsule-customer-execution.yml").write_text(workflow_source)


def assert_block2_trace(invoked, expected, stderr):
    for command in [
        "generate-command-overview",
        "check-command-overview",
        "check-command-contract",
        "check-core-documentation-accountability",
        "check-docs-commands.py",
        "check-prompt-commands.py",
        "requirements_evidence_gate.py --staged",
    ]:
        assert command in invoked
    assert "pre_commit_code_review.py" not in invoked
    if expected == 0:
        assert "DEFERRED" in stderr
        assert "mandatory exact-head GitHub Linux CI; this is not a PASS" in stderr
        assert "contract-test-contracts" in invoked
    else:
        assert "Capsule review deferral" in stderr


def independent_review_job():
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    return workflow["jobs"].get("independent-review")


def _isolated_reviewer_modules(review_case, *, selected_paths=None, scope_exit=None):
    review_exit, preparation_status, fixture_reason = review_case
    replacements = {
        "REVIEW_EXIT": str(review_exit),
        "STATUS": repr(preparation_status),
        "REASON": repr(fixture_reason),
        "SELECTED_PATHS": repr([] if preparation_status == "NOT_APPLICABLE" else ["governed.py"])
        if selected_paths is None
        else repr(selected_paths),
        "SCOPE_EXIT": str(0 if preparation_status in {"PASS", "NOT_APPLICABLE"} else 1)
        if scope_exit is None
        else str(scope_exit),
    }
    return {name: Template(source).substitute(replacements) for name, source in _ISOLATED_REVIEWER_TEMPLATES.items()}


def create_isolated_reviewer(tmp_path: Path, review_case, *, selected_paths=None, scope_exit=None):
    trusted = tmp_path / "trusted"
    for name in ("home", "tmp", "subject"):
        (trusted / name).mkdir(parents=True)
    venv.create(trusted / "venv", with_pip=False)
    interpreter = trusted / "venv/bin/python"
    site = Path(
        subprocess.check_output(
            [str(interpreter), "-I", "-c", "import sysconfig;print(sysconfig.get_path('purelib'))"], text=True
        ).strip()
    )
    modules = _isolated_reviewer_modules(review_case, selected_paths=selected_paths, scope_exit=scope_exit)
    for name, content in modules.items():
        path = site / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    fake = trusted / "subject/specfact_cli"
    fake.mkdir()
    (fake / "__init__.py").write_text("raise AssertionError('candidate import attempted')")
    (trusted / "project.toml").write_text('manager = "hatch"\nenvironment = "default"\n')
    environment = os.environ | {
        "TRUSTED_ROOT": str(trusted),
        "GITHUB_TOKEN": "fixture-unused",
        "GH_TOKEN": "fixture-unused",
        "PYTHONPATH": str(trusted / "subject"),
        "SPECFACT_MODULES_ROOTS": str(trusted / "subject"),
        "SPECFACT_ALLOW_UNSIGNED": "1",
    }
    return trusted, environment


def assert_incomplete_preparation(trusted: Path, result, fixture_reason: str):
    assert not (trusted / "argv.json").exists()
    assert not (trusted / "prepared").exists()
    diagnostic = json.loads((trusted / "status.public.json").read_text())
    assert diagnostic == {
        "status": "INCOMPLETE",
        "phase": "trusted_index_preparation",
        "diagnostic": fixture_reason if fixture_reason == "policy_parse_failure" else "unstructured_reason",
    }
    assert diagnostic["diagnostic"] in result.stdout
    if fixture_reason != "policy_parse_failure":
        assert fixture_reason not in result.stdout


def assert_installed_review_arguments(trusted: Path, *, prepared: bool = True):
    if prepared:
        assert (trusted / "prepared").read_text().splitlines() == ["base", "head"]
    else:
        assert not (trusted / "prepared").exists()
    args = json.loads((trusted / "argv.json").read_text())
    assert args[:3] == ["code", "review", "run"]
    assert args[args.index("--scope") + 1] == "index"
    assert args[args.index("--enforcement") + 1] == "changed"
    assert "--bug-hunt" in args


def public_projector(job_name):
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    name = STEP_NAME if job_name == "customer" else "Prepare and review through the authenticated installed controller"
    recipe = next(step["run"] for step in workflow["jobs"][job_name]["steps"] if step.get("name") == name)
    return recipe.rsplit("- <<'PY'", 1)[1].split("\n", 1)[1].split("\nPY\n", 1)[0]


def write_public_phase_record_report(root, nodeid, detail):
    finding = {
        "file": "public.py",
        "line": 1,
        "severity": "error",
        "category": "testing",
        "tool": "pytest",
        "rule": "TEST_OUTCOME_NOT_PASS",
        "message": f"Test {nodeid} failed during call.",
    }
    _write_public_report(root, [finding])
    (root / "public.py").write_text("def test_public_case():\n    pass\n")
    report = root / ".specfact/code-review.json"
    data = json.loads(report.read_text())
    records = [
        {"nodeid": nodeid, "phase": "setup", "outcome": "failed", "detail": "E PermissionError: PRIVATE_SETUP"},
        {"nodeid": nodeid, "phase": "call", "outcome": "failed", "detail": detail},
    ]
    data["analyzer_evidence"] = [{"id": "targeted-pytest-coverage", "target_execution": {"records": records}}]
    report.write_text(json.dumps(data))


def deferral_policy_environment(worktree: Path) -> dict[str, str]:
    interpreter = (Path(sys.base_prefix) / "bin/python3").resolve()
    assert interpreter.is_file()
    assert not interpreter.is_relative_to(REPO_ROOT)
    assert not interpreter.is_relative_to(worktree)
    return {
        "SPECFACT_CODE_REVIEW_POLICY_COMMIT": _git(worktree, "rev-parse", "HEAD"),
        "SPECFACT_CODE_REVIEW_POLICY_PYTHON": str(interpreter),
    }


def write_preparation_fixture(tmp_path, case):

    descriptor = tmp_path / "descriptor.json"
    descriptor.write_text("{}")
    payload = {"runtimes": {side: {"descriptor": str(descriptor)} for side in ("base", "head")}}
    if case.startswith("not_applicable"):
        payload = {"scope": "index", "status": "NOT_APPLICABLE", "diagnostic": "no_governed_impact", "runtimes": {}}
        overrides = {
            "not_applicable_reason": {"diagnostic": "private-reason"},
            "not_applicable_scope": {"scope": "full"},
            "not_applicable_runtimes": {"runtimes": ["private"]},
            "not_applicable_nonempty": {"runtimes": {"head": {"descriptor": str(descriptor)}}},
        }
        payload.update(overrides.get(case, {}))
    elif case == "missing_base":
        payload["runtimes"].pop("base")
    elif case == "missing_files":
        descriptor.unlink()
    report = tmp_path / "preparation.private.json"
    report.write_text("not-json/private" if case == "invalid" else json.dumps(payload))
    return report


SOURCE_PUBLISH_STEP = "Publish installed controller source observation"
SOURCE_INVOCATIONS = ("preparation", "review")
SOURCE_CANARY = "PRIVATE_SOURCE_CANARY:/private/source --private-argument"


def source_unavailable(invocation):
    return {"phase": "installed_controller_source", "invocation": invocation, "status": "unavailable"}


def source_observed(invocation, digests):
    return source_unavailable(invocation) | {
        "status": "observed",
        "identity_kind": "authenticated_source_and_loaded_origins",
        "runner_sha256": digests["runner"],
        "sandbox_sha256": digests["sandbox"],
    }


def run_source_publication(trusted, environment):
    steps = [step for step in independent_review_job()["steps"] if step.get("name") == SOURCE_PUBLISH_STEP]
    if not steps:
        return subprocess.CompletedProcess([], 0, "", "")
    assert len(steps) == 1
    return subprocess.run(
        ["bash", "-c", "set -euo pipefail\n" + steps[0]["run"]],
        cwd=trusted.parent,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )


def run_independent_source_command(trusted, environment):
    step = next(step for step in independent_review_job()["steps"] if step.get("id") == "independent_review")
    return subprocess.run(
        ["bash", "-c", step["run"]],
        cwd=trusted.parent,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )


_SYNTHETIC_SOURCE_CASE_CODE = {
    "valid": "",
    "other_version": "",
    "cache_present": "(sources/'__pycache__').mkdir(exist_ok=True)\n(sources/'__pycache__/unrelated.pyc').write_bytes(b'cache')",
    "verifier_false": "",
    "verifier_exception": "",
    "manifest_drift": "",
    "runner_drift": "",
    "sandbox_drift": "",
    "manifest_replace": "",
    "wrong_name": "",
    "invalid_metadata": "",
    "missing_key": "key.unlink()",
    "oversized_key": "key.write_bytes(b'K'*(64*1024+1))",
    "missing_runner": "sys.modules.pop(runner.__name__)",
    "missing_sandbox": "sys.modules.pop(sandbox.__name__)",
    "missing_spec": "sandbox.__spec__=None",
    "runner_file": "runner.__file__=str(root/'PRIVATE_SOURCE_CANARY.py')",
    "sandbox_file": "sandbox.__file__=runner.__file__",
    "runner_origin": "runner.__spec__.origin=sandbox.__file__",
    "sandbox_origin": "sandbox.__spec__.origin=runner.__file__",
    "relative_origin": "sandbox.__spec__.origin='sandbox.py'",
    "relative_file": "runner.__file__='runner.py'",
    "bytecode_origin": "sandbox.__spec__.origin=str(sources/'__pycache__/sandbox.pyc')",
    "missing_bindings": "del runner.execute_launch_plan\ndel sandbox.execute_launch_plan",
    "noncallable_binding": "runner.execute_launch_plan=sandbox.execute_launch_plan=None",
    "shared_string_binding": "runner.execute_launch_plan=sandbox.execute_launch_plan='PRIVATE_SOURCE_CANARY'",
    "different_binding": "runner.execute_launch_plan=lambda: None",
    "missing_source": "(sources/'sandbox.py').unlink()",
    "directory_source": "(sources/'sandbox.py').unlink()\n(sources/'sandbox.py').mkdir()",
    "fifo_source": "(sources/'sandbox.py').unlink()\nos.mkfifo(sources/'sandbox.py')",
    "oversized_source": "(sources/'sandbox.py').write_bytes(b'x'*(4*1024*1024+1))",
    "oversized_manifest": "manifest.write_bytes(b'x'*(256*1024+1))",
    "symlink_source": "original=sources/'sandbox.py'\noriginal.rename(sources/'original.py')\noriginal.symlink_to(sources/'original.py')",
    "symlink_descendant": "original=package/'src'\noriginal.rename(package/'original-src')\noriginal.symlink_to(package/'original-src',target_is_directory=True)",
    "symlink_package": "package.rename(package.with_name('original-package'))\npackage.symlink_to(package.with_name('original-package'),target_is_directory=True)",
    "receipt_write_error": "os.replace=lambda *args,**kwargs: (_ for _ in ()).throw(OSError('PRIVATE_SOURCE_CANARY'))",
    "observer_error": "def broken_key():\n    raise OSError('PRIVATE_SOURCE_CANARY')\nmodule_installer._bundled_public_key_path=broken_key",
    "distinct_invocations": "",
}


def _synthetic_source_installation(trusted, case):
    import shutil
    import sysconfig

    from specfact_cli.models import module_package

    interpreter = trusted / "venv/bin/python"
    site = Path(
        subprocess.check_output(
            [str(interpreter), "-I", "-c", "import sysconfig;print(sysconfig.get_path('purelib'))"], text=True
        ).strip()
    )
    package = trusted / "home/.specfact/modules/specfact-code-review"
    package.mkdir(parents=True)
    (package / "src").mkdir()
    shutil.move(str(site / "specfact_code_review"), str(package / "src/specfact_code_review"))
    (site / "synthetic-dependencies.pth").write_text(str(package / "src") + "\n" + sysconfig.get_path("purelib") + "\n")
    model_dir = site / "specfact_cli/models"
    model_dir.mkdir()
    (model_dir / "__init__.py").write_text("")
    shutil.copyfile(module_package.__file__, model_dir / "module_package.py")
    metadata = {"name": "nold-ai/specfact-code-review", "version": "0.51.2", "commands": ["code"]}
    if case == "other_version":
        metadata["version"] = "0.51.99"
    if case == "wrong_name":
        metadata["name"] = "nold-ai/other-module"
    if case == "invalid_metadata":
        metadata["version"] = None
    (package / "module-package.yaml").write_text(yaml.safe_dump(metadata))
    key = site / "specfact_cli/bundled.pem"
    key.write_text("SYNTHETIC_BUNDLED_PEM\n")
    return site, package


def _synthetic_source_verifier(site, case):
    installer = site / "specfact_cli/registry/module_installer.py"
    installer.write_text(
        "import json,os\nfrom pathlib import Path\n"
        "from specfact_cli.models.module_package import ModulePackageMetadata\n"
        "USER_MODULES_ROOT=Path(os.environ['HOME'])/'.specfact/modules'\n"
        f"CASE={case!r}\n"
        "def _bundled_public_key_path(): return Path(__file__).parents[1]/'bundled.pem'\n"
        "def verify_module_artifact(package,meta,**kwargs):\n"
        "    root=Path(os.environ['HOME']).parent\n"
        "    assert isinstance(meta,ModulePackageMetadata)\n"
        "    with (root/'verifier-calls.jsonl').open('a') as out:\n"
        "        out.write(json.dumps({'package':str(package),'metadata':meta.model_dump(),**kwargs})+'\\n')\n"
        "    if CASE=='verifier_exception': raise ValueError('PRIVATE_SOURCE_CANARY')\n"
        "    targets={'manifest_drift':'module-package.yaml','runner_drift':'src/specfact_code_review/run/runner.py',"
        "'sandbox_drift':'src/specfact_code_review/run/sandbox.py'}\n"
        "    if CASE in targets:\n"
        "        with (package/targets[CASE]).open('a') as out: out.write('\\n# drift\\n')\n"
        "    if CASE=='manifest_replace':\n"
        "        manifest=package/'module-package.yaml'\n"
        "        replacement=package/'replacement.yaml'\n"
        "        replacement.write_bytes(manifest.read_bytes())\n"
        "        replacement.replace(manifest)\n"
        "    return CASE!='verifier_false'\n"
    )


def _synthetic_source_subject_entry(sources, case):
    setup = (
        "import json,os,sys\nfrom pathlib import Path\n"
        "from specfact_cli.registry import module_installer\n"
        "from specfact_code_review.run import runner,sandbox\n"
        "root=Path(os.environ['HOME']).parent\n"
        "package=module_installer.USER_MODULES_ROOT/'specfact-code-review'\n"
        "sources=package/'src/specfact_code_review/run'\n"
        "manifest=package/'module-package.yaml'\n"
        "key=module_installer._bundled_public_key_path()\n" + _SYNTHETIC_SOURCE_CASE_CODE[case] + "\n"
        "original_chdir=os.chdir\n"
        "def subject_entry(path):\n"
        "    invocation='preparation' if sys.argv[2]=='prepare-index' else 'review'\n"
        "    receipt=root/f'controller-source-{invocation}.private.json'\n"
        "    entry={'cwd':str(Path.cwd()),'receipt':receipt.read_text() if receipt.is_file() else None}\n"
        "    (root/f'entry-{invocation}.json').write_text(json.dumps(entry))\n"
        "    original_chdir(path)\n"
        "os.chdir=subject_entry\n"
    )
    scope = sources / "scope.py"
    scope.write_text(scope.read_text() + setup)
    if case == "distinct_invocations":
        scope.write_text(
            scope.read_text() + "original_cleanup=cleanup_scope_resolution\n"
            "def cleanup_scope_resolution(resolution):\n"
            "    original_cleanup(resolution)\n"
            "    with (sources/'sandbox.py').open('a') as out: out.write('# review source\\n')\n"
        )


def synthetic_installed_source_reviewer(tmp_path, case="valid", review_case=(0, "PASS", "")):
    import hashlib

    trusted, environment = create_isolated_reviewer(tmp_path, review_case)
    site, package = _synthetic_source_installation(trusted, case)
    _synthetic_source_verifier(site, case)
    sources = package / "src/specfact_code_review/run"
    (sources / "sandbox.py").write_text("def execute_launch_plan(): return None\n")
    runner = sources / "runner.py"
    runner.write_text(runner.read_text() + "from .sandbox import execute_launch_plan\n")
    _synthetic_source_subject_entry(sources, case)
    expected = {
        name: hashlib.sha256((sources / f"{name}.py").read_bytes()).hexdigest() for name in ("runner", "sandbox")
    }
    (trusted / "subject/module-package.yaml").write_text("PRIVATE_SOURCE_CANARY")
    (trusted / "subject/tempting.pem").write_text("PRIVATE_SOURCE_CANARY")
    environment["SPECFACT_MODULE_PUBLIC_KEY"] = str(trusted / "subject/tempting.pem")
    environment["CONTROLLER_SOURCE_RECEIPT"] = str(trusted / "subject/tempting.json")
    return trusted, environment, expected
