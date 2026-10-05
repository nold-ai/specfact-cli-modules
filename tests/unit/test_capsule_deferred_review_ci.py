"""Execute the hosted gate recipe against a real isolated Git index."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
STEP_NAME = "Run deferred candidate commit review without weakening enforcement"


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


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
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.email", "fixture@example.invalid")
    _git(repository, "config", "user.name", "Fixture")
    target = repository / "packages/example/src/example.py"
    target.parent.mkdir(parents=True)
    target.write_text("value = 1\n")
    unrelated = target.with_name("unrelated.py")
    unrelated.write_text("value = 1\n")
    script = repository / "scripts/pre_commit_code_review.py"
    script.parent.mkdir()
    script.write_text(
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
    controller = repository / "packages/specfact-code-review/src/specfact_cli"
    controller.mkdir(parents=True)
    (controller / "__init__.py").write_text("")
    (controller / "cli.py").write_text(
        "import os,sys\n"
        "assert sys.argv[1:7] == ['code','review','runtime','prepare','--scope','index']\n"
        "assert os.environ['SPECFACT_MODULES_REPO'] == os.environ['GITHUB_WORKSPACE']\n"
        "assert os.environ['SPECFACT_CODE_REVIEW_CAPSULE_CACHE'].endswith('/commit-review-cache')\n"
        "print('{}')\n"
    )
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
    customer = tmp_path / "customer"
    (customer / "cache").mkdir(parents=True)
    (customer / "venv/bin").mkdir(parents=True)
    (customer / "venv/bin/python").symlink_to(sys.executable)
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


@pytest.mark.parametrize(
    "platform,ci,deferral,bundle,advanced_dev,independent_review,expected",
    [
        ("Darwin", "", "github-linux", "specfact-code-review", False, True, 0),
        ("Darwin", "", "github-linux", "specfact-code-review", False, False, 1),
        ("Darwin", "true", "github-linux", "specfact-code-review", False, True, 1),
        ("Linux", "", "github-linux", "specfact-code-review", False, True, 1),
        ("Darwin", "", "invalid", "specfact-code-review", False, True, 1),
        ("Darwin", "", "github-linux", "specfact-project", False, True, 1),
        ("Darwin", "", "github-linux", "specfact-project", True, True, 1),
    ],
)
def test_narrow_local_deferral_retains_block2_and_cannot_run_in_ci(
    tmp_path: Path,
    platform: str,
    ci: str,
    deferral: str,
    bundle: str,
    advanced_dev: bool,
    independent_review: bool,
    expected: int,
) -> None:
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
    _git(worktree, "add", ".")
    calls = tmp_path / "calls"
    script = (REPO_ROOT / "scripts/pre-commit-quality-checks.sh").read_text().rsplit('main "$@"', 1)[0]
    recipe = (
        script
        + r"""
