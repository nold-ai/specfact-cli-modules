from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from pytest import MonkeyPatch

from specfact_code_review.tools.radon_runner import run_radon
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
