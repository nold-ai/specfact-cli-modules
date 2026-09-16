"""Real native coverage must retain installed imports and authenticate source attribution."""

import base64
import csv
import hashlib
import importlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from specfact_code_review.run import installed_coverage, portable_worker, target_pytest
from specfact_code_review.run.runner import evaluate_portable_pytest_coverage
from specfact_code_review.run.target_pytest import _installed_coverage_candidates


def _record_hash(path: Path) -> str:
    return "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(path.read_bytes()).digest()).decode().rstrip("=")


def _distribution(site: Path, name: str, files: list[Path], *, local: bool = True) -> Path:
    metadata = site / f"{name}-1.0.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {name}\nVersion: 1.0\n")
    (metadata / "direct_url.json").write_text(
        json.dumps({"url": "file:///opt/specfact/output/project" if local else "https://example.invalid/wheel.whl"})
    )
    with (metadata / "RECORD").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerows((str(path.relative_to(site)), _record_hash(path), path.stat().st_size) for path in files)
    return metadata


@pytest.fixture(name="installed_project")
def installed_project_fixture(tmp_path: Path) -> SimpleNamespace:
    snapshot, site = tmp_path / "snapshot", tmp_path / "runtime/site-packages"
    source, installed = snapshot / "src/capsule_owned/math.py", site / "capsule_owned/math.py"
    source.parent.mkdir(parents=True)
    installed.parent.mkdir(parents=True)
    text = "def add(left, right):\n    return left + right\n"
    source.write_text(text)
    installed.write_text(text)
    initializer = installed.parent / "__init__.py"
    initializer.write_text('BUILT = "installed"\n')
    metadata = _distribution(site, "capsule-owned", [installed, initializer])
    tests = snapshot / "tests"
    tests.mkdir()
    (tests / "test_math.py").write_text(
        "import capsule_owned\nfrom capsule_owned.math import add\n"
        "def test_add():\n    assert capsule_owned.BUILT == 'installed'\n    assert add(2, 3) == 5\n"
    )
    return SimpleNamespace(snapshot=snapshot, site=site, source=source, installed=installed, metadata=metadata)


def _bridge(project: SimpleNamespace) -> Any:
    module = "specfact_code_review.run.installed_coverage"
    if importlib.util.find_spec(module) is None:
        # Pre-change behavior: only the snapshot is measured and no installed aliases exist.
        return SimpleNamespace(directories=(), mappings=(), diagnostics={})
    return importlib.import_module(module).plan_installed_coverage(
        [project.source], snapshot=project.snapshot, site_packages=project.site
    )


def _normalize(project, bridge, payload):
    module = "specfact_code_review.run.installed_coverage"
    if importlib.util.find_spec(module) is None:
        return payload, {}
    return importlib.import_module(module).attribute_installed_coverage(
        bridge, payload, snapshot=project.snapshot, relocations={path: path for path in bridge.measured_origins}
    )


def _native_coverage(project, bridge, tmp_path, *, import_mode="prepend"):
    report = tmp_path / "coverage.json"
    command = [
        sys.executable,
        "-P",
        "-m",
        "pytest",
        "-q",
        "-p",
        "pytest_cov",
        "--disable-warnings",
        f"--import-mode={import_mode}",
        f"--cov={project.snapshot}",
        *[f"--cov={path}" for path in bridge.directories],
        *[f"--cov={name}" for name in getattr(bridge, "modules", ())],
        f"--cov-report=json:{report}",
        "tests/test_math.py",
    ]
    result = subprocess.run(
        command,
        cwd=project.snapshot,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
        env={
            **os.environ,
            "PYTHONPATH": str(project.site),
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "COVERAGE_FILE": str(tmp_path / ".coverage"),
        },
    )
    assert report.is_file(), result.stdout + result.stderr
    return result, json.loads(report.read_text())


