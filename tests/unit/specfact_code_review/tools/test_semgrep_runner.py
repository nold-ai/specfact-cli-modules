from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from pytest import MonkeyPatch

from specfact_code_review.tools.semgrep_runner import (
    AI_BLOAT_GUIDANCE,
    SEMGREP_RULE_CATEGORY,
    _parse_semgrep_results,
    _run_semgrep_command,
    _snip_stderr_tail,
    _validate_semgrep_completion,
    find_semgrep_ai_bloat_config,
    find_semgrep_bugs_config,
    find_semgrep_config,
    run_semgrep,
    run_semgrep_bugs,
)
from tests.unit.specfact_code_review.tools.helpers import completed_process


FIXTURE_ROOT = Path(__file__).resolve().parents[3] / "fixtures" / "semgrep"
BAD_FIXTURE_RULES = {
    "bad_get_modify.py": "get-modify-same-method",
    "bad_nested_access.py": "unguarded-nested-access",
    "bad_cross_layer.py": "cross-layer-call",
    "bad_module_network.py": "module-level-network",
    "bad_print_in_src.py": "print-in-src",
}
AI_BLOAT_BAD_FIXTURE_RULES = {
    "bad_manual_loop_comprehension.py": "ai-bloat.manual-loop-comprehension",
    "bad_identity_try_except.py": "ai-bloat.identity-try-except",
    "bad_none_then_none.py": "ai-bloat.none-then-none",
    "bad_single_call_wrapper.py": "ai-bloat.single-call-wrapper",
}
GOOD_FIXTURES = [
    "good_get_modify.py",
    "good_nested_access.py",
    "good_cross_layer.py",
    "good_module_network.py",
    "good_print_in_src.py",
]
AI_BLOAT_GOOD_FIXTURES = [
    "good_manual_loop_comprehension.py",
    "good_passthrough_lambda.py",
    "good_identity_try_except.py",
    "good_none_then_none.py",
    "good_single_call_wrapper.py",
]


def test_semgrep_uses_signed_module_fallback_without_target_config(tmp_path: Path) -> None:
    from specfact_code_review.run import scope

    target = tmp_path / "target"
    module = tmp_path / "module"
    target.mkdir()
    (module / ".semgrep").mkdir(parents=True)
    (module / "resources/semgrep-rules").mkdir(parents=True)
    (module / ".semgrep/clean_code.yaml").write_text("rules: []\n", encoding="utf-8")
    (module / "resources/semgrep-rules/ai-bloat.yaml").write_text("rules: []\n", encoding="utf-8")

    bundle = scope.resolve_semgrep_bundle(target, signed_module_root=module)

    assert bundle.status == "PASS"
    assert bundle.clean.identity_kind == "signed_module_payload"
    assert bundle.ai_bloat.identity_kind == "signed_module_payload"


def test_semgrep_scanned_paths_match_every_eligible_input() -> None:
    from specfact_code_review.tools import semgrep_runner

    result = semgrep_runner.reconcile_scanned_paths(
        eligible=("src/a.py", "src/b.py"), scanned=("src/a.py", "src/b.py"), skipped=()
    )

    assert result.status == "PASS"


def test_semgrep_rule_target_narrowing_is_unknown() -> None:
    from specfact_code_review.tools import semgrep_runner

    result = semgrep_runner.validate_rule_pack({"rules": [{"id": "x", "paths": {"exclude": ["tests"]}}]})

    assert result.status == "UNKNOWN"
    assert result.reason == "semgrep_rule_target_narrowing"


@pytest.mark.parametrize(
    ("config_name", "runner"),
    [("clean_code.yaml", run_semgrep), ("bugs.yaml", run_semgrep_bugs)],
    ids=["clean", "bugs"],
)
def test_sealed_semgrep_pass_rejects_rule_target_narrowing_before_launch(
    tmp_path: Path, monkeypatch: MonkeyPatch, config_name: str, runner: object
) -> None:
    bundle = tmp_path / "bundle"
    (bundle / ".semgrep").mkdir(parents=True)
    (bundle / ".semgrep" / config_name).write_text(
        "rules:\n  - id: narrowed\n    paths:\n      exclude: [src/ignored.py]\n",
        encoding="utf-8",
    )
    target = tmp_path / "target.py"
    target.write_text("VALUE = 1\n", encoding="utf-8")
    run_mock = Mock(return_value=completed_process("semgrep", stdout='{"results": []}'))
    monkeypatch.setattr(subprocess, "run", run_mock)

    findings = runner([target], bundle_root=bundle)  # type: ignore[operator]

    assert len(findings) == 1
    assert findings[0].category == "tool_error"
    run_mock.assert_not_called()


@pytest.mark.parametrize(
    ("config_name", "runner"),
    [("clean_code.yaml", run_semgrep), ("bugs.yaml", run_semgrep_bugs)],
    ids=["clean", "bugs"],
)
def test_sealed_semgrep_pass_rejects_skipped_eligible_input(
    tmp_path: Path, monkeypatch: MonkeyPatch, config_name: str, runner: object
) -> None:
    bundle = tmp_path / "bundle"
    (bundle / ".semgrep").mkdir(parents=True)
    (bundle / ".semgrep" / config_name).write_text("rules: []\n", encoding="utf-8")
    target = tmp_path / "target.py"
    target.write_text("VALUE = 1\n", encoding="utf-8")
    payload = {"results": [], "paths": {"scanned": [], "skipped": [str(target)]}}
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("semgrep", stdout=json.dumps(payload))),
    )

    findings = runner([target], bundle_root=bundle)  # type: ignore[operator]

    assert len(findings) == 1
    assert findings[0].category == "tool_error"