uname() { if [[ "${1:-}" == "-m" ]]; then echo arm64; else echo "$FIXTURE_PLATFORM"; fi; }
hatch() {
  printf '%s\n' "$*" >> "$FIXTURE_CALLS"
  if [[ "$*" == *pre_commit_code_review.py* ]]; then return 99; fi
  if [[ "$*" == *contract-test-status* ]]; then return 1; fi
  return 0
}
run_block2
"""
    )
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
        assert "DEFERRED" in result.stderr
        assert "contract-test-contracts" in invoked
    else:
        assert "Capsule review deferral" in result.stderr


def test_hosted_preparation_has_separate_bound_and_cannot_bypass_review() -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    step = next(item for item in workflow["jobs"]["customer"]["steps"] if item.get("name") == STEP_NAME)
    recipe = step["run"]
    assert "timeout=1800" in recipe
    assert "code review runtime prepare --scope index" in recipe
    assert recipe.index("code review runtime prepare --scope index") < recipe.index("review_exit=0")
    assert 'SPECFACT_CODE_REVIEW_CAPSULE_CACHE="$CUSTOMER_ROOT/commit-review-cache"' in recipe
    assert "continue-on-error" not in step


def test_independent_reviewer_runs_in_fresh_job_without_candidate_host_code() -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    independent = workflow["jobs"].get("independent-review")
    assert independent is not None, "Installed reviewer must not share a writable venv/HOME with candidate host code"
    assert independent["runs-on"] == "ubuntu-24.04"
    assert independent["if"] == "github.event_name == 'pull_request'"
    assert not independent.get("needs"), "Candidate execution cannot suppress the independent review job"
    steps = independent["steps"]
    recipe = "\n".join(str(step.get("run", "")) for step in steps)
    assert "specfact-cli==0.55.4" in recipe
    assert "--version 0.50.1" in recipe
    assert "--source marketplace" in recipe
    assert "env -i" in recipe
    assert "pre_commit_code_review.py" not in recipe
    assert "link_dev_module.py" not in recipe
    assert "SPECFACT_MODULES_ROOTS" not in recipe
    assert "SPECFACT_ALLOW_UNSIGNED" not in recipe
    assert "$GITHUB_WORKSPACE/scripts" not in recipe
    assert "timeout=300" in recipe and "timeout=1800" in recipe
    assert "--scope index --enforcement changed --bug-hunt" in recipe
    assert "discover_snapshot" in recipe and "prepare_runtime" in recipe
    assert "runtime prepare --project-config" not in recipe, (
        "Mutable worktree prep cannot prewarm immutable index identities"
    )
    assert 'CommandRegistry.get_module_typer("code")' in recipe
    assert recipe.index('CommandRegistry.get_module_typer("code")') < recipe.index("os.chdir(sys.argv[1])")
    for step in steps:
        assert not step.get("continue-on-error", False)
        if "checkout@" in step.get("uses", ""):
            assert step["with"]["persist-credentials"] is False


@pytest.mark.parametrize("review_exit,preparation_status", [(0, "PASS"), (2, "PASS"), (7, "PASS"), (0, "UNKNOWN")])
def test_isolated_reviewer_preloads_trusted_code_and_never_accepts_incomplete_preparation(
    tmp_path: Path, review_exit: int, preparation_status: str
) -> None:
    import json
    import venv

    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/capsule-customer-execution.yml").read_text())
    job = workflow["jobs"]["independent-review"]
    step = next(
        item
        for item in job["steps"]
        if item.get("name") == "Prepare and review through the authenticated installed controller"
    )
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
    modules = {
        "specfact_cli/__init__.py": "",
        "specfact_cli/cli.py": (
            "import os,json\nfrom pathlib import Path\n"
            "root=Path(os.environ['HOME']).parent\n"
            "assert Path.cwd() == root, 'core discovery entered the candidate subject'\n"
            "assert not {'PYTHONPATH','GITHUB_TOKEN','GH_TOKEN','SPECFACT_MODULES_ROOTS','SPECFACT_ALLOW_UNSIGNED'} & os.environ.keys()\n"
            "def app(*,args):\n"
            "    assert Path.cwd() == root/'subject'\n"
            "    (root/'argv.json').write_text(json.dumps(args))\n"
            f"    raise SystemExit({review_exit})\n"
        ),
        "specfact_cli/registry/__init__.py": (
            "import os\nfrom pathlib import Path\n"
            "class CommandRegistry:\n"
            "    @classmethod\n"
            "    def get_module_typer(cls,name):\n"
            "        root=Path(os.environ['HOME']).parent\n"
            "        assert name=='code' and Path.cwd()==root\n"
            "        (root/'preloaded').touch()\n"
        ),
        "specfact_code_review/__init__.py": "",
        "specfact_code_review/run/__init__.py": "",
        "specfact_code_review/run/portable_snapshot.py": (
            "def discover_snapshot(root,*,config_path,source_snapshot):\n"
            "    assert root==source_snapshot.root and config_path.is_file()\n"
            "    return source_snapshot\n"
        ),
        "specfact_code_review/run/runtime_builder.py": (
            "import os\nfrom pathlib import Path\n"
            "def prepare_runtime(plan,*,runtime):\n"
            "    root=Path(os.environ['HOME']).parent\n"
            "    assert (root/'preloaded').exists()\n"
            "    with (root/'prepared').open('a') as out: out.write(plan.root.name+'\\n')\n"
        ),
        "specfact_code_review/run/runtime_interpreter.py": "def select_environment(plan,*,current): return current\n",
        "specfact_code_review/run/runner.py": (
            "def _capsule_environment_id(): return 'linux-x86_64-cp312'\n"
            "def _prepare_capsule_runtime(*,environment_id): return object(),''\n"
            "def _cleanup_capsule_runtime(runtime): pass\n"
        ),
        "specfact_code_review/run/scope.py": (
            "from types import SimpleNamespace\n"
            "def ScopeRequest(**kw): return SimpleNamespace(**kw)\n"
            "def resolve_scope(request):\n"
            "    assert request.scope=='index' and request.portable_project_runtime\n"
            f"    return SimpleNamespace(status={preparation_status!r},reason='fixture_policy_incompatible',"
            "base_snapshot=SimpleNamespace(root=request.repository/'base'),"
            "head_snapshot=SimpleNamespace(root=request.repository/'head'))\n"
            "def cleanup_scope_resolution(resolution): pass\n"
        ),
    }
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
    result = subprocess.run(["bash", "-c", step["run"]], env=environment, text=True, capture_output=True, check=False)
    expected = review_exit if preparation_status == "PASS" else 1
    assert result.returncode == expected, result.stdout + result.stderr
    assert (trusted / "preloaded").exists()
    if preparation_status != "PASS":
        assert not (trusted / "argv.json").exists()
        assert not (trusted / "prepared").exists()
        return
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
    launcher.write_text(
        f"#!{sys.executable}\n"
        + textwrap.dedent("""\
            import subprocess,sys
            from pathlib import Path
            result=subprocess.run([sys.executable,*sys.argv[1:]],check=False)
            if result.returncode:
                raise SystemExit(result.returncode)
            target=Path(sys.argv[-1])
            site=next((target/'lib').glob('python*/site-packages'))
            (site/'pip/__main__.py').write_text(
                "import sys\\nassert sys.argv[1:]==['install','--no-cache-dir','specfact-cli==0.55.4']\\n"
            )
            core=site/'specfact_cli'
            core.mkdir()
            (core/'__init__.py').write_text('')
            (core/'cli.py').write_text(
                "import sys\\nassert sys.argv[1:]==['module','install','nold-ai/specfact-code-review',"
                "'--scope','user','--version','0.50.1','--source','marketplace']\\n"
            )
            """)
    )
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
