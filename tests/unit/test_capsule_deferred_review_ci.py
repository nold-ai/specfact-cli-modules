"""Execute the hosted gate recipe against a real isolated Git index."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import venv
from pathlib import Path
from string import Template

import pytest
import yaml


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
    "import os,sys\n"
    "assert sys.argv[1:7] == ['code','review','runtime','prepare','--scope','index']\n"
    "assert os.environ['SPECFACT_MODULES_REPO'] == os.environ['GITHUB_WORKSPACE']\n"
    "assert os.environ['SPECFACT_CODE_REVIEW_CAPSULE_CACHE'].endswith('/commit-review-cache')\n"
    "print('{}')\n"
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
    "                \"'--scope','user','--version','0.51.0','--source','marketplace']\\n\"\n"
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
    "SimpleNamespace(status=$STATUS,reason=$REASON,base_snapshot=SimpleNamespace(root=request.repository/'base'),head_snapshot=SimpleNamespace(root=request.repository/'head'))\n"
    "def cleanup_scope_resolution(resolution): pass\n",
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


def _deferred_review_repository(tmp_path: Path, advanced_dev: bool):
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


@pytest.mark.parametrize("gate_exit", [0, 7])
@pytest.mark.parametrize("advanced_dev", [False, True])
def test_deferred_gate_reviews_exact_staged_tree_and_propagates_failure(
    tmp_path: Path, gate_exit: int, advanced_dev: bool
) -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    steps = workflow["jobs"]["customer"]["steps"]
    step = next((item for item in steps if item.get("name") == STEP_NAME), None)
    assert step is not None, "No blocking candidate commit review runs in hosted Linux CI"
    assert step["if"] == "github.event_name == 'pull_request' && matrix.python == '3.12'"
    assert not step.get("continue-on-error", False)
    assert steps.index(step) > next(
        i for i, item in enumerate(steps) if item.get("name", "").startswith("Allow user namespaces")
    )
    repository, base, head = _deferred_review_repository(tmp_path, advanced_dev)
    customer = tmp_path / "customer"
    (customer / "cache").mkdir(parents=True)
    venv.create(customer / "venv", with_pip=False)
    environment = os.environ | {
        "CUSTOMER_ROOT": str(customer),
        "GITHUB_WORKSPACE": str(repository),
        "CANDIDATE_HEAD": head,
        "CANDIDATE_BASE": base,
        "FIXTURE_GATE_EXIT": str(gate_exit),
        "GITHUB_TOKEN": "fixture-unused",
        "GH_TOKEN": "fixture-unused",
    }
    result = subprocess.run(
        ["bash", "-c", step["run"]], cwd=repository, env=environment, capture_output=True, text=True, check=False
    )
    assert result.returncode == gate_exit, result.stdout + result.stderr
    from specfact_code_review.run.runtime_discovery import discover_project

    plan = discover_project(REPO_ROOT, config_path=customer / "commit-review-project.toml")
    assert (plan.manager, plan.environment) == ("hatch", "default")
    assert not list((customer / "cache").iterdir())
    assert _git(repository, "rev-parse", "HEAD") == head
    assert not _git(repository, "status", "--porcelain")


def _deferral_worktree(tmp_path: Path, scenario):
    _platform, _ci, _deferral, bundle, advanced_dev, independent_review, _expected = scenario
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.email", "fixture@example.invalid")
    _git(repository, "config", "user.name", "Fixture")
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
        f"packages/{bundle}/resources/example.py",
        "openspec/changes/example/spec.md",
    ]
    for relative in files:
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("baseline\n")
    capsule_manifest = repository / "packages/specfact-code-review/module-package.yaml"
    capsule_manifest.parent.mkdir(parents=True, exist_ok=True)
    capsule_manifest.write_text("version: 1\n")
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
    for relative in files[-2:]:
        (worktree / relative).write_text("candidate\n")
    if independent_review == "unstaged_restore":
        (worktree / ".github/workflows/capsule-customer-execution.yml").write_text(
            workflow_source.split("\n  independent-review:", 1)[0]
        )
    _git(worktree, "add", ".")
    if independent_review == "unstaged_restore":
        (worktree / ".github/workflows/capsule-customer-execution.yml").write_text(workflow_source)
    return worktree


def _assert_block2_trace(invoked, expected, stderr):
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
        assert "contract-test-contracts" in invoked
    else:
        assert "Capsule review deferral" in stderr


@pytest.mark.parametrize(
    "scenario",
    [
        ("Darwin", "", "github-linux", "specfact-code-review", False, True, 0),
        ("Darwin", "", "github-linux", "specfact-code-review", False, False, 1),
        ("Darwin", "", "github-linux", "specfact-code-review", False, "unstaged_restore", 1),
        ("Darwin", "true", "github-linux", "specfact-code-review", False, True, 1),
        ("Linux", "", "github-linux", "specfact-code-review", False, True, 1),
        ("Darwin", "", "invalid", "specfact-code-review", False, True, 1),
        ("Darwin", "", "github-linux", "specfact-project", False, True, 1),
        ("Darwin", "", "github-linux", "specfact-project", True, True, 1),
    ],
)
def test_narrow_local_deferral_retains_block2_and_cannot_run_in_ci(tmp_path: Path, scenario) -> None:
    platform, ci, deferral, _bundle, _advanced_dev, _independent_review, expected = scenario
    worktree = _deferral_worktree(tmp_path, scenario)
    calls = tmp_path / "calls"
    script = (REPO_ROOT / "scripts/pre-commit-quality-checks.sh").read_text().rsplit('main "$@"', 1)[0]
    recipe = script + _BLOCK2_HATCH_FIXTURE
    environment = os.environ | {
        "FIXTURE_PLATFORM": platform,
        "FIXTURE_CALLS": str(calls),
        "GITHUB_ACTIONS": ci,
        "CI": ci,
        "SPECFACT_CODE_REVIEW_DEFER_TO_CI": deferral,
    }
    result = subprocess.run(
        ["bash", "-c", recipe], cwd=worktree, env=environment, capture_output=True, text=True, check=False
    )
    assert result.returncode == expected, result.stdout + result.stderr
    invoked = calls.read_text()
    _assert_block2_trace(invoked, expected, result.stderr)


def test_hosted_preparation_has_separate_bound_and_cannot_bypass_review() -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    step = next(item for item in workflow["jobs"]["customer"]["steps"] if item.get("name") == STEP_NAME)
    recipe = step["run"]
    assert "timeout=1800" in recipe
    assert "code review runtime prepare --scope index" in recipe
    assert recipe.index("code review runtime prepare --scope index") < recipe.index("review_exit=0")
    assert 'SPECFACT_CODE_REVIEW_CAPSULE_CACHE="$CUSTOMER_ROOT/commit-review-cache"' in recipe
    assert "continue-on-error" not in step


def _independent_review_job():
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    return workflow["jobs"].get("independent-review")


def test_independent_reviewer_runs_in_fresh_job_without_candidate_host_code() -> None:
    independent = _independent_review_job()
    assert independent is not None, "Installed reviewer must not share writable venv/HOME with candidate host code"
    assert independent["runs-on"] == "ubuntu-24.04"
    assert independent["if"] == "github.event_name == 'pull_request'"
    assert not independent.get("needs"), "Candidate execution cannot suppress the independent review job"
    recipe = "\n".join(str(step.get("run", "")) for step in independent["steps"])
    assert "specfact-cli==0.55.4" in recipe
    assert "--version 0.51.0" in recipe
    assert "--source marketplace" in recipe
    assert "env -i" in recipe


@pytest.mark.parametrize(
    "forbidden",
    [
        "pre_commit_code_review.py",
        "link_dev_module.py",
        "SPECFACT_MODULES_ROOTS",
        "SPECFACT_ALLOW_UNSIGNED",
        "$GITHUB_WORKSPACE/scripts",
    ],
)
def test_independent_reviewer_excludes_each_candidate_host_route(forbidden: str) -> None:
    independent = _independent_review_job()
    recipe = "\n".join(str(step.get("run", "")) for step in independent["steps"])
    assert forbidden not in recipe


def test_independent_reviewer_preserves_scope_budgets_and_preload_order() -> None:
    independent = _independent_review_job()
    recipe = "\n".join(str(step.get("run", "")) for step in independent["steps"])
    assert "timeout=300" in recipe and "timeout=1800" in recipe
    assert "--scope index --enforcement changed --bug-hunt" in recipe
    assert "discover_snapshot" in recipe and "prepare_runtime" in recipe
    assert "runtime prepare --project-config" not in recipe, "Mutable worktree prep cannot prewarm index identities"
    assert 'CommandRegistry.get_module_typer("code")' in recipe
    assert recipe.index('CommandRegistry.get_module_typer("code")') < recipe.index("os.chdir(sys.argv[1])")


def test_independent_reviewer_cannot_continue_after_failure_or_retain_credentials() -> None:
    for step in _independent_review_job()["steps"]:
        assert not step.get("continue-on-error", False)
        if "checkout@" in step.get("uses", ""):
            assert step["with"]["persist-credentials"] is False


def _isolated_reviewer_modules(review_case):
    review_exit, preparation_status, fixture_reason = review_case
    replacements = {"REVIEW_EXIT": str(review_exit), "STATUS": repr(preparation_status), "REASON": repr(fixture_reason)}
    return {name: Template(source).substitute(replacements) for name, source in _ISOLATED_REVIEWER_TEMPLATES.items()}


def _create_isolated_reviewer(tmp_path: Path, review_case):
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
    modules = _isolated_reviewer_modules(review_case)
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


@pytest.mark.parametrize(
    "review_exit,preparation_status,fixture_reason",
    [
        (0, "PASS", "policy_parse_failure"),
        (2, "PASS", "policy_parse_failure"),
        (7, "PASS", "policy_parse_failure"),
        (0, "UNKNOWN", "policy_parse_failure"),
        (0, "UNKNOWN", "private/path\nsecret"),
    ],
)
def test_isolated_reviewer_preloads_trusted_code_and_never_accepts_incomplete_preparation(
    tmp_path: Path, review_exit: int, preparation_status: str, fixture_reason: str
) -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    job = workflow["jobs"]["independent-review"]
    step = next(
        item
        for item in job["steps"]
        if item.get("name") == "Prepare and review through the authenticated installed controller"
    )
    trusted, environment = _create_isolated_reviewer(tmp_path, (review_exit, preparation_status, fixture_reason))
    result = subprocess.run(["bash", "-c", step["run"]], env=environment, text=True, capture_output=True, check=False)
    expected = review_exit if preparation_status == "PASS" else 1
    assert result.returncode == expected, result.stdout + result.stderr
    assert (trusted / "preloaded").exists()
    if preparation_status != "PASS":
        _assert_incomplete_preparation(trusted, result, fixture_reason)
    else:
        _assert_installed_review_arguments(trusted)


def _assert_incomplete_preparation(trusted: Path, result, fixture_reason: str):
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


def _assert_installed_review_arguments(trusted: Path):
    assert (trusted / "prepared").read_text().splitlines() == ["base", "head"]
    args = json.loads((trusted / "argv.json").read_text())
    assert args[:3] == ["code", "review", "run"]
    assert args[args.index("--scope") + 1] == "index"
    assert args[args.index("--enforcement") + 1] == "changed"
    assert "--bug-hunt" in args


def test_trusted_bootstrap_cannot_import_candidate_venv_module(tmp_path: Path) -> None:
    import textwrap

    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    step = workflow["jobs"]["independent-review"]["steps"][2]
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    marker = tmp_path / "host-code-executed"
    (candidate / "venv.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\nraise SystemExit(9)\n"
    )
    launcher_dir = tmp_path / "launcher"
    launcher_dir.mkdir()
    launcher = launcher_dir / "python"
    launcher.write_text(f"#!{sys.executable}\n" + textwrap.dedent(_TRUSTED_BOOTSTRAP_LAUNCHER))
    launcher.chmod(0o700)
    runner_temp = tmp_path / "runner"
    runner_temp.mkdir()
    environment = os.environ | {
        "RUNNER_TEMP": str(runner_temp),
        "GITHUB_ENV": str(tmp_path / "job.env"),
        "PATH": str(launcher_dir) + os.pathsep + os.environ["PATH"],
    }
    result = subprocess.run(
        ["bash", "-c", step["run"]], cwd=candidate, env=environment, text=True, capture_output=True, check=False
    )
    assert not marker.exists(), "Candidate code executed on the trusted bootstrap host"
    assert result.returncode == 0, result.stdout + result.stderr


def test_failed_candidate_diagnostics_expose_only_bounded_tracked_locations(tmp_path: Path) -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    step = next(item for item in workflow["jobs"]["customer"]["steps"] if item.get("name") == STEP_NAME)
    code = step["run"].rsplit("- <<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
    _git(tmp_path, "init", "-q")
    source = tmp_path / "public.py"
    source.write_text("value = 1\n")
    _git(tmp_path, "add", "public.py")
    report = tmp_path / ".specfact/code-review.json"
    report.parent.mkdir()
    report.write_text(
        json.dumps(
            {
                "analyzer_evidence": [{"id": "PRIVATE_ANALYZER", "diagnostic": "PRIVATE_TOKEN"}],
                "findings": [
                    {"file": "public.py", "line": 12, "severity": "warning", "message": "PRIVATE_MESSAGE"},
                    {"file": "/private/SECRET.py", "line": 1, "severity": "error"},
                    {"file": "untracked_SECRET.py", "line": 1, "severity": "error"},
                    {"file": "public.py", "line": True, "severity": "error"},
                    {"file": "public.py", "line": 0, "severity": "error"},
                    {"file": "public.py", "line": 1, "severity": "PRIVATE_SEVERITY"},
                    *[{"file": "public.py", "line": line, "severity": "info"} for line in range(20, 225)],
                ],
            }
        )
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    rows = [json.loads(line)["finding_location"] for line in result.stdout.splitlines()]
    assert len(rows) == 200
    assert rows[0] == {"file": "public.py", "line": 12, "severity": "warning"}
    assert "PRIVATE" not in result.stdout and "SECRET" not in result.stdout


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
def test_both_failed_reviews_project_fixed_analyzer_identity_without_private_text(
    tmp_path: Path, job_name: str
) -> None:
    code = _public_projector(job_name)
    _write_public_report(tmp_path, _FIXED_ANALYZER_FINDING_ROWS)
    result = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    rows = [json.loads(line)["finding_location"] for line in result.stdout.splitlines()]
    assert rows[1] == {
        "file": "public.py",
        "line": 1,
        "severity": "error",
        "category": "clean_code",
        "tool": "radon",
        "rule": "CC34",
    }
    assert rows[0]["failure_class"] == "timeout"
    assert "PRIVATE" not in result.stdout


def _public_projector(job_name):
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    name = STEP_NAME if job_name == "customer" else "Prepare and review through the authenticated installed controller"
    recipe = next(step["run"] for step in workflow["jobs"][job_name]["steps"] if step.get("name") == name)
    return recipe.rsplit("- <<'PY'\n", 1)[1].split("\nPY\n", 1)[0]


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
def test_public_tool_errors_cannot_disappear_after_two_hundred_ordinary_findings(tmp_path: Path, job_name):
    _git(tmp_path, "init", "-q")
    (tmp_path / "public.py").write_text("value = 1\n")
    _git(tmp_path, "add", "public.py")
    report = tmp_path / ".specfact/code-review.json"
    report.parent.mkdir()
    rows = [{"file": "public.py", "line": n, "severity": "info"} for n in range(1, 220)]
    rows.append(
        {
            "file": "public.py",
            "line": 1,
            "severity": "error",
            "category": "tool_error",
            "tool": "pytest",
            "message": "PRIVATE_SECRET",
        }
    )
    report.write_text(json.dumps({"findings": rows}))
    result = subprocess.run(
        [sys.executable, "-c", _public_projector(job_name)], cwd=tmp_path, capture_output=True, text=True, check=False
    )
    projected = [json.loads(line)["finding_location"] for line in result.stdout.splitlines()]
    assert result.returncode == 0, result.stderr
    assert len(projected) == 200
    assert projected[0]["category"] == "tool_error" and projected[0]["tool"] == "pytest"
    assert "PRIVATE" not in result.stdout


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize("review_exit,diagnostic", [("1", "review_report_missing"), ("124", "analysis_timeout")])
def test_missing_review_report_has_fixed_public_cause(tmp_path: Path, job_name, review_exit, diagnostic):
    environment = dict(os.environ, REVIEW_PUBLIC_EXIT=review_exit)
    result = subprocess.run(
        [sys.executable, "-c", _public_projector(job_name)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"status": "INCOMPLETE", "phase": "review", "diagnostic": diagnostic}


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize(
    "message,failure_class",
    [
        ("semgrep returned structured errors PRIVATE", "structured_errors"),
        ("semgrep process failed PRIVATE", "process_failure"),
        ("semgrep returned empty stdout PRIVATE", "empty_output"),
        ("Unrecognized CrossHair output PRIVATE", "unrecognized_output"),
    ],
)
def test_public_execution_classification_never_prints_raw_messages(tmp_path: Path, job_name, message, failure_class):
    _git(tmp_path, "init", "-q")
    (tmp_path / "public.py").write_text("value = 1\n")
    _git(tmp_path, "add", "public.py")
    report = tmp_path / ".specfact/code-review.json"
    report.parent.mkdir()
    report.write_text(
        json.dumps(
            {
                "findings": [
                    {"file": "public.py", "line": 1, "severity": "error", "category": "tool_error", "message": message}
                ]
            }
        )
    )
    result = subprocess.run(
        [sys.executable, "-c", _public_projector(job_name)], cwd=tmp_path, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    row = json.loads(result.stdout)["finding_location"]
    assert row["failure_class"] == failure_class
    assert "PRIVATE" not in result.stdout


def test_trusted_review_budget_timeout_retains_three_hundred_seconds_and_fixed_exit(monkeypatch, tmp_path):
    import re
    import runpy

    recipe = next(
        step["run"]
        for step in _independent_review_job()["steps"]
        if step.get("name") == "Prepare and review through the authenticated installed controller"
    )
    command = re.findall(r"-I -c \\\n\s*'([^']+)'", recipe)[-1]
    wrapper = tmp_path / "trusted_review_budget.py"
    wrapper.write_text(command)
    observed = []

    def timeout(args, *, timeout, check):
        observed.append((args, timeout, check))
        raise subprocess.TimeoutExpired(args, timeout, stderr="PRIVATE_SECRET")

    monkeypatch.setattr(subprocess, "run", timeout)
    monkeypatch.setattr(sys, "argv", ["-c", "trusted-python", "trusted-reviewer.py"])
    with pytest.raises(SystemExit) as result:
        runpy.run_path(str(wrapper), run_name="__main__")
    assert result.value.code == 124
    assert observed == [(["trusted-python", "trusted-reviewer.py"], 300, False)]


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize(
    "details,expected",
    [
        (
            [{"type": "Syntax error", "message": "PRIVATE_SOURCE"}, {"type": "Timeout"}, {"type": "SECRET_TYPE"}],
            ["Syntax error", "Timeout"],
        ),
        (
            [{"type": ["PartialParsing", "PRIVATE_SPAN"]}, {"type": "Fatal error", "private": "PRIVATE_TOKEN"}],
            ["Fatal error", "PartialParsing"],
        ),
        (
            [{"type": "Syntax error"}, {"type": "Timeout"}, {"type": "Fatal error"}, {"type": "Out of memory"}],
            ["Fatal error", "Syntax error", "Timeout"],
        ),
    ],
)
def test_structured_semgrep_failure_projects_only_fixed_variant_tags(tmp_path: Path, job_name, details, expected):
    _git(tmp_path, "init", "-q")
    (tmp_path / "public.py").write_text("value = 1\n")
    _git(tmp_path, "add", "public.py")
    report = tmp_path / ".specfact/code-review.json"
    report.parent.mkdir()
    finding = {
        "file": "public.py",
        "line": 1,
        "severity": "error",
        "category": "tool_error",
        "tool": "semgrep",
        "message": "semgrep returned structured errors; details=" + json.dumps(details),
    }
    report.write_text(json.dumps({"findings": [finding]}))
    result = subprocess.run(
        [sys.executable, "-c", _public_projector(job_name)], cwd=tmp_path, text=True, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr
    projected = json.loads(result.stdout)["finding_location"]
    assert projected["failure_class"] == "structured_errors"
    assert projected["semgrep_error_types"] == expected
    assert "PRIVATE" not in result.stdout and "SECRET" not in result.stdout


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize(
    "details",
    [
        '{"type":"Syntax error"}',
        "not-json",
        '[{"type":"SECRET_TYPE"}]',
        '[{"type":"Syntax error"}]' + "PRIVATE" * 1000,
        "[" * 1500 + "]" * 1500,
    ],
)
def test_malformed_or_oversized_semgrep_details_keep_generic_public_cause(tmp_path: Path, job_name, details):
    _git(tmp_path, "init", "-q")
    (tmp_path / "public.py").write_text("value = 1\n")
    _git(tmp_path, "add", "public.py")
    report = tmp_path / ".specfact/code-review.json"
    report.parent.mkdir()
    finding = {
        "file": "public.py",
        "line": 1,
        "severity": "error",
        "category": "tool_error",
        "tool": "semgrep",
        "message": "semgrep returned structured errors; details=" + details,
    }
    report.write_text(json.dumps({"findings": [finding]}))
    result = subprocess.run(
        [sys.executable, "-c", _public_projector(job_name)], cwd=tmp_path, text=True, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr
    projected = json.loads(result.stdout)["finding_location"]
    assert projected["failure_class"] == "structured_errors"
    assert "semgrep_error_types" not in projected
    assert "PRIVATE" not in result.stdout and "SECRET" not in result.stdout


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
def test_semgrep_decoder_depth_failure_keeps_generic_public_cause(tmp_path: Path, job_name):
    _write_public_report(tmp_path, _DEPTH_FAILURE_FINDING_ROWS)
    fault = """import json
