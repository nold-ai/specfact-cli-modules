from __future__ import annotations

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[3]
MAPPING = "openspec/changes/code-review-17-project-runtime-bootstrap/requirements-evidence.yaml"
SELECTORS = ["tests/example.py::test_first", "tests/example.py::test_second"]


@pytest.fixture(autouse=True)
def record_selector(request, record_property):
    record_property("specfact.selector", request.node.nodeid)


def native_job():
    path = ROOT / ".github/workflows/native-hatch-acceptance.yml"
    assert path.is_file(), "Mandatory native Hatch acceptance workflow is missing"
    workflow = yaml.safe_load(path.read_text())
    return workflow, workflow["jobs"]["native-hatch"]


def test_native_hatch_job_binds_exact_head_and_separate_interpreters():
    workflow, job = native_job()
    assert workflow["permissions"] == {"contents": "read"}
    assert not job.get("needs")
    assert not job.get("continue-on-error", False)
    checkout = next(s for s in job["steps"] if s.get("uses", "").startswith("actions/checkout@"))
    assert checkout["with"] == {
        "ref": "${{ github.event.pull_request.head.sha || github.sha }}",
        "fetch-depth": 0,
        "persist-credentials": False,
    }
    setups = {s["id"]: s["with"]["python-version"] for s in job["steps"] if "python-version" in s.get("with", {})}
    assert setups == {"project-python": "3.11.15", "controller-python": "3.12.13"}
    assert any("hatch==1.18.1" in s.get("run", "") for s in job["steps"])
    step = next(s for s in job["steps"] if s.get("name") == "Run mapped native Hatch acceptance")
    assert step["env"]["SPECFACT_HATCH_PROJECT_PYTHON"] == "${{ steps.project-python.outputs.python-path }}"
    assert "SPECFACT_HATCH_EXECUTABLE" in step["env"]
    assert "SPECFACT_HATCH_PROOF_WORKSPACE" in step["env"]
    artifacts = [s for s in job["steps"] if s.get("uses", "").startswith("actions/upload-artifact@")]
    assert len(artifacts) == 1
    assert artifacts[0]["if"] == "always()"
    assert "receipt.json" in artifacts[0]["with"]["path"]
    assert "junit.xml" in artifacts[0]["with"]["path"]


@pytest.mark.parametrize("result,expected", [("success", 0), ("failure", 1), ("cancelled", 1), ("skipped", 1)])
def test_native_hatch_result_blocks_quality_without_replacing_security(result, expected):
    workflow = yaml.safe_load((ROOT / ".github/workflows/pr-orchestrator.yml").read_text())
    assert "native-hatch" in workflow["jobs"], "Required native Hatch prerequisite is missing"
    assert workflow["jobs"]["native-hatch"]["uses"] == "./.github/workflows/native-hatch-acceptance.yml"
    quality = workflow["jobs"]["quality"]
    assert {"native-hatch", "native-scope", "customer-capsules", "verify-module-signatures"} <= set(quality["needs"])
    step = next(s for s in quality["steps"] if s.get("name") == "Require native Hatch acceptance")
    assert step["env"]["NATIVE_HATCH_RESULT"] == "${{ needs.native-hatch.result }}"
    completed = subprocess.run(
        ["bash", "-c", step["run"]], env={"NATIVE_HATCH_RESULT": result}, capture_output=True, text=True, check=False
    )
    assert completed.returncode == expected, completed.stdout + completed.stderr


def junit(selectors, outcome):
    suite = ET.Element("testsuite")
    for index, selector in enumerate(selectors):
        case = ET.SubElement(suite, "testcase", name=f"case{index}")
        properties = ET.SubElement(case, "properties")
        ET.SubElement(properties, "property", name="specfact.selector", value=selector)
        if index == 0 and outcome in {"skipped", "failure", "error"}:
            ET.SubElement(case, outcome)
    return ET.tostring(suite, encoding="unicode")


@pytest.mark.parametrize(
    "outcome",
    [
        "complete",
        "skipped",
        "failure",
        "error",
        "missing",
        "duplicate",
        "extra",
        "nonzero",
        "no-report",
        "empty-mapping",
        "duplicate-mapping",
        "archived-mapping",
        "ambiguous-archive",
    ],
)
def test_native_hatch_accepts_only_complete_exact_mapping(tmp_path, outcome):
    _, job = native_job()
    step = next(s for s in job["steps"] if s.get("name") == "Run mapped native Hatch acceptance")
    program = step["run"]
    prefix = "hatch run python - <<'PY'\n"
    assert program.startswith(prefix) and program.rstrip().endswith("\nPY")
    program = program[len(prefix) :].rstrip()[:-3]
    mapping = tmp_path / MAPPING
    mapping.parent.mkdir(parents=True)
    selected = (
        [] if outcome == "empty-mapping" else SELECTORS + (SELECTORS[:1] if outcome == "duplicate-mapping" else [])
    )
    mapping.write_text(
        json.dumps(
            {
                "schema_version": "2",
                "requirements": {
                    "native": {
                        "verification_cases": [
                            {"method": "test", "selector": {"runner": "pytest", "node_id": node}} for node in selected
                        ]
                        + [{"method": "inspection"}]
                    }
                },
            }
        )
    )
    if outcome in {"archived-mapping", "ambiguous-archive"}:
        archive = tmp_path / "openspec/changes/archive/2026-01-01-code-review-17-project-runtime-bootstrap"
        archive.mkdir(parents=True)
        archived = archive / mapping.name
        mapping.rename(archived)
        if outcome == "ambiguous-archive":
            other = archive.with_name("2026-01-02-code-review-17-project-runtime-bootstrap")
            other.mkdir()
            (other / mapping.name).write_bytes(archived.read_bytes())
    observed = (
        SELECTORS[:1]
        if outcome == "missing"
        else SELECTORS
        + (SELECTORS[:1] if outcome == "duplicate" else ["tests/example.py::test_extra"] if outcome == "extra" else [])
    )
    source = tmp_path / "source.xml"
    source.write_text(junit(observed, outcome))
    fake = tmp_path / "pytest.py"
    fake.write_text(
        "import json,os,shutil,sys\nfrom pathlib import Path\n"
        "Path('pytest-argv.json').write_text(json.dumps(sys.argv[1:]))\n"
        "if os.environ['OUTCOME'] != 'no-report':\n"
        " target=Path(sys.argv[sys.argv.index('--junitxml')+1]); target.parent.mkdir(parents=True,exist_ok=True)\n"
        " shutil.copyfile(os.environ['SOURCE_XML'],target)\n"
        "raise SystemExit(7 if os.environ['OUTCOME']=='nonzero' else 0)\n"
    )
    report = tmp_path / "out/junit.xml"
    completed = subprocess.run(
        [sys.executable, "-c", program],
        cwd=tmp_path,
        env=os.environ
        | {
            "PYTHONPATH": str(tmp_path),
            "OUTCOME": outcome,
            "SOURCE_XML": str(source),
            "NATIVE_HATCH_JUNIT": str(report),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert (completed.returncode == 0) == (outcome in {"complete", "archived-mapping"}), (
        completed.stdout + completed.stderr
    )
    if outcome == "ambiguous-archive":
        assert "exactly one" in completed.stdout + completed.stderr
    calls = tmp_path / "pytest-argv.json"
    if outcome in {"empty-mapping", "duplicate-mapping", "ambiguous-archive"}:
        assert not calls.exists()
    else:
        arguments = json.loads(calls.read_text())
        assert [s for s in arguments if "::" in s] == SELECTORS
