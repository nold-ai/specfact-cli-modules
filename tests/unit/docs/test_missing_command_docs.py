"""Contract tests for the docs-09 missing command reference pages."""

from __future__ import annotations

from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]

_EXPECTED_PAGES: dict[str, tuple[str, ...]] = {
    "docs/bundles/spec/validate.md": (
        "specfact spec validate",
        "specfact spec backward-compat",
        "Bundle-owned resources",
    ),
    "docs/bundles/spec/generate-tests.md": (
        "specfact spec generate-tests",
        "--bundle",
        "--output",
    ),
    "docs/bundles/spec/mock.md": (
        "specfact spec mock",
        "--spec",
        "--port",
    ),
    "docs/bundles/govern/enforce.md": (
        "specfact govern enforce stage",
        "specfact govern enforce sdd",
        "--output-format",
    ),
    "docs/bundles/govern/patch.md": (
        "specfact govern patch apply",
        "--write",
        "--dry-run",
    ),
    "docs/bundles/code-review/run.md": (
        "specfact code review run",
        "--scope",
        "--fix",
    ),
    "docs/bundles/code-review/ledger.md": (
        "specfact code review ledger status",
        "specfact code review ledger update",
        "--from",
    ),
    "docs/bundles/code-review/rules.md": (
        "specfact code review rules show",
        "specfact code review rules init",
        "--ide",
    ),
    "docs/bundles/codebase/analyze.md": (
        "specfact code analyze contracts",
        "--repo",
        "--bundle",
    ),
    "docs/bundles/codebase/drift.md": (
        "specfact code drift detect",
        "--format",
        "--out",
    ),
    "docs/bundles/codebase/repro.md": (
        "specfact code repro --repo .",
        "specfact code repro setup",
        "--sidecar-bundle",
    ),
}

_EXPECTED_OVERVIEW_LINKS: dict[str, tuple[str, ...]] = {
    "docs/bundles/spec/overview.md": ("validate/", "generate-tests/", "mock/"),
    "docs/bundles/govern/overview.md": ("enforce/", "patch/"),
    "docs/bundles/code-review/overview.md": ("run/", "ledger/", "rules/"),
    "docs/bundles/codebase/overview.md": ("analyze/", "drift/", "repro/"),
}


def _read_repo_text(relative_path: str) -> str:
    return (_REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_missing_command_docs_pages_exist_and_cover_expected_commands() -> None:
    for relative_path, expected_snippets in _EXPECTED_PAGES.items():
        page_path = _REPO_ROOT / relative_path
        assert page_path.exists(), f"missing docs page: {relative_path}"

        page_text = _read_repo_text(relative_path)
        assert page_text.startswith("---\n"), f"missing front matter: {relative_path}"
        for snippet in expected_snippets:
            assert snippet in page_text, f"{relative_path} missing snippet: {snippet}"


def test_bundle_overviews_link_to_new_command_reference_pages() -> None:
    for relative_path, expected_links in _EXPECTED_OVERVIEW_LINKS.items():
        overview_text = _read_repo_text(relative_path)
        for link_suffix in expected_links:
            assert link_suffix in overview_text, f"{relative_path} missing link containing: {link_suffix}"
