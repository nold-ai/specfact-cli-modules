"""Docs review gate: link integrity, front matter, and navigation checks.

Adapted from specfact-cli/tests/unit/docs/test_release_docs_parity.py to
validate the modules docs site (modules.specfact.io).
"""

from __future__ import annotations

import re
import sys
import warnings
from pathlib import Path
from urllib.parse import unquote


_REPO_FOR_SCRIPTS = Path(__file__).resolve().parents[3]
_SCRIPTS_DIR = _REPO_FOR_SCRIPTS / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import docs_site_validation as dsv  # noqa: E402


MODULES_DOCS_HOST = "modules.specfact.io"
CORE_DOCS_HOST = "docs.specfact.io"
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
HTML_HREF_RE = re.compile(r'href="([^"]+)"')
JEKYLL_RELATIVE_URL_RE = re.compile(r'\{\{\s*[\'"]([^\'"]+)[\'"]\s*\|\s*relative_url\s*\}\}')
REQUIRED_NAV_FRONT_MATTER_KEYS = ("layout", "title", "permalink")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _repo_file(path: str) -> Path:
    return _repo_root() / path


def _docs_root() -> Path:
    return _repo_root() / "docs"


_SKIP_DOCS_TREE_PARTS = frozenset({"_site", "vendor", ".bundle", ".jekyll-cache"})


def _is_docs_markdown(path: Path) -> bool:
    return path.suffix == ".md" and not _SKIP_DOCS_TREE_PARTS.intersection(path.parts)


def _is_publishable_page(path: Path) -> bool:
    """True if the file is expected to be a published Jekyll page (not a README index)."""
    return _is_docs_markdown(path) and path.name != "README.md"


def _iter_docs_markdown_paths() -> list[Path]:
    return sorted(path.resolve() for path in _docs_root().rglob("*.md") if _is_docs_markdown(path))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _split_front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text

    lines = text.splitlines()
    end_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break
    if end_index is None:
        return {}, text

    metadata: dict[str, str] = {}
    for raw_line in lines[1:end_index]:
        if ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")

    body = "\n".join(lines[end_index + 1 :])
    return metadata, body


def _normalize_route(route: str) -> str:
    cleaned = unquote(route.strip())
    if not cleaned:
        return "/"
    if not cleaned.startswith("/"):
        cleaned = "/" + cleaned
    cleaned = re.sub(r"/{2,}", "/", cleaned)
    if cleaned != "/" and not cleaned.endswith("/"):
        cleaned += "/"
    return cleaned


def _front_matter_end_index(lines: list[str]) -> int | None:
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return index
    return None


def _extract_redirect_route(stripped_line: str) -> str | None:
    if not stripped_line.startswith("- "):
        return None
    route = stripped_line[2:].split("#", 1)[0].strip().strip('"').strip("'")
    return _normalize_route(route)


