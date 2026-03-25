from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_CONFIG = REPO_ROOT / "docs" / "_config.yml"
DOCS_INDEX = REPO_ROOT / "docs" / "index.md"
DOCS_LAYOUT = REPO_ROOT / "docs" / "_layouts" / "default.html"
OUTDATED_DOCS_HOSTS = (
    "modules.docs.specfact.io",
    "cli.docs.specfact.io",
    "nold-ai.github.io/specfact-cli-modules",
    "nold-ai.github.io/specfact-cli",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_modules_docs_config_targets_public_modules_domain() -> None:
    config = _read(DOCS_CONFIG)

    assert 'url: "https://modules.specfact.io"' in config
    assert 'baseurl: ""' in config
    assert 'docs_home_url: "https://docs.specfact.io"' in config
    assert 'core_cli_docs_url: "https://docs.specfact.io"' in config
    assert 'modules_docs_url: "https://modules.specfact.io"' in config


def test_modules_landing_page_marks_modules_repo_as_canonical_owner() -> None:
    index = _read(DOCS_INDEX)

    assert "Canonical documentation for official nold-ai bundles" in index
    assert "bundle-specific deep guidance" in index or "module-specific workflows" in index
    assert "nold-ai.github.io/specfact-cli-modules" not in index


def test_modules_layout_exposes_shared_cross_site_navigation() -> None:
    layout = _read(DOCS_LAYOUT)

    assert ">Docs Home<" in layout
    assert ">Core CLI<" in layout
    assert ">Modules<" in layout
    assert "{{ site.docs_home_url }}" in layout
    assert "{{ site.core_cli_docs_url }}" in layout
    assert "{{ site.modules_docs_url }}" in layout


def test_modules_layout_keeps_sidebar_module_focused() -> None:
    layout = _read(DOCS_LAYOUT)

    assert "Official Modules Docs" in layout
    assert "Authoring" in layout
    assert "Bundles" in layout
    assert ">Examples<" not in layout


def test_docs_tree_does_not_reference_retired_public_hosts() -> None:
    skip_parts = frozenset({"vendor", "_site", ".bundle", ".jekyll-cache"})
    for path in REPO_ROOT.joinpath("docs").rglob("*"):
        if not path.is_file():
            continue
        if skip_parts.intersection(path.parts):
            continue
        text = _read(path)
        for host in OUTDATED_DOCS_HOSTS:
            assert host not in text, f"{path} still references retired host {host}"
