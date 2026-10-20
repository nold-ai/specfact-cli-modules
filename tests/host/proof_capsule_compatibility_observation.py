"""Whole-process compatibility proof with genuine native runtime construction."""

from __future__ import annotations

import copy
import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import sysconfig
import tomllib
import venv
from pathlib import Path

import pytest
import specfact_cli
from specfact_cli.registry.module_installer import _bundled_public_key_path

from specfact_code_review.run import runtime_builder
from specfact_code_review.run.runtime_artifacts import load_runtime
from specfact_code_review.run.runtime_compatibility import analyzer_dependency_conflicts
from specfact_code_review.run.runtime_domains import member_dependency_graphs
from specfact_code_review.run.runtime_models import ProjectPlan, ProjectRuntimeError
from tests.host import capsule_compatibility_native_fixtures as native
from tests.host.proof_capsule_compatibility_publisher import legacy_summary, run_publisher
from tests.support.capsule_review_fixtures import REPO_ROOT, independent_review_job, isolated_python_site_packages


def installed_native_fixture(tmp_path, *, review_exit=17, fail_head=False, case="valid"):
    """Install real sources; synthetic authority is limited to declared external seams."""
    trusted = tmp_path / "trusted"
    trusted.mkdir(mode=0o700)
    for name in ("home", "tmp", "subject"):
        (trusted / name).mkdir(mode=0o700)
    venv.create(trusted / "venv", with_pip=False)
    site = isolated_python_site_packages(trusted / "venv/bin/python")
    package = trusted / "home/.specfact/modules/specfact-code-review"
    source = Path(runtime_builder.__file__).parents[1]
    shutil.copytree(source, package / "src/specfact_code_review", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copyfile(source.parents[1] / "module-package.yaml", package / "module-package.yaml")
    shutil.copyfile(native.__file__, site / "synthetic_compatibility_fixture.py")
    shutil.copytree(
        Path(specfact_cli.__file__).parent, site / "specfact_cli", ignore=shutil.ignore_patterns("__pycache__")
    )
    keys = site / "specfact_cli/resources/keys"
    keys.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_bundled_public_key_path(), keys / "module-signing-public.pem")
    paths = [package / "src", Path(sysconfig.get_path("purelib"))]
    (site / "synthetic-installation.pth").write_text("\n".join(map(str, paths)) + "\n")
    (site / "sitecustomize.py").write_text(
        "import sys\n"
        "if sys.argv[0].endswith('reviewer.py'):\n"
        "    from synthetic_compatibility_fixture import install_synthetic_boundaries\n"
        "    install_synthetic_boundaries()\n"
    )
    (trusted / "fixture-config.json").write_text(
        json.dumps({"review_exit": review_exit, "fail_head": fail_head, "case": case})
    )
    (trusted / "project.toml").write_text('manager = "hatch"\nenvironment = "default"\n')
    prepare_subject(trusted / "subject")
    write_installation_receipt(trusted, source, site)
    if case == "source_drift":
        path = package / "src/specfact_code_review/run/runtime_compatibility.py"
        path.write_text(path.read_text() + "\n# synthetic source drift\n")
    return trusted


def prepare_subject(subject):
    (subject / "pyproject.toml").write_text(
        '[project]\nname = "compatibility-fixture"\nversion = "0.1.0"\nrequires-python = ">=3.12,<3.13"\n'
        '[tool.hatch.envs.default]\npython = "3.12"\n'
    )
    (subject / "governed.py").write_text("def value():\n    return 1\n")
    commands = [
        ("init", "-q"),
        ("config", "user.name", "Synthetic Fixture"),
        ("config", "user.email", "fixture@example.invalid"),
        ("config", "commit.gpgsign", "false"),
        ("add", "."),
        ("commit", "-qm", "Synthetic baseline"),
    ]
    for arguments in commands:
        subprocess.run(["git", "-C", str(subject), *arguments], check=True, capture_output=True)
    (subject / "governed.py").write_text("def value():\n    return 2\n")
    subprocess.run(["git", "-C", str(subject), "add", "."], check=True, capture_output=True)


