"""Docs review gate: link integrity, front matter, and navigation checks.

Adapted from specfact-cli/tests/unit/docs/test_release_docs_parity.py to
validate the modules docs site (modules.specfact.io).
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path
from urllib.parse import unquote, urlparse


MODULES_DOCS_HOST = "modules.specfact.io"
CORE_DOCS_HOST = "docs.specfact.io"
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
HTML_HREF_RE = re.compile(r'href="([^"]+)"')
JEKYLL_RELATIVE_URL_RE = re.compile(r'\{\{\s*[\'"]([^\'"]+)[\'"]\s*\|\s*relative_url\s*\}\}')
JEKYLL_SITE_VAR_RE = re.compile(r"\{\{.*\}\}")
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


def _list_front_matter_redirect_from_routes(text: str) -> list[str]:
    """Return normalized redirect_from routes declared in YAML front matter only."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return []

    end_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break
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
            if stripped.startswith("- "):
                route = stripped[2:].split("#", 1)[0].strip().strip('"').strip("'")
                routes.append(_normalize_route(route))
            elif stripped and not stripped.startswith("-") and not stripped.startswith("#"):
                in_redirect_block = False
    return routes


def _published_route_for_path(path: Path, metadata: dict[str, str]) -> str:
    permalink = metadata.get("permalink")
    if permalink:
        return _normalize_route(permalink)
    return _normalize_route(f"/{path.stem}/")


def _build_published_docs_index() -> tuple[dict[str, Path], dict[Path, dict[str, str]], dict[Path, str]]:
    route_to_path: dict[str, Path] = {}
    path_to_metadata: dict[Path, dict[str, str]] = {}
    path_to_route: dict[Path, str] = {}

    for path in _iter_docs_markdown_paths():
        metadata, _ = _split_front_matter(_read_text(path))
        route = _published_route_for_path(path, metadata)
        route_to_path[route] = path
        path_to_metadata[path] = metadata
        path_to_route[path] = route

    return route_to_path, path_to_metadata, path_to_route


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


def _normalize_jekyll_relative_url(link: str) -> str:
    match = JEKYLL_RELATIVE_URL_RE.fullmatch(link.strip())
    if match:
        return match.group(1)
    return link


def _is_published_docs_route_candidate(route: str) -> bool:
    return route not in {"/assets/main.css/", "/feed.xml/"}


def _resolve_internal_docs_target(  # pylint: disable=too-many-return-statements
    source: Path,
    raw_link: str,
    route_to_path: dict[str, Path],
    path_to_route: dict[Path, str],
) -> tuple[str | None, Path | None, str | None]:
    stripped = _normalize_jekyll_relative_url(raw_link.strip())
    if not stripped or stripped.startswith("#"):
        return None, None, None

    # Skip unresolved Jekyll template variables (e.g. {{ site.docs_home_url }})
    if JEKYLL_SITE_VAR_RE.search(stripped):
        return None, None, None

    parsed = urlparse(stripped)
    if parsed.scheme in {"mailto", "javascript", "tel"}:
        return None, None, None
    if parsed.scheme in {"http", "https"}:
        if parsed.netloc != MODULES_DOCS_HOST:
            return None, None, None
        route = _normalize_route(parsed.path or "/")
        if not _is_published_docs_route_candidate(route):
            return None, None, None
        target = route_to_path.get(route)
        if target is None:
            return route, None, f"{source.relative_to(_repo_root())} -> {route}"
        return route, target, None
    if parsed.scheme:
        return None, None, None

    target_value = unquote(parsed.path)
    if not target_value:
        return None, None, None

    if target_value.startswith("/"):
        route = _normalize_route(target_value)
        if not _is_published_docs_route_candidate(route):
            return None, None, None
        target = route_to_path.get(route)
        if target is None:
            return route, None, f"{source.relative_to(_repo_root())} -> {route}"
        return route, target, None

    candidate = (source.parent / target_value).resolve()
    if candidate.is_dir():
        readme_candidate = (candidate / "README.md").resolve()
        if readme_candidate.is_file() and _is_docs_markdown(readme_candidate):
            route = path_to_route.get(readme_candidate)
            if route is None:
                return None, None, f"{source.relative_to(_repo_root())} -> {target_value}"
            return route, readme_candidate, None
        return None, None, None

    if candidate.is_file() and _is_docs_markdown(candidate):
        route = path_to_route.get(candidate)
        if route is None:
            return None, None, f"{source.relative_to(_repo_root())} -> {target_value}"
        return route, candidate, None

    if not candidate.suffix:
        markdown_candidate = candidate.with_suffix(".md")
        if markdown_candidate.is_file() and _is_docs_markdown(markdown_candidate):
            resolved_candidate = markdown_candidate.resolve()
            route = path_to_route.get(resolved_candidate)
            if route is None:
                return None, None, f"{source.relative_to(_repo_root())} -> {target_value}"
            return route, resolved_candidate, None

    route = _normalize_route(target_value)
    if not _is_published_docs_route_candidate(route):
        return None, None, None
    target = route_to_path.get(route)
    if target is None:
        return route, None, f"{source.relative_to(_repo_root())} -> {target_value} (normalized: {route})"
    return route, target, None