def test_sealed_semgrep_pass_accepts_omitted_optional_skipped_paths(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    bundle = tmp_path / "bundle"
    (bundle / ".semgrep").mkdir(parents=True)
    (bundle / ".semgrep/clean_code.yaml").write_text("rules: []\n", encoding="utf-8")
    target = tmp_path / "target.py"
    target.write_text("VALUE = 1\n", encoding="utf-8")
    payload = {"results": [], "paths": {"scanned": [str(target)]}}
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("semgrep", stdout=json.dumps(payload))),
    )

    assert run_semgrep([target], bundle_root=bundle) == []


def test_semgrep_pass_union_cannot_hide_rule_exclusion() -> None:
    from specfact_code_review.tools import semgrep_runner

    result = semgrep_runner.reconcile_passes(
        eligible=("src/a.py",),
        passes=(
            {"id": "clean", "scanned": (), "skipped": ("src/a.py",)},
            {"id": "ai-bloat", "scanned": ("src/a.py",), "skipped": ()},
        ),
    )

    assert result.status == "UNKNOWN"


def test_semgrep_disable_nosem_preserves_string_literal_finding() -> None:
    from specfact_code_review.tools import semgrep_runner

    plan = semgrep_runner.build_snapshot_invocation(
        eligible=("src/app.py",), source=b'VALUE = "nosemgrep"\neval("1")\n'
    )

    assert "--disable-nosem" in plan.argv
    assert plan.suppression_controls_disabled is True
    assert plan.expected_rules == ("python.lang.security.audit.eval-detected",)


def test_ai_bloat_guidance_matches_ai_bloat_rule_categories() -> None:
    categorized_ai_bloat_rules = {rule for rule, category in SEMGREP_RULE_CATEGORY.items() if category == "ai_bloat"}

    assert categorized_ai_bloat_rules == set(AI_BLOAT_GUIDANCE)


def test_run_semgrep_command_creates_runtime_dirs(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    target = tmp_path / "target.py"
    config = tmp_path / "clean_code.yaml"
    target.write_text("print('x')\n", encoding="utf-8")
    config.write_text("rules: []\n", encoding="utf-8")
    captured_env: dict[str, str] = {}

    def _run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        del command
        env = kwargs["env"]
        assert isinstance(env, dict)
        captured_env.update({str(key): str(value) for key, value in env.items()})
        assert Path(captured_env["XDG_CONFIG_HOME"]).is_dir()
        assert Path(captured_env["XDG_CACHE_HOME"]).is_dir()
        assert Path(captured_env["SEMGREP_SETTINGS_FILE"]).parent.is_dir()
        return completed_process("semgrep", stdout='{"results": []}', returncode=0)

    monkeypatch.setattr(subprocess, "run", _run)

    _run_semgrep_command([target], bundle_root=None, config_file=config)

    assert captured_env["XDG_CONFIG_HOME"].endswith(".config")


def test_sealed_semgrep_rejects_fatal_exit_with_parseable_payload(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    bundle = tmp_path / "bundle"
    (bundle / ".semgrep").mkdir(parents=True)
    (bundle / ".semgrep/clean_code.yaml").write_text("rules: []\n", encoding="utf-8")
    target = tmp_path / "target.py"
    target.write_text("VALUE = 1\n", encoding="utf-8")
    payload = {"results": [], "errors": [], "paths": {"scanned": [str(target)], "skipped": []}}
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("semgrep", stdout=json.dumps(payload), returncode=2)),
    )

    findings = run_semgrep([target], bundle_root=bundle)

    assert len(findings) == 1
    assert findings[0].category == "tool_error"
    assert "returncode=2" in findings[0].message


def test_sealed_semgrep_rejects_structured_execution_errors(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    bundle = tmp_path / "bundle"
    (bundle / ".semgrep").mkdir(parents=True)
    (bundle / ".semgrep/clean_code.yaml").write_text("rules: []\n", encoding="utf-8")
    target = tmp_path / "target.py"
    target.write_text("VALUE = 1\n", encoding="utf-8")
    payload = {
        "results": [],
        "errors": [{"type": "ParseError", "message": "target parse failed"}],
        "paths": {"scanned": [str(target)], "skipped": []},
    }
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("semgrep", stdout=json.dumps(payload), returncode=0)),
    )

    findings = run_semgrep([target], bundle_root=bundle)

    assert len(findings) == 1
    assert findings[0].category == "tool_error"
    assert "structured errors" in findings[0].message


@pytest.mark.parametrize("bug_pass", [False, True], ids=["clean", "bugs"])
@pytest.mark.parametrize("returncode", [0, 1])
def test_structured_semgrep_errors_retain_diagnostic_context(
    tmp_path: Path, monkeypatch: MonkeyPatch, bug_pass: bool, returncode: int
) -> None:
    """Both passes retain the native error without accepting partial execution."""
    bundle = tmp_path / "bundle"
    (bundle / ".semgrep").mkdir(parents=True)
    for name in ("clean_code", "bugs"):
        (bundle / f".semgrep/{name}.yaml").write_text("rules: []\n", encoding="utf-8")
    target = tmp_path / "target.py"
    target.write_text("VALUE = 1\n", encoding="utf-8")
    payload = {
        "results": [],
        "errors": [{"type": "ParseError", "code": 3, "message": "target parse failed", "source": "PRIVATE_SOURCE"}],
    }
    process = Mock(return_value=completed_process("semgrep", stdout=json.dumps(payload), returncode=returncode))
    monkeypatch.setattr(subprocess, "run", process)

    findings = (run_semgrep_bugs if bug_pass else run_semgrep)([target], bundle_root=bundle)

    assert len(findings) == 1
    assert (findings[0].category, findings[0].severity) == ("tool_error", "error")
    assert "count=1" in findings[0].message
    assert json.loads(findings[0].message.split("; details=", 1)[1]) == [
        {"type": "ParseError", "code": 3, "message": "target parse failed"}
    ]
    assert process.call_count == 2