def run_preparation_recipe(trusted, replacement=""):
    recipe = next(step["run"] for step in independent_review_job()["steps"] if step.get("id") == "independent_review")
    if replacement:
        original = "prepare_runtime(plan, runtime=runtime)"
        assert recipe.count(original) == 1
        recipe = recipe.replace(original, replacement)
    completed = subprocess.run(
        ["bash", "-c", recipe],
        cwd=trusted,
        env=dict(os.environ, TRUSTED_ROOT=str(trusted)),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    (trusted / "recipe.stdout").write_text(completed.stdout)
    (trusted / "recipe.stderr").write_text(completed.stderr)
    return completed


def read_events(trusted):
    return [json.loads(line) for line in (trusted / "native-events.jsonl").read_text().splitlines()]


def test_preparation_writes_bound_native_observations(tmp_path):
    trusted = installed_native_fixture(tmp_path)
    result = run_preparation_recipe(trusted)
    assert result.returncode == 17, result.stdout + result.stderr + (trusted / "preparation.private.log").read_text()
    events = read_events(trusted)
    assert [event["removed"] for event in events if event["event"] == "worker_cleanup"] == [True, True]
    assert [event["removed"] for event in events if event["event"] == "scope_cleanup"] == [True]
    assert native.CANARY not in result.stdout + result.stderr
    assert native.CANARY in (trusted / "review.private.log").read_text()
    receipt = trusted / "compatibility.private.json"
    assert receipt.is_file(), "Successful genuine preparation wrote no compatibility.private.json"
    assert receipt.stat().st_mode & 0o777 == 0o600


def test_preparation_receipt_identity_values(tmp_path):
    trusted = installed_native_fixture(tmp_path)
    run_preparation_recipe(trusted)
    receipt = trusted / "compatibility.private.json"
    assert receipt.is_file(), "Successful genuine preparation wrote no compatibility.private.json"
    observed = json.loads(receipt.read_text())
    report = json.loads((trusted / "review.private.json").read_text())
    assert set(observed) == {"schema", "sides"}
    assert observed["schema"] == "compatibility-observation-v1"
    for side in observed["sides"]:
        binding = side["binding"]
        report_binding = report["scope_evidence"]["project_runtime"][binding["side"]]
        assert binding["descriptor_identity"] == report_binding["identity"]
        assert binding["project_identity"] == report_binding["project_identity"]
        assert binding["environment_id"] == native.ENVIRONMENT
        assert binding["source_roots"] == report_binding["source_roots"]


def test_preparation_receipt_predicate_values(tmp_path):
    trusted = installed_native_fixture(tmp_path)
    run_preparation_recipe(trusted)
    receipt = trusted / "compatibility.private.json"
    assert receipt.is_file(), "Successful genuine preparation wrote no compatibility.private.json"
    observed = json.loads(receipt.read_text())
    report = json.loads((trusted / "review.private.json").read_text())
    assert [side["binding"]["side"] for side in observed["sides"]] == ["base", "head"]
    for side in observed["sides"]:
        binding = side["binding"]
        assert side["status"] == "observed"
        assert side["signed_reference_matches"] is True
        assert side["clearing_subsets"] == [["contracts_pinned_transitive"]]
        assert side["native_conflicts"] == {"contracts": report["analyzer_evidence"][0][binding["side"]]["diagnostic"]}
        assert [witness["predicate"] for witness in side["witnesses"]] == [
            "pinned_version_string_inequality",
            "active_requirement_rejects_target",
        ]
        assert {witness["category"] for witness in side["witnesses"]} == {"contracts_pinned_transitive"}


@pytest.mark.parametrize(
    "case", ["conflict", "clear", "equivalent_string", "missing", "satisfied", "prerelease", "false_marker"]
)
def test_native_predicates_and_graphs(tmp_path, case):
    inventory = native.native_inventory(tmp_path, "clear")
    version = native.reference_versions()["z3-solver"]
    z3 = inventory["installed"][1]["metadata"]
    configure_predicate_case(inventory, tmp_path, case, version)
    conflicts = analyzer_dependency_conflicts(inventory, tmp_path)
    expected = {}
    if case == "conflict":
        expected["contracts"] = (
            "project_analyzer_dependency_incompatible:"
            f"z3-solver: target={z3['version']}, required=>={version} by crosshair-tool; "
            f"z3-solver: target={z3['version']}, sealed entry={version}"
        )
    if case == "equivalent_string":
        expected["contracts"] = (
            f"project_analyzer_dependency_incompatible:z3-solver: target={version}.0, sealed entry={version}"
        )
    assert conflicts == expected
    graphs = member_dependency_graphs(inventory, tmp_path)
    assert set(graphs) == {"pylint", "basedpyright", "crosshair", "pytest-observe"}
    assert {row["name"] for row in graphs["crosshair"]["installed"]} >= {"crosshair-tool", "z3-solver"}
    assert graphs["crosshair"]["sealed_imports"] == ["crosshair_tool", "z3_solver"]


def configure_predicate_case(inventory, tmp_path, case, version):
    z3 = inventory["installed"][1]["metadata"]
    if case == "conflict":
        z3["version"] = "0.0.0+private.compatibility.canary"
    if case == "equivalent_string":
        z3["version"] = version + ".0"
    if case == "missing":
        inventory["installed"].pop(1)
    if case in {"satisfied", "prerelease", "false_marker"}:
        extra_version = "1.1rc1" if case == "prerelease" else "2.0"
        inventory["installed"].append(native.write_distribution(tmp_path, "private-dependency", extra_version))
        metadata = next(tmp_path.glob("crosshair_tool-*.dist-info/METADATA"))
        requirement = (
            'private-dependency<1; sys_platform == "win32"' if case == "false_marker" else "private-dependency>=1.0"
        )
        with metadata.open("a") as stream:
            stream.write(f"Requires-Dist: {requirement}\n")


@pytest.mark.parametrize("case", ["conflict", "basedpyright", "missing_graph_payload"])
def test_reference_comparison_requires_whole_native_clear(tmp_path, case):
    inventory = native.native_inventory(tmp_path)
    original = copy.deepcopy(inventory)
    if case == "basedpyright":
        inventory["installed"][4]["metadata"]["version"] = "0.0.0"
        original = copy.deepcopy(inventory)
    if case == "missing_graph_payload":
        next(tmp_path.glob("astroid-*.dist-info/RECORD")).unlink()
        with pytest.raises(ProjectRuntimeError, match="project_analyzer_import_inventory_missing"):
            native.native_trial(inventory, tmp_path)
        assert inventory == original
        return
    conflicts, graphs = native.native_trial(inventory, tmp_path)
    assert set(conflicts) == ({"basedpyright"} if case == "basedpyright" else set())
    assert set(graphs) == {"pylint", "basedpyright", "crosshair", "pytest-observe"}
    assert inventory == original
    resource = Path(runtime_builder.__file__).parents[1] / "resources/contracts/pr-range-v1-toolchain-lock.json"
    assert hashlib.sha256(resource.read_bytes()).hexdigest() == native.REFERENCE_HASH


@pytest.mark.parametrize("review_exit,fail_head", [(17, False), (124, False), (17, True)])
def test_preparation_preserves_failure_and_cleanup(tmp_path, review_exit, fail_head):
    trusted = installed_native_fixture(tmp_path, review_exit=review_exit, fail_head=fail_head)
    result = run_preparation_recipe(trusted)
    assert result.returncode == (1 if fail_head else review_exit), result.stdout + result.stderr
    events = read_events(trusted)
    assert [event["removed"] for event in events if event["event"] == "worker_cleanup"] == [True, True]
    assert [event["removed"] for event in events if event["event"] == "scope_cleanup"] == [True]
    assert (trusted / "review-attempted").exists() is not fail_head
    assert native.CANARY not in result.stdout + result.stderr


@pytest.mark.parametrize("field", ["project", "worker", "environment", "payload"])
def test_observation_refuses_unbound_native_state(tmp_path, field):
    trusted = installed_native_fixture(tmp_path)
    result = run_preparation_recipe(trusted)
    assert result.returncode == 17, result.stdout + result.stderr
    descriptor_path = next(
        (trusted / "home/.cache/specfact/code-review/project-runtimes-v2").glob("*/project-runtime.json")
    )
    descriptor = json.loads(descriptor_path.read_text())
    document = descriptor["project"]
    plan = ProjectPlan(root=trusted / "subject", **document)
    environment = descriptor["environment_id"]
    worker = descriptor["worker_identity"]
    if field == "project":
        plan = ProjectPlan(root=trusted / "subject", manager="hatch", source_identity="foreign")
    if field == "worker":
        worker = "foreign"
    if field == "environment":
        environment = "linux-x86_64-cp313"
    if field == "payload":
        (descriptor_path.parent / "inventory.json").write_text("{}")
    with pytest.raises(ProjectRuntimeError):
        load_runtime(descriptor_path, plan=plan, environment_id=environment, worker_identity=worker)


def test_native_owner_is_explicit_and_ordinary_collection_isolated(tmp_path):
    config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    command = config["tool"]["hatch"]["envs"]["default"]["scripts"]["test"]
    native_command = command.split(" && ")[1]
    assert "tests/host/proof_capsule_compatibility_observation.py" in native_command
    assert "tests/host/proof_capsule_compatibility_publisher.py" in native_command
    tripwire = tmp_path / "import_tripwire.py"
    tripwire.write_text(
        "import importlib.abc,sys\n"
        "class BlockNativeProof(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self,fullname,path=None,target=None):\n"
        "        blocked=('capsule_compatibility_native_fixtures', 'proof_capsule_compatibility_')\n"
        "        if any(part in fullname for part in blocked):\n"
        "            raise AssertionError('ordinary discovery imported a native compatibility owner')\n"
        "sys.meta_path.insert(0,BlockNativeProof())\n"
    )
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests", "-p", "import_tripwire"],
        cwd=REPO_ROOT,
        env=dict(os.environ, PYTHONPATH=str(tmp_path)),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def write_installation_receipt(trusted, source, site):
    sources = {"core": Path(specfact_cli.__file__).parent, "reviewer": source}
    manifests = {
        owner: {
            str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts
        }
        for owner, root in sources.items()
    }
    key = _bundled_public_key_path()
    receipt = {
        "authority": "synthetic_installation_and_acquisition",
        "interpreter": sys.executable,
        "python": sys.version,
        "core_source_version": specfact_cli.__version__,
        "core_distribution_version": importlib.metadata.version("specfact-cli"),
        "sources": {owner: str(root) for owner, root in sources.items()},
        "installed_core": str(site / "specfact_cli"),
        "public_key_source": str(key),
        "public_key_sha256": hashlib.sha256(key.read_bytes()).hexdigest(),
        "source_manifests": manifests,
    }
    (trusted / "installation.private.json").write_text(json.dumps(receipt, sort_keys=True))


@pytest.mark.parametrize("case", ["verifier_false", "verifier_error", "source_drift"])
def test_preparation_refuses_untrusted_observation(tmp_path, case):
    trusted = installed_native_fixture(tmp_path, case=case)
    result = run_preparation_recipe(trusted)
    assert result.returncode == 17, result.stdout + result.stderr
    events = read_events(trusted)
    assert [event["removed"] for event in events if event["event"] == "worker_cleanup"] == [True, True]
    assert [event["removed"] for event in events if event["event"] == "scope_cleanup"] == [True]
    receipt = trusted / "compatibility.private.json"
    assert receipt.is_file(), "Successful genuine preparation wrote no compatibility.private.json"
    assert json.loads(receipt.read_text()) == {
        "schema": "compatibility-observation-v1",
        "sides": [{"status": "unavailable", "side": side} for side in ("base", "head")],
    }
    assert native.CANARY not in result.stdout + result.stderr


@pytest.mark.parametrize("field", ["root", "identity", "descriptor_path", "descriptor"])
def test_preparation_rejects_modified_genuine_return(tmp_path, field):
    trusted = installed_native_fixture(tmp_path)
    values = {
        "root": "Path('/private/foreign-root')",
        "identity": "'sha256:' + '0' * 64",
        "descriptor_path": "Path('/private/foreign-project-runtime.json')",
        "descriptor": "{**value.descriptor, 'worker_identity': 'foreign'}",
    }
    replacement = (
        "(lambda value: __import__('dataclasses').replace(value, "
        + field
        + "="
        + values[field]
        + "))(prepare_runtime(plan, runtime=runtime))"
    )
    result = run_preparation_recipe(trusted, replacement)
    assert result.returncode == 17, result.stdout + result.stderr
    events = read_events(trusted)
    assert [event["removed"] for event in events if event["event"] == "worker_cleanup"] == [True, True]
    assert [event["removed"] for event in events if event["event"] == "scope_cleanup"] == [True]
    receipt = trusted / "compatibility.private.json"
    assert receipt.is_file(), "Successful genuine preparation wrote no compatibility.private.json"
    assert json.loads(receipt.read_text()) == {
        "schema": "compatibility-observation-v1",
        "sides": [{"status": "unavailable", "side": side} for side in ("base", "head")],
    }


def test_preparation_does_not_reuse_a_prior_pair(tmp_path):
    trusted = installed_native_fixture(tmp_path, fail_head=True)
    receipt = trusted / "compatibility.private.json"
    stale = {
        "schema": "compatibility-observation-v1",
        "sides": [{"status": "stale", "side": side} for side in ("base", "head")],
    }
    receipt.write_text(json.dumps(stale))
    receipt.chmod(0o600)
    result = run_preparation_recipe(trusted)
    assert result.returncode == 1
    assert not (trusted / "review-attempted").exists()
    assert not receipt.exists() or json.loads(receipt.read_text()) != stale


def test_native_preparation_to_final_publisher(tmp_path):
    trusted = installed_native_fixture(tmp_path)
    result = run_preparation_recipe(trusted)
    assert result.returncode == 17, result.stdout + result.stderr
    assert (trusted / "compatibility.private.json").is_file(), "Native preparation transport is absent"
    projected = run_publisher(trusted)
    records = [
        {"side": side, "analyzer": "contracts", "predicate": predicate, "category": "contracts_pinned_transitive"}
        for side in ("base", "head")
        for predicate in ("pinned_version_string_inequality", "active_requirement_rejects_target")
    ]
    assert projected == legacy_summary() | {
        "compatibility_proof": {
            "status": "observed",
            "records": records,
            "reference_comparison": {
                "status": "native_compatibility_clear",
                "substitution_categories": ["contracts_pinned_transitive"],
            },
        }
    }


@pytest.mark.parametrize(
    "category,name,member",
    [
        ("contracts_entry", "crosshair-tool", "contracts"),
        ("contracts_pinned_transitive", "z3-solver", "contracts"),
        ("pylint_entry", "pylint", "pylint"),
        ("pylint_pinned_transitive", "astroid", "pylint"),
    ],
)
def test_preparation_constructs_every_fixed_native_category(tmp_path, category, name, member):
    trusted = installed_native_fixture(tmp_path, case=category)
    result = run_preparation_recipe(trusted)
    assert result.returncode == 17, result.stdout + result.stderr
    events = read_events(trusted)
    verified = [event for event in events if event["event"] == "verified_prepared"]
    version = native.reference_versions()[name]
    for event in verified:
        assert set(event["native_conflicts"]) == {member}
        assert (
            f"{name}: target=0.0.0+private.compatibility.canary, sealed entry={version}"
            in event["native_conflicts"][member]
        )
        assert event["member_domains"] == ["basedpyright", "crosshair", "pylint", "pytest-observe"]
    assert len(verified) == 2
    assert [event["removed"] for event in events if event["event"] == "worker_cleanup"] == [True, True]


@pytest.mark.parametrize("category", list(native.FIXED_CATEGORIES.values()))
def test_preparation_attributes_every_fixed_native_category(tmp_path, category):
    trusted = installed_native_fixture(tmp_path, case=category)
    result = run_preparation_recipe(trusted)
    assert result.returncode == 17, result.stdout + result.stderr
    verified = [event for event in read_events(trusted) if event["event"] == "verified_prepared"]
    receipt = trusted / "compatibility.private.json"
    assert receipt.is_file(), "Successful genuine preparation wrote no compatibility.private.json"
    observed = json.loads(receipt.read_text())
    for side in observed["sides"]:
        assert {witness["category"] for witness in side["witnesses"]} == {category}
        assert side["clearing_subsets"] == [[category]]
        assert side["native_conflicts"] == verified[0]["native_conflicts"]


def test_preparation_verifies_payload_after_genuine_return(tmp_path):
    trusted = installed_native_fixture(tmp_path)
    replacement = (
        "(lambda value: ((value.root / 'inventory.json').write_text('{}'), value)[1])"
        "(prepare_runtime(plan, runtime=runtime))"
    )
    result = run_preparation_recipe(trusted, replacement)
    assert result.returncode == 17, result.stdout + result.stderr
    events = read_events(trusted)
    assert len([event for event in events if event["event"] == "native_verification_rejected"]) == 2
    assert [event["removed"] for event in events if event["event"] == "worker_cleanup"] == [True, True]
    assert [event["removed"] for event in events if event["event"] == "scope_cleanup"] == [True]
    receipt = trusted / "compatibility.private.json"
    assert receipt.is_file(), "Successful genuine preparation wrote no compatibility.private.json"
    assert json.loads(receipt.read_text()) == {
        "schema": "compatibility-observation-v1",
        "sides": [{"status": "unavailable", "side": side} for side in ("base", "head")],
    }
