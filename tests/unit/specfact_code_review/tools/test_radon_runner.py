from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from pytest import MonkeyPatch
from radon.cli.tools import cc_to_dict
from radon.complexity import cc_visit

from specfact_code_review.tools import radon_runner
from specfact_code_review.tools.basedpyright_runner import run_basedpyright
from specfact_code_review.tools.pylint_runner import run_pylint
from specfact_code_review.tools.radon_runner import _kiss_metric_findings, run_radon
from tests.unit.specfact_code_review.tools.helpers import assert_tool_run, completed_process, create_noisy_file


def test_radon_snapshot_config_cannot_filter_complexity_results(tmp_path: Path) -> None:
    from specfact_code_review.run import scope

    (tmp_path / "radon.cfg").write_text("[radon]\nexclude=src/*\nignore=tests/*\n", encoding="utf-8")
    projection = scope.project_radon_policy(tmp_path, expected_version="6.0.1")

    assert projection.values["exclude"] == ""
    assert projection.values["ignore"] == ""


def test_radon_uses_sealed_full_result_options(tmp_path: Path) -> None:
    from specfact_code_review.run import scope

    projection = scope.project_radon_policy(tmp_path, expected_version="6.0.1")

    assert projection.contract == "radon-full-result-v1"
    assert projection.values["cc_ranks"] == ["A", "B", "C", "D", "E", "F"]
    assert projection.values["mi_ranks"] == ["A", "B", "C"]
    assert projection.values["output_file"] is None
    assert projection.control_cwd_empty is True
    assert projection.private_home is True
    assert "RADONCFG" not in projection.environment


def _parameter_count_rules(tmp_path: Path, monkeypatch: MonkeyPatch, source: str) -> set[str]:
    file_path = tmp_path / "commands.py"
    file_path.write_text(source, encoding="utf-8")
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("radon", stdout=json.dumps({str(file_path): []}))),
    )
    return {finding.rule for finding in run_radon([file_path])}


