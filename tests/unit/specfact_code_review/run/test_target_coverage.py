"""Native policy and reviewer coverage retain separate evidence and outcomes."""

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from specfact_code_review.run import target_coverage, target_pytest


_HELPER = Path(target_pytest.__file__).with_name("target_coverage.py")
_SCRIPT = r"""
import importlib.util, json, os, sys
from pathlib import Path
import pytest
helper, snapshot, output, extra = map(Path, sys.argv[1:])
args = ["-q", "-p", "pytest_cov", *json.loads(extra.read_text()), "tests"]
if helper.is_file():
    spec = importlib.util.spec_from_file_location("_specfact_target_coverage", helper)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.configure(snapshot=snapshot, output=output, directories=[])
    args[0:0] = ["-p", spec.name]
    code = pytest.main(args)
    evidence = module.evidence()
else:
    # Exact pre-change injection: a valued snapshot scope and replacing JSON report.
    args[-1:-1] = [f"--cov={snapshot}", f"--cov-report=json:{output}"]
    code = pytest.main(args)
    evidence = {"coverage": json.loads(output.read_text()) if output.exists() else {},
                "coverage_policy": {"mode": "legacy-forced", "native_threshold_failed": False}}
output.with_suffix(".receipt").write_text(json.dumps({"exit_code": int(code), **evidence}))
raise SystemExit(int(code))
"""


def _project(tmp_path, *, native="", extra_config="", failure=False):
    source = tmp_path / "project"
    source.mkdir()
    (source / "tests").mkdir()
    (source / "app.py").write_text("def covered():\n    return 1\ndef untouched():\n    return 2\n")
    (source / "unrelated.py").write_text("VALUE = 99\n")
    expected = 0 if failure else 1
    (source / "tests/test_app.py").write_text(
        f"from app import covered\ndef test_app():\n    assert covered() == {expected}\n"
    )
    (source / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath=["."]\n'
        f"addopts={json.dumps(native)}\n"
        '[tool.coverage.run]\nsource=["app"]\n'
        "[tool.coverage.report]\nfail_under=95\nprecision=2\n" + extra_config
    )
    return source