_original_loads = json.loads
def _depth_failure(value, *args, **kwargs):
    if value == "DECODER_DEPTH_FAILURE":
        raise RecursionError("PRIVATE_DECODER_TRACE")
    return _original_loads(value, *args, **kwargs)
json.loads = _depth_failure
"""
    result = subprocess.run(
        [sys.executable, "-c", fault + _public_projector(job_name)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    projected = json.loads(result.stdout)["finding_location"]
    assert projected["failure_class"] == "structured_errors"
    assert "semgrep_error_types" not in projected
    assert "PRIVATE" not in result.stdout and "PRIVATE" not in result.stderr


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize(
    "message,code",
    [
        ("project_pytest_coverage_worker_missing; PRIVATE", "project_pytest_coverage_worker_missing"),
        ("project_pytest_coverage_evidence_unavailable:PRIVATE", "project_pytest_coverage_evidence_unavailable"),
        ("project_pytest_execution_incomplete:exit=4 PRIVATE", "project_pytest_execution_incomplete"),
        ("project_pytest_root_outside_snapshot", "project_pytest_root_outside_snapshot"),
        ("project_pytest_root_missing_or_invalid; PRIVATE", "project_pytest_root_missing_or_invalid"),
        ("project_pytest_collection_error; PRIVATE", "project_pytest_collection_error"),
        ("[Errno 2] PRIVATE_PATH", "file_missing"),
        ("[Errno 13] PRIVATE_PATH", "permission_denied"),
        ("PRIVATE project_pytest_execution_incomplete", None),
        ("project_pytest_execution_incomplete_PRIVATE", None),
        ("PRIVATE_UNKNOWN", None),
    ],
)
def test_public_pytest_failure_codes_withhold_private_payload(tmp_path: Path, job_name, message, code):
    _git(tmp_path, "init", "-q")
    (tmp_path / "public.py").write_text("value = 1\n")
    _git(tmp_path, "add", "public.py")
    report = tmp_path / ".specfact/code-review.json"
    report.parent.mkdir()
    report.write_text(
        json.dumps(
            {
                "findings": [
                    {
                        "file": "public.py",
                        "line": 1,
                        "severity": "error",
                        "category": "tool_error",
                        "tool": "pytest",
                        "message": message,
                    }
                ]
            }
        )
    )
    result = subprocess.run(
        [sys.executable, "-c", _public_projector(job_name)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    projected = json.loads(result.stdout)["finding_location"]
    assert projected.get("diagnostic_code") == code
    assert "PRIVATE" not in result.stdout


@pytest.mark.parametrize(
    "progress,analyzer",
    [
        ("PRIVATE\nChecking capsule analyzer contracts...\n", "contracts"),
        (
            "Checking capsule analyzer pylint...\nPRIVATE\nChecking capsule analyzer targeted-pytest-coverage...\n",
            "targeted-pytest-coverage",
        ),
        ("Checking capsule analyzer PRIVATE...\n", None),
        ("PRIVATE Checking capsule analyzer pylint...\n", None),
        ("Checking capsule analyzer pylint...\n" + "X" * 65537, None),
    ],
)
def test_independent_timeout_projects_only_bounded_exact_progress(tmp_path: Path, progress, analyzer):
    log = tmp_path / "progress.private.log"
    log.write_text(progress)
    environment = dict(os.environ, REVIEW_PUBLIC_EXIT="124", REVIEW_PUBLIC_PROGRESS=str(log))
    result = subprocess.run(
        [sys.executable, "-c", _public_projector("independent-review")],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    row = json.loads(result.stdout)
    assert row["diagnostic"] == "analysis_timeout"
    assert row.get("analyzer") == analyzer
    assert "PRIVATE" not in result.stdout


@pytest.mark.parametrize("job_name", ["customer", "independent-review"])
@pytest.mark.parametrize("rule", ["TEST_OUTCOME_NOT_PASS", "TEST_COVERAGE_POLICY_FAILED"])
def test_public_testing_findings_survive_ordinary_location_cap(tmp_path: Path, job_name, rule):
    rows = [{"file": "public.py", "line": n, "severity": "info"} for n in range(1, 220)]
    rows.append(
        {
            "file": "public.py",
            "line": 1,
            "severity": "error",
            "category": "testing",
            "tool": "pytest",
            "rule": rule,
            "message": "PRIVATE_TRACE_WITH_PARAMETERS",
        }
    )
    _write_public_report(tmp_path, rows)
    result = subprocess.run(
        [sys.executable, "-c", _public_projector(job_name)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    projected = [json.loads(line)["finding_location"] for line in result.stdout.splitlines()]
    assert result.returncode == 0, result.stderr
    assert len(projected) == 200
    assert projected[0].get("category") == "testing"
    assert projected[0].get("rule") == rule
    assert "PRIVATE" not in result.stdout


def test_deferred_host_fixture_does_not_alias_managed_caller_python(tmp_path: Path, monkeypatch):
    managed = tmp_path / "managed-python"
    managed.write_text("#!/bin/sh\nexit 78\n")
    managed.chmod(0o755)
    monkeypatch.setattr(sys, "executable", str(managed))
    test_deferred_gate_reviews_exact_staged_tree_and_propagates_failure(tmp_path, 0, False)
