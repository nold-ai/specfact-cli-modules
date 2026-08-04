from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
import yaml

from tests.unit._script_test_utils import load_module_from_path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check-docs-commands.py"


def _load_script():
    return load_module_from_path("check_docs_commands", SCRIPT_PATH)


def _script_attr(script, name: str):
    return getattr(script, name)


def test_docs_command_mounts_include_nested_prompt_validator_mounts() -> None:
    script = _load_script()
    mounts = set(_script_attr(script, "MODULE_APP_MOUNTS"))

    assert ("specfact_govern.enforce.commands", "app", ("specfact", "govern", "enforce")) in mounts
    assert ("specfact_spec.contract.commands", "app", ("specfact", "spec", "contract")) in mounts
    assert ("specfact_spec.sdd.commands", "app", ("specfact", "spec")) in mounts
    assert ("specfact_spec.generate.commands", "app", ("specfact", "spec")) in mounts


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


def test_command_example_rejects_unknown_trailing_subcommand() -> None:
    script = _load_script()
    valid_paths = {
        ("specfact",),
        ("specfact", "code"),
        ("specfact", "code", "review"),
        ("specfact", "code", "review", "run"),
    }

    assert not _script_attr(script, "_command_example_is_valid")("specfact code review review run --help", valid_paths)


def test_command_example_allows_positional_arguments_for_an_executable_group() -> None:
    script = _load_script()
    valid_paths = {
        ("specfact",),
        ("specfact", "code"),
        ("specfact", "code", "import"),
        ("specfact", "code", "import", "from-code"),
    }

    assert _script_attr(script, "_command_example_is_valid")(
        "specfact code import my-bundle",
        valid_paths,
        {("specfact", "code", "import")},
    )


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


@pytest.mark.parametrize(
    ("content", "message"),
    (
        ('{"command": "specfact backlog"}\n', "expected a JSON list"),
        ('[{"owner_package": "specfact-backlog"}]\n', "missing 'command'"),
    ),
)
def test_build_valid_command_paths_rejects_malformed_generated_input(
    tmp_path: Path, monkeypatch, content: str, message: str
) -> None:
    script = _load_script()
    generated = tmp_path / "commands.generated.json"
    generated.write_text(content, encoding="utf-8")
    monkeypatch.setattr(script, "GENERATED_COMMANDS_PATH", generated)

    with pytest.raises(ValueError, match=message):
        _script_attr(script, "_build_command_inventory")()


def _scan_path_findings(script, path: Path, text: str, finding_function: str):
    path.write_text(text, encoding="utf-8")
    scan = _script_attr(script, "_scan_text_by_path_for_findings")
    per_line = _script_attr(script, finding_function)
    return scan({path: path.read_text(encoding="utf-8")}, per_line)


@pytest.mark.parametrize(
    "case",
    (
        (
            "legacy.md",
            "Copy the prompt from src/specfact_cli/prompts/review.md before running the workflow.\n",
            "_legacy_resource_findings_for_line",
            "legacy-resource",
            "src/specfact_cli/prompts",
        ),
        (
            "links.md",
            "[Broken](https://docs.specfact.io/missing/page/)\n"
            "[Allowed](https://docs.specfact.io/reference/documentation-url-contract/)\n",
            "_core_docs_link_findings_for_line",
            "cross-site-link",
            "missing/page",
        ),
    ),
)
def test_docs_validation_reports_stale_reference_findings(tmp_path: Path, case: tuple[str, str, str, str, str]) -> None:
    filename, text, finding_function, category, message = case
    script = _load_script()
    findings = _scan_path_findings(script, tmp_path / filename, text, finding_function)

    assert len(findings) == 1
    assert findings[0].category == category
    assert message in findings[0].message