def test_structured_semgrep_error_diagnostics_are_bounded_and_escaped() -> None:
    """Untrusted nested metadata and long control-filled messages stay bounded."""
    payload: dict[str, object] = {
        "errors": [
            {"type": "ParseError", "code": 3, "message": "parse\n\t\x1b" + "x" * 1000},
            {"type": {"source": "PRIVATE_SOURCE"}, "code": ["PRIVATE_SOURCE"], "message": {"source": "PRIVATE_SOURCE"}},
            {"type": "z" * 1000, "code": "z" * 1000, "message": "\x00" * 1000},
            {"type": "FOURTH_ERROR", "message": "OMITTED_MESSAGE"},
        ]
    }

    with pytest.raises(ValueError) as error:
        _validate_semgrep_completion(completed_process("semgrep", stdout="", returncode=0), payload)

    diagnostic = str(error.value)
    assert "count=4" in diagnostic
    assert "omitted=1" in diagnostic
    assert "PRIVATE_SOURCE" not in diagnostic
    assert "FOURTH_ERROR" not in diagnostic
    assert "OMITTED_MESSAGE" not in diagnostic
    assert "\\n\\t\\u001b" in diagnostic
    assert not any(ord(char) < 32 for char in diagnostic)
    _assert_bounded_semgrep_details(diagnostic)


def _assert_bounded_semgrep_details(diagnostic: str) -> None:
    """Validate the aggregate bound and the surviving allowlisted JSON fields."""
    assert len(diagnostic) <= 3900
    details = json.loads(diagnostic.split("; details=", 1)[1])
    assert len(details) == 3
    assert details[1] == {}
    assert len(details[0]["message"]) <= 512
    assert len(details[2]["message"]) <= 512


@pytest.fixture(autouse=True)
def _stub_semgrep_on_path(monkeypatch: MonkeyPatch) -> None:  # pyright: ignore[reportUnusedFunction]
    real_which = shutil.which

    def _which(name: str) -> str | None:
        if name == "semgrep":
            return "/fake/semgrep"
        return real_which(name)

    monkeypatch.setattr("specfact_code_review.tools.tool_availability.shutil.which", _which)


def test_run_semgrep_maps_findings_to_review_finding(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = {
        "results": [
            {
                "check_id": "get-modify-same-method",
                "path": str(file_path),
                "start": {"line": 4},
                "extra": {"message": "Method mixes read and write responsibilities."},
            }
        ],
        "paths": {"scanned": [str(file_path)], "skipped": []},
    }
    run_mock = Mock(return_value=completed_process("semgrep", stdout=json.dumps(payload), returncode=1))
    monkeypatch.setattr(subprocess, "run", run_mock)

    findings = run_semgrep([file_path])

    assert len(findings) == 1
    assert findings[0].tool == "semgrep"
    assert findings[0].category == "clean_code"
    assert findings[0].rule == "get-modify-same-method"
    assert findings[0].line == 4
    assert findings[0].fixable is False
    run_mock.assert_called_once()


def test_run_semgrep_maps_naming_rule_to_naming_category(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = {
        "results": [
            {
                "check_id": "banned-generic-public-names",
                "path": str(file_path),
                "start": {"line": 2},
                "extra": {"message": "Public API name is too generic."},
            }
        ]
    }
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("semgrep", stdout=json.dumps(payload), returncode=1)),
    )

    findings = run_semgrep([file_path])

    assert len(findings) == 1
    assert findings[0].category == "naming"
    assert findings[0].rule == "banned-generic-public-names"


def test_run_semgrep_maps_ai_bloat_rules_to_info_findings(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = {
        "results": [
            {
                "check_id": "ai-bloat.single-call-wrapper",
                "path": str(file_path),
                "start": {"line": 5},
                "extra": {"message": "Single-call wrapper adds no behavior.", "severity": "WARNING"},
            }
        ]
    }
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("semgrep", stdout=json.dumps(payload), returncode=1)),
    )

    findings = run_semgrep([file_path])

    assert len(findings) == 1
    assert findings[0].category == "ai_bloat"
    assert findings[0].severity == "info"
    assert findings[0].rule == "ai-bloat.single-call-wrapper"
    assert findings[0].guidance_kind == "design_judgment"
    assert findings[0].recommended_action == "inspect"
    assert findings[0].clean_code_principle == "dry"
    assert findings[0].rationale
    assert findings[0].safety_checks


def test_run_semgrep_filters_findings_to_requested_files(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    other_path = tmp_path / "other.py"
    payload = {
        "results": [
            {
                "check_id": "cross-layer-call",
                "path": str(file_path),
                "start": {"line": 7},
                "extra": {"message": "Cross-layer calls should be separated."},
            },
            {
                "check_id": "print-in-src",
                "path": str(other_path),
                "start": {"line": 9},
                "extra": {"message": "Avoid print in source files."},
            },
        ],
        "paths": {"scanned": [str(file_path)], "skipped": []},
    }
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("semgrep", stdout=json.dumps(payload), returncode=1)),
    )

    findings = run_semgrep([file_path])

    assert len(findings) == 1
    assert findings[0].file == str(file_path)
    assert findings[0].rule == "cross-layer-call"


