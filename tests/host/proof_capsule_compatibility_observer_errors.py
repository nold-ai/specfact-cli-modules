from __future__ import annotations

import json

import pytest

from tests.host import capsule_compatibility_native_fixtures as native
from tests.host.proof_capsule_compatibility_observation import (
    installed_native_fixture,
    read_events,
    run_preparation_recipe,
)
from tests.host.proof_capsule_compatibility_publisher import legacy_summary, run_publisher
from tests.support.capsule_review_fixtures import isolated_python_site_packages


MALFORM_AFTER_PREPARE = (
    "(lambda value: ((Path.home() / '.specfact/modules/specfact-code-review/module-package.yaml')"
    ".write_bytes(b'observer: [\\n'), value)[1])(prepare_runtime(plan, runtime=runtime))"
)
FAULT_INSTALLATION = """
if sys.argv[0].endswith('reviewer.py'):
    import json
    from pathlib import Path
    import yaml

    fault_root = Path.home().parent
    fault_config = json.loads((fault_root / 'observer-fault.json').read_text())
    original_dumps = json.dumps
    original_safe_load = yaml.safe_load

    def raise_observer_fault():
        with (fault_root / 'observer-fault-hits').open('a') as stream:
            stream.write(fault_config['exception'] + '\\n')
        exceptions = {'OverflowError': OverflowError, 'SystemExit': SystemExit, 'KeyboardInterrupt': KeyboardInterrupt}
        raise exceptions[fault_config['exception']]('PRIVATE_OBSERVER_FAULT')

    def fault_dumps(value, *args, **kwargs):
        if isinstance(value, dict) and value.get('schema') == 'compatibility-observation-v1':
            if bool(value['sides']) == fault_config['populated']:
                raise_observer_fault()
        return original_dumps(value, *args, **kwargs)

    def fault_safe_load(value):
        if value == b'observer: [\\n':
            if fault_config['exception'] == 'native-yaml':
                try:
                    return original_safe_load(value)
                finally:
                    manifest = Path.home() / '.specfact/modules/specfact-code-review/module-package.yaml'
                    manifest.write_bytes((fault_root / 'original-manifest.yaml').read_bytes())
            raise_observer_fault()
        return original_safe_load(value)

    if fault_config['operation'] == 'serialize':
        json.dumps = fault_dumps
    else:
        yaml.safe_load = fault_safe_load
"""


def install_observation_fault(trusted, *, operation, exception, populated=True):
    settings = {"operation": operation, "exception": exception, "populated": populated}
    (trusted / "observer-fault.json").write_text(json.dumps(settings))
    manifest = trusted / "home/.specfact/modules/specfact-code-review/module-package.yaml"
    (trusted / "original-manifest.yaml").write_bytes(manifest.read_bytes())
    site = isolated_python_site_packages(trusted / "venv/bin/python")
    with (site / "sitecustomize.py").open("a") as stream:
        stream.write(FAULT_INSTALLATION)


def assert_cleanup(trusted, workers):
    events = read_events(trusted)
    assert [event["removed"] for event in events if event["event"] == "worker_cleanup"] == [True] * workers
    assert [event["removed"] for event in events if event["event"] == "scope_cleanup"] == [True]
    return events


def assert_unchanged_review(trusted, baseline, result, original):
    assert result.returncode == original.returncode, (trusted / "preparation.private.log").read_text()
    assert result.stdout == original.stdout
    assert result.stderr == original.stderr
    for name in ("preparation.private.log", "review.private.log"):
        assert (trusted / name).read_bytes() == (baseline / name).read_bytes()
    assert (trusted / "review-attempted").exists()
    assert native.CANARY not in result.stdout + result.stderr
    assert "PRIVATE_OBSERVER_FAULT" not in result.stdout + result.stderr
    events = assert_cleanup(trusted, 2)
    assert len([event for event in events if event["event"] == "verified_prepared"]) == 2