def test_validate_core_docs_links_allows_core_handoff_routes(tmp_path: Path) -> None:
    """Handoff URLs used in modules docs must stay in ALLOWED_CORE_DOCS_ROUTES (see scripts/check-docs-commands.py)."""
    script = _load_script()
    doc_path = tmp_path / "handoff.md"
    findings = _scan_path_findings(
        script,
        doc_path,
        "[Debug](https://docs.specfact.io/core-cli/debug-logging/)\n"
        "[Debug anchor](https://docs.specfact.io/core-cli/debug-logging/#examining-ado-api-errors)\n"
        "[Directory](https://docs.specfact.io/reference/directory-structure/)\n"
        "[Feature keys](https://docs.specfact.io/reference/feature-keys/)\n",
        "_core_docs_link_findings_for_line",
    )

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
    assert 'hatch run python -m pip install -e "${SPECFACT_CLI_REPO}"' in workflow
    assert "python scripts/check-docs-commands.py" in workflow
    assert "scripts/check-docs-commands.py" in workflow
    assert "tests/unit/test_check_docs_commands_script.py" in workflow
    assert "tests/unit/docs/test_code_review_docs_parity.py" in workflow


def test_docs_review_workflow_uses_matching_core_branch_when_available() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "docs-review.yml").read_text(encoding="utf-8")

    assert "id: core-ref" in workflow
    assert "git ls-remote --exit-code --heads https://github.com/nold-ai/specfact-cli.git" in workflow
    assert "FALLBACK_REF: ${{ github.base_ref || github.ref_name }}" in workflow
    assert 'echo "ref=$fallback" >> "$GITHUB_OUTPUT"' in workflow
    assert "ref: ${{ steps.core-ref.outputs.ref }}" in workflow
    assert (
        "ref: ${{ (github.ref == 'refs/heads/main' || github.head_ref == 'main') && 'main' || 'dev' }}" not in workflow
    )


def _docs_review_workflow() -> dict[str, object]:
    workflow = yaml.load(
        (REPO_ROOT / ".github" / "workflows" / "docs-review.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    assert isinstance(workflow, dict)
    return workflow


def _docs_review_steps(workflow: dict[str, object]) -> list[dict[str, str]]:
    jobs = cast(dict[str, dict[str, list[dict[str, str]]]], workflow["jobs"])
    return jobs["docs-review"]["steps"]


def _step_named(steps: list[dict[str, str]], name: str) -> tuple[int, dict[str, str]]:
    return next((index, step) for index, step in enumerate(steps) if step.get("name") == name)


def test_docs_review_checks_module_inventory_and_core_accountability() -> None:
    workflow = _docs_review_workflow()
    triggers = cast(dict[str, dict[str, list[str]]], workflow["on"])

    for path in (
        "packages/**",
        "registry/**",
        "scripts/check-core-documentation-accountability.py",
        "tests/unit/test_core_documentation_accountability.py",
    ):
        assert path in triggers["pull_request"]["paths"]
        assert path in triggers["push"]["paths"]

    steps = _docs_review_steps(workflow)
    _review_index, review_step = _step_named(steps, "Run docs review suite")
    for test_path in (
        "tests/unit/test_core_documentation_accountability.py",
        "tests/unit/test_pre_commit_quality_parity.py",
        "tests/unit/docs/test_llms_overview_freshness.py",
    ):
        assert test_path in review_step["run"]
    accountability_index, accountability_step = _step_named(steps, "Validate core documentation accountability")
    upload_index, _upload_step = _step_named(steps, "Upload docs review logs")
    assert accountability_step["run"] == "hatch run check-core-documentation-accountability"
    assert accountability_step.get("continue-on-error") not in {True, "true"}
    assert accountability_index < upload_index


def test_iter_validation_docs_paths_scans_repo_wide_docs_tree() -> None:
    script = _load_script()

    paths = _script_attr(script, "_iter_validation_docs_paths")()
    relative_paths = {path.relative_to(REPO_ROOT).as_posix() for path in paths}

    assert "docs/bundles/backlog/overview.md" in relative_paths
    assert "docs/getting-started/README.md" in relative_paths
    assert "docs/integrations/devops-adapter-overview.md" in relative_paths