def _run(source, tmp_path, extra=(), *, startup=None):
    output = tmp_path / "private.json"
    arguments = tmp_path / "arguments.json"
    arguments.write_text(json.dumps(extra))
    completed = subprocess.run(
        [sys.executable, "-c", _SCRIPT, str(_HELPER), str(source), str(output), str(arguments)],
        cwd=source,
        env={
            **os.environ,
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "COVERAGE_FILE": str(tmp_path / ".coverage"),
            **({"PYTHONPATH": str(startup)} if startup else {}),
        },
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    receipt = output.with_suffix(".receipt")
    assert receipt.is_file(), completed.stdout + completed.stderr
    return completed, json.loads(receipt.read_text())


def test_reviewer_does_not_activate_dormant_aggregate_policy(tmp_path):
    completed, receipt = _run(_project(tmp_path), tmp_path)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert receipt["coverage_policy"]["mode"] == "reviewer"
    assert receipt["coverage_policy"]["threshold"] == 95
    assert receipt["coverage"]["totals"]["percent_covered"] < 95
    assert all("unrelated.py" not in path for path in receipt["coverage"]["files"])


def test_native_threshold_failure_and_json_destination_remain_native(tmp_path):
    source = _project(tmp_path, native="--cov --cov-report=json:customer.json")
    completed, receipt = _run(source, tmp_path)
    assert completed.returncode == 1
    assert (source / "customer.json").is_file()
    assert receipt["coverage_policy"]["mode"] == "native"
    assert receipt["coverage_policy"]["native_threshold_failed"] is True
    assert all("unrelated.py" not in path for path in receipt["coverage"]["files"])


@pytest.mark.parametrize("options", ["--no-cov", "--cov --no-cov"])
def test_explicit_coverage_disable_leaves_evidence_incomplete(tmp_path, options):
    completed, receipt = _run(_project(tmp_path, native=options), tmp_path)
    assert completed.returncode == 0
    assert receipt["coverage"] == {}
    assert receipt["coverage_policy"]["mode"] == "disabled"
    assert "--no-cov" in receipt["coverage_diagnostic"]


def test_native_no_report_control_does_not_disable_private_measurement(tmp_path):
    source = _project(tmp_path, native="--cov --cov-report= --cov-fail-under=0")
    completed, receipt = _run(source, tmp_path)
    assert completed.returncode == 0
    assert receipt["coverage"]["files"]
    assert receipt["coverage_policy"]["mode"] == "native"
    assert not (source / "htmlcov").exists()


def test_native_failure_report_suppression_remains_incomplete(tmp_path):
    source = _project(tmp_path, native="--cov --no-cov-on-fail", failure=True)
    completed, receipt = _run(source, tmp_path)
    assert completed.returncode == 1
    assert receipt["coverage"] == {}
    assert "--no-cov-on-fail" in receipt["coverage_diagnostic"]


def test_target_observer_does_not_override_native_coverage_arguments(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "project-runtime.json").write_text(
        json.dumps(
            {
                "project": {"pytest_config": {"addopts": "--cov=app --cov-report=json:customer.json"}},
                "inventory": {"pytest_arguments": []},
            }
        )
    )
    measurement = {"coverage": {}, "coverage_policy": {"mode": "reviewer"}, "coverage_threshold": 95}
    collector = SimpleNamespace(configure=lambda **_kwargs: None, evidence=lambda: measurement)
    monkeypatch.setitem(sys.modules, "_specfact_target_coverage", collector)
    monkeypatch.setattr(target_pytest, "ROOT", runtime)
    monkeypatch.setattr(target_pytest, "SNAPSHOT_ROOT", tmp_path)
    monkeypatch.setattr(
        target_pytest, "Path", lambda value: Path(str(value).replace("/opt/specfact/tmp", str(tmp_path)))
    )
    monkeypatch.setattr(sys, "argv", ["observer", json.dumps({"selectors": ["tests"]})])
    captured = []

    def run(arguments, *, plugins):
        assert len(plugins) == 1
        captured.extend(arguments)
        return 0

    monkeypatch.setattr(pytest, "main", run)
    with pytest.raises(SystemExit) as result:
        target_pytest.main()
    assert result.value.code == 0
    assert not any(token.startswith(("--cov=", "--cov-report=")) for token in captured)
    assert "_specfact_target_coverage" in captured
    observation = json.loads((tmp_path / "pytest-observation.json").read_text())
    assert observation["coverage_policy"] == measurement["coverage_policy"]


def test_excluded_measurement_preserves_success_and_incomplete_reason(tmp_path):
    source = _project(tmp_path)
    config = source / "pyproject.toml"
    config.write_text(config.read_text().replace('source=["app"]', 'source=["not_installed_anywhere"]'))
    completed, receipt = _run(source, tmp_path)
    assert completed.returncode == 0
    assert receipt["coverage"] == {}
    assert "No data to report" in receipt["coverage_diagnostic"]


def test_native_collect_only_does_not_claim_aggregate_failure(tmp_path):
    source = _project(tmp_path, native="--cov --collect-only")
    completed, receipt = _run(source, tmp_path)
    assert completed.returncode == 0
    assert receipt["coverage_policy"]["native_threshold_failed"] is False


def test_private_export_uses_native_topdir_after_customer_chdir(tmp_path):
    source = _project(tmp_path)
    (source / "tests/test_app.py").write_text(
        'import os\nfrom app import covered\ndef test_app():\n    assert covered() == 1\n    os.chdir("tests")\n'
    )
    completed, receipt = _run(source, tmp_path)
    assert completed.returncode == 0, completed.stderr
    assert receipt["coverage"]["files"]["app.py"]["executed_lines"] == [1, 2, 3]


@pytest.mark.parametrize("native", ["", "--cov --cov-fail-under=0"])
def test_parallel_measurement_combines_real_workers(tmp_path, native):
    source = _project(tmp_path, native=native)
    (source / "tests/test_second.py").write_text(
        "from app import untouched\ndef test_second():\n    assert untouched() == 2\n"
    )
    startup = _worker_startup(tmp_path)
    completed, receipt = _run(source, tmp_path, ["-p", "xdist.plugin", "-n", "2"], startup=startup)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "2 passed" in completed.stdout
    assert receipt["coverage"]["files"]["app.py"]["executed_lines"] == [1, 2, 3, 4]
    assert receipt["coverage"]["totals"]["percent_covered"] == 100
    assert receipt["coverage_policy"]["mode"] == ("native" if native else "reviewer")


def _worker_startup(tmp_path):
    startup = tmp_path / "startup"
    startup.mkdir()
    (startup / "sitecustomize.py").write_text(
        "import importlib.util,sys\n"
        f'spec=importlib.util.spec_from_file_location("_specfact_target_coverage",{str(_HELPER)!r})\n'
        "module=importlib.util.module_from_spec(spec)\nsys.modules[spec.name]=module\nspec.loader.exec_module(module)\n"
    )
    return startup


def test_missing_parallel_coverage_receipt_stays_incomplete(tmp_path):
    source = _project(tmp_path)
    (source / "conftest.py").write_text(
        "import pytest\n@pytest.hookimpl(tryfirst=True)\n"
        "def pytest_testnodedown(node,error):\n"
        '    if node.gateway.id == "gw0":\n        node.workeroutput.pop("cov_worker_node_id",None)\n'
    )
    completed, receipt = _run(source, tmp_path, ["-p", "xdist.plugin", "-n", "2"], startup=_worker_startup(tmp_path))
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert receipt["coverage"] == {}
    assert "coverage_worker_missing" in receipt["coverage_diagnostic"]


def test_configured_child_interpreter_retains_measured_lines(tmp_path):
    source = _project(tmp_path)
    config = source / "pyproject.toml"
    config.write_text(config.read_text().replace('source=["app"]', 'source=["app"]\npatch=["subprocess"]'))
    (source / "tests/test_app.py").write_text(
        "import subprocess,sys\ndef test_app():\n"
        '    child=subprocess.run([sys.executable,"-c","from app import covered; assert covered()==1"],check=False)\n'
        "    assert child.returncode == 0\n"
    )
    completed, receipt = _run(source, tmp_path)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert receipt["coverage"]["files"]["app.py"]["executed_lines"] == [1, 2, 3]


def test_native_report_failure_is_precise_and_keeps_test_exit(tmp_path):
    source = _project(tmp_path, native="--cov --cov-fail-under=0 --cov-report=json:occupied")
    (source / "occupied").mkdir()
    completed, receipt = _run(source, tmp_path)
    assert completed.returncode == 3, completed.stdout + completed.stderr
    assert "IsADirectoryError" in completed.stdout
    assert receipt["coverage_policy"]["native_threshold_failed"] is False


def test_native_report_warning_does_not_hide_unavailable_reporting(tmp_path):
    source = _project(tmp_path, native="--cov", extra_config='omit=["*"]\n')
    completed, receipt = _run(source, tmp_path)
    assert completed.returncode == 1
    assert receipt["coverage"] == {}
    assert "NoDataError:No data to report" in receipt["coverage_diagnostic"]
    assert "Failed to generate report: No data to report" in completed.stdout


def test_explicit_blocked_cov_plugin_stays_incomplete(tmp_path):
    completed, receipt = _run(_project(tmp_path), tmp_path, ["-p", "no:pytest_cov"])
    assert completed.returncode == 0
    assert receipt["coverage"] == {}
    assert "no:pytest_cov" in receipt["coverage_diagnostic"]


def test_unsupported_plugin_contract_is_actionable(tmp_path, monkeypatch):
    target_coverage.configure(snapshot=tmp_path, output=tmp_path / "out.json", directories=[])
    monkeypatch.setattr(target_coverage.importlib.metadata, "version", lambda _name: "8.0.0")
    target_coverage.pytest_load_initial_conftests(None, None, [])
    receipt = target_coverage.evidence()
    assert receipt["coverage"] == {}
    assert "unsupported_pytest_cov_contract:8.0.0" in receipt["coverage_diagnostic"]
    assert receipt["coverage_policy"]["native_threshold_failed"] is False


def test_verified_preload_does_not_break_strict_rewrite_warning_policy(tmp_path):
    completed, receipt = _run(_project(tmp_path), tmp_path, ["-W", "error::pytest.PytestAssertRewriteWarning"])
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert receipt["coverage"]["files"]


def test_effective_scope_receipt_reflects_native_cli_overrides(tmp_path):
    source = _project(tmp_path, native="--cov=unrelated --cov-branch --cov-fail-under=0 --cov-precision=4")
    completed, receipt = _run(source, tmp_path)
    assert completed.returncode == 0
    configuration = receipt["coverage_configuration"]
    assert configuration["run"]["source"] == ["app"]
    assert configuration["effective"]["run"]["source"] == ["unrelated"]
    assert configuration["effective"]["run"]["branch"] is True
    assert configuration["effective"]["threshold"] == 0
    assert configuration["effective"]["precision"] == 4
    assert receipt["coverage_policy"]["mode"] == "native"