def test_run_radon_returns_empty_when_only_non_python_paths(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    manifest = tmp_path / "module-package.yaml"
    manifest.write_text("name: example\n", encoding="utf-8")
    run_mock = Mock()
    monkeypatch.setattr(subprocess, "run", run_mock)

    result = run_radon([manifest])

    assert isinstance(result, list)
    assert not result

    run_mock.assert_not_called()


def test_run_radon_maps_complexity_thresholds_and_filters_files(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    other_path = tmp_path / "other.py"
    payload = {
        str(file_path): [
            {"type": "function", "name": "warn_me", "complexity": 13, "lineno": 7},
            {"type": "function", "name": "fail_me", "complexity": 16, "lineno": 19},
            {"type": "function", "name": "ok_me", "complexity": 10, "lineno": 27},
        ],
        str(other_path): [
            {"type": "function", "name": "skip_me", "complexity": 20, "lineno": 3},
        ],
    }
    run_mock = Mock(return_value=completed_process("radon", stdout=json.dumps(payload)))
    monkeypatch.setattr(subprocess, "run", run_mock)

    findings = run_radon([file_path])

    assert len(findings) == 2
    assert findings[0].file == str(file_path)
    assert findings[0].severity == "warning"
    assert findings[0].category == "clean_code"
    assert findings[1].severity == "error"
    assert {finding.rule for finding in findings} == {"CC13", "CC16"}
    assert_tool_run(run_mock, ["radon", "cc", "-j", str(file_path)])


def test_run_radon_full_result_executes_and_reconciles_every_sealed_metric_pass(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    file_path = (tmp_path / "target.py").resolve()
    file_path.write_text("VALUE = 1\n", encoding="utf-8")
    payloads = {
        "cc": {str(file_path): []},
        "mi": {str(file_path): {"mi": 100.0, "rank": "A"}},
        "raw": {str(file_path): {"loc": 1, "lloc": 1, "sloc": 1}},
        "hal": {str(file_path): {"total": {"h1": 0, "h2": 0}}},
    }

    def _fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return completed_process("radon", stdout=json.dumps(payloads[command[1]]))

    run_mock = Mock(side_effect=_fake_run)
    monkeypatch.setattr(subprocess, "run", run_mock)

    findings = run_radon([file_path], full_result=True)

    assert not findings
    assert [call.args[0][1] for call in run_mock.call_args_list] == ["cc", "mi", "raw", "hal"]
    for call in run_mock.call_args_list:
        command = call.args[0]
        assert "-j" in command
        assert command[command.index("-e") + 1] == ""
        assert command[command.index("-i") + 1] == ""
        assert command[-1] == str(file_path)


def test_run_radon_returns_no_findings_for_complexity_twelve_or_below(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = {
        str(file_path): [
            {"type": "function", "name": "ok_me", "complexity": 12, "lineno": 11},
        ]
    }
    monkeypatch.setattr(subprocess, "run", Mock(return_value=completed_process("radon", stdout=json.dumps(payload))))

    findings = run_radon([file_path])

    assert isinstance(findings, list)
    assert not findings


def test_run_radon_returns_tool_error_on_parse_error(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    monkeypatch.setattr(
        subprocess, "run", Mock(return_value=completed_process("radon", stdout="not-json", returncode=2))
    )

    findings = run_radon([file_path])

    assert len(findings) == 1
    assert findings[0].category == "tool_error"
    assert findings[0].tool == "radon"


def test_run_radon_emits_kiss_metrics_from_source_shape(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = create_noisy_file(tmp_path)
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("radon", stdout=json.dumps({str(file_path): []}))),
    )

    findings = run_radon([file_path])

    assert {finding.rule for finding in findings} >= {
        "kiss.loc.warning",
        "kiss.nesting.warning",
        "kiss.parameter-count.warning",
    }
    assert {finding.category for finding in findings} == {"kiss"}


def test_run_radon_uses_dedicated_tool_identifier_for_kiss_findings(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = create_noisy_file(tmp_path)
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("radon", stdout=json.dumps({str(file_path): []}))),
    )

    findings = run_radon([file_path])

    kiss_findings = [finding for finding in findings if finding.rule.startswith("kiss.")]
    assert kiss_findings
    assert {finding.tool for finding in kiss_findings} == {"radon-kiss"}


@pytest.mark.parametrize(
    ("source", "expects_parameter_count_warning"),
    [
        (
            """
def callback(ctx: typer.Context, a: str, b: str, c: str, d: str, e: str) -> None:
    return None
""",
            True,
        ),
        (
            """
import typer

app = typer.Typer()

@app.command("run")
def callback(a: str, b: str, c: str, d: str, e: str, f: str) -> None:
    return None
""",
            False,
        ),
        (
            """
@custom.command("run")
def callback(a: str, b: str, c: str, d: str, e: str, f: str) -> None:
    return None
""",
            True,
        ),
    ],
)
def test_run_radon_applies_parameter_count_rule_to_cli_decorators(
    tmp_path: Path, monkeypatch: MonkeyPatch, source: str, expects_parameter_count_warning: bool
) -> None:
    findings = _parameter_count_rules(
        tmp_path,
        monkeypatch,
        source,
    )

    assert ("kiss.parameter-count.warning" in findings) is expects_parameter_count_warning


@pytest.mark.parametrize(
    "relative",
    [
        "packages/specfact-code-review/src/specfact_code_review/run/native_worker.py",
        "tests/unit/specfact_code_review/run/test_native_project_runtime.py",
        "tests/unit/specfact_code_review/run/test_native_project_inventory.py",
        "tests/unit/specfact_code_review/run/native_project_runtime_fixtures.py",
    ],
)
def test_native_admission_and_ownership_proofs_have_no_blocking_complexity(relative: str) -> None:
    """Exercise actual production policy without replacing admission behavior tests."""
    source = Path(__file__).resolve().parents[4] / relative

    blocks = [cc_to_dict(block) for block in cc_visit(source.read_text())]
    findings = radon_runner._map_radon_blocks(blocks, str(source)) + radon_runner._kiss_metric_findings(source)
    blocking = [finding for finding in findings if finding.severity == "error"]
    assert not blocking, [(finding.rule, finding.line, finding.message) for finding in blocking]


def test_native_acquisition_fixture_has_no_function_length_warning() -> None:
    """Apply unchanged production source-shape policy to the authenticated fixture."""

    fixture = (
        Path(__file__).resolve().parents[4] / "tests/unit/specfact_code_review/run/native_project_runtime_fixtures.py"
    )
    findings = _kiss_metric_findings(fixture)

    assert not [finding for finding in findings if finding.rule == "kiss.loc.warning"]


@pytest.mark.parametrize(
    "function_name",
    [
        "test_local_deferral_rejects_unscheduled_indexed_customer_review",
        "test_deferral_requires_integrated_review_execution_contract",
        "test_deferral_requires_integrated_change_detector_execution",
    ],
)
def test_host_deferral_mutation_proofs_have_no_nesting_warning(function_name: str) -> None:
    """Apply actual KISS policy without changing any host mutation scenario."""
    source = Path(__file__).resolve().parents[4] / "tests/host/proof_capsule_deferred_review_ci.py"
    definition = next(
        node for node in ast.parse(source.read_text()).body if getattr(node, "name", None) == function_name
    )
    findings = run_radon([source])
    assert not [finding for finding in findings if finding.category == "tool_error"]
    assert not [
        finding
        for finding in findings
        if finding.line == definition.lineno and finding.rule in {"kiss.nesting.warning", "kiss.nesting.error"}
    ]


def test_distribution_ownership_mutation_has_no_nesting_warning() -> None:
    """Exercise actual KISS policy while retaining every ownership mutation."""
    source = (
        Path(__file__).resolve().parents[4] / "tests/unit/specfact_code_review/run/test_native_project_inventory.py"
    )
    definition = next(
        node
        for node in ast.parse(source.read_text()).body
        if getattr(node, "name", None) == "_mutate_distribution_ownership"
    )
    findings = run_radon([source])
    assert not [finding for finding in findings if finding.category == "tool_error"]
    assert not [
        finding
        for finding in findings
        if finding.line == definition.lineno and finding.rule in {"kiss.nesting.warning", "kiss.nesting.error"}
    ]


def test_pytest_failure_fixture_has_no_nesting_warning() -> None:
    """Exercise actual KISS policy without weakening artifact failure controls."""
    source = (
        Path(__file__).resolve().parents[4] / "tests/unit/specfact_code_review/run/test_native_pytest_observations.py"
    )
    definition = next(
        node
        for node in ast.parse(source.read_text()).body
        if getattr(node, "name", None) == "test_native_pytest_failure_reaches_real_evaluator_with_incomplete_remedy"
    )
    callback = next(node for node in ast.walk(definition) if getattr(node, "name", None) == "execute")
    findings = run_radon([source])
    assert not [finding for finding in findings if finding.category == "tool_error"]
    assert not [
        finding
        for finding in findings
        if finding.line == callback.lineno and finding.rule in {"kiss.nesting.warning", "kiss.nesting.error"}
    ]


def test_canonical_allocation_proof_functions_have_no_function_length_warning() -> None:
    """Retain compiled controls while bounding their existing source construction."""
    source = Path(__file__).resolve().parents[4] / "tests/native/proof_native_canonical_path.py"
    definitions = [node for node in ast.parse(source.read_text()).body if isinstance(node, ast.FunctionDef)]
    findings = run_radon([source])
    assert not [finding for finding in findings if finding.category == "tool_error"]
    assert not [
        finding
        for finding in findings
        if finding.line in {node.lineno for node in definitions}
        and finding.rule in {"kiss.loc.warning", "kiss.loc.error"}
    ]


@pytest.mark.parametrize(
    "function_name",
    [
        "test_hatch_prepares_an_unfamiliar_environment_without_project_catalog",
        "test_poetry_prepares_locked_dependency_environment_without_catalog",
        "test_prepares_authenticated_bundle_through_closed_native_project_plan",
    ],
)
def test_project_runtime_proof_callbacks_have_no_function_length_warning(function_name: str) -> None:
    """Apply real KISS policy while retaining original preparation proof cases."""
    source = Path(__file__).resolve().parents[4] / "tests/unit/specfact_code_review/run/test_native_project_runtime.py"
    definitions = [node for node in ast.parse(source.read_text()).body if isinstance(node, ast.FunctionDef)]
    target = next(node for node in definitions if node.name == function_name)
    factories = [
        node
        for node in definitions
        if node.name in {"_hatch_project_phase", "_poetry_project_phase", "_launch_authenticated_project_session"}
    ]
    findings = run_radon([source])
    assert not [finding for finding in findings if finding.category == "tool_error"]
    assert not [
        finding
        for finding in findings
        if finding.line in {target.lineno, *(node.lineno for node in factories)}
        and finding.rule in {"kiss.loc.warning", "kiss.loc.error"}
    ]


def test_owner_entry_proof_fixtures_satisfy_unchanged_complexity_policy() -> None:
    source = Path(__file__).resolve().parents[4] / "tests/host/proof_capsule_deferred_review_ci.py"
    targets = {
        node.lineno
        for node in ast.parse(source.read_text()).body
        if isinstance(node, ast.FunctionDef)
        and (
            node.name.startswith("test_owner_")
            or node.name.startswith("_owner_entry_")
            or node.name.startswith("_assert_owner_entry_")
        )
    }
    findings = run_radon([source])
    assert not [finding for finding in findings if finding.category == "tool_error"]
    assert not [finding for finding in findings if finding.line in targets]


def test_registered_namespace_verification_phases_preserve_real_complexity_policy() -> None:
    source = Path("packages/specfact-code-review/src/specfact_code_review/run/target_bootstrap.py").resolve()
    tree = ast.parse(source.read_text(encoding="utf-8"))
    phase_lines = {
        node.lineno
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name
        in {"_verified_analyzer_spec", "_verified_virtual_spec", "_registered_six_spec", "_verified_six_importer"}
    }
    findings = run_radon([source], full_result=True)
    assert not any(row.category == "tool_error" for row in findings)
    assert not any(row.line in phase_lines for row in findings)


def test_registered_namespace_owner_passes_complete_configured_type_style_policy() -> None:
    source = Path("packages/specfact-code-review/src/specfact_code_review/run/target_bootstrap.py").resolve()
    tree = ast.parse(source.read_text(encoding="utf-8"))
    owner = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_registered_six_spec"
    )
    assert owner.end_lineno is not None
    findings = run_basedpyright([source]) + run_pylint([source])
    assert not any(row.category == "tool_error" for row in findings)
    assert not any(owner.lineno <= row.line <= owner.end_lineno for row in findings)


def test_target_output_guard_has_no_constant_condition_in_complete_public_style_analysis() -> None:
    source = Path("packages/specfact-code-review/src/specfact_code_review/run/target_crosshair.py").resolve()
    findings = run_pylint([source])
    assert not any(row.category == "tool_error" for row in findings)
    assert not any(row.rule == "W0125" for row in findings)


def test_actual_commit_race_proofs_preserve_complete_quality_policy() -> None:
    source = Path("tests/host/proof_capsule_deferred_review_ci.py").resolve()
    portable = Path("tests/unit/specfact_code_review/run/test_owner_commit_entry.py").resolve()
    findings = run_radon([source], full_result=True) + run_pylint([source, portable])
    assert not any(row.category == "tool_error" for row in findings)
    assert not any(row.rule in {"R1732", "C0411"} for row in findings)
    target_lines = {
        node.lineno
        for node in ast.parse(source.read_text(encoding="utf-8")).body
        if isinstance(node, ast.FunctionDef)
        and (
            node.name.startswith("_late_commit_race_")
            or node.name == "test_owner_entry_rejects_actual_post_hook_index_race"
        )
    }
    assert not any(row.line in target_lines and row.rule.startswith("kiss.loc.") for row in findings)


def test_native_argument_materialization_satisfies_complete_nesting_policy() -> None:
    source = Path("packages/specfact-code-review/src/specfact_code_review/run/native_worker.py").resolve()
    target = next(
        node
        for node in ast.parse(source.read_text(encoding="utf-8")).body
        if isinstance(node, ast.FunctionDef) and node.name == "_materialized_adapter_argv"
    )
    findings = run_radon([source], full_result=True)
    assert not any(row.category == "tool_error" for row in findings)
    assert not any(
        row.line == target.lineno and row.rule in {"kiss.nesting.warning", "kiss.nesting.error"} for row in findings
    )
