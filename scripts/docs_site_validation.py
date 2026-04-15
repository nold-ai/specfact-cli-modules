"""Shared Jekyll docs validation: published routes, body links, front matter.

Used by ``scripts/check-docs-commands.py``, unit tests, and CI. Resolves
Markdown links relative to each page's *published* permalink (browser
semantics), not the repository source path.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any, NamedTuple
from urllib.parse import unquote, urljoin, urlparse

import yaml
from beartype import beartype
from icontract import ensure, require


# pylint: disable=unnecessary-lambda  # icontract lambdas are intentional for introspection


MODULES_DOCS_HOST = "modules.specfact.io"
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
# HTML <a href="..."> or <a href='...'> (single line; skips handled in extract_markdown_links_with_lines)
HTML_ANCHOR_HREF_RE = re.compile(r"""href\s*=\s*(["'])(?P<u>[^"'<>]+)\1""", re.IGNORECASE)
JEKYLL_RELATIVE_URL_RE = re.compile(r'\{\{\s*[\'"]([^\'"]+)[\'"]\s*\|\s*relative_url\s*\}\}')
JEKYLL_SITE_VAR_RE = re.compile(r"\{\{.*\}\}")
YAML_DELIM = "---"
_SKIP_PARTS = frozenset({"_site", "vendor", ".bundle", ".jekyll-cache"})
_REQUIRED_PAGE_KEYS = ("layout", "title", "permalink")


class ValidationFinding(NamedTuple):
    category: str
    source: Path
    line_number: int
    message: str


class DocsLinkResolutionContext(NamedTuple):
    """Frozen bundle for link resolution to keep helper arity low."""

    docs_root: Path
    route_to_path: dict[str, Path]
    path_to_route: dict[Path, str]
    modules_host: str


@beartype
@require(lambda script_file: isinstance(script_file, Path))
@ensure(lambda result: isinstance(result, Path))
def repo_root_from_here(script_file: Path) -> Path:
    return script_file.resolve().parents[1]


@beartype
@require(lambda path, docs_root: isinstance(path, Path) and isinstance(docs_root, Path))
@ensure(lambda result: isinstance(result, bool))
def is_docs_markdown(path: Path, docs_root: Path) -> bool:
    if path.suffix != ".md":
        return False
    try:
        rel = path.resolve().relative_to(docs_root)
    except ValueError:
        return False
    return not _SKIP_PARTS.intersection(rel.parts)


@beartype
@require(lambda path, docs_root: isinstance(path, Path) and isinstance(docs_root, Path))
@ensure(lambda result: isinstance(result, bool))
def is_publishable_page(path: Path, docs_root: Path) -> bool:
    """True for normal docs pages; READMEs only when they use Jekyll front matter (directory indexes)."""
    if not is_docs_markdown(path, docs_root):
        return False
    if path.name.lower() != "readme.md":
        return True
    lines = path.read_text(encoding="utf-8").splitlines()
    return bool(lines and lines[0].strip() == YAML_DELIM)


@beartype
@require(lambda docs_root: isinstance(docs_root, Path))
@ensure(lambda result: isinstance(result, list))
def iter_docs_markdown_paths(docs_root: Path) -> list[Path]:
    return sorted(p.resolve() for p in docs_root.rglob("*.md") if is_docs_markdown(p, docs_root))


@beartype
@require(lambda route: isinstance(route, str))
@ensure(lambda result: isinstance(result, str) and result.startswith("/"))
def normalize_route(route: str) -> str:
    cleaned = unquote(route.strip())
    if not cleaned:
        return "/"
    if not cleaned.startswith("/"):
        cleaned = "/" + cleaned
    cleaned = re.sub(r"/{2,}", "/", cleaned)
    if cleaned != "/" and not cleaned.endswith("/"):
        cleaned += "/"
    return cleaned


@beartype
@require(lambda text: isinstance(text, str))
@ensure(lambda result: isinstance(result, tuple) and len(result) == 3)
def split_yaml_front_matter(text: str) -> tuple[dict[str, Any], str, int]:
    """Return front matter dict, body text, and line number where body starts."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != YAML_DELIM:
        return {}, text, 1

    for index in range(1, len(lines)):
        if lines[index].strip() == YAML_DELIM:
            raw_yaml = "\n".join(lines[1:index])
            try:
                data = yaml.safe_load(raw_yaml) or {}
            except yaml.YAMLError:
                return {}, text, 1
            if not isinstance(data, dict):
                return {}, text, 1
            body = "\n".join(lines[index + 1 :])
            return data, body, index + 2
    return {}, text, 1


@beartype
@require(lambda path, docs_root, front_matter: isinstance(path, Path) and isinstance(docs_root, Path))
@ensure(lambda result: isinstance(result, str))
def published_route_for_doc(path: Path, docs_root: Path, front_matter: dict[str, Any]) -> str:
    permalink = front_matter.get("permalink")
    if isinstance(permalink, str) and permalink.strip():
        return normalize_route(permalink)

    relative_path = path.relative_to(docs_root)
    if relative_path.name == "index.md":
        parent = relative_path.parent
        return "/" if str(parent) == "." else f"/{'/'.join(parent.parts)}/"
    if relative_path.name.lower() == "readme.md":
        parent = relative_path.parent
        return "/" if str(parent) == "." else f"/{'/'.join(parent.parts)}/"
    path_no_ext = relative_path.with_suffix("")
    if str(path_no_ext.parent) == ".":
        return f"/{path_no_ext.name}/" if path_no_ext.name else "/"
    return f"/{'/'.join(path_no_ext.parts)}/"


@beartype
@require(lambda front_matter: isinstance(front_matter, dict))
@ensure(lambda result: isinstance(result, list))
def list_redirect_from_routes(front_matter: dict[str, Any]) -> list[str]:
    raw = front_matter.get("redirect_from")
    if raw is None:
        return []
    if isinstance(raw, str):
        return [normalize_route(raw)]
    if isinstance(raw, list):
        routes: list[str] = []
        for item in raw:
            if isinstance(item, str):
                routes.append(normalize_route(item))
        return routes
    return []


@beartype
@require(lambda docs_root: isinstance(docs_root, Path))
@ensure(
    lambda result: (
        isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], dict) and isinstance(result[1], dict)
    )
)
def build_route_mappings(docs_root: Path) -> tuple[dict[str, Path], dict[Path, str]]:
    """Map routes to declaring files and resolved files to canonical routes in one tree pass."""
    route_to_path: dict[str, Path] = {}
    path_to_route: dict[Path, str] = {}

    for path in iter_docs_markdown_paths(docs_root):
        fm, _, _ = split_yaml_front_matter(path.read_text(encoding="utf-8"))
        if not fm:
            continue
        canonical = published_route_for_doc(path, docs_root, fm)
        route_to_path[canonical] = path
        for alias in list_redirect_from_routes(fm):
            route_to_path[alias] = path
        path_to_route[path.resolve()] = canonical
    return route_to_path, path_to_route


@beartype
@require(lambda docs_root: isinstance(docs_root, Path))
@ensure(lambda result: isinstance(result, dict))
def build_route_index(docs_root: Path) -> dict[str, Path]:
    """Map every published and redirect alias route to its declaring markdown file."""
    return build_route_mappings(docs_root)[0]


@beartype
@require(lambda docs_root: isinstance(docs_root, Path))
@ensure(lambda result: isinstance(result, dict))
def build_path_to_canonical_route(docs_root: Path) -> dict[Path, str]:
    """Map each markdown source path to its canonical published route."""
    return build_route_mappings(docs_root)[1]


def _normalize_jekyll_relative_url(link: str) -> str:
    match = JEKYLL_RELATIVE_URL_RE.fullmatch(link.strip())
    if match:
        return match.group(1)
    return link


def _ignored_internal_link(stripped: str, parsed_scheme: str) -> bool:
    if not stripped or stripped.startswith("#") or JEKYLL_SITE_VAR_RE.search(stripped):
        return True
    return parsed_scheme in {"mailto", "javascript", "tel"}


def _is_published_docs_route_candidate(route: str) -> bool:
    return route not in {"/assets/main.css/", "/feed.xml/"}


def _resolve_route(route: str, route_to_path: dict[str, Path]) -> tuple[Path | None, str | None]:
    if not _is_published_docs_route_candidate(route):
        return None, None
    target = route_to_path.get(route)
    if target is None:
        return None, f"missing published route {route}"
    return target, None


def _path_lookup_result(
    target_file: Path,
    target_value: str,
    route_to_path: dict[str, Path],
    path_to_route: dict[Path, str],
) -> tuple[Path | None, str | None]:
    route = path_to_route.get(target_file)
    if route is None:
        return None, f"{target_file}: no canonical route ({target_value})"
    if route not in route_to_path:
        return None, f"missing published route {route}"
    return target_file, None


def _resolve_candidate_markdown_target(
    candidate: Path,
    target_value: str,
    docs_root: Path,
    route_to_path: dict[str, Path],
    path_to_route: dict[Path, str],
) -> tuple[Path | None, str | None]:
    if candidate.is_dir():
        readme_candidate = (candidate / "README.md").resolve()
        if readme_candidate.is_file() and is_docs_markdown(readme_candidate, docs_root):
            return _path_lookup_result(readme_candidate, target_value, route_to_path, path_to_route)
        index_candidate = (candidate / "index.md").resolve()
        if index_candidate.is_file() and is_docs_markdown(index_candidate, docs_root):
            return _path_lookup_result(index_candidate, target_value, route_to_path, path_to_route)
        return None, None
    if candidate.is_file() and is_docs_markdown(candidate, docs_root):
        return _path_lookup_result(candidate, target_value, route_to_path, path_to_route)
    if candidate.suffix:
        return None, None
    markdown_candidate = candidate.with_suffix(".md")
    if markdown_candidate.is_file() and is_docs_markdown(markdown_candidate, docs_root):
        return _path_lookup_result(markdown_candidate.resolve(), target_value, route_to_path, path_to_route)
    return None, None


def _resolve_filesystem_relative(
    source: Path,
    ctx: DocsLinkResolutionContext,
    raw_link: str,
) -> tuple[Path | None, str | None]:
    """Resolve links the way repository-relative paths work on disk."""
    stripped = _normalize_jekyll_relative_url(raw_link.strip())
    parsed = urlparse(stripped)
    if _ignored_internal_link(stripped, parsed.scheme):
        return None, None

    if parsed.scheme in {"http", "https"}:
        if parsed.netloc != ctx.modules_host:
            return None, None
        route = normalize_route(parsed.path or "/")
        return _resolve_route(route, ctx.route_to_path)

    if parsed.scheme:
        return None, None

    target_value = unquote(parsed.path)
    if not target_value:
        return None, None

    if target_value.startswith("/"):
        route = normalize_route(target_value)
        return _resolve_route(route, ctx.route_to_path)

    candidate = (source.parent / target_value).resolve()
    result = _resolve_candidate_markdown_target(
        candidate, target_value, ctx.docs_root, ctx.route_to_path, ctx.path_to_route
    )
    if result[0] is not None or result[1] is not None:
        return result

    normalized_route = normalize_route(target_value)
    target, failure = _resolve_route(normalized_route, ctx.route_to_path)
    return (target, None) if failure is None else (None, failure)


def _uses_repo_relative_authoring(raw_link: str) -> bool:
    """Detect links authored against the docs tree rather than published URL segments."""
    stripped = raw_link.strip().split("#", 1)[0]
    return stripped.startswith("/") or ".." in stripped or ".md" in stripped.lower()


def _resolve_published_relative_url(
    published_page_route: str,
    target_path: str,
    fragment: str,
    ctx: DocsLinkResolutionContext,
) -> tuple[Path | None, str | None]:
    base = f"https://{ctx.modules_host}{published_page_route}"
    if not published_page_route.endswith("/"):
        base += "/"
    joined = urljoin(base, target_path + (f"#{fragment}" if fragment else ""))
    joined_parsed = urlparse(joined)
    if joined_parsed.netloc != ctx.modules_host:
        return None, None
    route = normalize_route(joined_parsed.path or "/")
    return _resolve_route(route, ctx.route_to_path)


def _resolve_http_or_opaque(parsed, ctx: DocsLinkResolutionContext) -> tuple[Path | None, str | None] | None:
    """Return a finished resolution for HTTP(S) modules links, or ``None`` to continue."""
    if parsed.scheme in {"http", "https"}:
        if parsed.netloc != ctx.modules_host:
            return None, None
        route = normalize_route(parsed.path or "/")
        return _resolve_route(route, ctx.route_to_path)
    if parsed.scheme:
        return None, None
    return None


@beartype
@require(
    lambda source, ctx, published_page_route, raw_link: (
        isinstance(source, Path)
        and isinstance(ctx, DocsLinkResolutionContext)
        and isinstance(published_page_route, str)
        and isinstance(raw_link, str)
    )
)
@ensure(lambda result: isinstance(result, tuple) and len(result) == 2)
def resolve_internal_link_hybrid(
    *,
    source: Path,
    ctx: DocsLinkResolutionContext,
    published_page_route: str,
    raw_link: str,
) -> tuple[Path | None, str | None]:
    """Resolve internal links; bare segments use published URL semantics."""
    stripped = _normalize_jekyll_relative_url(raw_link.strip())
    parsed = urlparse(stripped)
    if _ignored_internal_link(stripped, parsed.scheme):
        return None, None

    http_or_opaque = _resolve_http_or_opaque(parsed, ctx)
    if http_or_opaque is not None:
        return http_or_opaque

    target_path = unquote(parsed.path)
    fragment = parsed.fragment
    if parsed.netloc or not target_path:
        return None, None

    fs_first = _uses_repo_relative_authoring(raw_link)
    if fs_first:
        fs_target, fs_err = _resolve_filesystem_relative(source, ctx, raw_link)
        if fs_target is not None and fs_err is None:
            return fs_target, None

    pub_target, pub_err = _resolve_published_relative_url(published_page_route, target_path, fragment, ctx)
    if pub_err is None:
        return pub_target, None
    if fs_first:
        return pub_target, pub_err
    return pub_target, pub_err


@beartype
@require(lambda body: isinstance(body, str))
@ensure(lambda result: isinstance(result, list))
def extract_markdown_links_with_lines(body: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for line_number, line in enumerate(body.splitlines(), start=1):
        if "<!-- TODO:" in line:
            continue
        seen_urls: set[str] = set()
        for match in MARKDOWN_LINK_RE.finditer(line):
            url = match.group(1)
            if url not in seen_urls:
                seen_urls.add(url)
                found.append((line_number, url))
        for match in HTML_ANCHOR_HREF_RE.finditer(line):
            url = match.group("u")
            if url not in seen_urls:
                seen_urls.add(url)
                found.append((line_number, url))
    return found


@beartype
@require(lambda docs_root, repo_root: isinstance(docs_root, Path) and isinstance(repo_root, Path))
@ensure(lambda result: isinstance(result, list))
def scan_published_route_body_links(docs_root: Path, repo_root: Path) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    route_to_path, path_to_route = build_route_mappings(docs_root)
    ctx = DocsLinkResolutionContext(docs_root, route_to_path, path_to_route, MODULES_DOCS_HOST)

    for path in iter_docs_markdown_paths(docs_root):
        text = path.read_text(encoding="utf-8")
        fm, body, body_start = split_yaml_front_matter(text)
        if not fm:
            continue
        published = published_route_for_doc(path, docs_root, fm)
        for offset, raw in extract_markdown_links_with_lines(body):
            target, err = resolve_internal_link_hybrid(
                source=path,
                ctx=ctx,
                published_page_route=published,
                raw_link=raw,
            )
            if err and target is None:
                rel = path.relative_to(repo_root)
                line_no = max(1, body_start + offset - 1)
                findings.append(
                    ValidationFinding(
                        "published-link",
                        path,
                        line_no,
                        f"{rel}: link `{raw}` resolves to broken route from {published} ({err})",
                    )
                )
    return findings


def _frontmatter_findings_for_publishable_path(path: Path, repo_root: Path) -> list[ValidationFinding]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    first = lines[0] if lines else ""
    rel = path.relative_to(repo_root)
    if first.strip() != YAML_DELIM:
        return [
            ValidationFinding(
                "frontmatter",
                path,
                1,
                f"{rel}: publishable page must start with Jekyll front matter ({YAML_DELIM})",
            )
        ]

    fm, _, _ = split_yaml_front_matter(text)
    missing = [k for k in _REQUIRED_PAGE_KEYS if not fm.get(k)]
    if not missing:
        return []
    return [
        ValidationFinding(
            "frontmatter",
            path,
            1,
            f"{rel}: missing required front matter keys: {', '.join(missing)}",
        )
    ]


@beartype
@require(lambda docs_root, repo_root: isinstance(docs_root, Path) and isinstance(repo_root, Path))
@ensure(lambda result: isinstance(result, list))
def scan_frontmatter_findings(docs_root: Path, repo_root: Path) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for path in iter_docs_markdown_paths(docs_root):
        if not is_publishable_page(path, docs_root):
            continue
        findings.extend(_frontmatter_findings_for_publishable_path(path, repo_root))
    return findings


@beartype
@require(lambda docs_root: isinstance(docs_root, Path))
@ensure(lambda result: isinstance(result, set))
def build_valid_internal_routes(docs_root: Path) -> set[str]:
    """All routes that should be treated as in-site targets (canonical + redirect aliases)."""
    route_to_path, _ = build_route_mappings(docs_root)
    return set(route_to_path.keys())


@beartype
@require(lambda docs_dir: isinstance(docs_dir, Path))
@ensure(lambda result: isinstance(result, list))
def scan_gemfile_lock_installability(docs_dir: Path) -> list[ValidationFinding]:
    """Run ``bundle check`` in ``docs_dir``; requires ``bundle`` on PATH (no silent skip)."""
    gemfile_lock = docs_dir / "Gemfile.lock"
    if not gemfile_lock.is_file():
        return [
            ValidationFinding(
                "docs-build-dependency",
                docs_dir / "Gemfile",
                1,
                "docs/Gemfile.lock is missing",
            )
        ]
    try:
        proc = subprocess.run(
            ["bundle", "check"],
            cwd=str(docs_dir),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return [
            ValidationFinding(
                "docs-build-dependency",
                gemfile_lock,
                1,
                "bundle check timed out after 120s",
            )
        ]

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        msg = "bundle check failed; run `cd docs && bundle install` locally"
        if detail:
            msg = f"{msg}: {detail[:500]}"
        return [ValidationFinding("docs-build-dependency", gemfile_lock, 1, msg)]
    return []


@beartype
@require(lambda repo_root, findings: isinstance(repo_root, Path) and isinstance(findings, list))
@ensure(lambda result: isinstance(result, str))
def format_findings(repo_root: Path, findings: list[ValidationFinding]) -> str:
    def _name(p: Path) -> str:
        try:
            return str(p.relative_to(repo_root))
        except ValueError:
            return str(p)

    return "\n".join(f"{_name(f.source)}:{f.line_number}: [{f.category}] {f.message}" for f in findings)
