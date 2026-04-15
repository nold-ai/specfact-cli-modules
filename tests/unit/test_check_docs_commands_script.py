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

    examples = _script_attr(script, "_extract_command_examples_from_text")(
        doc_path.read_text(encoding="utf-8"), doc_path
    )

    assert [example.text for example in examples] == [
        "specfact code review run --help",
        "specfact backlog refine --help",
    ]


def test_iter_bash_examples_accepts_fence_suffixes(tmp_path: Path) -> None:
    script = _load_script()
    doc_path = tmp_path / "fenced.md"
    text = """
```bash {#commands}
specfact backlog refine --help
```
""".strip()

    examples = _script_attr(script, "_iter_bash_examples")(text, doc_path)

    assert [example.text for example in examples] == ["specfact backlog refine --help"]


def test_command_example_is_valid_accepts_longest_matching_prefix() -> None:
    script = _load_script()
    valid_paths = {
        ("specfact",),
        ("specfact", "backlog", "refine"),
        ("specfact", "code", "review", "run"),
    }

    assert _script_attr(script, "_command_example_is_valid")(
        "specfact code review run packages/specfact-code-review/src/specfact_code_review/run/commands.py",
        valid_paths,
    )
    assert not _script_attr(script, "_command_example_is_valid")("specfact backlog nonexistent --help", valid_paths)


def test_command_example_is_valid_allows_root_help_but_not_unknown_subgroups() -> None:
    script = _load_script()
    valid_paths = {
        ("specfact",),
        ("specfact", "backlog"),
        ("specfact", "backlog", "refine"),
    }

    assert _script_attr(script, "_command_example_is_valid")("specfact --help", valid_paths)
    assert _script_attr(script, "_command_example_is_valid")("specfact -h", valid_paths)
    assert not _script_attr(script, "_command_example_is_valid")("specfact policy validate --repo .", valid_paths)


def test_validate_legacy_resource_paths_reports_stale_core_owned_paths(tmp_path: Path) -> None:
    script = _load_script()
    doc_path = tmp_path / "legacy.md"
    doc_path.write_text(
        "Copy the prompt from src/specfact_cli/prompts/review.md before running the workflow.\n",
        encoding="utf-8",
    )

    scan = _script_attr(script, "_scan_text_by_path_for_findings")
    per_line = _script_attr(script, "_legacy_resource_findings_for_line")
    findings = scan({doc_path: doc_path.read_text(encoding="utf-8")}, per_line)

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

    scan = _script_attr(script, "_scan_text_by_path_for_findings")
    per_line = _script_attr(script, "_core_docs_link_findings_for_line")
    findings = scan({doc_path: doc_path.read_text(encoding="utf-8")}, per_line)

    assert len(findings) == 1
    assert findings[0].category == "cross-site-link"
    assert "missing/page" in findings[0].message


def test_validate_core_docs_links_allows_core_handoff_routes(tmp_path: Path) -> None:
    """Handoff URLs used in modules docs must stay in ALLOWED_CORE_DOCS_ROUTES (see scripts/check-docs-commands.py)."""
    script = _load_script()
    doc_path = tmp_path / "handoff.md"
    doc_path.write_text(
        "[Debug](https://docs.specfact.io/core-cli/debug-logging/)\n"
        "[Debug anchor](https://docs.specfact.io/core-cli/debug-logging/#examining-ado-api-errors)\n"
        "[Directory](https://docs.specfact.io/reference/directory-structure/)\n"
        "[Feature keys](https://docs.specfact.io/reference/feature-keys/)\n",
        encoding="utf-8",
    )

    scan = _script_attr(script, "_scan_text_by_path_for_findings")
    per_line = _script_attr(script, "_core_docs_link_findings_for_line")
    findings = scan({doc_path: doc_path.read_text(encoding="utf-8")}, per_line)

    assert not findings


def test_docs_pages_workflow_runs_python_docs_validation() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "docs-pages.yml").read_text(encoding="utf-8")
    install_snip = "python -m pip install -r requirements-docs-ci.txt"
    check_snip = "python scripts/check-docs-commands.py --jekyll-bundle-check"
    assert install_snip in workflow
    assert check_snip in workflow
    install_index = workflow.index(install_snip)
    check_index = workflow.index(check_snip)
    upload_index = workflow.index("Upload artifact")
    assert install_index < check_index, "pip install must precede docs validation in the workflow file"
    assert check_index < upload_index, "docs validation must run before the Pages artifact upload step"


def test_docs_review_workflow_runs_docs_command_validation() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "docs-review.yml").read_text(encoding="utf-8")

    assert "python -m pip install -r requirements-docs-ci.txt" in workflow
    assert "python scripts/check-docs-commands.py" in workflow
    assert "scripts/check-docs-commands.py" in workflow
    assert "tests/unit/test_check_docs_commands_script.py" in workflow
    assert "tests/unit/docs/test_code_review_docs_parity.py" in workflow


def test_iter_validation_docs_paths_scans_repo_wide_docs_tree() -> None:
    script = _load_script()

    paths = _script_attr(script, "_iter_validation_docs_paths")()
    relative_paths = {path.relative_to(REPO_ROOT).as_posix() for path in paths}

    assert "docs/bundles/backlog/overview.md" in relative_paths
    assert "docs/getting-started/README.md" in relative_paths
    assert "docs/integrations/devops-adapter-overview.md" in relative_paths