@pytest.mark.parametrize("review_exit", [17, 124])
def test_yaml_observation_error_preserves_review(tmp_path, review_exit):
    (tmp_path / "baseline").mkdir()
    (tmp_path / "malformed").mkdir()
    baseline = installed_native_fixture(tmp_path / "baseline", review_exit=review_exit)
    original = run_preparation_recipe(baseline)
    trusted = installed_native_fixture(tmp_path / "malformed", review_exit=review_exit)
    install_observation_fault(trusted, operation="parse", exception="native-yaml")
    result = run_preparation_recipe(trusted, MALFORM_AFTER_PREPARE)
    assert original.returncode == review_exit
    assert_unchanged_review(trusted, baseline, result, original)
    assert json.loads((trusted / "compatibility.private.json").read_text()) == {
        "schema": "compatibility-observation-v1",
        "sides": [{"status": "unavailable", "side": side} for side in ("base", "head")],
    }
    assert run_publisher(trusted) == legacy_summary() | {"compatibility_proof": {"status": "unavailable"}}


def test_yaml_observation_error_preserves_native_failure(tmp_path):
    trusted = installed_native_fixture(tmp_path, fail_head=True)
    install_observation_fault(trusted, operation="parse", exception="native-yaml")
    result = run_preparation_recipe(trusted, MALFORM_AFTER_PREPARE)
    assert result.returncode == 1
    events = assert_cleanup(trusted, 2)
    assert len([event for event in events if event["event"] == "verified_prepared"]) == 1
    assert not (trusted / "review-attempted").exists()
    failure = (trusted / "preparation.private.log").read_text()
    assert "ValueError: " + native.CANARY + ":synthetic build failure" in failure
    assert failure.splitlines()[-1].startswith(
        "specfact_code_review.run.runtime_models.ProjectRuntimeError: project_runtime_prepare_failed; private log: "
    )
    assert failure.splitlines()[-1].endswith("; ValueError")
    assert native.CANARY not in result.stdout + result.stderr


@pytest.mark.parametrize("populated", [False, True], ids=["initial-reset", "prepared-side"])
def test_transport_error_preserves_review(tmp_path, populated):
    (tmp_path / "baseline").mkdir()
    (tmp_path / "serialization").mkdir()
    baseline = installed_native_fixture(tmp_path / "baseline")
    original = run_preparation_recipe(baseline)
    trusted = installed_native_fixture(tmp_path / "serialization")
    install_observation_fault(trusted, operation="serialize", exception="OverflowError", populated=populated)
    result = run_preparation_recipe(trusted)
    assert original.returncode == 17
    assert (trusted / "observer-fault-hits").read_text().splitlines() == ["OverflowError"] * (2 if populated else 1)
    assert_unchanged_review(trusted, baseline, result, original)
    if populated:
        assert run_publisher(trusted) == legacy_summary() | {"compatibility_proof": {"status": "unavailable"}}
    else:
        assert run_publisher(trusted)["compatibility_proof"]["status"] == "observed"


@pytest.mark.parametrize("operation", ["parse", "serialize"])
@pytest.mark.parametrize("exception", ["SystemExit", "KeyboardInterrupt"])
def test_observer_interruptions_propagate(tmp_path, operation, exception):
    trusted = installed_native_fixture(tmp_path)
    install_observation_fault(trusted, operation=operation, exception=exception)
    replacement = MALFORM_AFTER_PREPARE if operation == "parse" else ""
    result = run_preparation_recipe(trusted, replacement)
    assert result.returncode == 1
    assert (trusted / "observer-fault-hits").read_text().splitlines() == [exception]
    events = assert_cleanup(trusted, 1)
    assert len([event for event in events if event["event"] == "verified_prepared"]) == 1
    assert not (trusted / "review-attempted").exists()
    assert "PRIVATE_OBSERVER_FAULT" in (trusted / "preparation.private.log").read_text()
    assert "PRIVATE_OBSERVER_FAULT" not in result.stdout + result.stderr