def test_run_semgrep_returns_tool_error_when_semgrep_is_unavailable(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    run_mock = Mock()
    monkeypatch.setattr("specfact_code_review.tools.tool_availability.shutil.which", lambda _name: None)
    monkeypatch.setattr(subprocess, "run", run_mock)

    findings = run_semgrep([file_path])

    assert len(findings) == 1
    assert findings[0].category == "tool_error"
    assert findings[0].tool == "semgrep"
    assert findings[0].severity == "warning"
    run_mock.assert_not_called()


def test_run_semgrep_returns_empty_list_for_clean_file(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("semgrep", stdout=json.dumps({"results": []}))),
    )

    findings = run_semgrep([file_path])

    assert not findings


def test_run_semgrep_returns_tool_error_when_results_key_is_missing(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("semgrep", stdout=json.dumps({"version": "1.0"}))),
    )

    findings = run_semgrep([file_path])

    assert len(findings) == 1
    assert findings[0].category == "tool_error"
    assert findings[0].tool == "semgrep"


def test_run_semgrep_ignores_unsupported_rules(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = {
        "results": [
            {
                "check_id": "unsupported-rule",
                "path": str(file_path),
                "start": {"line": 3},
                "extra": {"message": "Ignored rule."},
            }
        ]
    }
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("semgrep", stdout=json.dumps(payload), returncode=1)),
    )

    findings = run_semgrep([file_path])

    assert not findings


def test_run_semgrep_returns_empty_for_no_files() -> None:
    assert run_semgrep([]) == []


def test_parse_semgrep_results_rejects_non_list_results() -> None:
    with pytest.raises(ValueError, match="semgrep results must be a list"):
        _parse_semgrep_results({"results": {}})