def _list_front_matter_redirect_from_routes(text: str) -> list[str]:
    """Return normalized redirect_from routes declared in YAML front matter only."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return []

    end_index = _front_matter_end_index(lines)
    if end_index is None:
        return []

    routes: list[str] = []
    in_redirect_block = False
    for line in lines[1:end_index]:
        if line.strip() == "redirect_from:":
            in_redirect_block = True
            continue
        if in_redirect_block:
            stripped = line.strip()
            route = _extract_redirect_route(stripped)
            if route is not None:
                routes.append(route)
            elif stripped and not stripped.startswith("#"):
                in_redirect_block = False
    return routes


def _published_route_for_path(path: Path, metadata: dict[str, str]) -> str:
    permalink = metadata.get("permalink")
    if permalink:
        return _normalize_route(permalink)
    return _normalize_route(f"/{path.stem}/")


def _extract_links(source: Path, content: str) -> list[str]:
    if source.suffix == ".html":
        return HTML_HREF_RE.findall(content)
    links = []
    for line in content.splitlines():
        # Skip lines with TODO comments indicating known missing targets
        if "<!-- TODO:" in line:
            continue
        links.extend(MARKDOWN_LINK_RE.findall(line))
    return links


def _navigation_sources() -> list[Path]:
    return [
        _repo_file("docs/index.md").resolve(),
        _repo_file("docs/_layouts/default.html").resolve(),
    ]


def _scan_navigation_targets() -> tuple[list[str], set[Path]]:
    docs_root = _docs_root()
    repo_root = _repo_root()
    route_to_path = dsv.build_route_index(docs_root)
    path_to_route = dsv.build_path_to_canonical_route(docs_root)
    ctx = dsv.DocsLinkResolutionContext(docs_root, route_to_path, path_to_route, dsv.MODULES_DOCS_HOST)
    failures: list[str] = []
    targets: set[Path] = set()

    for source in _navigation_sources():
        text = _read_text(source)
        if source.suffix == ".md":
            fm, _, _ = dsv.split_yaml_front_matter(text)
            published = dsv.published_route_for_doc(source, docs_root, fm)
        else:
            published = "/"
        for link in _extract_links(source, text):
            target, err = dsv.resolve_internal_link_hybrid(
                source=source,
                ctx=ctx,
                published_page_route=published,
                raw_link=link,
            )
            if err:
                failures.append(f"{source.relative_to(repo_root)}: {err}")
            if target is not None:
                targets.add(target.resolve())

    return failures, targets


def _scan_authored_doc_link_failures() -> tuple[list[str], set[Path]]:
    findings = dsv.scan_published_route_body_links(_docs_root(), _repo_root())
    return [f.message for f in findings], set()


# ---------------------------------------------------------------------------
# Front matter validation
# ---------------------------------------------------------------------------


def test_all_publishable_docs_pages_have_jekyll_front_matter() -> None:
    """All .md files that are expected to be published pages (not READMEs) must
    have Jekyll front matter starting with ``---``.

    Files in the restructured directories (bundles/, authoring/, integrations/)
    are hard failures. Pre-existing files without front matter are warnings.
    """
    restructured_prefixes = ("bundles/", "authoring/", "integrations/", "workflows/", "team-and-enterprise/")
    missing: list[str] = []
    for path in _iter_docs_markdown_paths():
        if not _is_publishable_page(path):
            continue
        text = _read_text(path)
        first_line = text.splitlines()[0] if text else ""
        if first_line != "---":
            missing.append(str(path.relative_to(_repo_root())))
    restructured_missing = [m for m in missing if any(f"docs/{p}" in m for p in restructured_prefixes)]
    preexisting_missing = [m for m in missing if m not in restructured_missing]
    if preexisting_missing:
        warnings.warn(
            f"Pre-existing docs files missing front matter ({len(preexisting_missing)}):\n"
            + "\n".join(preexisting_missing),
            stacklevel=1,
        )
    assert not restructured_missing, "Restructured docs files missing front matter:\n" + "\n".join(restructured_missing)


# ---------------------------------------------------------------------------
# Navigation link integrity
# ---------------------------------------------------------------------------


def test_navigation_links_resolve_to_published_docs_routes() -> None:
    failures, _ = _scan_navigation_targets()
    assert not failures, "Broken navigation docs links:\n" + "\n".join(sorted(failures))


def test_authored_internal_docs_links_resolve_to_published_docs_targets() -> None:
    """Internal Markdown links must pass the shared published-route scanner."""
    failures, _ = _scan_authored_doc_link_failures()
    assert not failures, "Broken authored docs links:\n" + "\n".join(sorted(failures))


def test_navigation_link_targets_have_required_front_matter_keys() -> None:
    """Nav link targets must have layout, title, and permalink."""
    _, targets = _scan_navigation_targets()
    missing: list[str] = []

    for target in sorted(targets):
        fm, _, _ = dsv.split_yaml_front_matter(_read_text(target))
        missing_keys = [key for key in REQUIRED_NAV_FRONT_MATTER_KEYS if not fm.get(key)]
        if missing_keys:
            missing.append(f"{target.relative_to(_repo_root())}: missing {', '.join(missing_keys)}")

    assert not missing, "Nav targets missing required front matter keys:\n" + "\n".join(missing)


# ---------------------------------------------------------------------------
# Cross-site navigation
# ---------------------------------------------------------------------------


def test_top_navigation_exposes_docs_home_core_cli_and_modules() -> None:
    layout = _read_text(_repo_file("docs/_layouts/default.html"))
    assert ">Docs Home<" in layout
    assert ">Core CLI<" in layout
    assert ">Modules<" in layout


def test_config_links_to_core_docs_site() -> None:
    config = _read_text(_repo_file("docs/_config.yml"))
    assert CORE_DOCS_HOST in config


# ---------------------------------------------------------------------------
# Redirect coverage for moved files
# ---------------------------------------------------------------------------


def _guides_legacy_redirect_violation(path: Path, text: str) -> str | None:
    """If ``docs/guides/<stem>.md`` publishes outside ``/guides/``, require ``redirect_from`` for ``/guides/<stem>/``.

    Returns a human-readable violation message, or ``None`` when the rule is satisfied.
    """
    try:
        rel = path.relative_to(_docs_root())
    except ValueError:
        return None
    if len(rel.parts) < 2 or rel.parts[0] != "guides" or rel.suffix != ".md":
        return None
    if rel.name == "README.md":
        return None

    metadata, _ = _split_front_matter(text)
    canonical = _published_route_for_path(path, metadata)
    if canonical.startswith("/guides/"):
        return None

    expected = _normalize_route(f"/guides/{path.stem}/")
    redirects = _list_front_matter_redirect_from_routes(text)
    if expected in redirects:
        return None
    return (
        f"{path}: canonical {canonical} is outside /guides/ but redirect_from "
        f"does not include legacy alias {expected} (got {redirects})"
    )


def _iter_guides_legacy_redirect_violations() -> list[str]:
    guides = _docs_root() / "guides"
    if not guides.is_dir():
        return []
    violations: list[str] = []
    for path in sorted(guides.glob("*.md")):
        if path.name == "README.md":
            continue
        text = _read_text(path)
        msg = _guides_legacy_redirect_violation(path.resolve(), text)
        if msg:
            violations.append(msg)
    return violations


def test_daily_devops_routine_exists() -> None:
    assert _repo_file("docs/guides/daily-devops-routine.md").is_file()


def test_daily_devops_routine_bundle_links() -> None:
    text = _read_text(_repo_file("docs/guides/daily-devops-routine.md"))
    expected_links = {
        "Morning standup": "[Backlog bundle overview](/bundles/backlog/overview/)",
        "Refinement": "[Cross-module chains](/guides/cross-module-chains/)",
        "Development": "[AI IDE workflow](/ai-ide-workflow/)",
        "Review": "[Contract testing workflow](/contract-testing-workflow/)",
        "End-of-day": "[Govern enforce](/bundles/govern/enforce/)",
    }

    for label, link in expected_links.items():
        assert link in text, f"{label} step is missing bundle command reference link {link}"


def _extract_redirect_from_entries() -> dict[str, Path]:
    """Build map of redirect_from routes to the file that declares them."""
    redirects: dict[str, Path] = {}
    for path in _iter_docs_markdown_paths():
        text = _read_text(path)
        if "redirect_from:" not in text:
            continue
        for route in _list_front_matter_redirect_from_routes(text):
            redirects[route] = path
    return redirects


def test_list_front_matter_redirect_from_routes_ignores_body_redirect_marker() -> None:
    text = """---