def test_native_installed_package_coverage_is_attributed_without_changing_imports(installed_project, tmp_path):
    project = installed_project
    bridge = _bridge(project)
    result, raw = _native_coverage(project, bridge, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    before = json.dumps(raw, sort_keys=True)
    attributed, diagnostics = _normalize(project, bridge, raw)
    row = attributed["files"].get(str(project.source))
    assert row is not None, "native installed production source is absent from snapshot-only coverage"
    assert row["summary"]["percent_covered"] == 100
    assert not diagnostics
    assert json.dumps(raw, sort_keys=True) == before
    assert any(str(project.installed) == str((project.snapshot / path).resolve()) for path in raw["files"])


def test_actual_defect_stays_failed_after_installed_attribution(installed_project, tmp_path):
    project = installed_project
    (project.snapshot / "tests/test_math.py").write_text(
        "from capsule_owned.math import add\ndef test_wrong():\n    assert add(2, 3) == 6\n"
    )
    bridge = _bridge(project)
    result, raw = _native_coverage(project, bridge, tmp_path)
    attributed, diagnostics = _normalize(project, bridge, raw)
    assert result.returncode == 1
    assert str(project.source) in attributed["files"]
    assert not diagnostics


def _invalidate_installed_attribution(project, scenario):
    if scenario == "changed":
        project.source.write_text("def add(left, right):\n    return left - right\n")
        return
    if scenario == "duplicate-source":
        duplicate = project.snapshot / "another/capsule_owned/math.py"
        duplicate.parent.mkdir(parents=True)
        duplicate.write_bytes(project.source.read_bytes())
        return
    if scenario == "duplicate-owner":
        _distribution(project.site, "other", [project.installed])
        return
    if scenario == "record-hash":
        record = project.metadata / "RECORD"
        record.write_text(record.read_text().replace(_record_hash(project.installed), "sha256=broken"))
        return
    if scenario == "record-escape":
        with (project.metadata / "RECORD").open("a") as stream:
            stream.write("../outside.py,sha256=broken,1\n")
        return
    assert scenario == "foreign-namespace"
    foreign = project.installed.parent / "foreign.py"
    foreign.write_text("VALUE = 1\n")
    _distribution(project.site, "foreign", [foreign], local=False)


@pytest.mark.parametrize(
    "scenario", ["changed", "duplicate-source", "duplicate-owner", "record-hash", "record-escape", "foreign-namespace"]
)
def test_unsafe_installed_attribution_is_incomplete(installed_project, scenario):
    project = installed_project
    _invalidate_installed_attribution(project, scenario)
    bridge = _bridge(project)
    assert not bridge.mappings
    assert str(project.source) in bridge.diagnostics


def test_nonlocal_distribution_does_not_claim_identical_snapshot(installed_project):
    project = installed_project
    (project.metadata / "direct_url.json").write_text(json.dumps({"url": "https://example.invalid/owned.whl"}))
    assert not _bridge(project).mappings


@pytest.mark.parametrize("changed", ["source", "installed"])
def test_content_change_after_planning_invalidates_coverage(installed_project, changed):
    project = installed_project
    bridge = _bridge(project)
    assert bridge.mappings
    getattr(project, changed).write_text("CHANGED = True\n")
    payload = {"files": {str(project.installed): {"summary": {"percent_covered": 100}}}}
    attributed, diagnostics = _normalize(project, bridge, payload)
    assert str(project.source) not in attributed["files"]
    assert str(project.source) in diagnostics


def test_missing_measured_row_cannot_be_manufactured(installed_project):
    project = installed_project
    bridge = _bridge(project)
    assert bridge.mappings
    attributed, diagnostics = _normalize(project, bridge, {"files": {}})
    assert not attributed["files"]
    assert str(project.source) in diagnostics


def test_direct_snapshot_coverage_takes_precedence(installed_project):
    project = installed_project
    bridge = _bridge(project)
    payload = {
        "files": {
            str(project.source): {"summary": {"percent_covered": 10}, "executed_lines": [1]},
            str(project.installed): {"summary": {"percent_covered": 100}},
        }
    }
    attributed, diagnostics = _normalize(project, bridge, payload)
    assert attributed["files"][str(project.source)]["summary"]["percent_covered"] == 10
    assert not diagnostics


@pytest.mark.parametrize("relative", [False, True])
def test_measured_path_forms_and_low_coverage_preserved(installed_project, relative):
    project = installed_project
    bridge = _bridge(project)
    name = os.path.relpath(project.installed, project.snapshot) if relative else str(project.installed)
    raw = {"files": {name: {"summary": {"percent_covered": 12.5}}}}
    attributed, diagnostics = _normalize(project, bridge, raw)
    assert attributed["files"][str(project.source)]["summary"]["percent_covered"] == 12.5
    assert not diagnostics


def _passed_observation(project):
    return {
        "exit_code": 0,
        "collected": ["tests/test_math.py::test_add"],
        "records": [{"nodeid": "tests/test_math.py::test_add", "phase": "call", "outcome": "passed"}],
        "coverage": {"files": {str(project.installed): {"summary": {"percent_covered": 100}}}},
    }


def test_controller_wires_owned_directories_and_preserves_raw_observation(installed_project, tmp_path, monkeypatch):

    project = installed_project
    monkeypatch.chdir(project.snapshot)
    observation = tmp_path / "observation.json"
    planned = installed_coverage.plan_installed_coverage(
        [project.source], snapshot=project.snapshot, site_packages=project.site
    )
    monkeypatch.setattr(portable_worker, "plan_installed_coverage", lambda *args, **kwargs: planned)
    monkeypatch.setattr(
        portable_worker,
        "Path",
        lambda path: observation if path == "/opt/specfact/tmp/pytest-observation.json" else Path(path),
    )
    sent = {}

    def command(_member, arguments):
        sent.update(json.loads(arguments[0]))
        return ["native-child"]

    def execute(*_args, **_kwargs):
        observation.write_text(json.dumps(_passed_observation(project)))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(portable_worker, "target_command", command)
    monkeypatch.setattr(portable_worker.subprocess, "run", execute)
    findings = portable_worker.run_portable_pytest(
        [project.source], ("portable-pytest-v2", '{"selectors":["tests/test_math.py"]}')
    )
    assert not findings
    assert sent["coverage_directories"] == [str(project.installed.parent)]
    assert set(sent["coverage_candidates"]) == {str(path.resolve()) for path in project.site.rglob("*.py")}
    assert sent["selectors"] == ["tests/test_math.py"]
    retained = json.loads(observation.read_text())
    assert list(retained["coverage"]["files"]) == [str(project.installed)]
    assert retained["coverage_attribution"]["mappings"][0]["source"] == str(project.source)


def test_owned_namespace_leaf_can_measure_without_importing_package(installed_project):
    project = installed_project
    (project.installed.parent / "__init__.py").unlink()
    _distribution(project.site, "namespace-marker", [], local=False)
    # Remove the absent initializer RECORD row; a PEP420 package needs no initializer.
    record = project.metadata / "RECORD"
    record.write_text("\n".join(line for line in record.read_text().splitlines() if "__init__.py" not in line) + "\n")
    assert "capsule_owned" not in sys.modules
    bridge = _bridge(project)
    assert len(bridge.mappings) == 1
    assert "capsule_owned" not in sys.modules


def test_owned_package_directory_is_verified_once_for_multiple_sources(installed_project, monkeypatch):

    project = installed_project
    other_source = project.source.with_name("other.py")
    other_installed = project.installed.with_name("other.py")
    other_source.write_text("VALUE = 2\n")
    other_installed.write_bytes(other_source.read_bytes())
    with (project.metadata / "RECORD").open("a") as stream:
        stream.write(f"capsule_owned/other.py,{_record_hash(other_installed)},{other_installed.stat().st_size}\n")
    original = installed_coverage._owned_directory
    calls = []

    def count(*args):
        calls.append(args)
        return original(*args)

    monkeypatch.setattr(installed_coverage, "_owned_directory", count)
    bridge = installed_coverage.plan_installed_coverage(
        [project.source, other_source], snapshot=project.snapshot, site_packages=project.site
    )
    assert len(bridge.mappings) == 2
    assert len(calls) == 1


@pytest.mark.parametrize("bad", [None, ["bad"], {1: {}}, {"path": None}])
def test_bad_native_coverage_is_an_actionable_tool_error(installed_project, bad):

    project = installed_project
    bridge = _bridge(project)
    findings = portable_worker._installed_coverage_findings(
        [project.source], bridge, {"coverage": {"files": bad}}, evaluate_portable_pytest_coverage
    )
    assert findings[0].category == "tool_error"
    assert "project_pytest_installed_coverage_unavailable" in findings[0].message


def test_native_worker_accepts_only_contained_coverage_directories(installed_project, monkeypatch):

    project = installed_project
    monkeypatch.setattr(target_pytest, "ROOT", project.site.parent)
    request = {"coverage_directories": [str(project.installed.parent)]}
    assert target_pytest._installed_coverage_directories(request) == [str(project.installed.parent)]
    for path in (project.site, project.snapshot, project.installed):
        with pytest.raises(ValueError, match="installed_coverage_directory_invalid"):
            target_pytest._installed_coverage_directories({"coverage_directories": [str(path)]})


@pytest.mark.parametrize("payload", [{}, {"coverage_candidates": []}], ids=["default", "empty"])
def test_native_coverage_candidates_allow_empty_selection(
    installed_project: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, payload: dict[str, Any]
) -> None:
    """A worker without installed coverage candidates needs no inferred paths."""
    monkeypatch.setattr(target_pytest, "ROOT", installed_project.site.parent)
    assert not _installed_coverage_candidates(payload)


def test_native_coverage_candidates_preserve_attached_absolute_path(
    installed_project: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Preserve the exact contained path selected by the controller."""
    monkeypatch.setattr(target_pytest, "ROOT", installed_project.site.parent)
    candidates = [str(installed_project.installed.resolve())]
    assert _installed_coverage_candidates({"coverage_candidates": candidates}) == candidates


@pytest.mark.parametrize(
    "candidates",
    [None, "module.py", {"path": "module.py"}, ("module.py",), [None], [42], [True], ["capsule_owned/math.py"]],
    ids=["null", "string", "mapping", "tuple", "null-item", "integer-item", "boolean-item", "relative-path"],
)
def test_native_coverage_candidates_reject_malformed_inputs(
    installed_project: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, candidates: Any
) -> None:
    """Reject malformed types and relative paths before constructing coverage mappings."""
    monkeypatch.setattr(target_pytest, "ROOT", installed_project.site.parent)
    with pytest.raises(ValueError, match=r"^project_pytest_coverage_candidate_invalid$"):
        _installed_coverage_candidates({"coverage_candidates": candidates})


@pytest.mark.parametrize("via_symlink", [False, True], ids=["outside-path", "symlink-escape"])
def test_native_coverage_candidates_reject_paths_outside_attached_runtime(
    installed_project: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, via_symlink: bool
) -> None:
    """An absolute spelling inside site-packages cannot authorize an escaping symlink."""
    project = installed_project
    monkeypatch.setattr(target_pytest, "ROOT", project.site.parent)
    candidate = project.source.resolve()
    if via_symlink:
        candidate = project.site / "escaped.py"
        candidate.symlink_to(project.source.resolve())
    with pytest.raises(ValueError, match=r"^project_pytest_coverage_candidate_invalid$"):
        _installed_coverage_candidates({"coverage_candidates": [str(candidate)]})


def test_unexecuted_flat_snapshot_row_does_not_mask_real_installed_coverage(installed_project, tmp_path, monkeypatch):
    project = installed_project
    flat = project.snapshot / "capsule_owned"
    project.source.parent.rename(flat)
    project.source = flat / "math.py"
    (flat / "__init__.py").write_bytes((project.installed.parent / "__init__.py").read_bytes())
    bridge = _bridge(project)
    result, raw = _native_coverage(project, bridge, tmp_path, import_mode="importlib")
    assert result.returncode == 0, result.stdout + result.stderr
    snapshot_row = raw["files"]["capsule_owned/math.py"]
    assert snapshot_row["executed_lines"] == []
    assert snapshot_row["summary"]["percent_covered"] == 0
    attributed, diagnostics = _normalize(project, bridge, raw)
    assert attributed["files"][str(project.source)]["summary"]["percent_covered"] == 100
    assert not diagnostics

    monkeypatch.chdir(project.snapshot)
    assert not evaluate_portable_pytest_coverage([project.source], {"coverage": attributed})
    assert raw["files"]["capsule_owned/math.py"]["summary"]["percent_covered"] == 0


@pytest.fixture(name="aliased_project")
def aliased_project_fixture(installed_project):
    project = installed_project
    project.good = project.source.with_name("good.py")
    project.installed_good = project.installed.with_name("good.py")
    project.good.write_text("VALUE = 7\n")
    project.installed_good.write_bytes(project.good.read_bytes())
    with (project.metadata / "RECORD").open("a") as stream:
        stream.write(f"capsule_owned/good.py,{_record_hash(project.installed_good)},10\n")
    (project.snapshot / "pyproject.toml").write_text('[tool.coverage.paths]\nsource=["src", "*/site-packages"]\n')
    test = project.snapshot / "tests/test_math.py"
    test.write_text(
        test.read_text() + "from capsule_owned.good import VALUE\ndef test_good():\n    assert VALUE == 7\n"
    )
    return project


def _native_relocations(project):
    script = """
import json, os, runpy, sys
from types import SimpleNamespace
import coverage
module, topdir, customer_cwd, candidates = sys.argv[1:]
native = coverage.Coverage(config_file=os.path.join(topdir, "pyproject.toml"))
native.get_data()  # Initialize the same fresh-process path cache as pytest-cov.
plugin = SimpleNamespace(cov_controller=SimpleNamespace(cov=native, topdir=topdir))
relocate = runpy.run_path(module)["_native_coverage_relocations"]
os.chdir(customer_cwd)
receipt = relocate(plugin, json.loads(candidates))
assert os.getcwd() == customer_cwd
print(json.dumps(receipt))
"""
    result = subprocess.run(
        [
            sys.executable,
            "-P",
            "-c",
            script,
            target_pytest.__file__,
            str(project.snapshot),
            str(Path.cwd()),
            json.dumps([str(path.resolve()) for path in project.site.rglob("*.py")]),
        ],
        cwd=project.snapshot,
        text=True,
        capture_output=True,
        check=True,
        timeout=60,
    )
    relocated, diagnostic = json.loads(result.stdout)
    assert not diagnostic
    return relocated


def test_native_coverage_alias_cannot_credit_transformed_source(aliased_project, tmp_path, monkeypatch):
    project = aliased_project
    monkeypatch.chdir(project.snapshot)
    project.source.write_text("def add(left, right):\n    return left - right\n")
    bridge = installed_coverage.plan_installed_coverage(
        [project.source, project.good], snapshot=project.snapshot, site_packages=project.site
    )
    assert bridge.diagnostics[str(project.source)] == "installed_source_differs"
    result, raw = _native_coverage(project, bridge, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert raw["files"]["src/capsule_owned/math.py"]["executed_lines"]
    attributed, diagnostics = installed_coverage.attribute_installed_coverage(
        bridge, raw, snapshot=project.snapshot, relocations=_native_relocations(project)
    )
    assert "coverage_alias_origin_ambiguous" in diagnostics[str(project.source)]
    assert str(project.good) not in diagnostics
    findings = evaluate_portable_pytest_coverage(
        [project.source, project.good], {"coverage": attributed, "coverage_attribution_errors": diagnostics}
    )
    assert findings and findings[0].category == "tool_error"


def test_native_alias_accepts_identical_installed_source(aliased_project, tmp_path, monkeypatch):
    project = aliased_project
    monkeypatch.chdir(project.snapshot)
    bridge = _bridge(project)
    result, raw = _native_coverage(project, bridge, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    attributed, diagnostics = installed_coverage.attribute_installed_coverage(
        bridge, raw, snapshot=project.snapshot, relocations=_native_relocations(project)
    )
    assert not diagnostics
    assert not evaluate_portable_pytest_coverage([project.source], {"coverage": attributed})


def test_unrelated_native_alias_does_not_reject_direct_snapshot_execution(aliased_project, monkeypatch):
    project = aliased_project
    monkeypatch.chdir(project.snapshot)
    project.source.write_text("def add(left, right):\n    return left - right\n")
    (project.snapshot / "pyproject.toml").write_text('[tool.coverage.paths]\nsource=["src", "*/build/src"]\n')
    bridge = _bridge(project)
    assert bridge.diagnostics[str(project.source)] == "installed_source_differs"
    relocations = _native_relocations(project)
    assert relocations[str(project.installed)] == str(project.installed)
    raw = {"files": {str(project.source): {"executed_lines": [1, 2], "summary": {"percent_covered": 100}}}}
    _, diagnostics = installed_coverage.attribute_installed_coverage(
        bridge, raw, snapshot=project.snapshot, relocations=relocations
    )
    assert not diagnostics


def test_native_alias_cannot_clear_post_execution_identity_change(aliased_project, monkeypatch):
    project = aliased_project
    monkeypatch.chdir(project.snapshot)
    bridge = _bridge(project)
    project.source.write_text("CHANGED = True\n")
    raw = {"files": {str(project.source): {"executed_lines": [1, 2], "summary": {"percent_covered": 100}}}}
    _, diagnostics = installed_coverage.attribute_installed_coverage(
        bridge, raw, snapshot=project.snapshot, relocations=_native_relocations(project)
    )
    assert "source_identity_changed_after_execution" in diagnostics[str(project.source)]


@pytest.mark.parametrize("changed", ["source", "installed"])
def test_direct_snapshot_row_cannot_erase_post_plan_identity_change(installed_project, changed):
    project = installed_project
    bridge = _bridge(project)
    getattr(project, changed).write_text("CHANGED = True\n")
    raw = {"files": {str(project.source): {"executed_lines": [1], "summary": {"percent_covered": 100}}}}
    _, diagnostics = installed_coverage.attribute_installed_coverage(
        bridge, raw, snapshot=project.snapshot, relocations={str(project.installed): str(project.installed)}
    )
    assert diagnostics[str(project.source)] == "source_identity_changed_after_execution"


def test_missing_native_alias_api_retains_observation_and_origin_diagnostic(monkeypatch, tmp_path):
    monkeypatch.setattr(target_pytest, "SNAPSHOT_ROOT", tmp_path)
    observer = target_pytest.Observer()
    observer.coverage_origin["candidates"] = ["/opt/specfact/project-runtime/site-packages/pkg/app.py"]
    observer.records = [{"nodeid": "test_app.py::test_app", "phase": "call", "outcome": "passed"}]
    plugin = SimpleNamespace(
        cov_controller=SimpleNamespace(cov=object(), topdir=str(tmp_path)), options=SimpleNamespace(cov_fail_under=80)
    )
    config = SimpleNamespace(
        rootpath=tmp_path, getini=lambda _name: [], pluginmanager=SimpleNamespace(getplugin=lambda _name: plugin)
    )
    observer.pytest_sessionfinish(SimpleNamespace(config=config), 0)
    assert observer.records[0]["outcome"] == "passed"
    assert observer.pytest_root == "."
    assert observer.coverage_threshold == 80
    assert not observer.coverage_origin["relocations"]
    assert observer.coverage_origin["diagnostic"] == "coverage_origin_unavailable:AttributeError"
    assert target_pytest._native_coverage_relocations(None, []) == ({}, "")


def test_native_alias_uses_coverage_topdir_and_restores_customer_cwd(aliased_project, tmp_path, monkeypatch):
    project = aliased_project
    elsewhere = tmp_path / "customer-cwd"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    relocations = _native_relocations(project)
    assert Path(relocations[str(project.installed)]).resolve() == project.source.resolve()
    assert Path.cwd() == elsewhere


def test_native_alias_cannot_credit_renamed_unmatched_source(aliased_project, tmp_path, monkeypatch):
    project = aliased_project
    destination = project.snapshot / "src/original/math.py"
    destination.parent.mkdir()
    project.source.rename(destination)
    project.source = destination
    project.source.write_text("def add(left, right):\n    return left - right\n")
    (project.snapshot / "pyproject.toml").write_text(
        '[tool.coverage.paths]\nsource=["src/original", "*/site-packages/capsule_owned"]\n'
    )
    bridge = installed_coverage.plan_installed_coverage(
        [project.source, project.good], snapshot=project.snapshot, site_packages=project.site
    )
    result, raw = _native_coverage(project, bridge, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    attributed, diagnostics = installed_coverage.attribute_installed_coverage(
        bridge, raw, snapshot=project.snapshot, relocations=_native_relocations(project)
    )
    assert "coverage_alias_origin_unverified" in diagnostics.get(str(project.source), "")
    monkeypatch.chdir(project.snapshot)
    findings = evaluate_portable_pytest_coverage(
        [project.source, project.good], {"coverage": attributed, "coverage_attribution_errors": diagnostics}
    )
    assert any(
        finding.tool == "pytest" and "coverage_alias_origin_unverified" in finding.message for finding in findings
    )


def test_missing_measured_origin_receipt_cannot_authenticate_snapshot_row(installed_project):
    project = installed_project
    bridge = _bridge(project)
    raw = {"files": {str(project.source): {"executed_lines": [1, 2], "summary": {"percent_covered": 100}}}}
    _, diagnostics = installed_coverage.attribute_installed_coverage(
        bridge, raw, snapshot=project.snapshot, relocations={str(project.installed): str(project.installed)}
    )
    assert diagnostics[str(project.source)] == "coverage_origin_unavailable"


@pytest.fixture(name="installed_single_module")
def installed_single_module_fixture(tmp_path: Path) -> SimpleNamespace:
    snapshot, site = tmp_path / "snapshot", tmp_path / "runtime/site-packages"
    snapshot.mkdir()
    site.mkdir(parents=True)
    source, installed = snapshot / "standalone.py", site / "standalone.py"
    source.write_text("def answer():\n    return 42\n")
    installed.write_bytes(source.read_bytes())
    metadata = _distribution(site, "standalone-owned", [installed])
    foreign = site / "unrelated.py"
    foreign.write_text("VALUE = 99\n")
    _distribution(site, "unrelated-owned", [foreign], local=False)
    tests = snapshot / "tests"
    tests.mkdir()
    (tests / "test_math.py").write_text(
        "import standalone, unrelated\ndef test_answer():\n"
        "    assert standalone.answer() == 42\n    assert unrelated.VALUE == 99\n"
    )
    return SimpleNamespace(snapshot=snapshot, site=site, source=source, installed=installed, metadata=metadata)


@pytest.mark.parametrize("layout", ["root", "src"])
def test_native_single_module_keeps_narrow_measurement_and_verified_attribution(
    installed_single_module, tmp_path, layout
):
    project = installed_single_module
    if layout == "src":
        target = project.snapshot / "src/standalone.py"
        target.parent.mkdir()
        project.source.rename(target)
        project.source = target
    bridge = _bridge(project)
    assert len(bridge.mappings) == 1, bridge.diagnostics
    assert bridge.directories == ()
    assert bridge.modules == ("standalone",)
    assert str(project.installed) in bridge.measured_origins
    result, raw = _native_coverage(project, bridge, tmp_path, import_mode="importlib")
    assert result.returncode == 0, result.stdout + result.stderr
    _assert_single_module_attribution(project, bridge, raw)


def _assert_single_module_attribution(project, bridge, raw):
    original = json.dumps(raw, sort_keys=True)
    assert not any(path.endswith("unrelated.py") for path in raw["files"])
    attributed, diagnostics = _normalize(project, bridge, raw)
    assert not diagnostics
    assert attributed["files"][str(project.source)]["summary"]["percent_covered"] == 100
    assert json.dumps(raw, sort_keys=True) == original


@pytest.mark.parametrize("invalid", ["duplicate-source", "duplicate-owner", "content", "module-name"])
def test_single_module_identity_rejection_keeps_measurement_closed(installed_single_module, invalid):
    project = installed_single_module
    if invalid == "duplicate-source":
        duplicate = project.snapshot / "src/standalone.py"
        duplicate.parent.mkdir()
        duplicate.write_bytes(project.source.read_bytes())
    elif invalid == "duplicate-owner":
        _distribution(project.site, "second-owner", [project.installed])
    elif invalid == "content":
        project.source.write_text("def answer():\n    return 0\n")
    else:
        source = project.source.with_name("not-a-module.py")
        installed = project.installed.with_name(source.name)
        project.source.rename(source)
        project.installed.rename(installed)
        project.source = source
        (project.metadata / "RECORD").write_text(
            f"{installed.name},{_record_hash(installed)},{installed.stat().st_size}\n"
        )
    bridge = _bridge(project)
    assert not bridge.mappings
    assert not getattr(bridge, "modules", ())
    assert not bridge.directories
    assert str(project.source) in bridge.diagnostics


@pytest.mark.parametrize("changed", ["source", "installed"])
def test_single_module_changed_after_execution_cannot_receive_credit(installed_single_module, tmp_path, changed):
    project = installed_single_module
    bridge = _bridge(project)
    result, raw = _native_coverage(project, bridge, tmp_path, import_mode="importlib")
    assert result.returncode == 0, result.stdout + result.stderr
    getattr(project, changed).write_text("def answer():\n    return -1\n")
    attributed, diagnostics = _normalize(project, bridge, raw)
    assert diagnostics[str(project.source)] == "source_identity_changed_after_execution"
    assert str(project.source) not in attributed["files"]