def test_find_semgrep_config_with_explicit_bundle_root(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    (root / ".semgrep").mkdir(parents=True)
    (root / ".semgrep" / "clean_code.yaml").write_text("rules: []\n", encoding="utf-8")
    assert find_semgrep_config(bundle_root=root) == root / ".semgrep" / "clean_code.yaml"


def test_find_semgrep_config_with_explicit_bundle_root_reports_missing_config(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        find_semgrep_config(bundle_root=tmp_path)


def test_find_semgrep_bugs_config_with_explicit_bundle_root(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    (root / ".semgrep").mkdir(parents=True)
    (root / ".semgrep" / "bugs.yaml").write_text("rules: []\n", encoding="utf-8")

    assert find_semgrep_bugs_config(bundle_root=root) == root / ".semgrep" / "bugs.yaml"
    assert find_semgrep_bugs_config(bundle_root=tmp_path / "missing") is None


def test_find_semgrep_ai_bloat_config_with_explicit_bundle_root(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    rules = root / "resources" / "semgrep-rules"
    rules.mkdir(parents=True)
    (rules / "ai-bloat.yaml").write_text("rules: []\n", encoding="utf-8")

    assert find_semgrep_ai_bloat_config(bundle_root=root) == rules / "ai-bloat.yaml"
    assert find_semgrep_ai_bloat_config(bundle_root=tmp_path / "missing") is None


def test_snip_stderr_tail_keeps_last_chars() -> None:
    """Long stderr should retain the suffix (most recent diagnostics), not the prefix."""
    long = "UNIQUE_HEAD_MARKER" + ("A" * 5000) + "END_OF_ERROR"
    out = _snip_stderr_tail(long)
    assert "END_OF_ERROR" in out
    assert out.startswith("…")
    assert "UNIQUE_HEAD_MARKER" not in out


def test_find_semgrep_config_stops_at_git_directory(tmp_path: Path) -> None:
    """Do not resolve a config outside the repo (e.g. stray ~/.semgrep)."""
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    nested = repo / "nested" / "pkg" / "tools"
    nested.mkdir(parents=True)
    (repo / "nested" / ".semgrep").mkdir(parents=True)
    (repo / "nested" / ".semgrep" / "clean_code.yaml").write_text("rules: []\n", encoding="utf-8")
    fake_here = nested / "runner.py"
    fake_here.write_text("#", encoding="utf-8")
    assert find_semgrep_config(module_file=fake_here) == repo / "nested" / ".semgrep" / "clean_code.yaml"


def test_run_semgrep_bugs_returns_empty_when_semgrep_cli_missing(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Bug pass must not emit a second skip finding; run_semgrep already reports missing semgrep."""
    bundle = tmp_path / "bundle"
    (bundle / ".semgrep").mkdir(parents=True)
    (bundle / ".semgrep" / "bugs.yaml").write_text("rules: []\n", encoding="utf-8")
    target = tmp_path / "x.py"
    target.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr("specfact_code_review.tools.tool_availability.shutil.which", lambda _name: None)

    assert run_semgrep_bugs([target], bundle_root=bundle) == []


def test_run_semgrep_bugs_returns_empty_for_no_files() -> None:
    assert run_semgrep_bugs([]) == []


def test_run_semgrep_bugs_maps_security_and_clean_code_findings(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    bundle = tmp_path / "bundle"
    (bundle / ".semgrep").mkdir(parents=True)
    (bundle / ".semgrep" / "bugs.yaml").write_text("rules: []\n", encoding="utf-8")
    file_path = tmp_path / "target.py"
    payload = {
        "results": [
            {
                "check_id": "specfact-bugs-eval-exec",
                "path": str(file_path),
                "start": {"line": 2},
                "extra": {"message": "Avoid eval.", "severity": "ERROR"},
            },
            {
                "check_id": "specfact-bugs-useless-comparison",
                "path": str(file_path),
                "start": {"line": 3},
                "extra": {"message": "Comparison is always true."},
            },
        ],
        "paths": {"scanned": [str(file_path)], "skipped": []},
    }
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("semgrep", stdout=json.dumps(payload), returncode=1)),
    )

    findings = run_semgrep_bugs([file_path], bundle_root=bundle)

    assert [(finding.category, finding.severity, finding.rule) for finding in findings] == [
        ("security", "error", "specfact-bugs-eval-exec"),
        ("clean_code", "warning", "specfact-bugs-useless-comparison"),
    ]


def test_run_semgrep_bugs_returns_tool_error_for_invalid_payload(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    bundle = tmp_path / "bundle"
    (bundle / ".semgrep").mkdir(parents=True)
    (bundle / ".semgrep" / "bugs.yaml").write_text("rules: []\n", encoding="utf-8")
    file_path = tmp_path / "target.py"
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=completed_process("semgrep", stdout=json.dumps({"results": [{}]}), returncode=1)),
    )

    findings = run_semgrep_bugs([file_path], bundle_root=bundle)

    assert len(findings) == 1
    assert findings[0].category == "tool_error"


def test_run_semgrep_retries_after_transient_parse_failure(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    file_path = tmp_path / "target.py"
    payload = {
        "results": [
            {
                "check_id": "unguarded-nested-access",
                "path": str(file_path),
                "start": {"line": 2},
                "extra": {"message": "Nested attribute access can fail."},
            }
        ]
    }
    run_mock = Mock(
        side_effect=[
            completed_process("semgrep", stdout="", returncode=2),
            completed_process("semgrep", stdout=json.dumps(payload), returncode=1),
        ]
    )
    monkeypatch.setattr(subprocess, "run", run_mock)

    findings = run_semgrep([file_path])

    assert len(findings) == 1
    assert findings[0].rule == "unguarded-nested-access"
    assert run_mock.call_count == 2


@pytest.mark.parametrize(("fixture_name", "expected_rule"), list(BAD_FIXTURE_RULES.items()))
def test_each_bad_fixture_triggers_expected_rule(fixture_name: str, expected_rule: str) -> None:
    if shutil.which("semgrep") is None:
        pytest.skip("semgrep CLI is required for fixture validation")

    findings = run_semgrep([FIXTURE_ROOT / fixture_name])

    assert findings
    assert expected_rule in {finding.rule for finding in findings}


@pytest.mark.parametrize("fixture_name", GOOD_FIXTURES)
def test_each_good_fixture_triggers_no_findings(fixture_name: str) -> None:
    if shutil.which("semgrep") is None:
        pytest.skip("semgrep CLI is required for fixture validation")

    findings = run_semgrep([FIXTURE_ROOT / fixture_name])

    assert not findings


@pytest.mark.parametrize(("fixture_name", "expected_rule"), list(AI_BLOAT_BAD_FIXTURE_RULES.items()))
def test_each_ai_bloat_bad_fixture_triggers_expected_rule(fixture_name: str, expected_rule: str) -> None:
    if shutil.which("semgrep") is None:
        pytest.skip("semgrep CLI is required for fixture validation")

    findings = run_semgrep([FIXTURE_ROOT / fixture_name])

    assert expected_rule in {finding.rule for finding in findings}
    assert all(finding.severity == "info" for finding in findings if finding.rule == expected_rule)


def test_ai_bloat_passthrough_lambda_rule_triggers_for_generated_fixture(tmp_path: Path) -> None:
    if shutil.which("semgrep") is None:
        pytest.skip("semgrep CLI is required for fixture validation")

    target = tmp_path / "bad_passthrough_lambda.py"
    target.write_text(
        """
def canonicalize(value: str) -> str:
    return value.strip()


callbacks = [lambda value: canonicalize(value)]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    findings = run_semgrep([target])

    assert "ai-bloat.passthrough-lambda" in {finding.rule for finding in findings}
    assert all(finding.severity == "info" for finding in findings if finding.rule == "ai-bloat.passthrough-lambda")


@pytest.mark.parametrize("fixture_name", AI_BLOAT_GOOD_FIXTURES)
def test_each_ai_bloat_good_fixture_triggers_no_ai_bloat_findings(fixture_name: str) -> None:
    if shutil.which("semgrep") is None:
        pytest.skip("semgrep CLI is required for fixture validation")

    findings = run_semgrep([FIXTURE_ROOT / fixture_name])

    assert not any(finding.category == "ai_bloat" for finding in findings)


def test_customer_capsule_payload_contains_all_signed_semgrep_rules(tmp_path: Path) -> None:
    """Rules survive the authenticated Python-package-only capsule copy."""
    import shutil

    from specfact_code_review.tools import semgrep_runner

    package = Path(semgrep_runner.__file__).resolve().parents[1]
    copied = tmp_path / "specfact_code_review"
    shutil.copytree(package, copied, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    module = copied / "tools/semgrep_runner.py"
    for finder in (find_semgrep_config, find_semgrep_bugs_config, find_semgrep_ai_bloat_config):
        config = finder(module_file=module)
        assert config is not None and config.is_file() and config.is_relative_to(copied)


def test_customer_semgrep_policy_resolves_packaged_module_layout(tmp_path: Path) -> None:
    """Controller policy resolution accepts rules inside the signed Python payload."""
    from specfact_code_review.run import scope
    from specfact_code_review.tools import semgrep_runner

    module_root = Path(semgrep_runner.__file__).resolve().parents[3]
    bundle = scope.resolve_semgrep_bundle(tmp_path, signed_module_root=module_root)
    try:
        assert bundle.status == "PASS", bundle.reason
        assert bundle.clean.identity_kind == "signed_module_payload"
    finally:
        import shutil

        shutil.rmtree(bundle.root)


def test_customer_semgrep_child_uses_sealed_python_startup(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Semgrep's Python entrypoint retains only the capsule import closure."""
    from specfact_code_review import _review_utils

    monkeypatch.setattr(_review_utils, "__file__", "/opt/specfact/builtin/specfact_code_review/_review_utils.py")
    run = Mock(return_value=completed_process("semgrep", stdout='{"results": []}'))
    monkeypatch.setattr(subprocess, "run", run)
    _run_semgrep_command([tmp_path / "target.py"], bundle_root=None, config_file=tmp_path / "rules.yaml")
    command = run.call_args.args[0]
    assert command[:5] == [
        "/opt/specfact/python/bin/python",
        "-I",
        "-S",
        "/opt/specfact/bootstrap/sealed_bootstrap.py",
        "semgrep.console_scripts.pysemgrep",
    ]


@pytest.mark.parametrize("shape", ["path", "span", "partial"])
def test_linux23_semgrep_native_identity_survives_loss_boundary(tmp_path, monkeypatch, shape):
    from specfact_code_review.tools import semgrep_runner

    monkeypatch.chdir(tmp_path)
    config = tmp_path / "rules.yaml"
    config.write_text("rules: []\n")
    monkeypatch.setattr(semgrep_runner, "find_semgrep_config", lambda **_: config)
    monkeypatch.setattr(semgrep_runner, "find_semgrep_ai_bloat_config", lambda **_: None)
    monkeypatch.setattr(semgrep_runner, "skip_if_tool_missing", lambda *_: [])
    location = {"path": "src/b.py", "start": {"line": 7, "col": 3}, "end": {"line": 8, "col": 4}}
    error = {"type": "Syntax error", "code": 3, "path": "src/b.py", "message": "PRIVATE_SOURCE"}
    if shape == "span":
        error["spans"] = [{"file": location["path"], "start": location["start"], "end": location["end"]}]
    elif shape == "partial":
        error["type"] = ["PartialParsing", [location]]
    monkeypatch.setattr(
        semgrep_runner,
        "_run_semgrep_command",
        lambda *_, **__: completed_process("semgrep", stdout=json.dumps({"results": [], "errors": [error]})),
    )
    finding = run_semgrep([Path("src/a.py"), Path("src/b.py")])[0]
    assert finding.category == "tool_error"
    assert (finding.file, finding.line) == ("src/a.py", 1)
    diagnostic = finding.model_dump(mode="json")["native_diagnostic"]
    assert diagnostic["kind"] == "semgrep"
    observed = diagnostic["observations"][0]
    assert observed["input_path"] == "src/b.py"
    assert observed["target"] == "subject"
    assert observed["coordinate_status"] == ("absent" if shape == "path" else "accepted")
    if shape != "path":
        assert observed["line"] == 7 and observed["column"] == 3
    assert "PRIVATE_SOURCE" not in json.dumps(diagnostic)


@pytest.fixture
def linux23_semgrep_observe(tmp_path, monkeypatch):
    from specfact_code_review.tools import semgrep_runner

    monkeypatch.chdir(tmp_path)
    config = tmp_path / "rules.yaml"
    config.write_text("rules: []\n")
    monkeypatch.setattr(semgrep_runner, "find_semgrep_config", lambda **_: config)
    monkeypatch.setattr(semgrep_runner, "find_semgrep_ai_bloat_config", lambda **_: None)
    monkeypatch.setattr(semgrep_runner, "skip_if_tool_missing", lambda *_: [])

    def observe(errors, files=None, returncode=0):
        monkeypatch.setattr(
            semgrep_runner,
            "_run_semgrep_command",
            lambda *_, **__: subprocess.CompletedProcess(
                [], returncode, json.dumps({"results": [], "errors": errors}), "PRIVATE_STDERR"
            ),
        )
        return run_semgrep(files or [Path("src/a.py")])[0].model_dump(mode="json")["native_diagnostic"]

    return observe, config


@pytest.mark.parametrize("value", [True, -1, 0, 2147483648, "7", None])
def test_linux23_semgrep_rejects_invalid_native_positions(linux23_semgrep_observe, value):
    observe, _ = linux23_semgrep_observe
    diagnostic = observe(
        [
            {
                "type": "Syntax error",
                "spans": [{"file": "src/a.py", "start": {"line": value, "col": 1}, "end": {"line": 7, "col": 2}}],
            }
        ]
    )
    row = diagnostic["observations"][0]
    assert row["coordinate_status"] == "rejected"
    assert row["input_path"] == "src/a.py" and row["line"] is None


@pytest.mark.parametrize(
    "path", ["a.py", "./src/a.py", "src/../src/a.py", "/foreign/src/a.py", "src\\a.py", "src/a.py\n"]
)
def test_linux23_semgrep_rejects_unmatched_native_paths(linux23_semgrep_observe, path):
    observe, _ = linux23_semgrep_observe
    row = observe([{"type": "Syntax error", "path": path, "start": {"line": 99}}])["observations"][0]
    assert (row["target"], row["coordinate_status"], row["input_path"], row["line"]) == (
        "unknown",
        "rejected",
        None,
        None,
    )


def test_linux23_semgrep_exact_absolute_input_is_canonical(linux23_semgrep_observe):
    observe, _ = linux23_semgrep_observe
    source = Path.cwd() / "src/a.py"
    row = observe([{"type": "Syntax error", "path": str(source)}], files=[source])["observations"][0]
    assert (row["input_path"], row["coordinate_status"]) == ("src/a.py", "absent")


def test_linux23_semgrep_actual_rule_digest_and_coordinate(linux23_semgrep_observe):
    import hashlib

    observe, config = linux23_semgrep_observe
    row = observe(
        [
            {
                "type": ["PatternParseError", ["PRIVATE_PATTERN"]],
                "spans": [{"file": str(config), "start": {"line": 2, "col": 3}, "end": {"line": 2, "col": 4}}],
            }
        ],
        returncode=2,
    )["observations"][0]
    assert row["error_kind"] == "pattern_parse_error"
    assert row["target"] == "rule" and row["coordinate_status"] == "accepted"
    assert row["rule_input_id"] == "config_1"
    assert row["rule_input_sha256"] == hashlib.sha256(config.read_bytes()).hexdigest()
    assert row["input_path"] == "rules.yaml"
    assert "PRIVATE" not in json.dumps(row)


def test_linux23_semgrep_external_config_does_not_claim_subject_coordinates(tmp_path, linux23_semgrep_observe):
    from specfact_code_review.tools import semgrep_runner

    _, _config = linux23_semgrep_observe
    external = tmp_path.parent / (tmp_path.name + "-config.yaml")
    external.write_text("rules: []\n")
    inputs = semgrep_runner._semgrep_diagnostic_inputs([Path("src/a.py")], external)
    diagnostic = semgrep_runner._semgrep_native_diagnostic(
        {
            "errors": [
                {
                    "type": "Rule parse error",
                    "spans": [{"file": str(external), "start": {"line": 2, "col": 1}, "end": {"line": 2, "col": 2}}],
                }
            ]
        },
        inputs,
    )
    row = diagnostic.observations[0]
    assert row.target == "rule" and row.rule_input_sha256 is not None
    assert row.coordinate_status == "rejected" and row.input_path is None and row.line is None


@pytest.mark.parametrize("shape", ["errors", "spans", "partial"])
def test_linux23_semgrep_nested_observation_bounds(linux23_semgrep_observe, shape):
    observe, _ = linux23_semgrep_observe
    location = {"file": "src/a.py", "start": {"line": 7, "col": 1}, "end": {"line": 7, "col": 2}}
    if shape == "errors":
        errors = [{"type": "Syntax error", "path": "src/a.py"}] * 4
    elif shape == "spans":
        errors = [{"type": "Syntax error", "spans": [location] * 4}]
    else:
        errors = [{"type": ["PartialParsing", [{**location, "path": location["file"]}] * 4]}]
    diagnostic = observe(errors)
    assert (len(diagnostic["observations"]), diagnostic["total_count"], diagnostic["omitted_count"]) == (3, 4, 1)


def test_linux23_semgrep_whole_utf8_budget_omits_observations(linux23_semgrep_observe):
    observe, _ = linux23_semgrep_observe
    paths = [Path("é" * 400 + '"' * 200 + str(index) + ".py") for index in range(3)]
    errors = [{"type": "Syntax error", "path": str(path)} for path in paths]
    diagnostic = observe(errors, paths)
    assert len(json.dumps(diagnostic, ensure_ascii=False, separators=(",", ":")).encode()) <= 4096
    assert diagnostic["total_count"] == 3
    assert diagnostic["omitted_count"] > 0


@pytest.mark.parametrize(
    "kind", [["Unknown", ["PRIVATE"]], ["PatternParseError", {"secret": "PRIVATE"}], {"secret": "PRIVATE"}, "PRIVATE"]
)
def test_linux23_semgrep_unknown_shape_is_finite(linux23_semgrep_observe, kind):
    observe, _ = linux23_semgrep_observe
    diagnostic = observe([{"type": kind, "code": True, "path": "src/a.py"}])
    assert diagnostic["observations"][0]["error_kind"] == "other"
    assert diagnostic["observations"][0]["native_code"] is None
    assert "PRIVATE" not in json.dumps(diagnostic)


def test_linux23_diagnostic_old_absent_and_strict_roundtrip():
    from specfact_code_review.run.findings import ReviewFinding

    old = {
        "category": "tool_error",
        "severity": "error",
        "tool": "pytest",
        "rule": "tool_error",
        "file": "a.py",
        "line": 1,
        "message": "legacy",
    }
    assert ReviewFinding.model_validate(old).native_diagnostic is None
    diagnostic = {
        "kind": "pytest",
        "phase": "observation_read",
        "exception_kind": "FileNotFoundError",
        "observation_state": "read_failed",
    }
    finding = ReviewFinding.model_validate({**old, "native_diagnostic": diagnostic})
    assert ReviewFinding.model_validate_json(finding.model_dump_json()).native_diagnostic == finding.native_diagnostic
    with pytest.raises(ValueError):
        ReviewFinding.model_validate({**old, "native_diagnostic": {**diagnostic, "message": "PRIVATE"}})
    with pytest.raises(ValueError):
        ReviewFinding.model_validate({**old, "native_diagnostic": {**diagnostic, "child_returncode": True}})


@pytest.fixture
def linux24_legacy_finding():
    return {
        "category": "tool_error",
        "severity": "error",
        "tool": "pytest",
        "rule": "tool_error",
        "file": "a.py",
        "line": 1,
        "message": "legacy",
        "fixable": False,
        "status": "open",
        "differential_state": None,
        "autofix_available": False,
        "blocking": True,
        "waiver_reference": None,
        "execution_state": None,
        "evidence_outcome": None,
        "evidence_refs": None,
        "confidence": None,
        "rewrite_hint": None,
        "canonical_pattern": None,
        "intent_key": None,
        "estimated_deletion_lines": None,
        "related_locations": None,
        "guidance_kind": None,
        "recommended_action": None,
        "clean_code_principle": None,
        "rationale": None,
        "safety_checks": None,
        "preserve_reason": None,
        "action_status": None,
        "before_ref": None,
        "after_ref": None,
        "improvement": None,
        "signal_trace": None,
        "preserve_reasons": None,
        "remediation_packet": None,
    }


@pytest.mark.parametrize("explicit_none", [False, True])
@pytest.mark.parametrize("round_trip", [False, True])
def test_linux24_absent_diagnostic_preserves_complete_wire(linux24_legacy_finding, explicit_none, round_trip):
    from specfact_code_review.run.findings import ReviewFinding, ReviewReport

    payload = dict(linux24_legacy_finding)
    if explicit_none:
        payload["native_diagnostic"] = None
    finding = ReviewFinding.model_validate(payload)
    assert finding.model_dump(round_trip=round_trip) == linux24_legacy_finding
    assert finding.model_dump(mode="json", round_trip=round_trip) == linux24_legacy_finding
    assert json.loads(finding.model_dump_json(round_trip=round_trip)) == linux24_legacy_finding
    assert ReviewFinding.model_validate_json(json.dumps(payload)).model_dump() == linux24_legacy_finding
    assert ReviewFinding.model_validate(finding.model_dump()).model_dump() == linux24_legacy_finding
    report = ReviewReport(run_id="legacy", score=0, summary="legacy", findings=[finding])
    python_report = report.model_dump(round_trip=round_trip)
    json_report = json.loads(report.model_dump_json(round_trip=round_trip))
    assert python_report["findings"] == [linux24_legacy_finding]
    assert json_report["findings"] == [linux24_legacy_finding]
    assert report.model_dump(mode="json", round_trip=round_trip) == json_report
    assert json_report["run_id"] == "legacy"
    assert json_report["score"] == 0
    assert json_report["summary"] == "legacy"
    assert ReviewReport.model_validate_json(report.model_dump_json()).findings[0].model_dump() == linux24_legacy_finding


def test_linux24_absent_diagnostic_preserves_field_selection(linux24_legacy_finding):
    from specfact_code_review.run.findings import ReviewFinding

    finding = ReviewFinding.model_validate(linux24_legacy_finding)
    assert finding.model_dump(include={"native_diagnostic", "waiver_reference"}) == {"waiver_reference": None}
    expected = dict(linux24_legacy_finding)
    expected.pop("message")
    assert finding.model_dump(exclude={"message"}) == expected


@pytest.mark.parametrize(
    "diagnostic",
    [
        {"kind": "semgrep", "observations": [], "total_count": 0, "omitted_count": 0},
        {
            "kind": "pytest",
            "phase": "observation_read",
            "exception_kind": "FileNotFoundError",
            "stable_code": None,
            "child_returncode": None,
            "observation_state": "read_failed",
        },
    ],
)
def test_linux24_populated_diagnostic_preserves_complete_wire(linux24_legacy_finding, diagnostic):
    from specfact_code_review.run.findings import ReviewFinding, ReviewReport

    expected = {**linux24_legacy_finding, "native_diagnostic": diagnostic}
    finding = ReviewFinding.model_validate(expected)
    assert finding.model_dump() == expected
    assert finding.model_dump(mode="json", round_trip=True) == expected
    assert json.loads(finding.model_dump_json()) == expected
    assert ReviewFinding.model_validate_json(finding.model_dump_json()).model_dump() == expected
    report = ReviewReport(run_id="diagnostic", score=0, summary="diagnostic", findings=[finding])
    assert report.model_dump()["findings"] == [expected]
    assert report.model_dump(mode="json")["findings"] == [expected]
    assert json.loads(report.model_dump_json())["findings"] == [expected]
    assert finding.model_dump(include={"native_diagnostic", "waiver_reference"}) == {
        "native_diagnostic": diagnostic,
        "waiver_reference": None,
    }
    assert finding.model_dump(exclude={"native_diagnostic"}) == linux24_legacy_finding


def test_linux23_semgrep_usable_error_json_retains_native_data_when_results_invalid(tmp_path, monkeypatch):
    from specfact_code_review.tools import semgrep_runner

    monkeypatch.chdir(tmp_path)
    config = tmp_path / "rules.yaml"
    config.write_text("rules: []\n")
    monkeypatch.setattr(semgrep_runner, "skip_if_tool_missing", lambda *_: [])
    monkeypatch.setattr(semgrep_runner, "find_semgrep_config", lambda **_: config)
    monkeypatch.setattr(semgrep_runner, "find_semgrep_ai_bloat_config", lambda **_: None)
    monkeypatch.setattr(
        semgrep_runner,
        "_run_semgrep_command",
        lambda *_, **__: subprocess.CompletedProcess(
            [], 2, json.dumps({"errors": [{"type": "Syntax error", "path": "src/a.py"}]}), "PRIVATE"
        ),
    )
    finding = run_semgrep([Path("src/a.py")])[0]
    assert "semgrep output missing results key" in finding.message
    assert finding.native_diagnostic is not None
    assert finding.native_diagnostic.model_dump()["observations"][0]["input_path"] == "src/a.py"
