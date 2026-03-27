from __future__ import annotations

from pathlib import Path

from tests.unit._script_test_utils import load_module_from_path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check-docs-commands.py"


def _load_script():
    return load_module_from_path("check_docs_commands", SCRIPT_PATH)


def _script_attr(script, name: str):
    return getattr(script, name)


def test_extract_command_examples_reads_bash_and_inline_examples(tmp_path: Path) -> None:
    script = _load_script()
    doc_path = tmp_path / "example.md"
    doc_path.write_text(
        """
# Example

`specfact backlog refine --help`

```bash
specfact code review run --help
```
""".strip()
        + "\n",
        encoding="utf-8",
    )

    examples = _script_attr(script, "_extract_command_examples")(doc_path)

    assert [example.text for example in examples] == [
        "specfact code review run --help",
        "specfact backlog refine --help",
    ]


def test_command_example_is_valid_accepts_longest_matching_prefix() -> None:
    script = _load_script()
    valid_paths = {
        ("specfact", "backlog", "refine"),
        ("specfact", "code", "review", "run"),
    }

    assert _script_attr(script, "_command_example_is_valid")(
        "specfact code review run packages/specfact-code-review/src/specfact_code_review/run/commands.py",
        valid_paths,
    )
    assert not _script_attr(script, "_command_example_is_valid")("specfact backlog nonexistent --help", valid_paths)


def test_validate_legacy_resource_paths_reports_stale_core_owned_paths(tmp_path: Path) -> None:
    script = _load_script()
    doc_path = tmp_path / "legacy.md"
    doc_path.write_text(
        "Copy the prompt from src/specfact_cli/prompts/review.md before running the workflow.\n",
        encoding="utf-8",
    )

    findings = _script_attr(script, "_validate_legacy_resource_paths")([doc_path])

    assert len(findings) == 1
    assert findings[0].category == "legacy-resource"
    assert "src/specfact_cli/prompts" in findings[0].message


def test_validate_core_docs_links_rejects_unknown_route(tmp_path: Path) -> None:
    script = _load_script()
    doc_path = tmp_path / "links.md"
    doc_path.write_text(
        "[Broken](https://docs.specfact.io/missing/page/)\n"
        "[Allowed](https://docs.specfact.io/reference/documentation-url-contract/)\n",
        encoding="utf-8",
    )

    findings = _script_attr(script, "_validate_core_docs_links")([doc_path])

    assert len(findings) == 1
    assert findings[0].category == "cross-site-link"
    assert "missing/page" in findings[0].message


def test_docs_review_workflow_runs_docs_command_validation() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "docs-review.yml").read_text(encoding="utf-8")

    assert "python -m pip install pytest typer PyYAML beartype icontract rich pydantic specfact-cli" in workflow
    assert "python scripts/check-docs-commands.py" in workflow
    assert "scripts/check-docs-commands.py" in workflow
    assert "tests/unit/test_check_docs_commands_script.py" in workflow