layout: default
title: Example
redirect_from:
  - /legacy-path/
---

Body content.

redirect_from:
  - /not-front-matter/
"""

    assert _list_front_matter_redirect_from_routes(text) == ["/legacy-path/"]


def test_list_front_matter_redirect_from_routes_keeps_entries_after_comments() -> None:
    text = """---
layout: default
title: Example
redirect_from:
  # legacy aliases
  - /legacy-one/ # keep

  - \"/legacy-two/\"
permalink: /current/
---
Body
"""

    assert _list_front_matter_redirect_from_routes(text) == ["/legacy-one/", "/legacy-two/"]


def test_moved_files_have_redirect_from_entries() -> None:
    """Every file under bundles/, authoring/, integrations/ that was moved from
    guides/ should have a redirect_from entry pointing to its old location."""
    redirects = _extract_redirect_from_entries()
    moved_dirs = ("bundles", "authoring", "integrations")
    missing: list[str] = []

    for path in _iter_docs_markdown_paths():
        rel = path.relative_to(_docs_root())
        if not any(str(rel).startswith(d) for d in moved_dirs):
            continue
        # New per-bundle landing pages (not migrated from guides/) have no legacy URL.
        parts = rel.parts
        if len(parts) >= 3 and parts[0] == "bundles" and path.name == "overview.md":
            continue
        metadata, _ = _split_front_matter(_read_text(path))
        if not metadata:
            continue
        # Check that at least one redirect_from entry exists for this file
        found = any(v == path for v in redirects.values())
        if not found:
            missing.append(str(rel))

    assert not missing, "Moved files missing redirect_from entries:\n" + "\n".join(missing)


def test_guides_canonical_outside_guides_prefix_includes_legacy_redirect_alias() -> None:
    """docs-06 §7.4: require ``/guides/<basename>/`` in ``redirect_from`` for guides with non-/guides/ canonical URLs.

    Applies to ``docs/guides/*.md`` whose canonical permalink is not under ``/guides/``.
    """
    violations = _iter_guides_legacy_redirect_violations()
    assert not violations, "Guides legacy redirect alias missing:\n" + "\n".join(violations)


def test_guides_legacy_redirect_rule_passing_example() -> None:
    path = _docs_root() / "guides" / "example-pass.md"
    text = """---
layout: default
title: Example
permalink: /example-pass/
redirect_from:
  - /guides/example-pass/
---
"""
    assert _guides_legacy_redirect_violation(path.resolve(), text) is None


def test_guides_legacy_redirect_rule_failing_example() -> None:
    path = _docs_root() / "guides" / "example-fail.md"
    text = """---
layout: default
title: Example
permalink: /example-fail/
---
"""
    msg = _guides_legacy_redirect_violation(path.resolve(), text)
    assert msg is not None
    assert "/guides/example-fail/" in msg


def test_team_and_enterprise_pages_exist() -> None:
    expected = [
        _repo_file("docs/team-and-enterprise/team-collaboration.md"),
        _repo_file("docs/team-and-enterprise/agile-scrum-setup.md"),
        _repo_file("docs/team-and-enterprise/multi-repo.md"),
        _repo_file("docs/team-and-enterprise/enterprise-config.md"),
    ]
    missing = [str(path.relative_to(_repo_root())) for path in expected if not path.is_file()]
    assert not missing, "Missing team-and-enterprise docs pages:\n" + "\n".join(missing)


def test_team_and_enterprise_pages_use_bundle_owned_resource_language() -> None:
    files = [
        _repo_file("docs/team-and-enterprise/team-collaboration.md"),
        _repo_file("docs/team-and-enterprise/agile-scrum-setup.md"),
        _repo_file("docs/team-and-enterprise/multi-repo.md"),
        _repo_file("docs/team-and-enterprise/enterprise-config.md"),
    ]
    combined = "\n".join(_read_text(path) for path in files)
    assert "bundle-owned" in combined
    assert "specfact init ide" in combined


def test_team_and_enterprise_index_links_exist() -> None:
    text = _read_text(_repo_file("docs/index.md"))
    expected_links = [
        "team-and-enterprise/team-collaboration/",
        "team-and-enterprise/agile-scrum-setup/",
        "team-and-enterprise/multi-repo/",
        "team-and-enterprise/enterprise-config/",
    ]
    for link in expected_links:
        assert link in text


# ---------------------------------------------------------------------------
# Config plugin alignment
# ---------------------------------------------------------------------------


def test_config_includes_redirect_from_plugin() -> None:
    config = _read_text(_repo_file("docs/_config.yml"))
    assert "jekyll-redirect-from" in config


def test_gemfile_includes_redirect_from_gem() -> None:
    gemfile = _read_text(_repo_file("docs/Gemfile"))
    assert "jekyll-redirect-from" in gemfile
