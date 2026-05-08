from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit._script_test_utils import load_module_from_path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check-prompt-commands.py"
DOCS_REVIEW_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "docs-review.yml"
PRE_COMMIT_SCRIPT = REPO_ROOT / "scripts" / "pre-commit-quality-checks.sh"


def _load_script():
    return load_module_from_path("check_prompt_commands", SCRIPT_PATH)


def _script_attr(script, name: str):
    return getattr(script, name)


def _write_prompt(tmp_path: Path, text: str) -> Path:
    prompt = tmp_path / "packages" / "specfact-codebase" / "resources" / "prompts" / "specfact.validate.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text(text.strip() + "\n", encoding="utf-8")
    return prompt


def test_extract_prompt_command_examples_handles_common_prompt_syntax(tmp_path: Path) -> None:
    script = _load_script()
    prompt = _write_prompt(
        tmp_path,
        """
# Prompt

Run `/specfact.validate --repo .` when using the IDE shortcut.

```bash
# comments are ignored
specfact code repro --repo . \\
  --budget 120
```

- `specfact govern enforce sdd --no-interactive`
""",
    )

    examples = _script_attr(script, "_extract_prompt_command_examples_from_text")(
        prompt.read_text(encoding="utf-8"), prompt
    )

    assert [example.text for example in examples] == [
        "specfact code repro --repo . --budget 120",
        "specfact govern enforce sdd --no-interactive",
        "specfact.validate --repo .",
    ]


def test_validate_prompt_commands_reports_stale_command_path(tmp_path: Path) -> None:
    script = _load_script()
    prompt = _write_prompt(
        tmp_path,
        """
Prompt instructions are operating guidance. Current CLI help is authoritative; if this prompt drifts, inspect `--help`.

```bash
specfact repro --repo .
```
""",
    )
    command_index = _script_attr(script, "CommandIndex")(
        command_paths={("specfact",), ("specfact", "code"), ("specfact", "code", "repro")},
        options_by_path={("specfact", "code", "repro"): {"--repo"}},
    )

    findings = _script_attr(script, "_validate_prompt_command_examples")(
        {prompt: prompt.read_text(encoding="utf-8")},
        command_index,
    )

    assert len(findings) == 1
    assert findings[0].category == "command"
    assert "specfact repro --repo ." in findings[0].message


def test_main_writes_findings_to_stderr(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    script = _load_script()
    prompt = _write_prompt(
        tmp_path,
        """
Prompt instructions are operating guidance for SpecFact CLI, not the source of truth.
Current CLI help is authoritative. If a command or option fails, inspect the nearest valid `--help`,
correct the invocation when the mapping is obvious, and ask the user when no safe correction is clear.

```bash
specfact repro --repo .
```
""",
    )

    assert _script_attr(script, "_main")([str(prompt)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Unknown prompt command example: specfact repro --repo ." in captured.err


def test_validate_prompt_commands_reports_stale_option(tmp_path: Path) -> None:
    script = _load_script()
    prompt = _write_prompt(
        tmp_path,
        """
Prompt instructions are operating guidance. Current CLI help is authoritative; if this prompt drifts, inspect `--help`.

`specfact code repro --repo . --missing-option`
""",
    )
    command_index = _script_attr(script, "CommandIndex")(
        command_paths={("specfact",), ("specfact", "code"), ("specfact", "code", "repro")},
        options_by_path={("specfact", "code", "repro"): {"--repo", "--help"}},
    )

    findings = _script_attr(script, "_validate_prompt_command_examples")(
        {prompt: prompt.read_text(encoding="utf-8")},
        command_index,
    )

    assert len(findings) == 1
    assert findings[0].category == "option"
    assert "--missing-option" in findings[0].message


def test_validate_prompt_guidance_requires_cli_reality_check(tmp_path: Path) -> None:
    script = _load_script()
    prompt = _write_prompt(
        tmp_path,
        """
```bash
specfact code repro --repo .
```
""",
    )

    findings = _script_attr(script, "_validate_cli_reality_check_guidance")(
        {prompt: prompt.read_text(encoding="utf-8")}
    )

    assert len(findings) == 1
    assert findings[0].category == "guidance"
    assert "CLI reality-check" in findings[0].message


def test_validate_prompt_guidance_accepts_self_healing_language(tmp_path: Path) -> None:
    script = _load_script()
    prompt = _write_prompt(
        tmp_path,
        """
Prompt instructions are operating guidance for SpecFact CLI, not the source of truth.
Current CLI help is authoritative. If a command or option fails, inspect the nearest valid `--help`,
correct the invocation when the mapping is obvious, and ask the user when no safe correction is clear.

```bash
specfact code repro --repo .
```
""",
    )

    findings = _script_attr(script, "_validate_cli_reality_check_guidance")(
        {prompt: prompt.read_text(encoding="utf-8")}
    )

    assert not findings


def test_build_command_index_reports_failed_mount_context(monkeypatch: pytest.MonkeyPatch) -> None:
    script = _load_script()

    monkeypatch.setattr(script, "MODULE_APP_MOUNTS", (("missing.module", "app", ("specfact", "missing")),))

    with pytest.raises(RuntimeError) as exc_info:
        _script_attr(script, "_build_command_index")()

    message = str(exc_info.value)
    assert "missing.module:app" in message
    assert "specfact missing" in message


def test_module_app_mounts_include_govern_enforce_app() -> None:
    script = _load_script()

    assert (
        "specfact_govern.enforce.commands",
        "app",
        ("specfact", "govern", "enforce"),
    ) in _script_attr(script, "MODULE_APP_MOUNTS")


def test_docs_review_workflow_runs_prompt_command_validation() -> None:
    workflow = DOCS_REVIEW_WORKFLOW.read_text(encoding="utf-8")

    assert "packages/*/resources/prompts/**" in workflow
    assert "python scripts/check-prompt-commands.py" in workflow
    assert "scripts/check-prompt-commands.py" in workflow
    assert "tests/unit/test_check_prompt_commands_script.py" in workflow


def test_pre_commit_runs_prompt_validation_before_safe_change_skip() -> None:
    script = PRE_COMMIT_SCRIPT.read_text(encoding="utf-8")

    validation_index = script.index("run_prompt_command_validation_gate")
    safe_change_index = script.index("if check_safe_change; then")
    assert validation_index < safe_change_index