def _navigation_sources() -> list[Path]:
    return [
        _repo_file("docs/index.md").resolve(),
        _repo_file("docs/_layouts/default.html").resolve(),
    ]


def _scan_navigation_targets() -> tuple[list[str], set[Path]]:
    route_to_path, _, path_to_route = _build_published_docs_index()
    failures: list[str] = []
    targets: set[Path] = set()

    for source in _navigation_sources():
        for link in _extract_links(source, _read_text(source)):
            _, target, failure = _resolve_internal_docs_target(source, link, route_to_path, path_to_route)
            if failure:
                failures.append(failure)
            if target is not None:
                targets.add(target)

    return failures, targets


def _scan_authored_doc_link_failures() -> tuple[list[str], set[Path]]:
    route_to_path, _, path_to_route = _build_published_docs_index()
    failures: list[str] = []
    targets: set[Path] = set()

    for source in _iter_docs_markdown_paths():
        metadata, body = _split_front_matter(_read_text(source))
        if not metadata:
            continue
        for link in _extract_links(source, body):
            _, target, failure = _resolve_internal_docs_target(source, link, route_to_path, path_to_route)
            if failure:
                failures.append(failure)
            if target is not None:
                targets.add(target)

    return failures, targets


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
    """Check internal links in authored docs with front matter.

    Pre-existing broken links in files not touched by the IA restructure are
    tracked separately (docs-09-missing-command-docs). This test reports all
    failures but only fails on files within the restructured directories.
    """
    restructured_prefixes = ("bundles/", "authoring/", "integrations/", "workflows/", "team-and-enterprise/")
    failures, _ = _scan_authored_doc_link_failures()
    restructured_failures = [
        f for f in failures if any(f"docs/{p}" in f.split(" -> ")[0] for p in restructured_prefixes)
    ]
    if failures and not restructured_failures:
        warnings.warn(
            f"Pre-existing broken authored docs links ({len(failures)} total):\n"
            + "\n".join(sorted(failures)[:10])
            + ("\n  ..." if len(failures) > 10 else ""),
            stacklevel=1,
        )
    assert not restructured_failures, "Broken authored docs links in restructured files:\n" + "\n".join(
        sorted(restructured_failures)
    )


def test_navigation_link_targets_have_required_front_matter_keys() -> None:
    """Nav link targets must have layout, title, and permalink.

    Pre-existing files without front matter are warned but not failed,
    to avoid blocking the restructure on unrelated debt.
    """
    restructured_prefixes = ("bundles/", "authoring/", "integrations/", "workflows/", "team-and-enterprise/")
    _, targets = _scan_navigation_targets()
    _, path_to_metadata, _ = _build_published_docs_index()
    missing: list[str] = []

    for target in sorted(targets):
        metadata = path_to_metadata[target]
        missing_keys = [key for key in REQUIRED_NAV_FRONT_MATTER_KEYS if not metadata.get(key)]
        if missing_keys:
            missing.append(f"{target.relative_to(_repo_root())}: missing {', '.join(missing_keys)}")

    restructured_missing = [m for m in missing if any(p in m for p in restructured_prefixes)]
    preexisting_missing = [m for m in missing if m not in restructured_missing]
    if preexisting_missing:
        warnings.warn(
            f"Pre-existing nav targets missing front matter ({len(preexisting_missing)}):\n"
            + "\n".join(preexisting_missing),
            stacklevel=1,
        )
    assert not restructured_missing, "Restructured nav targets missing required front matter keys:\n" + "\n".join(
        restructured_missing
    )


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


# ---------------------------------------------------------------------------
# Config plugin alignment
# ---------------------------------------------------------------------------


def test_config_includes_redirect_from_plugin() -> None:
    config = _read_text(_repo_file("docs/_config.yml"))
    assert "jekyll-redirect-from" in config


def test_gemfile_includes_redirect_from_gem() -> None:
    gemfile = _read_text(_repo_file("docs/Gemfile"))
    assert "jekyll-redirect-from" in gemfile
